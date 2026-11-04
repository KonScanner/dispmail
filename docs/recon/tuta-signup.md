# Tuta (formerly Tutanota) — live signup recon

Recon date: 2026-11-03 (Europe/Athens), headless Chromium 1920×1080, read-only.
Nothing was submitted: no account was created, no password was typed, no captcha solved.

Artifacts (this folder):
- `tuta-step-1.png|html` — plan selection, default selection = Legend (paid)
- `tuta-step-2.png|html` — Free plan selected
- `tuta-step-3.png|html` — account form (step 2 of the wizard)
- `tuta-step-4-domain-menu.png|html` — domain dropdown open
- `_raw/tuta-step-*.json` — per-step control inventory (attributes, rects, selector candidates, meta/timing)
- `_raw/tuta-step-*-meta.json` — URL/title/performance snapshot per step

---

## (a) Current flow

**Entry point / redirects**

| URL | Result |
|---|---|
| `https://app.tuta.com/signup` | **HTTP 302** → `Location: https://app.tuta.com/?r=/signup` |
| `https://app.tuta.com/?r=/signup` | **HTTP 200**, page renders; SPA then rewrites the address bar back to `https://app.tuta.com/signup` |
| `https://app.tuta.com/` | HTTP 200 (login screen) |
| `https://tutanota.com/` | **HTTP 301** → `https://tuta.com/` (marketing site) |
| `https://tuta.com/signup` | **HTTP 404** — there is no marketing-site signup page |

So the real current entry point is **`https://app.tuta.com/signup`** (302 → `/?r=/signup` → 200), and the
final URL once the app boots is `https://app.tuta.com/signup`. Page title: **“Tuta: Login & Sign up for free”**.

**Stack**: React SPA (`window.tutao` global, `#root`, React root element; no framework markers for
Angular/Vue). ESM chunks loaded on demand (~30 script requests). **No iframes, no shadow DOM, no cookie
banner.** x-frame-options: DENY, x-content-type-options: nosniff, no Cloudflare headers.

**Visible signup path (all in one URL, modal state machine):**

1. **Plan selection** (`#plan-selector`, `[data-testid="dialog:select-subscription"]`).
   Three cards `.buyOptionBox-v2`: *Revolutionary* (€3.60/yr or €3/mo, 20 GB), *Legend* (€9.60/yr or €8/mo,
   500 GB, **selected by default**), *Free* (€0, 1 GB, one calendar, FAQ support, “Your free account will be
   deleted if you don't login for 6 months”). Buttons: `Back`, `Business use`, `Continue`.
2. **Free plan selected** → card 3 radio becomes `checked`. `Continue` advances (no URL change).
3. **Create Account form** inside `#signup-account-dialog`: Username + domain dropdown, Set password,
   Repeat password, 2 mandatory agreements, `Create account` (disabled until both checkboxes are ticked).
   Sidebar still shows the three plan cards, Free constraints, and `See other plans`.
4. **Recovery Kit** — step 3 of the wizard, reached only *after* clicking `Create account`.
   **Observed after this rewrite** (from the account's Settings → Login → Recovery code dialog,
   which uses the same component): the code is **64 hexadecimal characters in 16 groups of
   four**, shown over four lines, for example `fa54 7805 6b94 bfca / 4d3c ...`. The dialog
   has `Copy Recovery Code`, `Download PDF-file` and `Ok`. The code is shown after a password
   confirmation. Step names found in the signup bundle:
   `Select Plan`, `Create Account`, `Recovery Kit`, `Order Confirmation` (free skips Order Confirmation).

**Wizard step indicator**: `button[aria-label="Free"]` (done, check icon), `button[aria-label="Create Account"]`
(current), `button[aria-label="Recovery Kit"]` (`disabled="true"` until step 3 is reached).

---

## (b) Step table — every control with a Selenium-usable selector

Legend: ✅ stable (semantic attribute) · ⚠️ medium (structure/label text) · ❌ position-dependent.

### Step 1 — plan selection

| Control | Label / visible text | Attributes | Selector (Selenium 4) | Stability |
|---|---|---|---|---|
| Plan radio ×3 | Revolutionary / Legend / Free | `input type=radio name="BuyOptionBox"`, `class="m-0 big-radio"`; **no id, no value, no aria-label** | `#plan-selector input[name="BuyOptionBox"]` → 3 matches, **index 2 = Free** (0=Revolutionary, 1=Legend) | ⚠️ index order = visual order; verify `checked` after click |
| Free card container | “Free”, “1 GB storage”, “One calendar”, “FAQ support” | `.buyOptionBox-v2` (3rd), inside `#plan-selector > div:nth-of-type(2)` (cards 1–2 share `div:nth-of-type(1)`) | `#plan-selector > div:nth-of-type(2) .buyOptionBox-v2` or `.buyOptionBox-v2:last-of-type` | ⚠️ |
| Yearly/Monthly switch | Yearly · Monthly | `label[aria-label="\u2008"]` (thin space!) containing `input[type=checkbox][role=switch]` | `#plan-selector label[aria-label] input[role="switch"]` | ⚠️ aria-label is a whitespace char |
| Back | “Back” | `data-testid="btn:back_action"` | `button[data-testid="btn:back_action"]` | ✅ |
| Business use | “Business use” | `data-testid="btn:businessUse_action"` | `button[data-testid="btn:businessUse_action"]` | ✅ |
| Continue | “Continue” | `data-testid="btn:continue_action"`; **no `disabled` attribute at any point** | `button[data-testid="btn:continue_action"]` | ✅ |

Plan names/prices shown: Revolutionary **€3.60** (yearly) / **€3** per month, 20 GB · Legend **€9.60** / **€8**,
500 GB · Free **€0**, 1 GB, “Only 1 free Account per person”, “No extra email addresses”, “Account will be
deleted after 6 months if not logged into”.
Yearly/Monthly toggle is present (`input[role=switch]`, checked=false) but both price pairs are rendered
simultaneously in the DOM; only the active pair is visually emphasised.

### Step 2 — Free selected

Same page; radio 3 becomes `checked`, `Continue` remains enabled and advances to the account form.
Verified: `document.querySelectorAll('#plan-selector input[name=BuyOptionBox]')` →
`[false, false, true]`, then `Continue` click → `#signup-account-dialog` present.

### Step 3 — Create Account form (`#signup-account-dialog`)

| Control | Label / hint | Attributes | Selector | Stability |
|---|---|---|---|---|
| Username | “Username” (hint below: “Enter preferred email address”) | `input`, `aria-label="Username"`, `data-testid="tfi:username_label"`, `autocomplete="new-password"`, `autocapitalize="none"`, class `input  text`; **no id, no name, no placeholder attr** | `input[data-testid="tfi:username_label"]` or `input[aria-label="Username"]` | ✅ |
| Domain button | `@tutamail.com` | `data-testid="btn:domain_label"`, shows current suffix | `button[data-testid="btn:domain_label"]` | ✅ |
| Domain menu items | `tuta.com`, `tutamail.com`, `tuta.io`, `tutanota.com`, `tutanota.de`, `keemail.me` | `.dropdown-content[role="menu"]` → `button[role="option"][data-testid="btn:domain"][title="<domain>"]`, label = domain text; plus a `Close` button | `button[role="option"][title="tutanota.com"]` (or `[data-testid="btn:domain"]` + text) | ✅ title/role; ✅ testid |
| Set password | “Set password”, hint “Please enter a new password.” | `input type=password`, `aria-label="Set password"`, `data-testid="tfi:newPassword_label"` | `input[data-testid="tfi:newPassword_label"]` | ✅ |
| Reveal password | eye icon ×2 | `data-testid="btn:revealPassword_action"` | `button[data-testid="btn:revealPassword_action"]` (first = password) | ⚠️ duplicated |
| Generate password | “Generate password” | plain `<button class="hover click">`, **no testid/id** | `//button[normalize-space()="Generate password"]` | ⚠️ text only |
| Repeat password | “Repeat password” | `input type=password`, `aria-label="Repeat password"`, `data-testid="tfi:repeatedPassword_label"` | `input[data-testid="tfi:repeatedPassword_label"]` | ✅ |
| Agreement 1 | “I do not own any other Free Tuta account and I will not use this account for business.” | `input type=checkbox`, class `checkbox list-checkbox click`; **no id/name/aria/testid** | `//label[contains(.,"I do not own any other Free Tuta account")]//input[@type="checkbox"]` or `#signup-account-dialog > div > div:nth-of-type(3) > div:nth-of-type(1) input[type=checkbox]` | ⚠️ label text / structure |
| Agreement 2 | “I have read and agree to the following documents:” | same | `//label[contains(.,"I have read and agree")]//input[@type="checkbox"]` | ⚠️ |
| Terms link | “General terms and conditions” | `a` → `https://tuta.com/terms`, `target="_blank"` | `#signup-account-dialog a[href="https://tuta.com/terms"]` | ✅ |
| Create account | “Create account” | `data-testid="btn:create_new_account_label"`, **`disabled` until BOTH checkboxes ticked** | `button[data-testid="btn:create_new_account_label"]` | ✅ |
| Back | “Back” | `data-testid="btn:back_action"` | `button[data-testid="btn:back_action"]` | ✅ |
| See other plans | “See other plans” | `data-testid="btn:seeOtherPlans_action"` | `button[data-testid="btn:seeOtherPlans_action"]` | ✅ |
| Sidebar plan cards | names/prices as above | no testids; `#signup-view` text | read `#signup-view` innerText | ⚠️ |

Enablement detail (important for automation): `Create account` becomes enabled when **only the two
checkboxes** are ticked — with the username and both password fields empty, `disabled` was already `false`.
Client-side validation of username/password happens on submit, not on the button state.

### Username / domain validation observed in the UI

| Input typed | Message shown |
|---|---|
| `ab` | “Mail address is not valid.” |
| `Bad_Name With Space!` | “Mail address is not valid.” |
| `abc` | “Email address is not available.” |
| `recon.probe_x-1` | “Email address is available.” |
| `ReconProbeX7731` | “Email address is available.” (uppercase preserved, not lower-cased) |
| `recon+probe` | “Email address is not available.” (not “not valid” — `+` is rejected by the format check via the availability path) |

Conclusions: min length > 2 (2 chars = invalid format, 3 chars = format-valid), allowed characters observed
`[A-Za-z0-9._-]`, `+` and spaces rejected, no `maxlength` attribute, no auto-lowercasing. The exact allowed
character set is enforced server/JS-side — only these samples were tested.

---

## (c) Blockers / captcha / anti-bot

- **No CAPTCHA at any observed step**: no reCAPTCHA/hCaptcha/Turnstile DOM nodes, no iframes, no
  `challenges.cloudflare.com`; the signup chunk `signup-BtOQe-rm.js` contains **zero** occurrences of
  `captcha|recaptcha|hcaptcha|turnstile`.
- **No Cloudflare challenge / JS interstitial**; app page and chunks returned 200.
- **No cookie/consent banner** on app.tuta.com.
- Only “blockers” are UI state gates: Free plan not preselected (default = paid Legend), `Create account`
  disabled until both agreements are checked, and the DOM re-renders between steps (the `.buyOptionBox-v2`
  cluster and the Continue wrapper are replaced on plan change — stale element references fail).
- Whether a captcha appears **on submit** is unverified (we never submit). There is no evidence for one in
  the signup bundle.

**Timings** (same-session measurements): first-paint 176 ms, FCP 232 ms; the plan UI (`#signup-view`,
`btn:continue_action`) was already present when polled immediately after navigation settled (~2.5 s
including the CLI's load wait). Card selection animates (`scale`/`opacity`, ~200–300 ms); wait ~0.5–1 s
before clicking `Continue`. Navigation document: 302 then 200, ~310 ms TTFB/DOMContentLoaded in-page.

---

## (d) What broke vs the old automation (`sites/tutanota.py`)

1. **`__select_signup()`** clicked `/html/body/div/div[3]/div[2]/div/div[1]/div[2]/button[1]/div/div` — the old
   landing hero with a “Sign up” button no longer exists. `/signup` lands directly on the plan selector.
2. **`__select_free_version()`** used `/html/body/div/div[2]/.../div[5]/button/div` for the free card. The
   plan dialog is now `#plan-selector` (radios `name="BuyOptionBox"` + `data-testid` buttons); the free card is
   the 3rd `.buyOptionBox-v2` inside a different wrapper div, so the old path matches nothing.
3. **`__select_checkboxes()`** used `#modal > div:nth-child(2) > div > div > div > div:nth-child(2) > div:nth-child(1|2) > div > input[type=checkbox]`.
   `#modal` still exists but is `display:none` and empty during signup; the agreements now live in
   `#signup-account-dialog` and are wrapped in `<label>`. Old selectors hit hidden/absent nodes.
4. **`__deal_with_username/password_1/password_2`** depended on `#signup-account-dialog > div > div.text-field...`
   and `...div.flex-grow.rel > input` — the dialog markup is now flat (label + input + button), no
   `.text-field`/`.flex-grow` wrappers.
5. **Hard-coded domain**: old code assumed `@tutanota.com`; the default is now `@tutamail.com`, with six
   selectable domains (`tuta.com`, `tutamail.com`, `tuta.io`, `tutanota.com`, `tutanota.de`, `keemail.me`).
6. **`__deal_with_final_checkboxes()`** used `/html/body/div/div[2]/.../div[3]/div/input` and `/div[4]/div/input` —
   the two agreements are label-wrapped `input[type=checkbox]` with no id/name/aria; the absolute XPaths and
   the `div[3]`/`div[4]` indices are gone.
7. **`__save_recovery()`** read a positional div after account creation. The signup recovery
   screen was not reachable in this recon, but the same recovery-code component was observed in
   Settings: a 64-character hex code in 16 groups of four, with a `Copy Recovery Code` button.
   The rewrite extracts that pattern from the page text and waits up to
   `DISPMAIL_RECOVERY_TIMEOUT` (20 s) for it to render.
8. **Selenium 3 API usage throughout** (`find_element_by_xpath`, `find_element_by_css_selector`,
   `find_element_by_class_name`) — removed in Selenium 4; must use `find_element(By.XPATH, ...)`.
   `options.headless = True` is deprecated (`--headless=new`), and
   `webdriver.Chrome(ChromeDriverManager().install(), options=...)` is the old webdriver-manager style.
9. Fixed `t.sleep(1)`/`t.sleep(4)` + retry-until-click loop replaced by deterministic waits
   (`WebDriverWait` on `#signup-account-dialog`, `[data-testid="btn:create_new_account_label"]`).

---

## (e) Recommended stable selector strategy

1. Prefer `data-testid` — Tuta annotates every actionable button: `btn:back_action`,
   `btn:businessUse_action`, `btn:continue_action`, `btn:domain_label`, `btn:domain`,
   `btn:revealPassword_action`, `btn:create_new_account_label`, `btn:seeOtherPlans_action`, and the fields
   `tfi:username_label`, `tfi:newPassword_label`, `tfi:repeatedPassword_label`.
2. For the two agreements use **label text** (the only handle): `//label[contains(., "I have read and agree")]//input`.
   Click the `input`, not the label, and assert `.is_selected()`; if a click is swallowed, click the label
   element (the input is 14×14 px inside it).
3. Radio selection: `#plan-selector input[name="BuyOptionBox"]` and pick by **checked state / index 2**, then
   assert `checked == True` before clicking `Continue` (index order is visual order, no `value` attributes).
4. Never use positional `/html/body/...` XPaths. The page is a single-URL SPA: wait on element presence
   (`#plan-selector` → `#signup-account-dialog`), not on URL changes.
5. Watch CSS attribute-selector quoting: values contain `:` (`btn:continue_action`). Unquoted
   `[data-testid=btn:continue_action]` is an **invalid selector** in JS/CSS — always quote:
   `[data-testid="btn:continue_action"]`.
6. Re-query elements after every step: selecting a plan re-renders the Continue wrapper and card cluster, so
   stale `WebElement` handles raise `StaleElementReferenceException`.
7. Do **not** type into `Generate password` — it mutates the password field with a generated value; if the
   flow must stay deterministic, ignore it and set the password explicitly.

### Free plan without phone number / recovery email — evidence

Yes. The entire signup form (step 3) contains only: username + domain, password, repeat password, 2
agreements (free-account ownership, terms). **No phone number and no recovery email field** exist in the
form (`_raw/tuta-step-3.json` control inventory: 3 text/password inputs + 2 checkboxes + buttons only).
The “Recovery Kit” is step 3 of the wizard, i.e. issued **after** account creation, per the step indicator
and bundle step names. A free account is constrained to “Only 1 free Account per person”, “No extra email
addresses”, and is deleted after 6 months without login (shown on the plan card).
