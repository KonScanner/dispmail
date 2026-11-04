---
layout: default
title: Egress
nav_order: 5
description: "Why a run checks its exit, and how to declare it."
---

# Egress

A mailbox account is tied to the network that created it. A provider that sees the same
address arrive from two unrelated networks can flag it. DispMail therefore refuses to write
to a provider page until it has confirmed where the browser is leaving from.

## The check

1. The browser opens two public address services and reads the country and the autonomous
   system number of the exit.
2. The values are compared with the egress you declared.
3. The run stops with exit code 3 when the country differs, when the ASN differs, when the
   two services disagree, or when the exit is your home address.

The check runs inside the browser, so it sees the same route the sign-up page will see. It
fails closed: an unreachable service is a mismatch, not a pass.

## Two ways to declare an egress

### System VPN or phone hotspot

```bash
mullvad relay set location pl && mullvad connect
uv run dispmail tuta --egress-country PL --egress-name pl-mullvad ...
```

No secret is stored in the repository. `--egress-name` is the key for the cooldown: two
different relays with the same name share a cooldown.

### HTTP or SOCKS proxy

Configure it in `.env`, copied from `.env.example`:

```text
DISPMAIL_PROXY_SERVER=socks5://127.0.0.1:1080
DISPMAIL_PROXY_USERNAME=user
DISPMAIL_PROXY_PASSWORD=your-proxy-password
```

The same values are accepted as `--proxy-server`, `--proxy-username` and `--proxy-password`.
Prefer the environment variable for the password: a command line is visible to other local
processes.

## The persona

The browser presents a locale, timezone and viewport that match the declared country. A
Belgian exit gets a Belgian clock, not a UTC window. Tuta is served in English in every
case.

## Flags and variables

| Flag | Variable | Meaning |
|------|----------|---------|
| `--egress-name` | `DISPMAIL_EGRESS_NAME` | Cooldown key for this route |
| `--egress-country` | `DISPMAIL_EGRESS_COUNTRY` | Expected ISO country |
| `--egress-asn` | `DISPMAIL_EGRESS_ASN` | Expected autonomous system number |
| `--home-ip` | `DISPMAIL_HOME_IP` | An exit that must never be used |
| `--proxy-server` | `DISPMAIL_PROXY_SERVER` | Proxy URL |
| `--proxy-username` | `DISPMAIL_PROXY_USERNAME` | Proxy user |
| `--proxy-password` | `DISPMAIL_PROXY_PASSWORD` | Proxy password |

Next: [Account data]({% link data.md %}).
