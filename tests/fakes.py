"""Test doubles for the browser, egress probe and confirmation seams."""

from dataclasses import replace
from pathlib import Path

from dispmail.browser import Browser, EgressFacts, Locator, StepTimeoutError
from dispmail.settings import EgressSpec, Settings


class FakeBrowser:
    """Records calls and lets each test choose what is visible/checked/enabled."""

    def __init__(self) -> None:
        self.actions: list[tuple[str, str]] = []
        self.url_value = ""
        self.title_value = ""
        self.content_value = ""
        self.content_sequence: list[str] = []
        self.texts: dict[str, str] = {}
        self.missing: set[str] = set()
        self.present: set[str] = set()
        self.content_sequence: list[str] = []
        self.unchecked: set[str] = set()
        self.disabled: set[str] = set()
        self.fail_on: dict[str, Exception] = {}
        self.url_after_click: dict[str, str] = {}
        self.present_after_click: dict[str, set[str]] = {}
        self.closed = False

    def _record(self, action: str, locator: Locator) -> None:
        self.actions.append((action, locator.selector))
        failure = self.fail_on.get(locator.selector)
        if failure is not None:
            raise failure

    def goto(self, url: str) -> None:
        self.actions.append(("goto", url))
        self.url_value = url

    def wait_for(self, locator: Locator, *, timeout=None, state: str = "visible") -> None:
        self._record("wait_for", locator)
        if locator.selector in self.missing:
            raise StepTimeoutError(f"missing {locator}")

    def click(self, locator: Locator, *, timeout=None) -> None:
        self._record("click", locator)
        if locator.selector in self.missing:
            raise StepTimeoutError(f"missing {locator}")
        if locator.selector in self.url_after_click:
            self.url_value = self.url_after_click[locator.selector]
        self.present.update(self.present_after_click.get(locator.selector, set()))

    def fill(self, locator: Locator, value: str, *, timeout=None) -> None:
        self._record("fill", locator)
        self.actions.append(("value", value))

    def is_checked(self, locator: Locator) -> bool:
        self.actions.append(("is_checked", locator.selector))
        return locator.selector not in self.unchecked

    def wait_enabled(self, locator: Locator, *, timeout: float = 5.0) -> None:
        self._record("wait_enabled", locator)
        if locator.selector in self.disabled:
            raise StepTimeoutError(f"{locator} never enabled")

    def is_enabled(self, locator: Locator) -> bool:
        self.actions.append(("is_enabled", locator.selector))
        return locator.selector not in self.disabled

    def text_of(self, locator: Locator) -> str:
        self._record("text_of", locator)
        return self.texts.get(locator.selector, "")

    def has(self, locator: Locator, *, timeout: float = 0.0) -> bool:
        self.actions.append(("has", locator.selector))
        return locator.selector in self.present and locator.selector not in self.missing

    def has_in_frame(
        self, frame_selector: str, inner_selector: str, *, timeout: float = 0.0
    ) -> bool:
        self.actions.append(("has_in_frame", f"{frame_selector}>>{inner_selector}"))
        return f"{frame_selector}>>{inner_selector}" in self.present

    def count(self, locator: Locator) -> int:
        return 1 if locator.selector in self.present else 0

    def content(self) -> str:
        if self.content_sequence:
            if len(self.content_sequence) > 1:
                return self.content_sequence.pop(0)
            return self.content_sequence[0]
        return self.content_value

    def url(self) -> str:
        return self.url_value

    def title(self) -> str:
        return self.title_value

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"png")

    def close(self) -> None:
        self.closed = True


class FakeProbe:
    def __init__(self, facts: EgressFacts | None = None, error: Exception | None = None) -> None:
        self.facts = facts or EgressFacts(
            ip="203.0.113.7", country="GR", asn=64500, org="Example", source="fake"
        )
        self.error = error
        self.calls = 0

    def check(self, browser: Browser) -> EgressFacts:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.facts


class ScriptedConfirmation:
    def __init__(self, answers: list[bool]) -> None:
        self.answers = answers
        self.prompts: list[str] = []

    def confirm(self, prompt: str) -> bool:
        self.prompts.append(prompt)
        return self.answers.pop(0)


def make_settings(tmp_path: Path, **overrides: object) -> Settings:
    base = Settings(
        state_dir=tmp_path / "state",
        data_dir=tmp_path / "data",
        recovery_timeout=0.2,
        artifacts_dir=tmp_path / "artifacts",
        egress=EgressSpec(name="test", expect_country="GR"),
    )
    return replace(base, **overrides)
