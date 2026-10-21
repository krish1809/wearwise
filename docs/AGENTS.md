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
- **LangChain only for the model integration**: one chat-model interface whatever the provider, tool binding, and structured output. The Trend Scout and the weekly email use it. The Stylist keeps the M10 model adapter (section 3). Not used: chains, vector stores, document loaders, retrievers, or memory classes.
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

The tools, cards, grounding check, limits, and evaluation are the ones in `docs/AI.md`, section 3. What changes is the loop around them, which is now a graph (`app/agents/stylist.py`):

```
earlier proposals still waiting become "not now"; load the thread's last messages
   -> model
        -- tools (read, or propose_*) --> run them as the logged-in person --> model
        -- reply                       --> ground
                                             passes             --> save
                                             fails the 1st time --> model, with what failed
                                             fails again        --> apology and the tools' own cards --> save
   save -> proposed anything? --> confirm: paused until the person decides each proposal
                                  Confirm or Not now resumes it; it ends when none is left
```

- **The model is the M10 adapter.** The Stylist calls the model through `app/adapters/ai`, not LangChain's integration. That adapter is tested, needs no SDK, forces the final `reply` call, and counts each person's tokens toward their limits. Porting the loop and the model at the same time would have changed two things at once; keeping the adapter means the M10 tests check the port unchanged. The Trend Scout and the weekly email, which are new, use LangChain's integration (`app/agents/model.py`).
- **A graph built by hand, not `create_agent`.** The grounding check, its one retry, and the apology are this app's own rules. As middleware they'd be hidden inside a ready-made agent; as steps and edges, each one is visible and tested.
- **Memory stays in `chat_messages`.** The page, the export, and account deletion already read that table. Keeping whole conversations in checkpoints would store a second copy of every message, written again at every step.
- **Pauses.** A `propose_` tool checks the proposal (owned pieces, a whole outfit) and stores it as a pending `chat_actions` row, in the `tools` step. A turn that proposed anything pauses at `confirm` once its reply is saved. Storing and pausing are separate steps, because LangGraph runs a paused step again from its start when it resumes, and a proposal must not be stored twice.
- **Deciding.** Confirm and Not now run the app's own code, as in M10, then resume the run with the proposal that was decided. The run ends once nothing it proposed is still waiting. The model isn't called on a click: that would cost tokens, could fail after the change was already made, and would add a message nobody asked for. The next message's history tells the model how each proposal ended.
- **A new message** first answers every proposal still waiting with "not now" and ends the paused run, so a proposal can't be confirmed after the conversation has moved on. This happens once the message is allowed, even if the model then fails.
- **The rows decide.** Whether a proposal can still be confirmed is decided by its `chat_actions` row; the paused run follows the rows. So a checkpoint that was pruned or lost never strands a proposal, and the rule above holds without it.
- **Checkpoints.** The thread id is `chat:<thread id>`. The state is three small fields (tool calls so far, grounding rejections, the proposals still waiting), written once, when the turn pauses or ends (`durability="exit"`). A turn that doesn't pause, or that fails, deletes its checkpoint straight away. Deleting the conversation or the account deletes it too, and housekeeping prunes one left for more than a day. The API keeps the checkpointer on a small pool: up to 4 connections, opened on first use.
- **Grounding** is a step after the model's reply, with the same rules as M10. Its one retry is an edge back to the model.
- **New read tools:**

| Tool | Returns |
|---|---|
| `get_trends(category_id, season)` | Approved trends for the person's sections, each with its summary and the sites it was seen on; both filters optional |
| `get_latest_digest()` | The person's latest weekly picks: each piece, why, and the person's own pieces it names. The shop links stay on the Weekly picks page |

## 4. The Trend Scout

Twice a week by default, on Tuesday and Friday early in the morning in India, so new trends can be approved before the Sunday digests. Fashion moves slower than news: running more often would mostly find the same articles again. Nothing about any person goes into a search or comes out of a run.

```
plan_queries -> search -> read -> extract -> validate -> dedupe_merge -> save -> report
```

| Step | Model? | What it does |
|---|---|---|
| `plan_queries` | Yes, with template queries when its answer can't be used | Up to 8 queries from a brief written by code: the season in India for the next four weeks (from the date, as the engine works it out), the sections, the style profiles people have chosen (names and counts only), and any festive or wedding window in `seed/calendar.json`. Together they cover clothing, footwear, accessories, and fragrance. Code checks the queries: at most 8, each under 120 characters, with no web addresses, site operators, or numbers other than a year. With the model off or down, the run stops here, before spending any search credits, since nothing could read the pages. |
| `search` | No | The web search adapter (section 7): pages from the past month, boosting India, only on the sites in `seed/trend_sites.json` (Indian fashion magazines and the lifestyle pages of national news sites, a list the owner reviews). Shops, marketplaces, and social networks are blocked as a second guard. Finding products stays with the M9 product adapters. |
| `read` | No | The page text the search returns, up to three passages per page, cut to 3,000 characters. No page is fetched separately. Skipped, and counted: blocked or unlisted sites, pages without a date or older than 45 days, too little text, and the same page twice. At most 40 pages, best first. |
| `extract` | Yes, structured output, no tools | A list of `TrendCandidate` (below). Each page is wrapped in tags it can't close, and the model cites a page by its id, so it can't cite a page that wasn't read. The page text is data, never instructions. |
| `validate` | No | Drops a candidate that has fewer than 2 sources from different sites, or any source older than 45 days or with no date. A quote not found word for word in the text that was read is removed. Values outside the app's own lists (categories, colour families, fabrics, patterns, fits, seasons, sections, style profiles) are dropped, and a candidate with none left goes. So does anything about body types, weight, or skin tone. Each drop is recorded with its reason. |
| `dedupe_merge` | No | A candidate with the same normalised name as an active trend, or with mostly the same attributes, is merged into it: its sources are added and `last_seen_at` moves on. A trend not seen for 8 weeks expires. |
| `save` | No | New trends are saved as `pending`, or `approved` when `TRENDS_REQUIRE_APPROVAL=false`. The run's row in `agent_runs` is completed. |
| `report` | No (template) | An email to the owner: the queries, the sources read, the trends added, merged, and dropped (each with its reason), search credits, tokens, estimated cost, how long it took, any errors, and how many trends are waiting for approval, with a link. |

**`TrendCandidate`:** name; a summary of at most 40 words; why now; category ids, colour families, fabrics, patterns, fits, seasons, sections, and style profile ids, all from the seed lists; and its sources, each a page id and a short quote that supports it. The address, title, and published date come from the search, not the model.

**Approval is a status, not a pause.** The admin page lists pending trends with their sources, dates, and quotes, and each one is approved or rejected on its own. Digests use approved trends only. A run held open for days waiting for a person would block the next scheduled run, and approving three trends out of five doesn't fit a single resume.

**Limits per run**, from settings: queries (8), pages read (40), model tokens, seconds (600), and search credits for the month (`SEARCH_MONTHLY_CREDIT_CAP`, counted from what each search response reports). When a limit is reached, the run stops after the step it's in, keeps what is valid, and the report says which limit stopped it.

**Resuming.** The run's thread id is `scout:<run id>`. A run that dies part-way resumes from its last checkpoint, without paying for the same searches again. Its checkpoints are deleted when it finishes.

## 5. The weekly digest

Off until a person turns it on and confirms their address from the email that follows (section 7). They choose the day (Sunday by default) and can turn it off at any time. It arrives at about 08:00 in India.

Each person gets one run with the thread id `digest:<user id>:<ISO week>`, where the week is the week of their email day (so an email a day late still belongs to the week it was for):

```
prepare -> write -> check -> send
             ^        |
             +- once -+   (then the template wording)
```

| Step | Model? | What it does |
|---|---|---|
| `prepare` | No | Gather, pick, and where to buy, in one step (`app/services/digests.py`).<br>**Gather:** sections, styles, preferred and avoided colours, usual spend per category, the season, the wardrobe and how it's measured, approved trends that fit the sections, and earlier "not for me" answers.<br>**Pick:** engine code, below.<br>**Where to buy:** for each pick to buy, the M9 shop searches with its words, and the person's usual spend for that kind of piece beside them. Shops don't document price filters (D46), so the links carry none, and there are live products only from an approved product API.<br>The template wording, the digest, and its picks are saved. With nothing worth it, or the week's email already sent, the run ends here. |
| `write` | Yes, structured output, no tools | A subject line (at most 70 characters), a two-sentence intro, and one sentence per pick (at most 30 words). The input is the picks, their reasons and numbers, the trends' names and summaries, and the names of the person's own pieces. It never includes the email address, measurements, or photos. A second try is told what the first broke. |
| `check` | No | Below. Wording that passes replaces the template's on the digest and the page. If it fails twice, or the model is off, down, or over the daily cap, the template wording goes out, so the email still does. |
| `send` | No | HTML and plain text, built from the saved rows (`app/services/digest_email.py`). Item names and colour dots, never private photos or article images. Links: the Weekly picks page, the shop searches, "not for me" for each pick, settings, and unsubscribe (a signed link and the `List-Unsubscribe` and `List-Unsubscribe-Post` headers). The digest's id is the provider's idempotency key. The digest records how it went: sent (with the provider's message id), held (the allowlist or the daily cap), or failed. |

### Picks (engine)

Plain data in, plain data out, with unit tests:

1. **Candidates from trends.** Built by the service: for each approved trend in season for the person's sections, and each category it names that fits those sections, a candidate piece. It takes:
   - the category's level of dress and warmth;
   - the trend's colour (one the person prefers, else its first they don't avoid; a trend that names no colour takes the category's staple colour, and one whose colours are all avoided isn't for them);
   - its first pattern, fabric, and fit, and its seasons.
2. **Already in your wardrobe.** If something the person owns is very close to the candidate (the analyzer's likeness of 0.8 or more), it isn't a purchase. The pick becomes that piece, with a good outfit it's already part of. A piece in a colour the person avoids is neither a purchase nor a pick.
3. **Otherwise, the purchase analyzer**, exactly as for a purchase check. A Skip verdict is dropped. The analysis is the slow part, so only the 8 most promising candidates (by trend and season fit) get one.
4. **Score:**

```
pick = 0.60 * value + 0.25 * trend_fit + 0.15 * season_fit

value      = coverage gain / the gain a Buy needs (the top third of the staples'), capped at 1,
             times (1 - likeness to the closest piece owned); an accessory counts the
             outfits it finishes, out of ten
trend_fit  = overlap of the trend's styles and colours with the person's styles and preferred colours
season_fit = 1 for this week's season, 0.5 for next month's, otherwise 0
```

   An "already in your wardrobe" pick is worth the good outfits it's already in, out of ten. A trend the person marked "not for me" is never picked again. The same category and colour scores half for 8 weeks.

5. **Choose** up to 3 picks, each from a different category and a different trend, highest score first.
6. **Nothing worth it?** Then no email. The Weekly picks page says it's a good week to buy nothing, which is a real answer.

### Checks before sending

- **Who and what:**
  - Every item id belongs to the person, and every trend is an approved one. Both are ensured by `prepare`, which works only from those.
  - Every address in the email came from an adapter or the app itself. The email is built from the saved rows, and the model's words carry no links (checked).
- **The model's wording:**
  - Every number in it appears in the input.
  - Every length limit holds.
  - No web addresses or email addresses.
  - No comment on bodies, and no pressure to buy (word lists, plus the same rules in the prompt).
- **The address:** confirmed, opted in, not a demo, and allowed by the allowlist and the daily cap (the mail service).

### Once a week, at most

- One digest per person per ISO week, enforced by a unique key.
- Running the job twice skips anyone whose digest has gone. A run that died after `check` resumes at `send` without another model call.
- One person's failure is recorded (by error type only) and the run goes on to the next.
- The provider's idempotency key covers a send that was retried.

### In the app

- **Weekly picks** (`/picks`): the latest digest for the logged-in person. Each pick has its trend, the sentence, the analyzer's reasons, the person's own pieces to wear it with (with their photos), and the shop searches with their usual spend. Called "Weekly picks" rather than "This week", which would be easy to confuse with My Week.
- **Show this week's picks** (the preview): works out this week's digest now and shows it, without emailing. Limited to 10 an hour, since it runs the analysis. Once this week's email has gone, it shows what was sent.
- **Not for me**, from the email or the page: stored with the pick, it lowers similar picks in later weeks. Working the picks out again keeps those answers.

## 6. Running on a schedule

The free server sleeps after 15 quiet minutes, so a scheduler inside it wouldn't fire reliably. The jobs run on GitHub Actions instead, as scheduled workflows that start the job directly. They can also be started by hand from the Actions tab.

| Job | Schedule (India time) | Workflow |
|---|---|---|
| Trend Scout | Tuesday and Friday, 05:41 | `trend-scout.yml` |
| Weekly digest | Daily, 08:07, for the people whose day it is | `weekly-digest.yml` |

- **Started by hand first.** Both workflows start from the Actions tab only, until one real Trend Scout run has been reviewed and its trends approved. Then their schedules are added.
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
  - **An allowlist until a domain is verified.** Without a verified domain, the provider sends only to the account owner's own address. Until a domain is verified, `EMAIL_ALLOWLIST` limits all sending to the addresses listed, and digests are labelled as a preview. Settings tells anyone not on the list that the email goes only to the owner for now, rather than sending a confirmation link that would never arrive.
- **Links:**
  - **Signed.** Unsubscribe and "not for me" links carry a signature (`EMAIL_LINK_SECRET`) and the one thing they're for, so they work from the email without logging in and can do nothing else. They don't expire, since an unsubscribe link in an old email must still work. Production never signs or accepts them without the secret.
  - **Single use.** Confirmation (two days) and password reset (an hour) use single-use tokens stored as hashes, which expire; asking again stops the earlier link.
  - **Clicks, not visits.** The pages these links open confirm an address as they load, but unsubscribe and "not for me" wait for a click, so a mail app that checks links can't act for the person.
- **Password reset:** asking always gets the same answer, whether or not there's an account (and demo accounts never get one). Setting the new password counts as confirming the address and logs out every session.
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
| Stylist | The M10 evaluation still passes on LangGraph. Questions about trends and the digest answer from the tools. Nothing is saved before Confirm, and a confirmed action runs once even if Confirm is pressed twice. A turn waits until each proposal is decided, a new message answers what still waits with Not now, and a turn that doesn't wait keeps no checkpoint. |
| Privacy | Deleting an account removes its digests, picks, email events, tokens, and its checkpoints. Another person gets 404 for a digest or pick. |

Before the schedules are switched on, the owner reviews one real Trend Scout run by hand: its trends, sources, and quotes.

## 10. What the agents are not used for

- Choosing or scoring outfits, picks, or purchases.
- Counting anything, or producing prices, stock, or ratings.
- Trends without sources, or sources it didn't read.
- Comments on bodies, or inferring body shape, gender, or skin tone.
- Reading shop listing pages, or getting around logins, CAPTCHAs, or bot checks.
- Emailing anyone who hasn't confirmed.
