# Decisions

A short log of choices that would be expensive to change, with the reason. Add an entry whenever a decision is made or reversed. Newest at the bottom.

Format: what was decided, why, what was rejected, and when to revisit.

---

## D1. Next.js frontend, FastAPI backend, PostgreSQL

**Why:** the engine is algorithmic work that suits Python and its test tools; Next.js is the most widely used React setup; Postgres handles relational data with arrays and JSON.
**Rejected:** a single Next.js app with API routes (engine in TypeScript would be less natural to test and extend with ML later); Django (heavier than needed).
**Revisit if:** the two-service setup causes more deployment trouble than it is worth.

## D2. One repository

**Why:** one pull request can change the API and the UI together, and the docs live beside the code.
**Rejected:** separate repos.

## D3. Server-side sessions in an httpOnly cookie, API proxied through the frontend's domain

**Why:** simple, revocable, and safe from script access. Proxying makes the cookie first-party and removes CORS.
**Rejected:** JWT in local storage (readable by scripts, hard to revoke); a hosted auth service (less to learn, another dependency).
**Revisit if:** a mobile app is added.

## D4. The engine is deterministic; the AI only explains and converses

**Why:** testable, explainable, free to run, and works when the AI is down. It also stops the chatbot inventing items.
**Rejected:** asking a language model to pick outfits directly.
**Revisit if:** a learned compatibility model beats the rules on the golden set (see `ENGINE.md` section 15). Even then it would sit inside the engine, not replace it with a chat model.

## D5. Categories, colours, occasions, style profiles, and archetypes are data

**Why:** wardrobes vary enormously, especially across menswear, womenswear, and ethnic wear. Adding a garment type must not need a code change.
**Rejected:** enums in code.

## D6. No bulk scraping; product discovery through adapters

**Why:** scrapers against large retailers are brittle and usually against the sites' terms; the interesting work is ranking against a wardrobe. See `SHOPPING.md` part 2.
**Rejected:** scraping Myntra, Flipkart, and Amazon listings.
**Revisit if:** an official product API or feed is approved; add it as another adapter.

## D7. Deploy from M0; Vercel, Render, Neon, Cloudflare R2

**Why:** free to start, and deployment problems surface early. Neon over Render's free Postgres because the latter expires after 30 days. R2 because Render's free instances have no permanent disk.
**Rejected:** deploying at the end; a single VPS (more to manage while learning).
**Revisit if:** cold starts hurt demos, or the project becomes commercial.
**Changed by D33:** photos are stored in Backblaze B2, not R2.

## D8. Images are private and served through signed URLs

**Why:** wardrobe photos are personal and may show the user or their home.
**Rejected:** a public bucket.

## D9. Vertical slices, with v1.0 after M5

**Why:** each milestone ends with something real and deployed; a finished small app beats an unfinished large one.
**Rejected:** building all page shells first and wiring them later, which conflicts with "no fake functionality".

## D10. India first

**Why:** it is where the builder shops and dresses. Rupees, Indian retailers in search links, ethnic wear as first-class categories, and summer / monsoon / winter / mild as seasons.
**Revisit if:** other regions are added; seasons and retailers are already data.

---

<!-- Add new decisions below. Record the versions chosen in M0 here too. -->

## D11. Versions chosen in M0 (October 2026)

| Area | Versions |
|---|---|
| Backend | Python 3.14 (3.14.8), uv 0.12.23, FastAPI 0.143, Starlette 1.7, Uvicorn 0.54, SQLAlchemy 2.1.4, Alembic 1.20, Pydantic 2.14, pydantic-settings 2.15, psycopg 3.3.6 |
| Backend tools | ruff 0.17, mypy 2.4 (strict), pytest 9.1, httpx2 2.13 (the test client Starlette now asks for) |
| Frontend | Node 22, pnpm 10.34.6, Next.js 16.4, React 19.3, TypeScript 5.9.3, Tailwind CSS 4.3 |
| Frontend tools | ESLint 9.39, Prettier 3.9, Vitest 5.0, Vite 8.3, openapi-typescript 7.13, openapi-fetch 0.17 |
| Database | PostgreSQL 18 (18.6 locally, in CI, and on Neon) |

Held back on purpose:
- **Python 3.15:** only release candidates were available, so 3.14.
- **TypeScript 7.0:** typescript-eslint (used by Next's lint config) supports below 6.1, and openapi-typescript supports 5.x, so 5.9.
- **pnpm 11 and 12:** Vercel builds with pnpm 10 out of the box; later versions need an experimental Corepack setting, and builds were reported failing. So 10.
- **ESLint 10:** create-next-app 16.4 installs 9, the version Next's lint config is tested with.

Next.js runs with `cacheComponents` and `partialPrefetching` on, as create-next-app 16.4 sets them; Next's docs say the next major turns both on everywhere.

**Revisit:** at the start of a milestone, when something holding a tool back has caught up.

## D12. Synchronous SQLAlchemy with psycopg 3

**Why:** simpler to learn and debug than async. FastAPI runs synchronous routes in a thread pool, which is plenty at this scale.
**Rejected:** async SQLAlchemy (more concepts for little gain here).
**Revisit if:** concurrency becomes a measured bottleneck.

## D13. The app uses Neon's pooled connection; migrations use the direct one

**Why:** Neon's pooler runs PgBouncer in transaction mode, and Neon recommends direct connections for schema migrations. `MIGRATION_DATABASE_URL` is optional and falls back to `DATABASE_URL`. The backend also accepts plain `postgresql://` URLs and adds the driver name, so connection strings are pasted unchanged.
**Rejected:** one URL for both (works until a migration needs a session-level feature the pooler drops).

## D14. UUIDv7 primary keys

**Why:** `uuid.uuid7()` (new in Python 3.14) starts with a timestamp, so new rows land at the end of the index and IDs sort by creation, which helps cursor pagination in M3. IDs are made in Python, so they're known before the insert.
**Rejected:** UUIDv4 (random order scatters index writes); integer sequences (guessable, and they leak counts).

## D15. Typed API client from the OpenAPI schema

**Why:** openapi-typescript turns FastAPI's schema into types, and openapi-fetch checks every path, parameter, and body against them at compile time. CI regenerates the types and fails if the committed ones are out of date, so the frontend and backend can't drift apart.
**Rejected:** hand-written fetch wrappers (drift unnoticed); a generated SDK (more code to review).

## D16. mypy in strict mode for the backend

**Why:** runs inside the uv environment with the rest of the Python tools; works with Pydantic's plugin and SQLAlchemy 2's typed models without extra stubs.
**Rejected:** pyright (good, but runs on Node, adding a second toolchain to backend checks).

## D17. Hosting settings live in the repository

**Why:** `render.yaml` holds the backend's build and start commands, region, and variables, so changes are reviewed like code. Render deploys a commit only after CI passes on it. Migrations run in the start command because free instances can't run a pre-deploy command. There is no Render health check: the health route queries the database, and frequent checks would keep Neon awake and use up its free compute hours. Third-party GitHub Actions are pinned to a commit, because a tag can be moved.
**Rejected:** configuring everything by hand in dashboards.
**Revisit if:** the backend moves to a paid instance (then use a pre-deploy command for migrations, and a health route that doesn't touch the database).

## D18. Components: shadcn/ui on Radix, restyled, with WearWise tokens as the only palette

**Why:** Radix gives dialogs, menus, tabs, and form controls correct keyboard and screen-reader behaviour. shadcn copies the component source into `frontend/components/ui/`, so each one is restyled to `docs/DESIGN_SYSTEM.md` rather than worn as a stock theme. Tailwind's default colours, type sizes, and shadows are switched off in `app/globals.css`, so only the design tokens exist and the palette can't drift. The shadcn CLI isn't a runtime dependency (about 300 packages for one CSS file); the few CSS variants the components need are copied into `globals.css`.
**Rejected:** shadcn's new default primitives (Base UI), since the architecture doc names Radix; keeping shadcn's own colour names (`primary`, `muted`) next to ours.
**Revisit if:** a component needs behaviour Radix doesn't offer.

## D19. Selects are native `<select>` elements, styled

**Why:** phones open their own picker, which suits long lists such as the 89 categories; it works without JavaScript and is accessible by default. Radix Select 2.3.8 also left pre-filled selects blank under React 19's development Strict Mode, which would make every edit form look empty while building.
**Rejected:** Radix Select; turning off Strict Mode for the whole app.
**Trade-off:** the open list is drawn by the operating system and can't be styled.

## D20. Inputs and selects get a stronger border than the divider colour

**Why:** `line` (#D9DCD8) measures 1.38:1 on white, so an empty input was barely visible. `line-strong` (#858A91) measures 3.48:1 on white and 3.18:1 on paper, above the usual 3:1 target for the edges of form controls. Dividers and cards keep the quieter `line`.
**Rejected:** relying on labels alone to show where a field is.

## D21. Sessions and sign-in

**Why:** a 256-bit random token in an httpOnly, SameSite=Lax cookie (Secure in production); the database keeps only its SHA-256, so a leaked database can't be turned back into logins, and no server secret is needed. Sessions last 30 days and slide forward at most once a day while used. Passwords use Argon2id with the library's defaults. An unknown email runs a dummy password check, so it takes as long as a wrong password, and both get the same message. State-changing requests need an `X-Requested-With` header (CSRF). Rate limits are counted in Postgres per time window (log in: 10 per email and 30 per IP every 15 minutes; register: 10 per IP an hour), so they survive restarts and deploys without Redis.
**Rejected:** JWTs (can't be revoked without a deny list), in-memory rate limits (reset on every Render restart), a session secret (nothing for it to protect).
**Revisit if:** the API is called directly by a mobile app, or traffic needs a dedicated rate-limit store.

## D22. Logged-in pages: a cookie check at the edge, the real check in the API, the frame first

**Why:** `frontend/proxy.ts` only checks that a session cookie exists, so it never calls the backend and adds no cold-start delay. The API checks the session on every request; an ended session returns 401 and clears the cookie, and the page sends the person to log in, then back. The shell (sidebar, top bar, tab bar) draws immediately and each page shows its own placeholder until the API answers, which also lets Next.js check that navigation stays instant. Deleting an account needs the account's email typed out, checked again by the API.
**Rejected:** checking the session against the API inside `proxy.ts` (a backend call on every page, through Render's cold starts); hiding the whole shell until the user is known.
**Also:** while only Home and Settings exist, Settings sits in the sidebar and the phone tab bar as well as the avatar menu; it moves to the avatar menu alone once more pages arrive.

## D23. Reference data: slug keys, loaded on every deploy, never deleted

**Why:** the seed files' ids ("navy", "college", "minimal") are the primary keys, so profiles (and later items) store readable ids that stay stable when a display name changes. `backend/scripts/seed_reference.py` runs after migrations in `make migrate`, CI, the test setup, and Render's start command. It inserts or updates by id and touches only rows whose values changed, so running it twice changes nothing. It never deletes: a row dropped from a seed file may still be referenced, so retiring one is a migration's job. Short fixed lists from `taxonomy.json` (sections, fits, sizing systems) share one `vocabulary_terms` table keyed by (kind, id) instead of a table each. `seed/taxonomy.json` gained the sizing systems the onboarding step needs (IN / UK, EU, US). The app reads all the lists in one `GET /api/v1/reference`, cached for the whole visit: they're small and change only on deploy, and one request beats seven.
**Rejected:** loading reference data inside a migration (every seed edit would need a new migration); deleting rows missing from the files; an endpoint per list.
**Revisit when:** M3 adds categories and custom occasions with a `user_id`; those are per-person and get their own routes.

## D24. One profile row per person; empty means "not answered"

**Why:** every answer is optional, so the profile row is created on first read and starts empty. Lists and JSON objects default to empty rather than null, so code reading them never has to tell "not answered" from "answered with nothing", and clearing an answer stores the same empty value. `PATCH /api/v1/profile` changes only the fields sent, and null clears one. Measurements are stored in cm to one decimal place; the app converts for display only, and a value the person didn't edit is sent back exactly as stored, so switching units never changes stored numbers. Money is whole paise. Ids are checked against the reference tables, and a colour can't be both loved and avoided. `onboarding_step` records the step reached, so closing the tab loses nothing; "Skip all" marks onboarding finished and skipped, and Home offers once to finish it.
**Rejected:** a nullable column for every answer (two kinds of empty); separate tables for measurements and preferences (one row is read together everywhere); storing inches (conversions would drift).
**Also:** latitude and longitude wait for the weather adapter in M6. The currency column exists but has one value, INR, so it isn't editable yet.

## D25. Brand notes: one per brand, unique ignoring capitals, a capped list without pagination

**Why:** a unique index on `(user_id, lower(brand))` stops "H&M" and "h&m" becoming two notes, even when two saves race. Notes are typed by hand, so the list is capped at 200 per person and returned whole, sorted A to Z; cursor pagination (the API convention) is kept for lists that grow without limit, such as items and the wear log.
**Rejected:** pagination for a list nobody will fill; checking duplicates only in Python.

## D26. Photos: shrunk in the browser, checked and converted by the API, private in R2

**Why:** phone photos are 3 to 8 MB, and Vercel limits request bodies on its functions to 4.5 MB, so the web app first redraws each photo at most 2000 px on its longest side as a JPEG (about half a megabyte). Uploads are quicker on mobile data, and redrawing drops the metadata, so a phone's recorded location never leaves the device. Safari can read iPhone HEIC photos, so they work too. The API still treats every upload as untrusted: it decides the format from the content (JPEG, PNG, or WebP), refuses files over `MAX_UPLOAD_MB` (8) or 50 megapixels, applies the rotation tag, drops all metadata again, and stores a 1600 px WebP and a 400 px thumbnail under a new key, so a stored file never changes and browsers can cache it for a year. Photos are uploaded before the item is saved, so the colour can be suggested; unsaved uploads are removed after a day. The bucket is private: the API checks ownership and answers with a ten-minute signed link to R2 (locally, it streams the file). Files are deleted only after the database change that removes them is committed. New libraries: Pillow 12.3 (images), boto3 1.43 (the S3 protocol, which R2 speaks; types-boto3 for mypy), python-multipart 0.0.32 (FastAPI's file uploads).
**Rejected:** uploading straight from the browser to R2 with presigned POSTs (the API couldn't check or convert the file first); a public bucket; serving through Next.js image optimisation (it can't see the login cookie).
**Revisit if:** quick add (several photos at once) arrives, or R2's free allowance runs short.
**Changed by D33:** photos are stored in Backblaze B2, and the API streams them rather than answering with signed links.

## D27. Dominant colour without AI

**Why:** the colour in the middle of a photo that isn't also around its edges is usually the garment, since clothes are photographed in the middle of a bed, floor, or wall. Pixels go into coarse colour buckets; the winner is the bucket covering the most of the middle minus how much of the border it covers, and its average is widened to every middle pixel within a small CIELAB distance, so one garment's shades aren't split across buckets. The nearest colour family is found in CIELAB, where equal distances look about equally different, unlike RGB. It's plain functions in `backend/app/engine/color.py`, tested on made-up pixel grids, and always shown as a suggestion the person can change.
**Rejected:** k-means clustering (slower, and needs a library for little gain at 64 px); asking a vision model (M10, and only to propose).

## D28. Items: category defaults, archive before delete, keyset pages

**Why:** an item needs only a category and a main colour; formality, warmth, and washing start from the category and can be changed. "No seasons" means every season, so the season filter includes those items. Archive hides an item but keeps it (and, from M4, its wear history); delete removes it and its photo after a confirmation. Matching sets are a shared `set_id`, at most six items, and a set of one dissolves. Lists use keyset pagination: the cursor holds the last row's sort key and id, so pages don't repeat or skip items when something is added meanwhile; sorts are newest, oldest, and by category. Search matches every word against the name, brand, size, notes, category, and colour. Custom categories are rows with a `user_id`; the foreign key from items to categories checks at the end of each statement (Postgres's default), not immediately, so deleting an account can remove both, while the service refuses to delete a custom category still in use. Every change bumps `users.wardrobe_version` for the engine's cache in M5.
**Rejected:** offset pagination (shifts when items are added); deleting rows on archive.

## D29. A demo wardrobe only in demo accounts

**Why:** `make demo` fills `demo@example.com` with the 66 generic staples from `seed/archetypes.json`, without photos or prices, because the staples have none and nothing may be made up. The account is marked `is_demo`, the app labels it "Demo account", and the script refuses any account that isn't a demo. Running it again replaces the demo wardrobe. A new demo account gets a random password, printed once.
**Rejected:** demo items in seed files or migrations (they would reach real accounts); invented photos or prices.

## D30. Outfits: templates decide what's complete; pieces keep their names

**Why:** the rules for a whole outfit are the templates in `seed/taxonomy.json` (a top, a bottom, and footwear; a one-piece and footwear; a saree, its blouse, and footwear), checked by plain functions in `backend/app/engine/outfits.py`. The best-fitting template is the one with the fewest pieces it can't place, then the most required slots filled, then the fewest missing, then seed order, so an empty outfit points at "top, bottom, footwear" rather than at whichever template needs fewest pieces. An outfit must be complete to be saved; the studio asks the API (`POST /outfits/check`) after every change and shows what's still needed in one sentence. One item per slot is enforced in the engine and by a unique index. Each piece stores the item's name, so deleting an item leaves the outfit showing it as removed instead of breaking; swapping in another piece completes it again. Slots carry a role from the seed (core, accessory, finishing), stored on `vocabulary_terms.role`, so the finishing-touches prompt comes from data. Engine fields on outfits (`source`, `score`, `reasons`, `engine_version`) wait for M5.
**Rejected:** saving incomplete outfits (the engine and the planner would have to cope with them everywhere); deleting outfits when an item is deleted (loses the person's work); hard-coding which slots are accessories.

## D31. The wear log is the record; counts are recounted from it

**Why:** a wear log is an outfit or loose items on a day; logging an outfit copies its pieces (with their slot and name), so changing the outfit later doesn't rewrite history, and deleting an outfit or an item leaves the days they were worn. `items.wears_since_wash` is recounted from the log whenever the log changes, as wears on days after `items.last_washed_on`, which is set when an item comes back from the laundry. Recounting rather than adding one keeps the number right when a log is edited, deleted, or added for an earlier day. Logging the same outfit for the same day twice returns the first log, so a double tap is harmless. The browser sends its own calendar day; the API accepts up to a day past its UTC date, since phones in India are five and a half hours ahead.
**Rejected:** a running counter (drifts with every edit or back-dated log); storing wash events (not needed until M6's laundry planning).

## D32. Logged-in pages render the same on the server and on first load in the browser

**Why:** logged-in pages are client components whose data comes from the API in the browser, so the server renders their loading state. The app shell asks who is logged in before the page itself hydrates, and if that answer arrives first, the page's first render in the browser would differ from the server's HTML, which React rejects. `useCurrentUser` therefore hides the user until hydration is done (`useHydrated`, built on `useSyncExternalStore`), so the first render always matches, and the page fills in a moment later. Any data a component fetches before pages hydrate needs the same treatment.
**Rejected:** turning off server rendering for logged-in pages (loses the instant frame and navigation); fetching the user on the server (a backend call on every page through Render's cold starts, as D22 explains).

## D33. Photos in Backblaze B2, streamed by the API

**Why:** Cloudflare R2 asks for a card on file even for its free allowance; Backblaze B2 gives 10 GB free without one and speaks the same S3 protocol, so the adapter stays and only its details change. B2 differs from R2 in five ways that shaped them. Every request is signed for the account's region, so `S3_REGION` is required (R2 would take `auto`). Downloads are free only up to three times the average stored each month, about 20 MB for a 30-item wardrobe, so the API now streams each photo after the ownership check, with a one-year private browser cache. The signed links it gave before changed every ten minutes, so the browser downloaded every photo again on each visit; a fixed address lets each device download a photo about once. Newer boto3 adds checksum headers to every request, and Backblaze has refused them, so checksums are sent only where the S3 protocol requires one, and files are deleted one request at a time, eight at once, instead of with the bulk delete, which requires one. B2 keeps every version of a file, so a delete only hides it; the bucket's lifecycle setting "Keep only the last version" removes it a day later. Bucket names are shared by every Backblaze account, so the bucket's name is set in Render's dashboard, not in `render.yaml`. Photos now pass through Render, which adds a hop on a photo's first load, but the browser keeps them afterwards.
**Rejected:** R2 (needs a card); Supabase Storage (1 GB free, and free projects pause after a week without use); keeping signed links on B2 (a few dozen visits a month would use up the free downloads).
**Revisit if:** photos load too slowly through the API, or Render's bandwidth runs short; R2 with signed links is the way back, since its downloads are free.

## D34. Outfit engine v1.0: the doc's numbers, and the gaps it left

**Why:** the engine follows `docs/ENGINE.md` (filters, templates, generation, pair and outfit scores, context, accessories, diversity, reasons) as plain functions in `backend/app/engine/`, with every number in `config.py` and `ENGINE_VERSION` 1.0. Where the doc is silent: colour uses the measured hex when there is one, else the family's, converted to OKLCH; an item is neutral when its family's neutrality is 0.8 or more or its chroma is under 0.03, and muted under 0.10; multicolour has no single hue, so it scores 0.75 with a neutral and 0.45 with a colour. Texture pairs like a solid. One-piece outfits weigh their pairs like separates (one-piece with a saree blouse 1.0, a layer 0.9, footwear 0.8), and any other core pair 0.5. Accessories join the base score's weighted mean (0.3, belt with shoes 0.7) but not its worst pair. The occasion score can reach 1.1 with the preferred-group bonus, and the total is capped at 1. Until weather arrives (M6), the season stands in for the temperature: the request's season, else the month on an Indian calendar (March to May summer, June to September monsoon, October and November mild, December to February winter), with target upper-body warmth of 0 to 1, 1 to 2, 1 to 3, and 3 to 6, and the monsoon counting as rain likely; the rules for below 10 °C (shorts, open shoes) wait for real temperatures. The preference score averages, per core piece, the like-rate for its colour family and category and its own like-rate, so "I don't like this piece" lowers that piece alone. Items have no editable extras yet, so a fragrance is chosen by its seasons and occasions and the nearest formality. The "half the results" cap applies to core pieces, not accessories (one watch may finish every outfit), and when only capped options remain the rest are still shown, so a wardrobe with one pair of shoes still gets several outfits. With nothing for the occasion, the range is relaxed by a step each side and the results are flagged. Reason sentences live in one dictionary, written so an item's name never has to agree with a verb ("jeans" and "loafers" are plural). New test library: hypothesis 6.170 (property tests on random wardrobes).
**Rejected:** tuning weights by feel before the golden set exists; a season calendar in the seed files (it's a stand-in that weather replaces).
**Revisit if:** the golden set disagrees with the owner (change one thing, record before and after, new engine version), or M6 brings weather.

## D35. Beam search above 5,000 combinations, not 50,000

**Why:** measured locally: a wardrobe of 48,400 combinations took 1.19 s to enumerate, and 0.50 s after scoring combinations without building their reasons; Render's free instance has a tenth of a CPU. Above 5,000, the beam search (width 200) found the same top ten as trying everything in all 15 trials (5 wardrobes, 3 occasions each), in 0.045 s against 0.44 s. A 150-item wardrobe takes 0.10 s. A test checks that the beam and enumeration agree on a wardrobe of 20,412 combinations, and another that 150 items take under a second.
**Rejected:** keeping 50,000 (several seconds per request on the server).
**Revisit if:** a loved outfit misses the top 20 because the beam dropped it.

## D36. Suggestions are kept; reactions are replayed, not accumulated

**Why:** every outfit shown is a row in `suggestions` with its engine version, score, components, and reasons, so like, dislike, save, and wear act on exactly what was shown, and acceptance (saved, liked, or worn, divided by shown) can be compared between versions (`services/suggestions.acceptance`). One action, `POST /outfits/suggest`, serves the three entry points: no anchors, one ("what goes with this?"), or several ("complete this outfit"). Pair preferences and like-rates are worked out from `suggestion_feedback` on every request, replaying `pref += 0.3 * (target - pref)` oldest first, so turning a like into a dislike, or taking one back, gives the same numbers as if the first reaction never happened; the `pair_preferences` table in the data model is therefore not built. A new rating replaces the last; saved and worn are recorded once each. Saving makes an outfit with `source = engine` and the suggestion's version, score, and reasons; swapping a piece later clears the score and reasons, which described the old pieces. Pair scores are cached in process per user, wardrobe version, and engine version (eight wardrobes at most), and suggesting is limited to 300 requests an hour per account.
**Rejected:** a stored `pair_preferences` table (a second copy that can drift from the reactions); three endpoints for one pipeline; letting the browser send scores back when saving.
**Revisit if:** `suggestions` grows large (prune unreacted rows after a few months), or there are a few hundred reactions, enough to try fitting the weights.

## D37. The golden set: exported by script, labelled by the owner, committed

**Why:** `make golden email=...` (or the script with `DATABASE_URL` set to Neon's connection string) writes `backend/tests/golden/`: the wardrobe as the engine sees it (items keyed i01, i02, ...; names and attributes, no photos), about 80 pairs from the slot pairs that matter most, spread across the engine's scores so the set holds good and bad pairs alike, and the favourite outfits that have an occasion as "loved outfits". The owner labels each pair good, fine, or bad in a spreadsheet. The test skips until 60 pairs are labelled, then needs 80% of good-versus-bad comparisons ordered as the owner did, and each loved outfit in the top 20 for its occasion. The export never overwrites labels unless forced.
**Rejected:** labelling a made-up wardrobe (it would test my taste, not the owner's); showing the engine's scores in the labelling sheet (they would bias the labels).
**Revisit if:** the owner prefers not to commit item names; they can rename items first, since only attributes are scored.

## D38. The planner's day pools spread across the wardrobe

**Why:** the planner asks the engine for each day's 40 best outfits, but a beam search keeps its 200 best half-built outfits, and after "top and bottom" those were nearly all built on the three or four best tops; a 150-item test week then ran out of clean tops by Tuesday. For the planner's lists only (suggestions are unchanged and still match trying every combination in all 15 trials of D35), the beam caps any one piece at an eighth of its places, and each day's pool gives every piece at most its slot's fair share (the pool size divided by the pieces in that slot, at least 4); if that leaves room, the best of the rest fill it. An accessory that's due a wash (socks, mostly) comes off a planned outfit rather than ruling it out: before this, one pair of socks blocked 30 of a day's 34 outfits. A 150-item week plans in about 0.8 s on a laptop.
**Rejected:** a bigger pool (more work, still crowded); spreading the beam for suggestions too (it cost 20 of 150 top-ten matches with trying everything).
**Revisit if:** planned weeks look samey, or planning is slow on the server.

## D39. Weather from Open-Meteo, cached per place per day, with a manual fallback

**Why:** Open-Meteo needs no key and is free for non-commercial use (CC BY 4.0, credited in the footer with GeoNames for place search). The city is chosen from a place search, so the forecast comes from the right Hyderabad; its coordinates are stored rounded to two decimals (about a kilometre) and neighbours share one forecast row. One 16-day fetch per place per UTC day, made after committing the read transaction (no outside call inside a transaction), with a five-second timeout and one retry; a failure is remembered for 30 minutes so pages stay quick during an outage. A day's feels-like temperature is the middle of the forecast's apparent maximum and minimum (a day out, not just its peak). Without a city or a forecast, the person's manual setting stands in (hot 34°, mild 24°, cold 13°, rainy 27° with rain likely), and without that the season (D34). With weather the engine uses the doc's temperature bands, rain from the forecast's chance (50% or more), and in the cold a caution for bare legs and open toes, read from new category traits in the seed (`traits: bare_legs, open_toe`), so no category is named in code. `ENGINE_VERSION` 1.1. No new libraries: the adapter uses Python's own HTTP client.
**Rejected:** geocoding the typed city silently (wrong town, no way to tell); fetching on every request; a weather API that needs a key.
**Revisit if:** the app becomes commercial (Open-Meteo's paid plan), or Render's region makes the fetch slow.

## D40. My Week: stored plan days, kept choices, worn from the wear log

**Why:** each day of a plan is a `plan_days` row: the outfit (as suggestions keep it, plain id arrays), its reasons, the occasion it was planned for, the weather snapshot, and a lock. A day's occasion is the one chosen for that day, else an event's, else the weekday's usual one (`profiles.weekday_occasions`), else the first occasion from onboarding. A day planned for a different occasion than it now has is flagged until planned again. Planning again keeps locked days and worn days; the planner simulates their wears, and checks every choice against the locked days later in the week, so a lock can't be broken by an earlier day. Swapping picks from options that keep the whole week within the rules, re-scored by the server, and locks the day. "Worn" is the existence of the day's wear log, logged through the same code as "I wore this today", so deleting the log un-wears the day. An optional laundry weekday counts everything clean again from that day. Laundry done marks items washed (back to available, wears counted afresh).
**Rejected:** a `status` column for worn (it could disagree with the wear log); planning past days; letting a swap be any outfit the browser sends.
**Revisit if:** people want more than seven days ahead, or repeat guards by who saw an outfit (stretch in the product spec).

## D41. Trips: a compact packing list that dresses each day for its occasion

**Why:** a trip has a destination from the place search (for its own forecast), dates (up to 14 days), and an occasion per day. The packing follows section 13 of the engine doc, greedy and so "a compact list": add the outfit that dresses the most extra days per new piece, counting only days that can actually be worn within each piece's wears before a wash (no laundry on a trip), then leave out each piece, least useful first, while every day stays dressed. A day counts as dressed by an outfit scoring 0.65 or more within its occasion's level of dress when the wardrobe has one, so a wedding day gets the kurta rather than the casual shirt already packed. Basics are plain counts (socks and underwear, one a day). Marking items packed sets their status, so they leave everyday suggestions; deleting the trip unpacks them.
**Rejected:** the smallest possible list (an exact set cover is slow and not needed); laundry on the road.
**Revisit if:** trips get longer than two weeks, or people want to pack for a laundry stop.


## D42. A style match needs a colour or category the style is known by (engine 1.2)

**Why:** an item matched a style when it fitted half of the style's signals (colour, pattern, category, formality, and fabric and fit when known). A plain shirt in the middle of the formality scale fits "solid" and "within a step of the centre" for nearly every style, so it matched all twelve; the worn style in Insights showed every style at 100%, and the style score in suggestions couldn't tell styles apart. Now an item that isn't tagged with the style must also have one of the style's colours or categories, then still fit half the signals. The same rule serves suggestions (the S component), the planner, and Insights, so `ENGINE_VERSION` is 1.2 and pair scores cached under 1.1 are dropped. A test checks that a plain middling piece in a colour and category a style doesn't list no longer matches it.
**Rejected:** raising the share to two thirds (it also dropped pieces in the style's own colours with an unknown fabric); weighting the signals (more numbers to tune before the golden set exists).
**Revisit if:** the golden set or the worn style disagree with the owner's sense of their style.

## D43. Insights: counted from rows, measured on the steady wardrobe, cached per wardrobe

**Why:** `GET /insights` returns every number for the page in one response, and each is counted from the person's own rows, with a test that works each one out by hand from a fixed fixture.
- **Wear:** a piece's wears are the wear logs it's in. Most and least worn, and the style worn, wait for 5 days logged (fewer is noise, and the page says how many to go); least worn counts only things owned 30 days or more. Cost per wear is the price divided by wears, rounded to the paisa, shown from the first wear and only with a price; worn pieces without one get "Add a price". The three cheapest and up to three dearest, never the same piece in both.
- **The wardrobe graph** follows section 11 of the engine doc: every item not archived or retired counts as clean and at hand, nothing counts as worn lately, and the weather comes from each season, so the numbers move only when the wardrobe does. A good outfit scores 0.7 or more for one of the person's occasions (chosen in onboarding or Settings, or in the usual week) and one of the four seasons. "Distinct" means distinct core pieces, so outfits that differ only in a watch count once; an accessory's versatility is the good outfits it finishes (fit 0.7 or more, in a slot the template allows). Large wardrobes go through the planner's spread beam search (D38), so counts there are of the outfits found, not every possible one. Coverage is counted in full and shown up to 10, then "10+". Without any occasion chosen there's nothing to measure against, so versatility, orphans, coverage, and declutter are left out and the page asks for occasions.
- **Rescue** for an orphan is one sentence from the reason file, the first that applies: nothing owned for a slot it needs; a level of dress outside every occasion; a slot it pairs badly with (best pairing under 0.65); or partners that pair with it but not with each other. The last two suggest a plain neutral that contrasts with it in lightness, never a product.
- **Declutter:** not worn for six months (or never, and owned six months) and in fewer than two good outfits. It's a suggestion to look again, nothing more.
- **Caching:** measuring runs the engine for every occasion and season, so the result is kept in process per user, wardrobe version, engine version, occasions, and number of reactions (eight at most, like the pair cache).
- **Charts:** plain bars in neutral ink with the number beside each, colour only as the swatch for a colour family, and a table for screen readers behind the months chart; no chart library.
- **Navigation:** Insights takes Settings' place in the main navigation and the phone's tab bar, which keeps five tabs; Settings stays in the avatar menu, as the design system has it. Home shows one fact from the same response, a different one each day.

**Rejected:** wear counts stored on items (a second copy that can drift from the wear log); counting every possible outfit in large wardrobes (seconds per request on the server); estimated cost per wear for unpriced pieces.
**Revisit if:** measuring is slow on the server for big wardrobes (move it to a background job), or M8's purchase analyzer needs the graph with and without a candidate (it will reuse `measure`).

## D44. A good outfit is dressed for its occasion; what a purchase adds, and how it's measured

**Why:**
- **Dressed for it.** A good outfit for an occasion now needs its mean formality inside the occasion's range as well as a score of 0.7. The occasion is 15% of the score, so a casual shirt, chinos, and loafers scored 0.82 for an interview, and the coverage map showed interviews as covered by casual clothes, hiding exactly the gap people need to see. This is the same rule packing uses (D41). It applies to the wardrobe graph (versatility, orphans, coverage in Insights) and to shopping; suggestions are unchanged and still offer a near outfit with its caution, so `ENGINE_VERSION` stays 1.2. Enumerated combinations off the level are dropped before scoring, which took gaps on a 150-item wardrobe from 1.9 s to 0.5 s.
- **What a candidate adds.** For each occasion and season, the engine runs with the candidate fixed in place and counts the good outfits that need it. Outfits without it don't change, so coverage afterwards is coverage before plus those; a property test on random wardrobes checks this against a full recount. "Distinct" means distinct core pieces, as in D43. An accessory makes no new outfit, so it's judged by the good outfits it finishes and can be at most Consider; fragrance and grooming go by duplication alone.
- **Value.** Good outfits for one occasion and season are worth log2(1 + n), counting at most ten (section 1.2 of the shopping doc). Only occasions and seasons with fewer than ten can gain, so gaps and the budget split run the engine only there.
- **Likeness.** The doc's weights (category 0.35, colour 0.35, pattern 0.15, formality 0.15), with colour closeness falling from 1 to 0 over 0.15 apart in OKLab (white and cream about 0.6, navy and black about 0.2). At 0.8 a candidate duplicates what's owned: Skip, naming it. Buy needs likeness below 0.7, not the doc's 0.6: kind, pattern, and level alone make 0.65, so 0.6 would rule out a second pair of chinos in any colour. Buy also needs two or more new outfits, a coverage gain above zero and in the top third of what single staples would add to this wardrobe, and a price within the person's usual spend for its kind of clothing when both are known.
- **Gaps** rank single staples by coverage gain. An occasion and season with nothing, which no single staple can open (an interview needs a shirt, trousers, and shoes), gets the fewest staples that together make a first good outfit there, each later set building on the earlier ones ("navy blazer, with the pieces above").
- **The starter capsule** adds, one step at a time, the staple with the most gain; when no single staple adds anything (an empty wardrobe), the step is a whole outfit, the one with the most gain per piece among the 50 good in the most occasions and seasons. Costs are the person's usual spend per kind of clothing, never prices; stages of three pieces; twelve at most.
- **The budget split** records, for each new outfit, the set of candidates it needs as a bit mask, so any subset's coverage can be counted without running the engine again. Up to twelve candidates, every subset is compared, with a sum-over-subsets pass (n x 2^n steps). Past twelve, it's greedy by gain per rupee, where a step can be the missing pieces of an outfit that needs several, then compared with the best single piece. On 300 random cases of eight candidates, greedy reached 98% of the best on average, the best itself in four cases out of five, and two thirds of it at worst.
- **Projected cost per wear** is an estimate, labelled as one: the price over the wears a year the person's other pieces of the same category get since they started logging. Hidden without a price, a month and five days of wear logs, or similar pieces owned for two weeks.

**Rejected:** counting a casual outfit as covering an interview; running every staple against every occasion and season on each visit with no cap (12 s on a 150-item wardrobe locally); recounting coverage for each of 4,096 subsets; letting an accessory be Buy on coverage it can't add.
**Revisit if:** the golden set or the owner's own purchases disagree with the verdicts; people want a Buy for a first watch or belt (it would need its own measure).

## D45. The shopping list, the Style Guide, and the navigation

**Why:**
- **Candidates** are described like items (`candidates`): typed in, or a staple added from gaps, the capsule, or the Style Guide. A price is stored with the time it was given and never shown without it. A link is stored only if it starts with http or https, opened with `noopener noreferrer nofollow`, and never fetched in M8. Statuses: considering, buy next, later, skipped, and bought, which only "I bought it" sets.
- **The analysis** is worked out when a candidate is viewed and stored on its row with a key of everything it depends on: wardrobe version, engine version, occasions, styles and colours, reactions, sections, budgets, and the candidate's own attributes and price. The list shows a verdict only while its key is current, and "Not checked yet" otherwise, so a list never runs the engine for every row.
- **Pair scores** for candidates and staples go in a copy of the pair cache, since their attributes can change without the wardrobe version changing.
- **Insights cache.** The measures cache (D43) is now also keyed on the styles, preferred and avoided colours, and fit preference, which change scores; before, changing them left Insights stale until the wardrobe changed.
- **Buying.** "I bought it" creates the item through the same code as adding one, moves the candidate's photo to it (photos carry `candidate_id` until then, and are never cleaned up as unattached), and so changes the wardrobe version: suggestions, plans, insights, and every analysis follow. This is the loop for building a wardrobe from nothing: the capsule says what to buy first, the list holds it, and buying it makes it part of the wardrobe the next plan works from.
- **Limits:** 200 candidates per person; 300 analyses, gap lists, plans, and splits an hour.
- **Reference data.** Staples (`archetypes.json`) and the Style Guide's text (`guide.json`, new: each fabric's feel, best seasons, care, label, and what to watch out for, and the colour basics) are loaded into `archetypes` and `guide_entries` like the other seed files. The guide's statements about what WearWise checks match the engine's rules (colours that compete, belt and shoes).
- **Navigation** follows the design system now that there are more sections: the sidebar has Home, Wardrobe, Outfits, My Week, Shopping, Insights, and Style Guide; the phone has four tabs and More, which replaces D43's five-tab bar. The Style Guide's brand notebook is the same brand notes as Settings.

**Rejected:** analysing every candidate whenever the list loads (slow on a small server); a copy of the staples in the frontend; fetching shop pages for a pasted link (M9, under the rules in the shopping doc).
**Revisit if:** analyses are slow on the server for big wardrobes (work them out after saving, in the background), or people want the list's verdicts without opening each one.

## D46. Real products: shop searches, one pasted page at a time, and a demo catalogue only with a checked licence

**Why:**
- **Shop search links.** A staple or a candidate becomes search words (colour, kind, and "men" or "women" when the profile has one section), linked to each shop's own search page: Myntra, AJIO, Flipkart, and Amazon, with the address formats each site uses (checked October 2026; they're one list in `adapters/products.py`). There are no price filters in the links: the shops don't document them and they change often, so the person's usual spend is shown beside the links instead ("Look for under ₹2,000"). Nothing is fetched; the person browses there. Opened with `noopener noreferrer nofollow`.
- **A pasted link** is read by `adapters/pages.py`: one page, the one the person asked about, and only its link-preview data (Open Graph and schema.org Product: name, brand, picture, price, colour, material). Its rules:
  - robots.txt is obeyed under the name "WearWise", and one that can't be read (refused, an error, a timeout) counts as a no; a missing one (404) allows;
  - no cookies, no login, nothing worked around: a login page or a bot check is just "not a product", and the person fills in the form;
  - only public addresses: the host is resolved, every address must be public, and the connection goes to the checked address (so a link, or a redirect, can't point the server at its own network or a cloud metadata address); http and https on the standard ports only, no passwords in links;
  - five seconds, one retry for a server error or timeout, three redirects, 2 MB;
  - what was read is kept a day in `link_previews` (shared, page data only, nothing about who pasted it), and a failure for 30 minutes, so a page is read at most once a day;
  - 30 reads an hour per person.
- **Suggestions, never guesses.** Page text is untrusted: trimmed, length-limited, and stored as plain text. Category, colour, and fabric are suggested only where their seed names appear in the page's own words, and the person checks every field before saving. A price in another currency is reported, not converted. A candidate counts as "from a link" (and its price as "checked" on that day) only when the page's details were actually read; a link that couldn't be read is kept on an ordinary entry. Prices noted or checked more than a day ago say "may have changed".
- **Pictures stay at the shop.** A candidate from a link keeps the page's picture address and the browser loads it from the shop, without a referrer; nothing is copied to our storage. M11's content security policy needs to allow https images for this.
- **The demo catalogue** (`catalog_products`) is loaded by `make catalog file=...` from the "Fashion Product Images" dataset's styles.csv. The dataset's licence couldn't be confirmed (its mirror's card has no licence), so nothing is loaded or committed; the owner checks the licence on the dataset's own page first. Labels map onto seed categories and colours only where the match is clear (the rest are skipped and counted); no seasons, and a pattern or fabric only when the name states one. Demo products have no price, no buy link, and a "Demo" label everywhere. For a staple or candidate, the catalogue's products of the same kind are weighed (the 30 closest in colour), duplicates of what's owned left out, and ranked by coverage gain times one minus likeness; they're hidden entirely while no catalogue is loaded.
- **No affiliate or product API**: none has been applied for (section 2.3 of the shopping doc lists what's known).

**Rejected:** fetching shop search results (that's scraping, and the shops' bot checks are there to stop it); copying product pictures; guessing a category or colour from a picture of someone else's product; loading a dataset whose licence isn't known.
**Revisit if:** a shop changes its search addresses (update the list), an affiliate programme approves the app (adapter 5), or the owner confirms the dataset's licence (load it, and mention its source on the page).

## D47. The stylist and photo tagging: one provider, tools over our own code, and nothing changed without a yes

**Why:**
- **Provider.** Anthropic's API, with the Claude Haiku 5.5 model for both chat and images (checked October 2026): it takes images, calls tools, and follows a schema; its commercial terms say customer content isn't used to train models, which matters for wardrobe photos (Gemini's free tier, by contrast, may use content to improve Google's products); and price trackers list it at about $0.10 per million input tokens and $0.50 per million output under 100,000 tokens, roughly a quarter of a US cent per chat message. It's called with Python's own HTTP client (no SDK), 30 seconds, one retry when busy or erring. Everything vendor-specific is in `adapters/ai/`; settings are `AI_PROVIDER` (off, fake, anthropic), the key, the two model names, the daily cap, and the prices that turn token counts into spend. Off by default: the Stylist leaves the navigation and the photo button disappears. The fake (scripted turns, or one honest round trip with "a test reply from the fake provider") is refused in production.
- **The chat loop.** Each message goes with the system prompt, the last eight messages (each earlier reply's cards written out with names and ids, so "swap the shoes" finds the outfit), and the tool list. Read tools call the same services as the pages (wardrobe search, suggestions, the week, insights, gaps, the shopping list and analysis, shop searches, the guide), as the logged-in person, with results capped at 6,000 characters. The model ends by calling `reply` with its text and cards; up to five tool calls, then `reply` is required.
- **Grounding.** Every id in a card must have been returned by a tool in this conversation (stored per reply) and still belong to the person; text may contain no ids. A failed reply goes back once as an error on the `reply` call; a second failure is replaced with an apology and the cards the tools actually returned. A plain-text answer is held to the same rule.
- **Nothing changes without a yes.** Saving an outfit, planning a day, adding to the list, and logging a wear are `propose_` tools: the server checks the pieces (owned, a whole outfit) and stores a pending `chat_actions` row shown as a card with Confirm and Not now. Confirming runs the app's own code; cancelled or done proposals can't be confirmed again. Text from pages, names, and notes reaches the model only inside tool results, which the prompt calls data.
- **Limits and spend.** 6 messages a minute and 40 a day per person (10 for the demo account), 20 tagged photos a day (3 for demo), and a global daily cap (`AI_DAILY_SPEND_CAP_USD`, default $1) checked before every call; tokens and cost go to `ai_usage`, and a failed message's tokens still count. When unavailable, the page says why (off, resting until tomorrow, didn't respond) and nothing else is affected.
- **Photo tagging** sends only the stored 400 px image, with a schema whose choices are the app's own category, colour, pattern, fabric, and fit ids; anything else is dropped, and every filled field is marked for checking (fabric: "check the label"). It runs only when the person presses "Fill in from the photo".
- **Checking the real model.** `make eval-stylist` asks the doc's twenty questions (plus a planted instruction in the shopping list) with the real model on a throwaway demo account, counts grounding failures, prints every answer for reading, and deletes the account. It costs a few cents and is run by hand before release.

**Rejected:** a vendor SDK (a dependency for one HTTPS call); letting the model write data directly; checking prose for invented items (unreliable; items appear only as cards, by id); a free tier that may use photos for training.
**Revisit if:** the provider's prices or terms change (the prices are settings), answers are slow on the server, or the evaluation finds invented items.

## D48. Interaction and polish: gestures with plain equivalents, a dark theme from the tokens, and small tools counted from rows

**Why:**
- **Dark theme.** Every colour was already a CSS variable, so dark is the same tokens with other values under `:root[data-theme="dark"]`; no component has its own dark styles. Two tokens were added for text on filled shapes (`on-ink`, `on-light`) so nothing writes `white`. The choice (Like this device, Light, Dark) lives in the browser, not the account: it's about the screen, and it has to apply before the page paints, which a server round trip can't. A test measures every text pair and input edge in both themes.
- **Gestures, without libraries.** Dragging uses the browser's own drag and drop; swiping uses pointer events. Each is a few dozen lines, and each has a plain equivalent that sends exactly the same request (pressing a piece; Like and Dislike), which the tests check. Swipes ignore the mouse and need a clear sideways move, so scrolling never rates anything. Native drag and drop doesn't work with a finger, so phones press pieces instead.
- **Undo instead of "are you sure?"** where undo is honest: archiving, skipping a candidate, deleting a conversation (which waits until the toast closes). Deleting an item or a candidate still asks first, because a photo can't come back.
- **Live score.** `POST /outfits/check` also returns the engine's score, whether it's good, and its reasons once the pieces make a whole outfit. The season stands in for the weather, so it never waits on a forecast. Trying a candidate on (`POST /candidates/{id}/try`) scores it with chosen pieces as if it were owned; nothing is saved.
- **The colour map** plots each piece at the engine's own hue and lightness (OKLCH), with neutrals on their own strip, as plain SVG; each colour family is a button that filters the wardrobe. **A coverage square** opens to its outfits, worked out the same way as the map (the steady wardrobe, the season's weather), so the counts match.
- **Sleep on it.** A candidate can hold a day (`remind_on`, one week to one month ahead in the app, up to a year in the API). On that day the shopping list asks "Still want it?", with Keep or Skip. There are no emails or notifications: the app has no way to send them, and the question waits on the list.
- **Wear what you own.** Only the start day is stored, on the profile; progress is counted on every request from the wear log between the start and day 60, over the pieces in the wardrobe now. Nothing is estimated, and stopping keeps the wear log as it is.
- **Remix.** Two to ten of the person's own pieces, scored like the coverage map for each of their occasions this season, with the same 0.7 threshold as everywhere else; each outfit can be saved. Pieces that aren't the person's (or are archived) get 422 with the field named, as `/outfits/check` does for a list in a body; routes with an id in the path still answer 404.
- **Quick jump** (Ctrl or Cmd + K) is a fixed list of pages and actions plus the existing item search; the Stylist is listed only when it's switched on.

**Rejected:** a drag-and-drop or gesture library (two dependencies for what the browser does); a chart library for one plot; keeping the theme on the account; push or email reminders; storing challenge progress (it would drift from the wear log).
**Revisit if:** people want to drag with a finger (that needs pointer-based dragging), reminders need to reach people outside the app (that needs an email service), or days should follow the person's time zone (the server counts days in UTC, so in India a new day starts at 05:30).

## D49. The security pass: checks that walk every route, headers on both apps, and narrower photo decoding

**Why:**
- **Every route, checked by walking them all.** A test reads the API's own schema (the list of every route it serves) and calls each one: without a login, every route outside a short public list (health, register, log in, log out) must answer 401; without the custom header, every change must answer 403; and a made-up id must answer 404, never 500. A new route that forgets any of these fails CI. A floor on the number of routes stops the test passing by walking nothing (it once did, when FastAPI started including routers lazily).
- **A budget for changes.** Every change a person makes counts against 1,000 an hour, far above use by hand; the costly routes (uploads, suggestions, plans, place search, shopping, links, the stylist) keep their tighter limits. It's counted in Postgres like the other limits, so it survives restarts.
- **Headers.** The web app sends a content security policy: scripts, styles, fonts, and requests only from this site, no framing, forms only to this site, no plugins. Scripts may be inline, because Next.js puts its page data in inline scripts; the strict alternative (a fresh nonce per request) would make every page render on demand and lose the cached pages. Images may come from any https address, because shop pictures are shown from the shop. Also: no MIME sniffing, no framing, a strict referrer policy, no camera, microphone, or location, and HSTS. The API sends a policy that allows nothing at all (it serves JSON and images), no-store caching except for photos (which set their own private caching), and same-origin resource policy. The interactive docs get no policy, since they load from a CDN.
- **Photos.** Pillow 13 (eight advisories in 12.x, all in decoders for formats we refuse). Uploads are now opened with only the JPEG, PNG, and WebP decoders; before, Pillow tried every decoder it has to identify the file, and only then did we refuse anything that wasn't a photo. A test proves the TIFF parser never sees an upload.
- **The log-in redirect** is resolved the way the browser will resolve it, then refused unless it stays on this site. The old prefix check passed "/(tab)/elsewhere", which browsers turn into "//elsewhere".
- **Dependency audit.** `make audit` checks the packages the live app runs on (`pip-audit` through `uvx`, and `pnpm audit --prod`; neither is added to the project). It runs weekly in GitHub Actions and by hand, not on pull requests, so a new advisory can't block unrelated changes and deploys. Development-only advisories are read and judged: today's one (braces, inside Next's lint plugin, with no fixed release) only ever sees our own file patterns.

**Rejected:** nonce-based CSP (loses static and cached pages); per-route rate limits everywhere (one budget is simpler and the costly routes already have their own); auditing on every pull request.
**Revisit if:** Next.js can attach nonces without dynamic rendering, or an advisory lands in a runtime package.

## D50. Privacy: an export read from the schema, one rule for what's a person's, and nothing personal kept forever

**Why:**
- **What's a person's is decided by one rule**, read from the schema: a table with a `user_id` pointing at `users`, or a table that hangs off such a table and is deleted with it. Both "Download my data" and "Delete account" follow it, so a table added later is exported and deleted without anyone remembering to. A test fails if a table is neither the person's nor listed as shared, and another if anything pointing at a user doesn't cascade. A third fills an account through the API (items, photos, outfits, the wear log, suggestions and reactions, events, the plan, a trip, the shopping list, a conversation), deletes it, and checks that none of its rows and none of its photo files are left, while another account's are untouched.
- **The export** is a zip: `data.json` (every row, one list per table, with the app's own column names), every photo at the stored size, and a README explaining the format. It leaves out the password hash and login sessions. It's built in a temporary file that moves to disk past 16 MB, so a large wardrobe doesn't sit in the server's memory, and streamed in chunks. Five a hour per person, since it reads every photo.
- **Nothing personal is kept forever by accident.** Rate-limit counts can name an IP address; they were deleted only when the same visitor came back, so now every count also removes anything over a day old. Photos uploaded but never saved were cleared only by their owner's next upload; now any upload clears everyone's day-old leftovers, fifty at a time.
- **The privacy page** says in plain words what's stored, what's in the browser (one session cookie and the theme choice), which service sees what (Vercel, Render, Neon, Backblaze, Open-Meteo, Anthropic only when the stylist is on and used, and shops only for pasted links and their own pictures), and how to download or delete. It links to the public repository for questions.

**Rejected:** a list of tables kept by hand (it would drift); exporting photos as links (they're private, and links would expire); keeping rate-limit rows until their visitor returns.
**Revisit if:** exports grow past what a request can build in time (then build it in the background and send a link), or the project gets a contact address of its own.

## D51. Observability without another service: request ids, JSON logs, errors in a table, and an owner's page

**Why:**
- **No error-tracking service.** A hosted tracker (Sentry, for example) is the usual answer, but it adds two SDKs, a third service that would receive stack traces and page addresses, and an account to keep; at this size, the database already in use does the job. Unexpected server errors and browser errors go to `error_events` with no account attached, are kept 30 days, and show on the owner's page.
- **One id per request**, made in the browser and kept by the server (or made there), on every log line, every answer, and every recorded error. A person who sees a 500 sees "mention reference ...", which finds the log lines. The server's answer to an unexpected error says nothing about what broke.
- **Logs as JSON in production** (readable text in development), with the route's pattern instead of the path, and no query string or IP address, so the logs hold no ids, searches, or addresses. The browser's error reports keep only the page's path for the same reason.
- **The owner's page** is for accounts listed in `ADMIN_EMAILS`; everyone else gets the same 404 as a missing page, so nobody learns it exists. A setting rather than a role in the database: there is one owner, and a database flag would need a way to set it. Acceptance per engine version counts each suggestion once if it was liked, saved, or worn, from the suggestions table itself.

**Rejected:** a hosted error tracker for now; logging IP addresses and query strings; an admin role in the database.
**Revisit if:** there are enough people that grouping and alerting errors are worth a service.

## D52. The demo: a fresh copy for each visitor, deleted a day later, tidied when the server starts

**Why:**
- **A copy each, not one shared account.** The roadmap asked for one demo account reset nightly. With one account, every visitor sees what the last one changed (or deleted), and the reset needs a scheduled job, which the free plans don't offer. Instead, "Try the demo" makes a fresh account for the visitor: the staples for the section they choose (menswear or womenswear: the app's sections, not a gender), and the profile in `seed/demo.json` (occasions, usual week, styles, city). It's logged in at once with a session cookie; its address ends in `.invalid` and its password is random and never shown, so the cookie is the only way in. Nothing is shared between visitors.
- **Deleted a day later**, with everything in it, by the same cascade as account deletion (D50). The app says so in a note at the top of every page, with the time, and links to making a real account. The demo script's named demo accounts are left alone.
- **Bounded.** Ten demos an hour per address, and at most 300 running; past that, the oldest goes first. Demo accounts already have lower stylist limits (D47).
- **Housekeeping without a scheduler.** Expired demos, unsaved photos, old error reports and rate-limit counts, and ended sessions are removed by `scripts/housekeeping.py`, which runs in the start command (and never stops the start). The free server sleeps after a quiet spell, so it starts, and tidies, often; starting a demo also clears expired ones first.

**Rejected:** one shared demo account (visitors would see each other's changes); a paid cron job or an outside scheduler for one tidy-up; logging in to a demo with a shared password.
**Revisit if:** the server stops sleeping (a paid plan), so starts become rare: then run housekeeping on a schedule.

## D53. The performance pass: indexes for every link to a person's data, measures kept in the database, and numbers written down

**Why:**
- **Measured first.** A wardrobe of 300 items, 100 outfits, a year of wear logs, and about 480 suggestions, timed through the API with its SQL queries counted (locally, so production on a tenth of a CPU will be slower): lists, an item, outfits, and the wear log answer in 20 to 40 ms with 6 to 13 queries, the same number of queries however long the list; a suggestion 0.2 s; checking or remixing an outfit 40 to 60 ms; Insights 3.4 s the first time after a change and 70 ms after; a candidate's analysis 1.8 s first, then stored; planning the week 1.1 s; the export 0.1 s; deleting the account 60 ms. At 60 items Insights takes 0.5 s and the analysis 0.3 s; at 120, 1.2 s and 0.6 s.
- **Indexes for every link to a person's data.** Postgres doesn't index foreign keys by itself, so deleting an outfit, a wear log, an item, a custom category, or an account had to scan whole tables for what pointed at them (suggestions, kept indefinitely, the largest). Eight indexes, partial where most rows are empty, and a test that every link to a person's data has one.
- **Insights' measures kept in the database.** They were cached in the server's memory, which the free server loses whenever it sleeps (after 15 quiet minutes), so most visits worked them out again. Now the latest measures are saved per person under the same fingerprint (wardrobe version, engine version, occasions, styles, colours, reactions, seasons); they're worked out again only when one of those changes.
- **Tried and dropped:** remembering scores inside each scorer. Profiling showed 340,000 scorings for 42,000 different outfits, but the repeats are across the sixteen occasion and season searches, not within one (2% hits), so it changed nothing and was taken out. Sharing the pair part of the score across those searches would save about 40% of the first Insights load; it's left for when a large wardrobe needs it.
- **Pages.** Photos already load as 400 px WebP thumbnails, lazily, with their size set; full size only on an item's own page. JavaScript, compressed: about 240 KB on the landing page, of which about 150 KB is React and Next.js itself, and 380 to 410 KB on app pages. Nothing stood out to cut without restructuring.

**Rejected:** a cache service (Redis is on the not-used list, and Postgres does it); memoizing scores per scorer (measured, no gain).
**Revisit if:** wardrobes past a few hundred items become common, or the server moves off the free plan's tenth of a CPU (then the first Insights load and the week plan are the places to work on).

## D54. End-to-end tests: the five journeys, accessibility, and keyboard, on every pull request and daily against production

**Why:**
- **Playwright with axe**, the tools the architecture doc named, as development-only packages pinned to releases at least two weeks old (`@playwright/test` 1.64.0, `@axe-core/playwright` 4.13.0): a brand-new release is where a bad publish would show up first.
- **What runs.** The five journeys from the architecture doc in order, by one new person (sign up, add an item with a photo, build and save an outfit, get suggestions and like one, check a purchase), then deleting the account through Settings; axe (WCAG 2.1 A and AA) on four public and fifteen app pages in both themes; and keyboard checks (skip link, a focus ring on every Tab stop of five busy pages, dialogs that hold and return focus). Each at desktop and phone size: 32 tests, under a minute.
- **Few accounts, nothing left behind.** Each run makes one account and one demo per size and deletes them, so it stays inside the sign-up and demo limits and leaves an empty database (checked: zero users after a full run on a fresh stack).
- **Where.** On every pull request, against a fresh stack in CI (Postgres, the API with canned weather and pages and the stylist off, and a production build of the site), so Render deploys only after they pass. Daily against the live site, which also serves as the uptime check: a failure emails the owner, and one run a day doesn't keep the free server awake. Locally, `make e2e` against `make dev`; `E2E_CHANNEL=chrome` uses Chrome already on the machine instead of downloading Playwright's.

**Rejected:** a separate uptime service (frequent checks would keep the free server and database awake); tests that share one long-lived account (they'd depend on what the last run left).
**Revisit if:** the suite grows past a few minutes, or the limits it stays inside change.

## D55. Agents on LangGraph, with LangChain only for the model integration

**Why:**
- **What three agents need.** Graphs with conditional edges (the grounding retry; the digest's check, then template wording). Checkpoints in Postgres, so a run that dies resumes: a Trend Scout run doesn't pay for its searches twice, and a digest that died between writing and sending doesn't call the model again. Pauses for a person's yes (the Stylist's Confirm). Retries per step. One hand-written loop was fine for the chat (D47); three agents, two of them on a schedule, are a framework's job, and the graphs are the part of an agent project worth reading.
- **Versions, checked October 2026.** langgraph 1.2.16, langchain 1.4.6, langchain-core 1.6.12, langchain-anthropic 1.7.6, langgraph-checkpoint-postgres 3.2.0, all MIT licensed. They install and run on Python 3.14: a test graph paused and resumed, although langgraph's package metadata lists Python only up to 3.13. Pinned to exact versions when added.
- **LangChain for the model only.**
  - It provides one chat-model interface for any provider, tool binding, and structured output.
  - The Stylist uses `create_agent`, with middleware for its tool-call limit and its pause for confirmation.
  - Not used: chains, vector stores, document loaders, retrievers, or memory classes.
- **A partial reversal of D47's "no vendor SDK".** The model integration brings the provider's SDK, and langchain-core brings `langsmith`, which is installed but unused unless tracing is on. Photo tagging stays on the M10 adapter until it's next changed.
- **The engine rule is unchanged.** Agents reach data only through services, so an agent can't answer differently from the pages.
- **Memory.** The conversation stays in `chat_messages`, which the page, the export, and deletion already use. Checkpoints hold only an unfinished run, and are deleted when it ends. Keeping conversations in checkpoints would store a second copy of every message, written again at every step, on a 1 GB database.
- **Tracing is off in production.** A tracing service would receive prompts that carry wardrobe data. It's allowed for Trend Scout runs, which carry no personal data, and for local runs.

**Rejected:**
- The hand-written loop for the new agents: three loops, each with its own resume and retry code.
- LangChain's chains and memory classes: the graphs are explicit instead.
- A hosted agent service: one more service holding wardrobe data.
- Checkpoints as the chat's memory.

**Revisit if:** new releases keep breaking the pinned versions, or a smaller library covers checkpoints and pauses.

## D56. Scheduled jobs on GitHub Actions

**Why:**
- **The free server sleeps** after 15 quiet minutes, so a scheduler inside it wouldn't fire. D52 avoided needing one by tidying up whenever the server starts; the agents need to run at set times.
- **GitHub Actions** (checked October 2026):
  - free for public repositories on GitHub's standard runners;
  - a manual trigger;
  - a time zone on schedules (`Asia/Kolkata`).

  The jobs run on GitHub's machine and exit, so they don't keep the free server awake or share its tenth of a CPU.
- **Built around its limits.**
  - Scheduled runs can be delayed or dropped at busy times, most often on the hour: hence odd minutes, and a two-day catch-up for the digest.
  - They run only from the default branch.
  - They switch off after 60 days without activity in a public repository; the owner's run report is how a missed run is noticed.
  - Failure emails go to whoever last changed the schedule line.
- **One at a time.** Each workflow has a `concurrency` group, and each job holds a "running" row per kind in `agent_runs` (a partial unique index, lapsing after 2 hours). Postgres advisory locks belong to a database session, and Neon's pooled connections don't keep one, so they aren't used.
- **The cost.** The production database address and the keys live in a GitHub environment as well as on Render. The workflows never run on pull requests.

**Rejected:**
- A scheduler inside the API, which sleeps.
- A paid cron service, or a paid server that never sleeps.
- An endpoint on Render for GitHub to call: the job would run inside a request on a tenth of a CPU, and GitHub would still need a secret.

**Revisit if:** the server moves to a plan that doesn't sleep, or the repository becomes private (then Actions minutes count).

## D57. Email: Resend, confirmed opt-in, an allowlist until a domain is verified, and signed links

**Why:**
- **Resend** (checked October 2026): 3,000 emails a month, 100 a day, up to 3 domains on the free plan, and an `Idempotency-Key` header that is remembered for 24 hours. It sits behind an `EmailSender` adapter, with a console version and a fake.
- **An allowlist until a domain is verified.** Without one, Resend sends only to its account owner's address, and the app's `vercel.app` address can't be verified because its DNS isn't ours. So `EMAIL_ALLOWLIST` limits all sending until a domain is bought, and the app labels digests as a preview meanwhile. The owner's run reports work from the start.
- **Confirmed opt-in instead of verifying every sign-up.** Turning the digest on sends a confirmation link; following it sets `email_verified_at` and the opt-in time. Sign-up and the demo stay as they are, and the only people emailed are those who asked and proved the address is theirs. Demo accounts can't opt in.
- **Links.**
  - **Signed:** unsubscribe and "not for me" links carry a signature (`EMAIL_LINK_SECRET`) and do one thing each, so they work from the email without logging in.
  - **Single use:** confirmation (and password reset, if built with it) uses single-use tokens stored as hashes, which expire.
  - **One-click unsubscribe:** mail apps send it as a POST without the header the app requires against cross-site requests, so that one route is guarded by its token instead, and the route audit lists it as public.
- **Once a week is the database's job**: one digest per person per week, by a unique key. The provider's 24-hour key only covers a retried send.

**Rejected:**
- Verifying every address at sign-up: it changes sign-up for everyone, and emails people who didn't ask.
- Sending from a free mailbox's address through the provider: it fails the mailbox's own authentication checks.
- An unsubscribe link carrying only the account's id.

**Revisit if:** a domain is verified (then empty the allowlist), or sending nears the free plan's daily limit.

## D58. The Trend Scout: Tavily, twice a week, two sources per trend, and approval as a status

**Why:**
- **Tavily** (checked October 2026) has:
  - 1,000 credits a month free (a basic search is 1 credit, an advanced one 2);
  - a past-month window, preferred and blocked site lists, and a country boost;
  - the credits used, reported in each response.

  It's called over HTTPS behind a `WebSearch` adapter, with a fake and no SDK. Its terms let it keep queries and train models on them, so queries carry no personal data: they're built from the season, the sections, style names with counts, and the festive calendar.
- **Twice a week**, Tuesday and Friday early in the morning in India: fashion moves slower than news, and this leaves time to approve trends before the Sunday digests. About 8 credits a run and about 70 a month, with a monthly cap in code (`SEARCH_MONTHLY_CREDIT_CAP`) counted from what the responses report.
- **What counts as a trend.** Two sources from different sites within 45 days, each with a quote found word for word in the text that was read; values only from the seed lists; nothing about bodies. The lists of preferred and blocked sites and the festive calendar are seed data the owner reviews.
- **Approval is a status, not a pause.** New trends wait as pending until the owner approves or rejects each one on the admin page, and digests use approved trends only. A run paused for days would block the next scheduled run, and approving some of a run's trends doesn't fit a single resume. Pausing a run is used where it fits: the Stylist's Confirm.
- **No article images** anywhere, because of copyright.
- **The owner** is whoever is in `ADMIN_EMAILS` (D51), not a new column on users.

**Rejected:**
- Running every 12 hours: mostly repeats.
- Reading shop listing pages for trends.
- Showing trends straight from the model, without approval.
- Holding the run open until approval.

**Revisit if:** the free allowance or prices change, or approved runs are reliably right (then `TRENDS_REQUIRE_APPROVAL=false`).

## D59. The checkpointer's tables: made by the library, ignored by Alembic, deleted by thread

**Why:**
- **Not an Alembic migration.** The checkpointer's `setup()` creates four tables, versions them itself, and builds indexes with `CREATE INDEX CONCURRENTLY`, which can't run inside a migration's transaction. So a start step (`scripts/agent_setup.py`, safe to repeat) calls `setup()` after the migrations, the jobs call it too, and Alembic's autogenerate is told to ignore the four tables; otherwise it would offer to drop them.
- **It works through Neon's pooler.** It connects with autocommit and without prepared statements, the library's own default.
- **Deletion and export.** The tables have no `user_id`, so the rule that makes deletion complete (D50) can't see them. Instead:
  - **Thread ids name the owner:** `chat:<thread id>`, `digest:<user id>:<week>`, `scout:<run id>`.
  - **Deleting an account** deletes the person's threads, and a test checks nothing is left.
  - **The export** leaves them out as run state.
  - **Clean-up:** a finished run deletes its checkpoints, and housekeeping removes any left after a day, since the library has no expiry of its own.

**Rejected:**
- An Alembic migration that calls `setup()`: it fails on the concurrent index, and wouldn't follow the library's own upgrades.
- Keeping checkpoints indefinitely: they hold conversation state and grow at every step.

**Revisit if:** the library gains a built-in expiry, or a way to create its tables inside a migration.
