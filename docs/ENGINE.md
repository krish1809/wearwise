# Outfit engine

The engine is the core of WearWise. It is ordinary, deterministic Python: given the same wardrobe and context it returns the same outfits, and every number in it can be explained and tested. The AI layer calls it; it never replaces it.

All numbers below are starting values. They are meant to be tuned against the golden set (section 9), and they live in one config file so tuning never means hunting through code.

## 1. Inputs and outputs

```
suggest(wardrobe, context, n) -> list[ScoredOutfit]

wardrobe : items with category, slot, colour, pattern, fabric, fit, formality,
           warmth, seasons, style tags, status, wear history, set id
context  : occasion, date, weather (optional), requested style (optional),
           anchor items (optional), exclusions, user preferences, feedback
returns  : outfits with a score, per-component scores, and reason codes
```

Three entry points share one pipeline:

| Entry point | Anchors |
|---|---|
| Suggest for an occasion | none |
| What goes with this? | one item |
| Complete this outfit | two or more items |

## 2. Pipeline

```
1. Filter      drop items that can't be used at all
2. Template    pick outfit templates that the remaining items can fill
3. Generate    enumerate or beam-search the core slots
4. Score       pair scores -> outfit base score -> context score
5. Accessorise add the best belt, watch, bag, fragrance where they fit
6. Diversify   pick n results that differ from each other
7. Explain     turn the strongest score components into reasons
```

## 3. Hard filters

An item is removed before generation if any of these is true:

- It belongs to another user, or is archived.
- Its status isn't `available`, or `wears_since_wash >= wears_before_wash`.
- Its colour is on the user's avoided list.
- Its formality is two or more steps outside the occasion's range.
- The context has a season and the item's seasons don't include it (skipped if the item has no seasons set).
- The user excluded it for this request.

An outfit is rejected if any core pair differs by three or more formality steps, or if two items occupy the same slot.

## 4. Templates

Templates are data from `seed/taxonomy.json`, so new garment structures need no code:

| Template | Required | Optional |
|---|---|---|
| Separates | top, bottom, footwear | layer, accessories, fragrance |
| One-piece | one-piece, footwear | layer, accessories, fragrance |
| Saree | saree, saree blouse, footwear | accessories, fragrance |

"Core" below means the required slots plus the layer.

## 5. Pair score

For two items `a` and `b` in different slots, `P(a, b)` is between 0 and 1.

```
P(a,b) = 0.35*colour + 0.30*formality + 0.15*pattern + 0.10*fabric + 0.10*style + pref(a,b)
```

`pref(a, b)` is the learned adjustment from feedback, between -0.2 and +0.2. If `a` and `b` share a `set_id`, `P = 1`.

### Colour (0 to 1)

Convert each item's hex to OKLCH: lightness `L`, chroma `C`, hue `h`. An item is neutral if its colour family has neutrality of 0.8 or more, or its chroma is very low.

| Case | Score |
|---|---|
| One or both neutral, lightness differs by 0.25 or more | 0.95 |
| One or both neutral, similar lightness | 0.85 |
| Both chromatic, hue within 15 degrees, lightness differs by 0.2 or more (tonal) | 0.80 |
| Both chromatic, hue within 15 degrees, similar lightness (near-miss match) | 0.55 |
| Hue 15 to 45 degrees apart (analogous) | 0.75 |
| Hue 45 to 100 degrees apart | 0.35 |
| Hue 100 to 150 degrees apart | 0.50 |
| Hue 150 to 180 degrees apart, one of them muted | 0.70 |
| Hue 150 to 180 degrees apart, both saturated | 0.45 |

### Formality (0 to 1)

| Difference in steps | Score |
|---|---|
| 0 | 1.0 |
| 1 | 0.8 |
| 2 | 0.4 |
| 3 or more | reject |

### Pattern (0 to 1)

| Case | Score |
|---|---|
| Solid with solid | 0.9 |
| Solid with patterned | 1.0 |
| Two patterns of different kinds | 0.5 |
| Two patterns of the same kind | 0.25 |
| Graphic with any pattern | 0.2 |

### Fabric and season (0 to 1)

Start at 0.8. Drop to 0.3 for known clashes (linen with heavy wool, technical sportswear with suiting or silk) and to 0.5 for denim on denim in a similar shade. Multiply by 0.5 if the two items share no season.

### Style (0 to 1)

Jaccard overlap of style tags. If either item has no tags, 0.5.

## 6. Outfit base score

Not every pair matters equally.

| Slot pair | Weight |
|---|---|
| top and bottom | 1.0 |
| top and layer | 0.9 |
| bottom and footwear | 0.8 |
| belt and footwear | 0.7 |
| layer and bottom | 0.6 |
| top and footwear | 0.5 |
| any accessory with a core item | 0.3 |

```
mean  = weighted mean of P over the outfit's core pairs
worst = lowest P among the core pairs
B     = 0.7*mean + 0.3*worst
```

The `worst` term means one bad pairing drags the outfit down even when everything else agrees.

Outfit-level adjustments to `B`:

- More than two distinct chromatic hue groups among the core items: minus 0.15.
- More than one patterned core item: minus 0.10.
- Belt and shoes both leather and the same colour family: plus 0.05. Clearly different: minus 0.05.

## 7. Context score

```
Score = 0.50*B + 0.15*O + 0.10*W + 0.10*R + 0.10*U + 0.05*S
```

**O, occasion.** 1 if the mean formality of the core items is inside the occasion's range, falling 0.35 for each step outside. Plus 0.1 if the occasion prefers a group (festive prefers ethnic) and the outfit has it.

**W, weather.** Compare the outfit's upper-body warmth (`top + layer`, or `one-piece + layer`) with a band chosen by feels-like temperature.

| Feels like | Target upper warmth | Extra rules |
|---|---|---|
| 32 °C and above | 1 | plus for linen and cotton; minus for polyester and layers |
| 25 to 32 °C | 1 to 2 | shorts fine |
| 18 to 25 °C | 2 to 4 | |
| 10 to 18 °C | 4 to 6 | |
| below 10 °C | 6 and above | minus for shorts and open footwear |
| Rain likely | | minus for suede, canvas, and white or very light bottoms |

`W` is 1 inside the band and drops 0.3 per unit outside. With no weather data, use the season from the user's settings, and treat monsoon as "rain likely". (Until M6, the season came from the request or the month, with bands chosen for Indian seasons: D34. Since M6 the forecast's feels-like temperature, the middle of the day's apparent maximum and minimum, sets the band, and the manual setting stands in when there's no forecast: D39.)

**R, rotation.** For each core item, `min(days since last worn, 14) / 14`, with never-worn counted as 1. `R` is the mean. If the exact same core outfit was worn in the last 7 days, `R = 0`.

**U, user preference.** The mean, over core items, of a like-rate estimated from feedback for that item's colour family and category: `(likes + 1) / (likes + dislikes + 2)`. Preferred colours and the preferred fit from the profile add a small bonus.

**S, style.** The share of core items that match the requested style's signals from `seed/style_profiles.json`. If no style is requested, use the profile's styles; if none, 0.5. (An item that isn't tagged with the style also needs one of its colours or categories: D42.)

## 8. Generation, accessories, diversity, reasons

**Generation.** Multiply the item counts of the core slots. If the product is 50,000 or less, enumerate everything (5,000 in v1.0, measured in D35). Otherwise beam-search: fill slots in the order top, bottom, footwear, layer, keeping the best 200 partial outfits by partial score. With anchors, their slots are fixed.

**Accessories.** For each of the best 50 core outfits, look at each optional slot and add the accessory with the highest mean pair score against the core, if that score is 0.7 or more. Fragrance is chosen by season, occasion, and time of day from its `attrs`, not by pair score.

**Diversity.** Pick results one at a time (maximal marginal relevance):

```
next = argmax over candidates of  0.7*Score(o) - 0.3*max similarity(o, already picked)
similarity = Jaccard overlap of core item IDs
```

No single non-anchor item may appear in more than half the results.

**Reasons.** Every component emits reason codes with a strength, for example `color.neutral_plus_accent`, `color.tonal`, `formality.match`, `pattern.one_statement`, `weather.breathable`, `rotation.not_worn_recently`, `set.match`, and cautions such as `formality.shoes_more_casual`. Show the two or three strongest positives and any caution. The sentences for each code live in one file, so wording changes never touch scoring.

**When something is missing.** If no template can be filled, return which slot is empty and why ("no footwear at this formality is clean"), then relax the occasion by one step and return the closest outfits, flagged as a compromise.

## 9. Knowing whether it is any good

| Check | What it is | Pass mark |
|---|---|---|
| Golden pairs | 60 or more pairs from a real wardrobe, hand-labelled good / fine / bad | The engine's ordering agrees with the labels on 80% of good-versus-bad comparisons |
| Golden outfits | 10 outfits the owner loves | Each appears in the top 20 for its occasion |
| Property tests | Random wardrobes | Never an unavailable item, never two items in a slot, never another user's item, scores always in range |
| Wear test | Top 10 for two occasions on the owner's wardrobe | Owner would wear 6 or more |
| Acceptance rate | Saved, liked, or worn divided by shown, per engine version | Tracked, should rise between versions |
| Speed | 150-item wardrobe | Under one second |

Any weight change is a new `ENGINE_VERSION`. Run the golden set before and after, and write both numbers in `DECISIONS.md`.

## 10. Learning from feedback

- **Like, saved, worn** nudge each core pair's `pref` towards +0.2. **Dislike** nudges towards -0.2. Update rule: `pref += 0.3 * (target - pref)`.
- A dislike with the reason "I don't like this item" lowers that item only, not its pairs.
- The same events update the like and dislike counts behind `U`.
- Global weights stay fixed per engine version. Once there are a few hundred feedback events, try fitting the component weights with logistic regression and compare on the golden set.

## 11. Wardrobe graph

Items are nodes. Two items in different slots are connected if `P >= 0.65`.

| Measure | Definition | Used for |
|---|---|---|
| Versatility | Number of distinct good outfits (`Score >= 0.7` and dressed at the occasion's level, D44, for any of the user's occasions) containing the item | Insights, purchase analysis |
| Orphan | Available item with versatility below 2 | Insights, "rescue" suggestions |
| Coverage | For each occasion and season, the number of distinct good outfits, capped at 10 | Gap analysis, purchase analysis |

"Distinct" means after the diversity step, so ten outfits that differ only in the watch count once.

These measures describe the wardrobe, not today. Compute them over every item that isn't archived or retired (ignore laundry and packed status), with rotation fixed at 1 and weather taken from the season, so the numbers don't shift from day to day. Cache all three per `wardrobe_version`. (Built as: distinct core pieces, so an accessory never makes a new outfit; an accessory's versatility is the good outfits it finishes; occasions from onboarding and the usual week; a one-sentence rescue for each orphan; cached per wardrobe version, engine version, occasions, and reactions: D43. Since M11 the cache is a table, `saved_measures`, one row per person under that fingerprint, so it outlasts the server's sleep: D53.)

## 12. Weekly planner (M6)

**Input:** seven days, each with an occasion and weather; locked days; current wear state of each item.

**Constraints**
- An item can't be planned once its simulated `wears_since_wash` reaches its limit. The simulation runs forward through the week and resets on a laundry day if the user sets one.
- The same top is not planned twice within three days.
- The same footwear is not planned three days in a row.
- Locked days are fixed.

**Objective:** the sum of daily scores, plus a small bonus for variety across the week (distinct colours and categories), minus penalties for repeats.

**Method:** beam search over days with width 50. For each partial week, ask the engine for the top 20 outfits for the next day given the simulated state, extend, and keep the best 50. That is at most 7 x 50 x 20 outfit evaluations. (Built as: each day's 40 best outfits ranked once, spread across the wardrobe; each choice also checked against locked days later in the week; an accessory due a wash comes off instead of blocking: D38, D40.)

**Tests:** constraints never violated on random wardrobes; beam result is never worse than the greedy day-by-day plan; regenerating with locked days changes only unlocked days.

## 13. Packing list (M6)

Given trip days with occasions and weather, find a small set of items that gives every day an outfit scoring 0.65 or more, with no laundry during the trip.

Greedy method: start empty; repeatedly add the item that covers the most still-uncovered days (ties go to higher versatility); stop when all days are covered; then try removing each item and keep the removal if every day is still covered. Add counted basics (socks and innerwear per day) as a plain checklist. (Built as: whole outfits added by days dressed per new piece, within each piece's wears before a wash, and each day dressed within its occasion's level when the wardrobe allows: D41.)

This is a set-cover-style problem, so greedy is a heuristic, not a guaranteed minimum. Say "a compact list", not "the smallest possible list".

## 14. Weekly digest picks (M12)

The weekly digest's picks are engine code too: trends become candidate pieces, each judged by the purchase analyzer against the person's wardrobe, and scored mostly on what they would add (`0.60 * value + 0.25 * trend fit + 0.15 * season fit`). A trend that matches something the person already owns becomes an outfit built around that piece instead of a purchase. The model only words the result. Details and tests: `docs/AGENTS.md`, section 5.

## 15. Later: a learned model (stretch)

A public dataset of human-made outfits can train a small compatibility model. Compare it with the rule engine on the golden set and on a fill-in-the-blank task, and only blend it in if it wins. Check the dataset's licence before using it. This makes a good write-up either way: rules versus learned, with numbers.
