# Deployment

Deploy in M0 and keep deploying. Every merge to `main` goes live, so a broken deploy is found the day it happens, not in the last week.

## Setup

| Part | Service | Free-tier facts (checked October 2026) | What it means for WearWise |
|---|---|---|---|
| Frontend | Vercel, Hobby plan | Free; personal, non-commercial use only | Fine for a portfolio project. Adding affiliate links or ads would make it commercial. |
| Backend | Render, free web service | Sleeps after 15 minutes without traffic; waking takes about a minute; 750 instance hours a month; no permanent disk | First request after a quiet spell is slow. Show a "waking up" state. Never store uploads on its disk. |
| Database | Neon, Free plan | 1 GB storage per project; 100 compute-hours a month; pauses after 5 minutes idle | Plenty for this app. First query after a pause is slightly slow. |
| Images | Cloudflare R2 | 10 GB storage and 1 million writes a month free; no egress fees | About 1 MB per item with thumbnail, so thousands of items fit. |
| Weather | Open-Meteo | No key; non-commercial; 10,000 calls a day; attribution required | Cache per city per day. Credit Open-Meteo in the footer. |

Do not use Render's free Postgres: it expires 30 days after creation.

Limits and prices change. Check each provider's page before relying on a number here.

## Environments

| | Local | Production |
|---|---|---|
| Frontend | `localhost:3000` | Vercel |
| Backend | `localhost:8000` | Render |
| Database | Postgres in Docker | Neon |
| Images | `./.storage` folder | R2 bucket |
| AI | Fake provider by default | Real provider |
| Email | Printed to the console | Real provider |

Vercel also builds a preview for every pull request. Point previews at the production backend only for read-only checks, or give them their own Neon branch.

## Environment variables

See `.env.example` for the full list. Principles:

- Secrets live in each host's settings, never in the repo.
- Only variables starting with `NEXT_PUBLIC_` reach the browser. No secret may have that prefix.
- The backend refuses to start if a required variable is missing, and says which one.

## Request path in production

```
browser -> https://<app>.vercel.app/api/v1/...
        -> Next.js rewrite
        -> https://<api>.onrender.com/api/v1/...
```

The browser never calls the Render URL directly, so the session cookie is first-party and no CORS setup is needed. `BACKEND_URL` is a server-side variable on Vercel.

## Migrations

- Every schema change is an Alembic migration, committed with the code that needs it.
- The backend's start command runs `alembic upgrade head` and then starts the server, so every deploy migrates first.
- Migrations must work on a database that already has data. Add a column as nullable or with a default, backfill, then tighten.
- Never edit a migration that has run in production. Write a new one.

## Release checklist

For each milestone, before merging to `main`:

1. Lint, type check, and tests pass locally and in CI.
2. Migrations run on a copy of production data, or on a Neon branch.
3. New environment variables are set on Vercel and Render and added to `.env.example`.
4. After deploy, open the production site and walk through the milestone's "Done when" list.
5. Tag the release (`v0.3.0` for M3, and so on; `v1.0.0` after M5).

## Cold starts

A sleeping backend plus a paused database makes the first request after a break take up to a minute.

- The frontend shows "Waking the server, this takes up to a minute" when the health check is slow, instead of an error.
- Don't rely on a third-party pinger to keep it awake around the clock; 750 hours covers one always-on service for a month with nothing to spare.
- If the delay hurts a demo, open the site a minute beforehand, or move the backend to a small paid instance for that month.

## Backups

Neon keeps a short history for restores on the free plan; check the current window. Before any risky migration, take a manual dump with `pg_dump`. Photos in R2 are not backed up; for a personal project that is acceptable, and the README should say so.

## Observability (M11)

- Structured logs on the backend with a request ID that the frontend also logs.
- An error tracker on both sides.
- An uptime check on `/api/v1/health`.
- A simple page of counts for yourself: users, items, suggestions shown, acceptance rate, AI spend today.

## If the project becomes commercial

Affiliate links, ads, or paid plans change the terms on Vercel and Open-Meteo, and require a disclosure on the site. At that point, move to paid plans and reread each provider's terms.
