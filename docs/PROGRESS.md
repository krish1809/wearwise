# Progress

The running state of the project, updated at the end of every slice. Keep it short and current.

## Now

- **Last updated:** 2026-10-21
- **Current milestone:** M11 Hardening and launch, built on `m11-hardening` and waiting for your commit and merge. After it: v1.0 once the golden set and wear test (M5) pass, and anything you choose next.
- **Current slice:** none open; all eight M11 slices are built.
- **Next action (owner):**
  1. Commit `m11-hardening`, push it, open its pull request, and merge once CI passes (CI now also runs the end-to-end tests). Render runs the three new migrations on deploy.
  2. In Render, wearwise-api > Environment, add `ADMIN_EMAILS` with your account's email, so `/admin` (the owner's page of counts) opens for you. Check that the service's start command now includes `python -m scripts.housekeeping` (it comes from `render.yaml`).
  3. Once it's live, open the site and press "Try the demo". Then, in GitHub, Actions > "End-to-end against production" > Run workflow (or `E2E_BASE_URL=https://wearwise-rouge.vercel.app make e2e` locally): all tests must pass against production, the last "Done when" item of M11.
  4. Still open from earlier: switching the stylist on (Render settings in D47), `make eval-stylist` and tagging 30 photos, the "Weather service unavailable" log line, the golden set and wear test (M5), and the demo catalogue's licence. Password reset by email needs an email provider; tell me if you want one and which.

M1 slices:

| # | Slice | State |
|---|---|---|
| 1 | Design tokens and fonts (`frontend/app/globals.css`, `frontend/app/layout.tsx`) | done |
| 2 | Components in `frontend/components/ui/` and the development-only `/styleguide` page | done |
| 3 | Design review at 375 px and 1440 px | approved 2026-10-12, with a stronger input border (D20) |
| 4 | Auth backend: users and sessions, register, log in, log out, current user, rate limits | done |
| 5 | Register and log-in pages; protected pages redirect to log in | done |
| 6 | App shell: sidebar, phone tab bar, avatar menu | done |
| 7 | Landing page | done |
| 8 | Account deletion with typed confirmation | done |

M2 slices:

| # | Slice | State |
|---|---|---|
| 1 | Reference tables and the seed script; `GET /api/v1/reference` | done |
| 2 | Profile, brand notes, onboarding finish and reminder routes; name editing | done |
| 3 | Shared section forms; units and money helpers | done |
| 4 | Onboarding: six steps with Back, Skip, Continue, and Skip all | done |
| 5 | Settings tabs (Profile, Style, Budget, Brands, Account) and the Home reminder | done |
| 6 | Browser walkthrough at 375 px and 1440 px | done |

M3 slices:

| # | Slice | State |
|---|---|---|
| 1 | Categories (seeded and custom) and the rest of the taxonomy lists in the database | done |
| 2 | Items API: create with category defaults, edit, archive, delete, status, matching sets, filtered and searched pages | done |
| 3 | Photos: storage adapter (folder, R2, memory), checks, EXIF removal, resizing, dominant colour | done |
| 4 | Wardrobe grid: search, filter rail and sheet, removable chips, sort, load more | done |
| 5 | Add, edit, and item pages; custom categories page | done |
| 6 | Demo wardrobe script; browser walkthrough; docs | done (your own 25 to 30 items: after deploy) |

M4 slices:

| # | Slice | State |
|---|---|---|
| 1 | Outfit templates from the seed; template rules in the engine; slot roles | done |
| 2 | Outfits API: save, check, edit and swap, favourite, duplicate, delete; removed pieces | done |
| 3 | Wear log API: log an outfit or loose items, edit, delete; recounted wears since wash | done |
| 4 | Outfit board, studio, finishing touches | done |
| 5 | Outfits list and page, wear log pages, item wear details, Home's Today card | done |
| 6 | Browser walkthrough at 375 px and 1440 px; docs | done |
M5 slices:

| # | Slice | State |
|---|---|---|
| 1 | Engine types and config (`app/engine/config.py`, `types.py`), `ENGINE_VERSION` | done |
| 2 | Pair score: OKLCH colour table, formality, pattern, fabric and season, style | done |
| 3 | Outfit score: slot-pair weights, mean plus worst, outfit adjustments | done |
| 4 | Context score: occasion, season standing in for weather, rotation, preference, style | done |
| 5 | Generation: hard filters, templates, enumeration and beam search, anchors | done |
| 6 | Accessories, diversity, reasons and their sentence file | done |
| 7 | Service and API: wardrobe loading, pair cache, stored suggestions, `POST /outfits/suggest` | done |
| 8 | UI: Suggest page, "What goes with this?", "Complete this outfit", reasons on outfits, Home | done |
| 9 | Feedback: like, dislike with a reason, skip, save, wear; replayed into ranking | done |
| 10 | Golden set: export script, labelling format, agreement test | done (labels: yours) |
| 11 | Missing pieces: which slot and why, a flagged compromise, honest notes | done |

M6 slices:

| # | Slice | State |
|---|---|---|
| 1 | Weather adapter (Open-Meteo, fake), forecast cache per place per day, place search, manual setting | done |
| 2 | Weather in the engine: temperature bands, rain from the forecast, cold traits; engine 1.1 | done |
| 3 | Events and the usual week; a day's occasion | done |
| 4 | Planner: beam search over days, laundry simulation, repeat rules, locked days | done |
| 5 | My Week page: seven days, swap, lock, plan again, mark as worn | done |
| 6 | Laundry view and "Laundry done" | done |
| 7 | Trips and packing lists; packed items leave suggestions | done |
| 8 | Home: today's weather and planned outfit; footer credit | done |

M7 slices:

| # | Slice | State |
|---|---|---|
| 1 | Engine: distinct good outfits, versatility, orphans and their rescue, coverage, worn style; stricter style match, engine 1.2 | done |
| 2 | Service and API: wear counts, rankings, cost per wear, months, kinds, colours, declutter; `GET /insights`; measures cached per wardrobe | done |
| 3 | Insights page: wear, value, versatility, coverage, worn style, declutter; text alternatives for every chart | done |
| 4 | Navigation and Home's one insight; logged-out visitors sent to log in | done |
| 5 | Browser walkthrough at 375 px and 1440 px; docs | done |

M8 slices:

| # | Slice | State |
|---|---|---|
| 1 | Engine: what a candidate adds, likeness, the verdict, gaps with whole first outfits, the starter capsule, the budget split; a good outfit dressed at the occasion's level | done |
| 2 | Data: staples and Style Guide text in the database, candidates, photos for candidates; one migration | done |
| 3 | Service and API: candidates, analysis stored by key, compare, gaps, capsule, budget split, buying, the guide | done |
| 4 | Shopping pages: the list and gaps, add and edit, a candidate and its analysis, compare, budget split, starter plan | done |
| 5 | Style Guide: fabrics, styles, colour basics, brand notebook; navigation with More on phones | done |
| 6 | Browser walkthrough at 375 px and 1440 px; docs | done |

M9 slices:

| # | Slice | State |
|---|---|---|
| 1 | Adapters: shop search links; a page reader for one pasted link (robots.txt, public addresses only, limits) with a fake | done |
| 2 | Data: `link_previews`, `catalog_products`, candidate pictures; the demo catalogue loader and `make catalog` | done |
| 3 | Service and API: read a link (cached a day), suggestions from the page's words, shop searches and ranked demo products, candidates from links and the catalogue | done |
| 4 | UI: "From a link" on the add page, "Find it" from staples and candidates, the shop's picture, source and "may have changed" | done |
| 5 | Browser walkthrough at 375 px and 1440 px; docs | done |

M10 slices:

| # | Slice | State |
|---|---|---|
| 1 | Provider interface (`adapters/ai/`): the real provider over HTTPS, a scripted fake, and off; settings with prices and a daily cap | done |
| 2 | Data: chat threads, messages (cards, tools, ids seen), proposals, daily usage; one migration | done |
| 3 | Photo tagging with the app's own choices only; usage limits and spend | done |
| 4 | The stylist: tools over the app's own services, the `reply` tool, the grounding check, proposals confirmed in the app | done |
| 5 | UI: the Stylist page (conversations, cards, confirm), "Fill in from the photo", navigation only when switched on | done |
| 6 | Tests for the evaluation's plumbing, `make eval-stylist` for the real model, browser walkthrough, docs | done |

M10b slices:

| # | Slice | State |
|---|---|---|
| 1 | Dark theme from the tokens, the theme choice in the account menu, a contrast test for both themes | done |
| 2 | Quick jump (Ctrl or Cmd + K), and Undo on archive, skip, and conversation delete | done |
| 3 | Swipe suggestions on phones, sending what Like and Dislike send | done |
| 4 | The studio's tray: drag a piece onto the board or press it, with a live score and its reasons | done |
| 5 | The colour map, and coverage squares that open to their outfits or what's missing | done |
| 6 | Try a candidate on with pieces you own | done |
| 7 | Sleep on it, Wear what you own, and Remix; one migration | done |
| 8 | Browser walkthrough at 375 px and 1440 px in both themes; docs | done |

M11 slices:

| # | Slice | State |
|---|---|---|
| 1 | Security: route audit, a budget for changes, headers on both apps, photo decoders, the log-in redirect, dependency audit | done |
| 2 | Privacy: download my data, a check that deletion leaves nothing, the privacy page | done |
| 3 | Observability: request ids, structured logs, errors recorded on both sides, an owner-only page of counts | done |
| 4 | Demo: "Try the demo" gives each visitor a fresh copy, removed after a day | done |
| 5 | Accessibility pass | done |
| 6 | Performance pass | done |
| 7 | End-to-end tests for the five main journeys, runnable against production | done |
| 8 | README: screenshots, architecture diagram, the engine in brief, known limitations | done |

- **Overall:** all 13 milestones built (M0 to M11), 12 released (M0 to M10b). v1.0 (M0 to M5) waits on the golden set and the wear test. v1.0 (M0 to M5) waits on the golden set and the wear test.

Live:

| What | Where |
|---|---|
| Web app (Vercel) | https://wearwise-rouge.vercel.app |
| API (Render, Singapore) | https://wearwise-api-kzj4.onrender.com (the app reaches it through `/api/*`; `/docs` shows the API) |
| Database (Neon, Singapore) | Postgres 18; connection strings live only in Render's environment settings |

## Starting a new session

1. Read this file first.
2. Read the section of `docs/ROADMAP.md` for the current milestone, including its "Done when" list.
3. Read only the docs that milestone needs. The README has a table of every doc and what it covers.

Rules that apply to every change:

- Work on the current milestone only. Don't build ahead.
- `backend/app/engine/` imports nothing from `api`, `models`, `services`, or `adapters`. It takes plain data and returns plain data (`docs/ARCHITECTURE.md`).
- Every query on user data filters by the session's user. Never accept a user ID from the client. A request for another user's row returns 404, and each milestone adds a two-user test for its tables.
- No fake functionality and no invented data: no dead buttons, placeholder pages, made-up items, prices, or statistics (`docs/PRODUCT_SPEC.md` section 4).
- Categories, colours, occasions, style profiles, and archetypes come from `seed/` through the database. Never hard-code them (D5).
- Every schema change is an Alembic migration.
- External services (weather, AI, product sources) sit behind an interface in `adapters/` with a timeout, a fallback, and a fake for tests.
- The owner makes every commit, push, tag, and pull request by hand. A finished slice ends with a list of files to stage and a suggested commit message.
- After each slice, run lint, type checks, and tests, then update **Now** and **Log** in this file.

## Done so far

Planning and reference material, committed and pushed to `github.com/krish1809/wearwise` on `main` (commit `f34001e`):

| Area | What exists | Where |
|---|---|---|
| Product | Features by tier (Core, Next, Stretch), pages, principles, definition of done, success measures | `docs/PRODUCT_SPEC.md` |
| Plan | 12 milestones with build lists, "Done when" lists, and order rules | `docs/ROADMAP.md` |
| Architecture | Stack, module layout, auth and cookie proxy design, ownership, images, API conventions, testing | `docs/ARCHITECTURE.md` |
| Data | Starting schema for every milestone | `docs/DATA_MODEL.md` |
| Engine | Pair and outfit scoring tables, generation, diversity, reasons, quality checks, planner, packing | `docs/ENGINE.md` |
| Shopping | Purchase analyzer, verdict rules, gaps, capsule, budget split, product source rules | `docs/SHOPPING.md` |
| AI | Auto-tagging, Stylist tools, grounding check, evaluation set, cost controls | `docs/AI.md` |
| Design | Colour and type tokens, spacing, the outfit board, component list, navigation, writing rules | `docs/DESIGN_SYSTEM.md` |
| Hosting | Vercel, Render, Neon, R2; environments; migrations; release checklist | `docs/DEPLOYMENT.md` |
| Decisions | D1 to D17 | `docs/DECISIONS.md` |
| Seed data | 16 slots, 89 categories, 3 outfit templates; 28 colour families; 12 occasions; 12 style profiles; 66 archetypes; 3 sizing systems (added in M2). M2 loads colours, occasions, style profiles, category groups, sections, fits, and sizing systems; M3 loads the rest. | `seed/` |
| Config | Every environment variable up to M10, `.gitignore`, pull request template | `.env.example`, `.github/` |

M0 code, merged in pull request #1 and deployed:

| Area | What exists | Where |
|---|---|---|
| Backend | FastAPI app in the architecture's module layout; settings; one session per request; health route and service; `app_meta` table and its migration | `backend/app/`, `backend/alembic/` |
| Backend tests | Health ok and database down, missing variable, URL handling, and the rule that the engine imports nothing from the other layers | `backend/tests/` |
| Frontend | Next.js app whose home page checks the API through the `/api/*` proxy, waits up to 90 seconds for a sleeping backend, and offers "Try again" | `frontend/` |
| Frontend tests | Health mapping, retry while the server wakes, and the three messages the page can show | `frontend/lib/`, `frontend/components/` |
| Tooling | One `make` command per task, local Postgres, CI workflow, Render Blueprint | `Makefile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `render.yaml` |

**Carry into M1:**

- The error response shape from `docs/ARCHITECTURE.md` (`{"error": {...}}`) isn't wired up yet; add it with the first route that validates input.
- Tests only read so far. When M1's tests start writing, wrap each test in a transaction that rolls back.
- When rate limiting needs the client's IP, run uvicorn with proxy headers on Render.

## Milestones

| # | Milestone | You can now... | Status | Released | Notes |
|---|---|---|---|---|---|
| M0 | Foundations | open a live URL that talks to the API and database | done | 2026-10-12 | https://wearwise-rouge.vercel.app |
| M1 | Design system, shell, auth | register, log in, and move around a styled, empty app | done | 2026-10-16 | pull request #3 |
| M2 | Onboarding and profile | set (or skip) sizes, style, budget; edit them later | done | 2026-10-16 | pull request #3 |
| M3 | Wardrobe | add, find, edit everything you own, with photos | done | 2026-10-16 | pull request #3 |
| M4 | Outfit Studio and wear log | build and save outfits; log what you wore | done | 2026-10-16 | pull request #3 |
| M5 | Outfit engine (v1.0) | get ranked outfit suggestions with reasons | done | 2026-10-20 | pull request #4; v1.0 tag waits on the golden set and wear test |
| M6 | My Week | plan seven days with weather, laundry, events, packing | done | 2026-10-20 | pull requests #5 and #6 |
| M7 | Insights | see cost per wear, versatility, orphans, coverage | done | 2026-10-20 | pull request #7 (with M8) |
| M8 | Smart Shopping I | analyse a purchase; see gaps; plan a capsule on a budget | done | 2026-10-20 | pull request #7 |
| M9 | Smart Shopping II | find real products for a gap | done | 2026-10-20 | pull request #8 |
| M10 | AI | auto-tag photos; chat with a stylist that knows your wardrobe | done | 2026-10-21 | pull request #9; off until a key is set |
| M10b | Interaction and polish | drag outfits together, swipe suggestions, see your colours, and use a few new everyday tools | done | 2026-10-21 | pull request #9 |
| M11 | Hardening and launch | hand the link to anyone | built, not merged | | end-to-end run against production after deploy |

## Before M0 (only you can do these)

- [x] GitHub repo created and the docs pushed (checked 2026-10-11: local `main` matches `origin/main`)
- [ ] 25 to 30 photos of your own items taken (needed by M3)
- [x] Accounts: Vercel, Render, Neon (set up 2026-10-12)
- [ ] Backblaze account (needed by M3 for B2 photo storage; replaces Cloudflare, D33)
- [ ] Optional: applied for an affiliate or product API (only matters in M9)

**Local tools (checked 2026-10-11):** uv 0.12.23 (it installs Python 3.14 for the backend), Node 22.23.0, pnpm 10.34.6, Docker 29.8.0 with Compose v5.5.1, make 4.3, gh 2.45.0.

## Log

Add an entry per slice, newest first.

### 2026-10-21, M11 slice 8: the README, and a layout fix

- Built: the README rewritten for a stranger: what it is, the live link and "Try the demo", five screenshots (`docs/screenshots/`, from a throwaway account with drawn test photos), what it does, an architecture diagram, the engine in brief, the stack, testing, security and privacy, and the known limitations (moved here from this file). Fixed: the outfit studio on a phone was wider than the screen (the page grid had no column set, so the tray's long strip of pieces widened it; my M10b change); every main page now gets an explicit single column on small screens, and the accessibility sweep fails any page that scrolls sideways (it caught this one before the fix).
- Checked: README claims against the code and docs (the golden set is described as waiting on labels; the templates and filters as the engine has them). All 32 end-to-end tests pass, with the sideways check on twenty pages including an item's own page.

### 2026-10-21, M11 slice 7: end-to-end tests

- Built: `e2e/journeys.spec.ts`: sign up, add an item with a photo (a small drawn test image, so the suggested colour is known), build and save an outfit, get suggestions and like one, check a purchase, and delete the account. CI's new `e2e` job runs every end-to-end test against a fresh stack on each pull request; `.github/workflows/e2e-production.yml` runs them daily against the live site (and by hand). `make e2e`.
- Checked: all 32 end-to-end tests (journeys, accessibility, keyboard; desktop and phone) pass against a fresh database with CI's settings and a production build, in parallel, in 49 seconds, and leave no users behind. Not yet run against production: that needs this branch deployed.
- Decided: D54.

### 2026-10-21, M11 slice 6: performance pass

- Built: eight indexes on links to a person's data (suggestions to outfits and wear logs, reactions to items, planned days to wear logs, candidates to items, items and candidates to categories, proposals to their account), in one migration, and a test that every such link has one. Insights' measures saved in `saved_measures` (one row per person, under the measures' fingerprint), so they outlast the server's sleep.
- Checked: timings and query counts for a 300-item wardrobe, and at 60 and 120 items (D53); the index test (it passed without the indexes at first, because it counted the foreign keys themselves; fixed, then it failed without them and passed with them); measures are worked out once, read back after the memory is cleared, and worked out again after a wardrobe change. A per-scorer memo was tried, measured at 2% hits, and removed. JavaScript per page measured on a production build. The accessibility and keyboard suites (20 tests) pass against the production build. Backend 508 passed, 2 skipped.
- Decided: D53.

### 2026-10-21, M11 slice 5: accessibility pass

- Built: Playwright and axe for end-to-end tests (`@playwright/test` 1.64.0 and `@axe-core/playwright` 4.13.0, dev only, pinned to releases at least two weeks old; `pnpm e2e`, config in `frontend/playwright.config.ts`). `e2e/accessibility.spec.ts` runs axe (WCAG 2.1 A and AA) on the four public pages and fifteen app pages, in both themes, at desktop and phone size, from one demo per run. `e2e/keyboard.spec.ts`: the first Tab offers "Skip to content", every Tab stop on five busy pages shows a focus ring, and dialogs hold focus and give it back. Fixed: dialogs opened without a trigger (quick jump, a coverage square) dropped focus to the top of the page when they closed; the shared dialog now returns focus to wherever it was.
- Checked: axe finds nothing on 19 pages × 2 themes × 2 sizes; the scan was mutation-checked (an image without alt text planted after the page settles is caught, and each page is checked to be the page itself, drawn, in the right theme, with axe's own checks run). The keyboard checks, 16 across both sizes, pass; the focus-return check failed before the fix. Running the suites repeatedly showed the demo limit was too tight for a test run, so the tests now make one demo per size and the limit is ten an hour per address.

### 2026-10-21, M11 slice 4: the demo

- Built: "Try the demo" on the landing and log-in pages (`POST /auth/demo`, public, ten an hour per address): a fresh account per visitor with the menswear or womenswear staples and the profile in `seed/demo.json`, logged in at once, deleted a day later. A note on every page of a demo says until when, and links to making an account; Home greets a demo plainly instead of with its address. `scripts/housekeeping.py` (also `make housekeeping`) removes expired demos, unsaved photos, old error reports and rate-limit counts, and ended sessions; it runs in Render's start command. `demo_ends_at` and `created_at` on the user.
- Checked: a demo starts logged in with the section's staples, the demo profile, and suggestions ready; each visitor's copy is their own (another gets 404 for its items); limited per address; a demo over a day old goes with all its rows while a fresh one, a named demo, and real accounts stay; at most so many run at once, oldest out first; housekeeping removes only what has expired (and a session past its end logs out). In a browser at 1440 px (menswear) and 375 px (womenswear): from the landing page into Home with the note, the wardrobe's count, suggestions, and "Make your own account" to the register page. Two fixes from the screenshots: the demo label wrapped on a phone, and the wardrobe opened on toiletries.
- Decided: D52 (a copy per visitor instead of one account reset nightly).

### 2026-10-21, M11 slice 3: observability

- Built: a request id on every API call (sent by the browser, kept or made by the API, returned on every answer); JSON logs in production with one line per request (route pattern, status, milliseconds; no query string or IP address); unexpected errors logged, stored in `error_events`, and answered with a 500 that gives the reference; browser errors reported from the new error pages and any unhandled error (`POST /client-errors`, public, limited); `/admin`, the owner's page of counts, for `ADMIN_EMAILS` only. One migration (`error_events`).
- Checked: request ids made, kept, and replaced when they look wrong; an unexpected error is recorded with its route pattern and the end of its stack trace, answered with its reference and the usual headers, and shows nothing of what broke (the test caught that traces were being cut from the wrong end); one log line per request by route pattern; JSON lines; browser reports stored without the query, limited, and refused when too long; the owner's page is a 404 for anyone else, and acceptance counts each suggestion once. The route audit now has five public routes. In a browser at 1440 px and 375 px: another account gets "Page not found" (with a request id on the answer), and the owner sees the counts and a reported browser error.
- Decided: D51.

### 2026-10-21, M11 slice 2: privacy

- Built: "Download my data" in Settings > Account (`GET /account/export`: a zip with `data.json`, every photo, and a README; five an hour). `app/services/export.py` decides what's a person's from the schema, for the export and for deletion. The privacy page (`/privacy`, public), linked from the landing page, the app's footer, and the new "Your data" card. Rate-limit counts are deleted within a day; photos never saved with anything are cleared for everyone, not only on their owner's next upload.
- Checked: every table is a person's or shared; everything pointing at a user cascades; an account filled through the API exports every kind of row and its photo, without the password hash, sessions, or anyone else's rows; deleting it leaves none of its rows or photo files and leaves another account's untouched; downloads are limited; old rate-limit counts and day-old unsaved photos go (both tests fail without the change). In a browser at 1440 px and 375 px: the privacy page from the landing page without an account, the Your data card, and a real download whose zip holds the item and its photo. Backend 493 passed, 2 skipped; frontend 174 tests; lint and types on both.
- Decided: D50.

### 2026-10-21, M11 slice 1: security pass

- Built: `tests/test_route_audit.py` walks every route in the API's schema (97 today): 401 without a login outside four public routes, 403 for a change without the custom header, 404 for a made-up id. A budget of 1,000 changes an hour per person on every data route (`write_budget`). Security headers: a content security policy and the usual headers on the web app (`next.config.ts`), and a locked-down policy with no-store caching on the API (`app/api/middleware.py`). Pillow 13, and uploads opened with only the JPEG, PNG, and WebP decoders. The log-in redirect now refuses "/(tab)/elsewhere" and similar. `make audit` and a weekly audit workflow.
- Checked: the route audit, mutation-checked (taking health off the public list fails it; it first passed by walking no routes at all, which is why it now has a floor); headers on both apps and photos keeping their own caching; the budget refuses the next change with Retry-After, leaves reading alone, and is per person; the TIFF parser never sees an upload (fails without the change); the redirect bypasses. `make audit`: no known vulnerabilities in runtime packages (one development-only advisory, judged in D49). The M9, M10, and M10b browser walkthroughs pass against a production build with the new policy, with no console errors. Backend: 486 passed, 2 skipped.
- Decided: D49.

### 2026-10-21, M10b slices 1 to 8: interaction and polish

- Built: a dark theme from the same tokens (`:root[data-theme="dark"]`), with `on-ink` and `on-light` for text on filled shapes, chosen in the account menu (Like this device, Light, Dark) and applied before the page paints. Quick jump (Ctrl or Cmd + K): pages, actions, and your items. Undo toasts on archive, skip, and deleting a conversation. Swiping suggestions on phones (touch and pen only; reduced motion keeps the card still). The studio's tray: drag a piece onto the board or press it, with a live score meter and the engine's reasons (`/outfits/check` now returns them). The colour map (`/wardrobe/colours`, `GET /items/colours`). Coverage squares that open (`GET /insights/coverage/{occasion}/{season}`). "Try it with your pieces" on a candidate (`POST /candidates/{id}/try`). Sleep on it: remind me in a week, two weeks, or a month, and "Still want it?" on the shopping list on that day. Wear what you own: a 60-day challenge on Insights, counted from the wear log (`/insights/challenge`). Remix (`/outfits/remix`, `POST /outfits/remix`): the good outfits two to ten pieces make, per occasion, each one savable. One migration: `candidates.remind_on`, `profiles.challenge_started_on`.
- Checked: `make check`: backend 476 passed, 2 skipped (the golden set waits on your labels); frontend 168 tests; build. New tests: dragging equals pressing and the meter shows the score; swipes send what the buttons send, can be undone, and ignore scrolling and the mouse; quick jump finds and opens; every text pair passes contrast in both themes; colours, a coverage square (only your own occasions), and trying a candidate on (someone else's gets 404); a reminder must be after today and within a year, comes due on its day, and clears on skip or keep; the challenge counts only wear between its start and day 60, is per person, and stops; remix uses only the chosen pieces, and refuses one, eleven, or someone else's. A browser walkthrough at 1440 px and 375 px, light and dark: the theme kept after a reload, quick jump to Remix, Remix finding an outfit, the studio's live score, the colour map, the challenge started, a coverage square opened, a candidate tried on and slept on, and an archive undone; no console or server errors. The staged M10 snapshot was also checked on its own (backend 467 passed; frontend types, lint, 119 tests; API types current), so the two commits each pass.
- Decided: D48.

### 2026-10-20, M10 slices 1 to 6: the stylist and photo tagging

- Built: the provider interface in `app/adapters/ai/` with Anthropic's API (Claude Haiku 5.5, over HTTPS without an SDK), a scripted fake, and an off setting (the default); settings for the key, models, prices, and a daily spend cap, refusing the fake in production. `chat_threads`, `chat_messages`, `chat_actions`, and `ai_usage` in one migration. The stylist (`app/services/stylist.py`): sixteen tools over the app's own services, answers through a `reply` tool with cards by id, the grounding check (ids must come from this conversation's tools and still belong to the person; no ids in text; one retry, then an apology with the tools' own results), and proposals that wait for Confirm. Photo tagging with the app's own lists as the only choices. Limits: messages per minute and day, photos per day, lower for the demo account, and the daily cap before every call (D47). API: `/ai/status`, `/photos/{id}/tag`, `/chat/threads`, `/chat/messages`, `/chat/actions/{id}/confirm` and `/cancel`. Frontend: the Stylist page (conversations, example questions, replies with outfit, item, shopping-list, staple, and proposal cards, Confirm and Not now, "unavailable" with its reason), "Fill in from the photo" on the item form with every filled field marked, and the Stylist in the navigation only when switched on. `make eval-stylist` for the real model.
- Checked: `make check` (numbers below). Tests with scripted turns for each plumbing row of the evaluation table: an answer's cards resolve to real items; an invented id is sent back once and then replaced; a corrected reply is accepted; ids in text refused; another account's item can't be fetched or shown; nothing changes until Confirm (and not twice); an incomplete outfit isn't even proposed; an instruction planted in a shopping-list name gets nothing done; a provider failure leaves no messages or proposals but its tokens count; the spend cap and the daily limit; "more formal" gives a higher mean formality; a follow-up sees what the last reply showed; tagging keeps only the app's own ids, sends only the image, and counts it; ownership of conversations and proposals; results capped; login required. The settings refuse the fake in production and the real provider without its key, models, and prices. A browser walkthrough at 1440 px and 375 px with the fake provider's honest round trip: the Stylist from the navigation and from More, a question answered with three real item cards, the conversation kept and listed, and "Fill in from the photo" saying nothing could be read; no console errors.
- Not yet checked: the real model (needs your key): `make eval-stylist`, and tagging 30 of your photos.
- Decided: D47.

### 2026-10-20, M9 slices 1 to 5: Smart Shopping II

- Built: shop search links for a staple or a candidate (Myntra, AJIO, Flipkart, Amazon), with the usual spend beside them; a reader for one pasted product page (`app/adapters/pages.py`) that obeys robots.txt, reaches only public addresses (each address checked, the connection pinned to it, every redirect checked), and reads only link-preview data, cached a day in `link_previews`; suggestions for category, colour, and fabric from the page's own words; a demo catalogue (`catalog_products`) with a loader for the "Fashion Product Images" styles.csv (`make catalog file=...`), ranked by what each product would add (D46). API: `POST /links/preview`, `GET /shopping/shop`, `POST /candidates/from-catalog`; candidates take `source` ("manual" or "link") and the shop's `image_url`. Frontend: "From a link" on the add page (read, then check and save), "Find it" from every staple (its name) and from candidates without a link, the shop's picture shown from the shop, where each candidate came from, and "may have changed" on prices over a day old. One migration.
- Checked: `make check` passes. Reader tests against a local test server: product data from schema.org and Open Graph, robots.txt obeyed (including rules for WearWise by name), a missing robots.txt allows and an unreadable one refuses, private addresses refused (loopback, private ranges, link-local and the cloud metadata address, IPv6 loopback, shared address space, and a host with any private address), a redirect into a private network refused, size limits, non-pages, and refused pages without a retry. API tests: one read per page per day, a day later read again, blocked and unreachable pages answered rather than failed, failures remembered, a foreign price reported not converted, candidates from links and the catalogue, the loader's mapping and skips, demo products ranked and marked (every product shown has a link or is marked demo), the rate limit, a second account's candidate 404. A browser walkthrough at 1440 px and 375 px: a staple's "Find it" panel with the four shops and usual spend, pasting https://example.com/ (one real read, no product, the link kept), the candidate's source and noted price, and "Find it in shops" from a staple on the list; no console errors. Fixed while building: a link that couldn't be read was labelled "read from the page" with its typed price "checked"; it now counts as typed in.
- Not done: no demo catalogue is loaded, since the dataset's licence couldn't be confirmed (D46); no affiliate API (none applied for).
- Decided: D46.

### 2026-10-20, M8 slices 1 to 6: Smart Shopping I

- Built: the purchase analyzer in `app/engine/shopping.py`: a candidate fixed in place in each occasion and season, the good outfits that need it, coverage gain with diminishing returns, likeness to what's owned, matches, orphans rescued, cost per new outfit, and Buy, Consider, or Skip with reasons (D44). Gaps from the staples, with a whole first outfit for an occasion no single staple opens; the starter capsule, starting from a whole outfit when the wardrobe is empty; the budget split, every subset up to twelve candidates and greedy past that. A good outfit now has to be dressed at the occasion's level, in Insights as well (D44). `archetypes`, `guide_entries`, `candidates`, and candidate photos in one migration; the Style Guide's text in `seed/guide.json`. API: `/candidates` (add, from a staple, edit, delete, compare, analysis, purchase), `/shopping/gaps`, `/shopping/capsule`, `/shopping/split`, `/guide`. Frontend: Shopping (what would add the most, your list by status with verdicts, compare), add and edit, a candidate's page (verdict, the numbers, where it adds outfits, outfits it would make, what it goes with, "I bought it"), Split a budget, Plan a starter wardrobe, and the Style Guide (fabrics, styles with the staples you have, colour basics, brand notebook). The navigation gains Shopping and Style Guide, with More on phones (D45).
- Checked: `make check` passes. The shopping doc's required tests: an identical candidate is Skip and names the duplicate; opening an empty occasion beats adding to a full one; adding a candidate never lowers coverage, and matches a full recount on random wardrobes (hypothesis); the budget split never exceeds the budget and equals a brute force on random cases; the analysis is worked out again when the wardrobe changes. Also: greedy against the best (98% on average), the capsule from nothing, gaps with a whole outfit, an orphan rescued, accessories at most Consider, buying (item, photo, price paid), a candidate's photo kept out of reach of items, account deletion, category deletion, and a second account getting 404 on every route. Analysis on a 150-item wardrobe in about 0.2 s and its gaps in about 0.5 s on a laptop. The migration applies, rolls back, and reapplies with no drift. A browser walkthrough at 1440 px and 375 px: the More menu, gaps and adding a staple, the form, a candidate's verdict, a duplicate's Skip, compare, the budget split, the starter plan, buying, the Style Guide's tabs, and a logged-out visit sent to log in; no console errors. Fixed while building: casual outfits counting as interview outfits; the doc's 0.6 likeness ruling out any second pair of chinos; greedy stopping when an outfit needs two new pieces; pages wider than a phone (grids without a shrinkable column, and screen-reader text escaping a scroll area); Insights' cache missing the profile's styles and colours.
- Decided: D44 (good outfits and the analyzer), D45 (shopping list, Style Guide, navigation).

### 2026-10-20, M7 slices 1 to 5: Insights

- Built: the wardrobe graph in `app/engine/insights.py` (section 11 of the engine doc): good outfits (0.7 or more) for each of the person's occasions and seasons on the steady wardrobe (everything not retired counts as clean, nothing as worn lately), versatility counted over distinct core pieces with accessories counted by the outfits they finish, orphans (under two) with a one-sentence rescue, coverage, and the style worn (palette, formality mix, and matching styles, weighted by wears). The style match now needs one of a style's colours or categories (D42; engine 1.2). `app/services/insights.py` counts wears, last worn, cost per wear, days logged by month, wears by kind and colour, and declutter suggestions from the person's rows, and caches the measures per wardrobe version (D43). `GET /insights`. Frontend: the Insights page (most and least worn, days logged, what you wear, cost per wear with "Add a price", versatile and stranded pieces, the occasion by season table, the style you wear, "Worth a second look"), Insights in the navigation in place of Settings (still in the avatar menu), and one insight on Home that changes daily. No new tables, so no migration.
- Checked: backend tests against a fixture where every number is worked out by hand (wear counts, rankings, cost per wear, months, kinds, colours, palette, formality, coverage, orphan, declutter), the wait for five days logged, coverage waiting for occasions, a second account seeing only its own numbers, and a login required; engine tests for distinct outfits, accessories, orphans and each rescue, steady status, and the worn style. A browser walkthrough at 1440 px and 375 px (nine items, six days logged): Home's insight, the navigation, the whole Insights page, and a logged-out visit sent to log in; no console errors. Fixed while building: every style showed as 100% matched (D42); a rescue blamed the occasions when the partners clashed; "Add a price" and the item name ran together for screen readers.
- Decided: D42 (style match), D43 (Insights).

### 2026-10-20, M5 and M6 deployed

- Done: pull requests #4 (M5) and #5 (M6) merged; CI passed on `main`; Vercel and Render deployed (Render finished at 05:57 UTC, running both migrations and the seed).
- Checked on the live site, through Vercel, with a throwaway account (deleted afterwards): register; nine items; place search for Pune through the server (1.8 s); the profile's city and usual week; suggestions (10 outfits, engine 1.1, 0.6 s); a planned week (0.75 s; four days dressed, the last three explained, since four tops each needed a wash after one wear and no laundry day was set); wearing today; the laundry list; a three-day trip packed in five items. Not working: the forecast. Both Pune and Mumbai went by the season, failing in about a second (not a timeout), while the same request from a laptop answers in under a second; Render's free servers share outgoing addresses, so Open-Meteo's per-address limit is the likely cause. The app falls back as designed.
- Fixed after deploying: `/week`, `/laundry`, and `/trips` were missing from the pages that send a logged-out visitor to log in (the API refused their data, but the empty page loaded); a test now checks every logged-in section is listed. The message for a day the laundry blocks now suggests setting a laundry day.
- Left: the forecast on the live server (needs the log line), then M5's golden set and wear test.

### 2026-10-20, M6 slices 1 to 8: My Week

- Built: weather from Open-Meteo behind an adapter with a fake (`app/adapters/weather.py`), cached once per place per day and fetched outside any transaction, falling back to the person's manual setting and then the season (D39); place search for the city. The engine reads real weather (temperature bands, rain chance, cold traits from the seed; version 1.1). `events`, `plan_days`, `trips`, `trip_items`, `weather_forecasts`, category traits, and five profile fields in one migration. The planner (`app/engine/planner.py`): a beam search over days with the laundry simulation, no top twice in three days, no shoes three days running, locked days kept and looked ahead to, and a greedy plan as the floor (D38, D40). Packing lists (`app/engine/packing.py`, D41). API: `/places`, `/weather`, `/plan` (week, generate, change a day, options, wear), `/events`, `/laundry`, `/trips`. Frontend: My Week (seven day cards with weather, occasion, outfit, swap, lock, wear; your usual week; events), Laundry, Trips (list, plan a trip, packing list with packed marks and day-by-day outfits), the city search and "when there's no forecast" in Settings, Home's weather and planned outfit, My Week in the navigation, and the Open-Meteo and GeoNames credit in the footer.
- Checked: `make check` passes (ruff, mypy on 119 files, 351 backend tests with the 2 golden-set tests skipped, TypeScript, ESLint, Prettier, 101 frontend tests, build). The migration applies, rolls back, and reapplies with no drift. Tests cover the Open-Meteo client (parsing, a retry on server errors, none on bad requests, timeouts), one fetch per place per day, the manual and season fallbacks, a remembered outage, the temperature bands and cold rules, the planner's rules on random wardrobes (hypothesis) with locked days and laundry days, beam never worse than greedy, swaps that keep the week valid, packing within wears left, and every route's ownership. "Done when": a generated week has no repeated top and nothing past its wear limit; locking two days and planning again keeps them; with the weather service down, planning works on the manual setting. A browser walkthrough at 1440 px and 375 px against the real Open-Meteo: choosing Pune, the usual week, a wedding event, planning, lock, swap, plan again (locked and swapped days kept), wearing today, the laundry, a Jaipur trip with a festive day (packed, then deleted), and Home; no console errors. Fixed while building: the planner breaking a later locked day; day pools built on three tops; socks blocking whole outfits; a wedding packed with a casual shirt; grey placeholders instead of colour swatches in two lists.
- Left: the M5 items above.
- Decided: D38 (planner pools), D39 (weather), D40 (My Week), D41 (trips).

### 2026-10-16, M5 slices 1 to 11: outfit engine

- Built: the engine in `backend/app/engine/` (`config.py` with every number, `types.py`, `pairs.py`, `scoring.py`, `generate.py`, `reasons.py`, `feedback.py`, `golden.py`), following `docs/ENGINE.md` with the gaps filled in D34. `suggestions` and `suggestion_feedback` tables and engine fields on outfits in one migration. API: `POST /outfits/suggest` for all three entry points; `POST /suggestions/{id}/feedback` (like, dislike with an optional reason, skip; a new rating replaces the last), `DELETE` to take it back, `/save` and `/wear` (each once). Pair scores cached per wardrobe version; reactions replayed into pair preferences and like-rates on every request (D36). Frontend: a Suggest page (occasion, season, style; boards whose pieces settle in, reasons with cautions marked, Save, I wore this today, Like, Dislike with a reason dialog), "What goes with this?" on item pages, "Complete this outfit" in the studio (saving it unchanged saves the suggestion), "Why it works" on saved suggestions, and "Suggest an outfit" on Home. `make golden` exports a wardrobe for labelling.
- Checked: `make check` passes (ruff, mypy on 102 files, 284 backend tests with the 2 golden-set tests skipped until labelled, TypeScript, ESLint, Prettier, 92 frontend tests, build, API types). The migration applies, rolls back, and reapplies with no drift. Engine tests cover each colour, formality, pattern, fabric, and style rule from the tables; outfit and context scores; filters, templates (separates, one-piece, saree), anchors, accessories, fragrance by season, diversity, missing pieces, compromises, the one-outfit note, reasons, determinism, the pair cache, and rotation. Property tests (hypothesis, 450 random wardrobes and anchors) never find an unavailable, archived, unwashed, or other person's item, two items in a slot, a score outside 0 to 1, or a crash. Speed: 150 items in 0.10 s; the beam search matches trying every combination (D35). API tests cover validation, the three entry points, storage with the engine version, rating changes, ranking moving after a like and a dislike, save and wear once each, stale suggestions, the rate limit, account deletion, and another account getting 404. A browser walkthrough at 1440 px and 375 px: Home's button, the occasion prompt, suggestions, like, dislike for one piece, wear, save and "Why it works", "What goes with this?" for jeans, "Complete this outfit" from chinos and saving it, and a second account without shoes told what's missing; no console errors. Fixed from the walkthrough: sentences where a plural item name took a singular verb ("the jeans keeps"); suggestions sharing a name (names now list top, bottom, and shoes); "6 outfits for mild"; an anchor due a wash now says so.
- Left: the golden set labels and the wear test (yours), then the v1.0 release.
- Decided: D34 (engine gaps), D35 (beam above 5,000), D36 (stored suggestions, replayed reactions), D37 (golden set).

### 2026-10-16, M1 to M4 deployed

- Done: Backblaze B2 set up (EU Central, private bucket, "keep only the last version", a key for that bucket alone) and its five settings added in Render. Pull request #3 merged `m4-outfits` into `main` with a merge commit; CI passed (backend, frontend, API types); Vercel and Render deployed it.
- Checked on the live site, through Vercel as a browser would: the log-in and register pages load, and logged-in pages redirect to log in. A throwaway account registered and logged in; the reference data was loaded; a test photo uploaded to Backblaze in about 6 seconds with "navy" suggested; the photo and its thumbnail came back from Backblaze as WebP in under half a second, with the one-year browser cache; deleting the account removed it and logged it out.
- Left: the owner's walkthrough of the "Done when" lists, and their own 25 to 30 items.

### 2026-10-15, photo storage: Backblaze B2 instead of Cloudflare R2

- Built: `S3_REGION` (required with S3 storage; Backblaze signs every request for the account's region), and an endpoint pasted without `https://` gets it added. The S3 adapter sends checksum headers only where the protocol requires them, and deletes files one request at a time, eight at once, instead of the bulk delete. The API now streams every photo with a one-year private browser cache instead of redirecting to a ten-minute signed link, so each device downloads each photo about once, and Backblaze's free downloads (three times what's stored) go far; a storage outage now gives a 503 with a reason instead of a server error. The bucket's name moved from `render.yaml` to Render's dashboard, since Backblaze bucket names are shared by every account. Deploy steps rewritten for Backblaze.
- Checked: ruff, mypy, 163 backend tests (9 new: the adapter's requests caught before they leave, showing the endpoint, the region in the signature, no checksum headers, one delete per file, failures logged; the endpoint fix; the region named when missing; the year-long cache; the 503), TypeScript, ESLint, Prettier, 86 frontend tests, API types regenerated. With the checksum setting removed, the new test fails on the `x-amz-sdk-checksum-algorithm` header that Backblaze has been reported to refuse.
- Left: Backblaze set up, then merge; the first upload on the live site is the real check against Backblaze.
- Decided: D33.

### 2026-10-15, M4 slices 1 to 6: Outfit Studio and wear log

- Built: `outfit_templates` (seeded and cross-checked), `outfits`, `outfit_items`, `wear_logs`, `wear_log_items`, `items.last_washed_on`, and `vocabulary_terms.role` (slot kinds from the seed) in one migration. Template rules as plain functions (`app/engine/outfits.py`). API: outfits (list with favourite, occasion, and item filters; check; save; view; edit and swap; duplicate; delete) and the wear log (list by item, outfit, or day; log an outfit or loose items; edit; delete). Wear counts, last worn, and wears since washing on item pages. Frontend: Outfits in the navigation; the flat-lay outfit board with its swatch strip; the studio (pick by slot, live "still needed" line, finishing touches, name, occasion, favourite); outfit pages ("I wore this today", another day, favourite, duplicate, edit, delete, when you wore it); the wear log (by day, edit, delete) and logging loose items; the item page's wear card and outfits; Home's Today card.
- Checked: `make check` passes (ruff, mypy on 82 files, 154 backend tests, TypeScript, 86 frontend tests, build). The migration applies, rolls back, and reapplies with no drift. Tests cover the template rules (separates, one-piece, saree, crowded slots, misplaced pieces, the empty start), saving and checking outfits, swapping, duplicating, removed pieces after an item is deleted, the wear log (double taps, future days, edits and deletes recounting, washing, history after outfits and items change), and ownership for both. A browser walkthrough at 1440 px and 375 px: empty outfits, the studio slot by slot with its "still needed" line, a finishing touch, save, "I wore this today" (then disabled), favourite, duplicate, swap the shoes, favourites filter, the item page's wear card and outfits, deleting an item an outfit uses (shown as removed), the wear log (edit a note, log loose items for yesterday, delete), and Home's Today card; no console errors. Fixed while testing: the best-fit rule pointing an empty outfit at one-piece; slot buttons whose spoken names ran together ("Choosetop"); outfit cards that read every piece aloud before the outfit's name; a hydration mismatch on a full page load, because the shell had fetched the user before the page hydrated (the user is now exposed only after hydration).
- Left: merging M1 to M3, then M4.
- Decided: D30 (outfits and templates), D31 (wear log).

### 2026-10-13, M3 slices 1 to 6: wardrobe

- Built: `categories` (89 seeded, plus custom ones per person), `items`, and `item_images` tables in one migration; the seed now loads slots, patterns, fabrics, seasons, statuses, the formality scale, and categories. API: categories (list, add, delete when unused), photos (upload, view), items (list with search, filters, sort, and cursor pages; add; view; edit; archive and restore; delete; matching sets). Photos are shrunk in the browser, then checked, cleaned of metadata, resized, and stored by the API, with the dominant colour mapped to a colour family (`app/engine/color.py`). Storage is a folder locally and Cloudflare R2 in production; the API refuses to start in production without R2. Frontend: Wardrobe in the navigation; a photo-first grid with search, filters (a rail on desktop, a bottom sheet on phones), colour swatches, removable chips, sort, and "Load more"; add and edit forms (photo, suggested colour, category filtered by the sections you shop, "More details"); item page with status, archive, delete, and matching sets; your own categories. `make demo` fills a demo account from `seed/archetypes.json`. A favicon, which also removes a 404 on every page.
- Checked: `make check` passes (ruff, mypy on 70 files, 117 backend tests, TypeScript, 71 frontend tests, build). The migration applies, rolls back, and reapplies with no drift. Tests cover CRUD, every filter and their combination, search, all three sorts across pages, ownership (another account gets 404 for items, photos, and categories), the upload checks (not a photo, GIF, oversized, metadata removed, rotation applied), cleanup of unsaved photos, deletion of files with items and accounts, and the demo script refusing real accounts. A browser walkthrough at 1440 px and 375 px: empty wardrobe, add an item from a phone-style photo (upright, colour suggested as navy), the section filter and "show all", status change, two items without photos, filter by colour, search and back, matching set, edit, archive and restore, delete, a non-photo refused with its reason, a custom category; no console errors. Fixed from the screenshots: colour filters as swatches in a compact grid, filter groups that fold, a rail that scrolls on its own, only the suggested colour shown until "Other colours". Fixed from the build: the shell's navigation now waits in Suspense for the address on pages like `/wardrobe/[id]`.
- Left: R2 set up and the owner's own 25 to 30 items after deploy.
- Decided: D26 (photo pipeline), D27 (dominant colour), D28 (items), D29 (demo accounts).

### 2026-10-13, M2 slices 1 to 6: onboarding and profile

- Built: reference tables (`color_families`, `occasions`, `style_profiles`, `category_groups`, `vocabulary_terms`) loaded from `seed/` by `scripts/seed_reference.py`, which `make migrate`, CI, the tests, and Render's start command run; `render.yaml` now deploys on changes to `seed/` too. `profiles` and `brand_notes` tables; `GET /api/v1/reference`, `GET`/`PATCH /api/v1/profile`, `POST /api/v1/onboarding/finish`, `POST /api/v1/onboarding/reminder/dismiss`, brand-note routes, and `PATCH /api/v1/account` for the name. Frontend: six onboarding steps (what you shop and city; sizes and fit; measurements in cm or inches; occasions; styles and colours; budget) with Back, Skip, Continue, and Skip all, resuming where the person stopped; register goes to onboarding, and log in does until it's finished or skipped; Settings in tabs, where every section can be saved or cleared (with Undo); brand notes; Home offers once to finish a skipped setup.
- Checked: `make check` passes (ruff, mypy on 53 files, 70 backend tests, TypeScript, 53 frontend tests, build). The migration applies, rolls back, and reapplies, and `alembic check` finds no drift. The seed restores edited and deleted rows and changes nothing on a second run. Tests cover the M2 "Done when" list: skipping everything leaves a working empty profile; every answer can be changed and cleared; cm and inches convert both ways and untouched values are saved exactly; user A can't see user B's profile, and B gets 404 for A's brand notes. A browser walkthrough at 1440 px and 375 px: register, all six steps (saving, skipping, switching units), Settings shows the answers, clear and undo, brand notes with a duplicate refused, name change, a second account skips everything and dismisses the reminder, the first logs back in to Home. Fixed from the screenshots: size fields grouped under a clear heading, settings tabs on one line at 360 px, toasts above the phone tab bar.
- Left: the production check for M1 and M2 after merging.
- Decided: D23 (reference data), D24 (profile shape), D25 (brand notes).

### 2026-10-12, M1 slices 5 to 8: sign-in pages, app shell, landing page, account deletion

- Built: the password rule (12 characters or more, nothing else) and its tests; log-in and register pages with checks in the form and the API's messages; `proxy.ts` sends anyone without a session cookie to log in and back; the app shell (sidebar on desktop, tab bar on phones, avatar menu with log out, skip link); Home; Settings with account details and deletion behind a typed email; the landing page; `POST /api/v1/account/delete`; an expired session's cookie is now cleared by the API.
- Checked: `make check` passes (ruff, mypy on 39 files, 37 backend tests, TypeScript, 30 frontend tests, build); API types regenerate unchanged. A browser run at 1440 px and 375 px: a logged-in page redirects to log in and back; register, home, settings, log out, wrong password, log in, delete account, old login refused. Keyboard order on desktop: skip link, wordmark, Home, Settings, account menu. No instant-navigation warnings from Next.js.
- Left: the production check after merging.
- Decided: D22 (the shell draws first; pages wait for the user).

### 2026-10-12, M1 slice 4: auth backend

- Built: `users`, `sessions`, and `rate_limit_hits` tables and their migration; register, log in, log out, and current-user routes under `/api/v1/auth`; Argon2id hashing; session tokens stored only as hashes in an httpOnly cookie; a `current_user` dependency; the `X-Requested-With` check on state-changing requests; rate limits counted in Postgres; one error shape for every failure; the frontend client sends the header.
- Checked: ruff and mypy clean (35 files); 24 backend tests pass; the 4 sign-up tests fail with `password_problem is waiting to be written`. The migration applies, rolls back, and reapplies.
- Left: the owner's password rule and its tests; then slices 5 to 8.
- Decided: D20 (stronger input border), D21 (sessions and sign-in).

### 2026-10-12, M1 slices 1 to 3: design tokens, components, style guide

- Built: colour, type, radius, and shadow tokens with Tailwind's defaults switched off; Bricolage Grotesque and Instrument Sans through `next/font`; 19 components (button, input, field, native select, checkbox, radio, switch, filter and removable chips, tabs, card, photo tile, dialog, bottom sheet, toast, tooltip, skeleton, empty and error states, load more, avatar menu); a development-only `/styleguide` that shows hover, focus, and pressed states through `data-preview`, and opens overlays with `?open=`.
- Checked: frontend lint, types, and 17 tests pass; the production build passes and `/styleguide` is a 404 there. Screenshots at 375 px and 1440 px, including every overlay, with no element wider than the screen. The review found and fixed: title-case labels, buttons stretched to full width, a clipped focus ring on tabs, blank pre-filled selects, a menu touching the screen edge.
- Left: the owner's approval of the look, then slice 4.
- Decided: D18 (shadcn on Radix, restyled, tokens as the only palette) and D19 (native selects).

### 2026-10-12, M0 slice 6: first deploy (M0 done)

- Built: Neon project (Postgres 18, Singapore), Render web service from `render.yaml` (free, Singapore), Vercel project with root directory `frontend` and `BACKEND_URL` set.
- Checked: CI green on pull request #1 (backend 25 s, frontend 36 s, API types 22 s) and again on `main` after the merge. Render ran the migration on Neon, and `/api/v1/health` answers `database: ok`: 2.3 s on the first request, 0.25 s after. The same request through the Vercel URL returns ok, and its headers show Vercel's Mumbai edge forwarding to Render's uvicorn. The browser's JavaScript contains no Render address. Screenshots of the live site at 375 px and 1440 px show "API ok, database ok".
- Left: nothing for M0.
- Decided: nothing new.

### 2026-10-11, M0 slices 1 to 5 and 7: walking skeleton, local

- Built: backend skeleton with health check, local Postgres and first migration, Next.js frontend behind the `/api/*` proxy, typed API client, CI workflow, `make` commands, README quick start, Render Blueprint and deploy steps.
- Checked: `make check` passes (ruff clean, mypy strict with no issues in 22 files, 10 backend tests, 9 frontend tests, production build). The migration applies, rolls back, and reapplies. On the running app: health answers 200 with the database up and 503 with it stopped, and recovers when it restarts. A browser request through the Next.js proxy reaches FastAPI and Postgres. Screenshots at 375 px and 1440 px show "API ok, database ok", and the page shows "Can't reach the API" with "Try again" when the backend is down. A missing `DATABASE_URL` stops startup and names the variable. `make dev` starts both servers, and one Ctrl+C stops both.
- Left: first CI run on a pull request; first deploy; walking through the M0 "Done when" list on the live URL.
- Decided: D11 to D17 in `docs/DECISIONS.md` (versions, sync SQLAlchemy, direct connection for migrations, UUIDv7, typed client, mypy, hosting settings in the repo).

### 2026-10-11, before M0: project review

- Built: nothing yet.
- Checked: read every doc; the seed file counts match `seed/README.md`; the repo has no application code; local tool versions recorded above.
- Left: plan M0.
- Decided: nothing new.

<!--
### YYYY-MM-DD, M3 slice 2: item create and list
- Built: ...
- Checked: backend tests 42 passed; type check clean; looked at 375 px and 1440 px
- Left: ...
- Decided: ... (also added to DECISIONS.md)
-->

## Milestone notes

After each milestone, three lines: the hardest problem, the decision you made and why, one number.

### M0

- Hardest: picking versions that work together on every host. The newest TypeScript broke the lint and type-generation tools, and the newest pnpm isn't supported by Vercel's builds, so both were held back (D11).
- Decision: deploy in the first milestone, with the browser talking only to Vercel, which forwards `/api/*` to Render. Hosting problems surfaced while the app was one endpoint, and the login cookie in M1 will be first-party.
- Number: the live health check takes 0.25 s warm and 2.3 s after the database wakes; 19 automated tests and 3 CI jobs gate every merge.

<!--
### M5
- Hardest: ...
- Decision: ...
- Number: golden-set agreement 84%; would wear 7 of top 10 for college
-->

## Known limitations

Moved to the README at M11 (its "Known limitations" section), where visitors see them.
