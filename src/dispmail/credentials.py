"""Credential generation that respects each provider's rules."""

import secrets
import string
import unicodedata
from dataclasses import dataclass, field
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


def make_username(first: str, last: str, rng: Random) -> str:
    """Build a provider-safe local part from a name."""
    suffix = str(rng.randint(1000, 999_999))
    base = (ascii_slug(first) + ascii_slug(last))[: _USERNAME_MAX - len(suffix)] or "user"
    username = base + suffix
    while len(username) < _USERNAME_MIN:
        username += str(rng.randint(0, 9))
    return username


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
    return Credentials(
        first_name=first,
        last_name=last,
        username=make_username(first, last, rng),
        password=make_password(rules),
        day=day,
        month=month,
        year=year,
        gender=rng.choice(("Pan", "Pani")),
    )
