---
layout: default
title: Limits and exit codes
nav_order: 7
description: "Weekly caps, cooldowns, CAPTCHA policy and process exit codes."
---

# Limits and exit codes

DispMail enforces its own limits so that a mistake does not become a provider block.

## Weekly cap

Four accounts per provider in a rolling seven days. The database and the run ledger both
count, so deleting `data/sqlite.db` does not reset the budget.

- `--weekly-limit` and `DISPMAIL_WEEKLY_LIMIT` change the cap.
- `--replace-account` bypasses the cap once, for a lost account.

## Cooldowns

| Event | Cooldown |
|-------|----------|
| A CAPTCHA appears in a live run | 24 hours for that provider on that egress |
| A second challenge inside seven days | 7 days |
| The provider blocks the address | 7 days |

A challenge in a dry run records no cooldown. The cooldown key is `--egress-name`, not the
address, so two relays with one name share a cooldown. `--ignore-cooldown` starts a run
anyway.

## One run at a time

A run takes an exclusive lock on the state directory. A second run stops with exit code 5.

## CAPTCHAs

DispMail never solves a CAPTCHA.

- Headless: the run stops with exit code 4.
- Headed and `--assisted`: the run waits for you. The default wait is 1800 seconds
  (`--assist-timeout`).

## Artifacts

Each run writes a screenshot and the page HTML to `artifacts/`. Before writing, the HTML is
sanitized: textareas are emptied, `value` attributes are blanked, and every secret of the
run is replaced with `***`.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Flow error: a step did not complete |
| 2 | Usage error: bad arguments or a missing flag |
| 3 | Egress mismatch |
| 4 | CAPTCHA challenge |
| 5 | Budget: weekly cap, cooldown or lock |
| 6 | Provider changed: the page no longer matches |
| 7 | Rejected: the provider refused the account |
| 8 | The account already exists in the database |
| 9 | Blocked: the provider refused the address for a week |

Next: [Development]({{ site.baseurl }}{% link development.md %}).
