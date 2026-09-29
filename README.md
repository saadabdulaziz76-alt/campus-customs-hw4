# Campus Customs

A Yale apparel storefront with a shop assistant that answers from the real
catalogue. Built for Homework 4.

The assistant does not guess. Every price, size and stock figure it states comes
from a tool call against the shop's database, and it names products by id only —
the server turns those ids into cards, so a product the model invents is dropped
before a shopper ever sees it.

**React 19 · Vite · TypeScript** on the front, **FastAPI · PydanticAI · SQLite**
behind.

---

## Before you start: add the data pack

**The database and the product photos are not in this repository.** They are
course-supplied and deliberately excluded by `.gitignore`.

Put the `data/` folder in the project root, next to this README:

```
hw4/
├── data/                        <-- add this
│   ├── campus_customs.db
│   └── products/                # 102 product images
├── backend/
├── frontend/
└── README.md
```

The backend reads `data/campus_customs.db` and serves the photos from
`data/products/`. Without the pack the site loads but the catalogue is empty.

---

## Setup

You need **Python 3.11+** and **Node 18+**.

### 1 · Environment variables

```bash
cp .env.example .env
```

Then open `.env` and add your Portkey key:

```
PORTKEY_API_KEY=your-key-here
```

The catalogue, product pages, search, filters and accounts all work without a
key — only the chat assistant needs it, and it degrades politely if the key is
missing rather than erroring.

### 2 · Backend

From the project root:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r requirements.txt
```

### 3 · Front end

```bash
cd frontend
npm install
```

---

## Running it

Two terminals. **Start the backend first** — the front end renders without it,
but the catalogue and chat stay empty until the API answers.

**Terminal 1 — backend**, from `backend/`:

```bash
uvicorn main:app --reload --port 8000
```

**Terminal 2 — front end**, from `frontend/`:

```bash
npm run dev
```

Then open **http://localhost:5173**.

The API runs on **http://127.0.0.1:8000**. They are different origins, so the
API sends open CORS headers; `frontend/src/api.ts` holds the single `API_BASE`
constant the front end uses.

### Check it is wired up

```bash
curl http://127.0.0.1:8000/api/health
```

Reports row counts for all four tables, the model name, whether the prompt file
loaded and whether a key is configured — never the key itself.

### A test account

The seeded database includes one:

```
test@campuscustoms.yale.edu  /  password
```

---

## What to try

- **Browse** the catalogue, filter by size, open a product.
- **Ask the assistant a stock question** — "Do you have the Baseball Left Chest
  Crewneck in XL?" It will tell you it is sold out in XL and offer something you
  can actually buy in that size.
- **Ask a category question** — "What hoodies do you have?" The shop page fills
  with matching cards behind the conversation.
- **Sign in, chat, then reload.** A signed-in shopper's conversation is restored;
  a guest's is not.
- Wait a moment on any page and **Handsome Dan** walks past. There is a switch in
  the footer.

---

## Layout

```
hw4/
├── AI_prompts.md              every prompt used to build this, in order
├── requirements.txt           Python dependencies
├── .env.example               environment template — placeholders only
├── .gitignore
├── README.md
├── frontend/                  Vite + React + TypeScript
└── backend/
    ├── main.py                FastAPI app — run with: uvicorn main:app --reload
    ├── agent.py               agent wiring, loop limits, run_agent()
    ├── models.py              every Pydantic type
    ├── tools.py               the six tools and the database helpers
    ├── auth.py                password hashing and session tokens
    ├── audit.py               the append-only audit trail
    └── prompts/
        └── prompt.md          system prompt — voice, tools, honesty, safety
└── output/
    ├── harness.md             how the whole system works
    ├── design.md              the visual design and why
    ├── usability.md           four usability improvements
    ├── app_check.html         live site check — open by double-clicking
    ├── app_check_images/      screenshots linked from app_check.html
    └── audit_trail.json       append-only log of agent-loop activity
```

**`auth.py` and `audit.py`** are not in the assignment's sketch of the layout
because they came from later problems — accounts in Problem 4 and the audit
trail in Problem 12. Both are required for the app to run.

---

## How it works

Full detail is in [`output/harness.md`](output/harness.md). The short version:

**One chat turn**

```
ChatPanel ──POST /api/chat──▶ main.py
                                run_agent()              agent.py
                                  → tools call SQLite    tools.py
                                  → { product_ids, result_summary, show_on_page }
                                products_by_ids()        ids become real cards
                              ◀── { reply, products[], tools_used[], saved }
                                       │
                          ┌────────────┴────────────┐
                    chat renders reply        page fills with cards
```

**The boundary that keeps it honest.** The agent returns ids; the server
hydrates them from the database. Prices and images always come from SQLite, never
from the model's text, and an unknown id is simply dropped.

**Six tools, all read-only:** `search_products`, `get_product`,
`check_availability`, `find_alternatives`, `list_garment_types`,
`current_product`. None of them can reach the `users` table, so email addresses
and password hashes are unreachable rather than merely forbidden.

**Loop limits:** 6 model requests and 10 tool calls per run, enforced with
PydanticAI's `UsageLimits`. Hitting one ends the run with a polite fallback and
records `stop_reason: "usage_limit_exceeded"` in the audit trail.

**Passwords** are stored as PBKDF2-HMAC-SHA256 with a per-user salt at 600,000
iterations, compared in constant time. The API's user model has no hash field, so
one cannot leak through an endpoint.

---

## Notes

- `output/audit_trail.json` is **JSON Lines** — one JSON object per line. That is
  what makes appending safe; a single JSON array would have to be rewritten on
  every event.
- The audit trail records tool names, arguments, trimmed results and stop
  reasons. It deliberately does **not** record shoppers' message text or email
  addresses.
- Handsome Dan is drawn entirely in CSS. There is no image file.
