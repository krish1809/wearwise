# Seed data

Reference data loaded into the database by `backend/scripts/seed_reference.py` (run by `make migrate` and on every deploy). The app reads these from tables, never from these files at runtime.

| File | Contents | First used |
|---|---|---|
| `taxonomy.json` | 16 slots, 89 categories with default formality, warmth, and wears-before-wash; outfit templates; lists of patterns, fabrics, fits, sizing systems, seasons, statuses | M2 (sections, fits, sizing systems, category groups), M3 (the rest) |
| `colors.json` | 28 colour families with a representative hex and a neutrality value | M2 |
| `occasions.json` | 12 occasions with formality ranges | M2 |
| `style_profiles.json` | 12 style profiles with the colours, fabrics, fits, and categories that signal each | M2 |
| `archetypes.json` | 66 common wardrobe staples used by gap analysis and the starter capsule; no prices | M8 |

Notes:

- These are starting values written during planning. Expect to adjust them once you have used the app on your own wardrobe.
- IDs are stable keys. Rename the display `name` freely; change an `id` only with a migration.
- The seed script must be idempotent: running it twice changes nothing, and it never overwrites a user's custom rows.
- Cross-references were checked when the files were generated: every category points at a real slot and group, every archetype at a real category, colour, fabric, and style profile.
