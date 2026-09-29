"""Campus Customs — API.

Serves the product catalogue, accounts, and the shop assistant to the React
front end.

Run from the backend/ folder:
    uvicorn main:app --reload --port 8000

API docs:   http://127.0.0.1:8000/docs
Front end:  http://127.0.0.1:5173

Layout:
    main.py            this file — FastAPI app and routes
    agent.py           the PydanticAI agent
    tools.py           tools the agent calls, plus shared database helpers
    models.py          Pydantic types shared by the API and the agent
    auth.py            password hashing and session tokens
    prompts/prompt.md  the assistant's system prompt
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import auth
import tools
from agent import MODEL_NAME, PROMPT_PATH, ShopDeps, api_key, run_agent
from models import (
    SIZE_ORDER,
    ChatMessageIn,
    AuthResponse,
    CustomerContext,
    ChatRequest,
    ChatResponse,
    LoginRequest,
    ProductCard,
    ProductDetail,
    ProductList,
    PublicUser,
    RegisterRequest,
    SizeStock,
)
from tools import DB_PATH, IMAGES_DIR, connect, row_to_product

app = FastAPI(title="Campus Customs", version="0.2.0")

# The Vite dev server is a different origin, so the browser needs CORS. Open is
# fine for local coursework.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Product photos are served from the data pack rather than copied into the front
# end, so `catalogue.image_file_path` stays the single source of truth.
if IMAGES_DIR.is_dir():
    app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


# ---------------------------------------------------------------------------
# health and catalogue
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict[str, Any]:
    con = connect()
    try:
        counts = {
            t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("catalogue", "inventory", "users", "chat_messages")
        }
    finally:
        con.close()
    return {
        "ok": True,
        "database": DB_PATH.name,
        "tables": counts,
        "images_mounted": IMAGES_DIR.is_dir(),
        "cache": tools.cache_stats(),
        "agent": {
            "model": MODEL_NAME,
            "prompt_file": str(PROMPT_PATH.relative_to(PROMPT_PATH.parents[1])),
            "prompt_loaded": PROMPT_PATH.is_file(),
            # Whether a key is present — never the key itself.
            "api_key_configured": bool(api_key()),
        },
    }


@app.get("/api/products", response_model=ProductList)
def list_products(
    q: str | None = Query(default=None, description="free-text search"),
    garment_type: str | None = Query(default=None, description="loose garment filter"),
    max_price: float | None = Query(default=None),
    size: str | None = Query(default=None, description="only items in stock in this size"),
    sort: str = Query(default="name", pattern="^(name|price_asc|price_desc)$"),
) -> ProductList:
    products = tools.all_products()

    # Stock summary on every row, so the grid can show availability and filter
    # by size without the browser making 102 extra requests.
    for p in products:
        stock = tools.stock_for(p["product_id"])
        p["sizes_in_stock"] = [s["size"] for s in stock if s["in_stock"]]
        p["sizes_out_of_stock"] = [s["size"] for s in stock if not s["in_stock"]]
        p["total_stock"] = sum(s["quantity"] for s in stock)

    if q:
        needle = q.lower().strip()
        products = [
            p for p in products
            if needle in p["name"].lower()
            or needle in p["description"].lower()
            or needle in p["garment_type"].lower()
            or any(needle in c.lower() for c in p["colors"])
            or any(needle in t.lower() for t in p["search_tags"])
        ]

    if garment_type:
        needle = garment_type.lower().strip()
        products = [p for p in products if needle in p["garment_type"].lower()]

    if max_price is not None:
        products = [p for p in products if p["price"] <= max_price]

    if size:
        wanted = size.strip().upper()
        products = [p for p in products if wanted in p["sizes_in_stock"]]

    if sort == "price_asc":
        products.sort(key=lambda p: p["price"])
    elif sort == "price_desc":
        products.sort(key=lambda p: -p["price"])
    else:
        products.sort(key=lambda p: p["name"].lower())

    return ProductList(count=len(products), products=products)


@app.get("/api/garment-types")
def garment_types() -> dict[str, list[str]]:
    con = connect()
    try:
        rows = con.execute(
            "SELECT DISTINCT garment_type FROM catalogue ORDER BY garment_type"
        ).fetchall()
    finally:
        con.close()
    return {"garment_types": [r[0] for r in rows]}


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: str) -> ProductDetail:
    con = connect()
    try:
        row = con.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(404, f"No product with id '{product_id}'")
        stock = con.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()
    finally:
        con.close()

    by_size = {r["size"]: r["quantity"] for r in stock}
    ordered = [s for s in SIZE_ORDER if s in by_size]
    ordered += [s for s in by_size if s not in SIZE_ORDER]
    sizes = [
        SizeStock(size=s, quantity=by_size[s], in_stock=by_size[s] > 0) for s in ordered
    ]

    return ProductDetail(
        **row_to_product(row),
        sizes=sizes,
        total_stock=sum(s.quantity for s in sizes),
    )


# ---------------------------------------------------------------------------
# authentication
# ---------------------------------------------------------------------------

# Deliberately identical for "no such email" and "wrong password", so the API
# cannot be used to discover which addresses have accounts.
BAD_CREDENTIALS = "Invalid email or password."

# How many stored turns to replay when a signed-in shopper returns.
STORED_HISTORY_TURNS = 12


def public_user(row: sqlite3.Row) -> PublicUser:
    """Map a users row to the safe subset. Never touches password_hash."""
    return PublicUser(
        id=row["id"],
        name=row["name"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        email=row["email"],
        created_at=row["created_at"],
    )


def current_user(authorization: str | None = Header(default=None)) -> sqlite3.Row:
    """Resolve the bearer token to a user, or 401."""
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    user_id = auth.read_token(token)
    if user_id is None:
        raise HTTPException(401, "Not signed in.")

    con = connect()
    try:
        row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        con.close()
    if row is None:
        raise HTTPException(401, "Not signed in.")
    return row


def optional_user(authorization: str | None = Header(default=None)) -> sqlite3.Row | None:
    """Like current_user, but returns None instead of 401.

    The chat works for signed-out visitors; being signed in just means the
    conversation gets saved.
    """
    try:
        return current_user(authorization)
    except HTTPException:
        return None


@app.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(body: RegisterRequest) -> AuthResponse:
    email = auth.normalise_email(body.email)
    if not auth.email_looks_valid(email):
        raise HTTPException(400, "That does not look like a valid email address.")

    problem = auth.password_problem(body.password)
    if problem:
        raise HTTPException(400, problem)

    first = body.first_name.strip()
    last = body.last_name.strip()
    if not first or not last:
        raise HTTPException(400, "Please give both a first and last name.")

    con = connect()
    try:
        if con.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone():
            raise HTTPException(409, "An account with that email already exists.")

        # Hashed here; the plaintext is never written anywhere.
        cur = con.execute(
            """INSERT INTO users (name, email, password_hash, first_name, last_name)
               VALUES (?, ?, ?, ?, ?)""",
            (f"{first} {last}", email, auth.hash_password(body.password), first, last),
        )
        con.commit()
        row = con.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        con.close()

    return AuthResponse(token=auth.create_token(row["id"]), user=public_user(row))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(body: LoginRequest) -> AuthResponse:
    email = auth.normalise_email(body.email)

    con = connect()
    try:
        row = con.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()
    finally:
        con.close()

    if row is None:
        # Same cost as a real check, so timing does not reveal the account.
        auth.waste_time_like_a_real_check()
        raise HTTPException(401, BAD_CREDENTIALS)

    if not auth.verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, BAD_CREDENTIALS)

    return AuthResponse(token=auth.create_token(row["id"]), user=public_user(row))


@app.get("/api/auth/me", response_model=PublicUser)
def me(user: sqlite3.Row = Depends(current_user)) -> PublicUser:
    return public_user(user)


# ---------------------------------------------------------------------------
# the shop assistant
# ---------------------------------------------------------------------------


def to_card(product: dict[str, Any]) -> ProductCard:
    return ProductCard(
        product_id=product["product_id"],
        name=product["name"],
        garment_type=product["garment_type"],
        price=product["price"],
        image_url=product["image_url"],
        short_description=product["short_description"],
    )


def stored_history(user_id: int, limit: int) -> list[ChatMessageIn]:
    """The most recent stored turns for one shopper, oldest first.

    Scoped by user_id — one shopper can never be handed another's conversation.
    """
    con = connect()
    try:
        rows = con.execute(
            """SELECT role, content FROM chat_messages
               WHERE user_id = ? ORDER BY id DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    finally:
        con.close()
    return [
        ChatMessageIn(role=r["role"], content=r["content"])
        for r in reversed(rows)
        if r["role"] in ("user", "assistant")
    ]


def save_exchange(
    user_id: int, message: str, reply: str, cards: list[ProductCard]
) -> bool:
    """Write the turn to chat_messages. Failing to save must not break the chat."""
    try:
        con = connect()
        try:
            con.execute(
                "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?,?,?,?)",
                (user_id, "user", message, None),
            )
            con.execute(
                "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?,?,?,?)",
                (
                    user_id,
                    "assistant",
                    reply,
                    json.dumps([c.model_dump() for c in cards]) if cards else None,
                ),
            )
            con.commit()
        finally:
            con.close()
        return True
    except sqlite3.Error as exc:
        print(f"[chat] could not save conversation: {exc}")
        return False


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: sqlite3.Row | None = Depends(optional_user),
) -> ChatResponse:
    """One turn of conversation with the shop assistant.

    Signed-in shoppers get their conversation saved to `chat_messages` and
    replayed on their next visit. Guests can chat freely; nothing is stored.
    """
    # Who is chatting. Deliberately narrow — name, email, id. Never the hash.
    customer = None
    if user is not None:
        customer = CustomerContext(
            user_id=user["id"],
            name=user["name"],
            first_name=user["first_name"],
            email=user["email"],
        )

    deps = ShopDeps(customer=customer, page=body.page)

    # A returning shopper's memory comes from the database, not the browser, so
    # it survives a new device or a cleared tab.
    history: list = list(body.history)
    if user is not None and not history:
        history = stored_history(user["id"], STORED_HISTORY_TURNS)

    result = await run_agent(body.message, history, deps=deps)

    # The agent returns product *ids*; the cards are built here from the
    # catalogue, so an invented id is dropped rather than shown to a shopper.
    cards = [to_card(p) for p in tools.products_by_ids(result.product_ids)]

    saved = False
    if user is not None:
        saved = save_exchange(user["id"], body.message, result.reply, cards)

    return ChatResponse(
        reply=result.reply,
        products=cards,
        result_summary=result.result_summary,
        # Never claim to show products that did not survive the id lookup.
        show_on_page=bool(result.show_on_page and cards),
        tools_used=result.tools_used,
        saved=saved,
        error=result.error,
    )


@app.get("/api/chat/history")
def chat_history(user: sqlite3.Row = Depends(current_user)) -> dict[str, Any]:
    """This user's stored conversation. Scoped by user_id — never anyone else's."""
    con = connect()
    try:
        rows = con.execute(
            """SELECT role, content, products_json, created_at
               FROM chat_messages WHERE user_id = ? ORDER BY id""",
            (user["id"],),
        ).fetchall()
    finally:
        con.close()

    messages = []
    for r in rows:
        products = []
        if r["products_json"]:
            try:
                products = json.loads(r["products_json"])
            except json.JSONDecodeError:
                products = []
        messages.append(
            {
                "role": r["role"],
                "content": r["content"],
                "products": products,
                "created_at": r["created_at"],
            }
        )
    return {"count": len(messages), "messages": messages}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
