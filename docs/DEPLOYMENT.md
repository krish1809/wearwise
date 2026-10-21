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
| Web search (M12) | Tavily | 1,000 credits a month, no card; a basic search is 1 credit, an advanced one 2; past the plan, $0.008 a credit. Its terms let it keep queries and train on them | About 8 credits a Trend Scout run, about 70 a month at twice a week. Queries carry no personal data. A monthly cap in code. |
| Email (M12) | Resend | 3,000 emails a month and 100 a day (a UTC day); up to 3 domains. Without a verified domain it sends only to the account owner's own address. Bounces above 4% or spam reports above 0.08% can pause sending | The owner's run reports work at once. Anyone else needs a domain of your own. Stay under 100 a day. |
| Scheduled jobs (M12) | GitHub Actions | Free for public repositories on GitHub's standard runners. Schedules run only from the default branch, can be delayed or dropped at busy times (most often on the hour), and switch off after 60 days without activity in a public repository | Off-hour schedules, a catch-up for the digest, and a run report to notice a missed run. |

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
| Email | Printed to the console | Resend from M12; only to `EMAIL_ALLOWLIST` until a domain is verified (D57) |
| Web search | Off, or `SEARCH_PROVIDER=fake` for recorded results | Tavily from M12 |
| Scheduled jobs | Started by hand: `python -m app.jobs.trend_scout`, `python -m app.jobs.weekly_digest` | GitHub Actions from M12 |

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
- The backend's start command runs `alembic upgrade head`, loads the reference data from `seed/` (`python -m scripts.seed_reference`), runs housekeeping (`python -m scripts.housekeeping`: expired demo copies, unsaved photos, old error reports and rate-limit counts, ended sessions; it never stops the start), and then starts the server, so every deploy migrates and reseeds first. The free server sleeps when idle, so it starts, and tidies, often. `render.yaml` lists `backend/**` and `seed/**` as build filters, so a change to either deploys.
- From M12, the start command also runs `python -m scripts.agent_setup` after the migrations: it creates or updates the agents' checkpoint tables, which the checkpointer library owns and versions itself, so they aren't an Alembic migration (D59). The scheduled jobs run the same step before they start.
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

- **Logs.** In production the API writes one JSON object per line: time, level, message, and the request's id, plus fields such as the route, status, and milliseconds for the line every request ends with. Routes are logged as patterns (`/api/v1/items/{item_id}`), never with the query string or the visitor's IP address (uvicorn's own access log is off). Search Render's logs for a request id to see everything that request did.
- **Request ids.** The browser sends a fresh `X-Request-ID` with each API call; the API keeps it if it looks like one, or makes its own, and returns it on every answer. A 500 tells the person "mention reference ...", so a report can be matched to its log lines.
- **Errors.** Anything the API didn't expect is logged with its stack trace, stored in `error_events` (route, error type, message, the end of the stack trace; no account), and answered with a plain 500. The browser reports its own errors (from the error pages and any unhandled error) to `POST /api/v1/client-errors`, at most five per page load and thirty an hour per address. Events go after 30 days.
- **The owner's page.** `/admin` shows people, demo accounts, items, photos, outfits, wear logs, suggestion acceptance by engine version, the stylist's use and spend today, and the latest errors. Set `ADMIN_EMAILS` on Render to your account's email; everyone else gets "not found". It isn't linked anywhere.
- **Uptime.** No pinger: frequent checks would keep the free server and database awake and use up their hours. The end-to-end run against production (M11) doubles as a daily check, and GitHub emails you when it fails.

## Scheduled jobs (M12)

The Trend Scout and the weekly digest run on GitHub Actions, not on Render: the free server sleeps, so a scheduler inside it wouldn't fire (D56). Each job runs on GitHub's machine against the production database, then exits.

| Workflow | Schedule (`timezone: "Asia/Kolkata"`) | What it runs |
|---|---|---|
| `trend-scout.yml` | Tuesday and Friday at 05:41 | `python -m app.jobs.trend_scout` |
| `weekly-digest.yml` | Daily at 08:07, for the people whose day it is, plus anyone missed in the last two days | `python -m app.jobs.weekly_digest` |

- **By hand.** Both can also be run from the Actions tab (`workflow_dispatch`), and the Trend Scout locally with `make trend-scout`. The schedules are added only after one real Trend Scout run, started by hand, has been reviewed: until then, `trend-scout.yml` has no schedule.
- **Settings.**
  - **Where they live:** a GitHub environment called `production` (Settings > Environments > New environment).
  - **Secrets:**
    - `DATABASE_URL` (Neon's pooled string)
    - `AI_API_KEY`, `SEARCH_API_KEY`, `EMAIL_API_KEY`, `EMAIL_LINK_SECRET`
    - `ADMIN_EMAILS` and `EMAIL_ALLOWLIST`: email addresses are kept as secrets, so they're masked in the logs, which are public in a public repository.
  - **Variables:**
    - `AI_PROVIDER`, `AI_MODEL_CHAT`, `AI_MODEL_VISION`, `AI_PRICE_INPUT_PER_MTOK`, `AI_PRICE_OUTPUT_PER_MTOK`, `AI_DAILY_SPEND_CAP_USD` (the same values as on Render)
    - `EMAIL_PROVIDER` (`resend` once it's set up; until then the jobs send nothing and the run log says so), `EMAIL_FROM`, `APP_URL`
    - optionally `SEARCH_MONTHLY_CREDIT_CAP`, `TRENDS_REQUIRE_APPROVAL`, `EMAIL_DAILY_CAP`, and `DIGEST_BATCH_CAP`
  - **Set by the workflows themselves:** `APP_ENV=production`, `STORAGE_BACKEND=none` (the jobs never touch photos, so they need no Backblaze settings, and the API refuses `none`), and the search provider.
  - **Same values as Render:** `EMAIL_LINK_SECRET` must match Render's, because Render checks the links the jobs sign.
  - **Who can reach them:** the workflows run only on their schedule and by hand, never on a pull request, so a pull request from someone else's copy of the repository can't reach the secrets.
- **One at a time.** Each workflow has a `concurrency` group, and each job also holds a "running" row in `agent_runs`, which lapses after 2 hours.
- **Known limits.**
  - **Delays and dropped runs:** scheduled runs start from the default branch's latest commit, and can be late or dropped at busy times, most often on the hour, hence the odd minutes and the digest's catch-up.
  - **Switched off after 60 days:** in a public repository, schedules switch off after 60 days without activity. Turn them back on from the Actions tab.
  - **Who hears about failures:** GitHub emails a failure to whoever last changed the schedule line.
- **Noticing a missed run.** The owner's run report doesn't arrive, and `/admin/runs` shows when each job last ran and how it ended.

## Email (M12)

- **Provider.** Resend, behind the `EmailSender` adapter (`EMAIL_PROVIDER=resend`, `EMAIL_API_KEY`, `EMAIL_FROM`), set on Render (for confirming an address and a new password) and in GitHub's environment (for the weekly email and the run reports). In development, emails are printed to the console. In production without a provider, nothing is sent and nothing about the email is logged; Settings says email isn't set up yet.
- **Before a domain.**
  - **Who can receive email:** Resend's shared sender reaches only your own Resend account address. Set `EMAIL_ALLOWLIST` to that address. Everything else is held and logged, and the app labels digests as a preview.
  - **Run reports:** the owner's run reports work from the start.
- **To email anyone else.**
  1. Buy a domain.
  2. Add the DNS records Resend lists for it, and wait for Resend to verify it.
  3. Set `EMAIL_FROM` to an address on that domain.
  4. Then empty `EMAIL_ALLOWLIST`.

  A `vercel.app` address can't be used, because its DNS isn't yours.
- **Limits.** `EMAIL_DAILY_CAP` (90 by default) keeps under the free plan's 100 a day. Anyone held by it is sent to the next day. Keep bounces and spam reports low: Resend pauses sending past 4% and 0.08%.
- **Consent.**
  - **Who receives it:** only people who turned the digest on and confirmed their address. Demo accounts never do.
  - **Unsubscribing:** every digest has an unsubscribe link and the one-click `List-Unsubscribe` headers.

## If the project becomes commercial

Affiliate links, ads, or paid plans change the terms on Vercel and Open-Meteo, and require a disclosure on the site. At that point, move to paid plans and reread each provider's terms.
