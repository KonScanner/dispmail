"""Run artifacts: screenshot, sanitised DOM and JSONL event log."""

import html as html_module
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from dispmail.browser import Browser

_VALUE_ATTRIBUTE = re.compile(r'(\svalue=")[^"]*(")')
_TEXTAREA = re.compile(r"(<textarea[^>]*>)(.*?)(</textarea>)", re.IGNORECASE | re.DOTALL)
_REDACTED = "[redacted]"


def sanitize_html(html: str, secrets: tuple[str, ...] = ()) -> str:
    """Remove typed secrets from a DOM snapshot.

    Chrome does not serialise input properties as attributes, but a page can echo
    the typed value into text or a textarea (the "reveal password" patterns), so
    both the exact secret strings and all textarea bodies are redacted.
    """
    for secret in secrets:
        if secret and len(secret) >= 6:
            html = html.replace(secret, _REDACTED)
            html = html.replace(html_module.escape(secret), _REDACTED)
    html = _TEXTAREA.sub(rf"\1{_REDACTED}\3", html)
    return _VALUE_ATTRIBUTE.sub(r"\1\2", html)


@dataclass
class Artifacts:
    """One directory per run, frozen at construction time."""

    root: Path
    label: str
    secrets: tuple[str, ...] = ()
    _directory: Path = field(init=False, repr=False)

    def __post_init__(self) -> None:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self._directory = self.root / f"{stamp}-{self.label}"

    @property
    def directory(self) -> Path:
        return self._directory

    def write_event(self, event: dict[str, object]) -> None:
        directory = self.directory
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "events.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def capture(self, browser: Browser, name: str, secrets: tuple[str, ...] = ()) -> Path:
        combined = self.secrets + tuple(item for item in secrets if item)
        directory = self.directory
        directory.mkdir(parents=True, exist_ok=True)
        browser.screenshot(directory / f"{name}.png")
        (directory / f"{name}.html").write_text(
            sanitize_html(browser.content(), combined), encoding="utf-8"
        )
        return directory
