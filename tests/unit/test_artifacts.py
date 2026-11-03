"""Artifacts: one frozen directory per run and no typed secrets on disk."""

from datetime import UTC, datetime

import dispmail.artifacts as artifacts_module
from dispmail.artifacts import Artifacts, sanitize_html
from tests.fakes import FakeBrowser


def test_sanitize_removes_values_textareas_and_exact_secrets() -> None:
    html = (
        '<input type="password" value="hunter22"><textarea>hunter22</textarea><p>echo hunter22</p>'
    )
    cleaned = sanitize_html(html, ("hunter22",))
    assert "hunter22" not in cleaned
    assert 'value=""' in cleaned
    assert "[redacted]" in cleaned


def test_sanitize_redacts_html_escaped_secrets() -> None:
    secret = "Abc1&defGH2ij"
    cleaned = sanitize_html(f"<p>Your password: {secret}</p>", (secret,))
    assert "Abc1&amp;defGH2ij" not in cleaned
    assert "Abc1&defGH2ij" not in cleaned


def test_directory_is_frozen_even_when_the_clock_moves(monkeypatch, tmp_path) -> None:
    moments = iter(
        [
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 2, tzinfo=UTC),
        ]
    )

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return next(moments)

    monkeypatch.setattr(artifacts_module, "datetime", Clock)
    artifacts = Artifacts(tmp_path, "tuta")
    assert artifacts.directory == artifacts.directory
    assert artifacts.directory.name.startswith("20260101T")


def test_capture_redacts_the_run_password(tmp_path) -> None:
    browser = FakeBrowser()
    browser.content_value = "<html><body>hunter22</body></html>"
    artifacts = Artifacts(tmp_path, "tuta", secrets=("hunter22",))
    artifacts.capture(browser, "shot")
    assert "hunter22" not in (artifacts.directory / "shot.html").read_text(encoding="utf-8")


def test_capture_creates_every_file_in_one_directory(tmp_path) -> None:
    browser = FakeBrowser()
    browser.content_value = "<html></html>"
    artifacts = Artifacts(tmp_path, "tuta")
    artifacts.write_event({"event": "start"})
    artifacts.capture(browser, "shot")
    assert (artifacts.directory / "events.jsonl").exists()
    assert (artifacts.directory / "shot.png").exists()
    assert (artifacts.directory / "shot.html").exists()
