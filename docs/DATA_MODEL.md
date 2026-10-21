# Data model

A starting schema. Each milestone creates only the tables it needs, through Alembic migrations. Adjust names and columns when implementation shows a better shape, and note the change in `DECISIONS.md`.

Conventions: UUID primary keys, `created_at` and `updated_at` on every table, `user_id` on every user-owned table, money stored as integer paise with a currency code.

## Reference data (seeded from `seed/`)

| Table | Key columns | Source |
|---|---|---|
| `categories` | `id` (slug; `custom_<uuid>` for custom rows), `user_id` (null for system rows), `name`, `group_id`, `slot`, `sections[]` (empty for custom rows, which always show), `formality_default`, `formality_min`, `formality_max`, `warmth`, `wears_before_wash`, `position`. Custom names are unique per user, ignoring capitals. | `taxonomy.json` |
| `outfit_templates` | `id`, `name`, `required` (json), `optional` (json) | `taxonomy.json` |
| `color_families` | `id`, `name`, `hex` (null for multicolour), `neutrality`, `position` | `colors.json` |
| `occasions` | `id`, `name`, `formality_min`, `formality_max`, `prefers_groups[]`, `hint`, `position`; `user_id` (null for system rows) arrives with custom occasions | `occasions.json` |
| `style_profiles` | `id`, `name`, `description`, `signals` (json), `position` | `style_profiles.json` |
| `category_groups` | `id`, `name`, `position` | `taxonomy.json` groups |
| `vocabulary_terms` | `kind` (section, fit, sizing_system, slot, pattern, fabric, season, status, formality), `id`, `name`, `position`; key `(kind, id)` | `taxonomy.json` lists |
| `archetypes` | `id`, `name`, `category_id`, `color`, `pattern`, `fabric`, `formality`, `warmth`, `seasons[]`, `sections[]`, `styles[]`, `attrs` (json), `position` (M8) | `archetypes.json` |
| `guide_entries` | `kind` (fabric, colour), `id` (a fabric's vocabulary id, or a colour basic), `body` (json: a fabric's feel, seasons, care, label, and watch; a colour basic's title and text), `position`; key `(kind, id)` (M8) | `guide.json` |

Custom categories and occasions are rows with a `user_id`.

Reference tables use the seed file's id (a slug) as the primary key, and `position` keeps the files' order. `backend/scripts/seed_reference.py` loads them after every migration and deploy; it inserts and updates, never deletes (D23).

## Accounts (M1, M2)

**`users`**: `email` (unique, lower-cased), `password_hash`, `name`, `wardrobe_version` (int), `onboarding_completed_at`, `is_demo` (set only by the demo script, D29).

**`sessions`**: `user_id`, `token_hash` (unique), `expires_at`, `last_seen_at`, `user_agent`.

**`rate_limit_hits`**: `bucket` (for example `login:ip:203.0.113.5`; emails are hashed), `window_start`, `count`. Unique on `(bucket, window_start)`.

**`profiles`** (one per user, `user_id` unique; every answer optional, D24):
`sections[]`, `city`, `units` (cm or in, default cm), `currency` (INR), `height_cm`, `measurements` (json: chest, waist, hips, shoulder, inseam, all in cm), `sizes` (json: top, bottom, shoe, each `{label, system}`), `fit_preference`, `style_profile_ids[]`, `preferred_colors[]`, `avoided_colors[]`, `occasion_ids[]`, `budget_monthly` (paise), `category_budgets` (json: category group to typical spend in paise), `onboarding_step` (0 to 6), `onboarding_skipped`, `onboarding_reminder_dismissed_at`. `latitude` and `longitude` arrive with weather in M6.

Lists and json columns default to empty and are never null: empty means not answered. Store measurements in cm to one decimal place and convert for display.

**`brand_notes`**: `user_id`, `brand`, `size_notes`, `quality_notes`, `price_notes`. Unique on `(user_id, lower(brand))`; at most 200 per user (D25).

## Wardrobe (M3)

**`items`**

| Column | Type | Notes |
|---|---|---|
| `user_id` | uuid | indexed |
| `category_id` | text | to `categories` |
| `slot` | text | copied from the category for fast filtering |
| `name` | text | optional; defaults to "colour + category" |
| `brand`, `size_label` | text | optional |
| `color_primary`, `color_secondary` | text | to `color_families` |
| `color_hex` | text | measured from the photo or picked |
| `pattern` | text | solid, stripe, check, print, graphic, texture |
| `fabric` | text | cotton, linen, denim, wool, polyester, viscose, silk, leather, knit, blend, other |
| `fit` | text | slim, regular, relaxed, oversized |
| `formality` | smallint | 1 to 5 |
| `warmth` | smallint | 0 to 5 |
| `seasons[]` | text[] | summer, monsoon, winter, mild |
| `occasion_ids[]`, `style_tags[]` | text[] | |
| `price`, `currency`, `purchased_on` | | optional |
| `status` | text | available, laundry, repair, packed, lent, retired |
| `wears_before_wash`, `wears_since_wash` | smallint | first is null for things that aren't washed |
| `set_id` | uuid | items sharing a value are a matching set |
| `attrs` | jsonb | slot-specific extras, such as scent family for a fragrance or strap colour for a watch |
| `notes` | text | |
| `archived_at` | timestamp | soft delete |

Indexes: `(user_id, archived_at)`, `(user_id, slot)`, `(user_id, category_id)`, and a GIN index on the array columns that get filtered.

Built in M3 as above, with these choices: `name` is optional and the app shows "colour + category" when it's empty; `pattern` defaults to solid and `status` to available; formality, warmth, and `wears_before_wash` start from the category; empty `seasons[]` means every season; `price` is paise with `currency`. Items reference `categories` with Postgres's default (checked at the end of each statement), so an account's items and custom categories are deleted together (D28).

**`item_images`**: `user_id` (the uploader; for ownership checks and cleanup), `item_id` (null between upload and saving the item; unsaved uploads are removed after a day), `candidate_id` (a shopping candidate's photo, which moves to the item when it's bought; M8), `storage_key`, `thumb_key`, `width`, `height`, `is_primary`, `dominant_hex` (D26).

## Outfits and wear (M4, M5)

**`outfit_templates`** (reference, from `taxonomy.json`): `id`, `name`, `required` (json: slot, and optionally `categories` or `exclude_categories`), `optional[]` (slots), `position`.

**`outfits`**: `user_id`, `name` (optional), `template_id`, `occasion_id`, `is_favorite`, `source` (manual or engine; stylist arrives with M10), `engine_version`, `score`, `reasons` (json list of `{code, kind, text}`). An outfit saved from a suggestion keeps the suggestion's version, score, and reasons; swapping a piece clears the score and reasons (D36).

**`outfit_items`**: `outfit_id`, `item_id` (null once the item is deleted), `slot`, `item_name` (kept so a deleted item shows as removed). One row per slot, unique on `(outfit_id, slot)` (D30).

**`wear_logs`**: `user_id`, `worn_on` (date), `outfit_id` (nullable; null once the outfit is deleted), `occasion_id`, `note`. Indexed on `(user_id, worn_on)`.

**`wear_log_items`**: `wear_log_id`, `item_id` (null once the item is deleted), `slot`, `item_name`. Unique on `(wear_log_id, item_id)`. This table is the truth for every wear statistic. An outfit worn is expanded into its items at logging time, so later edits to the outfit don't rewrite history. `items.wears_since_wash` is recounted from it as wears after `items.last_washed_on` (D31).

**`suggestions`**: `user_id`, `kind` (occasion, with_item, complete), `occasion_id`, `season`, `template_id`, `item_ids[]` (every piece, in slot order), `core_ids[]` (sorted), `score`, `components` (json), `reasons` (json), `compromise`, `engine_version`, `rating` (like, dislike, skip, or null), `saved_outfit_id`, `wear_log_id`, `worn_on`. One row per outfit shown; item ids are plain arrays, so a deleted item makes a suggestion stale rather than breaking it. Indexed on `(user_id, created_at)` (D36).

**`suggestion_feedback`**: `user_id`, `suggestion_id`, `item_ids[]` (the core pieces, sorted), `occasion_id`, `verdict` (like, dislike, skip, saved, worn), `reason` (for a dislike: item, colors, formality, occasion, other), `item_id` (the piece, when the reason is item), `engine_version`.

Pair preferences are not a table: they are worked out from `suggestion_feedback` on every request, so they can't drift from it (D36).

## Planning (M6)

**`profiles`** gained `latitude`, `longitude` (the place chosen for `city`, rounded to two decimals), `manual_weather` (hot, mild, cold, rainy, or null for the season), `weekday_occasions` (json: "0" Monday to "6" Sunday to an occasion), and `laundry_weekday` (0 to 6, or null). **`categories`** gained `traits[]` (bare_legs, open_toe), from the seed.

**`events`**: `user_id`, `day`, `title`, `occasion_id`, `note`. Indexed on `(user_id, day)`.

**`plan_days`**: `user_id`, `day` (unique per user), `occasion_id` (chosen for the day; null follows events and the usual week), `planned_occasion_id`, `template_id`, `item_ids[]`, `core_ids[]`, `score`, `reasons` (json), `missing` (json), `locked`, `wear_log_id` (set once worn), `weather` (json snapshot: source, feels_like, rain_chance), `engine_version` (D40).

**`trips`**: `user_id`, `destination`, `latitude`, `longitude`, `start_date`, `end_date`, `days` (json: each day and its occasion), `outfits` (json: each day's outfit, reasons, and weather, or why it has none), `engine_version`. **`trip_items`**: `trip_id`, `item_id`, unique together (D41).

**`weather_forecasts`**: `latitude`, `longitude` (rounded), `fetched_on`, `fetched_at`, `days` (json). Unique on `(latitude, longitude, fetched_on)`; shared by everyone near a place, with no user data (D39).

## Shopping (M8, M9)

**`candidates`** (built in M8, D45)

| Column | Notes |
|---|---|
| `user_id` | |
| `source` | `manual`, `archetype` (with `archetype_id`), `link` (only when a pasted page was actually read, M9), or `catalog`; screenshot arrives in M10 |
| `name`, `brand`, `url`, `image_url`, `size_label`, `notes` | `url` and `image_url` must be http or https; the picture is shown from the shop's address, never copied (D46) |
| `price`, `currency`, `price_checked_at` | never shown without the check time |
| item attributes | `category_id`, `slot`, `color_primary`, `color_secondary`, `color_hex`, `pattern`, `fabric`, `fit`, `formality`, `warmth`, `seasons[]` |
| `status` | considering, buy_next, later, skipped, purchased (purchased only by buying it) |
| `target_price` | optional |
| `remind_on` | optional date (M10b): "sleep on it"; on that day the shopping list asks whether it's still wanted. Set only to a day after today and within a year; cleared when the person answers, skips it, or buys it |
| `analysis` | json, the last analysis and verdict |
| `analysis_key` | a hash of everything the analysis depends on (wardrobe version, engine version, occasions, styles and colours, reactions, sections, budgets, and the candidate's attributes and price); worked out again when it differs |
| `item_id` | the wardrobe item made from it when bought |

Marking a candidate bought creates the item, with the candidate's photo, through the same code as adding an item.

**`catalog_products`** (built in M9, D46): `source`, `external_id`, `title`, `brand`, `url`, `image_url`, `price`, `currency`, `category_id`, `color_primary`, `pattern`, `fabric`, `formality`, `warmth`, `seasons[]`, `sections[]`, `fetched_at`, `is_demo`. Unique on `(source, external_id)`. Demo rows have no price and no URL.

**`link_previews`** (M9, D46): `url` (unique), `fetched_at`, `outcome` (ok, blocked, unavailable, not_product), `data` (json: the page's preview data). Shared by everyone, with nothing about who pasted the link; read again after a day, or after 30 minutes for a failure.

## Chat (M10)

**`chat_threads`**: `user_id`, `title` (the first message, shortened).

**`chat_messages`**: `thread_id`, `role` (user, assistant), `content`, `cards` (json: outfit, item, candidate, and staple cards by id, and action cards), `tool_calls` (json: the tools called, with arguments), `seen` (json: ids the tools returned for this reply, which later replies in the thread may show), `tokens_in`, `tokens_out` (D47).

**`chat_actions`**: `user_id`, `thread_id`, `kind` (save_outfit, plan_outfit, add_to_list, log_wear), `payload` (json, with a one-line summary), `status` (pending, done, cancelled), `result` (json: what confirming made). Nothing is changed until the person confirms (D47).

**`ai_usage`**: `user_id`, `day`, `messages`, `images`, `tokens_in`, `tokens_out`, `cost_micro_usd`; unique per person per day. Used for the limits and the daily spend cap.

## Interaction and polish (M10b)

**`profiles`** gained `challenge_started_on` (date, or null when no challenge runs): the start of the "wear what you own" challenge. Its progress is not stored; it's counted on every request from `wear_log_items` between the start and the 60th day, over the pieces in the wardrobe now (not archived or retired).

**`candidates`** gained `remind_on` (see Shopping).

The theme choice is not stored on the server: it's a per-browser setting (D48).

## Deletion

Deleting an account removes every row above for that user and every stored image (D50). The rule that makes it complete: every table with a `user_id` points at `users` with ON DELETE CASCADE, and every table without one hangs off such a table with ON DELETE CASCADE (`chat_messages`, `outfit_items`, `trip_items`, `wear_log_items`). The same rule decides what "Download my data" exports. Every other table must be listed as shared in `app/services/export.py` (reference data, `link_previews`, `catalog_products`, `weather_forecasts`, `rate_limit_hits`, `app_meta`); a test fails for a table that is neither.

Nothing personal is kept forever outside a person's own rows: rate-limit counts (which can name an IP address, or a hash of an email) are deleted within a day, and photos uploaded but never saved with anything after about a day.
