# Agents (M12)

Three agents work on top of the app:

- **The Stylist** answers one person's questions from their own wardrobe. It was built in M10 (`docs/AI.md`) and moves onto the agent framework here.
- **The Trend Scout** reads fashion news on a schedule and keeps a short list of current trends in India, each with its sources. It's shared by everyone and sees no personal data.
- **The weekly digest** tells each person who asked for it what is worth buying this week, and where to look, or what to wear from what they already own.

This is the design. It's built in M12. All numbers below are starting values, kept in one config file, like the engine's.

## 1. The rule

Agents decide what to look at, which tools to call, and how to word things. Code decides everything that has a right answer.

| Decided by code (tested) | Left to the model |
|---|---|
| What matches, and how well (the engine) | Which tools to call, in what order |
| What a purchase would add (the purchase analyzer) | The search queries, from a brief code writes |
| Which trends a person sees, and which picks they get | Pulling trends out of article text, into fixed fields |
| Whether a trend has enough recent, independent sources | The wording of a reply, a subject line, or a sentence about a pick |
| Every link, price, and number shown or sent | |

Nothing an agent says is new information. Every item, outfit, trend, source, link, and number traces back to a tool result or a database row, and code checks that before anything is shown or sent. When a check fails, the agent's words are dropped and template wording built from the same data is used instead.

## 2. Framework and layout

- **LangGraph** for all three agents. Each is an explicit state graph: nodes are plain functions, and edges, including the conditional ones, are written in code. It provides three things the app would otherwise build by hand:
  - checkpoints in Postgres, so a run can stop and resume;
  - interrupts, which pause a run until a person says yes;
  - retries per node.
- **LangChain only for the model integration**: one chat-model interface whatever the provider, tool binding, and structured output. The Stylist uses `create_agent` with middleware for its tool-call limit and its pauses for confirmation. Not used: chains, vector stores, document loaders, retrievers, or memory classes.
- **The model** is chosen by the same settings as M10 (`AI_PROVIDER`, `AI_MODEL_CHAT`, the key, and the prices that turn tokens into spend). Tests use a scripted fake chat model that accepts tools. The daily spend cap and the `ai_usage` log from M10 cover every model call made by every agent.
- **Tracing** (`AGENT_TRACING`) is off by default. A tracing service receives the prompts, and the Stylist's and the digest's prompts carry wardrobe data, so tracing is allowed only for Trend Scout runs and local runs. Every run is logged in `agent_runs` either way.

```
backend/app/
  agents/      the graphs (stylist, trend_scout, digest), their tools, the checkpointer
  jobs/        scheduled entry points: python -m app.jobs.trend_scout, python -m app.jobs.weekly_digest
  engine/      unchanged rule; gains digest picks (plain data in, plain data out)
  adapters/    gains web search and email, each with a timeout, a fallback, and a fake
```

Import rules, enforced by tests:
- `engine/` still imports nothing from the rest of the app.
- `agents/` imports services and adapters, never `api/`.
- `services/` imports neither `agents/` nor `jobs/`.
- Tools are thin wrappers over services, so an agent can't do anything the app's own pages can't.

## 3. The Stylist on LangGraph

The tools, cards, grounding check, limits, and evaluation are the ones in `docs/AI.md`, section 3. What changes is the loop around them.

```
load the thread's last messages
   -> model
        -- read tool  --> run it as the logged-in person --> model
        -- propose_*  --> check it, store the proposal --> pause for confirmation
                              Confirm: run the app's own code, tell the model --> model
                              Not now: tell the model                         --> model
        -- reply      --> grounding check
                              passes             --> save the reply
                              fails the 1st time --> model, with what failed
                              fails again        --> apology and the tools' own cards
```

- **Memory stays in `chat_messages`.** The page, the export, and account deletion already read that table. The checkpointer holds only a turn that hasn't finished, such as one paused at a confirmation, and those checkpoints are deleted when the turn ends. Keeping whole conversations in checkpoints would store a second copy of every message, written again at every step.
- **Pauses.** A write tool first checks the proposal (owned pieces, a whole outfit) and stores it as a pending `chat_actions` row. Then the run pauses. Storing and pausing are separate steps, because LangGraph runs a paused step again from its start when it resumes, and the proposal must not be stored twice. Confirm resumes the run with yes, and Not now with no. A new message sent while a turn is paused first resumes it with "not now". The thread id is `chat:<thread id>`.
- **Grounding** is a step after the model's reply, with the same rules as M10. Its one retry is an edge back to the model.
- **New read tools:**

| Tool | Returns |
|---|---|
| `get_trends(section, category, season)` | Approved trends that fit the person's sections, each with its summary and sources |
| `get_latest_digest()` | The person's latest digest: its picks, their reasons, and the links it gave |

## 4. The Trend Scout

Twice a week by default, on Tuesday and Friday early in the morning in India, so new trends can be approved before the Sunday digests. Fashion moves slower than news: running more often would mostly find the same articles again. Nothing about any person goes into a search or comes out of a run.

```
plan_queries -> search -> read -> extract -> validate -> dedupe_merge -> save -> report
```

| Step | Model? | What it does |
|---|---|---|
| `plan_queries` | Yes, with template queries as the fallback | Up to 8 queries from a brief written by code: the season in India for the next four weeks (from the date, as the engine works it out), the sections, the style profiles people have chosen (names and counts only), and any festive or wedding window in `seed/calendar.json`. Together they cover clothing, footwear, accessories, and fragrance. Code checks the queries: at most 8, each under 120 characters, using only words from the brief and plain English. |
| `search` | No | The web search adapter (section 7), limited to the past month, boosting India. Editorial and news sites from `seed/trend_sites.json` are preferred; shop listing pages, marketplaces, and social networks are blocked. Finding products stays with the M9 product adapters. |
| `read` | No | The page text the search returns. If a page has to be fetched, the M9 page reader does it: robots.txt first, one fetch, a timeout and a size limit, text only, never images. |
| `extract` | Yes, structured output, no tools | A list of `TrendCandidate` (below). The page text is data, never instructions. |
| `validate` | No | Drops a candidate that has fewer than 2 sources from different sites, or any source older than 45 days or with no date. A quote not found word for word in the text that was read is removed. Values outside the app's own lists (categories, colour families, fabrics, patterns, fits, seasons, sections, style profiles) are dropped, and a candidate with none left goes. So does anything about body types, weight, or skin tone. Each drop is recorded with its reason. |
| `dedupe_merge` | No | A candidate with the same normalised name as an active trend, or with mostly the same attributes, is merged into it: its sources are added and `last_seen_at` moves on. A trend not seen for 8 weeks expires. |
| `save` | No | New trends are saved as `pending`, or `approved` when `TRENDS_REQUIRE_APPROVAL=false`. The run's row in `agent_runs` is completed. |
| `report` | No (template) | An email to the owner: the queries, the sources read, the trends added, merged, and dropped (each with its reason), search credits, tokens, estimated cost, how long it took, any errors, and how many trends are waiting for approval, with a link. |

**`TrendCandidate`:** name; a summary of at most 40 words; why now; category ids, colour families, fabrics, patterns, fits, seasons, sections, and style profile ids, all from the seed lists; and its sources, each with its address, title, published date, and a short quote that supports it.

**Approval is a status, not a pause.** The admin page lists pending trends with their sources, dates, and quotes, and each one is approved or rejected on its own. Digests use approved trends only. A run held open for days waiting for a person would block the next scheduled run, and approving three trends out of five doesn't fit a single resume.

**Limits per run**, from settings: queries (8), pages read (40), model tokens, seconds (600), and search credits for the month (`SEARCH_MONTHLY_CREDIT_CAP`, counted from what each search response reports). When a limit is reached, the run stops after the step it's in, keeps what is valid, and the report says which limit stopped it.

**Resuming.** The run's thread id is `scout:<run id>`. A run that dies part-way resumes from its last checkpoint, without paying for the same searches again. Its checkpoints are deleted when it finishes.

## 5. The weekly digest

Off until a person turns it on and confirms their address from the email that follows (section 7). They choose the day (Sunday by default) and can turn it off at any time. It arrives at about 08:00 in India.

Each person gets one run with the thread id `digest:<user id>:<ISO week>`:

```
gather -> pick -> find_where_to_buy -> write -> check -> send -> log
                                          ^         |
                                          +- once --+   (then template wording)
```

| Step | Model? | What it does |
|---|---|---|
| `gather` | No | Sections, styles, preferred and avoided colours, usual spend per category, usual sizes, and city. The season and the 7-day outlook (M6), a wardrobe summary, recent wears, the shopping list, gaps (M8), approved trends that fit the sections, and earlier "not for me" answers. |
| `pick` | No: engine code | Below. |
| `find_where_to_buy` | No | For each pick to buy: the M9 shop searches (the shops in config) with its keywords, with the person's usual spend for that kind of piece shown beside them. Shops don't document price filters (D46), so the links carry none. Live products only from an approved product API. No invented price, stock, or address. |
| `write` | Yes, structured output, no tools | A subject line (at most 70 characters), a two-line intro, and one sentence per pick (at most 30 words). The input is the picks, their reason codes, the names of the matching items the person owns, the trend summaries, and source titles. It never includes the email address, measurements, or photos. |
| `check` | No | Below. If it fails twice, or the model is off or down, the email uses template wording built from the reason codes, so the digest still goes out. |
| `send` | No | HTML and plain text. Item names and colour swatches, never private photos or article images. Links: the This week page, the shop searches, "not for me" for each pick, preferences, and unsubscribe (a signed link and the `List-Unsubscribe` and `List-Unsubscribe-Post` headers). The digest's id is the provider's idempotency key. |
| `log` | No | The digest, its picks, the provider's message id, and its status. |

### Picks (engine)

Plain data in, plain data out, with unit tests:

1. **Candidates from trends.** For each approved trend in season for the person's sections, and each category it names that fits those sections: a candidate piece with the category's defaults, the trend's colour (trying up to three of its colour families, skipping avoided ones, and keeping the best), its first pattern and fabric, and its seasons.
2. **Already in your wardrobe.** If something the person owns is very close to the candidate (the analyzer's likeness of 0.8 or more), it isn't a purchase. The pick becomes that item with an outfit built around it by "what goes with this", and the engine's reasons.
3. **Otherwise, the purchase analyzer**, exactly as for a purchase check. A Skip verdict is dropped.
4. **Score:**

```
pick = 0.60 * value + 0.25 * trend_fit + 0.15 * season_fit

value      = coverage gain / the best staple's gain for this wardrobe, capped at 1,
             times (1 - likeness to the closest piece owned)
trend_fit  = overlap of the trend's styles and colours with the person's styles and preferred colours
season_fit = 1 for this week's season, 0.5 for next month's, otherwise 0
```

   An "already in your wardrobe" pick takes the outfit's score as its value. A trend the person marked "not for me" is never picked again. The same category and colour scores half for 8 weeks.

5. **Choose** up to 3 picks, each from a different category, highest score first.
6. **Nothing worth it?** Then no email. The This week page says "nothing worth buying this week", which is a real answer.

### Checks before sending

- Every item id belongs to the person, and every trend id is an approved trend.
- Every address came from an adapter or the app itself.
- Every number in the text appears in the input.
- Every length limit holds.
- No comment on bodies, and no pressure to buy (a word list, plus the same rule in the prompt).
- The address is confirmed, opted in, not a demo, and allowed by the allowlist.

### Once a week, at most

- One digest per person per ISO week, enforced by a unique key.
- Running the job twice skips anyone whose digest has gone. A run that died between `write` and `send` resumes from its checkpoint without another model call.
- The provider's idempotency key covers a send that was retried.

### In the app

- **This week**: the latest digest for the logged-in person, with their own photos, the picks, and why each was chosen.
- **Send me a preview**, in Settings: builds this week's digest and shows it, without emailing.
- **Not for me**, from the email or the page: stored with the pick, it lowers similar picks in later weeks.

## 6. Running on a schedule

The free server sleeps after 15 quiet minutes, so a scheduler inside it wouldn't fire reliably. The jobs run on GitHub Actions instead, as scheduled workflows that start the job directly. They can also be started by hand from the Actions tab.

| Job | Schedule (India time) | Workflow |
|---|---|---|
| Trend Scout | Tuesday and Friday, 05:41 | `trend-scout.yml` |
| Weekly digest | Daily, 08:07, for the people whose day it is | `weekly-digest.yml` |

- **Off the hour.** Scheduled runs can be delayed, or dropped, under load, most often at the top of the hour.
- **Catch-up.** The digest job also sends to anyone whose day was in the last two days and who has had no digest this week, so a dropped or delayed run is made up the next day.
- **One at a time.**
  - Each workflow has a `concurrency` group.
  - Each job takes a "running" row in `agent_runs`; only one per kind may exist (a unique index), and it lapses after 2 hours.
  - Advisory locks aren't used, because they don't hold reliably through the database's connection pooler.
- **Batches.** The digest job works through people in batches, up to `DIGEST_BATCH_CAP` a run and under the email provider's daily limit. One person's failure is logged and doesn't stop the others. Anyone skipped by a cap is picked up by the next run's catch-up.
- **Noticing a missed run.** The owner's run report doesn't arrive, and `/admin/runs` shows each kind's last run. Workflows in a public repository switch off after 60 days with no activity.

## 7. Adapters

**Web search** (`WebSearch`): a search provider over HTTPS (Tavily first), and a fake that returns recorded results.
- **Each search:** a past-month window, a preferred-sites list and a blocked-sites list, and a request for the credits it used.
- **No personal data in queries:** the provider's terms let it keep queries and train models on them.
- **Monthly credit cap:** enforced in code from the credits each response reports.
- **When it fails or a cap is reached:** the run stops cleanly and reports why.

**Email** (`EmailSender`): printed to the console in development, a transactional provider in production (Resend first), and a fake in tests.
- **Who it sends to:**
  - **Opted-in, confirmed addresses only.** It sends only to a confirmed address with a recorded opt-in, and never to a demo account. Turning the digest on sends a confirmation link; following it confirms the address and records when.
  - **An allowlist until a domain is verified.** Without a verified domain, the provider sends only to the account owner's own address. Until a domain is verified, `EMAIL_ALLOWLIST` limits all sending to the addresses listed, and digests are labelled as a preview.
- **Links:**
  - **Signed.** Unsubscribe and "not for me" links carry a signature (`EMAIL_LINK_SECRET`) and the one thing they're for, so they work from the email without logging in and can do nothing else.
  - **Single use.** Confirmation (and password reset, if built with it) uses single-use tokens stored as hashes, which expire.
- **One-click unsubscribe:** mail apps send it as a POST without the header the app normally requires against cross-site requests. That one endpoint is guarded by its signed token instead, and the route audit lists it as public.
- **Daily limits:** `EMAIL_DAILY_CAP` stays under the provider's daily limit. Anyone skipped is logged and sent to later.

## 8. Safety, privacy, and cost

- **Web text is untrusted.** Steps that see page text have no tools that change anything, their output must pass a schema, and quotes are checked against the text.
- **No article images** in emails or pages, because of copyright. Trends are shown with colour swatches and text. Product images come only from permitted product sources.
- **What each outside service gets:**
  - The model gets wardrobe attributes, item names, and preferences: never the email address, measurements, or photos.
  - The search provider gets generic queries.
  - The email provider gets the address and the email.
  - The privacy page names all three.
- **Spend:**
  - Model calls count against the M10 daily cap.
  - Each run and each digest logs its tokens and estimated cost.
  - Search credits have their own monthly cap.

| Cost | Estimate (replaced by measured numbers at the end of M12) |
|---|---|
| Search credits per Trend Scout run | About 8 (8 basic searches) |
| Search credits per month | About 70 at twice a week, against a free allowance of 1,000 |
| Emails per week | One per opted-in person, plus confirmations and the owner's two run reports |
| Model tokens | Measured in M12 |

## 9. Tests and evaluation

Recorded search results as fixtures and the scripted fake model in every graph test. No network calls in CI.

| Agent | Must hold |
|---|---|
| Trend Scout | Extraction output fits the schema. Single-source, stale, undated, and off-list candidates are dropped, with reasons. A quote not found in the text is removed. Duplicates merge. Each limit stops a run cleanly and keeps what was valid. A second run at the same time is refused. A run resumed after a failure doesn't search again. |
| Digest picks (engine) | On a fixture wardrobe and fixture trends: never a piece the person already has (that becomes "already in your wardrobe"); never an avoided colour; at most one pick per category; only the person's own item ids; "not for me" is respected. |
| Digest run | Links only from adapters. Numbers in the text only from the input. Template wording when the model is down. A second run in the same week sends nothing. After unsubscribing, the next run sends nothing. Nothing goes to an unconfirmed address, a demo, or an address off the allowlist. |
| Stylist | The M10 evaluation still passes on LangGraph. Questions about trends and the digest answer from the tools. Nothing is saved before Confirm, and a confirmed action runs once even if Confirm is pressed twice. |
| Privacy | Deleting an account removes its digests, picks, email events, tokens, and its checkpoints. Another person gets 404 for a digest or pick. |

Before the schedules are switched on, the owner reviews one real Trend Scout run by hand: its trends, sources, and quotes.

## 10. What the agents are not used for

- Choosing or scoring outfits, picks, or purchases.
- Counting anything, or producing prices, stock, or ratings.
- Trends without sources, or sources it didn't read.
- Comments on bodies, or inferring body shape, gender, or skin tone.
- Reading shop listing pages, or getting around logins, CAPTCHAs, or bot checks.
- Emailing anyone who hasn't confirmed.
