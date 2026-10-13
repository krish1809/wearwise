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
| `archetypes` | `id`, `name`, `category_id`, attributes as for items | `archetypes.json` |

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

**`item_images`**: `user_id` (the uploader; for ownership checks and cleanup), `item_id` (null between upload and saving the item; unsaved uploads are removed after a day), `storage_key`, `thumb_key`, `width`, `height`, `is_primary`, `dominant_hex` (D26).

## Outfits and wear (M4, M5)

**`outfits`**: `user_id`, `name`, `template_id`, `occasion_id`, `source` (manual, engine, stylist), `is_favorite`, `engine_version`, `score`, `reasons` (json).

**`outfit_items`**: `outfit_id`, `item_id`, `slot`. One row per item.

**`wear_logs`**: `user_id`, `worn_on` (date), `outfit_id` (nullable), `occasion_id`, `note`.

**`wear_log_items`**: `wear_log_id`, `item_id`. This table is the truth for every wear statistic. An outfit worn is expanded into its items at logging time, so later edits to the outfit don't rewrite history.

**`suggestion_feedback`**: `user_id`, `item_ids[]` (sorted), `occasion_id`, `verdict` (like, dislike, skip, saved, worn), `reason` (optional), `engine_version`.

**`pair_preferences`**: `user_id`, `item_a`, `item_b` (ordered so a < b), `weight`. Derived from feedback; can be rebuilt.

## Planning (M6)

**`events`**: `user_id`, `date`, `title`, `occasion_id`, `note`.

**`plan_days`**: `user_id`, `date` (unique per user), `occasion_id`, `outfit_id`, `status` (planned, worn, skipped), `locked`, `weather` (json snapshot).

**`trips`**: `user_id`, `destination`, `start_date`, `end_date`, `occasion_ids[]`. **`trip_items`**: `trip_id`, `item_id`.

**`weather_cache`**: `latitude`, `longitude` (rounded), `date`, `payload`, `fetched_at`.

## Shopping (M8, M9)

**`candidates`**

| Column | Notes |
|---|---|
| `user_id` | |
| `source` | manual, link, screenshot, catalog, adapter name |
| `url`, `title`, `brand`, `image_key` or `image_url` | |
| `price`, `currency`, `price_checked_at` | never shown without the check time |
| item attributes | same columns as `items`: category, colours, pattern, fabric, formality, warmth, seasons |
| `status` | considering, buy_next, later, skipped, purchased |
| `target_price` | optional |
| `analysis` | json, the last analyzer result |
| `analysis_wardrobe_version` | rerun when it differs from the user's current version |

Marking a candidate purchased offers to create an item from it.

**`catalog_products`**: `source`, `external_id`, `title`, `brand`, `url`, `image_url`, `price`, `currency`, attributes, `fetched_at`, `is_demo`. Unique on `(source, external_id)`.

## Chat (M10)

**`chat_threads`**: `user_id`, `title`.

**`chat_messages`**: `thread_id`, `role`, `content`, `tool_calls` (json), `cards` (json), `tokens_in`, `tokens_out`.

**`ai_usage`**: `user_id`, `date`, `requests`, `tokens`, used for rate limits and the spend cap.

## Deletion

Deleting an account removes every row above for that user and every stored image. Write this as one service function in M1 and extend it in each milestone, so M11's "delete my account" is already complete.
