---
layout: default
title: Install
nav_order: 2
description: "Requirements, setup and the environment check."
---

# Install

DispMail is a Python program. It drives your own Chrome installation, so there is no
bundled browser to download.

## Requirements

| Requirement | Detail |
|-------------|--------|
| Python | 3.14.8 or newer. The version is pinned in `.python-version`. |
| `uv` | Used for the environment and for `uv run dispmail`. |
| Google Chrome | The browser must be installed. DispMail starts it with `--channel=chrome`. |
| System | Linux or macOS. The single-run lock uses `fcntl`. |

## Set up

```bash
git clone https://github.com/KonScanner/dispmail
cd dispmail
uv sync --all-groups
```

`--all-groups` also installs the lint and test groups. Only the `uv sync` install is needed
to run the tool.

## Check the environment

```bash
uv run dispmail doctor
```

The check reports the Python version, the patchright install, Chrome, the data and state
directories, and the egress configuration. Each line is marked `ok` or `FAIL`. Add `--json`
for machine-readable output.

```text
[ok  ] python       3.14.8
[ok  ] patchright   1.64.4
[ok  ] chrome       Google Chrome 136
[ok  ] data         /home/you/dispmail/data
[ok  ] state        /home/you/.local/share/dispmail
```

A failed check names the fix. `doctor` exits with code 1 when any check fails.

## Where files go

| Path | Content | Override |
|------|---------|----------|
| `data/` | Account database and recovery files | `--data-dir`, `DISPMAIL_DATA_DIR` |
| `artifacts/` | Screenshot and sanitized page HTML for each run | `--artifacts-dir`, `DISPMAIL_ARTIFACTS_DIR` |
| `~/.local/share/dispmail` | Run ledger and lock | `--state-dir`, `DISPMAIL_STATE_DIR` |

`data/` is created with mode 0700. Its files are 0600.

Next: [Usage]({% link usage.md %}).
