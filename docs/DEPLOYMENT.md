# Deployment

Deploy in M0 and keep deploying. Every merge to `main` goes live, so a broken deploy is found the day it happens, not in the last week.

## Setup

| Part | Service | Free-tier facts (checked October 2026) | What it means for WearWise |
|---|---|---|---|
| Frontend | Vercel, Hobby plan | Free; personal, non-commercial use only | Fine for a portfolio project. Adding affiliate links or ads would make it commercial. |
| Backend | Render, free web service | Sleeps after 15 minutes without traffic; waking takes about a minute; 750 instance hours a month; no permanent disk | First request after a quiet spell is slow. Show a "waking up" state. Never store uploads on its disk. |
| Database | Neon, Free plan | 1 GB storage per project; 100 compute-hours a month; pauses after 5 minutes idle | Plenty for this app. First query after a pause is slightly slow. |
| Images | Backblaze B2 | 10 GB storage free, no card needed; downloads free up to three times the average stored each month, then $0.01 per GB; without a card on file, Backblaze refuses requests past a free limit rather than charging | About 0.25 MB per item with its thumbnail. The API serves each photo with a one-year browser cache, so each device downloads it about once. |
| Weather | Open-Meteo | No key; non-commercial; 10,000 calls a day; attribution required | Cache per city per day. Credit Open-Meteo in the footer. |

Do not use Render's free Postgres: it expires 30 days after creation.

Limits and prices change. Check each provider's page before relying on a number here.

## First deploy, step by step

Do this once, after the M0 code is merged into `main`. Render and Vercel build from GitHub, so the code has to be there first. Use the same region for the database and the backend, so every query stays in one data centre.

**1. Neon (database)**

1. Create a project: name `wearwise`, Postgres 18, region AWS Asia Pacific (Singapore).
2. Open **Connect**. With **Connection pooling** on, copy the connection string; its host contains `-pooler`. This is `DATABASE_URL`.
3. Turn **Connection pooling** off and copy the string again. This is `MIGRATION_DATABASE_URL`.

Paste both exactly as Neon gives them (`postgresql://...`); the backend adds the driver name itself. Each contains the database password, so keep them out of the repo and out of chat messages.

**2. Render (backend)**

1. Sign in with GitHub and give Render access to the `wearwise` repository.
2. **New > Blueprint**, then pick the repository. Render reads `render.yaml` and proposes a free web service called `wearwise-api` in Singapore.
3. When asked, paste `DATABASE_URL` and `MIGRATION_DATABASE_URL` from step 1, then apply.
4. Wait for the first deploy. The log should show `Running upgrade -> ..., create app_meta` and then `Application startup complete`.
5. Copy the service URL Render shows, such as `https://wearwise-api.onrender.com`. Opening `<that URL>/api/v1/health` should show `"database":"ok"`. This is the one time to call the backend directly; the app itself always goes through Vercel.

**3. Vercel (frontend)**

1. Sign in with GitHub. **Add New > Project**, then import `wearwise`.
2. Set **Root Directory** to `frontend`. Vercel detects Next.js and pnpm.
3. Under **Environment Variables**, add `BACKEND_URL` with the Render URL from step 2 (no trailing slash), for Production and Preview.
4. Deploy. If `BACKEND_URL` is missing, the build stops with a message naming it.
5. Open the Vercel URL. Within a minute, while the backend wakes up, it should say **API ok, database ok**.

**4. Backblaze B2 (photos, before merging M3)**

The API refuses to start in production without it, so set it up before the M3 pull request is merged.

1. Sign up for **B2 Cloud Storage** at backblaze.com. No card is needed for the free allowance. When asked for a region, choose **EU Central**: Backblaze has no region in Asia, and Amsterdam is the closest to Singapore and India. The region can't be changed later.
2. **B2 Cloud Storage > Buckets > Create a Bucket**: a name such as `wearwise-photos-` followed by a few random letters, because bucket names are shared by every Backblaze account and `wearwise-photos` alone may be taken. Files in the bucket: **Private**. Default encryption: **Enable**. Object lock: **Disable** (it would stop the API deleting photos).
3. On the new bucket, open **Lifecycle Settings** and choose **Keep only the last version of the file**. Backblaze keeps every version of a file by default, so a deleted photo would only be hidden and still stored; with this setting it is removed a day later.
4. Note the bucket's **Endpoint**, such as `s3.eu-central-003.backblazeb2.com`. The region is the part between `s3.` and `.backblazeb2.com`, here `eu-central-003`.
5. **Application Keys > Add a New Application Key**: name `wearwise-api`, access to the new bucket only, type **Read and Write**. Copy the **keyID** and the **applicationKey**; the second is shown once. The master application key doesn't work with the S3 protocol.
6. In Render, under **Environment**, set `S3_ENDPOINT_URL` (the endpoint; `https://` is optional), `S3_REGION`, `S3_BUCKET` (the bucket's name), `S3_ACCESS_KEY_ID` (the keyID), and `S3_SECRET_ACCESS_KEY` (the applicationKey). `STORAGE_BACKEND` comes from `render.yaml`.
7. After the deploy, add an item with a photo on the live site, and check the bucket shows two files under `users/`.

Any S3-compatible service works with the same five settings. Cloudflare R2, for example, takes the region `auto`, but asks for a card on file.

**From then on**

- Every merge to `main` deploys both: Vercel straight away, Render once CI has passed on that commit.
- `render.yaml` is the source of truth for the backend's settings. Change it in a pull request, not in the dashboard. Secrets (`sync: false`) are the exception and live only in the dashboard.
- A new environment variable goes in `.env.example` and on the host (in `render.yaml` if it isn't secret).
- If the database password changes (Neon: **Connect > Reset password**), paste both new connection strings into Render under **Environment**. Render redeploys with them.

## Environments

| | Local | Production |
|---|---|---|
| Frontend | `localhost:3000` | Vercel |
| Backend | `localhost:8000` | Render |
| Database | Postgres in Docker | Neon |
| Images | `./.storage` folder | Backblaze B2 bucket |
| AI | Off by default; `AI_PROVIDER=fake` for a test round trip | Off until `AI_PROVIDER=anthropic` and its key, models, and prices are set (D47); the fake is refused |
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
- The backend's start command runs `alembic upgrade head`, loads the reference data from `seed/` (`python -m scripts.seed_reference`), and then starts the server, so every deploy migrates and reseeds first. `render.yaml` lists `backend/**` and `seed/**` as build filters, so a change to either deploys.
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

Neon keeps a short history for restores on the free plan; check the current window. Before any risky migration, take a manual dump with `pg_dump`. Photos in Backblaze B2 are not backed up; for a personal project that is acceptable, and the README should say so.

## Observability (M11)

- Structured logs on the backend with a request ID that the frontend also logs.
- An error tracker on both sides.
- An uptime check on `/api/v1/health`.
- A simple page of counts for yourself: users, items, suggestions shown, acceptance rate, AI spend today.

## If the project becomes commercial

Affiliate links, ads, or paid plans change the terms on Vercel and Open-Meteo, and require a disclosure on the site. At that point, move to paid plans and reread each provider's terms.
