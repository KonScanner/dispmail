"""Runtime settings, egress description and persona derivation."""

import os
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from random import Random

from dotenv import load_dotenv


class ExitCode(IntEnum):
    """Process exit codes, documented in docs/plan-egress-fingerprint.md."""

    OK = 0
    FLOW_ERROR = 1
    USAGE = 2
    EGRESS_MISMATCH = 3
    CHALLENGE = 4
    BUDGET = 5
    PROVIDER_CHANGED = 6
    REJECTED = 7
    EXISTS = 8


_TRUTHY = frozenset({"1", "true", "yes", "on"})
_FALSY = frozenset({"0", "false", "no", "off"})


def env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    value = raw.strip().lower()
    if value in _TRUTHY:
        return True
    if value in _FALSY:
        return False
    msg = f"{name} must be a boolean, got {raw!r}"
    raise ValueError(msg)


def env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:
        msg = f"{name} must be a number, got {raw!r}"
        raise ValueError(msg) from exc


def default_state_dir() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "dispmail"


@dataclass(frozen=True, slots=True)
class EgressSpec:
    """The route a run must leave through, and what we expect to see from it."""

    name: str = "direct"
    expect_country: str = "GR"
    expect_asn: int | None = None
    proxy_server: str | None = None
    proxy_username: str | None = None
    proxy_password: str | None = field(default=None, repr=False)

    @property
    def is_proxy(self) -> bool:
        return self.proxy_server is not None

    def proxy_settings(self) -> dict[str, str] | None:
        """Playwright ``proxy`` context option, or ``None`` for a direct route."""
        if not self.is_proxy:
            return None
        if self.proxy_server is None:
            msg = "proxy_server is unset"
            raise ValueError(msg)
        settings = {"server": self.proxy_server}
        if self.proxy_username:
            settings["username"] = self.proxy_username
        if self.proxy_password:
            settings["password"] = self.proxy_password
        return settings

    @classmethod
    def from_env(cls) -> EgressSpec:
        asn_raw = os.environ.get("DISPMAIL_EGRESS_ASN", "").strip()
        return cls(
            name=os.environ.get("DISPMAIL_EGRESS_NAME", "direct"),
            expect_country=os.environ.get("DISPMAIL_EGRESS_COUNTRY", "GR").upper(),
            expect_asn=int(asn_raw) if asn_raw else None,
            proxy_server=os.environ.get("DISPMAIL_PROXY_SERVER") or None,
            proxy_username=os.environ.get("DISPMAIL_PROXY_USERNAME") or None,
            proxy_password=os.environ.get("DISPMAIL_PROXY_PASSWORD") or None,
        )


@dataclass(frozen=True, slots=True)
class Persona:
    """Values that must agree with the exit IP's country."""

    locale: str
    timezone: str
    accept_language: str
    viewport: tuple[int, int]


_COUNTRY_PROFILES: dict[str, tuple[str, str]] = {
    "GR": ("el-GR", "Europe/Athens"),
    "PL": ("pl-PL", "Europe/Warsaw"),
    "DE": ("de-DE", "Europe/Berlin"),
    "GB": ("en-GB", "Europe/London"),
    "US": ("en-US", "America/New_York"),
    "NL": ("nl-NL", "Europe/Amsterdam"),
    "SE": ("sv-SE", "Europe/Stockholm"),
}

_VIEWPORTS: tuple[tuple[int, int], ...] = ((1366, 768), (1536, 864), (1920, 1080))


def accept_language_for(locale: str) -> str:
    """Build a plausible Accept-Language header for a locale."""
    language = locale.split("-", maxsplit=1)[0]
    return f"{locale},{language};q=0.9,en-US;q=0.7"


def persona_for(country: str, rng: Random) -> Persona:
    """Build a coherent persona for an egress country (minimal-spoofing policy)."""
    locale, timezone = _COUNTRY_PROFILES.get(country.upper(), ("en-US", "UTC"))
    return Persona(
        locale=locale,
        timezone=timezone,
        accept_language=accept_language_for(locale),
        viewport=rng.choice(_VIEWPORTS),
    )


@dataclass(frozen=True, slots=True)
class Settings:
    """Everything a run needs; built from the environment once, then immutable."""

    headless: bool = True
    timeout: float = 10.0
    navigation_timeout: float = 30.0
    submit_timeout: float = 60.0
    assist_timeout: float = 600.0
    recovery_timeout: float = 20.0
    manual: bool = False
    submit: bool = False
    assisted: bool = False
    accept_attestation: bool = False
    replace_account: bool = False
    seed: int | None = None
    home_ip: str | None = None
    state_dir: Path = field(default_factory=default_state_dir)
    data_dir: Path = field(default_factory=lambda: Path.cwd() / "data")
    artifacts_dir: Path = field(default_factory=lambda: Path.cwd() / "artifacts")
    egress: EgressSpec = field(default_factory=EgressSpec)

    @property
    def ledger_path(self) -> Path:
        return self.state_dir / "ledger.jsonl"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "sqlite.db"

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv(override=False)
        state_dir = Path(os.environ.get("DISPMAIL_STATE_DIR", default_state_dir()))
        return cls(
            headless=env_bool("DISPMAIL_HEADLESS", default=True),
            timeout=env_float("DISPMAIL_TIMEOUT", 10.0),
            navigation_timeout=env_float("DISPMAIL_NAVIGATION_TIMEOUT", 30.0),
            submit_timeout=env_float("DISPMAIL_SUBMIT_TIMEOUT", 60.0),
            assist_timeout=env_float("DISPMAIL_ASSIST_TIMEOUT", 600.0),
            recovery_timeout=env_float("DISPMAIL_RECOVERY_TIMEOUT", 20.0),
            manual=env_bool("DISPMAIL_MANUAL", default=False),
            submit=env_bool("DISPMAIL_SUBMIT", default=False),
            assisted=env_bool("DISPMAIL_ASSISTED", default=False),
            accept_attestation=env_bool("DISPMAIL_ACCEPT_ATTESTATION", default=False),
            replace_account=env_bool("DISPMAIL_REPLACE_ACCOUNT", default=False),
            seed=int(os.environ["DISPMAIL_SEED"]) if os.environ.get("DISPMAIL_SEED") else None,
            home_ip=os.environ.get("DISPMAIL_HOME_IP") or None,
            state_dir=state_dir,
            data_dir=Path(os.environ.get("DISPMAIL_DATA_DIR", Path.cwd() / "data")),
            artifacts_dir=Path(os.environ.get("DISPMAIL_ARTIFACTS_DIR", Path.cwd() / "artifacts")),
            egress=EgressSpec.from_env(),
        )
