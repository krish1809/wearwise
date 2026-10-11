# Progress

The running state of the project, updated at the end of every slice. Keep it short and current.

## Now

- **Last updated:** 2026-10-11
- **Current milestone:** M0 Foundations
- **Current slice:** not started. The M0 plan hasn't been written yet. Once it's approved, its slices go here.
- **Next action:** plan M0 against the M0 section of `docs/ROADMAP.md`, then build slice 1 (backend skeleton).
- **Overall:** planning is complete. No application code exists yet. 0 of 12 milestones are done, and v1.0 is M0 to M5.

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

**Not started:** everything in the table below. `frontend/`, `backend/`, and `docker-compose.yml` don't exist yet. There are no dev, test, lint, type check, or migrate commands yet; M0 adds them, plus the README quick start.

**Carry into M0:**

- Record the version of each tool chosen in `docs/DECISIONS.md`.
- Record synchronous SQLAlchemy with psycopg as a decision.
- Set up the `/api/*` rewrite from Next.js to the backend before auth exists. M1's cookies depend on it.

## Milestones

| # | Milestone | You can now... | Status | Released | Notes |
|---|---|---|---|---|---|
| M0 | Foundations | open a live URL that talks to the API and database | not started | | |
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

- None yet.
