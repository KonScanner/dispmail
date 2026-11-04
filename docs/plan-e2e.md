---
layout: default
title: End-to-end plan
parent: Design
nav_order: 1
description: "Test rings, seams, acceptance criteria."
---

# Plan: end-to-end testing

Status: **partly adopted.** Ring 1, the offline tests, is in `tests/`. Rings 2 and 3 need a controlled egress and, for Interia, a human at the CAPTCHA.

## 1. What "working end to end" will mean

A run is e2e-verified when, on a clean machine with Chrome installed:

```
uv sync --all-groups
uv run dispmail doctor          # ring 0
uv run pytest                   # ring 1, offline, no secrets
DISPMAIL_LIVE=1 uv run pytest -m live   # ring 2, real pages, no submit
uv run dispmail tuta --submit --accept-attestation   # ring 3, one real account
```

and every ring is green, with the artifacts showing what the browser saw.

## 2. Rings

| Ring | Command | Network | Browser | Secrets | Runs in CI |
|------|---------|---------|---------|---------|------------|
| 0 doctor | `dispmail doctor` | optional (egress probe) | no | no | no |
| 1 offline | `uv run pytest` | no | only for contract tests | no | **yes** |
| 2 live dry-run | `DISPMAIL_LIVE=1 pytest -m live` | yes | headed recommended | egress config | no |
| 3 live signup | `dispmail <provider> --submit` | yes | headed | egress + attestation | **never** |

Ring 1 is the fast feedback loop: it must stay deterministic and finish in seconds.

## 3. Test seams (design for testability first)

| Seam | Purpose | Test double |
|------|---------|-------------|
| `Browser` protocol (`open`, `fill`, `click`, `wait_for`, `content`, `screenshot`, `close`) | isolates patchright | `FakeBrowser` records a call log; `ScriptedBrowser` replays a DOM script |
| `EgressProbe` protocol (`check(context) -> EgressFacts`) | isolates the network probe | `FakeProbe` returns facts or raises |
| `Clock` protocol (`sleep`, `now`) | makes pacing deterministic | `FakeClock` |
| `ManualConfirm` protocol (`confirm(step) -> bool`) | replaces `input()` | `ScriptedConfirm` |
| `AccountStore` path | avoids writing the real account file | `tmp_path` |
| `Ledger` state dir | avoids mutating real budget | `tmp_path` |

The Selenium/patchright adapter is the only module omitted from coverage
(`src/dispmail/_selenium_browser.py` in `[tool.coverage.run].omit`); every other
module is unit-tested through these seams.

## 4. Ring 1 test inventory

### Unit (no browser, no network)

- `test_credentials.py` — username sanitisation (diacritics, apostrophes, hyphens,
  length, uniqueness), password rules per provider, birthday bounds, name splitting
  (mononym, two-part, three-part).
- `test_accounts.py` — append format `email:password[:recovery]`, `0600`, newline
  handling, custom path honoured, no duplicate append on failure.
- `test_ledger.py` — cap enforcement (one lifetime account per provider), concurrency
  lock, cooldown escalation after a challenge, corrupt-ledger handling, `--replace-account`.
- `test_egress.py` — verdict rules (country mismatch, ASN mismatch, home IP, probe
  failure), direct vs proxy option building, no submit on mismatch.
- `test_persona.py` — locale/timezone table per country, viewport matrix, no spoofed UA.
- `test_flows.py` — dry-run stops before the submit step; live runs it; failure
  taxonomy and exit codes; artifacts saved on failure; challenge → handoff in headed,
  abort in headless; resume reuses the same identity.
- `test_cli.py` — argument parsing, `list`, `doctor` output, exit codes, `--json`.
- `test_challenges.py` — signature matching for Turnstile/reCAPTCHA/Cloudflare and
  the false-positive guard (a normal page with the word "captcha" in a script tag is
  not a challenge).

### Contract (offline browser, snapshot-based)

For each provider, load the saved HTML from `tests/fixtures/snapshots/<provider>/`
into a real headless Chrome with `page.set_content(...)` and assert:

- every `Locator` in the provider spec resolves to exactly one visible element;
- required controls are enabled/disabled as the flow expects (e.g. Tuta "Create
  account" disabled before consents);
- the submit button exists and is reachable;
- challenge signatures are absent from the snapshot (so the fixture is a clean page).

This is the test that fails first when a provider redesigns its page, and it needs
no network. Snapshots are refreshed only by the recon script, never edited by hand.

## 5. Ring 2 (live dry-run)

`tests/e2e/test_dry_run.py`, marked `@pytest.mark.live`, skipped unless
`DISPMAIL_LIVE=1`:

- parametrised over providers and the in-scope domains;
- runs the real flow with `submit=False`, stopping at the submit step;
- asserts: pre-flight egress facts match the declared expectation; cookie CMP
  dismissed; every field filled; submit enabled; no challenge markers; run time
  under the budget;
- writes a trace and screenshots to `artifacts/<ts>-<provider>/` (dry-run traces are
  allowed; see the artifact policy);
- never accepts a legal attestation silently in a test: the fake confirmation seam
  records it.

Promotion to ring 3: for Tuta, five consecutive clean ring-2 runs on the chosen
egress, then one live run. For **Interia, one ring-2 run per egress per day maximum**:
live testing showed that repeated runs from the same IP trigger an image reCAPTCHA
before submit, which both burns the egress and destroys the evidence. A challenge in
ring 2 stops the egress and starts the cooldown (24 h, then 7 days).

## 6. Ring 3 (live signup) — CLI, not CI

Not a pytest test by default; it is the product doing its job. A `-m live_submit`
test exists only for a human-run, explicitly gated check:

```
DISPMAIL_LIVE=1 DISPMAIL_E2E_SUBMIT=1 uv run pytest -m live_submit
```

It asserts: exit code 0, the account file has exactly one new line with the expected
domain, the recovery key is non-empty (Tuta), the ledger recorded `created`, and a
second run is refused by the budget.

Interia's ring 3 is **assisted by design**: the test pauses at the image CAPTCHA and
the mail/SMS code and waits for the operator, then asserts the same outcomes. It is
never run unattended.

## 7. Success detection

| Provider | Success evidence | Failure evidence |
|----------|------------------|------------------|
| Tuta | wizard step 3 active, recovery-kit text present, code matches `[A-Z0-9-]{8,}` | inline error under the username, disabled submit after fill, error toast |
| Interia | image-CAPTCHA step passed + mail/SMS code accepted + URL becomes `poczta.interia.pl/...` (webmail) | inline Polish validation message, reCAPTCHA/image CAPTCHA, CMP still open, SMS step not completed |

Success is always a positive check (URL or DOM marker), never "the button was
clicked". Both providers get a `success` locator pair plus a `challenge` signature
list in their `ProviderSpec`.

## 8. Timing policy

- No `time.sleep`. Every interaction uses Playwright auto-wait plus explicit
  `wait_for` with a locator and a timeout.
- Timeouts: element 10 s, navigation 30 s, submit-result 60 s, human challenge 180 s.
- Per-step wall-clock budget logged; total dry-run budget 90 s; a step over budget is
  a `FLOW_ERROR` with the trace attached, not a retry.
- Typing delay 40–120 ms/char and 0.8–2.5 s dwell between steps (disabled or fixed
  under `--seed` in tests).

## 9. Artifacts and failure triage

`artifacts/<timestamp>-<provider>/`:

- `trace.zip` — dry-run and tests only (contains typed text);
- `final.png`, `page.html` — live failures, DOM sanitised (`input[value]` blanked,
  password fields emptied);
- `events.jsonl` — step start/end, durations, exit code, challenge detection;
- `egress.json` — probe facts (IP, country, ASN), never credentials.

Triage order for a failure: `exit_code` → `events.jsonl` (which step) → `final.png` →
`page.html` (selector drift) → `trace.zip` if available.

## 10. Local gates (no CI)

There is deliberately no CI: rings 2–3 need a specific egress, a real Chrome profile
and (for Interia) a human. Ring 1 runs locally and in the prek hook:

```bash
make check     # ruff format --check, ruff check, ty check, pytest (ring 1)
uvx prek install
```

`uv.lock` is committed. The contract tests skip when Chrome is unavailable instead of
failing the offline suite.

## 11. Maintenance loop

When a provider changes:

1. re-run `scripts/recon.py <provider>` (moves the browser through the flow up to the
   submit step, saves HTML/PNG, writes no account);
2. update `tests/fixtures/snapshots/` and the locators in the provider spec;
3. ring 1 must pass before any live attempt;
4. ring 2 five times; then ring 3 once.

Selector rot is detected by ring 1 (snapshot) and ring 2 (live DOM), in that order,
which keeps the expensive live runs rare.

## 12. Acceptance criteria for "up to speed"

- `make check` clean (`ruff format --check`, `ruff check`, `ty check`, `pytest`).
- `uv run ruff check .` clean.
- `uv run ty check` clean.
- `uv run pytest` green with coverage ≥ 80 % (adapter pragma-excluded).
- Python requirement `>=3.14.8`, `.python-version` committed, `uv.lock` committed.
- `dispmail doctor` reports Chrome, patchright, state dir and egress configuration.
- Tuta ring 2 green 5× and one ring-3 account created, fully unattended.
- Interia ring 2 green and one ring-3 account created in assisted mode (human solves
  the image CAPTCHA and the SMS/mail code); if the operator has no phone, Interia is
  documented as dry-run-only rather than silently failed.
- `docs/` reflects the final selectors and the recovery-kit markup.
