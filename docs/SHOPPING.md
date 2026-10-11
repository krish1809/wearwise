# Smart Shopping

Two parts. Part 1 is the purchase analyzer and everything built on it (M8). It needs no external data and is WearWise's main differentiator. Part 2 is finding real products (M9).

## Part 1. Deciding what is worth buying

### 1.1 The idea

A candidate item is treated as if it were already in the wardrobe. The engine runs before and after, and the difference is what the item adds.

A raw match count is misleading. A fifth white T-shirt "matches" everything and adds nothing. So the analyzer measures **new, distinct outfits for occasions where you are short**, and subtracts for duplication.

### 1.2 Measures

All of these reuse the engine in `ENGINE.md`.

**Matches.** Owned items with pair score `P >= 0.65` against the candidate, grouped by slot. Shown as photos: "goes with these 7 things you own".

**Distinct new outfits.** Good outfits (`Score >= 0.7`) in wardrobe-plus-candidate that contain the candidate, after the diversity step.

**Coverage gain.** For each occasion and season the user cares about, count distinct good outfits before and after, and apply diminishing returns:

```
value(n)      = log2(1 + min(n, 10))
coverage_gain = sum over (occasion, season) of  value(after) - value(before)
```

Going from 0 to 2 outfits for "office, summer" is worth far more than going from 9 to 11 for "college".

**Redundancy.** The highest similarity between the candidate and any owned item in the same slot:

```
similarity = 0.35*same category + 0.35*colour closeness + 0.15*same pattern + 0.15*formality closeness
```

At 0.8 or above, name the owned item: "very close to your navy chinos".

**Orphans rescued.** Owned orphans (versatility below 2) that would have versatility of 2 or more with the candidate.

**Cost per new outfit.** Price divided by distinct new outfits. Shown only when the price is known.

**Projected cost per wear.** Price divided by expected wears, where expected wears come from how often the user wears similar items. Always labelled as an estimate, and hidden if there is too little history.

### 1.3 Verdict

| Verdict | Rule (starting values) |
|---|---|
| Skip | Redundancy 0.8 or more, or fewer than 2 distinct new outfits |
| Buy | Coverage gain in the top third of what archetypes achieve for this wardrobe, redundancy below 0.6, and price within the category budget |
| Consider | Everything else |

Every verdict shows its reasons and the numbers behind it. The user can always override.

### 1.4 Gap analysis

`seed/archetypes.json` is a list of common wardrobe staples ("white casual shirt", "navy chinos", "white minimal sneakers") with full attributes and no prices.

Gap analysis runs the analyzer on every archetype that fits the user's sections and isn't already redundant, and ranks by coverage gain. The top results are the "buy next" list, each with its reason: "navy chinos would add 9 outfits, 5 of them for office".

An empty category is not a gap by itself. A gap is an occasion and season with too few outfits, and the fix is whichever item raises it most.

### 1.5 Starter capsule

For a small wardrobe: pick archetypes one at a time, each time taking the one with the largest coverage gain given everything picked so far, until the budget or item limit is reached. Present it in stages (first three purchases, next three) so it reads as a plan, not a shopping spree. Costs use the user's own typical spend per category from onboarding.

### 1.6 Budget split

"I have ₹3,000. Which of these should I buy?" Given candidates with prices and a budget, choose the subset with the largest combined coverage gain.

- Evaluate subsets jointly, because items interact: a new shirt and new trousers create outfits together that neither creates alone.
- With 12 or fewer candidates, check every affordable subset.
- With more, use greedy by gain per rupee, then compare with the best single item and keep the better.
- Because of those interactions the objective isn't submodular, so greedy has no guarantee here. Tests compare greedy with exhaustive search on small cases and report the gap.

### 1.7 Tests that must exist

- A candidate identical to an owned item gets Skip, and the duplicate is named.
- A candidate that opens an empty occasion outranks one that adds to a full occasion.
- Adding a candidate never lowers coverage.
- The budget split never exceeds the budget.
- Analysis is recomputed when `wardrobe_version` changes.

---

## Part 2. Finding real products

### 2.1 Decision: no bulk scraping

The original idea was to scrape shopping sites for the cheapest matching products. The plan here does not build on that, for three reasons:

1. **It breaks.** Large retailers render with JavaScript and run bot detection. A scraper that works this week fails next week, and a deployed app can't depend on it.
2. **It is usually not allowed.** Retailers' terms of use and robots.txt commonly restrict automated collection. Read them for any site before touching it. Getting around a login, CAPTCHA, or bot check is off the table.
3. **It isn't the interesting part.** The value is in ranking products against a wardrobe. A clean adapter design with honest sources shows that off better than a fragile scraper.

So product discovery is a set of adapters behind one interface, starting with sources that always work.

### 2.2 Sources, in build order

| # | Adapter | What it does | Status |
|---|---|---|---|
| 1 | Search links | Turns a gap into a search query and opens Myntra, Ajio, Flipkart, Amazon with keywords and a price cap. The user browses there. | Always works. Build first. |
| 2 | Pasted link | The user pastes one product URL. The server fetches that page once and reads its public preview metadata (Open Graph, schema.org product data), then the user confirms or fills in the rest. | Works where the site allows it; falls back to manual entry. Respect robots.txt. |
| 3 | Screenshot | The user uploads a product screenshot; the vision model (M10) proposes attributes. | Needs the AI layer. |
| 4 | Demo catalogue | A few thousand products from an open fashion dataset, loaded into `catalog_products` with `is_demo = true`. Lets ranking, filters, and cards be built and demonstrated. | Check the dataset's licence. Never present its prices as current. |
| 5 | Affiliate or product API | Live products with prices from an official programme. | Only if access is approved. |

After adapter 1 and 2 the feature is honest and useful. Adapter 4 makes the demo look complete. Adapter 5 is a bonus.

### 2.3 What is known about official sources

Checked in October 2026. Re-check before building, because programmes change.

- **Amazon.** The Product Advertising API is being replaced by the Creators API. Access requires an Amazon Associates account with at least 10 qualifying sales in the past 30 days. That rules it out for a new project.
- **Flipkart.** An Affiliate API exists with product feeds and keyword search, authenticated with an affiliate ID and token. Whether new affiliate registrations are currently accepted was not confirmed. Check the affiliate site directly.
- **Myntra and Ajio.** No public product API was found. Affiliate networks that carry Indian retailers sometimes offer product feeds or an API to approved publishers; that was not verified for any specific network.
- **Affiliate links make the app commercial.** That affects hosting terms (Vercel's free plan and Open-Meteo's free tier are both non-commercial) and means affiliate relationships must be disclosed on the site.

### 2.4 Adapter interface

```python
class ProductSource(Protocol):
    name: str
    is_live: bool                      # False for demo data

    def search(self, query: ProductQuery) -> list[ProductResult]: ...
    def fetch(self, url: str) -> ProductResult | None: ...
```

`ProductQuery`: category, colour family, fabric, section, size, max price, free-text keywords.

`ProductResult`: source name, external ID, title, brand, URL, image URL, price and currency (optional), attributes (optional), `fetched_at`, `is_demo`.

Rules for every adapter:

- A timeout of a few seconds, one retry at most, and a clean empty result on failure.
- Cache results; never refetch the same thing within its freshness window.
- Missing fields stay missing. No guessed prices, sizes, stock, or ratings.
- Every card shows the source and when the data was fetched. Prices older than a day are marked "may have changed".
- Text from product pages is untrusted input. It is never passed to the AI as instructions.

### 2.5 Ranking real products

1. Take a gap (an archetype) and build a `ProductQuery` from it, plus the user's size and budget.
2. Ask each enabled adapter.
3. Map each result onto item attributes (from structured data where present, otherwise from the query).
4. Run the purchase analyzer on each.
5. Rank by coverage gain per rupee, with redundancy as a penalty.
6. Show the top results with their reasons, a "why this one" line, and a link out to the retailer.

### 2.6 Size and fit

- Show the user's usual size and any brand note beside each product.
- If the user pastes a size chart, compare it with their measurements and say which size is closest and where it differs.
- Never state that something will fit. Say "closest to your measurements" and show the differences.
