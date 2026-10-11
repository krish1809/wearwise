# WearWise

Know what to wear, see what your wardrobe is missing, and make every purchase count.

WearWise is a personal wardrobe and styling web app. You catalogue everything you wear, including shoes, accessories, and fragrance. It suggests outfits from what you own and explains why they work, plans your week around weather and laundry, and tells you what a new purchase would add before you buy it.

It is not a store. There is no checkout. When WearWise points to a product, you buy it on the retailer's site.

## Status

Planning complete. Building starts at milestone M0. See [`docs/PROGRESS.md`](docs/PROGRESS.md).

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

<!-- Written in M0. Must work from a fresh clone. -->
Not available yet.

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
