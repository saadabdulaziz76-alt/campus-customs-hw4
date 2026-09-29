"""Structured types for Campus Customs.

Everything the API returns or the agent produces is defined here, so the shape
of the data lives in one place and both FastAPI and PydanticAI validate against
the same models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Sizes in display order; the inventory table stores them unordered.
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]


# ---------------------------------------------------------------------------
# catalogue
# ---------------------------------------------------------------------------


class Product(BaseModel):
    """One catalogue row, as the website consumes it."""

    product_id: str
    name: str
    garment_type: str
    description: str
    short_description: str
    colors: list[str] = Field(default_factory=list)
    search_tags: list[str] = Field(default_factory=list)
    price: float
    image_url: str
    # Stock summary, so the grid can show availability without opening each item.
    sizes_in_stock: list[str] = Field(default_factory=list)
    sizes_out_of_stock: list[str] = Field(default_factory=list)
    total_stock: int = 0


class SizeStock(BaseModel):
    size: str
    quantity: int
    in_stock: bool


class ProductDetail(Product):
    sizes: list[SizeStock] = Field(default_factory=list)
    total_stock: int = 0


class ProductList(BaseModel):
    count: int
    products: list[Product]


# ---------------------------------------------------------------------------
# accounts
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class PublicUser(BaseModel):
    """Everything the front end may see about a user.

    Note what is missing: there is no `password_hash` field, so a hash cannot
    leak through this model even by mistake.
    """

    id: int
    name: str
    first_name: str | None = None
    last_name: str | None = None
    email: str
    created_at: str | None = None


class AuthResponse(BaseModel):
    token: str
    user: PublicUser


# ---------------------------------------------------------------------------
# what the agent's tools return
#
# Every tool returns one of these rather than a loose dict, so the shape of a
# lookup is enforced in one place and the model always receives the same fields
# in the same names.
# ---------------------------------------------------------------------------


class SizeAvailability(BaseModel):
    """Stock for one size of one product."""

    size: str
    quantity: int = Field(description="Units on hand right now.")
    in_stock: bool = Field(description="True when quantity > 0. Precomputed so it is never inferred.")


class ProductLookup(BaseModel):
    """Everything known about one product: description, price, colours."""

    found: bool
    product_id: str
    name: str = ""
    garment_type: str = ""
    description: str = Field(default="", description="The full catalogue description, not truncated.")
    colors: list[str] = Field(default_factory=list)
    price: float = 0.0
    price_display: str = Field(default="", description="Pre-formatted, e.g. '$58'. Quote this rather than reformatting.")
    sizes: list[SizeAvailability] = Field(default_factory=list)
    sizes_in_stock: list[str] = Field(default_factory=list)
    sizes_out_of_stock: list[str] = Field(default_factory=list)
    total_stock: int = 0
    any_in_stock: bool = False
    error: str | None = Field(default=None, description="Set when found is false. Say this; do not guess around it.")


class StockLookup(BaseModel):
    """Stock for a product, optionally narrowed to one size."""

    found: bool
    product_id: str
    name: str = ""
    requested_size: str | None = Field(default=None, description="The size asked about, if any.")
    requested_size_in_stock: bool | None = Field(
        default=None, description="Availability of the requested size. None when no size was asked about."
    )
    requested_size_quantity: int | None = None
    sizes: list[SizeAvailability] = Field(default_factory=list)
    sizes_in_stock: list[str] = Field(default_factory=list)
    sizes_out_of_stock: list[str] = Field(
        default_factory=list,
        description="Sizes at zero. Tell the shopper about these — do not quietly omit them.",
    )
    total_stock: int = 0
    any_in_stock: bool = False
    error: str | None = None


class SearchHit(BaseModel):
    """One product in a search result — trimmed, for context economy."""

    product_id: str
    name: str
    garment_type: str
    price: float
    price_display: str
    colors: list[str] = Field(default_factory=list)
    sizes_in_stock: list[str] = Field(default_factory=list)
    sizes_out_of_stock: list[str] = Field(default_factory=list)
    summary: str = Field(description="A shortened description. Call get_product for the full text.")


class SearchResults(BaseModel):
    """What a catalogue search returned."""

    total_matches: int
    showing: int
    truncated: bool = Field(description="True when more matched than are shown. Say so rather than implying these are all.")
    filters_applied: dict[str, str] = Field(default_factory=dict)
    products: list[SearchHit] = Field(default_factory=list)


class Alternative(BaseModel):
    """A substitute that is genuinely available in the size the shopper wants."""

    product_id: str
    name: str
    garment_type: str
    price: float
    price_display: str
    colors: list[str] = Field(default_factory=list)
    quantity_in_size: int = Field(description="Units left in the requested size. Always > 0.")
    price_difference: float = Field(description="Versus the original: negative is cheaper.")
    why: str = Field(description="One line on how it compares to the item they wanted.")


class AlternativesLookup(BaseModel):
    """Substitutes for an item that is unavailable in the shopper's size."""

    original_product_id: str
    original_name: str = ""
    size: str = ""
    original_available_in_size: bool = Field(
        default=False,
        description="True when the original IS in stock in that size — then no substitute is needed.",
    )
    alternatives: list[Alternative] = Field(default_factory=list)
    message: str = Field(default="", description="What to tell the shopper if nothing suitable exists.")


class GarmentTypeCount(BaseModel):
    type: str
    count: int


class CatalogueOverview(BaseModel):
    """A broad orientation to what the shop sells."""

    total_products: int
    price_min: float
    price_max: float
    garment_types: list[GarmentTypeCount] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# the agent
# ---------------------------------------------------------------------------


class ProductCard(BaseModel):
    """The compact product shape the chat widget renders beside a reply."""

    product_id: str
    name: str
    garment_type: str
    price: float
    image_url: str
    short_description: str = ""


class AgentReply(BaseModel):
    """What the model is asked to return.

    The agent names products by **id only**. The server then looks each id up in
    the catalogue and builds the cards, so a product that does not exist cannot
    reach the shopper — if the model invents an id, it is simply dropped.
    """

    reply: str = Field(description="The message to show the shopper, in Campus Customs' voice.")
    product_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Product ids to show as cards. Use only ids returned by a tool in "
            "this conversation. Leave empty when recommending nothing."
        ),
    )
    result_summary: str = Field(
        default="",
        description=(
            "A short label for what this set of products is, shown as a heading "
            "above them on the page — e.g. 'Hoodies under $70' or 'Davenport "
            "College'. Three to six words. Leave empty when returning no products."
        ),
    )
    show_on_page: bool = Field(
        default=True,
        description=(
            "True when these products should fill the shop page as a browsable "
            "set — the normal case for 'what do you have in X?'. False when they "
            "are only incidental to the answer, such as a single item mentioned "
            "while answering a question about sizing."
        ),
    )


class ChatMessageIn(BaseModel):
    """One earlier turn, replayed to give the agent context."""

    role: Literal["user", "assistant"]
    content: str


class PageContext(BaseModel):
    """Where the shopper is on the site when they send a message.

    This is what lets "do you have this in pink?" resolve to an actual product:
    the front end reports which page is open, and the agent is told what is on
    screen before it reads the question.
    """

    path: str = Field(default="", description="The route, e.g. '/products/yale-dad-t-shirt'.")
    product_id: str | None = Field(
        default=None,
        description="Set when a single-product page is open — the item 'this' refers to.",
    )


class CustomerContext(BaseModel):
    """Who the agent is talking to. Absent for guests.

    Deliberately narrow: a name, an email and an id. No password hash, no
    address, no order history — the agent is given only what it needs to be
    personal, and nothing that would be damaging to leak.
    """

    user_id: int
    name: str
    first_name: str | None = None
    email: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessageIn] = Field(
        default_factory=list,
        description="Recent turns from this browser session, oldest first.",
    )
    page: PageContext | None = Field(
        default=None,
        description="What the shopper is looking at right now.",
    )


class ChatResponse(BaseModel):
    """The chat API contract.

    `products` is the structured half: fully hydrated cards the front end
    renders on the page. `reply` is the conversational half. The two travel
    together so the page and the conversation can never disagree.
    """

    reply: str
    products: list[ProductCard] = Field(
        default_factory=list,
        description="Matching products, already looked up in the catalogue. Safe to render directly.",
    )
    result_summary: str = Field(
        default="",
        description="Heading for the product set on the page, e.g. 'Hoodies under $70'.",
    )
    show_on_page: bool = Field(
        default=False,
        description="True when the front end should surface these products on the shop page.",
    )
    tools_used: list[str] = Field(default_factory=list)
    saved: bool = Field(
        default=False,
        description="True when the exchange was written to chat_messages (signed-in users only).",
    )
    error: str | None = None
