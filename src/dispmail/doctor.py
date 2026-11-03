"""Readiness checks: Python, patchright, Chrome, paths and egress configuration."""

import shutil
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from dispmail.settings import ExitCode, Settings


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    ok: bool
    detail: str


REQUIRED_PYTHON = (3, 14, 8)


def run_checks(settings: Settings) -> list[Check]:
    """Return every check, in a stable order, without touching the network."""
    return [
        _python_check(),
        _dependency_check(),
        _chrome_check(),
        _writable("state-dir", settings.state_dir),
        _writable("data-dir", settings.data_dir),
        _egress_check(settings),
    ]


def exit_code_for(checks: list[Check]) -> ExitCode:
    return ExitCode.OK if all(check.ok for check in checks) else ExitCode.FLOW_ERROR


def _python_check() -> Check:
    current = sys.version_info[:3]
    ok = current >= REQUIRED_PYTHON
    return Check(
        "python",
        ok,
        f"{current[0]}.{current[1]}.{current[2]} (need >= 3.14.8)",
    )


def _dependency_check() -> Check:
    try:
        version = metadata.version("patchright")
    except metadata.PackageNotFoundError:
        return Check("patchright", False, "not installed; run `uv sync --all-groups`")
    return Check("patchright", True, version)


def _chrome_check() -> Check:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return Check("chrome", True, path)
    return Check("chrome", False, "no Chrome/Chromium on PATH")


def _writable(name: str, directory: Path) -> Check:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".dispmail-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return Check(name, False, str(exc))
    return Check(name, True, str(directory))


def _egress_check(settings: Settings) -> Check:
    egress = settings.egress
    if not egress.expect_country:
        return Check("egress", False, "DISPMAIL_EGRESS_COUNTRY is empty")
    kind = "proxy" if egress.is_proxy else "direct"
    detail = f"{egress.name} ({kind}), expect {egress.expect_country}"
    if egress.expect_asn is not None:
        detail += f" AS{egress.expect_asn}"
    return Check("egress", True, detail)
