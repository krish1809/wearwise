# Progress

The running state of the project, updated at the end of every slice. Keep it short and current.

## Now

- **Last updated:** 2026-10-11
- **Current milestone:** M0 Foundations
- **Current slice:** 6 of 7, the first deploy. Slices 1 to 5 and 7 are built and pass every check locally.
- **Next action (owner):** commit the slices on a branch, open a pull request, and wait for CI to pass. Then merge and follow "First deploy, step by step" in `docs/DEPLOYMENT.md` (Neon, Render, Vercel). M0 is done when the live URL says "API ok, database ok".
- **Overall:** 0 of 12 milestones done; M0 is close. v1.0 is M0 to M5.

M0 slices:

| # | Slice | State |
|---|---|---|
| 1 | Backend skeleton: FastAPI, settings that stop startup when a variable is missing, `GET /api/v1/health` | done |
| 2 | Local database: `docker-compose.yml` (Postgres 18 on port 5433), first migration (`app_meta`), health reads its row | done |
| 3 | Frontend skeleton: Next.js, `/api/*` rewrite to the backend, home page showing the health result | done |
| 4 | Typed API client generated from the backend's OpenAPI schema (`make api-types`) | done |
| 5 | CI: backend, frontend, and stale-API-types jobs in `.github/workflows/ci.yml` | written; first run happens on the pull request |
| 6 | Deploy: `render.yaml`, dashboard steps in `docs/DEPLOYMENT.md` | waiting for the owner |
| 7 | Docs: README quick start and commands, decisions D11 to D17 | done |

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
| Decisions | D1 to D10 | `docs/DECISIONS.md` |
| Seed data | 16 slots, 89 categories, 3 outfit templates; 28 colour families; 12 occasions; 12 style profiles; 66 archetypes. Not loaded anywhere yet: the seed script is written in M2 and M3. | `seed/` |
| Config | Every environment variable up to M10, `.gitignore`, pull request template | `.env.example`, `.github/` |

M0 code, not yet committed (see the slice table above):

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
| M0 | Foundations | open a live URL that talks to the API and database | in progress: built locally, deploy pending | | |
| M1 | Design system, shell, auth | register, log in, and move around a styled, empty app | not started | | |
| M2 | Onboarding and profile | set (or skip) sizes, style, budget; edit them later | not started | | |
| M3 | Wardrobe | add, find, edit everything you own, with photos | not started | | |
| M4 | Outfit Studio and wear log | build and save outfits; log what you wore | not started | | |
| M5 | Outfit engine (v1.0) | get ranked outfit suggestions with reasons | not started | | v1.0 release |
| M6 | My Week | plan seven days with weather, laundry, events, packing | not started | | |
| M7 | Insights | see cost per wear, versatility, orphans, coverage | not started | | |
| M8 | Smart Shopping I | analyse a purchase; see gaps; plan a capsule on a budget | not started | | |
| M9 | Smart Shopping II | find real products for a gap | not started | | |
| M10 | AI | auto-tag photos; chat with a stylist that knows your wardrobe | not started | | |
| M11 | Hardening and launch | hand the link to anyone | not started | | |

## Before M0 (only you can do these)

- [x] GitHub repo created and the docs pushed (checked 2026-10-11: local `main` matches `origin/main`)
- [ ] 25 to 30 photos of your own items taken (needed by M3)
- [ ] Accounts: Vercel, Render, Neon (needed by M0's deploy slice); Cloudflare (needed by M3 for R2)
- [ ] Optional: applied for an affiliate or product API (only matters in M9)

**Local tools (checked 2026-10-11):** Python 3.12.3, uv 0.12.23, Node 22.23.0, npm 10.9.8, Docker 29.8.0 with Compose v5.5.1, make 4.3, gh 2.45.0. pnpm isn't installed yet, but corepack 0.34.6 is available to provide it. M0's frontend slice needs pnpm.

## Log

Add an entry per slice, newest first.

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

<!--
### M5
- Hardest: ...
- Decision: ...
- Number: golden-set agreement 84%; would wear 7 of top 10 for college
-->

## Known limitations

Things that are deliberately not handled yet. Move them into the README at M11.

- On Render's free plan, the first request after 15 idle minutes takes about a minute while the backend wakes. The home page says so and keeps checking.
- The `make` commands assume Linux or macOS. On Windows, use WSL.
