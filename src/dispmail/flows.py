"""Flow engine: ordered steps, the submit gate, success detection and exit codes."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from random import Random
from typing import Protocol

from dispmail.accounts import Account, AccountExistsError, AccountRepository
from dispmail.artifacts import Artifacts
from dispmail.browser import (
    Browser,
    EgressFacts,
    EgressMismatchError,
    EgressProbe,
    StepTimeoutError,
    verify_egress,
)
from dispmail.challenges import GENERIC_CHALLENGES, ChallengeSignature, detect
from dispmail.credentials import Credentials, PasswordRules, generate
from dispmail.ledger import BudgetError, Ledger, attempt, run_lock
from dispmail.settings import ExitCode, Settings

logger = logging.getLogger(__name__)


class FlowAbortError(Exception):
    """A provider deliberately stops the flow with a classified exit code."""

    def __init__(self, message: str, exit_code: ExitCode, outcome: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.outcome = outcome


class StepKind(StrEnum):
    PREPARE = "prepare"
    SUBMIT = "submit"


@dataclass(frozen=True, slots=True)
class Step:
    """One interaction; exactly one step per provider is the submit step."""

    name: str
    action: Callable[[Browser, Credentials], None]
    kind: StepKind = StepKind.PREPARE


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """Everything provider-specific, with locators kept as data."""

    name: str
    display: str
    url: str
    email_domain: str
    steps: tuple[Step, ...]
    success: Callable[[Browser], bool]
    success_description: str
    challenges: tuple[ChallengeSignature, ...] = ()
    password_rules: PasswordRules = field(default_factory=PasswordRules)
    faker_locale: str = "en_US"
    locale: str | None = None
    needs_attestation: bool = False
    plans: tuple[str, ...] = ("free",)
    domains: tuple[str, ...] = ()
    recovery: Callable[[Browser], str | None] | None = None
    recovery_extension: str = "txt"

    def submit_step(self) -> Step:
        for step in self.steps:
            if step.kind is StepKind.SUBMIT:
                return step
        msg = f"{self.name} has no submit step"
        raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class FlowResult:
    provider: str
    ok: bool
    exit_code: ExitCode
    outcome: str
    detail: str = ""
    account: Account | None = None
    egress: EgressFacts | None = None
    duration: float = 0.0
    artifacts: Path | None = None


class Confirmation(Protocol):  # pragma: no cover - interface only
    def confirm(self, prompt: str) -> bool: ...


class TerminalConfirmation:  # pragma: no cover - interactive
    """Ask a human at the terminal; used only when ``--manual`` is set."""

    def confirm(self, prompt: str) -> bool:
        answer = input(f"{prompt} [y/N]: ").strip().lower()
        return answer == "y"


class AutoConfirm:
    def confirm(self, prompt: str) -> bool:
        logger.info("auto-confirmed: %s", prompt)
        return True


class FlowRunner:
    """Execute a provider flow under the budget, egress and submit rules."""

    def __init__(
        self,
        browser: Browser,
        settings: Settings,
        probe: EgressProbe,
        store: AccountRepository,
        ledger: Ledger,
        confirm: Confirmation | None = None,
        persona_label: str | None = None,
    ) -> None:
        self.browser = browser
        self.settings = settings
        self.probe = probe
        self.store = store
        self.ledger = ledger
        self.persona_label = persona_label
        self.confirm = confirm or AutoConfirm()

    def run(
        self,
        spec: ProviderSpec,
        *,
        credentials: Credentials | None = None,
        rng: Random | None = None,
    ) -> FlowResult:
        started = time.monotonic()
        artifacts = Artifacts(self.settings.artifacts_dir, spec.name)
        try:
            with run_lock(self.settings.state_dir):
                return self._run_locked(spec, artifacts, started, credentials, rng)
        except BudgetError as exc:
            return self._record(
                spec,
                artifacts,
                started,
                ExitCode.BUDGET,
                "budget",
                str(exc),
            )
        except Exception as exc:  # classify, never leak a traceback
            logger.exception("unexpected failure in %s", spec.name)
            return FlowResult(
                provider=spec.name,
                ok=False,
                exit_code=ExitCode.FLOW_ERROR,
                outcome="flow-error",
                detail=f"{type(exc).__name__}: {exc}",
                duration=time.monotonic() - started,
                artifacts=artifacts.directory if artifacts.directory.exists() else None,
            )

    def _run_locked(  # noqa: C901, PLR0912 - the flow states are explicit on purpose
        self,
        spec: ProviderSpec,
        artifacts: Artifacts,
        started: float,
        credentials: Credentials | None,
        rng: Random | None,
    ) -> FlowResult:
        if self.store.find(platform=spec.name) and not self.settings.replace_account:
            return self._record(
                spec,
                artifacts,
                started,
                ExitCode.BUDGET,
                "budget",
                f"{spec.name} already has an account in {self.store.db_path}; "
                "only one account per provider is allowed "
                "(pass --replace-account if the old account is gone)",
            )
        self.ledger.check(
            spec.name,
            self.settings.egress.name,
            allow_replacement=self.settings.replace_account,
        )
        self.ledger.record(
            attempt(spec.name, self.settings.egress.name, "started", int(ExitCode.OK))
        )

        try:
            facts = self.probe.check(self.browser)
            verify_egress(
                self.settings.egress,
                facts,
                home_ip=self.settings.home_ip,
            )
        except EgressMismatchError as exc:
            return self._record(
                spec,
                artifacts,
                started,
                ExitCode.EGRESS_MISMATCH,
                "egress-mismatch",
                str(exc),
            )

        creds = credentials or generate(
            spec.password_rules,
            faker_locale=spec.faker_locale,
            rng=rng,
        )
        artifacts.secrets = (creds.password,)
        if spec.needs_attestation and self.settings.submit and not self.settings.accept_attestation:
            return self._record(
                spec,
                artifacts,
                started,
                ExitCode.USAGE,
                "attestation-required",
                "this provider requires --accept-attestation for a live run",
                egress=facts,
            )

        account_email = f"{creds.username}@{spec.email_domain}"
        pending: Path | None = None
        if self.settings.submit:
            pending = self.store.stash_pending(Account(account_email, creds.password), spec.name)
            logger.info("credentials held at %s until submit is confirmed", pending)

        self.browser.goto(spec.url)
        for step in spec.steps:
            challenge = detect(self.browser, spec.challenges + GENERIC_CHALLENGES)
            if challenge is not None:
                blocked = self._handle_challenge(spec, artifacts, step.name, challenge)
                if blocked is not None:
                    return self._finish_failure(spec, artifacts, started, blocked, facts)
            if step.kind is StepKind.SUBMIT and not self.settings.submit:
                return self._record(
                    spec,
                    artifacts,
                    started,
                    ExitCode.OK,
                    "dry-run",
                    f"stopped before submit step {step.name!r}",
                    egress=facts,
                )
            outcome = self._execute_step(spec, step, creds, artifacts)
            if outcome is not None:
                return self._finish_failure(spec, artifacts, started, outcome, facts)

        wait_budget = (
            self.settings.assist_timeout if self.settings.assisted else self.settings.submit_timeout
        )
        success, challenge = self._wait_for_success(spec, wait_budget)
        if challenge is not None:
            blocked = self._challenge_result(spec, artifacts, challenge)
            return self._finish_failure(spec, artifacts, started, blocked, facts)
        if not success:
            artifacts.capture(self.browser, "rejected")
            return self._record(
                spec,
                artifacts,
                started,
                ExitCode.REJECTED,
                "rejected",
                "submit completed but success was never observed",
                egress=facts,
            )
        if self.settings.manual and not self.confirm.confirm(
            f"{spec.display}: has the account been created?"
        ):
            return self._record(
                spec,
                artifacts,
                started,
                ExitCode.REJECTED,
                "manual-rejected",
                "operator said the account was not created",
                egress=facts,
            )

        recovery = self._extract_recovery(spec)
        account = Account(
            email=account_email,
            password=creds.password,
            recovery=recovery,
        )
        if recovery:
            artifacts.secrets = (creds.password, recovery)
        try:
            self.store.add(
                account,
                platform=spec.name,
                egress=f"{self.settings.egress.name}:{facts.country}",
                persona=self.persona_label,
                recovery_extension=spec.recovery_extension,
            )
        except AccountExistsError as exc:
            logger.warning("%s", exc)
            return self._record(
                spec,
                artifacts,
                started,
                ExitCode.EXISTS,
                "exists",
                "an account with this address is already recorded",
                egress=facts,
            )
        except Exception as exc:
            logger.exception("the account exists but could not be stored")
            return self._record(
                spec,
                artifacts,
                started,
                ExitCode.FLOW_ERROR,
                "store-error",
                f"{type(exc).__name__}: {exc}",
                egress=facts,
            )
        try:
            self.ledger.record(
                attempt(
                    spec.name,
                    self.settings.egress.name,
                    "created",
                    int(ExitCode.OK),
                    account_hash=self.ledger.account_hash(account.email),
                )
            )
        except OSError:
            logger.exception("the account was stored but the ledger write failed")
        if pending is not None:
            self.store.clear_pending(account.email, spec.name)
        logger.info("created %s", account.email)
        return FlowResult(
            provider=spec.name,
            ok=True,
            exit_code=ExitCode.OK,
            outcome="created",
            detail=account.email,
            account=account,
            egress=facts,
            duration=time.monotonic() - started,
        )

    def _extract_recovery(self, spec: ProviderSpec) -> str | None:
        """Recovery extraction is best effort: it must never lose the account row."""
        if spec.recovery is None:
            return None
        try:
            return spec.recovery(self.browser)
        except Exception:  # noqa: BLE001 - the account is already created
            logger.warning("could not extract the recovery kit; capture it manually")
            return None

    def _execute_step(
        self,
        spec: ProviderSpec,
        step: Step,
        creds: Credentials,
        artifacts: Artifacts,
    ) -> FlowResult | None:
        logger.info("%s: %s", spec.name, step.name)
        artifacts.write_event({"event": "step-start", "provider": spec.name, "step": step.name})
        try:
            step.action(self.browser, creds)
        except FlowAbortError as exc:
            artifacts.capture(self.browser, f"{step.name}-aborted")
            return FlowResult(
                provider=spec.name,
                ok=False,
                exit_code=exc.exit_code,
                outcome=exc.outcome,
                detail=f"step {step.name!r}: {exc}",
                artifacts=artifacts.directory,
            )
        except StepTimeoutError as exc:
            artifacts.capture(self.browser, f"{step.name}-timeout")
            challenge = detect(self.browser, spec.challenges + GENERIC_CHALLENGES)
            if challenge is not None:
                if (
                    self.settings.assisted
                    and not self.settings.headless
                    and self._wait_for_challenge_clear(spec)
                ):
                    # The human cleared it; retry the blocked interaction exactly once.
                    try:
                        step.action(self.browser, creds)
                    except Exception as retry_exc:
                        logger.exception("retrying %s after the handoff failed", step.name)
                        return FlowResult(
                            provider=spec.name,
                            ok=False,
                            exit_code=ExitCode.FLOW_ERROR,
                            outcome="flow-error",
                            detail=f"step {step.name!r} retry: {retry_exc}",
                            artifacts=artifacts.directory,
                        )
                    return None
                return self._challenge_result(spec, artifacts, challenge)
            return FlowResult(
                provider=spec.name,
                ok=False,
                exit_code=ExitCode.PROVIDER_CHANGED,
                outcome="provider-changed",
                detail=f"step {step.name!r}: {exc}",
                artifacts=artifacts.directory,
            )
        except Exception as exc:  # classified at the step boundary
            logger.exception("step %s failed", step.name)
            artifacts.capture(self.browser, f"{step.name}-error")
            return FlowResult(
                provider=spec.name,
                ok=False,
                exit_code=ExitCode.FLOW_ERROR,
                outcome="flow-error",
                detail=f"step {step.name!r}: {type(exc).__name__}: {exc}",
                artifacts=artifacts.directory,
            )
        artifacts.write_event({"event": "step-end", "provider": spec.name, "step": step.name})

        challenge = detect(self.browser, spec.challenges + GENERIC_CHALLENGES)
        if challenge is None:
            return None
        return self._handle_challenge(spec, artifacts, step.name, challenge)

    def _handle_challenge(
        self,
        spec: ProviderSpec,
        artifacts: Artifacts,
        step_name: str,
        challenge: ChallengeSignature,
    ) -> FlowResult | None:
        """Return ``None`` when assisted mode cleared it, else the CHALLENGE result."""
        artifacts.write_event(
            {
                "event": "challenge",
                "provider": spec.name,
                "step": step_name,
                "signature": challenge.description,
            }
        )
        if (
            self.settings.assisted
            and not self.settings.headless
            and self._wait_for_challenge_clear(spec)
        ):
            return None
        return self._challenge_result(spec, artifacts, challenge)

    def _challenge_result(
        self,
        spec: ProviderSpec,
        artifacts: Artifacts,
        challenge: ChallengeSignature,
    ) -> FlowResult:
        artifacts.capture(self.browser, "challenge")
        return FlowResult(
            provider=spec.name,
            ok=False,
            exit_code=ExitCode.CHALLENGE,
            outcome="challenge",
            detail=challenge.description,
            artifacts=artifacts.directory if artifacts.directory.exists() else None,
        )

    def _wait_for_success(
        self,
        spec: ProviderSpec,
        timeout: float,
    ) -> tuple[bool, ChallengeSignature | None]:
        deadline = time.monotonic() + timeout
        assisted = self.settings.assisted and not self.settings.headless
        while time.monotonic() < deadline:
            try:
                if spec.success(self.browser):
                    return True, None
            except Exception:  # the page may be mid-navigation
                logger.debug("success check raised; retrying", exc_info=True)
            challenge = detect(self.browser, spec.challenges + GENERIC_CHALLENGES)
            if challenge is not None:
                if not assisted:
                    return False, challenge
                if not self._wait_for_challenge_clear(spec):
                    return False, challenge
            time.sleep(1)
        return False, None

    def _wait_for_challenge_clear(self, spec: ProviderSpec) -> bool:
        deadline = time.monotonic() + self.settings.assist_timeout
        while time.monotonic() < deadline:
            if detect(self.browser, spec.challenges + GENERIC_CHALLENGES) is None:
                return True
            time.sleep(2)
        return False

    def _finish_failure(
        self,
        spec: ProviderSpec,
        artifacts: Artifacts,
        started: float,
        result: FlowResult,
        facts: EgressFacts,
    ) -> FlowResult:
        return self._record(
            spec,
            artifacts,
            started,
            result.exit_code,
            result.outcome,
            result.detail,
            egress=facts,
            challenged=result.exit_code is ExitCode.CHALLENGE,
        )

    def _record(
        self,
        spec: ProviderSpec,
        artifacts: Artifacts,
        started: float,
        exit_code: ExitCode,
        outcome: str,
        detail: str,
        *,
        egress: EgressFacts | None = None,
        challenged: bool = False,
    ) -> FlowResult:
        try:
            self.ledger.record(
                attempt(
                    spec.name,
                    self.settings.egress.name,
                    outcome,
                    int(exit_code),
                    challenged=challenged,
                    detail=detail,
                )
            )
        except OSError:
            logger.exception("could not append to the ledger")
        return FlowResult(
            provider=spec.name,
            ok=exit_code is ExitCode.OK,
            exit_code=exit_code,
            outcome=outcome,
            detail=detail,
            egress=egress,
            duration=time.monotonic() - started,
            artifacts=artifacts.directory if artifacts.directory.exists() else None,
        )
