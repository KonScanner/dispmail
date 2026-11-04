# Interia (Poczta Interia) — live free-mailbox signup recon

Recon date: 2026-11-03 (Europe/Athens), headless Chromium 1920×1080, read-only.
Nothing was submitted: no account created, no password typed, no captcha solved, submit button never clicked.

Artifacts (this folder):
- `interia-step-1.png|html` — plan chooser (root URL `/#/nowe-konto`)
- `interia-step-2.png|html` — free form **with** RODO/cookie consent modal (blocker)
- `interia-step-3.png|html` — free form after consent
- `interia-step-4.png|html` — domain dropdown open (12 domains)
- `interia-step-5.png|html` — month dropdown open (Styczeń…Grudzień)
- `_raw/interia-step-*.json` — per-step control inventory (attributes, rects, selector candidates, meta/timing)

---

## (a) Current flow

**Entry points / redirects**

| URL | Result |
|---|---|
| `https://konto-pocztowe.interia.pl/` | HTTP 200; the SPA hash-redirects to `/#/nowe-konto` → **“Wybierz konto”** plan chooser |
| `https://konto-pocztowe.interia.pl/#/nowe-konto` | plan chooser (fragment routes never hit the server) |
| `https://konto-pocztowe.interia.pl/#/nowe-konto/darmowe` | **free mailbox form** — the documented entry point still works and lands on the form directly |
| `https://konto-pocztowe.interia.pl/#/nowe-konto/bez-reklam` | paid “Bez reklam” route (in bundle) |
| `https://konto-pocztowe.interia.pl/#/nowe-konto/firmowe` | paid/business route (in bundle) |
| `https://poczta.interia.pl/` | 301 → `https://poczta.interia.pl/logowanie/` (webmail login) |

Page title: **“Załóż konto pocztowe – Poczta w Interia – rejestracja konta email”**.
Curl note: a plain `curl` GET of the root returns `content-type: application/json` while the browser
receives and renders HTML (200) — the server appears to content-negotiate on `Accept`; use a browser-like
`Accept: text/html` header when checking status from scripts.

**Stack**: hand-written TypeScript/JS SPA (no React/Angular/Vue markers: `window.React`, `ng`, `__NEXT_DATA__`,
`data-v-app` all absent), CSS-module hashed class names (`_2E5n5h3v8fnkpu`, `_1san5h3v8fnkpu`, …), hash router.
No shadow DOM. Iframes present: Google reCAPTCHA enterprise (`anchor` + `bframe`), a 0×0 CMP iframe
(`prywatnosc.interia.pl/rodo-iframe`), Gemius/TCF tracking frames.

**Visible signup path:**

1. **Plan chooser** (`/#/nowe-konto`, “Wybierz konto”) — 3 cards `.account-type`:
   *Darmowe* **0,00 zł**, *Bez reklam* **49,00 zł / ROK**, *PocztaPRO* **29,00 zł / ROK**.
   Each card has `<a href="#/nowe-konto/darmowe|bez-reklam|firmowe">WYBIERAM</a>` plus an overlapping
   `<button class="btn btn--rectangular">WYBIERAM</button>` (same label, 3 pairs).
2. **Free form** (`/#/nowe-konto/darmowe`) — full-screen **RODO/cookie consent modal** covers the page.
   Must be dismissed before anything is reachable.
3. **Free form after consent** — “Twój wybór: Konto Darmowe / Możesz zmienić w trakcie użytkowania”,
   fields: Imię, Nazwisko, Dzień/Miesiąc/Rok, “Jak się do Ciebie zwracać?” (gender), Nazwa konta + Nazwa
   domeny (`interia.pl`), Hasło (+ live requirements), Powtórz hasło, 4 checkbox rows (accept-all +
   3 agreements), submit **“ZAŁÓŻ DARMOWE KONTO”**, link “Przejdź do rejestracji konta płatnego”.
4. **After submit — NOT OBSERVED.** Bundle evidence shows a captcha step then verification steps
   (`krok_captcha`, `krok_2_mail/sms`, …) — see (c) and (e).

---

## (b) Step table — every control with a Selenium-usable selector

Stability: ✅ semantic/stable id · ⚠️ structural or label text · ❌ random per page load.

### Step 1 — plan chooser

| Control | Visible text | Attributes | Selector | Stability |
|---|---|---|---|---|
| Free card | “Darmowe”, “0,00 zł”, 3 bullet points | `.account-type`, `.account-type__title` | `.account-type` (1st) / text “Darmowe” | ⚠️ |
| Free CTA link | “WYBIERAM” | `a[href="#/nowe-konto/darmowe"]` | `a[href="#/nowe-konto/darmowe"]` | ✅ best handle |
| Free CTA overlay button | “WYBIERAM” | `button.btn.btn--rectangular` (no id/name) | `a[href="#/nowe-konto/darmowe"]` then click | ⚠️ button catches the pointer, link is the semantic target |
| Paid CTAs | “WYBIERAM” | `a[href="#/nowe-konto/bez-reklam"]`, `a[href="#/nowe-konto/firmowe"]` | same pattern | ✅ |

Prices as shown: Free **0,00 zł**, Bez reklam **49,00 zł ROK**, PocztaPRO **29,00 zł ROK**.

### Step 2 — free form + RODO/cookie consent modal (blocking)

> ⚠️ Cookie/consent modal, full-screen, appears on load and after a fresh navigation. It intercepts clicks.

| Control | Visible text | Attributes | Selector | Stability |
|---|---|---|---|---|
| Accept / go to site | “PRZEJDŹ DO SERWISU” | `class="rodo-popup-agree rodo-popup-main-agree"`, `aria-label="Przejdź do serwisu"`, `data-index="3"` | `button[aria-label="Przejdź do serwisu"]` | ✅ |
| Remind later | “PRZYPOMNIJ PÓŹNIEJ” | `class="rodo-popup-later"`, `aria-label="Przypomnij później"` | `button[aria-label="Przypomnij później"]` | ✅ |
| Privacy settings | “USTAWIENIA PRYWATNOŚCI” | `class="rodo-popup-settings rodo-popup-main-settings"`, `aria-label="Ustawienia prywatności"` | `button[aria-label="Ustawienia prywatności"]` | ✅ |
| Footer link | “Ustawienia Preferencji” | `class="link"` | `//button[normalize-space()="Ustawienia Preferencji"]` | ⚠️ |

All three buttons are in the **main document** (not the 0×0 `rodo-iframe`). Accepting removes the modal
entirely (verified: no `PRZEJDŹ DO SERWISU` button afterwards, control count 64 → 50).

### Step 3 — free form after consent

| Control | Label / hint | Attributes | Selector | Stability |
|---|---|---|---|---|
| Imię | “Imię” | `input type=text`, **random `id`/`name`** (e.g. `j2a7e3`, `a303g`), `class="_2E5n5h3v8fnkpu"`, `autocomplete="new-password"`; label sibling `label._331q5h3v8fnkpu[for="<same random id>"]` | structural: `form .register-form__inputs > div:nth-of-type(2) input[type=text]` — or resolve at runtime: `label[for]` → id | ❌ id/name · ⚠️ structure |
| Nazwisko | label text is **empty**, visible “Nazwisko” comes from CSS `::before` on the label | same random-id input; label class `_331q5h3v8fnkpu RMii5h3v8fnkpu` | `//form//label[contains(@class,'RMii')]/@for` → find by id, or 3rd text input in `.register-form__inputs` | ⚠️ |
| Dzień | “Dzień” | `input#birthdayDay`, `name="birthdayDay"`, `class="account-input"`, `maxlength="2"` | `#birthdayDay` | ✅ |
| Miesiąc | “Miesiąc” | custom select: `div.account-input-container.account-select` → `input.fake-input` + `span.account-input__value`; options `ul.account-select__options.visible` | `//div[contains(@class,'account-select')][.//label[normalize-space()='Miesiąc']]` then `//li[contains(@class,'account-select__options__item')]` | ⚠️ |
| Rok | label text “Rok” (rendered “Rok ur.”) | `input#birthdayYear`, `name="birthdayYear"`, `maxlength="4"` | `#birthdayYear` | ✅ |
| Gender | “Jak się do Ciebie zwracać?” | custom select `div.account-input-container.account-select.account-input__label--gender`; options **“Pan”**, **“Pani”** | `div.account-input__label--gender` + option by text | ⚠️ |
| Nazwa konta (local part) | “Nazwa konta” | `input type=text`, **random `id`/`name`** (e.g. `4vqm8`, `znze9h`), class `_2E5n5h3v8fnkpu`; domain is a separate control | `//form//div[label[normalize-space()='Nazwa konta']]//input` | ⚠️ label text |
| Nazwa domeny | “Nazwa domeny”, current value `interia.pl` | `.domains-row` → `.account-input-container.account-select.domains-select` → `span.account-input__value`; options `ul.account-select__options` | `.domains-row .account-select` + `li.account-select__options__item` by domain text | ⚠️ |
| Domain options | see list below | `li.account-select__options__item[.unavailable]` > `span.account-select__options__label` | `li.account-select__options__item .account-select__options__label` (text) | ⚠️ |
| Hasło | “Hasło” | `input#password`, `name="password"`, `type=password`, `class="account-input"`, `autocomplete="new-password"` | `#password` | ✅ |
| Password requirements | “Wymagania:” list | `.account-input__tips-header`, `ul.account-input__tips > li.account-input__tips--neutral` (with `i.marker`), text items | read `#password` container text | ⚠️ |
| Powtórz hasło | “Powtórz hasło” | `input#rePassword`, `name="rePassword"`, `type=password` | `#rePassword` | ✅ |
| Required rows | three rows marked with a red asterisk: commercial information (`agreement31-122`), personal-data marketing (`agreement30-121`), Regulamin (`agreement74-213`) |
| Accept-all | “Akceptuję i zaznaczam wszystkie poniższe zgody” | `input#`(none)`name="agreementacceptAll-acceptAll"`, `class="checkbox"`, rendered 0×0; wrapping `label.checkbox-container` | `input[name="agreementacceptAll-acceptAll"]` / click its `label` | ✅ name · ⚠️ click target |
| Marketing consent | “Wyrażam zgodę na otrzymywanie informacji handlowych…” | `input name="agreement31-122"`, label class `checkbox-container checkbox-container--required` | `input[name="agreement31-122"]` | ✅ name (ID suffix from API) |
| Personal-data marketing | “Wyrażam zgodę na przetwarzanie danych osobowych w celach marketingowych…” | `input name="agreement30-121"` | `input[name="agreement30-121"]` | ✅ |
| Regulamin (required) | “Akceptuję Regulamin świadczenia usługi i zobowiązuję się do jego przestrzegania.” + link “Regulamin” | `input name="agreement74-213"` | `input[name="agreement74-213"]` or `input[name^="agreement74-"]` | ✅ name |
| Submit | “ZAŁÓŻ DARMOWE KONTO” | `button[type=submit]`, no id/name/testid; not disabled while form is empty | `form button[type="submit"]` | ✅ |
| Paid signup link | “Przejdź do rejestracji konta płatnego” | `button` (not a link) | `//button[contains(.,"rejestracji konta płatnego")]` | ⚠️ |
| Honeypots (traps!) | — | `input.input--fake[name="login-fake"]`, `input.input--fake[name="password-fake"]` (positioned at x≈-9755), `#infoInput` (0×0, y≈-9789), several `input.fake-input` inside the custom selects | **exclude**: `.input--fake`, `#infoInput`, `.fake-input` | ✅ (easy to filter) |

**Miesiąc options** (exact labels, first option is selected by default? none selected initially):
`Styczeń, Luty, Marzec, Kwiecień, Maj, Czerwiec, Lipiec, Sierpień, Wrzesień, Październik, Listopad, Grudzień`.

**Nazwa domeny options** on the free form (order observed): `interia.pl` (default),
`poczta.fm`, `interia.eu`, `interia.com`, `intmail.pl`, `interiowy.pl`, `adresik.net`, `pisz.to`,
`vip.interia.pl`, `pacz.to`, `ogarnij.se`, `własny_adres.hub.pl`, plus an entry
“Załóż konto we własnej domenie”. While “Nazwa konta” was empty **every** `li` had the class
`unavailable` (including `interia.pl`) — that class tracks local-part availability, **not** plan entitlement.

**Password rules displayed in the UI** (answers the validation question without typing a password):
`Wymagania:` — “litery” · “liczba lub !#$%&*@” · “12 - 64 znaków” · “siła:” · “niepopularna kombinacja znaków”.
The individual `li` items flip class between `account-input__tips--neutral` and a positive state as the
user types (class names only; rule text captured verbatim).

---

## (c) Blockers / captcha / anti-bot

1. **RODO/cookie consent modal** (step 2) is a hard blocker: full-screen overlay, must be dismissed via
   `button[aria-label="Przejdź do serwisu"]` (or “Przypomnij później”). It reappears on fresh navigation
   until consent is stored (localStorage/cookie).
2. **Google reCAPTCHA Enterprise, invisible** — present from page load:
   - iframes `https://www.google.com/recaptcha/enterprise/anchor?...&size=invisible&sa=newAccount`
     (256×60) and `.../enterprise/bframe` (1918×150);
   - script `https://www.google.com/recaptcha/enterprise.js?onload=recaptchaOnLoadCallback&hl=pl&render=explicit&render=6Ld1J8MrAAAAAPU6l0PSxKVwkPdTelE8ExTfEPHW`;
   - visible badge “korzysta z zabezpieczenia reCAPTCHA” bottom-right;
   - site key `6Ld1J8MrAAAAAPU6l0PSxKVwkPdTelE8ExTfEPHW`, action/`sa=newAccount`.
   It is **executed on submit** (bundle: `executeCaptcha(createAccountAttempt)` / `getCaptchaToken()`), not on load.
3. **Image captcha step after submit** (from the JS bundle, not observed): `captchaStepView` with markup
   classes `captcha__container`, `captcha__image`, `captcha__img`, `captcha__input`, `captcha__error`,
   `captcha__command`; strings “Kod jest wymagany”, “Kod jest nieprawidłowy”,
   “Kod niepoprawny, spróbuj jeszcze raz.”, “Wpisz poprawny kod.”; analytics events
   `captchaStepView`, `captchaStepNextSuccess`, `captchaStepNextError`.
4. **Post-captcha verification steps** (from bundle analytics keys, not observed):
   `krok_1`, `krok_2_brak|krok_2_mail|krok_2_sms|krok_2_sms_mail`, `krok_3_mail|krok_3_sms`,
   `krok_4_sms`, `krok_5_sms`, `krok_6_sms` — i.e. the flow continues with e-mail/SMS verification.
   Do not assume the account exists right after clicking the submit button.
5. **Anti-bot hints** (no Cloudflare challenge, no JS interstitial; document 200):
   - **randomised field identity**: the three text inputs that hold Imię / Nazwisko / Nazwa konta get fresh
     6-char `id`+`name` values on every load (observed `a303g`, `dkp1x7`, `a9tto4` then `j2a7e3`, `aptlzj`,
     `4vqm8` then `h6fuss`, `dw9zgc`, `znze9h` …). Stable ids remain only for `birthdayDay`, `birthdayYear`,
     `password`, `rePassword`.
   - **honeypot inputs**: `login-fake`, `password-fake` (offscreen at x≈-9755) and hidden `#infoInput`
     (0×0 at y≈-9789). A naive “first text input” strategy fills a honeypot.
   - **agreements** are not static markup: loaded via `GET /api/account-api/agreements/17` (200) and named
     `agreement<id>-<id>`; captcha metadata via `GET /api/recaptcha/recaptcha/next-register` (200) and
     `POST /api/captcha/challenges?client_id=rejestracja.poczta.interia` (200, preflight OPTIONS 200).
   - labels for Nazwisko are rendered via CSS `::before` content (“Nazwisko”), so `label.textContent` is empty.
6. **HTTP statuses observed**: document 200; `main.202611031334.css` 200; `main.202611031334.js` 200;
   `GET /api/recaptcha/recaptcha/next-register` 200; `POST /api/captcha/challenges?...` 200;
   `GET /api/account-api/agreements/17` 200; fonts/logos 200. No 403/429/5xx, no challenge page.
7. **Timings**: first-paint / FCP **896 ms**; navigation entry `duration≈1955 ms` (DOMContentLoaded+load);
   the form is interactive ~1.5–2 s after navigation; the consent modal appears within that window and
   covers the form; custom-select option lists animate open (~200–300 ms) — wait for
   `ul.account-select__options.visible` before clicking an `li`.

---

## (d) What broke vs the old automation (`sites/interia.py`)

1. **`__deal_with_cookies()`** clicked `/html/body/div[3]/div[2]/button[3]`. The consent layer is now a
   full-screen modal with `rodo-popup-*` classes and `aria-label` buttons, inserted as a different body
   child; the old XPath matches a footer/marketing element or nothing.
2. **`__deal_with_name/surname`** used `/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[1|2]/input`.
   The form is now inside `.register-form` with CSS-module hashed wrappers, and those inputs carry
   **random ids/names per load** — any selector keyed on `id`/`name`/absolute index breaks on the next run.
3. **Field order changed**: old code assumed `div[5]` = Nazwa konta, `div[3]` = birthday, `div[4]` = gender.
   Current order is Imię, Nazwisko, birthday (day/month/year), gender, Nazwa konta + domain, password,
   repeat — and the local-part field is *after* the date/gender group.
4. **`__remove_gambling_ads()`** (`…/div[2]/div[1]/div[2]/div[4]/label`) — that gambling-ads consent no longer
   exists. Current agreements are accept-all + marketing + personal-data marketing + Regulamin.
5. **`__deal_with_month/gender`** used `find_element_by_class_name("account-select__options")` +
   `account-select__options__item`. Those class names **still exist** (good news), but the trigger is a
   `.account-select` container with a hidden `input.fake-input`, and the list only exists while open
   (`ul.account-select__options.visible`); old code clicked a positional container that has moved.
6. **Honeypots**: `input.input--fake` / `#infoInput` / `.fake-input` are new decoys. Old positional
   `form/div[1]/div[1]/input` type code can land on a decoy.
7. **Selenium 3 APIs** everywhere (`find_element_by_xpath`, `find_element_by_class_name`), plus
   `webdriver.Chrome(ChromeDriverManager().install(), options=...)` and `options.headless = True` — all
   removed/deprecated in Selenium 4 (`By.*`, Selenium Manager, `--headless=new`).
8. **Assumption that clicking submit ≈ account created** is now false: submit runs reCAPTCHA + an image
   captcha step + SMS/mail verification steps (bundle evidence).

---

## (e) Recommended stable selector strategy

1. **Dismiss consent first** with `button[aria-label="Przejdź do serwisu"]` (or “Przypomnij później”) and
   `WebDriverWait` for the modal to disappear before touching the form.
2. **Resolve the randomised inputs at runtime** instead of trusting ids/names:
   - Option A (robust): collect visible text inputs
     `[e for e in driver.find_elements(By.CSS_SELECTOR, "form input[type=text]") if e.is_displayed() and e.id not in ("infoInput",) and "input--fake" not in (e.get_attribute("class") or "")]`
     → order is `[Imię, Nazwisko, Nazwa konta]` (birthday fields have class `account-input`, so exclude them,
     or slice accordingly).
   - Option B (semantic): `label[for]` → id → element. First name:
     `//form//div[label[normalize-space(.)='Imię']]//input`; account name:
     `//form//div[label[normalize-space(.)='Nazwa konta']]//input`; surname: the label is empty and painted via
     `::before`, so use `//form//label[contains(@class,'RMii')]/@for` or the 2nd visible text input.
3. **Stable ids** where they exist: `#birthdayDay`, `#birthdayYear`, `#password`, `#rePassword`.
4. **Custom selects**: click the container (`div.account-select` scoped by its label text, e.g.
   `//div[contains(@class,'account-select')][.//label[normalize-space()='Miesiąc']]`), wait for
   `ul.account-select__options.visible`, then click the `li.account-select__options__item` whose
   `.account-select__options__label` text matches (`Styczeń`, `Pan`, `interia.pl`, …).
5. **Checkboxes are 0×0 inputs inside labels** — click the `label.checkbox-container` (or the input via JS
   `click()`); select by `name`: `agreementacceptAll-acceptAll`, `agreement31-122`, `agreement30-121`,
   `agreement74-213` (Regulamin = the legally required one). Assert `is_selected()`.
6. **Never rely on `.input--fake`/`#infoInput`**; explicitly exclude them and assert each fill landed in a
   visible element with `x > 0`.
7. **Submit is a hard stop for automation** until captcha handling exists: reCAPTCHA Enterprise invisible +
   image captcha + SMS/mail verification. Assert form validity, then hand off / pause.

### Does Interia still offer a free @interia.pl account? — evidence

Yes:
- plan chooser card **“Darmowe” — “0,00 zł”** with its own `WYBIERAM` link (`a[href="#/nowe-konto/darmowe"]`);
- the free form header reads “Twój wybór: Konto Darmowe / Możesz zmienić w trakcie użytkowania”;
- the domain selector defaults to **`interia.pl`** and the submit button reads **“ZAŁÓŻ DARMOWE KONTO”**;
- the page offers a separate “Przejdź do rejestracji konta płatnego” path for paid accounts.

**Uncertain — free-plan domain restriction.** On the free form the domain list shows all 12 domains
(interia.pl, poczta.fm, interia.eu, interia.com, intmail.pl, interiowy.pl, adresik.net, pisz.to,
vip.interia.pl, pacz.to, ogarnij.se, własny_adres.hub.pl), but every item carried the `unavailable` class
while “Nazwa konta” was empty, so that class reflects **local-part availability at that moment**, not plan
entitlement. The data does not confirm or refute “free plan = interia.pl only”; that must be re-tested by
typing a local part and re-opening the dropdown (one read-only check, not performed here).
