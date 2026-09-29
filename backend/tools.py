"""Tools the Campus Customs agent can call, plus the shared database helpers.

Every tool reads the SQLite database directly and returns compact dictionaries.
Two rules shape all of them:

  * Tool results are trimmed. Full descriptions and tag lists would fill the
    model's context for no benefit, so searches return short rows and the agent
    fetches detail only for a product it actually wants to discuss.
  * Nothing here touches the `users` table. The agent has no route to an email
    address or a password hash because no tool can reach them.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from models import (
    SIZE_ORDER,
    Alternative,
    AlternativesLookup,
    CatalogueOverview,
    GarmentTypeCount,
    ProductLookup,
    SearchHit,
    SearchResults,
    SizeAvailability,
    StockLookup,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
IMAGES_DIR = DATA_DIR / "products"

# Caps, so one tool call cannot drag the whole catalogue into the context.
MAX_SEARCH_RESULTS = 8
HARD_RESULT_LIMIT = 12

_WORD = re.compile(r"[a-z0-9]+")

# Words that appear on nearly everything here, so they say almost nothing about
# which product someone means.
_STOPWORDS = {"the", "a", "an", "and", "of", "with", "for", "in", "yale", "university"}


def _tokens(text: str) -> list[str]:
    """Lowercase word tokens. 'Yale Dad T-Shirt' -> ['yale','dad','t','shirt'].

    Splitting on non-alphanumerics is what makes 't-shirt' match a stored
    't shirt': a plain substring search fails on the hyphen alone.
    """
    return _WORD.findall(text.lower())


def _searchable(product: dict[str, Any]) -> str:
    return " ".join(
        [
            product["name"],
            product["garment_type"],
            product["description"],
            " ".join(product["colors"]),
            " ".join(product["search_tags"]),
            product["product_id"].replace("-", " "),
        ]
    ).lower()


def _relevance(product: dict[str, Any], terms: list[str]) -> int:
    """How well a product matches the query terms. Higher is better."""
    if not terms:
        return 1
    name = product["name"].lower()
    tags = " ".join(product["search_tags"]).lower()
    haystack = _searchable(product)

    score = 0
    for term in terms:
        if term not in haystack:
            return 0  # every meaningful term must appear somewhere
        if term in name:
            score += 5
        elif term in tags:
            score += 2
        else:
            score += 1
    return score


# ---------------------------------------------------------------------------
# database helpers (shared with main.py)
# ---------------------------------------------------------------------------


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def parse_json_field(raw: str | None) -> list[str]:
    """`colors` and `search_tags` are JSON arrays stored as TEXT."""
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return [str(v) for v in value] if isinstance(value, list) else [str(value)]
    except json.JSONDecodeError:
        return [part.strip() for part in raw.split(",") if part.strip()]


def image_url(image_file_path: str) -> str:
    """'products/foo.jpg' -> '/images/foo.jpg'."""
    return f"/images/{Path(image_file_path).name}"


def short_description(text: str, limit: int = 140) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[:limit].rsplit(" ", 1)[0] + "…"


def row_to_product(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": row["description"],
        "short_description": short_description(row["description"]),
        "colors": parse_json_field(row["colors"]),
        "search_tags": parse_json_field(row["search_tags"]),
        "price": float(row["price"]),
        "image_url": image_url(row["image_file_path"]),
    }


def sizes_for(con: sqlite3.Connection, product_id: str) -> list[dict[str, Any]]:
    rows = con.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
    ).fetchall()
    by_size = {r["size"]: r["quantity"] for r in rows}
    ordered = [s for s in SIZE_ORDER if s in by_size]
    ordered += [s for s in by_size if s not in SIZE_ORDER]
    return [
        {"size": s, "quantity": by_size[s], "in_stock": by_size[s] > 0} for s in ordered
    ]


def size_models(raw: list[dict[str, Any]]) -> list[SizeAvailability]:
    return [SizeAvailability(**s) for s in raw]


def money(value: float) -> str:
    """'$58' rather than '$58.0'. Pre-formatted so the model never reformats."""
    return f"${value:.2f}".replace(".00", "")



# ---------------------------------------------------------------------------
# catalogue cache
#
# Every tool call used to re-read all 102 catalogue rows, and one question often
# triggers two or three calls. The catalogue is read once and reused instead.
#
# Invalidation keys on the database file's modification time, so an inventory
# or price change is picked up on the next call without a restart. A cache that
# served stale prices would defeat the point of the assistant.
# ---------------------------------------------------------------------------

_cache: dict[str, Any] = {"mtime": None, "catalogue": None, "inventory": None}


def _db_mtime() -> float:
    try:
        return DB_PATH.stat().st_mtime
    except OSError:
        return 0.0


def _refresh_cache_if_stale() -> None:
    mtime = _db_mtime()
    if _cache["mtime"] == mtime and _cache["catalogue"] is not None:
        return

    con = connect()
    try:
        catalogue = [row_to_product(r) for r in con.execute("SELECT * FROM catalogue")]
        inventory: dict[str, dict[str, int]] = {}
        for r in con.execute("SELECT product_id, size, quantity FROM inventory"):
            inventory.setdefault(r["product_id"], {})[r["size"]] = r["quantity"]
    finally:
        con.close()

    _cache.update(mtime=mtime, catalogue=catalogue, inventory=inventory)


def all_products() -> list[dict[str, Any]]:
    """Every catalogue row, from cache. Returns copies so callers cannot mutate it."""
    _refresh_cache_if_stale()
    return [dict(p) for p in _cache["catalogue"]]


def stock_for(product_id: str) -> list[dict[str, Any]]:
    """Stock by size for one product, from cache, in display order."""
    _refresh_cache_if_stale()
    by_size = _cache["inventory"].get(product_id, {})
    ordered = [s for s in SIZE_ORDER if s in by_size]
    ordered += [s for s in by_size if s not in SIZE_ORDER]
    return [{"size": s, "quantity": by_size[s], "in_stock": by_size[s] > 0} for s in ordered]


def cache_stats() -> dict[str, Any]:
    """For /api/health — proof the cache is live, not a claim in a document."""
    _refresh_cache_if_stale()
    return {
        "products_cached": len(_cache["catalogue"] or []),
        "products_with_inventory": len(_cache["inventory"] or {}),
        "keyed_on_db_mtime": _cache["mtime"],
    }


# ---------------------------------------------------------------------------
# the agent's tools
# ---------------------------------------------------------------------------


def search_products(  # noqa: PLR0913 - each filter maps to a real shopper question
    query: str = "",
    garment_type: str = "",
    color: str = "",
    max_price: float = 0.0,
    min_price: float = 0.0,
    limit: int = MAX_SEARCH_RESULTS,
) -> SearchResults:
    """Search the catalogue.

    Args:
        query: free text matched against name, description, colours and tags.
        garment_type: loose filter, e.g. "hoodie", "crewneck", "t-shirt".
        color: colour filter, e.g. "navy", "gray".
        max_price: only products at or below this price. 0 means no limit.
        min_price: only products at or above this price. 0 means no limit.
        limit: how many to return, capped at 12.

    Returns:
        SearchResults — trimmed rows, best matches first.
    """
    limit = max(1, min(int(limit or MAX_SEARCH_RESULTS), HARD_RESULT_LIMIT))

    con = connect()
    try:
        products = all_products()

        scored_by_relevance = False
        if query:
            # Token matching, not substring: "Yale Dad t-shirt" must still find
            # the product stored as "Yale Dad T Shirt".
            terms = [t for t in _tokens(query) if t not in _STOPWORDS]
            if not terms:
                terms = _tokens(query)  # the query was nothing but stopwords
            ranked = [(p, _relevance(p, terms)) for p in products]
            products = [p for p, s in sorted(ranked, key=lambda x: -x[1]) if s > 0]
            scored_by_relevance = True

        if garment_type:
            # `garment_type` is free text with 22 overlapping values, so match
            # as a substring — an exact comparison misses most hoodies.
            needle = garment_type.lower().strip()
            products = [p for p in products if needle in p["garment_type"].lower()]

        if color:
            needle = color.lower().strip()
            products = [p for p in products if any(needle in c.lower() for c in p["colors"])]

        if max_price and max_price > 0:
            products = [p for p in products if p["price"] <= max_price]
        if min_price and min_price > 0:
            products = [p for p in products if p["price"] >= min_price]

        total = len(products)
        # A text query keeps its relevance order; otherwise cheapest first.
        if not scored_by_relevance:
            products.sort(key=lambda p: p["price"])
        top = products[:limit]

        # Attach a one-line stock summary so the agent can answer "is it
        # available?" without a second call.
        for p in top:
            stock = stock_for(p["product_id"])
            p["sizes_in_stock"] = [s["size"] for s in stock if s["in_stock"]]
            # Carried through so the agent can mention gaps without a second call.
            p["sizes_out_of_stock"] = [s["size"] for s in stock if not s["in_stock"]]
    finally:
        con.close()

    filters = {k: str(v) for k, v in {
        "query": query, "garment_type": garment_type, "color": color,
        "max_price": max_price or "", "min_price": min_price or "",
    }.items() if v}

    return SearchResults(
        total_matches=total,
        showing=len(top),
        truncated=total > len(top),
        filters_applied=filters,
        products=[
            SearchHit(
                product_id=p["product_id"],
                name=p["name"],
                garment_type=p["garment_type"],
                price=p["price"],
                price_display=money(p["price"]),
                colors=p["colors"],
                sizes_in_stock=p["sizes_in_stock"],
                sizes_out_of_stock=p["sizes_out_of_stock"],
                summary=short_description(p["description"], 110),
            )
            for p in top
        ],
    )


def get_product(product_id: str) -> ProductLookup:
    """Full detail for one product: description, price, colours and stock.

    Args:
        product_id: the catalogue id, e.g. "yale-dad-t-shirt".
    """
    con = connect()
    try:
        row = con.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return ProductLookup(
                found=False,
                product_id=product_id,
                error=f"No product with the id '{product_id}'. Search for it by name instead.",
            )
        product = row_to_product(row)
        stock = sizes_for(con, product_id)
    finally:
        con.close()

    sizes = size_models(stock)
    return ProductLookup(
        found=True,
        product_id=product["product_id"],
        name=product["name"],
        garment_type=product["garment_type"],
        description=product["description"],
        colors=product["colors"],
        price=product["price"],
        price_display=money(product["price"]),
        sizes=sizes,
        sizes_in_stock=[s.size for s in sizes if s.in_stock],
        sizes_out_of_stock=[s.size for s in sizes if not s.in_stock],
        total_stock=sum(s.quantity for s in sizes),
        any_in_stock=any(s.in_stock for s in sizes),
    )


def check_availability(product_id: str, size: str = "") -> StockLookup:
    """How many are in stock, by size.

    Args:
        product_id: the catalogue id.
        size: XS, S, M, L, XL or XXL. Leave empty for every size.
    """
    con = connect()
    try:
        row = con.execute(
            "SELECT name FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return StockLookup(
                found=False,
                product_id=product_id,
                error=f"No product with the id '{product_id}'. Search for it by name instead.",
            )
        stock = sizes_for(con, product_id)
    finally:
        con.close()

    sizes = size_models(stock)
    result = StockLookup(
        found=True,
        product_id=product_id,
        name=row["name"],
        sizes=sizes,
        sizes_in_stock=[s.size for s in sizes if s.in_stock],
        sizes_out_of_stock=[s.size for s in sizes if not s.in_stock],
        total_stock=sum(s.quantity for s in sizes),
        any_in_stock=any(s.in_stock for s in sizes),
    )

    if size:
        wanted = size.strip().upper()
        result.requested_size = wanted
        match = next((s for s in sizes if s.size == wanted), None)
        if match is None:
            result.requested_size_in_stock = False
            result.requested_size_quantity = 0
            result.error = (
                f"{wanted} is not a size this shop carries. "
                f"Sizes run {', '.join(SIZE_ORDER)}."
            )
        else:
            result.requested_size_in_stock = match.in_stock
            result.requested_size_quantity = match.quantity

    return result


def list_garment_types() -> CatalogueOverview:
    """What kinds of garment the shop sells, and the overall price range."""
    con = connect()
    try:
        rows = con.execute(
            "SELECT garment_type, COUNT(*) AS n FROM catalogue "
            "GROUP BY garment_type ORDER BY n DESC"
        ).fetchall()
        lo, hi = con.execute("SELECT MIN(price), MAX(price) FROM catalogue").fetchone()
        total = con.execute("SELECT COUNT(*) FROM catalogue").fetchone()[0]
    finally:
        con.close()

    return CatalogueOverview(
        total_products=total,
        price_min=lo,
        price_max=hi,
        garment_types=[GarmentTypeCount(type=r["garment_type"], count=r["n"]) for r in rows],
    )


def find_alternatives(product_id: str, size: str, limit: int = 4) -> AlternativesLookup:
    """Similar products that ARE in stock in a size the shopper needs.

    Call this whenever you have to tell someone their size is sold out. Returns
    same-kind garments, closest in price first, filtered to ones genuinely
    available in that size — so an alternative is never a second dead end.

    Args:
        product_id: the item they wanted.
        size: the size they need, e.g. "XL".
        limit: how many to suggest, at most 6.
    """
    limit = max(1, min(int(limit or 4), 6))
    wanted = (size or "").strip().upper()

    products = all_products()
    original = next((p for p in products if p["product_id"] == product_id), None)
    if original is None:
        return AlternativesLookup(
            original_product_id=product_id,
            size=wanted,
            message="No product with that id — search for it by name first.",
        )

    original_stock = {s["size"]: s["quantity"] for s in stock_for(product_id)}
    if not wanted:
        return AlternativesLookup(
            original_product_id=product_id,
            original_name=original["name"],
            message="Ask which size they need before looking for alternatives.",
        )

    if original_stock.get(wanted, 0) > 0:
        return AlternativesLookup(
            original_product_id=product_id,
            original_name=original["name"],
            size=wanted,
            original_available_in_size=True,
            message=f"{original['name']} is in stock in {wanted} — no alternative needed.",
        )

    # Same kind of garment first: a hoodie should be replaced by a hoodie.
    kind = original["garment_type"].lower()
    kind_words = {w for w in _tokens(kind)} - _STOPWORDS

    candidates = []
    for p in products:
        if p["product_id"] == product_id:
            continue
        qty = {s["size"]: s["quantity"] for s in stock_for(p["product_id"])}.get(wanted, 0)
        if qty <= 0:
            continue  # never suggest something that is also sold out in their size
        other_words = {w for w in _tokens(p["garment_type"])} - _STOPWORDS
        overlap = len(kind_words & other_words)
        if overlap == 0:
            continue
        candidates.append((overlap, abs(p["price"] - original["price"]), qty, p))

    # Closest garment type, then closest price.
    candidates.sort(key=lambda c: (-c[0], c[1]))
    top = candidates[:limit]

    if not top:
        return AlternativesLookup(
            original_product_id=product_id,
            original_name=original["name"],
            size=wanted,
            message=(
                f"Nothing similar is in stock in {wanted} either. Offer a different "
                f"size of {original['name']}, or ask what else they might consider."
            ),
        )

    alts = []
    for _, _, qty, p in top:
        diff = round(p["price"] - original["price"], 2)
        if diff == 0:
            why = f"Same price, and {qty} left in {wanted}."
        elif diff < 0:
            why = f"{money(abs(diff))} cheaper, {qty} left in {wanted}."
        else:
            why = f"{money(diff)} more, {qty} left in {wanted}."
        alts.append(
            Alternative(
                product_id=p["product_id"],
                name=p["name"],
                garment_type=p["garment_type"],
                price=p["price"],
                price_display=money(p["price"]),
                colors=p["colors"],
                quantity_in_size=qty,
                price_difference=diff,
                why=why,
            )
        )

    return AlternativesLookup(
        original_product_id=product_id,
        original_name=original["name"],
        size=wanted,
        alternatives=alts,
    )


def products_by_ids(product_ids: list[str]) -> list[dict[str, Any]]:
    """Hydrate ids into full product rows, preserving order and dropping unknowns.

    Not an agent tool — the server calls this to turn the ids the model returned
    into product cards. Anything the model invented simply vanishes here.
    """
    if not product_ids:
        return []
    con = connect()
    try:
        found: dict[str, dict[str, Any]] = {}
        for pid in dict.fromkeys(product_ids):  # de-duplicate, keep order
            row = con.execute(
                "SELECT * FROM catalogue WHERE product_id = ?", (pid,)
            ).fetchone()
            if row is not None:
                found[pid] = row_to_product(row)
    finally:
        con.close()
    return [found[pid] for pid in dict.fromkeys(product_ids) if pid in found]
