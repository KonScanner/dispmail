"""CLI surface: listing, doctor, usage gates and a scripted dry run."""

import json

import pytest

from dispmail import cli
from dispmail.accounts import Account, AccountRepository
from dispmail.providers import tuta
from tests.fakes import FakeBrowser, FakeProbe


def test_list_prints_providers(capsys) -> None:
    assert cli.main(["list"]) == 0
    output = capsys.readouterr().out
    assert "tuta" in output
    assert "interia" in output
    assert "assisted" in output


def test_doctor_json(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("DISPMAIL_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("DISPMAIL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DISPMAIL_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    code = cli.main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)
    names = {check["name"] for check in payload}
    assert {"python", "patchright", "chrome", "egress"} <= names
    assert code in {0, 1}


def test_tuta_submit_requires_attestation() -> None:
    assert cli.main(["tuta", "--submit"]) == 2


def test_interia_submit_requires_assisted() -> None:
    assert cli.main(["interia", "--submit"]) == 2


def test_dry_run_json(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("DISPMAIL_USERNAME_TIMEOUT", "0.1")
    monkeypatch.setattr(cli, "open_browser", lambda _settings, _persona, **_kwargs: FakeBrowser())
    monkeypatch.setattr(cli, "HttpEgressProbe", FakeProbe)
    code = cli.main(
        [
            "tuta",
            "--json",
            "--state-dir",
            str(tmp_path / "state"),
            "--data-dir",
            str(tmp_path / "data"),
            "--artifacts-dir",
            str(tmp_path / "artifacts"),
            "--egress-country",
            "GR",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["outcome"] == "dry-run"
    assert payload["ok"] is True


def test_unknown_provider_exits_with_usage() -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["nope"])
    assert excinfo.value.code == 2


def _seed(tmp_path, capsys) -> None:
    repository = AccountRepository(tmp_path / "data")
    repository.add(Account("alpha@tuta.com", "secret-a", "KIT"), platform="tuta")
    repository.add(Account("beta@interia.pl", "secret-b"), platform="interia")
    capsys.readouterr()


def test_read_masks_passwords(tmp_path, capsys) -> None:
    _seed(tmp_path, capsys)
    assert cli.main(["read", "--data-dir", str(tmp_path / "data")]) == 0
    output = capsys.readouterr().out
    assert "alpha@tuta.com" in output
    assert "secret-a" not in output
    assert "********" in output


def test_read_show_passwords(tmp_path, capsys) -> None:
    _seed(tmp_path, capsys)
    assert cli.main(["read", "--show-passwords", "--data-dir", str(tmp_path / "data")]) == 0
    assert "secret-a" in capsys.readouterr().out


def test_read_json_filters(tmp_path, capsys) -> None:
    _seed(tmp_path, capsys)
    code = cli.main(
        [
            "read",
            "--json",
            "--email-regex",
            "^beta@",
            "--data-dir",
            str(tmp_path / "data"),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert [row["email"] for row in payload] == ["beta@interia.pl"]
    assert payload[0]["password"] == "********"


def test_read_invalid_regex_is_usage(tmp_path, capsys) -> None:
    code = cli.main(["read", "--email-regex", "(", "--data-dir", str(tmp_path / "data")])
    assert code == 2
    assert "invalid --email-regex" in capsys.readouterr().err


def test_read_empty(tmp_path, capsys) -> None:
    assert cli.main(["read", "--data-dir", str(tmp_path / "data")]) == 0
    assert "no accounts" in capsys.readouterr().out


def _live_browser() -> FakeBrowser:
    browser = FakeBrowser()
    browser.url_after_click[tuta.CREATE.selector] = "https://app.tuta.com/mail"
    browser.texts["xpath=//body"] = (
        "fa54 7805 6b94 bfca 4d3c 56dd 14f7 6b84 a4b2 d777 c443 fdde 18d7 6017 5b70 0c74"
    )
    return browser


def _run_args(tmp_path, *extra: str) -> list[str]:
    return [
        "tuta",
        "--submit",
        "--accept-attestation",
        "--json",
        "--state-dir",
        str(tmp_path / "state"),
        "--data-dir",
        str(tmp_path / "data"),
        "--artifacts-dir",
        str(tmp_path / "artifacts"),
        "--egress-country",
        "GR",
        *extra,
    ]


def test_run_json_masks_secrets(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("DISPMAIL_RECOVERY_TIMEOUT", "0.2")
    monkeypatch.setenv("DISPMAIL_USERNAME_TIMEOUT", "0.1")
    monkeypatch.setattr(cli, "open_browser", lambda _settings, _persona, **_kwargs: _live_browser())
    monkeypatch.setattr(cli, "HttpEgressProbe", FakeProbe)
    code = cli.main(_run_args(tmp_path))
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["account"]["password"] == "********"
    assert payload["account"]["recovery"] == "********"


def test_run_json_show_passwords(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("DISPMAIL_RECOVERY_TIMEOUT", "0.2")
    monkeypatch.setenv("DISPMAIL_USERNAME_TIMEOUT", "0.1")
    monkeypatch.setattr(cli, "open_browser", lambda _settings, _persona, **_kwargs: _live_browser())
    monkeypatch.setattr(cli, "HttpEgressProbe", FakeProbe)
    code = cli.main([*_run_args(tmp_path), "--show-passwords"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["account"]["password"] != "********"
    assert payload["account"]["recovery"] == (
        "fa54 7805 6b94 bfca 4d3c 56dd 14f7 6b84 a4b2 d777 c443 fdde 18d7 6017 5b70 0c74"
    )


def test_assisted_requires_headed() -> None:
    assert cli.main(["interia", "--assisted"]) == 2


def test_invalid_domain_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["tuta", "--domain", "evil.example"])
    assert excinfo.value.code == 2


def test_read_limit_zero_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["read", "--limit", "0"])
    assert excinfo.value.code == 2


def test_read_json_masks_the_recovery_key(tmp_path, capsys) -> None:
    repository = AccountRepository(tmp_path / "data")
    repository.add(Account("alpha@tuta.com", "pw", "KIT"), platform="tuta")
    capsys.readouterr()
    assert cli.main(["read", "--json", "--data-dir", str(tmp_path / "data")]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["recovery"] == "********"
    assert (
        cli.main(["read", "--json", "--show-passwords", "--data-dir", str(tmp_path / "data")]) == 0
    )
    assert json.loads(capsys.readouterr().out)[0]["recovery"] == "KIT"


def test_seed_from_env_is_preserved(monkeypatch) -> None:
    monkeypatch.setenv("DISPMAIL_SEED", "42")
    args = cli.build_parser().parse_args(["tuta"])
    settings = cli._settings_from_args(args)
    assert settings.seed == 42
