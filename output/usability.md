# Campus Customs — Usability Improvements

Four improvements, chosen because each fixes something I actually ran into while
building the shop rather than because it was easy to add.

Two shape the website; two shape the assistant.

| # | Where | Improvement |
|---|---|---|
| 1 | Front end | Filter by size, and show stock status on every card |
| 2 | Front end | Filters live in the URL, so views are shareable and Back works |
| 3 | Agent | `find_alternatives` — never leave a shopper at a dead end |
| 4 | Backend | Catalogue cache, so tool calls stop re-reading the database |

---

## 1 · Front end — Filter by size, and show stock on the card

### What I added

- A **size filter** on the Products page: XS through XXL. Choosing one shows
  only garments actually available in that size.
- A **stock badge on every product card**, in three states:
  - *nothing* — fully stocked, no noise
  - **"Some sizes sold out"** — amber, when at least one size is unavailable
  - **"Low stock"** — when fewer than 10 units remain across all sizes
- When a size filter is active, each card also shows how many are left in
  **that** size ("4 left in M").

### Why it helps

**The database made this necessary.** 145 of the 612 size rows are at zero —
roughly a quarter of all size options are sold out. Before this change, the only
way to discover that was to open a product, scroll to the size picker, and find
your size struck through. On a 102-product catalogue, a shopper who wears XS
could open a dozen items before finding one they can buy.

For the business this is the difference between a browsing session and an
abandoned one. Surfacing availability at the grid level means a shopper filters
once and everything they see afterwards is something they can actually order,
and the "Low stock" badge does honest work on the items most likely to sell out.

---

## 2 · Front end — Filters live in the URL

### What I added

Search text, category, sort order and the new size filter are written to the
URL as query parameters (`/products?q=davenport&size=M&sort=price_asc`), and read
back out on load. The browser's Back and Forward buttons move through filter
states, and a filtered view can be copied and shared.

### Why it helps

Three concrete failures this fixes:

1. **Opening a product and pressing Back lost the search.** A shopper who
   searched "davenport", opened a crewneck, and came back to the grid landed on
   the unfiltered catalogue and had to start over. Now they return to exactly
   what they were looking at.
2. **A filtered view could not be shared.** "Look at these" meant describing the
   filters. Now it is a link — useful for a parent and a student deciding
   together, which is a real Campus Customs shopping pattern.
3. **Reloading the page reset everything.**

None of this is visible as a feature; it is visible as the site no longer losing
your place. That is usually what usability means.

---

## 3 · Agent — `find_alternatives`, so nobody hits a dead end

### What I added

A new tool. Given a product and a size, it returns similar items — same garment
type, close in price — that are **genuinely in stock in that size**, ranked by
how close they are to the original.

The prompt now requires it: when the agent has to tell a shopper their size is
sold out, it must call `find_alternatives` and offer what *is* available in the
same reply.

### Why it helps

Before this, the honest answer was also a useless one:

> "The Champion Reverse Weave Hoodie is not available in XL."

Correct, and the conversation ends there. Now:

> "That one's sold out in XL, but the Basic Hoodie Big Yale is the same weight
> and price and has XL in stock."

For the shopper it is the difference between being told no and being helped. For
the business it is a recovered sale rather than a lost one — and because the
alternatives are filtered on real inventory for that specific size, it never
sends anyone toward a second dead end.

This is an accuracy improvement as much as a usability one: without a tool for
it, an agent asked for alternatives would be tempted to guess at similar
products from memory.

---

## 4 · Backend — Catalogue cache

### What I added

The catalogue is read into memory once and reused, with the cache invalidated
automatically when the database file changes on disk (checked by modification
time). Inventory is cached the same way.

Before, **every tool call re-read all 102 catalogue rows from SQLite**, and a
single question often triggers two or three tool calls.

### Why it helps

The assistant feels quicker, and the shop does less work per conversation. The
measured effect is recorded below.

It also matters for cost in a subtler way: a faster tool means a shorter
round-trip inside the agent's loop, so a multi-tool answer resolves sooner and
the shopper is less likely to give up on the panel and leave.

The invalidation is the part worth getting right — a cache that serves stale
prices or stale stock would be a *downgrade*, since the whole point of the
assistant is that it does not invent numbers. Keying on the file's modification
time means an inventory update is picked up on the next call without a restart.

---

---

# Verification — all four, in the running app

Every improvement was checked in the running site or against the live API, not
just built.

## 1 · Size filter and stock badges

| Check | Result |
|---|---|
| `GET /api/products?size=XS` | **75 of 102** products returned |
| `GET /api/products?size=XL` | **77 of 102** |
| Size chips on the Products page | XS · S · M · L · XL · XXL, plus "Any" |
| Note when a size is active | "Showing only items you can actually buy in XL" |
| Badges on cards | "1 size sold out" appearing on affected items |
| Per-size label when filtering | "XL in stock" on every card in the filtered grid |

Screenshot: `output/screenshots/13-size-filter-and-stock-badges.jpg`

## 2 · Filters in the URL

| Check | Result |
|---|---|
| Opening a shared link `/products?q=hoodie&size=XL&sort=price_desc` directly | Search box shows "hoodie", sort shows "Price, high to low", XL chip active, **21 items** |
| Open a product, then press **Back** | Returned to `/products?q=hoodie&size=XL&sort=price_desc` with all filters intact and the same 21 items |
| Default values | Dropped from the URL, so a clean view stays a clean `/products` |

The Back-button case is the one that mattered: before this change, opening a
product and returning dumped the shopper on the unfiltered catalogue.

## 3 · `find_alternatives`

Asked the live agent: *"I want the Champion Reverse Weave Hoodie in XL"* — a
size that is genuinely at zero.

**Tools called:** `search_products`, `check_availability`, **`find_alternatives`**

> "The Champion Reverse Weave Hoodie is sold out in XL. It's available in S, M,
> L and XXL at **$68**; these same-price hoodies are in stock in XL, including
> the Crew Left Chest Hoodie and Basic Hoodie Big Yale."

Five product cards came back with it, so the shopper can click straight through
to something they can buy. Every suggestion was checked against the database:
all are hoodies, all $68, all with XL genuinely in stock.

Edge cases verified: asking for a size that **is** available returns
`original_available_in_size: true` and no alternatives ("no alternative
needed"); an unknown product id returns a clear message rather than guesses;
and when nothing similar exists in that size, it says so instead of suggesting a
second dead end.

## 4 · Catalogue cache

Measured over 40 tool calls each way:

| | Per tool call |
|---|---|
| Before — read every row from SQLite each time | **0.90 ms** |
| After — cached | **0.24 ms** |
| **Speedup** | **3.8×** |

**Invalidation was tested directly**, because a cache serving stale prices would
be worse than no cache. Changing a price in the database while the server was
running:

```
price 32.0  →  changed in db to 33.0  →  tool reported 33.0  →  restored to 32.0
stale price served: NO — cache invalidated correctly
```

The cache is visible on `GET /api/health`:

```json
"cache": { "products_cached": 102, "products_with_inventory": 102,
           "keyed_on_db_mtime": 1790701606.5 }
```

## Build checks

`tsc -b` and `oxlint` both pass with zero warnings after all four changes.
