# Progress

The running state of the project, updated at the end of every slice. Keep it short and current.

## Now

- **Last updated:** 2026-10-20
- **Current milestone:** M7 Insights, built on `m7-insights` and waiting for your commit and merge. M5's last two "Done when" items (golden set, wear test) are still yours; v1.0 is tagged once they pass.
- **Current slice:** none open. Open issue: on the live server the forecast request to Open-Meteo is refused, so days go by the season (place search works). The Render log line "Weather service unavailable: ..." says why.
- **Next action (owner):**
  1. Commit `m7-insights` (staged), push it, open a pull request, and merge it once CI passes.
  2. In Render, open wearwise-api > Logs, search for "Weather service unavailable", and send the text after it.
  3. On the live site: log what you wear for five days, then open Insights.
  4. The wear test and the golden set (M5), then the v1.0 release.

**Carry into M8:** with an empty or tiny wardrobe, no single piece makes an outfit on its own, so every archetype's coverage gain is zero and the starter capsule's one-at-a-time greedy pick has nothing to choose by. The capsule should start from whole outfits (a top, a bottom, and shoes picked together), then add pieces one at a time. Bought candidates become items (the data model already says so), and the wardrobe's measures update from the new wardrobe version.

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

- **Overall:** 8 of 12 milestones built (M0 to M7), 7 released. v1.0 (M0 to M5) waits on the golden set and the wear test.

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
| M7 | Insights | see cost per wear, versatility, orphans, coverage | built, not merged | | |
| M8 | Smart Shopping I | analyse a purchase; see gaps; plan a capsule on a budget | not started | | |
| M9 | Smart Shopping II | find real products for a gap | not started | | |
| M10 | AI | auto-tag photos; chat with a stylist that knows your wardrobe | not started | | |
| M11 | Hardening and launch | hand the link to anyone | not started | | |

## Before M0 (only you can do these)

- [x] GitHub repo created and the docs pushed (checked 2026-10-11: local `main` matches `origin/main`)
- [ ] 25 to 30 photos of your own items taken (needed by M3)
- [x] Accounts: Vercel, Render, Neon (set up 2026-10-12)
- [ ] Backblaze account (needed by M3 for B2 photo storage; replaces Cloudflare, D33)
- [ ] Optional: applied for an affiliate or product API (only matters in M9)

**Local tools (checked 2026-10-11):** uv 0.12.23 (it installs Python 3.14 for the backend), Node 22.23.0, pnpm 10.34.6, Docker 29.8.0 with Compose v5.5.1, make 4.3, gh 2.45.0.

## Log

Add an entry per slice, newest first.

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

Things that are deliberately not handled yet. Move them into the README at M11.

- On Render's free plan, the first request after 15 idle minutes takes about a minute while the backend wakes. The landing and log-in pages wake it early, and every waiting screen says so.
- No password reset by email yet: it needs an email provider. Until then, a forgotten password means a new account. Planned for M11 at the latest.
- The email address can't be changed yet: doing it safely needs the password again. The name can be changed in Settings.
- Without a city or a manual setting, suggestions and plans go by the season (D34, D39).
- Shown suggestions are kept indefinitely for acceptance rates; prune unreacted ones if the table grows (D36).
- Photos in Backblaze B2 aren't backed up. For a personal project that's acceptable.
- iPhone HEIC photos upload from Safari, which can read them; other browsers may not.
- Settings still sits in the main navigation while it has only two neighbours; it moves to the avatar menu alone as Outfits and My Week arrive (D22).
- The `make` commands assume Linux or macOS. On Windows, use WSL.
