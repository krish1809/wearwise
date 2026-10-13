# WearWise

Know what to wear, see what your wardrobe is missing, and make every purchase count.

WearWise is a personal wardrobe and styling web app. You catalogue everything you wear, including shoes, accessories, and fragrance. It suggests outfits from what you own and explains why they work, plans your week around weather and laundry, and tells you what a new purchase would add before you buy it.

It is not a store. There is no checkout. When WearWise points to a product, you buy it on the retailer's site.

## Status

Live at https://wearwise-rouge.vercel.app. Milestone M1 adds the design system and accounts: register, log in and out, a styled app shell, and deleting your account. M2 adds a skippable six-step setup (sizes, measurements, occasions, style, colours, budget), Settings to change or clear every answer, and brand size notes. Wardrobe features start in M3. See [`docs/PROGRESS.md`](docs/PROGRESS.md).

<!-- At each release, replace this section with the live URL, a screenshot, and what works. -->

## What it will do

- **Wardrobe:** photo-first catalogue with search and filters, for any wardrobe size and any style.
- **Outfits:** ranked suggestions for an occasion, "what goes with this?", and "complete this outfit", each with a reason.
- **My Week:** a seven-day plan that respects weather, events, and what is clean. Packing lists for trips.
- **Insights:** cost per wear, most and least worn, which items are versatile and which are stranded.
- **Smart Shopping:** Buy, Consider, or Skip for anything you are thinking of buying, based on the outfits it would add and what it duplicates. Gap analysis and a budgeted starter capsule.
- **Stylist:** a chat that answers from your real wardrobe.

## How it works

The outfit engine is deterministic Python: it scores pairs of items on colour, formality, pattern, fabric, and style, combines them into outfits, and ranks them for the occasion, weather, and what you haven't worn lately. The purchase analyzer runs the same engine with and without a candidate item and measures the difference. The AI layer only explains results and handles conversation; it calls the engine and never replaces it.

Details: [`docs/ENGINE.md`](docs/ENGINE.md), [`docs/SHOPPING.md`](docs/SHOPPING.md), [`docs/AI.md`](docs/AI.md).

## Stack

Next.js, TypeScript, and Tailwind on the frontend. FastAPI, SQLAlchemy, and PostgreSQL on the backend. Images in S3-compatible object storage. Deployed on Vercel, Render, Neon, and Cloudflare R2.

Why: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/DECISIONS.md`](docs/DECISIONS.md).

## Quick start

You need [Docker](https://docs.docker.com/get-docker/), [uv](https://docs.astral.sh/uv/getting-started/installation/), Node.js 22, and pnpm 10 (`npm install -g pnpm@10`).

```bash
git clone https://github.com/krish1809/wearwise.git
cd wearwise
make setup   # install dependencies; create .env from .env.example
make dev     # start Postgres, apply migrations, run the API on :8000 and the web app on :3000
```

Open http://localhost:3000. It should say "API ok, database ok". The API's interactive docs are at http://localhost:8000/docs.

The local database runs in Docker on port 5433, so it doesn't clash with a Postgres already installed on your machine.

## Commands

Run `make` to list them all.

| Command | What it does |
|---|---|
| `make dev` | Start Postgres, apply migrations, run the API and the web app; Ctrl+C stops both |
| `make test` | Backend tests (against a throwaway `wearwise_test` database) and frontend tests |
| `make lint` | Lint and formatting checks |
| `make format` | Fix formatting and auto-fixable lint |
| `make typecheck` | mypy for the backend, TypeScript for the frontend |
| `make migration m="add users"` | Create a migration from changed models |
| `make migrate` | Apply migrations, then load the reference data in `seed/` |
| `make seed` | Load the reference data in `seed/` again (safe to repeat) |
| `make api-types` | Regenerate the frontend's API types after changing a route |
| `make check` | Everything CI runs |

## Making a change

Most features follow the same path through the code:

1. **Model** in `backend/app/models/`, then `make migration m="..."` and read the generated file before applying it.
2. **Service** in `backend/app/services/`: the use case, with every query filtered by the current user.
3. **Logic with rules in it** (scoring, planning, analysis) goes in `backend/app/engine/` as plain functions with unit tests. The engine imports nothing from the rest of the app, and a test enforces that.
4. **Route** in `backend/app/api/`, with request and response schemas. Tests in `backend/tests/`, including one where a second user gets 404.
5. `make api-types`, then the **page** in `frontend/app/` using the typed client in `frontend/lib/api/`.
6. `make check` before opening a pull request. CI runs the same checks, and `main` deploys once they pass.

How to host it: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Documentation

| Document | Contents |
|---|---|
| [Product spec](docs/PRODUCT_SPEC.md) | Features, pages, principles, definition of done |
| [Roadmap](docs/ROADMAP.md) | Milestones M0 to M11 |
| [Architecture](docs/ARCHITECTURE.md) | Structure, auth, images, conventions |
| [Data model](docs/DATA_MODEL.md) | Tables |
| [Engine](docs/ENGINE.md) | Scoring, generation, planner |
| [Shopping](docs/SHOPPING.md) | Purchase analyzer, product sources |
| [AI](docs/AI.md) | Auto-tagging, Stylist |
| [Design system](docs/DESIGN_SYSTEM.md) | Visual direction and components |
| [Deployment](docs/DEPLOYMENT.md) | Hosting and release |
| [Decisions](docs/DECISIONS.md) | Choices made and why |
| [Progress](docs/PROGRESS.md) | Current milestone and log |
