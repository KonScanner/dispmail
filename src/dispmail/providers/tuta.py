"""Tuta (formerly Tutanota) free-plan signup flow.

Selectors come from live recon on 2026-11-03: ``docs/recon/tuta-signup.md``.
The page is a single-URL React SPA; every element is re-queried after each step.
"""

import logging
import re
import time
from dataclasses import replace
from functools import partial
from pathlib import Path

from dispmail.browser import Browser, Locator, css, text, xpath
from dispmail.challenges import TUTA_CHALLENGES
from dispmail.credentials import Credentials, PasswordRules
from dispmail.flows import FlowAbortError, ProviderSpec, Step, StepKind
from dispmail.providers.contracts import Contract
from dispmail.settings import ExitCode

logger = logging.getLogger(__name__)

SIGNUP_URL = "https://app.tuta.com/signup"
DOMAINS = ("tuta.com", "tutamail.com", "tuta.io", "tutanota.com", "tutanota.de", "keemail.me")

PLAN_FREE = css('#plan-selector input[name="BuyOptionBox"] >> nth=2')
CONTINUE = css('button[data-testid="btn:continue_action"]')
USERNAME = css('input[data-testid="tfi:username_label"]')
DOMAIN_BUTTON = css('button[data-testid="btn:domain_label"]')
PASSWORD = css('input[data-testid="tfi:newPassword_label"]')
PASSWORD_REPEAT = css('input[data-testid="tfi:repeatedPassword_label"]')
ATTESTATION_INPUT = css('#signup-account-dialog input[type="checkbox"] >> nth=0')
TERMS_INPUT = css('#signup-account-dialog input[type="checkbox"] >> nth=1')
CREATE = css('button[data-testid="btn:create_new_account_label"]')
RECOVERY_BUTTON = css('button[aria-label="Recovery Kit"]')
MAIL_VIEW = css('[data-testid="collapsed-mail-view"]')
AVAILABLE = text("Email address is available.")
NOT_AVAILABLE = text("Email address is not available.")
SET_PASSWORD_MESSAGE = text("Please enter a new password.")
PAID_DOMAIN_MODAL = text("a subscription is needed")


def domain_option(domain: str) -> Locator:
    return css(f'button[role="option"][title="{domain}"]')


def _select_free(browser: Browser, _credentials: Credentials) -> None:
    browser.click(PLAN_FREE)
    if not browser.is_checked(PLAN_FREE):
        msg = "the Free plan radio did not stay selected"
        raise FlowAbortError(msg, ExitCode.PROVIDER_CHANGED, "provider-changed")
    browser.click(CONTINUE)
    browser.wait_for(USERNAME)


def _status_available(browser: Browser, timeout: float) -> bool:
    """Poll Tuta's inline availability message; unknown means try (submit re-validates)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        content = browser.content().lower()
        if "email address is not available" in content:
            return False
        if "email address is available" in content:
            return True
        if "verifying email address" in content:
            time.sleep(0.3)
            continue
        time.sleep(0.3)
    logger.warning("username availability did not settle; trying the candidate")
    return True


def _choose_username(browser: Browser, credentials: Credentials, timeout: float) -> Credentials:
    candidates = (credentials.username, *credentials.alternatives)[:6]
    for username in candidates:
        browser.fill(USERNAME, username)
        if _status_available(browser, timeout):
            return replace(credentials, username=username, alternatives=())
    msg = f"none of the {len(candidates)} generated usernames were available"
    raise FlowAbortError(msg, ExitCode.EXISTS, "exists")


def _fill_account(
    browser: Browser, credentials: Credentials, domain: str, timeout: float
) -> Credentials:
    chosen = _choose_username(browser, credentials, timeout)
    browser.click(DOMAIN_BUTTON)
    browser.click(domain_option(domain))
    if browser.has(PAID_DOMAIN_MODAL, timeout=1.5):
        msg = (
            f"the {domain} domain needs a paid Tuta plan; "
            "use --domain tutamail.com (the free default) or another free domain"
        )
        raise FlowAbortError(msg, ExitCode.USAGE, "paid-domain")
    browser.fill(PASSWORD, credentials.password)
    browser.fill(PASSWORD_REPEAT, credentials.password)
    browser.click(ATTESTATION_INPUT)
    browser.click(TERMS_INPUT)
    if not browser.is_checked(ATTESTATION_INPUT) or not browser.is_checked(TERMS_INPUT):
        msg = "one of the two required agreements did not get checked"
        raise FlowAbortError(msg, ExitCode.PROVIDER_CHANGED, "provider-changed")
    browser.wait_enabled(CREATE, timeout=8)
    return chosen


def _submit(browser: Browser, _credentials: Credentials) -> None:
    browser.click(CREATE)


def _success(browser: Browser) -> bool:
    if "/mail" in browser.url():
        return True
    if browser.has(MAIL_VIEW):
        return True
    return browser.has(RECOVERY_BUTTON) and browser.is_enabled(RECOVERY_BUTTON)


# Tuta shows 64 hex characters as 16 groups of four, space separated over four lines.
_RECOVERY_PATTERN = re.compile(r"(?:[0-9a-f]{4}\s+){15}[0-9a-f]{4}", re.IGNORECASE)


def _recovery(browser: Browser) -> str | None:
    """Return the 64-character recovery code, normalised to one line of 4-char groups."""
    body = browser.text_of(xpath("//body"))
    match = _RECOVERY_PATTERN.search(body)
    if match is None:
        logger.warning("no recovery code found on the recovery kit page")
        return None
    return " ".join(match.group(0).split()).lower()


def build(domain: str = "tutamail.com", *, username_timeout: float = 12.0) -> ProviderSpec:
    """Build the Tuta spec for one domain choice."""
    if domain not in DOMAINS:
        msg = f"unknown Tuta domain {domain!r}; choose one of {', '.join(DOMAINS)}"
        raise ValueError(msg)
    return ProviderSpec(
        name="tuta",
        display="Tuta",
        url=SIGNUP_URL,
        email_domain=domain,
        steps=(
            Step("select-free-plan", _select_free),
            Step(
                "fill-account",
                partial(_fill_account, domain=domain, timeout=username_timeout),
            ),
            Step("create-account", _submit, StepKind.SUBMIT),
        ),
        success=_success,
        success_description="recovery kit or inbox reached",
        challenges=TUTA_CHALLENGES,
        password_rules=PasswordRules(min_length=12, max_length=64),
        faker_locale="en_US",
        locale="en-US",
        needs_attestation=True,
        plans=("free",),
        domains=DOMAINS,
        recovery=_recovery,
        failure_texts=("Could not reach server",),
        blocked_texts=("Registration is temporarily blocked",),
    )


CONTRACTS: tuple[Contract, ...] = (
    Contract(
        "plan",
        Path("docs/recon/tuta-step-1.html"),
        (PLAN_FREE, CONTINUE),
    ),
    Contract(
        "form",
        Path("docs/recon/tuta-step-3.html"),
        (
            USERNAME,
            DOMAIN_BUTTON,
            PASSWORD,
            PASSWORD_REPEAT,
            ATTESTATION_INPUT,
            TERMS_INPUT,
            CREATE,
        ),
    ),
    Contract(
        "domain-menu",
        Path("docs/recon/tuta-step-4-domain-menu.html"),
        (domain_option("tuta.com"),),
    ),
)
