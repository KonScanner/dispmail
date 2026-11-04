---
layout: default
title: Providers
nav_order: 4
description: "Tuta and Interia: state, requirements and provider terms."
---

# Providers

Two paths exist. Both are free plans. Neither provider is affiliated with this project.

| Provider | Plan | Sign-up page | Live run |
|----------|------|--------------|----------|
| Tuta | Free | `app.tuta.com/signup` | Unattended, with `--accept-attestation` |
| Interia | Darmowe | `poczta.interia.pl` | Assisted, with `--assisted --headed` |

## Tuta

- Default address domain: `tutamail.com`. Other free domains: `tuta.io`, `tutanota.com`,
  `tutanota.de`, `keemail.me`.
- `tuta.com` is a paid domain. A run stops with exit code 6 when the page offers only a paid
  plan.
- The recovery kit is a 64-character hexadecimal string in 16 groups of four. DispMail reads
  it from the page after the account exists and writes it to the `data/` directory.
- Tuta asks you to confirm that you hold no other free Tuta account. `--submit` requires
  `--accept-attestation` to record that confirmation.
- A new account can stay under review for about 48 hours before the first login works.
- A free account is deleted after six months without a login.

## Interia

- Polish provider. The interface is Polish; the run forces an English browser locale where
  the page allows it.
- The form has three required consents. `--consents all` also accepts the optional ones.
- After the submit step the page shows an image CAPTCHA and then an SMS or mail
  verification. A human clears both; DispMail waits in the browser window.
- A new account can show "Dostęp do konta jest ograniczony" when you sign in from a
  different network. Sign in from the network that created it.

## Provider terms

Both providers limit free accounts per person. DispMail cannot check that you comply. The
tool records the attestation you pass on the command line and enforces a local limit of four
accounts per provider per seven days. The rest is your responsibility.

Next: [Egress]({% link egress.md %}).
