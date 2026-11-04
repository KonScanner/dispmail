---
layout: default
title: DispMail
nav_exclude: true
description: "Create one disposable mailbox without giving the provider your personal data."
---

# DispMail

Create one disposable mailbox without giving the provider your personal data.

DispMail opens a provider's sign-up page in the Chrome browser you already have, fills the
form with a generated name, birthday and password, and stops at the submit button. Add
`--submit` when you want it to finish the registration.

Everything happens on your computer. There is no server, no account and no telemetry.

<div class="ledger">
  <section>
    <h2>What it does</h2>
    <ul>
      <li>Fills a provider sign-up form with generated details.</li>
      <li>Stops before the account exists, unless you pass <code>--submit</code>.</li>
      <li>Records the address, the password and the recovery kit in a local SQLite file.</li>
      <li>Checks that the connection leaves through the egress you declared before it writes anything.</li>
    </ul>
  </section>
  <section>
    <h2>What it never does</h2>
    <ul>
      <li>Send your data to this project or to any third party.</li>
      <li>Hide your connection from the provider.</li>
      <li>Solve a CAPTCHA.</li>
      <li>Bypass a provider's limits or terms.</li>
    </ul>
  </section>
</div>

## Requirements

Python 3.14.8 or newer, `uv`, Google Chrome, and Linux or macOS.

## Start

```bash
git clone https://github.com/KonScanner/dispmail
cd dispmail
uv sync --all-groups
uv run dispmail doctor
```

Then read [Install]({{ site.baseurl }}{% link install.md %}) for the details, or go straight to
[Usage]({{ site.baseurl }}{% link usage.md %}).

## Before you run it

One free account per person is the rule at both providers. DispMail cannot check that you
follow it. It limits you to four accounts per provider in a rolling seven days and it
records your acceptance of the provider terms. The rest is your responsibility.

[Read the limits]({{ site.baseurl }}{% link limits.md %}) for the weekly cap, the cooldowns and the exit
codes.
