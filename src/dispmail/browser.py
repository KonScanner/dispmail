"""Browser abstraction over patchright, plus the egress probe."""

import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, cast, runtime_checkable

from patchright.sync_api import (
    Browser as PatchrightBrowserType,
)
from patchright.sync_api import (
    BrowserContext,
    Page,
    Playwright,
    ProxySettings,
    sync_playwright,
)
from patchright.sync_api import Locator as PatchrightLocator
from patchright.sync_api import (
    TimeoutError as PatchrightTimeoutError,
)

from dispmail.settings import EgressSpec, Persona, Settings, accept_language_for

logger = logging.getLogger(__name__)


WaitState = Literal["attached", "detached", "hidden", "visible"]


class BrowserError(Exception):
    """Base class for browser failures."""


class StepTimeoutError(BrowserError):
    """A locator did not become ready; usually means the page changed."""


class EgressMismatchError(BrowserError):
    """The run would not leave through the configured egress."""


@dataclass(frozen=True, slots=True)
class Locator:
    """A Playwright selector plus a human description for logs and plans."""

    selector: str
    description: str = ""

    def __str__(self) -> str:
        return self.description or self.selector


def css(selector: str) -> Locator:
    return Locator(selector)


def xpath(expression: str) -> Locator:
    return Locator(f"xpath={expression}")


def text(needle: str) -> Locator:
    return Locator(f"text={needle}")


@runtime_checkable
class Browser(Protocol):  # pragma: no cover - interface only
    """The narrow surface the flows are allowed to use."""

    def goto(self, url: str) -> None: ...

    def wait_for(
        self, locator: Locator, *, timeout: float | None = None, state: WaitState = "visible"
    ) -> None: ...

    def click(self, locator: Locator, *, timeout: float | None = None) -> None: ...

    def fill(self, locator: Locator, value: str, *, timeout: float | None = None) -> None: ...

    def is_checked(self, locator: Locator) -> bool: ...

    def is_enabled(self, locator: Locator) -> bool: ...

    def wait_enabled(self, locator: Locator, *, timeout: float = 5.0) -> None: ...

    def text_of(self, locator: Locator) -> str: ...

    def has(self, locator: Locator, *, timeout: float = 0.0) -> bool: ...

    def count(self, locator: Locator) -> int: ...

    def content(self) -> str: ...

    def url(self) -> str: ...

    def title(self) -> str: ...

    def screenshot(self, path: Path) -> None: ...

    def close(self) -> None: ...


class PatchrightBrowser:  # pragma: no cover - adapter, exercised by live runs
    """Concrete adapter around patchright (excluded from coverage)."""

    def __init__(
        self,
        page: Page,
        context: BrowserContext,
        browser: PatchrightBrowserType,
        playwright: Playwright,
    ) -> None:
        self._page = page
        self._context = context
        self._browser = browser
        self._playwright = playwright

    def _locator(self, locator: Locator) -> PatchrightLocator:
        return self._page.locator(locator.selector)

    @staticmethod
    def _millis(timeout: float | None) -> float | None:
        return None if timeout is None else timeout * 1000

    def goto(self, url: str) -> None:
        try:
            self._page.goto(url, wait_until="domcontentloaded")
        except PatchrightTimeoutError as exc:
            msg = f"navigation to {url} timed out"
            raise StepTimeoutError(msg) from exc

    def wait_for(
        self, locator: Locator, *, timeout: float | None = None, state: WaitState = "visible"
    ) -> None:
        try:
            self._locator(locator).wait_for(state=state, timeout=self._millis(timeout))
        except PatchrightTimeoutError as exc:
            msg = f"timed out waiting for {locator}"
            raise StepTimeoutError(msg) from exc

    def click(self, locator: Locator, *, timeout: float | None = None) -> None:
        try:
            self._locator(locator).click(timeout=self._millis(timeout))
        except PatchrightTimeoutError as exc:
            msg = f"timed out clicking {locator}"
            raise StepTimeoutError(msg) from exc

    def fill(self, locator: Locator, value: str, *, timeout: float | None = None) -> None:
        try:
            self._locator(locator).fill(value, timeout=self._millis(timeout))
        except PatchrightTimeoutError as exc:
            msg = f"timed out filling {locator}"
            raise StepTimeoutError(msg) from exc

    def is_checked(self, locator: Locator) -> bool:
        return bool(self._locator(locator).is_checked())

    def is_enabled(self, locator: Locator) -> bool:
        return bool(self._locator(locator).is_enabled())

    def wait_enabled(self, locator: Locator, *, timeout: float = 5.0) -> None:  # pragma: no cover
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._locator(locator).is_enabled():
                return
            time.sleep(0.1)
        msg = f"timed out waiting for {locator} to become enabled"
        raise StepTimeoutError(msg)

    def text_of(self, locator: Locator) -> str:
        try:
            return str(self._locator(locator).inner_text(timeout=self._millis(None)))
        except PatchrightTimeoutError as exc:
            msg = f"timed out reading {locator}"
            raise StepTimeoutError(msg) from exc

    def has(self, locator: Locator, *, timeout: float = 0.0) -> bool:
        if timeout > 0:
            try:
                self._locator(locator).wait_for(state="attached", timeout=self._millis(timeout))
            except PatchrightTimeoutError:
                return False
        return self._locator(locator).count() > 0

    def count(self, locator: Locator) -> int:
        return int(self._locator(locator).count())

    def content(self) -> str:
        return str(self._page.content())

    def url(self) -> str:
        return str(self._page.url)

    def title(self) -> str:
        return str(self._page.title())

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._page.screenshot(path=str(path), full_page=True)

    def close(self) -> None:
        self._context.close()
        self._browser.close()
        self._playwright.stop()


def open_browser(  # pragma: no cover
    settings: Settings,
    persona: Persona,
    *,
    locale: str | None = None,
) -> Browser:
    """Launch Chrome through patchright with a coherent, per-run context."""
    playwright = sync_playwright().start()
    arguments: list[str] = []
    if not settings.headless and os.environ.get("WAYLAND_DISPLAY"):
        arguments.append("--ozone-platform=wayland")
    browser = playwright.chromium.launch(
        headless=settings.headless,
        channel="chrome",
        args=arguments,
    )
    resolved_locale = locale or persona.locale
    accept_language = (
        persona.accept_language if locale is None else accept_language_for(resolved_locale)
    )
    context = browser.new_context(
        locale=resolved_locale,
        timezone_id=persona.timezone,
        viewport={"width": persona.viewport[0], "height": persona.viewport[1]},
        proxy=cast("ProxySettings", settings.egress.proxy_settings()),
    )
    context.set_extra_http_headers({"Accept-Language": accept_language})
    context.set_default_timeout(settings.timeout * 1000)
    context.set_default_navigation_timeout(settings.navigation_timeout * 1000)
    page = context.new_page()
    return PatchrightBrowser(page, context, browser, playwright)


@dataclass(frozen=True, slots=True)
class EgressFacts:
    """What an external endpoint reports about the exit we actually use."""

    ip: str
    country: str
    asn: int | None
    org: str
    source: str


class PageSource(Protocol):
    """The two browser facts the egress probe needs."""

    def goto(self, url: str) -> None: ...

    def content(self) -> str: ...


class EgressProbe(Protocol):  # pragma: no cover - interface only
    def check(self, browser: Browser) -> EgressFacts: ...


_CF_TRACE = "https://www.cloudflare.com/cdn-cgi/trace"
_IPINFO = "https://ipinfo.io/json"


class HttpEgressProbe:
    """Ask two independent endpoints from inside the browser context."""

    def check(self, browser: PageSource) -> EgressFacts:
        cloudflare = self._cloudflare(browser)
        needs_asn = cloudflare is None or cloudflare.asn is None
        ipinfo = self._ipinfo(browser) if needs_asn else None
        if cloudflare is None and ipinfo is None:
            msg = "could not determine the exit IP from any endpoint"
            raise EgressMismatchError(msg)
        if cloudflare is None:
            if ipinfo is None:
                msg = "could not determine the exit IP from any endpoint"
                raise EgressMismatchError(msg)
            return ipinfo
        if ipinfo is None:
            return cloudflare
        if ipinfo.ip != cloudflare.ip or ipinfo.country.upper() != cloudflare.country.upper():
            msg = (
                "the two egress endpoints disagree: "
                f"cloudflare={cloudflare.ip}/{cloudflare.country}, "
                f"ipinfo={ipinfo.ip}/{ipinfo.country}"
            )
            raise EgressMismatchError(msg)
        return EgressFacts(
            ip=cloudflare.ip,
            country=cloudflare.country,
            asn=ipinfo.asn,
            org=ipinfo.org or cloudflare.org,
            source=f"{cloudflare.source}+{ipinfo.source}",
        )

    def _cloudflare(self, browser: PageSource) -> EgressFacts | None:
        try:
            browser.goto(_CF_TRACE)
            body = browser.content()
        except BrowserError:
            return None
        ip_match = re.search(r"ip=([0-9a-fA-F.:]+)", body)
        country_match = re.search(r"loc=([A-Z]{2})", body)
        if not ip_match or not country_match:
            return None
        return EgressFacts(
            ip=ip_match.group(1),
            country=country_match.group(1),
            asn=None,
            org="",
            source="cloudflare",
        )

    def _ipinfo(self, browser: PageSource) -> EgressFacts | None:
        try:
            browser.goto(_IPINFO)
            body = browser.content()
        except BrowserError:
            return None
        ip_match = re.search(r'"ip"\s*:\s*"([^"]+)"', body)
        country_match = re.search(r'"country"\s*:\s*"([A-Z]{2})"', body)
        org_match = re.search(r'"org"\s*:\s*"AS(\d+)\s+([^"]*)"', body)
        if not ip_match or not country_match:
            return None
        return EgressFacts(
            ip=ip_match.group(1),
            country=country_match.group(1),
            asn=int(org_match.group(1)) if org_match else None,
            org=org_match.group(2) if org_match else "",
            source="ipinfo",
        )


def verify_egress(
    egress: EgressSpec,
    facts: EgressFacts,
    *,
    home_ip: str | None = None,
) -> None:
    """Fail closed unless the observed exit matches the declared one."""
    if facts.country.upper() != egress.expect_country.upper():
        msg = (
            f"egress mismatch: expected country {egress.expect_country}, "
            f"observed {facts.country} ({facts.ip} via {facts.source})"
        )
        raise EgressMismatchError(msg)
    if egress.expect_asn is not None and facts.asn != egress.expect_asn:
        msg = (
            f"egress mismatch: expected AS{egress.expect_asn}, observed AS{facts.asn} ({facts.org})"
        )
        raise EgressMismatchError(msg)
    if home_ip is not None and facts.ip == home_ip:
        msg = "egress mismatch: traffic is still leaving through the home IP"
        raise EgressMismatchError(msg)
    logger.info("egress ok: %s %s %s", facts.ip, facts.country, facts.org)
