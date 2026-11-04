---
layout: default
title: Account data
nav_order: 6
description: "Where accounts are stored, how they are protected, and how to read them."
---

# Account data

Accounts are stored only on your computer, in the directory given by `--data-dir`. The
default is `data/` inside the repository, which is excluded from version control.

## Files

| Path | Content |
|------|---------|
| `data/sqlite.db` | Account records, one row per created mailbox |
| `data/recovery_<email>_<platform>.txt` | Recovery kit as the provider gave it |
| `data/pending_<email>_<platform>.txt` | Temporary file, written at submit and removed when the account is stored |

`data/` is created with mode 0700. The database and the recovery files are 0600. Another
location is set with `--data-dir` or `DISPMAIL_DATA_DIR`.

## Columns

| Column | Content |
|--------|---------|
| `id` | Row identifier |
| `email` | Address, unique |
| `password` | Generated password |
| `recovery` | Recovery key, when the provider issues one |
| `platform` | `tuta` or `interia` |
| `recovery_file` | File name of the recovery kit |
| `created_at` | Creation time, UTC |
| `egress` | Egress name that created the account |
| `persona` | Locale and timezone used for the run |

## Read it

```bash
uv run dispmail read
```

Passwords and recovery keys are masked. The table is `platform`, `email`, `password`,
`recovery`, `created`.

| Filter | Effect |
|--------|--------|
| `--platform tuta` | One provider |
| `--email you@example.org` | One address |
| `--email-regex '^alpha'` | Regular expression over the address |
| `--recovery yes` | Rows that have a recovery key |
| `--since 2026-11-01T00:00:00+00:00` | Created after an ISO timestamp |
| `--limit 10` | Row limit |
| `--json` | JSON output |

`--show-passwords` prints the real password and recovery key. Use it in a terminal you
control.

## Make targets

| Target | Equivalent |
|--------|-----------|
| `make read` | `dispmail read` |
| `make read-tuta` | `dispmail read --platform tuta` |
| `make read-interia` | `dispmail read --platform interia` |
| `make read-recovery` | `dispmail read --recovery yes` |
| `make read-email RE='@tutamail.com$'` | `dispmail read --email-regex '...'` |
| `make read-json` | `dispmail read --json` |
| `make read-secrets` | `dispmail read --show-passwords` |

Every target passes `ARGS` through, for example `make read-tuta ARGS='--limit 5'`.

## Back up

A copy of `data/` is a copy of every password. Keep it on encrypted storage, or do not keep
it at all.

Next: [Limits and exit codes]({{ site.baseurl }}{% link limits.md %}).
