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
