# DispMail documentation site — design

2026-11-04. Status: awaiting approval.

## Intent

`https://konscanner.github.io/dispmail/` serves a 2021 static viewer. `index.html` and
`js/main.js` read `accounts.txt` in the browser; nothing writes that file since accounts
moved to SQLite, so the page renders empty. It also pulls `w3.css` from `w3schools.com`.

Replace it with documentation for people who value their own privacy: what the tool does,
how to install and run it, what it stores, and where its limits are. Serious tone, plain
wording, no marketing.

## Goals

- Explain the tool in plain language before any technical detail.
- One path: install, run, read accounts, understand limits.
- Depth on demand: flags, exit codes, egress rules, provider differences.
- Sober design: one accent colour, system fonts, generous spacing, light and dark.
- No external requests at runtime: no CDN, no web fonts, no analytics, no cookies.
- Markdown stays the single source. GitHub Pages builds it. No CI, no local toolchain.
- Keep repo-only material out of the published site (recon snapshots, this design).

## Non-goals

- Not a marketing page: no provider screenshots, no "anonymous" claims.
- No blog, changelog, comments, or analytics.
- No custom Python/MkDocs build pipeline.
- No CI workflow.
- No custom domain.

## Anti-goals

- A site that loads third-party assets or tracks readers.
- Copy that overstates what the tool guarantees.
- Documentation drifting from the CLI (flags, defaults, exit codes).
- Published files containing credentials, emails, or egress addresses.

## Constraints

- Pages uses the legacy builder. Source becomes `main /docs`; Jekyll 3.9 compiles it.
- Theme: `just-the-docs` via `remote_theme`, the only theme with built-in nav, search and
  dark mode that builds on Pages without a CI workflow.
- Project toolchain stays Python 3.14.8 + uv. The site build adds no local dependency.
- `data/` is gitignored and never published.
- Plan documents stay at `docs/*.md`; their relative links must keep working.

## Approaches

| Approach | Trade-off |
|----------|-----------|
| **Jekyll on Pages + `just-the-docs`** (chosen) | No CI, no local toolchain, search and nav built in. Look is a clean docs theme, not bespoke. |
| MkDocs Material | Better defaults, but needs a GitHub Actions workflow or a manual build and push to `gh-pages`. |
| Hand-rolled generator | Full design control, but we own navigation, search and layout indefinitely. |

Chosen because it keeps markdown as the source, adds no build step, and satisfies
"serious and simple".

## Site map

| Page | File | Content |
|------|------|---------|
| Home | `docs/index.md` | What it is, what it does not do, quick start, where to go next |
| Install | `docs/install.md` | Requirements, `uv sync`, `dispmail doctor` |
| Usage | `docs/usage.md` | Dry run, live run, assisted run, flags, `read` commands |
| Providers | `docs/providers.md` | Tuta and Interia: state, requirements, terms |
| Egress | `docs/egress.md` | Why the egress check exists, VPN and proxy modes, fail-closed behaviour |
| Account data | `docs/data.md` | What is stored where, permissions, masking, make targets |
| Safety and limits | `docs/safety.md` | Weekly limits, cooldowns, CAPTCHA policy, exit codes |
| Development | `docs/development.md` | Layout, `make check`, tests, contract snapshots, no CI |
| Design | `docs/design.md` | Overview page, children are the three plan documents |
| Design: e2e | `docs/plan-e2e.md` | Existing document, gains front matter |
| Design: egress | `docs/plan-egress-fingerprint.md` | Existing document, gains front matter |
| Design: providers | `docs/plan-provider-rework.md` | Existing document, gains front matter |
| Recon | `docs/recon/` | Excluded from the build; stays in the repository |

Navigation order: Home 1, Install 2, Usage 3, Providers 4, Egress 5, Account data 6,
Safety 7, Development 8, Design 9.

## Look

- `just-the-docs` with a minimal `docs/_sass/custom/custom.scss`: one steel accent,
  system font stack, slightly tighter heading scale, comfortable line length.
- Light and dark schemes kept.
- `search_enabled: true`, `nav_sort: case_insensitive`, GitHub link in the header.
- Titles short: "Install", not "How to Install DispMail Today".

## Decisions taken

- Delete `index.html`, `css/style.css`, `js/main.js`. They are dead and cannot serve the
  SQLite store.
- `docs/_config.yml` holds the theme and excludes `recon/` and `superpowers/`.
- README keeps the GitHub entry point and links to the site instead of duplicating it.
- Switch the Pages source to `main /docs` with the API, trigger a build, verify the
  published URLs.
- Plan pages get `parent: Design` front matter; their bodies are unchanged.

## Builder's calls

- Exact accent hex, spacing scale, and whether the home page carries a short "why this
  exists" paragraph. Default: yes, one paragraph.
- Keep page titles noun-only.

## Verification

1. Local Jekyll build if the gem installs cleanly (Ruby 3.3.8 is present); otherwise the
   Pages build log is the build check.
2. Screenshot home, one content page, and one plan page in light and dark.
3. Grep built HTML for external `http(s)://` asset references.
4. `make check` still passes.
5. After deploy: fetch the site root and each page, check navigation, search, and that
   `recon/` and `superpowers/` return 404.

## Out of scope

Custom domain, versioned docs, analytics, comments, i18n.
