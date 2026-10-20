# WearWise

Know what to wear, see what your wardrobe is missing, and make every purchase count.

WearWise is a personal wardrobe and styling web app. You catalogue everything you wear, including shoes, accessories, and fragrance. It suggests outfits from what you own and explains why they work, plans your week around weather and laundry, and tells you what a new purchase would add before you buy it.

It is not a store. There is no checkout. When WearWise points to a product, you buy it on the retailer's site.

## Status

Live at https://wearwise-rouge.vercel.app. Milestone M1 adds the design system and accounts: register, log in and out, a styled app shell, and deleting your account. M2 adds a skippable six-step setup (sizes, measurements, occasions, style, colours, budget), Settings to change or clear every answer, and brand size notes. M3 adds the wardrobe: add items with a photo (the colour is suggested from it), search, filter, sort, edit, archive, matching sets, and categories of your own. M4 adds the Outfit Studio (build an outfit slot by slot, with finishing touches), saved outfits (favourite, duplicate, swap a piece), and a wear log (“I wore this today”, wear counts, and wears since washing). M5 adds the outfit engine: ranked, varied suggestions for an occasion, “What goes with this?” from any item, and “Complete this outfit” in the studio, each with its reasons; like, dislike, save, or wear a suggestion, and likes and dislikes change what comes first next time. M6 adds My Week: a seven-day plan from your usual week, events, the forecast for your city (or your own setting when there isn't one), and what's clean, with lock, swap, and plan again; a laundry view; and packing lists for trips. M7 adds Insights: what you wear most and least, cost per wear (only where you've given a price), which pieces go with the most and which are stranded (and what would help), how many good outfits you have for each occasion and season, the style your wears show, and what might be worth a second look. M8 adds Shopping: put something you're thinking of buying on your list and see Buy, Consider, or Skip, with the outfits it would make, where you're short, and what it duplicates; compare candidates; see which staples would add the most; plan a starter wardrobe in stages within a budget; split a budget across your list; and mark something bought to add it to your wardrobe. A Style Guide covers fabrics, styles, colour basics, and your brand notes. M9 connects that to real shops: any staple or candidate links to Myntra, AJIO, Flipkart, and Amazon searches for it, with your usual spend as a guide, and pasting a product's link fills in its details from the page (when the shop allows it) so you can see what it would add. See [`docs/PROGRESS.md`](docs/PROGRESS.md).

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

Next.js, TypeScript, and Tailwind on the frontend. FastAPI, SQLAlchemy, and PostgreSQL on the backend. Images in S3-compatible object storage. Deployed on Vercel, Render, Neon, and Backblaze B2.

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
| `make demo` | Fill the demo account (`demo@example.com`) with a wardrobe of generic staples |
| `make golden email=you@example.com` | Export a wardrobe so its owner can label the engine's golden set (`docs/ENGINE.md`, section 9) |
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
