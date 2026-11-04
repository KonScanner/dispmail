"""Credential generation that respects each provider's rules."""

import secrets
import string
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, field
from itertools import islice
from random import Random

from faker import Faker

_SYMBOLS = "!#$%&*@"
_TRANSLITERATION = str.maketrans(
    {
        "ł": "l",
        "Ł": "L",
        "ø": "o",
        "Ø": "O",
        "đ": "d",
        "Đ": "D",
        "ß": "ss",
        "æ": "ae",
        "Æ": "AE",
    }
)
_USERNAME_ALLOWED = frozenset(string.ascii_lowercase + string.digits + "._-")
_USERNAME_MIN = 3
_USERNAME_MAX = 24


@dataclass(frozen=True, slots=True)
class PasswordRules:
    """Provider password policy, as displayed in the signup UI."""

    min_length: int = 12
    max_length: int = 64
    require_symbol: bool = True


@dataclass(frozen=True, slots=True)
class Credentials:
    """One identity, reused for every field of a signup."""

    first_name: str
    last_name: str
    username: str
    password: str = field(repr=False)
    day: int
    month: int
    year: int
    gender: str = "Pan"
    alternatives: tuple[str, ...] = ()


def ascii_slug(value: str) -> str:
    """Fold diacritics and keep only characters a mail provider accepts."""
    decomposed = unicodedata.normalize("NFKD", value.translate(_TRANSLITERATION))
    folded = "".join(char for char in decomposed if not unicodedata.combining(char))
    return "".join(char for char in folded.lower() if char in _USERNAME_ALLOWED)


def split_name(full_name: str) -> tuple[str, str]:
    """Split a Faker name into first/last, tolerating mononyms and 3+ parts."""
    parts = [part for part in full_name.replace("-", " ").split() if part]
    if not parts:
        return "Alex", "Doe"
    if len(parts) == 1:
        return parts[0], "Doe"
    return parts[0], parts[-1]


def _normalise_username(value: str) -> str:
    value = value.lower().strip("._-")
    while ".." in value:
        value = value.replace("..", ".")
    while "__" in value:
        value = value.replace("__", "_")
    while "--" in value:
        value = value.replace("--", "-")
    return value[:_USERNAME_MAX]


def username_candidates(first: str, last: str, rng: Random) -> Iterator[str]:
    """Yield memorable local parts: name first, then the same with escalating numbers."""
    first = ascii_slug(first) or "user"
    last = ascii_slug(last) or "name"
    bases = [
        first + last,
        f"{first}.{last}",
        f"{first}_{last}",
        f"{first[0]}.{last}",
        f"{first}.{last[0]}",
        f"{first[0]}{last}",
    ]
    rng.shuffle(bases)
    seen: set[str] = set()

    def remember(value: str) -> str | None:
        cleaned = _normalise_username(value)
        if len(cleaned) < _USERNAME_MIN or cleaned in seen:
            return None
        seen.add(cleaned)
        return cleaned

    for base in bases:
        cleaned = remember(base)
        if cleaned is not None:
            yield cleaned

    for digits in (1, 2, 3, 4, 6):
        low = 1 if digits == 1 else 10 ** (digits - 1)
        high = 9 if digits == 1 else 10**digits - 1
        for _ in range(3):
            number = str(rng.randint(low, high))
            base = rng.choice(bases)
            variant = rng.choice(
                (
                    base + number,
                    number + base,
                    first + number + last,
                    f"{first}.{number}.{last}",
                )
            )
            cleaned = remember(variant)
            if cleaned is not None:
                yield cleaned


def make_username(first: str, last: str, rng: Random) -> str:
    """The first, most memorable candidate."""
    return next(username_candidates(first, last, rng))


def make_password(rules: PasswordRules) -> str:
    """Generate a mixed-class password with the system CSPRNG."""
    if rules.max_length < 4:
        msg = "max_length must be at least 4 to hold one character of each class"
        raise ValueError(msg)
    length = min(max(rules.min_length, 16), rules.max_length)
    alphabet = string.ascii_letters + string.digits
    symbols = _SYMBOLS if rules.require_symbol else ""
    core = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
    ]
    if symbols:
        core.append(secrets.choice(symbols))
    pool = alphabet + symbols
    while len(core) < length:
        core.append(secrets.choice(pool))
    secrets.SystemRandom().shuffle(core)
    return "".join(core)


def make_birthday(rng: Random) -> tuple[int, int, int]:
    """Return a plausible adult birthday (day, month, year)."""
    return rng.randint(1, 28), rng.randint(1, 12), rng.randint(1950, 2002)


def generate(
    rules: PasswordRules | None = None,
    *,
    faker_locale: str = "en_US",
    rng: Random | None = None,
) -> Credentials:
    """Create one full identity for a signup flow."""
    rules = rules or PasswordRules()
    rng = rng or Random(secrets.randbits(64))
    faker = Faker(faker_locale)
    faker.seed_instance(rng.randint(0, 2**31 - 1))
    first, last = split_name(faker.name())
    day, month, year = make_birthday(rng)
    candidates = list(islice(username_candidates(first, last, rng), 10))
    return Credentials(
        first_name=first,
        last_name=last,
        username=candidates[0],
        password=make_password(rules),
        day=day,
        month=month,
        year=year,
        gender=rng.choice(("Pan", "Pani")),
        alternatives=tuple(candidates[1:]),
    )
