---
layout: default
title: Development
nav_order: 8
description: "Layout, checks and tests."
---

# Development

## Layout

```text
src/dispmail/
  cli.py           command line, flags and output
  flows.py         step runner, challenge handling, result recording
  browser.py       browser port and the egress probe
  providers/       one module per provider
  accounts.py      SQLite store and recovery files
  ledger.py        budget, cooldowns and the run lock
  credentials.py   generated identity and passwords
  artifacts.py     screenshots and sanitized HTML
  challenges.py    challenge signatures
tests/unit/        offline tests
tests/contract/    locator checks against the recon snapshots
docs/              this site and the recon evidence
```

## Checks

```bash
make check
```

That runs `ruff format --check`, `ruff check`, `ty check` and `pytest`. There is no CI: the
check runs locally, and a pre-commit hook runs it before each commit.

```bash
uvx prek install
```

## Tests

The unit tests run offline. They cover the credential generator, the ledger, the account
store, the artifact sanitizer, the challenge signatures, the CLI and the flow runner with a
fake browser.

The contract tests compare each provider's locators with the DOM snapshots in
`docs/recon/`. They fail when the selectors and the captured pages disagree.

```bash
uv run pytest
uv run pytest --cov        # coverage, 80 percent gate
```

## Add a provider

1. Write `src/dispmail/providers/<name>.py` with a `Step` list, a `ProviderSpec` and a
   builder.
2. Register the builder in `src/dispmail/providers/__init__.py`.
3. Capture the page DOM and add the locator contract in `tests/contract/`.
4. Run the dry path, then the assisted path.

Next: [Design documents]({{ site.baseurl }}{% link design.md %}).
