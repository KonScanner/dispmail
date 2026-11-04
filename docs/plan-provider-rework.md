# Plan: provider path rework

Status: **proposed, pending go-ahead.** Selectors were captured from the live sites on
2026-11-03; raw evidence is in `docs/recon/` (screenshots + full HTML snapshots).

## 0. What is actually broken today

| Area | Current state | Why it cannot work |
|------|---------------|--------------------|
| Selenium | `selenium==3.141.0` (2021) | `find_element_by_*` was removed in Selenium 4.3; `options.headless` is deprecated; `webdriver-manager` is superseded by Selenium Manager |
| Waiting | `t.sleep(...)` + infinite `force_click` loop, `force_find` that returns `None` after 10 tries | sleeps are both too short and too long; the infinite click loop hangs; the `None` return turns into `TypeError` later |
| Tuta | entry point `mail.tutanota.com/login`, XPath tied to the 2021 layout, free plan picked by positional XPath | URL, brand and DOM all changed; the new page is React with `data-testid`s |
| Interia | `/html/body/div[1]/...` XPaths, `find_element_by_class_name` | DOM changed, field `name`/`id` values are randomised per page load, cookie CMP blocks the form, submit is gated by invisible reCAPTCHA Enterprise |
| Credentials | `bytes(random_int)` (allocates up to 100 KB, raises for negative), 13-char password | Interia needs 12–64 chars, a letter plus a digit/symbol, and rejects common passwords; Tuta has its own rule |
| Names | `safe_split` indexes `[0]`, `[1]` | crashes on mononyms and on 3+-part Faker names |
| Domains | `tutanota` path writes `domain="interia"`, `interia` path writes `domain="tutanota"` | the two calls are swapped |
| File write | `write_if_complete(user_path=...)` ignores `user_path` | always writes to `os.getcwd()`; untestable |
| Success | `input("[y/N]")` | no unattended e2e, no verification, no record of what was seen |
| CLI | `sys.argv[1]` with no guard | `IndexError` with no args; no `--help`, no flags |
| Tests | none | every regression is discovered by running against a live site |
| Tooling | black/flake8 pre-commit pinned to Python 3.10, `requirements.txt` | not the agreed uv/ruff/ty stack |

## 1. What "path mode" means here

A path = **provider × plan × domain × consent strategy**, executed in a **mode**
= `dry-run | live` × `headless | headed` × `direct | proxy` × `manual | auto` confirm.

| Path id | Provider | Plan | Domain | Consents | In scope |
|---------|----------|------|--------|----------|----------|
| `tuta-free-tuta.com` | Tuta | Free | `tuta.com` | required only | **yes, first** |
| `tuta-free-tutamail.com` | Tuta | Free | `tutamail.com` | required only | yes, one run only |
| `tuta-free-tuta.io` | Tuta | Free | `tuta.io` | required only | yes |
| `tuta-free-tutanota.com` | Tuta | Free | `tutanota.com` | required only | yes |
| `tuta-free-tutanota.de` | Tuta | Free | `tutanota.de` | required only | yes |
| `tuta-free-keemail.me` | Tuta | Free | `keemail.me` | required only | yes |
| `tuta-paid` | Tuta | Revolutionary/Legend | any | n/a | **never** (would start a paid subscription) |
| `interia-free-required` | Interia | Free | `interia.pl` | required only (default) | **assisted only** |
| `interia-free-all` | Interia | Free | `interia.pl` | accept-all | assisted only, opt-in flag |
| `interia-paid` | Interia | Bez reklam / PocztaPRO | n/a | n/a | **never** (would start a paid subscription) |

Up to four accounts per provider in a rolling 7 days are allowed (see the egress
plan, decision #13). The domain variants exist because the domain is a parameter; they
are not separate accounts. Tuta still asks you to affirm one free account per person.

"Assisted" means the tool drives the flow until a human-only step (image CAPTCHA,
SMS code) and resumes after the human completes it. Tuta is fully unattended;
Interia cannot be, because its post-submit verification requires a human and a phone
or mailbox.

## 2. Tuta path

Entry: `https://app.tuta.com/signup` → HTTP 302 → `/?r=/signup` → 200, SPA rewrites the
address bar back to `/signup`. No CAPTCHA in the DOM **or in the signup bundle** at any
captured step (the old `mail.tutanota.com/login` is gone).

### Steps and selectors

| # | Step | Locator | Notes |
|---|------|---------|-------|
| 0 | Pre-flight egress check | n/a | fail closed before touching the provider |
| 1 | Open signup | `goto` | wait for `#plan-selector` and `[data-testid="btn:continue_action"]` |
| 2 | Choose **Free** | `#plan-selector input[name="BuyOptionBox"]` index 2 (0=Revolutionary, 1=Legend), then assert `checked` | **default is Legend (paid)**; selecting re-renders the card cluster and Continue wrapper, so re-query after this step; wait 0.5–1 s for the animation |
| 3 | Continue | `[data-testid="btn:continue_action"]` | never disabled; advances to `#signup-account-dialog` |
| 4 | Username | `input[data-testid="tfi:username_label"]` (or `input[aria-label="Username"]`) | min 3 chars, allowed `[A-Za-z0-9._-]`; `+` and spaces are invalid; availability is checked live ("Email address is available") |
| 5 | Domain | `button[data-testid="btn:domain_label"]`, then `button[role="option"][title="tutamail.com"]` | 6 domains; **`tuta.com` requires a paid plan** (live modal) while `tutamail.com` is the free default; menu adds a `Close` button |
| 6 | Password | `input[data-testid="tfi:newPassword_label"]` | rule not stated in DOM; generate 16+ mixed chars; do **not** click "Generate password" (mutates the field) |
| 7 | Repeat password | `input[data-testid="tfi:repeatedPassword_label"]` | |
| 8 | Attestation | checkbox labelled `I do not own any other Free Tuta account and I will not use this account for business.` | legal statement; live run requires `--accept-attestation` |
| 9 | Terms | checkbox labelled `I have read and agree to the following documents:` | required |
| 10 | Create account | `button[data-testid="btn:create_new_account_label"]` | enabled after **both checkboxes** are ticked, but ~200 ms after the DOM state changes — poll `wait_enabled`, never check once; username/password validation happens on submit. This is the **submit step** (live gate) |
| 11 | Recovery Kit | step 3 of the wizard, `button[aria-label="Recovery Kit"]` becomes enabled | the code is 64 hex chars in 16 groups of four; poll the page text for it (up to `DISPMAIL_RECOVERY_TIMEOUT`), store it, and keep the account row if it never renders |
| 12 | Success | recovery-kit text present and/or inbox URL | insert into `data/sqlite.db` and write `data/recovery_<email>_<platform>.txt` |

Entry/stack details: single-URL SPA state machine, no iframes, no shadow DOM, no cookie
banner, `x-frame-options: DENY`, no Cloudflare headers. The UI language follows the
browser: the tool forces `en-US` for Tuta (the Greek UI broke English status-text
selectors), while the timezone still comes from the egress country. Re-query every element after
each step; stale handles raise `StaleElementReferenceException`.

Still unverified: the Recovery Kit markup and the button that leaves it (step 3 of the
wizard, only reachable after a real submit), the password rule, and whether anything
(challenge or otherwise) appears on submit. The first live attempt must save a
screenshot + sanitized DOM at step 11 **before** writing the account file, so the
contract snapshot can be updated from reality.

### Tuta branches

- `--domain` overrides the default; invalid/taken username shows an inline error →
  regenerate the username once (`EXISTS` handling).
- Turnstile may appear only on submit (it is absent from the captured DOM). If it
  does, the challenge policy applies: human handoff, never automated.
- The Free plan sidebar states "Only 1 free Account per person". The tool refuses a
  second live Tuta run unless `--replace-account` is passed.

## 3. Interia path

Entry points (both confirmed live):

- `https://konto-pocztowe.interia.pl/#/nowe-konto` — plan chooser: `Darmowe` (0,00 zł,
  button `WYBIERAM`), `Bez reklam` (49,00 zł/rok), `PocztaPRO` (29,00 zł/rok).
- `https://konto-pocztowe.interia.pl/#/nowe-konto/darmowe` — free form used by the
  direct path. The flow uses this URL; the plan page is the fallback if it is retired.

State: **harder than Tuta.**

### Blockers found in recon

1. **Cookie CMP covers the form.** Buttons: `PRZEJDŹ DO SERWISU`, `USTAWIENIA
   PRYWATNOŚCI`, `Przypomnij później`. The old cookie XPath no longer exists.
2. **reCAPTCHA Enterprise, invisible, on submit.** `<div id="g-recaptcha"
   data-callback="onSubmit">` plus an invisible anchor iframe; a badge placeholder
   sits next to the submit button. It may pass silently or challenge.
3. **Randomised field names and ids.** `a303g`, `dkp1x7`, `a9tto4` differ on every
   load. The stable ones are `infoInput`, `birthdayDay`, `birthdayYear`, `password`,
   `rePassword`, and the agreement names (`agreementacceptAll-acceptAll`,
   `agreement74-213`, `agreement31-122`, `agreement30-121`).
4. **Consent inputs are hidden** (`visible: false`); the styled label is what a human
   clicks. Only the accept-all checkbox is visible until `Więcej` is expanded.
5. **Custom dropdowns**: month, gender (`Jak się do Ciebie zwracać?`: **Pan / Pani**)
   and the domain picker (`account-select domains-select`).
6. **Honeypots**: `input.input--fake[name=login-fake]`, `input.input--fake[name=password-fake]`
   (offscreen at x≈-9755), `#infoInput` (0×0), and `.fake-input` inside the custom
   selects. Any "first text input" strategy fills a decoy. They must be excluded
   explicitly.
7. **Post-submit verification is part of the flow** (bundle evidence, not observed):
   the submit handler runs `executeCaptcha(createAccountAttempt)` → an **image CAPTCHA
   step** (`captcha__image`, `captcha__input`, "Kod jest wymagany") → e-mail/SMS
   verification steps (`krok_2_mail`, `krok_2_sms`, `krok_4_sms`, ...). Creating an
   Interia account unattended is therefore **not possible**; it is a human-in-the-loop
   flow even with a clean egress.

### Confirmed form layout (from the post-CMP screenshot)

| Order | Field | Label / strategy |
|-------|-------|------------------|
| 1 | First name | label `Imię`; random `id`/`name` per load |
| 2 | Surname | label text is **empty** (rendered with CSS `::before`); use `label.RMii...`/`for` or the 2nd visible text input |
| 3 | Day | `#birthdayDay` (stable) |
| 4 | Month | `Miesiąc` custom select: `Styczeń, Luty, Marzec, Kwiecień, Maj, Czerwiec, Lipiec, Sierpień, Wrzesień, Październik, Listopad, Grudzień` |
| 5 | Year | `#birthdayYear` (stable) |
| 6 | Gender | custom select with options `Pan`, `Pani` |
| 7 | Username | label `Nazwa konta`; random `id`/`name` per load |
| 8 | Domain | `Nazwa domeny`, default `interia.pl`; 12 options; entitlement not yet confirmed |
| 9 | Password | `#password`; 12–64 chars, letter + digit/symbol, not a common password |
| 10 | Repeat password | `#rePassword` |
| 11 | Consents | all three **required** rows (`agreement31-122`, `agreement30-121`, `agreement74-213`) plus optional marketing rows; `required` checks the three with the red asterisk, `all` uses `agreementacceptAll-acceptAll`; inputs are 0×0 → click the wrapping label and assert `is_checked()` |
| 12 | Submit | `form button[type="submit"]` text `ZAŁÓŻ DARMOWE KONTO`; reCAPTCHA executes here |
| 13 | **After submit** | image CAPTCHA step, then mail/SMS verification; the account is not usable until those pass |

Free-plan domain menu (from the open dropdown): `interia.pl`, `poczta.fm`, `interia.eu`,
`interia.com`, `intmail.pl`, `interiowy.pl`, `adresik.net`, `pisz.to`, `vip.interia.pl`,
`pacz.to`, `ogarnij.se`, `własny_adres.hub.pl`, plus a "Załóż konto we własnej domenie"
entry. All items carry the `unavailable` class while the local part is empty, so that
class tracks local-part availability, **not** plan entitlement; whether the free plan
restricts the domain to `interia.pl` is still unverified.

### Interia branches

- Consent strategy: `accept-all` (single click) vs `required-only` (expand `Więcej`,
  check terms + data processing, leave marketing off). Both must be tested; the
  privacy-preferring default is `required-only`. This is independent of the mandatory
  Regulamin checkbox (`agreement74-213`).
- Domain: default `interia.pl`; the other 11 domains are exercised only to record
  whether the free plan allows them.
- reCAPTCHA: silent pass → image CAPTCHA → mail/SMS verification. This is why the
  Interia path is **assisted**: a human must solve the image CAPTCHA and receive the
  SMS/e-mail code in the same session. The tool fills the form, pauses, and resumes
  when the human confirms; it never solves a challenge itself.

## 4. Work breakdown

Ordered so that the pipeline is proven on the easier provider first.

| Phase | Work | Output |
|-------|------|--------|
| A | `settings`, `egress`, `egress_probe`, `persona`, `ledger`, `flows`, `browser` adapter, CLI skeleton | unit tests green, no site code |
| B | Tuta `ProviderSpec` from the table above + snapshot contract test | offline contract test green |
| C | Tuta dry-run, iterate 5× | ring 2 green, 0 challenges |
| D | Tuta live once; capture recovery kit DOM | account file written, snapshot updated |
| E | Interia recon v2 (post-CMP form) | new snapshot + field order |
| F | Interia `ProviderSpec` + contract test + dry-run | ring 1/2 green |
| G | Interia live once (CAPTCHA handoff) | account file written |
| H | CI ring 1, docs, `doctor` | green build |

Estimated: 2–3 working days, dominated by the two live runs and the Interia field
mapping.

## 5. Definition of done (per provider)

1. Offline contract test resolves every locator against the saved snapshot.
2. Five consecutive dry-runs: pre-flight passes, all fields fill, submit is enabled,
   nothing is submitted, zero challenges, under 90 s each.
3. One live run: account created, success detected, row written to `data/sqlite.db`,
   recovery kit captured to `data/recovery_<email>_<platform>.txt` (Tuta), ledger
   updated.
4. Failure paths exercised in unit tests: username taken, challenge, egress mismatch,
   budget exhausted, provider DOM changed.
5. Docs updated with the final selector table and the captured recovery-kit markup.

## 6. Known unknowns (resolve during implementation, not by guessing)

- Tuta: the recovery code is verified: 64 hex characters, 16 groups of four, shown with
  `Copy Recovery Code` / `Download PDF-file`. Still unknown: the exact post-create button that
  leaves the kit screen, and the password rule.
- Live-verified so far: plan selection, username availability, free-domain choice,
  password fill and both agreements all work; a dry-run stops cleanly before submit.
- Interia: whether the free plan restricts the domain to `interia.pl`; whether the
  SMS step is mandatory (vs e-mail verification) for a free account; the number of
  verification steps actually shown after a real submit; whether the image CAPTCHA
  appears before or after reCAPTCHA in practice; the final success URL; whether
  expanding `Więcej` is required for the `required-only` consent strategy.
- Both: whether the signup flow changes between the dry-run and the live run (that
  is what the contract snapshots and ring 2 exist to detect).
