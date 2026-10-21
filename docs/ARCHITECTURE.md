# Architecture

## Shape

One repository, two apps, one database.

```
Browser
   |
   v
Next.js on Vercel  ---- /api/* proxied ---->  FastAPI on Render
(pages, components)                          |        |         |
                                             v        v         v
                                        Postgres   Object     External services
                                        (Neon)     storage    (weather, AI, product sources,
                                                   (B2)        web search, email)

GitHub Actions (scheduled) --> backend jobs (Trend Scout, weekly digest) --> the same Postgres
```

Inside the backend, the code is one deployable service split into modules. No microservices.

```
backend/app/
  api/          HTTP routes, request and response schemas, auth dependency
  models/       SQLAlchemy tables
  services/     use cases: load data, call the engine, save results
  engine/       pure logic: scoring, generation, planning, purchase analysis
  adapters/     storage, weather, AI provider, product sources, web search, email (each behind an interface)
  agents/       the agents' graphs and their tools (M12)
  jobs/         scheduled entry points, run by GitHub Actions (M12)
  core/         settings, database session, security, errors
```

## The one structural rule

**`engine/` imports nothing from `api/`, `models/`, `services/`, or `adapters/`.** It takes plain data objects and returns plain data objects. A service loads rows, converts them, calls the engine, and stores the result.

Why this matters:
- The engine can be unit-tested in milliseconds with no database.
- The chat feature calls the same functions as the buttons do, so the AI can't produce a different answer from the UI.
- The scoring logic can be swapped or versioned without touching routes.

**Agents and jobs (M12)** follow the same idea one level up. `agents/` imports services and adapters, never `api/`; its tools are thin wrappers over services, so an agent can do nothing the app's own pages can't. `services/` imports neither `agents/` nor `jobs/`, and the engine imports neither. Tests enforce all three. Design: `docs/AGENTS.md`.

## Stack

| Layer | Choice | Reason |
|---|---|---|
| Frontend | Next.js (App Router), React, TypeScript | Most common React setup; good routing and image handling |
| Styling | Tailwind CSS with tokens from `DESIGN_SYSTEM.md` | Fast to build, consistent |
| Components | Radix-based primitives (shadcn/ui), restyled | Accessible behaviour for dialogs and menus without the stock look |
| Server state | TanStack Query | Caching, loading and error states, optimistic updates |
| Forms | React Hook Form with Zod | Typed validation |
| Backend | FastAPI, Pydantic | Python suits the engine; automatic OpenAPI |
| ORM, migrations | SQLAlchemy 2, Alembic | Standard and explicit |
| Database | PostgreSQL | Relational data with arrays and JSON where useful |
| Python tooling | uv, ruff, pytest, hypothesis | Fast, standard |
| JS tooling | pnpm, ESLint, Prettier, Vitest, Playwright | Standard |
| API types | TypeScript types generated from the OpenAPI schema | Frontend and backend can't drift apart |
| Agents (M12) | LangGraph, with LangChain for the model integration only | Explicit state graphs, checkpoints in Postgres, pauses for a person's yes, and retries per step (D55) |
| Scheduled jobs (M12) | GitHub Actions scheduled workflows | The free server sleeps, so a scheduler inside it wouldn't fire (D56) |

Use the current stable version of each at the time of M0, and record the versions in `docs/DECISIONS.md`.

Not used, on purpose: vector database, message queue, Redis, GraphQL, and LangChain's chains, vector stores, document loaders, and memory classes. Add one only when a milestone shows a real need, and record why. (An agent framework was on this list until M12, when the agents needed checkpoints, pauses for approval, and retries; LangGraph is used for the agents and nothing else: D55.)

## Auth

- Email and password. Hash with Argon2id.
- On login the server creates a session row and sets an opaque random token in an `httpOnly`, `Secure`, `SameSite=Lax` cookie. Only a hash of the token is stored.
- Every API route depends on `current_user`, which loads the session and user. Routes never accept a user ID from the client.
- Logout deletes the session row.

**Cookie and domain gotcha.** The frontend (Vercel) and backend (Render) live on different domains. A cookie set by the backend's domain would be a third-party cookie, which browsers block. So the browser only ever talks to the frontend's domain, and Next.js rewrites `/api/*` to the backend. The cookie is then first-party. This also removes CORS from the picture. Set it up in M0, before auth exists.

**CSRF.** `SameSite=Lax` blocks cross-site POSTs in modern browsers. Also require a custom header (for example `X-Requested-With`) on every state-changing request and reject requests without it. (One exception from M12: one-click unsubscribe, which mail apps send without the header, is guarded by a signed token in the link instead: D57.)

**Checks that walk every route (M11).** A test reads the API's own schema and calls every route: each needs a login except a short public list, each change needs the custom header, and an id that isn't there is a 404, never a 500. A new route can't quietly skip any of them (D49).

**Limits and headers (M11).** Log-ins, sign-ups, uploads, and demos are rate-limited, and every person's changes are capped at 1,000 an hour. The web app sends a content security policy and the usual security headers; the API sends a locked-down policy and `no-store`. Uploads are decoded only as JPEG, PNG, or WebP (D49).

## Ownership

Every table that holds user data has a `user_id`. Every query in `services/` filters by the current user's ID. A request for another user's row returns 404, not 403, so IDs can't be probed.

Each milestone adds a test that creates two users and proves one cannot read, change, or delete the other's rows for that milestone's tables.

## Images

```
upload -> validate (type by content, size limit) -> strip metadata -> resize
       -> write original (max 1600 px) and thumbnail (400 px), WebP
       -> store via StorageAdapter -> save keys in item_images
```

- `StorageAdapter` has two implementations: local folder for development, S3-compatible for Backblaze B2 in production.
- Render's free instances have no permanent disk, so local storage would lose every photo on redeploy. Production must use object storage from M3.
- Photos are private. The API streams each image after an ownership check, with a one-year private browser cache, since a stored file never changes. Do not make the bucket public.
- Strip EXIF data on upload; phone photos carry location.

## Caching the engine's work

Pair scores depend only on the items. Store a `wardrobe_version` integer on the user and bump it whenever an item is added, edited, or removed. Cache the pair-score matrix per user and version, in process memory at first. If memory or cold starts become a problem, move it to a table. Measure before adding anything. (In M11, Insights' measures moved to a table, `saved_measures`, kept per person under the same fingerprint, because the free server loses its memory whenever it sleeps: D53.)

## External services

Each sits behind an interface in `adapters/` with a fake implementation for tests.

| Service | Default | Notes |
|---|---|---|
| Weather | Open-Meteo | No key. Free tier is for non-commercial use and requires attribution. Cache per city per day. |
| AI | One provider behind `AIProvider` | Chosen in M10. See `AI.md`. |
| Product sources | Adapters | See `SHOPPING.md`. |
| Web search | Tavily (M12) | The Trend Scout only. Generic queries with no personal data, a monthly credit cap in code (D58). |
| Email | Resend (M12) | Digests, address confirmation, the owner's run reports, and password reset if built with them. Printed to the console in development. Only to confirmed addresses, and only to an allowlist until a domain is verified (D57). |

Rules for all of them: a timeout on every call, one retry at most, a fallback when it fails, and no call inside a database transaction.

## Scheduled jobs (M12)

The Trend Scout and the weekly digest run as GitHub Actions scheduled workflows that start `python -m app.jobs.<name>` against the production database, and can be started by hand. Each workflow has a `concurrency` group, and each job also holds a "running" row in `agent_runs`, so two can't overlap. Jobs are safe to run twice: a digest goes at most once a week, and a run that dies resumes from its checkpoint. Schedules and secrets: `docs/DEPLOYMENT.md`.

## Operations (M11)

Every request carries an id (sent by the browser, or made by the API) that appears on every log line, every answer, and every recorded error. Logs are JSON in production, by route pattern, without query strings or IP addresses. Unexpected errors are stored in `error_events` for 30 days, and the owner's page at `/admin` shows counts and the latest errors, for `ADMIN_EMAILS` only (D51). Details: `docs/DEPLOYMENT.md`, Observability.

## API conventions

- Base path `/api/v1`.
- Resource routes: `GET /items`, `POST /items`, `GET /items/{id}`, `PATCH /items/{id}`, `DELETE /items/{id}`.
- Actions as sub-resources: `POST /outfits/suggest`, `POST /candidates/{id}/analyze`.
- Lists are paginated with `limit` and `cursor`.
- Errors use one shape: `{ "error": { "code": "item_not_found", "message": "...", "fields": {...} } }`.
- Times in UTC ISO 8601; dates as `YYYY-MM-DD`; money as integer paise plus a currency code.

## Testing

| Kind | Tool | What it covers |
|---|---|---|
| Engine unit tests | pytest | Scoring functions, generation, planner, analyzer |
| Property tests | hypothesis | Invariants: no unavailable items, one item per slot, budget never exceeded |
| Golden set | pytest | Hand-labelled pairs and outfits from a real wardrobe, as a regression check |
| API tests | pytest with a test database | Routes, validation, ownership |
| Component tests | Vitest, Testing Library | Forms and tricky components |
| End to end | Playwright | Register, add item, build outfit, get suggestion, analyse purchase |
| Agents (M12) | pytest with recorded search results and a scripted fake model | Each graph's steps, limits, and checks; no network calls in CI |

Test logic heavily and test glue lightly. Don't chase a coverage number.

## Repository layout

```
wearwise/
  frontend/
    app/                routes
    components/         ui/ (primitives) and feature folders
    lib/                api client, generated types, helpers
  backend/
    app/                see module list above
    alembic/            migrations
    tests/
    scripts/            seed reference data, load demo wardrobe
  seed/                 taxonomy, colours, occasions, style profiles, archetypes
  docs/
  docker-compose.yml
  .env.example
```
