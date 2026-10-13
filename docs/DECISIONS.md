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
