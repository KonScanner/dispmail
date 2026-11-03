"""SQLite store: schema, permissions, recovery files and read filters."""

import re
import stat

import pytest

from dispmail.accounts import Account, AccountExistsError, AccountRepository, email_slug


@pytest.fixture
def repository(tmp_path) -> AccountRepository:
    return AccountRepository(tmp_path / "data")


def test_add_creates_row_and_recovery_file(repository) -> None:
    stored = repository.add(
        Account("user@tutamail.com", "secret", "ABCD-EFGH-IJKL"),
        platform="tuta",
        egress="test:GR",
        persona="en-US/Europe/Athens",
    )
    assert stored.email == "user@tutamail.com"
    assert stored.recovery == "ABCD-EFGH-IJKL"
    assert stored.recovery_file == "recovery_user@tutamail.com_tuta.txt"
    path = stored.recovery_path(repository.data_dir)
    assert path is not None
    assert path.read_text(encoding="utf-8") == "ABCD-EFGH-IJKL\n"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_database_and_directory_permissions(repository) -> None:
    repository.add(Account("user@tuta.com", "secret"), platform="tuta")
    assert stat.S_IMODE(repository.db_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(repository.data_dir.stat().st_mode) == 0o700


def test_duplicate_email_is_rejected(repository) -> None:
    repository.add(Account("one@tuta.com", "a"), platform="tuta")
    with pytest.raises(AccountExistsError):
        repository.add(Account("one@tuta.com", "b"), platform="tuta")


def test_no_recovery_means_no_file(repository) -> None:
    stored = repository.add(Account("user@interia.pl", "secret"), platform="interia")
    assert stored.recovery is None
    assert stored.recovery_file is None
    assert list((repository.data_dir).glob("recovery_*")) == []


def test_find_filters(repository) -> None:
    repository.add(Account("alpha@tuta.com", "a", "KIT"), platform="tuta")
    repository.add(Account("beta@interia.pl", "b"), platform="interia")
    assert [row.email for row in repository.find(platform="tuta")] == ["alpha@tuta.com"]
    assert [row.email for row in repository.find(email_regex=r"^beta@")] == ["beta@interia.pl"]
    assert [row.email for row in repository.find(recovery="yes")] == ["alpha@tuta.com"]
    assert [row.email for row in repository.find(recovery="no")] == ["beta@interia.pl"]
    assert repository.find(email="missing@tuta.com") == []
    assert len(repository.find(limit=1)) == 1


def test_since_filter(repository) -> None:
    repository.add(Account("alpha@tuta.com", "a"), platform="tuta")
    assert repository.find(since="2000-01-01T00:00:00+00:00")
    assert repository.find(since="2999-01-01T00:00:00+00:00") == []


def test_invalid_regex_raises(repository) -> None:
    with pytest.raises(re.error):
        repository.find(email_regex="(")


def test_invalid_limit_raises(repository) -> None:
    with pytest.raises(ValueError, match="limit"):
        repository.find(limit=0)


def test_email_slug() -> None:
    assert email_slug("user@tutamail.com") == "user@tutamail.com"
    assert email_slug("bad/../name@x.com") == "bad_.._name@x.com"


def test_recovery_extension_is_sanitised(repository) -> None:
    stored = repository.add(
        Account("user@tuta.com", "secret", "KIT"),
        platform="tuta",
        recovery_extension="../pdf",
    )
    assert stored.recovery_file == "recovery_user@tuta.com_tuta.pdf"
