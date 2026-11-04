"""Attempt ledger: budget caps, cooldowns and the single-run lock."""

import fcntl
import hashlib
import json
import logging
import secrets
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

CHALLENGE_COOLDOWN = timedelta(hours=24)
SECOND_CHALLENGE_COOLDOWN = timedelta(days=7)
CHALLENGE_WINDOW = timedelta(days=30)
WEEKLY_WINDOW = timedelta(days=7)


class BudgetError(Exception):
    """The run would exceed a cap, a cooldown or the concurrency lock."""


@dataclass(frozen=True, slots=True)
class Attempt:
    """One run of one provider, with no secret material."""

    ts: str
    provider: str
    egress: str
    outcome: str
    exit_code: int
    challenged: bool = False
    account_hash: str | None = None
    detail: str = ""

    @property
    def when(self) -> datetime:
        parsed = datetime.fromisoformat(self.ts)
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class Ledger:
    """JSONL state under the state directory; safe to delete when starting over."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.path = state_dir / "ledger.jsonl"
        self._salt_path = state_dir / "salt"

    def _salt(self) -> str:
        if not self._salt_path.exists():
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self._salt_path.write_text(secrets.token_hex(16), encoding="utf-8")
            self._salt_path.chmod(0o600)
        return self._salt_path.read_text(encoding="utf-8").strip()

    def account_hash(self, email: str) -> str:
        digest = hashlib.sha256(f"{self._salt()}:{email}".encode()).hexdigest()
        return digest[:16]

    def read(self) -> list[Attempt]:
        if not self.path.exists():
            return []
        attempts: list[Attempt] = []
        known = set(Attempt.__dataclass_fields__)
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("ignoring corrupt ledger line %d", number)
                continue
            if not isinstance(payload, dict):
                logger.warning("ignoring non-object ledger line %d", number)
                continue
            try:
                attempt = Attempt(**{key: value for key, value in payload.items() if key in known})
                _ = attempt.when  # validate the timestamp now, not during a budget check
            except TypeError, ValueError:
                logger.warning("ignoring corrupt ledger line %d", number)
                continue
            attempts.append(attempt)
        return attempts

    def record(self, attempt: Attempt) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(attempt), ensure_ascii=False) + "\n")
        self.path.chmod(0o600)

    def created_for(self, provider: str, *, since: datetime | None = None) -> list[Attempt]:
        return [
            attempt
            for attempt in self.read()
            if attempt.provider == provider
            and attempt.outcome in {"created", "created-unstored"}
            and (since is None or attempt.when >= since)
        ]

    def challenges_for(self, provider: str, egress: str) -> list[Attempt]:
        cutoff = datetime.now(UTC) - CHALLENGE_WINDOW
        return [
            attempt
            for attempt in self.read()
            if attempt.provider == provider
            and attempt.egress == egress
            and attempt.challenged
            and attempt.when >= cutoff
        ]

    def cooldown_until(self, provider: str, egress: str) -> datetime | None:
        challenges = self.challenges_for(provider, egress)
        if not challenges:
            return None
        window = CHALLENGE_COOLDOWN if len(challenges) == 1 else SECOND_CHALLENGE_COOLDOWN
        return max(challenge.when for challenge in challenges) + window

    def check(
        self,
        provider: str,
        egress: str,
        *,
        allow_replacement: bool = False,
        weekly_limit: int = 4,
    ) -> None:
        """Raise :class:`BudgetError` when this run must not start."""
        recent = self.created_for(provider, since=datetime.now(UTC) - WEEKLY_WINDOW)
        if len(recent) >= weekly_limit and not allow_replacement:
            msg = (
                f"{provider} reached {weekly_limit} accounts in the last 7 days "
                "(pass --replace-account if an old account is gone)"
            )
            raise BudgetError(msg)
        until = self.cooldown_until(provider, egress)
        if until is not None and datetime.now(UTC) < until:
            msg = f"{provider} on egress {egress!r} is cooling down until {until.isoformat()}"
            raise BudgetError(msg)


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def attempt(
    provider: str,
    egress: str,
    outcome: str,
    exit_code: int,
    *,
    challenged: bool = False,
    account_hash: str | None = None,
    detail: str = "",
    ts: str | None = None,
) -> Attempt:
    return Attempt(
        ts=ts or now_iso(),
        provider=provider,
        egress=egress,
        outcome=outcome,
        exit_code=exit_code,
        challenged=challenged,
        account_hash=account_hash,
        detail=detail,
    )


@contextmanager
def run_lock(state_dir: Path, *, timeout: float = 0.0) -> Generator[None]:
    """Hold an exclusive lock for the duration of a run."""
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / "run.lock"
    handle = lock_path.open("a+", encoding="utf-8")
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    msg = "another dispmail run holds the lock"
                    raise BudgetError(msg) from exc
                time.sleep(0.2)
            else:
                break
        yield
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
