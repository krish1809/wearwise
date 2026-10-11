# WearWise product spec

This is the source of truth for what WearWise is and does.

## 1. What it is

WearWise is a personal wardrobe and styling web app. You catalogue everything you wear, it shows you the best outfits you can already make, plans your week, and tells you whether a new purchase is worth the money before you spend it.

It is not a store. There is no cart, checkout, payment, or order tracking. When WearWise recommends a product, the user finishes the purchase on the retailer's site.

**The promise:** know what to wear, see what your wardrobe is missing, and make every purchase count.

## 2. The problem

Written from the builder's own experience:

- I own clothes but can't tell which combinations look good, so I repeat the same three outfits.
- When I shop, there are too many brands, fabrics, and websites. I buy something that looked good online and it matches nothing I own.
- I forget the finishing pieces (belt, watch, shoes, fragrance) that make an outfit look complete.
- I have no idea which clothes I actually wear and which were a waste of money.

Existing wardrobe apps (Whering, Acloset, Cladwell) already do cataloguing and outfit planning. WearWise's difference is that one wardrobe dataset answers three linked questions:

1. What should I wear today?
2. What should I buy next, and what should I skip?
3. Am I getting value from what I own?

## 3. Who it is for

- People with a small wardrobe who want to build it up without wasting money.
- People with a large wardrobe who can't see what they have.
- Any gender. The app asks which sections you shop (menswear, womenswear, or both) and shows categories accordingly. It never guesses.
- India first: rupees, Indian retailers, ethnic wear as a first-class category, and summer / monsoon / winter rather than four temperate seasons.

## 4. Principles

1. **The engine decides, the AI explains.** Outfit scoring, purchase value, and analytics are deterministic code with tests. The language model only turns those results into words and handles conversation. The app must stay useful with the AI switched off.
2. **Nothing invented.** No made-up wardrobe items, prices, stock, ratings, or statistics. If data is missing or stale, say so on screen.
3. **Finished features only.** No dead buttons, fake success messages, or placeholder pages. A page ships when it works end to end.
4. **Optional means optional.** Onboarding can be skipped entirely. Every measurement and preference is editable and deletable later.
5. **No shaming.** Never comment negatively on bodies, budgets, or wardrobe size.
6. **Buy less, buy better.** Recommend the purchase that adds the most real use. "You don't need this" is a valid answer.
7. **Private by default.** Photos, measurements, and wardrobe data belong to the user. Every query is scoped to the logged-in user on the server.
8. **Categories are data.** Garment types, occasions, colours, and style profiles live in tables seeded from `seed/`, so adding a category never needs a code change.

## 5. Features

Tiers: **Core** ships in v1.0 (milestones M0 to M5). **Next** ships in v1.x (M6 to M11). **Stretch** is optional and only after launch. Items marked *(new)* were added during planning and were not in the original list.

### A. Account and onboarding (M1, M2)

| Feature | Tier |
|---|---|
| Register, log in, log out, password reset by email | Core (reset: Next) |
| Skippable onboarding in short steps, each with Skip and Back | Core |
| Step 1: which sections you shop (menswear / womenswear / both), city for weather | Core |
| Step 2: usual sizes (top, bottom, shoe) and fit preference (slim, regular, relaxed, oversized) | Core |
| Step 3: optional body measurements (chest/bust, waist, hips, shoulder, inseam, height) in cm or inches | Core |
| Step 4: occasions you dress for (college, work, parties, travel, festive...) | Core |
| Step 5: styles you like (minimal, Italian, Gen Z streetwear, linen/summer, old money, ethnic fusion...) and colours you love or avoid | Core |
| Step 6: budget (monthly, and typical spend per category such as "a shirt") | Core |
| Sign in with Google | Stretch |

### B. Profile and sizing (M2)

| Feature | Tier |
|---|---|
| Edit or delete every onboarding answer in Settings | Core |
| Brand size notes *(new)*: "M in H&M, L in Zara, 32 in Levi's" | Core |
| Show your usual size next to wishlist items and product results | Next |
| Compare measurements against a size chart the user enters or pastes | Stretch |

Fit advice is always labelled as guidance. Sizes vary by brand, so the app never promises a perfect fit.

### C. Wardrobe (M3)

| Feature | Tier |
|---|---|
| Add an item with photo, category, colour, pattern, fabric, fit, formality, season, occasions, style tags, brand, size, price, purchase date, notes | Core |
| Everything you wear: tops, bottoms, one-pieces, layers, ethnic wear, footwear, bags, belts, watches, eyewear, jewellery, headwear, scarves and ties, fragrance, grooming | Core |
| Sensible defaults from the category (a formal shirt starts at formality 4), so adding an item needs only photo, category, and colour | Core |
| Colour suggested from the photo (dominant colour, computed without AI) | Core |
| Photo-first grid with search, filters (category, colour, season, occasion, style, status), and sort | Core |
| Edit, archive, delete with confirmation | Core |
| Item status: available, in laundry, at repair, packed, lent out, retired | Core |
| Matching sets *(new)*: link a blazer and trousers as one suit so the engine prefers pairing them | Core |
| Custom categories and tags | Core |
| Quick add *(new)*: upload several photos, then fill details one by one from a queue | Next |
| AI auto-tagging: a vision model proposes category, colour, pattern, and fabric for the user to confirm | Next (M10) |
| Background removal for clean cut-out images | Stretch |

### D. Outfit Studio (M4)

| Feature | Tier |
|---|---|
| Build an outfit by slot (top, bottom, shoes, layer, accessories, fragrance) from your own items | Core |
| Save, name, favourite, tag with an occasion, duplicate, delete | Core |
| Swap one piece and keep the rest | Core |
| "I wore this today" in one tap; edit the wear log afterwards | Core |
| Finishing touches checklist *(new)*: belt, watch, bag, fragrance prompts so the look is complete | Core |

### E. Outfit engine (M5)

Full design in `docs/ENGINE.md`.

| Feature | Tier |
|---|---|
| "Suggest outfits" for an occasion, using only available items | Core |
| "What goes with this?" starting from one item | Core |
| "Complete this outfit" starting from two or more items | Core |
| A plain-language reason on every suggestion | Core |
| Results that differ from each other, not ten near-copies | Core |
| Like, dislike, and "not for me" feedback that changes future ranking | Core |
| Weather- and season-aware scoring | Core (weather data: M6) |
| Style-aware scoring ("make it more Italian", "more formal") | Next |
| "When a piece is missing": say what is missing and offer the closest outfit that works | Core |

### F. My Week (M6)

| Feature | Tier |
|---|---|
| Seven-day plan generated from your schedule, weather, and what is clean | Next |
| Swap a day's outfit, lock a day, regenerate the rest | Next |
| Events *(new)*: "wedding on the 24th, festive" planned ahead | Next |
| Laundry awareness *(new)*: each category has wears-before-wash; worn-out items drop out until you tap "laundry done" | Next |
| Weather forecast for your city with a manual fallback | Next |
| Packing list: trip dates, destination, occasions give the smallest set of items that covers every day | Next |
| Repeat guard *(new)*: tag who saw an outfit so you don't repeat it with the same group | Stretch |

### G. Insights (M7)

| Feature | Tier |
|---|---|
| Most and least worn items, wear timeline | Next |
| Cost per wear (price divided by wears), shown only when price is known | Next |
| Versatility *(new)*: how many good outfits each item appears in | Next |
| Orphans *(new)*: items that pair with almost nothing, and what would rescue them | Next |
| Coverage map *(new)*: occasions by seasons grid showing where you have plenty of outfits and where you have none | Next |
| Style profile *(new)*: your real palette and formality mix, computed from what you wear | Next |
| Declutter suggestions *(new)*: unworn for six months and low versatility | Next |

### H. Smart Shopping (M8)

| Feature | Tier |
|---|---|
| Add a candidate by hand, by pasting a link, or by uploading a screenshot | Next |
| Purchase analysis: what it matches, distinct new outfits it unlocks, what it duplicates, which orphans it rescues, cost per new outfit | Next |
| Verdict: Buy, Consider, or Skip, with the reasons | Next |
| Compare two or more candidates side by side | Next |
| Wishlist with buy next / later / skipped and a target price | Next |
| Gap analysis: the items that would add the most to your wardrobe, ranked | Next |
| Starter capsule *(new)*: for a small wardrobe, a staged shopping plan under a budget | Next |
| Budget split: "I have ₹3,000, what should I buy?" chosen from candidates | Next |
| Cooling-off reminder *(new)*: wishlist items resurface after a waiting period before you buy | Stretch |

### I. Product discovery (M9)

Design and sourcing rules in `docs/SHOPPING.md`.

| Feature | Tier |
|---|---|
| "Shop this gap": one-tap searches on Myntra, Ajio, Flipkart, Amazon with the right keywords and price cap | Next |
| Paste a product link and get it analysed against your wardrobe | Next |
| Browse a demo catalogue ranked by value to your wardrobe | Next |
| Live products from an official affiliate or product API, if access is approved | Stretch |
| Price-drop tracking on wishlist items | Stretch (needs a live source) |

### J. AI (M10)

Design in `docs/AI.md`.

| Feature | Tier |
|---|---|
| Auto-tag wardrobe photos | Next |
| AI Stylist chat that answers from your real wardrobe by calling the engine | Next |
| Outfit, item, and product cards inside chat replies | Next |
| Follow-ups ("make it more formal", "swap the shoes") | Next |
| Chat can save an outfit or add to the plan, after you confirm | Next |
| Friendlier wording on outfit reasons and purchase verdicts | Next |

### K. Style Guide (M8, content grows over time)

This answers the fabric, brand, and style confusion directly.

| Feature | Tier |
|---|---|
| Fabric guide *(new)*: cotton, linen, denim, wool, polyester, viscose and others with feel, season, care, and what to look for on the label | Next |
| Style profiles: what each aesthetic looks like, the pieces it needs, and which you already own | Next |
| Colour basics: neutrals, how many colours per outfit, matching leathers and metals | Next |
| Brand notebook *(new)*: your own notes per brand on size, quality, and price | Next |

### L. Privacy and account (M11)

| Feature | Tier |
|---|---|
| Download all my data as a file | Next |
| Delete my account and every photo | Next |
| Plain-language privacy page stating what is stored and which third parties see what | Next |

## 6. Pages

| Page | Purpose |
|---|---|
| Landing | What WearWise does, with a demo account button |
| Register / Log in | Account access |
| Onboarding | Skippable setup |
| Home | Today's outfit, weather, this week at a glance, one insight |
| Wardrobe | Grid, filters, add and edit items |
| Item | One item: photo, details, wears, cost per wear, what it goes with |
| Outfit Studio | Build, generate, and save outfits |
| My Week | Plan, events, laundry, packing |
| Shopping | Wishlist, candidates, analysis, gaps, capsule, discovery |
| Insights | Wear data, versatility, coverage, style profile |
| Stylist | AI chat |
| Style Guide | Fabrics, style profiles, colour basics, brand notebook |
| Settings | Profile, sizes, preferences, privacy |

## 7. Out of scope

- Checkout, payments, orders, returns.
- Native mobile apps. The site is responsive and can be installed as a PWA later.
- Social feed, followers, public profiles.
- Virtual try-on or generating images of the user wearing clothes.
- Inferring body shape, gender, or skin tone from photos.
- Bulk scraping of retailer sites (see `docs/SHOPPING.md` for why and what replaces it).

## 8. Definition of done

A feature is done when all of these hold:

- It works end to end against the real database, for a new account and for a populated one.
- The server checks that the data belongs to the logged-in user. There is a test that user A cannot read or change user B's data.
- Inputs are validated on the server. The form shows useful errors.
- Loading, empty, and error states exist and were looked at.
- It works at phone width and with a keyboard.
- Logic with rules in it (scoring, analytics, planning) has unit tests.
- Lint, type checks, and tests pass, and the output was actually read.
- `docs/PROGRESS.md` is updated, and any decision that changed is recorded in `docs/DECISIONS.md`.

## 9. How we will know it works

- **Acceptance rate:** share of suggested outfits that get saved, liked, or worn. Tracked per engine version.
- **Cataloguing effort:** median time to add one item. Target under 30 seconds with defaults.
- **Honesty checks:** zero chat replies that mention an item not in the user's wardrobe (enforced in code and measured in tests).
- **Personal test:** the builder uses it every morning for two weeks and buys nothing that the analyzer marked Skip.
