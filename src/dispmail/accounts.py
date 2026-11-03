"""SQLite account store and recovery-kit files.

Everything lives under one gitignored data directory::

    data/sqlite.db
    data/recovery_<email>_<platform>.txt

The database is created with mode 0600 and the directory with 0700.
"""

import os
import re
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    recovery TEXT,
    platform TEXT NOT NULL,
    recovery_file TEXT,
    created_at TEXT NOT NULL,
    egress TEXT,
    persona TEXT
);
CREATE INDEX IF NOT EXISTS idx_accounts_platform ON accounts(platform);
CREATE INDEX IF NOT EXISTS idx_accounts_created ON accounts(created_at);
"""

_FILENAME_UNSAFE = re.compile(r"[^A-Za-z0-9@._-]+")


class AccountExistsError(Exception):
    """The same address is already in the database."""


@dataclass(frozen=True, slots=True)
class Account:
    """A created mailbox before it is persisted."""

    email: str
    password: str = field(repr=False)
    recovery: str | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class StoredAccount:
    """One row of the database, as returned by a read."""

    id: int
    email: str
    platform: str
    recovery_file: str | None
    created_at: str
    egress: str | None
    persona: str | None
    password: str = field(repr=False)
    recovery: str | None = field(default=None, repr=False)

    def recovery_path(self, data_dir: Path) -> Path | None:
        if self.recovery_file is None:
            return None
        return data_dir / self.recovery_file


def email_slug(email: str) -> str:
    """Make an address safe for a file name without changing its meaning."""
    return _FILENAME_UNSAFE.sub("_", email)


def _regexp(pattern: str, value: str | None) -> bool:
    if value is None:
        return False
    try:
        return re.search(pattern, value) is not None
    except re.error:
        return False


def _to_stored(row: sqlite3.Row) -> StoredAccount:
    return StoredAccount(
        id=int(row["id"]),
        email=str(row["email"]),
        password=str(row["password"]),
        recovery=row["recovery"],
        platform=str(row["platform"]),
        recovery_file=row["recovery_file"],
        created_at=str(row["created_at"]),
        egress=row["egress"],
        persona=row["persona"],
    )


class AccountRepository:
    """Create, write and query the account database."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "sqlite.db"

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection]:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.chmod(0o700)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.create_function("REGEXP", 2, _regexp)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(SCHEMA)
            self.db_path.chmod(0o600)
            yield connection
            connection.commit()
        finally:
            connection.close()

    def add(
        self,
        account: Account,
        *,
        platform: str,
        egress: str | None = None,
        persona: str | None = None,
        recovery_extension: str = "txt",
    ) -> StoredAccount:
        now = datetime.now(UTC).isoformat(timespec="seconds")
        with self._connect() as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO accounts (email, password, recovery, platform, created_at,"
                    " egress, persona) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        account.email,
                        account.password,
                        account.recovery,
                        platform,
                        now,
                        egress,
                        persona,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                msg = f"{account.email} is already recorded in {self.db_path}"
                raise AccountExistsError(msg) from exc
            row_id = cursor.lastrowid
            recovery_file = None
            if account.recovery:
                path = self._write_recovery(account, platform, recovery_extension)
                recovery_file = path.name
                connection.execute(
                    "UPDATE accounts SET recovery_file = ? WHERE id = ?",
                    (recovery_file, row_id),
                )
            row = connection.execute("SELECT * FROM accounts WHERE id = ?", (row_id,)).fetchone()
        if row is None:
            msg = "the inserted account disappeared"
            raise RuntimeError(msg)
        return _to_stored(row)

    def _write_recovery(self, account: Account, platform: str, extension: str) -> Path:
        if account.recovery is None:
            msg = "cannot write a recovery file without recovery text"
            raise ValueError(msg)
        safe_extension = re.sub(r"[^a-z0-9]", "", extension.lower()) or "txt"
        safe_platform = email_slug(platform)
        name = f"recovery_{email_slug(account.email)}_{safe_platform}.{safe_extension}"
        path = self.data_dir / name
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(account.recovery)
            handle.write("\n")
        return path

    def find(
        self,
        *,
        platform: str | None = None,
        email: str | None = None,
        email_regex: str | None = None,
        recovery: str | None = None,
        since: str | None = None,
        limit: int | None = None,
    ) -> list[StoredAccount]:
        clauses: list[str] = []
        parameters: list[object] = []
        if platform:
            clauses.append("platform = ?")
            parameters.append(platform)
        if email:
            clauses.append("email = ?")
            parameters.append(email)
        if email_regex:
            re.compile(email_regex)
            clauses.append("email REGEXP ?")
            parameters.append(email_regex)
        if recovery in {"any", "yes"}:
            clauses.append("recovery IS NOT NULL AND recovery != ''")
        elif recovery == "no":
            clauses.append("(recovery IS NULL OR recovery = '')")
        if since:
            clauses.append("created_at >= ?")
            parameters.append(since)
        query = "SELECT * FROM accounts"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id DESC"
        if limit is not None:
            if limit < 1:
                msg = "limit must be at least 1"
                raise ValueError(msg)
            query += " LIMIT ?"
            parameters.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [_to_stored(row) for row in rows]

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM accounts").fetchone()
        return int(row["total"]) if row is not None else 0
