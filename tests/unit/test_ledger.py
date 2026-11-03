"""Ledger: one-lifetime cap, challenge cooldowns and the run lock."""

from datetime import UTC, datetime, timedelta

import pytest

from dispmail.ledger import (
    SECOND_CHALLENGE_COOLDOWN,
    BudgetError,
    Ledger,
    attempt,
    run_lock,
)


def _created(provider: str = "tuta") -> str:
    return str(attempt(provider, "test", "created", 0))


def test_record_and_read_roundtrip(tmp_path) -> None:
    ledger = Ledger(tmp_path)
    ledger.record(attempt("tuta", "test", "created", 0, account_hash="abc"))
    entries = ledger.read()
    assert len(entries) == 1
    assert entries[0].provider == "tuta"
    assert entries[0].account_hash == "abc"


def test_corrupt_lines_are_skipped(tmp_path) -> None:
    ledger = Ledger(tmp_path)
    ledger.record(attempt("tuta", "test", "started", 0))
    ledger.path.write_text(ledger.path.read_text() + "not json\n", encoding="utf-8")
    assert len(ledger.read()) == 1


def test_one_lifetime_account_per_provider(tmp_path) -> None:
    ledger = Ledger(tmp_path)
    ledger.record(attempt("tuta", "test", "created", 0))
    with pytest.raises(BudgetError, match="one account"):
        ledger.check("tuta", "test")
    ledger.check("tuta", "test", allow_replacement=True)
    ledger.check("interia", "test")


def test_cooldown_after_one_challenge(tmp_path) -> None:
    ledger = Ledger(tmp_path)
    ledger.record(attempt("tuta", "test", "challenge", 4, challenged=True))
    assert ledger.cooldown_until("tuta", "test") is not None
    with pytest.raises(BudgetError, match="cooling down"):
        ledger.check("tuta", "test")


def test_second_challenge_extends_cooldown(tmp_path) -> None:
    ledger = Ledger(tmp_path)
    ledger.record(attempt("tuta", "test", "challenge", 4, challenged=True))
    ledger.record(attempt("tuta", "test", "challenge", 4, challenged=True))
    until = ledger.cooldown_until("tuta", "test")
    assert until is not None
    assert until - datetime.now(UTC) > SECOND_CHALLENGE_COOLDOWN - timedelta(minutes=1)


def test_challenge_outside_window_is_forgotten(tmp_path) -> None:
    ledger = Ledger(tmp_path)
    old = (datetime.now(UTC) - timedelta(days=31)).isoformat(timespec="seconds")
    ledger.record(attempt("tuta", "test", "challenge", 4, challenged=True, ts=old))
    assert ledger.cooldown_until("tuta", "test") is None


def test_account_hash_is_salted_by_state_dir(tmp_path) -> None:
    first = Ledger(tmp_path / "a")
    second = Ledger(tmp_path / "b")
    assert first.account_hash("user@tuta.com") != second.account_hash("user@tuta.com")
    assert first.account_hash("user@tuta.com") == first.account_hash("user@tuta.com")


def test_lock_is_exclusive(tmp_path) -> None:
    with run_lock(tmp_path), pytest.raises(BudgetError, match="lock"), run_lock(tmp_path):
        pass


def test_naive_timestamp_is_treated_as_utc(tmp_path) -> None:
    ledger = Ledger(tmp_path)
    ledger.path.write_text(
        '{"ts": "2026-11-03T20:00:00", "provider": "tuta", "egress": "test",'
        ' "outcome": "challenge", "exit_code": 4, "challenged": true}\n',
        encoding="utf-8",
    )
    entries = ledger.read()
    assert len(entries) == 1
    assert entries[0].when.tzinfo is not None
    assert ledger.cooldown_until("tuta", "test") is not None


def test_unknown_keys_are_ignored(tmp_path) -> None:
    ledger = Ledger(tmp_path)
    ledger.path.write_text(
        '{"ts": "2026-11-03T20:00:00+00:00", "provider": "tuta", "egress": "test",'
        ' "outcome": "created", "exit_code": 0, "future_field": 1}\n',
        encoding="utf-8",
    )
    assert len(ledger.read()) == 1


def test_garbage_timestamp_is_skipped(tmp_path) -> None:
    ledger = Ledger(tmp_path)
    ledger.path.write_text(
        '{"ts": "not-a-date", "provider": "tuta", "egress": "test",'
        ' "outcome": "created", "exit_code": 0}\n',
        encoding="utf-8",
    )
    assert ledger.read() == []
