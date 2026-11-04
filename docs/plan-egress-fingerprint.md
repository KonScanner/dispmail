---
layout: default
title: Egress and fingerprint
parent: Design
nav_order: 2
description: "Egress check, persona, budgets, challenge policy."
---

# Plan: egress, fingerprint and challenge handling

Status: **implemented.** This document is the design record behind `browser.py`, `ledger.py` and `credentials.py`.

## 0. Decision log

| # | Question | Decision |
|---|----------|----------|
| 1 | Objective and volume | Single user, a few accounts/month. Protect the real (home) IP. |
| 2 | Observed signal | CAPTCHA / Turnstile / Cloudflare challenge after a few signups. |
| 3 | Egress | One **sticky** exit per run. Primary: phone hotspot (mobile CGNAT). Candidate: Mullvad PL exit. Fallback: metered sticky residential proxy. No free proxy lists, no Tor. |
| 4 | Automation engine | `patchright` (patched Playwright) with the system Chrome. `undetected-chromedriver` is stale (2024-02) and rejected. |
| 5 | Persona depth | Minimal and coherent. Do not spoof platform/UA; derive timezone, locale, `Accept-Language` and viewport from the egress. No canvas/WebGL/audio noise unless measured as necessary. |
| 6 | Egress verification | Mandatory in-browser pre-flight IP/ASN/country check. **Fail closed** before any submit. |
| 7 | Pacing and budget | Ledger + hard caps + concurrency lock + cooldown escalation. Cap revised by #13: **one lifetime account per provider per person**. |
| 8 | Challenge policy | Human handoff in the same session. Never automate a challenge. Unattended mode aborts with a distinct exit code. |
| 9 | Artifacts | Live: screenshot + sanitized DOM + JSONL events only. Dry-run/tests: full Playwright trace. |
| 10 | Test gating | Ring 1 (offline) in CI; ring 2 (live dry-run) opt-in by env; ring 3 (real signup) manual CLI only. |
| 11 | Rebuild order | Revised by #15: **Tuta first**, then Interia. |
| 12 | Promotion rule | 5 clean dry-runs at 0 challenges, then 1 live account. Any challenge stops that egress (7-day cooldown). |
| 13 | Account volume vs terms | Revised on 2026-11-04 at the user's request: **up to 4 accounts per provider in a rolling 7 days** (`DISPMAIL_WEEKLY_LIMIT`). Tuta still asks you to affirm one free account per person; the tool cannot verify the attestation and logs a warning when an account is already recorded. |
| 14 | Recon evidence | Tuta: no captcha, stable `data-testid`s, free plan is not the default. Interia: reCAPTCHA Enterprise (invisible, on submit) and randomised field names per load. |
| 15 | Order after recon | Tuta first (clean testids, no captcha), then Interia (label selectors + captcha handoff). |

## 1. Objective and non-goals

Objective: create a small number of disposable accounts without exposing the user's
home IP or a random-looking fingerprint, and do it in a way that can be tested.

Non-goals:

- bulk account farming, resale, multiple accounts on the same provider, or traffic that
  pretends to be many users;
- automated CAPTCHA/Turnstile solving (also against the providers' terms);
- proxy pools or per-request IP rotation. Per-request rotation is a *stronger* bot
  signal than a stable session and is explicitly out of scope.

Hard rules the code enforces:

1. No submit unless the pre-flight egress check matches the declared expectation.
2. No submit while the ledger says the provider/egress budget is exhausted.
3. No concurrent runs (single-process lock).
4. No attempt to interact with a challenge programmatically.

## 2. Threat model

The providers score, at minimum:

| Signal | What it sees | Our position |
|--------|--------------|--------------|
| IP reputation | ASN class (residential/mobile vs datacenter), prior abuse, geo | Sticky mobile/residential exit; one identity per run |
| TLS / HTTP2 fingerprint | Real Chrome only if we use a real Chrome | System Chrome via patchright; no HTTP client for provider traffic |
| JS fingerprint | `navigator.webdriver`, UA/UA-CH, WebGL, canvas, fonts, timezone vs geo | patchright hides automation; everything else stays real and coherent |
| Behaviour | Typing cadence, dwell, step order, burst rate | Typed input with jitter, deliberate dwell, hard rate caps |
| Account-level | Duplicate usernames, same recovery address, same egress across accounts | Random usernames, one account per provider per day, egress recorded per account |

The asymmetry to exploit is **consistency, not randomness**: every value we present
must agree with every other value and with the exit IP.

## 3. Architecture

```
src/dispmail/
  cli.py            argparse/typer-free CLI, exit codes, --json
  settings.py       frozen Settings, env/.env parsing, paths
  egress.py         EgressSpec (direct | proxy), expected country/ASN
  egress_probe.py   in-browser IP/ASN/country probe + verdict
  persona.py        coherent locale/timezone/viewport derived from egress
  browser.py        patchright lifecycle, context options, redaction helpers
  challenges.py     challenge signatures and detection
  ledger.py         JSONL attempts, budget caps, cooldowns, flock
  flows.py          Step/FlowRunner: dry-run stop, artifacts, failure taxonomy
  credentials.py    username/password/name/birthday generation + validation
  accounts.py       account file append (0600), format email:password[:recovery]
  providers/
    base.py         ProviderSpec: url, plans, steps, success, challenge markers
    interia.py
    tuta.py
  doctor.py         environment + egress + browser readiness report
```

### 3.1 Egress interface

```python
@dataclass(frozen=True)
class EgressSpec:
    name: str  # "hotspot", "mullvad-pl", "residential-eu"
    kind: Literal["direct", "proxy"]
    expect_country: str  # ISO-3166 alpha-2, e.g. "GR"
    expect_asn: int | None  # optional; None = any ASN that is not the home ASN
    proxy: ProxyConfig | None  # server, username, password, sticky session id


@dataclass(frozen=True)
class EgressFacts:
    ip: str
    country: str
    asn: int
    asn_org: str
    checked_via: str  # which endpoint answered
```

- `direct`: no Playwright proxy options; the route is the system WireGuard tunnel
  (Mullvad) or the tethered interface. We still verify in-browser.
- `proxy`: Playwright `proxy={"server", "username", "password"}` on the browser
  context; credentials come from `.env`, never from the repo.
- The probe runs **inside the browser context** (`page.goto` to the check endpoint),
  so it exercises the exact route the signup will use. Two endpoints are tried:
  `https://www.cloudflare.com/cdn-cgi/trace` (ip, loc) and `https://ipinfo.io/json`
  (asn, org). If both disagree, abort.

Verdict rule: `country == expect_country` and (`expect_asn is None or asn == expect_asn`)
and `ip` is not the known home IP (recorded once by `dispmail doctor`). Any mismatch
is exit code 3 and no provider page is opened for writing.

### 3.2 Persona

One `Persona` per run, built from the egress country:

| Field | Source |
|-------|--------|
| `locale` | egress country table: GR→`el-GR`, PL→`pl-PL`, else `en-US` |
| `timezone` | egress country table: GR→`Europe/Athens`, PL→`Europe/Warsaw` |
| `accept_language` | from locale |
| `viewport` | one of `(1366,768)`, `(1536,864)`, `(1920,1080)`; chosen per run |
| user agent / platform / WebGL | untouched real system Chrome |

`patchright` supplies the automation-hiding. We do not add a stealth extension, a
custom Chromium build, or canvas/audio noise. If the probe shows the persona is
still challenged, the next step is the egress, not more fingerprint noise.

Fresh ephemeral context per account; no cookie or storage reuse between accounts.
An interrupted run may resume the **same** account with the same persona and egress
via `--resume`, recorded in the ledger; it never resumes with a different identity.

### 3.3 Pacing and budget

State lives in `DISPMAIL_STATE_DIR` (default `~/.local/share/dispmail` on Linux;
a workspace `.dispmail-state/` in tests; gitignored).

- `ledger.jsonl`: one line per attempt
  `{ts, provider, egress, persona, account_hash, outcome, challenge, exit_code}`.
  No passwords; `account_hash` is a salted hash so the file is not a credential store.
- Caps: **4 created accounts per provider in a rolling 7 days** (the database and the
  ledger both count). `--weekly-limit` changes the number; `--replace-account` bypasses
  the limit for a lost account. The ledger also enforces max 1 run at a time (`flock`
  on `run.lock`).
- Cooldowns: a challenge sets a 24 h cooldown for `(provider, egress)`; a second
  challenge sets 7 days. A provider IP block sets a 7-day cooldown immediately.
- Human-ish input: per-character delay 40–120 ms, step dwell 0.8–2.5 s, one short
  scroll before submit. Deterministic under `--seed` for tests.

### 3.4 Challenges

Detection is a per-provider list of signatures (URL fragment, title, visible text,
selector) plus generic Cloudflare/Turnstile markers. On detection:

- headed run: log, screenshot, and wait for the human to solve it in the same
  window (timeout 180 s, Enter to continue), then resume the same step list;
- headless run: save artifacts, exit code 4 `CHALLENGE`, record in the ledger;
- never click, solve, or retry a challenge automatically.

### 3.5 Failure taxonomy and exit codes

| Code | Name | Meaning | Action |
|------|------|---------|--------|
| 0 | OK | created, or dry-run reached a ready submit button | account written (live) |
| 1 | FLOW_ERROR | unexpected exception | artifacts, no retry loop |
| 2 | USAGE | bad arguments/config | print help |
| 3 | EGRESS_MISMATCH | probe failed or route changed | abort, nothing submitted |
| 4 | CHALLENGE | challenge detected | human handoff (headed) or abort |
| 5 | BUDGET | cap/cooldown/lock | abort with the reason |
| 6 | PROVIDER_CHANGED | expected element missing after bounded waits, no challenge markers | save DOM, docs say: re-run recon |
| 7 | REJECTED | provider validation error after submit | record, print fields, no retry |
| 8 | EXISTS | all generated usernames taken | stop; a new run generates new candidates |
| 9 | BLOCKED | provider blocks the IP ("registration is temporarily blocked") | 7-day cooldown for that (provider, egress); stop |

`PROVIDER_CHANGED` vs `BLOCKED`: a navigation returning 403/429 or a provider error
page is reported as `EGRESS_MISMATCH`/`BLOCKED`; a timeout with a normal page means
the DOM changed.

### 3.6 Secrets and artifacts

- `.env` (gitignored) holds `DISPMAIL_PROXY_*`; `dispmail doctor` shows presence only.
- Passwords are never logged, never in traces, never in the ledger.
- Live artifacts: PNG screenshot, `page.content()` with every `input[value]` and
  password field blanked, JSONL step log. No video, no trace.
- Dry-run/test artifacts: Playwright trace and video are allowed.
- Account store: SQLite at `data/sqlite.db` (mode `0600`), one row per account with
  email, password, recovery text, platform, egress and persona. The recovery kit is
  also written verbatim to `data/recovery_<email>_<platform>.txt` (mode `0600`). The
  whole `data/` directory is gitignored. Reads go through `dispmail read`, which masks
  passwords unless `--show-passwords` is passed.

## 4. E2E rings (summary)

| Ring | Runs | Needs network | What it proves |
|------|------|---------------|----------------|
| 0 `dispmail doctor` | on demand | no | Python, Chrome, patchright, state dir, egress config present |
| 1 unit + DOM contract | every `pytest`, CI | no | logic, budgets, failure taxonomy; every locator resolves against saved snapshot |
| 2 live dry-run | `DISPMAIL_LIVE=1 pytest -m live` | yes | page loads, fields fill, submit becomes enabled, pre-flight egress check passes, 5× no challenge |
| 3 live signup | manual `dispmail <provider> --submit` | yes | a real account is created and recorded |

Promotion: ring 2 five times with zero challenges → one ring-3 run. Any challenge in
ring 2 or 3 stops that egress, sets the 7-day cooldown, and the next attempt uses a
different egress.

## 5. Risks and open questions

- **Mullvad ASN**: datacenter-class; may be challenged even from a Polish exit. The
  probe measures it; we do not assume it works.
- **Mobile hotspot logistics**: tethering on a laptop, one run per session, IP changes
  between runs are fine because identity is per run.
- **Interia geo**: the site is Polish; a non-PL exit may be challenged or restricted.
  Recon must confirm; if it is PL-only, the hotspot must roam or we use a PL proxy.
- **Captcha on submit only**: Interia's invisible reCAPTCHA Enterprise and any Turnstile
  appear on submit, so dry-run cannot see them. The promotion rule accepts this limit;
  the live run handles it with human handoff.
- **Interia randomised field names**: `name`/`id` change per page load for name, surname
  and username. Locators must use the visible labels, and unused extra fields
  (`infoInput`, `login-fake`, `password-fake`) must be left alone; a snapshot test is the
  only defence against label drift.
- **Tuta free-plan default**: the plan step defaults to Legend (paid). The flow must
  explicitly select the Free card before Continue, or it will try to start a paid signup.
- **patchright maintenance**: small project; pin the version in `uv.lock`, keep the
  `Browser` adapter narrow so `nodriver`/SeleniumBase can replace it.
- **Chrome version**: local Chrome 136 is old; `doctor` warns when older than stable
  by more than one major version, because an outdated browser is its own signal.
- **Terms of service**: single-user, low volume, human present when challenged. If a
  provider objects or blocks, stop rather than escalate.

## 6. Implementation order

1. `settings` + `egress` + `egress_probe` + `persona` + `ledger` + `flows` with unit
   tests and a fake browser. No site code yet.
2. Provider contract snapshots from `docs/recon/`, then Tuta dry-run (ring 2).
3. Tuta live (ring 3), then Interia dry-run and live.
4. CI for ring 1, docs, `doctor` polish.
