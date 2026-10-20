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
**Revisit if:** a learned compatibility model beats the rules on the golden set (see `ENGINE.md` section 14). Even then it would sit inside the engine, not replace it with a chat model.

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
