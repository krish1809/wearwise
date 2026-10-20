# WearWise roadmap

Twelve milestones, M0 to M11. Each one is a vertical slice: database, API, UI, and tests for one area, deployed and usable at the end. Nothing is built as a mock-up first and wired up later.

**v1.0 is M0 to M5.** At that point WearWise is a deployed app where you catalogue your wardrobe, build outfits, and get ranked suggestions with reasons. That is already a complete portfolio project. M6 to M11 make it the full product.

## Overview

| # | Milestone | You can now... | Rough effort |
|---|---|---|---|
| M0 | Foundations | open a live URL that talks to the API and database | 2 to 3 days |
| M1 | Design system, shell, auth | register, log in, and move around a styled, empty app | 4 to 6 days |
| M2 | Onboarding and profile | set (or skip) sizes, style, budget; edit them later | 3 to 4 days |
| M3 | Wardrobe | add, find, edit everything you own, with photos | 6 to 8 days |
| M4 | Outfit Studio and wear log | build and save outfits; log what you wore | 4 to 5 days |
| M5 | Outfit engine | get ranked outfit suggestions with reasons | 7 to 10 days |
| | **v1.0 release** | | **about 5 to 7 weeks** |
| M6 | My Week | plan seven days with weather, laundry, events, packing | 6 to 8 days |
| M7 | Insights | see cost per wear, versatility, orphans, coverage | 4 to 5 days |
| M8 | Smart Shopping I | analyse a purchase; see gaps; plan a capsule on a budget | 7 to 10 days |
| M9 | Smart Shopping II | find real products for a gap | 5 to 7 days |
| M10 | AI | auto-tag photos; chat with a stylist that knows your wardrobe | 7 to 10 days |
| M10b | Interaction and polish | drag outfits together, swipe suggestions, see your colours, and use a few new everyday tools | 6 to 8 days |
| M11 | Hardening and launch | hand the link to anyone | 5 to 7 days |

Effort is a guess, counted in working days of two to three focused hours. Treat it as a way to notice when a milestone has grown too big, not as a deadline.

**Order rules**

- M0 to M5 are strictly in order.
- M6 and M7 can swap.
- M8 needs M5. M9 needs M8.
- The auto-tagging half of M10 can be pulled forward to any point after M3 if adding items by hand is too slow.

## Before M0: things only you can do

- [ ] Create the GitHub repo `wearwise` and push the docs.
- [ ] Photograph 25 to 30 of your own items against a plain wall or bedsheet, in daylight. They are your test data for every milestone.
- [ ] Create accounts: Vercel, Render, Neon, Backblaze (for B2 photo storage). No payment is needed to start; check each signup page.
- [ ] If you want live product data later, apply now for an affiliate or product API (see `docs/SHOPPING.md`). Approval can take weeks, and M9 works without it.

---

## M0. Foundations

**Goal:** a walking skeleton, deployed. One page on the frontend calls one endpoint on the backend, which reads one row from Postgres.

**Build**
- Monorepo: `frontend/` (Next.js, TypeScript, Tailwind), `backend/` (FastAPI, SQLAlchemy, Alembic), `docker-compose.yml` for local Postgres.
- `GET /api/v1/health` returns app version and a database check. The home page shows it.
- Lint, format, type check, and test commands for both sides, plus one passing test each.
- GitHub Actions running those checks on every pull request.
- Deploy: frontend on Vercel, backend on Render, database on Neon. Environment variables documented in `.env.example`.
- One command each for dev, test, lint, type check, and migrate, documented in the README.

**Done when**
- The production URL shows "API ok, database ok".
- A fresh clone runs locally by following the README, with no step missing.
- CI is green on a pull request.

**Learn:** how a request travels from browser to Next.js to FastAPI to Postgres; environment variables; migrations; what CI is for.

---

## M1. Design system, app shell, auth

**Goal:** the app looks like WearWise and knows who you are.

**Build**
- Design tokens and base components from `docs/DESIGN_SYSTEM.md`: button, input, select, chip, card, dialog, toast, skeleton, empty state.
- App shell: top bar and sidebar on desktop, bottom tab bar on phone. Only links to pages that exist.
- Register, log in, log out. Passwords hashed with Argon2. Sessions in an httpOnly cookie, stored server-side.
- Protected routes redirect to log in. A `current_user` dependency guards every API route.
- Landing page with the real product description.
- A `/styleguide` page (development only) showing every component and state.

**Done when**
- You can register, log out, log back in, and reach a protected page, in production.
- Wrong password, duplicate email, and expired session each show a clear message.
- Tests cover: register, log in, a protected route rejecting an anonymous request.
- The shell works at 375 px and 1440 px wide, and with keyboard only.

**Learn:** password hashing; cookies versus tokens; CSRF; why the frontend proxies API calls (see `docs/ARCHITECTURE.md`).

---

## M2. Onboarding and profile

**Goal:** WearWise knows your sizes, style, and budget, but only if you choose to tell it.

**Build**
- The six onboarding steps from the spec, one screen each, with Skip, Back, and "Skip all".
- Profile, measurements, brand size notes, style and colour preferences, budget, and occasions tables.
- Settings pages to edit or clear every answer.
- Seed `seed/occasions.json`, `seed/style_profiles.json`, and `seed/colors.json` into the database.

**Done when**
- A new user can skip everything and land on Home with a working app.
- Every answer can be changed and deleted later.
- Units convert correctly between cm and inches (tested).
- User A cannot read user B's profile (tested).

**Learn:** modelling optional data; form validation on both sides; seeding reference data.

---

## M3. Wardrobe

**Goal:** your real wardrobe is in the app and easy to browse.

**Build**
- Categories seeded from `seed/taxonomy.json`, filtered by the sections you shop, with a "show all" switch. Custom categories.
- Item create, edit, archive, delete. Defaults come from the category so the minimum is photo, category, colour.
- Photo upload: validate type and size, resize, make a thumbnail, store through a storage interface (local folder in development, Backblaze B2 in production).
- Dominant colour picked from the photo and mapped to a colour family from `seed/colors.json`, editable.
- Grid with search, filters, sort, and pagination. Item detail page.
- Status changes (available, laundry, repair, packed, lent, retired) and matching sets.
- A separate script that loads a demo wardrobe into a demo account only.

**Done when**
- You have added your own 25 to 30 items and can find any of them in two interactions.
- Adding an item with defaults takes under 30 seconds.
- Uploads reject non-images and oversized files with a clear message.
- Tests cover CRUD, filters, ownership, and the upload validator.

**Learn:** file uploads and object storage; database indexes for filtering; pagination; image processing.

---

## M4. Outfit Studio and wear log

**Goal:** outfits exist as saved things, and the app knows what you wore.

**Build**
- Builder: pick items by slot, see them laid out together, save.
- Template rules from the taxonomy (a top needs a bottom; a one-piece doesn't).
- Favourites, occasion tags, duplicate, delete, swap one piece.
- "I wore this" for an outfit or for loose items, with date; edit and delete wear logs.
- Finishing touches prompt for empty accessory slots.
- Wears-since-wash counter updates on each wear (used fully in M6).

**Done when**
- You can save an outfit and mark it worn, and the item pages show the wear.
- Deleting an item doesn't break saved outfits (they show the item as removed).
- Tests cover template validation and wear logging.

**Learn:** many-to-many relationships; soft delete; optimistic UI updates.

---

## M5. Outfit engine (v1.0)

**Goal:** WearWise suggests outfits you would actually wear, and says why.

**Build** (design in `docs/ENGINE.md`)
- A pure Python engine package with no database or web imports.
- Pair scoring: colour, formality, pattern, fabric and season, style.
- Outfit generation with hard filters, context scoring (occasion, season, rotation), and a diversity pass.
- Three entry points: suggest for an occasion, what goes with this item, complete this outfit.
- Reason codes turned into sentences.
- Like / dislike / skip feedback stored and used in ranking.
- A golden set of at least 60 hand-labelled pairs from your own wardrobe, used as a regression test.
- Engine version stored with each suggestion.

**Done when**
- For your own wardrobe, you would wear at least 6 of the top 10 suggestions for "college" and for one other occasion. Write the count in `docs/PROGRESS.md`.
- No suggestion ever includes an unavailable item, another user's item, or two items in the same slot (property tests).
- The golden set passes at the agreed threshold.
- Suggestions for a 150-item test wardrobe return in under one second.

**Then release v1.0:** tag it, record a two-minute demo, update the README.

**Learn:** turning fuzzy taste into testable rules; scoring and ranking; property-based testing; measuring quality.

---

## M6. My Week

**Goal:** the week is planned around weather, events, and what is clean.

**Build**
- Weather for the user's city from Open-Meteo, cached, with a manual "hot / mild / cold / rainy" fallback.
- Weekly planner over the engine: no item repeated too soon, laundry respected, locked days kept.
- Events with a date and dress code.
- Laundry view: what needs washing, "laundry done" resets counters.
- Packing list for a trip.

**Done when**
- A generated week has no repeated top and no item past its wear limit.
- Locking two days and regenerating changes only the other five.
- With the weather service down, planning still works on the manual setting.

**Learn:** search under constraints (beam search); caching third-party APIs; graceful degradation.

---

## M7. Insights

**Goal:** you can see what you wear, what is good value, and where the holes are.

**Build**
- Wear counts, last worn, cost per wear.
- Wardrobe graph: versatility, orphans.
- Coverage map of occasions by seasons.
- Style profile from wear history.
- Declutter suggestions.

**Done when**
- Every number can be traced to rows in the database (tested against a fixed fixture).
- Items with no price show "add a price" instead of a made-up cost per wear.
- Charts are readable on a phone and have text alternatives.

**Learn:** SQL aggregation; graph metrics; honest data visualisation.

---

## M8. Smart Shopping I

**Goal:** before you buy, you know what the item adds.

**Build** (design in `docs/SHOPPING.md`)
- Candidates and wishlist.
- Purchase analyzer: distinct new outfits, coverage gain, redundancy, orphans rescued, cost per new outfit, verdict.
- Compare candidates.
- Gap analysis using the archetype list in `seed/archetypes.json`.
- Starter capsule and budget split.
- Style Guide pages (fabrics, style profiles, colour basics, brand notebook).

**Done when**
- Analysing an item identical to one you own returns Skip and names the duplicate.
- A candidate that only repeats outfits you can already make scores lower than one that opens a new occasion (tested).
- The budget split never exceeds the budget, and matches exhaustive search on small test cases.

**Learn:** marginal value; diminishing returns; knapsack-style selection.

---

## M9. Smart Shopping II

**Goal:** from a gap to real products you can click through to.

**Build**
- Source adapter interface with at least three adapters: retailer search links, pasted-link import, demo catalogue.
- Ranking of real products by value to this wardrobe, within budget.
- Source, fetch time, and a "may be out of date" marker on every product card.
- An affiliate or product API adapter only if access has been approved.

**Done when**
- Every product shown has a real source and URL, or is clearly marked as demo data.
- A failing or blocked source degrades to search links without an error page.
- No adapter ignores robots.txt or works around a login, CAPTCHA, or bot check.

**Learn:** the adapter pattern; working with third-party data responsibly; timeouts and retries.

---

## M10. AI

**Goal:** adding clothes is fast, and you can talk to WearWise.

**Build** (design in `docs/AI.md`)
- Provider interface with one real provider and one fake for tests.
- Auto-tagging: photo in, proposed attributes out, user confirms.
- Stylist chat with tool calls into the engine, analyzer, and insights.
- Cards in replies; confirmation before any write.
- A grounding check that rejects any reply naming an item ID the user doesn't own.
- Rate limits and a daily spend cap.

**Done when**
- The evaluation set in `docs/AI.md` passes, including zero invented items.
- With the AI key removed, every non-chat feature still works and chat shows a clear "unavailable" state.
- No tool can be called with another user's ID (tested).

**Learn:** tool calling; grounding and validation; evaluating AI features; cost control.

---

## M10b. Interaction and polish

Added on 2026-10-20 at the owner's request, after M9: the app works; this makes it feel like WearWise rather than a set of forms. Everything here uses data the app already has; nothing is invented to fill a screen.

**Goal:** the core screens are direct and pleasant to use, and a few small tools make everyday use stick.

**Build**
- Outfit Studio by drag and drop: drag a piece onto the board, or between slots, with a live score that moves as pieces change (keyboard and tap still work).
- Swipe suggestions on phones: right to like, left to dislike, tap for the reasons; the same feedback the buttons send.
- A colour map of the wardrobe: items plotted by hue and lightness (the engine's own colour space); tap an area to filter the wardrobe.
- "What if" in Shopping: put a candidate on the board with pieces you own and watch the outfit count change.
- A coverage map you can tap: each occasion and season opens its outfits, or what's missing there.
- Polish: transitions that respect reduced motion, undo on destructive toasts, a quick-jump menu (Ctrl or Cmd + K), and a dark theme from the design tokens.
- Cooling-off: something on the shopping list comes back after a waiting period you choose, asking whether you still want it.
- "Wear what you own": a 60-day challenge to wear every piece at least once, from the wear log, with progress.
- Remix: pick up to ten pieces and see every good outfit they make.

**Done when**
- Every drag action has a keyboard and tap equivalent (tested), and nothing moves for people who ask for reduced motion.
- Swipe and buttons send identical feedback (tested), and an accidental swipe can be undone.
- Both themes pass contrast checks for body text, and the screenshots at 375 px and 1440 px match the design system in both.
- The challenge, cooling-off, and remix numbers come only from rows in the database (tested against a fixture).

**Learn:** pointer and keyboard interaction design; motion with restraint; theming with tokens.

---

## M11. Hardening and launch

**Goal:** safe to share, easy to understand.

**Build**
- Security pass: authorisation on every route, rate limits, upload handling, headers, dependency audit.
- Accessibility pass: keyboard, focus, contrast, labels.
- Performance pass: image sizes, slow queries, bundle size.
- End-to-end tests for the five main journeys.
- Data export and account deletion. Privacy page.
- Error tracking and basic logs.
- Demo account with a seeded wardrobe, reset nightly.
- README with screenshots, architecture diagram, and a short write-up of the engine.

**Done when**
- A stranger can open the link, try the demo account, and understand the product in two minutes.
- All end-to-end tests pass against production.
- The known limitations are written down in the README.

---

## After launch (stretch)

Pick by interest, one at a time:

- Learned compatibility model trained on a public outfit dataset, compared against the rule engine.
- Installable PWA with camera capture.
- Background removal for item photos.
- Sign in with Google.
- Price-drop tracking (needs a live product source).
- Repeat guard by social group.
- Size-chart comparison.
