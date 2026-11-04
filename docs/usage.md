---
layout: default
title: Usage
nav_order: 3
description: "Dry runs, live runs, assisted runs and the command reference."
---

# Usage

Every provider runs the same way: fill the form, then decide whether to create the account.

## Dry run

A dry run fills the form, captures a screenshot and stops at the submit button. No account
is created and nothing is stored.

```bash
uv run dispmail tuta --state-dir ./.dispmail-state
```

Read the captured page in `artifacts/` to see where the run stopped.

## Live Tuta

Tuta needs `--accept-attestation`. The flag records that you hold no other free Tuta
account.

```bash
uv run dispmail tuta --submit --accept-attestation \
  --state-dir ./.dispmail-state --headed
```

The recovery kit is read from the page after the account exists and written to
`data/recovery_<email>_tuta.txt`.

## Live Interia

Interia ends in an image CAPTCHA and an SMS or mail verification step. A live run is
assisted: DispMail waits for you in the browser window and continues when you have cleared
the step.

```bash
uv run dispmail interia --submit --assisted --headed --state-dir ./.dispmail-state
```

`--assisted` requires `--headed`. A headless run stops with exit code 4 at a challenge.

## Command reference

| Command | Effect |
|---------|--------|
| `dispmail list` | Providers, plans, domains and live requirements. |
| `dispmail doctor` | Environment and egress check. |
| `dispmail read` | Query the account database. |
| `dispmail tuta` | Run the Tuta path. |
| `dispmail interia` | Run the Interia path. |

## Run flags

| Flag | Effect |
|------|--------|
| `--submit` | Create the account. Without it the run stops at the button. |
| `--headed` | Show the browser window. Dry runs are headless by default. |
| `--assisted` | Wait while you clear a CAPTCHA or a verification code. |
| `--accept-attestation` | Confirm that you hold no other free account at this provider. |
| `--manual` | Ask in the terminal before the account is recorded. |
| `--replace-account` | Ignore the weekly limit. Use it when an old account is gone. |
| `--ignore-cooldown` | Start the run even if this egress is cooling down. |
| `--domain` | Tuta address domain. Default `tutamail.com`. |
| `--consents` | Interia consents. `required` or `all`. Default `required`. |
| `--seed` | Seed for the generated identity. |
| `--timeout` | Step timeout in seconds. |
| `--assist-timeout` | How long an assisted run waits for you. Default 1800. |
| `--username-timeout` | How long Tuta may try alternative addresses. |
| `--weekly-limit` | Accounts per provider per seven days. Default 4. |
| `--json` | Machine-readable result. Secrets are masked. |
| `--show-passwords` | Include the password and recovery key in `--json`. |

`--data-dir`, `--artifacts-dir`, `--state-dir`, `--egress-*` and `--proxy-*` are accepted
by every run command. The [egress page]({{ site.baseurl }}{% link egress.md %}) explains the network flags.

## Read the result

```bash
uv run dispmail read
uv run dispmail read --platform tuta --json
```

The [account data page]({{ site.baseurl }}{% link data.md %}) lists the filters and the make targets.

Next: [Providers]({{ site.baseurl }}{% link providers.md %}).
