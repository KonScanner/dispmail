"""Credential generation: usernames, names, passwords and birthdays."""

from random import Random

import pytest

from dispmail.credentials import (
    PasswordRules,
    ascii_slug,
    generate,
    make_password,
    make_username,
    split_name,
    username_candidates,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Łukasz Żółć", "lukaszzolc"),
        ("Ana María", "anamaria"),
        ("O'Keefe-Smith", "okeefe-smith"),
        ("  --  ", "--"),
    ],
)
def test_ascii_slug(raw: str, expected: str) -> None:
    assert ascii_slug(raw) == expected


@pytest.mark.parametrize(
    ("full_name", "expected"),
    [
        ("Cher", ("Cher", "Doe")),
        ("Ada Lovelace", ("Ada", "Lovelace")),
        ("Mary Jane Watson", ("Mary", "Watson")),
        ("", ("Alex", "Doe")),
    ],
)
def test_split_name(full_name: str, expected: tuple[str, str]) -> None:
    assert split_name(full_name) == expected


def test_username_is_provider_safe() -> None:
    username = make_username("Łukasz", "Żółć", Random(1))
    assert 3 <= len(username) <= 24
    assert set(username) <= set("abcdefghijklmnopqrstuvwxyz0123456789._-")


def test_password_meets_rules() -> None:
    rules = PasswordRules(min_length=12, max_length=64)
    password = make_password(rules)
    assert 12 <= len(password) <= 64
    assert any(char.isupper() for char in password)
    assert any(char.islower() for char in password)
    assert any(char.isdigit() for char in password)
    assert any(char in "!#$%&*@" for char in password)


def test_password_respects_short_maximum() -> None:
    password = make_password(PasswordRules(min_length=8, max_length=10))
    assert len(password) == 10


def test_generate_is_reproducible_for_identity_fields() -> None:
    first = generate(rng=Random(42))
    second = generate(rng=Random(42))
    assert (first.first_name, first.last_name, first.username) == (
        second.first_name,
        second.last_name,
        second.username,
    )
    assert first.password != second.password
    assert first.username != first.password
    assert 1 <= first.day <= 28
    assert 1 <= first.month <= 12
    assert 1950 <= first.year <= 2002


def test_generate_uses_provider_locale() -> None:
    credentials = generate(faker_locale="pl_PL", rng=Random(4))
    assert credentials.first_name
    assert credentials.last_name


def test_impossible_password_rules_are_rejected() -> None:
    with pytest.raises(ValueError, match="max_length"):
        make_password(PasswordRules(min_length=2, max_length=3))


def test_username_candidates_vary_and_escalate() -> None:
    candidates = list(username_candidates("Rachel", "Bauer", Random(3)))
    assert candidates[0] in {
        "rachelbauer",
        "rachel.bauer",
        "rachel_bauer",
        "r.bauer",
        "rachel.b",
        "rbauer",
    }
    assert any(candidate.isalpha() for candidate in candidates)
    assert any("." in candidate or "_" in candidate for candidate in candidates)
    numbered = [c for c in candidates if any(ch.isdigit() for ch in c)]
    assert numbered
    first_number = numbered[0]
    assert len(first_number) <= len("rachelbauer") + 1
    assert all(set(c) <= set("abcdefghijklmnopqrstuvwxyz0123456789._-") for c in candidates)


def test_generate_carries_alternatives() -> None:
    credentials = generate(rng=Random(5))
    assert credentials.alternatives
    assert credentials.username not in credentials.alternatives
