"""Interia free-mailbox signup flow.

Selectors come from live recon on 2026-11-03: ``docs/recon/interia-signup.md``.
Two things make this path different from Tuta: the identity fields get a new
random ``id``/``name`` on every load (so they are addressed by order, excluding
honeypots) and submit continues into a captcha/verification flow that only a
human can finish.
"""

import time
from functools import partial
from pathlib import Path

from dispmail.browser import Browser, Locator, StepTimeoutError, css, text, xpath
from dispmail.challenges import INTERIA_CHALLENGES
from dispmail.credentials import Credentials, PasswordRules
from dispmail.flows import FlowAbortError, ProviderSpec, Step, StepKind
from dispmail.providers.contracts import Contract
from dispmail.settings import ExitCode

SIGNUP_URL = "https://konto-pocztowe.interia.pl/#/nowe-konto/darmowe"
EMAIL_DOMAIN = "interia.pl"

MONTHS = (
    "Styczeń",
    "Luty",
    "Marzec",
    "Kwiecień",
    "Maj",
    "Czerwiec",
    "Lipiec",
    "Sierpień",
    "Wrzesień",
    "Październik",
    "Listopad",
    "Grudzień",
)

CONSENT_MODAL = css('button[aria-label="Przejdź do serwisu"]')
# The three identity text inputs, in visual order, excluding birthday, honeypots and
# the fake inputs inside the custom selects. Every other attribute is randomised.
IDENTITY_INPUTS = (
    "//form//input[@type='text' and not(contains(@class,'account-input'))"
    " and not(contains(@class,'input--fake')) and not(contains(@class,'fake-input'))"
    " and not(@id='infoInput')]"
)
FIRST_NAME = xpath(f"({IDENTITY_INPUTS})[1]")
LAST_NAME = xpath(f"({IDENTITY_INPUTS})[2]")
USERNAME = xpath(f"({IDENTITY_INPUTS})[3]")
DAY = css("#birthdayDay")
YEAR = css("#birthdayYear")
_MONTH_CONTAINER = "//div[contains(@class,'account-select')][.//label[normalize-space()='Miesiąc']]"
_GENDER_CONTAINER = "//div[contains(@class,'account-input__label--gender')]"
MONTH_SELECT = xpath(_MONTH_CONTAINER)
GENDER_SELECT = xpath(_GENDER_CONTAINER)
MONTH_OPTIONS = xpath(f"{_MONTH_CONTAINER}//ul[contains(@class,'account-select__options')]")
GENDER_OPTIONS = xpath(f"{_GENDER_CONTAINER}//ul[contains(@class,'account-select__options')]")
PASSWORD = css("#password")
PASSWORD_REPEAT = css("#rePassword")
CONSENT_ALL_LABEL = xpath("//label[.//input[@name='agreementacceptAll-acceptAll']]")
CONSENT_EXPAND = xpath("(//button[contains(@class,'expand-button')])[1]")
CONSENT_TERMS_LABEL = xpath("//label[.//input[@name='agreement74-213']]")
CONSENT_TERMS_INPUT = xpath("//input[@name='agreement74-213']")
SUBMIT = css('form button[type="submit"]')
LOGGED_IN = text("Wyloguj")


def month_option(month: str) -> Locator:
    return xpath(f"{_MONTH_CONTAINER}//li[.//span[normalize-space()='{month}']]")


def gender_option(gender: str) -> Locator:
    return xpath(f"{_GENDER_CONTAINER}//li[.//span[normalize-space()='{gender}']]")


def _dismiss_modal(browser: Browser, _credentials: Credentials) -> None:
    browser.click(CONSENT_MODAL)
    browser.wait_for(css("form"), timeout=15)


def _choose(
    browser: Browser,
    trigger: Locator,
    options: Locator,
    option: Locator,
) -> None:
    """Open one custom select, choose an option, then make sure the list is closed.

    Interia re-renders these selects while they animate and can leave two option
    lists open at once. Scoping every locator to its own select and closing the
    list after the choice prevents strict-mode violations and click interception.
    """
    for attempt in range(2):
        try:
            browser.click(trigger, timeout=5)
            browser.wait_for(options, timeout=5)
            browser.click(option, timeout=5)
        except StepTimeoutError:
            if attempt == 1:
                raise
            time.sleep(0.4)
        else:
            break
    try:
        browser.wait_for(options, timeout=3, state="hidden")
    except StepTimeoutError:
        browser.click(trigger, timeout=3)
        browser.wait_for(options, timeout=3, state="hidden")


def _fill_identity(browser: Browser, credentials: Credentials) -> None:
    browser.fill(FIRST_NAME, credentials.first_name)
    browser.fill(LAST_NAME, credentials.last_name)
    browser.fill(DAY, str(credentials.day))
    _choose(
        browser,
        MONTH_SELECT,
        MONTH_OPTIONS,
        month_option(MONTHS[credentials.month - 1]),
    )
    browser.fill(YEAR, str(credentials.year))
    _choose(browser, GENDER_SELECT, GENDER_OPTIONS, gender_option(credentials.gender))


def _fill_username(browser: Browser, credentials: Credentials) -> None:
    browser.fill(USERNAME, credentials.username)


def _fill_passwords(browser: Browser, credentials: Credentials) -> None:
    browser.fill(PASSWORD, credentials.password)
    browser.fill(PASSWORD_REPEAT, credentials.password)


def _accept_consents(browser: Browser, _credentials: Credentials, consents: str) -> None:
    if consents == "all":
        browser.click(CONSENT_ALL_LABEL)
        return
    browser.click(CONSENT_EXPAND)
    browser.click(CONSENT_TERMS_LABEL)
    if not browser.is_checked(CONSENT_TERMS_INPUT):
        msg = "the required Regulamin checkbox did not get checked"
        raise FlowAbortError(msg, ExitCode.PROVIDER_CHANGED, "provider-changed")


def _submit(browser: Browser, _credentials: Credentials) -> None:
    browser.click(SUBMIT)


def _success(browser: Browser) -> bool:
    url = browser.url()
    if "poczta.interia.pl" in url and "/logowanie" not in url:
        return True
    return browser.has(LOGGED_IN)


def build(consents: str = "required") -> ProviderSpec:
    """Build the Interia spec for one consent strategy."""
    if consents not in {"required", "all"}:
        msg = "consents must be 'required' or 'all'"
        raise ValueError(msg)
    return ProviderSpec(
        name="interia",
        display="Interia",
        url=SIGNUP_URL,
        email_domain=EMAIL_DOMAIN,
        steps=(
            Step("dismiss-consent", _dismiss_modal),
            Step("fill-identity", _fill_identity),
            Step("fill-username", _fill_username),
            Step("fill-passwords", _fill_passwords),
            Step("accept-consents", partial(_accept_consents, consents=consents)),
            Step("create-account", _submit, StepKind.SUBMIT),
        ),
        success=_success,
        success_description="webmail shell reached",
        challenges=INTERIA_CHALLENGES,
        password_rules=PasswordRules(min_length=12, max_length=64),
        faker_locale="pl_PL",
        locale="pl-PL",
        needs_attestation=False,
        plans=("free",),
        domains=(EMAIL_DOMAIN,),
    )


CONTRACTS: tuple[Contract, ...] = (
    Contract(
        "form",
        Path("docs/recon/interia-step-3.html"),
        (DAY, YEAR, PASSWORD, PASSWORD_REPEAT, SUBMIT, CONSENT_TERMS_INPUT),
    ),
    Contract(
        "consent-modal",
        Path("docs/recon/interia-step-2.html"),
        (CONSENT_MODAL,),
    ),
)
