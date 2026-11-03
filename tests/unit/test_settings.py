"""Settings, egress description and persona derivation."""

from pathlib import Path
from random import Random

import pytest

from dispmail.settings import EgressSpec, Settings, env_bool, persona_for


def test_persona_matches_country() -> None:
    persona = persona_for("pl", Random(1))
    assert persona.locale == "pl-PL"
    assert persona.timezone == "Europe/Warsaw"
    assert persona.accept_language.startswith("pl-PL,pl")


def test_unknown_country_falls_back_to_english() -> None:
    persona = persona_for("ZZ", Random(1))
    assert persona.locale == "en-US"
    assert persona.timezone == "UTC"


def test_viewport_is_from_the_common_matrix() -> None:
    persona = persona_for("GR", Random(1))
    assert persona.viewport in {(1366, 768), (1536, 864), (1920, 1080)}


def test_proxy_settings_include_credentials() -> None:
    egress = EgressSpec(
        name="proxy",
        expect_country="PL",
        proxy_server="http://127.0.0.1:8080",
        proxy_username="user",
        proxy_password="secret",
    )
    assert egress.is_proxy
    assert egress.proxy_settings() == {
        "server": "http://127.0.0.1:8080",
        "username": "user",
        "password": "secret",
    }


def test_proxy_password_is_not_in_repr() -> None:
    egress = EgressSpec(proxy_server="http://127.0.0.1:8080", proxy_password="topsecret")
    assert "topsecret" not in repr(egress)


def test_direct_egress_has_no_proxy_settings() -> None:
    assert EgressSpec().proxy_settings() is None


def test_env_bool_parsing(monkeypatch) -> None:
    monkeypatch.setenv("DISPMAIL_HEADLESS", "no")
    assert env_bool("DISPMAIL_HEADLESS", default=True) is False
    monkeypatch.setenv("DISPMAIL_HEADLESS", "1")
    assert env_bool("DISPMAIL_HEADLESS", default=False) is True
    monkeypatch.setenv("DISPMAIL_HEADLESS", "maybe")
    with pytest.raises(ValueError, match="boolean"):
        env_bool("DISPMAIL_HEADLESS", default=True)


def test_settings_from_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DISPMAIL_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("DISPMAIL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DISPMAIL_EGRESS_COUNTRY", "pl")
    monkeypatch.setenv("DISPMAIL_EGRESS_ASN", "64500")
    monkeypatch.setenv("DISPMAIL_HOME_IP", "203.0.113.9")
    monkeypatch.setenv("DISPMAIL_PROXY_SERVER", "http://127.0.0.1:8080")
    monkeypatch.setenv("DISPMAIL_PROXY_USERNAME", "user")
    monkeypatch.setenv("DISPMAIL_PROXY_PASSWORD", "secret")
    monkeypatch.delenv("DISPMAIL_SUBMIT", raising=False)
    settings = Settings.from_env()
    assert settings.state_dir == tmp_path / "state"
    assert settings.data_dir == tmp_path / "data"
    assert settings.egress.expect_country == "PL"
    assert settings.egress.expect_asn == 64500
    assert settings.home_ip == "203.0.113.9"
    assert settings.egress.proxy_settings() is not None
    assert settings.submit is False


def test_ledger_path_is_under_state_dir(tmp_path) -> None:
    settings = Settings(state_dir=tmp_path)
    assert settings.ledger_path == tmp_path / "ledger.jsonl"


def test_data_dir_defaults_to_cwd(monkeypatch) -> None:
    monkeypatch.delenv("DISPMAIL_DATA_DIR", raising=False)
    assert Settings.from_env().data_dir == Path.cwd() / "data"
    assert Settings.from_env().db_path == Path.cwd() / "data" / "sqlite.db"
