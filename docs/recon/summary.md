# Signup recon — side by side (Tuta vs Interia)

Recon date 2026-11-03, headless Chromium, **read-only**: no accounts created, no passwords entered,
no captchas solved, no form submitted. Details: [tuta-signup.md](tuta-signup.md) · [interia-signup.md](interia-signup.md).

## Side-by-side

| Aspect | Tuta | Interia |
|---|---|---|
| Documented entry | `https://app.tuta.com/signup` | `https://konto-pocztowe.interia.pl/#/nowe-konto/darmowe` |
| Server behaviour | **302** → `https://app.tuta.com/?r=/signup` (**200**); SPA rewrites URL back to `/signup` | Fragment route; document **200** for every `/…/#/…` URL (root hash-redirects to `/#/nowe-konto`) |
| Title | `Tuta: Login & Sign up for free` | `Załóż konto pocztowe – Poczta w Interia – rejestracja konta email` |
| Stack | React SPA (`window.tutao`, `#root`), ESM chunks | custom TS/JS SPA, hash router, CSS-module hashed classes |
| Shadow DOM / iframes | none | none / reCAPTCHA + 0×0 CMP + tracking iframes |
| Cookie banner | **none** | **full-screen RODO modal** (must dismiss first) |
| Plan step | plan cards in `#plan-selector`; free = 3rd card/radio; default = paid **Legend** | plan chooser `/#/nowe-konto`: Darmowe 0,00 zł · Bez reklam 49,00 zł/rok · PocztaPRO 29,00 zł/rok |
| Free option | “Free”, €0, 1 GB, 1 account, deleted after 6 months w/o login | “Darmowe”, 0,00 zł, free mailbox, default domain `interia.pl` |
| Form fields | Username (+6 domains, default `@tutamail.com`), Set/Repeat password, 2 agreements | Imię, Nazwisko, birthday, gender (Pan/Pani), local part + domain, password ×2, 4 consent rows |
| Stable handles | `data-testid` on every button/field (`btn:continue_action`, `tfi:username_label`, …) | fixed ids only for `birthdayDay`, `birthdayYear`, `password`, `rePassword`; agreement `name`s; everything else randomised |
| Randomised identity | none | Imię / Nazwisko / Nazwa konta get new 6-char `id`+`name` **per load** |
| Honeypots | none seen | `login-fake`, `password-fake`, `#infoInput`, `.fake-input` |
| CAPTCHA | **none** in DOM or bundle at any observed step | **reCAPTCHA Enterprise invisible** (site key `6Ld1J8MrAAAAAPU6l0PSxKVwkPdTelE8ExTfEPHW`, `sa=newAccount`) + **image captcha step** after submit (bundle) |
| Anti-bot | none observed (no CF challenge) | random ids, honeypots, API-driven agreements, CSS-`::before` label |
| Submit button | `btn:create_new_account_label`, disabled until **both** checkboxes ticked | `button[type=submit]` “ZAŁÓŻ DARMOWE KONTO”, never disabled while empty |
| Post-submit | “Recovery Kit” step — **not observed** | captcha step → SMS/mail verification steps — **not observed** |
| Console/status | 200 app, 302 `/signup`; FCP 232 ms | 200 document + APIs; FCP 896 ms, load ≈1.95 s |
| Old automation verdict | absolute XPaths in old layout all stale; modal/radio model changed; Selenium 3 APIs dead | absolute XPaths stale, **and** ids/names randomise, so even fixed positional ids cannot be trusted; consent layer moved |

## Answers to the five open questions

1. **Tuta Free card + Continue.** Free = 3rd `.buyOptionBox-v2` card, radio `#plan-selector input[name="BuyOptionBox"]` index **2** (0=Revolutionary, 1=Legend, 2=Free). It sits in `#plan-selector > div:nth-of-type(2)` (the two paid cards share `div:nth-of-type(1)`). `Continue` (`button[data-testid="btn:continue_action"]`) has **no `disabled` attribute** at any point and advances to the account form once Free is checked; verified `[false,false,true]` then `#signup-account-dialog` present.
2. **Tuta domain-menu markup.** `button[data-testid="btn:domain_label"]` opens `.dropdown-content[role="menu"]` containing `button[role="option"][data-testid="btn:domain"][title="<domain>"]` items (label text = domain) plus a `Close` button. Options: `tuta.com`, `tutamail.com` (default), `tuta.io`, `tutanota.com`, `tutanota.de`, `keemail.me`.
3. **Interia dropdown labels.** Gender: **Pan**, **Pani**. Month: **Styczeń, Luty, Marzec, Kwiecień, Maj, Czerwiec, Lipiec, Sierpień, Wrzesień, Październik, Listopad, Grudzień** (rendered in `li.account-select__options__item > span.account-select__options__label`). Domain list: `interia.pl`, `poczta.fm`, `interia.eu`, `interia.com`, `intmail.pl`, `interiowy.pl`, `adresik.net`, `pisz.to`, `vip.interia.pl`, `pacz.to`, `ogarnij.se`, `własny_adres.hub.pl`.
4. **Free plan vs domains.** Not confirmed. On the free form all 12 domain `li` items carried the `unavailable` class while “Nazwa konta” was empty — that class tracks local-part availability, not plan entitlement. Default value is `interia.pl`. Needs one more read-only check (type a local part, reopen the dropdown).
5. **Interia submit / reCAPTCHA evidence (from `_raw/interia-main.js`).** Token is fetched through
   `GET /api/recaptcha/recaptcha/next-register`; challenges through `POST /api/captcha/challenges?client_id=rejestracja.poczta.interia`;
   reCAPTCHA Enterprise executes on submit (`executeCaptcha(createAccountAttempt)`, `getCaptchaToken()`), and the
   bundle contains an explicit image-captcha step (`captchaStepView`, `krok_captcha`, `.captcha__image/.captcha__input/.captcha__error`,
   “Kod jest wymagany”, “Kod jest nieprawidłowy”, “Kod niepoprawny, spróbuj jeszcze raz.”). After the captcha come
   verification steps `krok_2_mail|sms|sms_mail` … `krok_6_sms` (SMS/mail codes). **None of this was observed live** —
   inferred from the bundle only. Also relevant: the same bundle shows the form fields with randomised ids/names,
   the honeypots, and the agreement IDs (`agreement31-122`, `agreement30-121`, `agreement74-213`, accept-all).

## Confirmed facts (observed live)

- Tuta entry chain: `app.tuta.com/signup` 302 → `/?r=/signup` 200 → SPA URL `/signup`; `tutanota.com` 301 → `tuta.com`; `tuta.com/signup` 404.
- Tuta flow is 3 observed steps: plan → free selected → account form (`#signup-account-dialog`); wizard labels “Free / 2 Create Account / 3 Recovery Kit”; bundle step names add “Order Confirmation”.
- Tuta plan prices: Revolutionary €3.60/€3 (20 GB), Legend €9.60/€8 (500 GB, preselected), Free €0 (1 GB).
- Tuta `Create account` enables on **checkboxes only**; username/password are validated on submit.
- Tuta username validation messages: “Mail address is not valid.” / “Email address is available.” / “Email address is not available.”; 2 chars invalid, 3+ accepted format-wise; `[A-Za-z0-9._-]` allowed in samples, `+`/space rejected, case preserved.
- Tuta: **no captcha, no cookie banner, no Cloudflare challenge**; zero captcha references in the signup bundle.
- Tuta: **no phone number and no recovery email** in signup; recovery is a “Recovery Kit” issued after account creation.
- Tuta `Back` returns to the plan step (same URL).
- Interia flow: plan chooser (`/#/nowe-konto`) → free form (`/#/nowe-konto/darmowe`) blocked by RODO modal → form.
- Interia free mailbox confirmed: “Darmowe — 0,00 zł”, “Twój wybór: Konto Darmowe”, domain default `interia.pl`, CTA “ZAŁÓŻ DARMOWE KONTO”.
- Interia password rules shown: litery; liczba lub !#$%&*@; 12 – 64 znaków; siła; niepopularna kombinacja znaków.
- Interia randomises 3 field ids/names per load; `birthdayDay`, `birthdayYear`, `password`, `rePassword` are stable.
- Interia honeypots: `login-fake`, `password-fake` (x≈-9755), `#infoInput` (0×0), `.fake-input`.
- Interia reCAPTCHA Enterprise invisible is present on the form page (iframes + badge + script) and is submit-time.
- Interia consent modal buttons have stable `aria-label`s: “Przejdź do serwisu”, “Przypomnij później”, “Ustawienia prywatności”.
- Interia: no Cloudflare/JS interstitial; document and APIs answered 200.
- Interia timings: FCP 896 ms, load ≈1.95 s; Tuta FCP 232 ms, plan UI ≈2.5 s after navigation.

## Uncertain / unverified

- Tuta post-submit **Recovery Kit** screen (selectors, contents, whether it can be skipped) — never reached.
- Whether Tuta presents a captcha **on submit** — no evidence in the bundle, but unproven.
- Tuta password policy (length/complexity) — not probed (no password typing allowed); no rule text in UI.
- Tuta full allowed-character set for the username (only 6 samples tested); no `maxlength` attribute.
- Tuta plan-step “Yearly/Monthly” toggle semantics: both price pairs exist in the DOM; the switch is `role=switch`, unchecked.
- Interia post-submit steps (captcha image, SMS/mail verification) — bundle-only evidence, never observed.
- Interia free-plan domain entitlement (question 4 above).
- Interia `content-type: application/json` on a plain curl of the root (browser still received HTML; likely `Accept`-based negotiation).
- Interia whether the submit button performs any client-side validation before the captcha request.
- Whether the RODO consent is stored as cookie or localStorage (not inspected).
