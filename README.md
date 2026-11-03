# DispMail

Create one disposable mailbox without giving personal data to the provider. DispMail
drives the system Chrome through a provider signup flow, stops before the submit
button by default, and stores the result locally.

The project was rebuilt against the live sites on 2026-11-03. The recon evidence,
selectors and blockers are in [`docs/recon/`](docs/recon/summary.md). The design and
test plans are in [`docs/`](docs/index.md).

## Status

| Provider | Plan | State |
|----------|------|-------|
| Tuta | Free | Dry run verified against the live site. A live run needs a clean egress. |
| Interia | Darmowe | Fill flow verified to the submit gate. This IP was challenged after repeated attempts. Live is assisted: it ends in an image CAPTCHA and SMS/mail verification. |

Both providers permit one free account per person. The ledger and the database enforce
one created account per provider.

## Requirements

- Python 3.14.8 or newer (`.python-version`)
- `uv`
- Google Chrome (patchright uses the system browser)
- Linux or macOS (the run lock uses `fcntl`)

## Install

```bash
uv sync --all-groups
uv run dispmail doctor
```

## Use

```bash
# Dry run: fill the form, stop before submit, create nothing.
uv run dispmail tuta --state-dir ./.dispmail-state

# Live Tuta: one free account, unattended.
uv run dispmail tuta --submit --accept-attestation \
  --state-dir ./.dispmail-state --headed

# Live Interia: solve the CAPTCHA and the SMS/mail step in the window.
uv run dispmail interia --submit --assisted --headed --state-dir ./.dispmail-state

uv run dispmail list      # providers, plans, live requirements
uv run dispmail doctor    # Python, patchright, Chrome, paths, egress
```

`uv run dispmail <provider> --help` lists `--domain`, `--consents`, `--timeout`,
`--assist-timeout`, `--seed`, `--json`, `--egress-*`, `--proxy-*` and `--home-ip`.

## Account data

All account data is under one gitignored `data/` directory:

```
data/sqlite.db                          email, password, recovery, platform, egress
data/recovery_<email>_<platform>.txt    recovery kit, as given by the provider
```

`data/` is mode 0700, the database and the recovery files are 0600. Set another
location with `DISPMAIL_DATA_DIR` or `--data-dir`.

Read the data with `dispmail read` or the make targets. Passwords and recovery keys
are masked unless `--show-passwords` is given.

```bash
uv run dispmail read
uv run dispmail read --platform tuta
uv run dispmail read --recovery yes
uv run dispmail read --email-regex '^alpha' --json
uv run dispmail read --show-passwords

make read-tuta
make read-interia
make read-recovery
make read-email RE='@tutamail.com$'
make read-json
make read-secrets
```

## Egress

A run refuses to open a provider page for writing unless the browser exit matches the
declared egress. The check runs inside the browser, uses two endpoints, and fails
closed on a country/ASN mismatch, on divergent endpoints, or when the exit is
`DISPMAIL_HOME_IP`.

Two modes:

1. System VPN or phone hotspot. No secrets in this repository.
   ```bash
   mullvad relay set location pl && mullvad connect
   uv run dispmail tuta --egress-country PL ...
   ```
2. HTTP/SOCKS proxy, configured only in `.env` (copy `.env.example`).

Exit codes: 0 ok, 1 flow error, 2 usage, 3 egress mismatch, 4 challenge, 5 budget or
cooldown or lock, 6 provider changed, 7 rejected, 8 account already recorded.

## Safety rules

- One account per provider per person. The database and the ledger both enforce it;
  `--replace-account` is the only override.
- One run at a time. A challenge sets a 24 hour cooldown, then 7 days.
- CAPTCHAs are never solved automatically. A headed assisted run waits for a human; a
  headless run stops with exit code 4.
- Passwords never enter logs or the ledger. Artifacts are a screenshot and a DOM with
  `value=` attributes blanked, textareas emptied, and the run secrets redacted.
- `--json` masks the password and the recovery key unless `--show-passwords` is given.

## Development

```bash
make check     # ruff format --check, ruff check, ty check, pytest
uvx prek install
```

Layout: `src/dispmail/` (engine, browser port, providers), `tests/unit/`,
`tests/contract/` (locator checks against the recon snapshots), `docs/`.

There is no CI. Rings 2 and 3 need a specific egress and, for Interia, a human.

## Legacy

`index.html`, `js/` and `css/` are an old static viewer. They read `accounts.txt`,
which the SQLite store no longer writes. They are not part of the CLI.
