# Seed data

Reference data loaded into the database by `backend/scripts/seed_reference.py` (run by `make migrate` and on every deploy). The app reads these from tables, never from these files at runtime.

| File | Contents | First used |
|---|---|---|
| `taxonomy.json` | 16 slots, 89 categories with default formality, warmth, wears-before-wash, and weather traits; outfit templates; lists of patterns, fabrics, fits, sizing systems, seasons, statuses | M2 (sections, fits, sizing systems, category groups), M3 (slots, categories, patterns, fabrics, seasons, statuses), M4 (outfit templates), M6 (traits) |
| `colors.json` | 28 colour families with a representative hex and a neutrality value | M2 |
| `occasions.json` | 12 occasions with formality ranges | M2 |
| `style_profiles.json` | 12 style profiles with the colours, fabrics, fits, and categories that signal each | M2 |
| `archetypes.json` | 66 common wardrobe staples used by gap analysis and the starter capsule; no prices | M8 |
| `demo.json` | The profile every demo copy starts with (occasions, usual week, styles, city), on top of the staples for the chosen section. Read by the demo code only, never loaded into reference tables | M11 |
| `trend_sites.json` | The sites the Trend Scout may search (Indian fashion magazines and the lifestyle pages of national news sites), and the shops, marketplaces, and social networks it never reads. For the owner to review. Read by the Trend Scout's code, never loaded into reference tables | M12 |
| `calendar.json` | The months festive and wedding seasons usually fall in, for the Trend Scout's queries: months, never dates, because festival dates move every year. Read by the Trend Scout's code | M12 |

Notes:

- These are starting values written during planning. Expect to adjust them once you have used the app on your own wardrobe.
- IDs are stable keys. Rename the display `name` freely; change an `id` only with a migration.
- The seed script must be idempotent: running it twice changes nothing, and it never overwrites a user's custom rows.
- Cross-references were checked when the files were generated: every category points at a real slot and group, every archetype at a real category, colour, fabric, and style profile.
