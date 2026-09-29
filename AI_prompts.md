# Homework 4 — Vibe Coder Prompts

A log of the prompts I typed while building this assignment, one section per
problem. Each section records the problem number and title, at least one prompt
I wrote, and — where one was needed — the follow-up prompt plus a note on what
the first prompt was missing.

The running site, the database writes, and the screenshots are the evidence that
the work was done. This file documents how I directed the AI to produce them.

---

## Problem 1 — Vibe Coder Prompt

### Prompt

Problem 1, title: "Vibe Coder Prompt". I want to have an `AI_prompts.md` at the
start of the assignment and keep it updated as you work. This will be the log of
what I typed to you (the vibe coder). I will describe each problem to you in my
own words. I want one section for each problem, and each section must include:
1) the problem number and title, 2) at least one prompt I typed, 3) one
follow-up prompt if I needed it, with one sentence on what was lacking after the
first. My running site, database writes and screenshots are the evidence — no
need for an extra proof essay beyond those prompts.

### Follow-up prompt

None needed.

---

## Problem 2 — Analyze the Database

### Prompt

Problem 2, title: "Analyze the database". Look at the database
`data/campus_customs.db` and please understand the fields of each table. You
need to at least understand `catalogue`, `inventory` and `users`. Start the file
`output/harness.md`. Write down each table and its fields, and one short line on
why each field matters for the shop or the chatbot. I want this harness file to
keep growing in later problems (models, tools, safety, specs).

### Follow-up prompt

None needed.

---

## Problem 3 — Build the Campus Customs Website

### Prompt

Problem 3, title: "Build the Campus Customs Website". I want you to scaffold a
React + Vite + TypeScript front end for Campus Customs. Put a nav bar at the top
that links to the main pages: 1) Home, 2) Products, 3) About Us, 4) Log in,
5) Create Account. Use Campus Customs-style wording from yalebulldogblue.com for
Home and About Us, but write these pages in your own voice — do not copy the
original site text. On the products page, show the product images from the
catalogue using the image paths in the database, with basic product info (name,
price, short description). Make each product open a single-item page (large
image on one side, full product text on the other — description, price,
size/stock when you have them), and clicking a card on products should take the
shopper there. Add a chat interface in the bottom right of the site; a floating
chat panel is fine. It does not need to talk to an agent yet — a stub that will
call my backend later is enough for this problem. I need a small API soon to
read the database, so it is fine to start a simple FastAPI app in
`backend/main.py` just to serve products and images, then grow it into the agent
backend in Problem 5.

### Follow-up prompt

None needed.

---

## Problem 4 — Create Account and Login

### Prompt

Problem 4, title: "Create account and login". Build me a normal create-account /
login flow, noting the following: 1) Create account: first name, last name,
email, password — confirm password is a nice touch. 2) Log in: email and
password. New accounts go into the `users` table. Ensure passwords are stored
securely so hackers (human or AI) can't access them. The seed database already
has a test user you can use while building: `test@campuscustoms.yale.edu` /
`password`. Confirm you can log in as that user and that a brand-new account you
create also works. Update `output/harness.md` with how auth works, what you
store for a user, and how passwords are protected.

### Follow-up prompt

None needed.

---

## Problem 5 — PydanticAI Agent Backend

### Prompt

Problem 5, title: "PydanticAI agent backend". Build the shop chatbot as a
PydanticAI agent behind FastAPI, plugged into the front-end chat widget. Put the
API app in `backend/main.py` — that is the file I run with Uvicorn. Keep the
agent as these four files next to it (same idea as Homework 3):
1) `backend/prompts/prompt.md`, the system prompt, which I will grow later.
2) `backend/agent.py`, the agent entry/wiring. 3) `backend/tools.py`, the tools
the agent can call. 4) `backend/models.py`, the Pydantic/PydanticAI structured
types. In `main.py`, expose a chatbot route so a message from the website
returns a reply from the agent, plus whatever is needed for products and auth.
I need the AI model API key wired up for the agent, so do the necessary. Put
Campus Customs voice and safety basics into `prompts/prompt.md` — tools and
safety get expanded later. Start or update types in `models.py` for chat replies
and product cards as needed. In `output/harness.md`, note how the front end
talks to FastAPI and how the agent is loaded (prompt file and model). Ensure the
backend runs from the `backend/` folder like this:
`uvicorn main:app --reload --port 8000`.

### Follow-up prompt

None needed.

---

## Problem 6 — Tools: Product Info and Stock

### Prompt

Problem 6, title: "Tools: product info and stock". I want the agent to have the
tools that look up real information from `campus_customs.db`: 1) product
description, 2) price, 3) how many are in stock, by size, when the customer
asks. The agent must use the database — it should not invent prices or
quantities. If a size is out of stock, tell that! Expand `prompts/prompt.md` so
the agent knows to call these tools for price and stock questions. Add or update
return types in `models.py`. In `output/harness.md`, list each tool and explain
which model fields I chose for lookup results and why.

### Follow-up prompt

None needed.

---

## Problem 7 — Chat Search That Updates the Page

### Prompt

Problem 7, title: "Chat search that updates the page". Add a neat feature to the
site: when a customer asks about a type of item — for example "what hoodies do
you have?" — the agent should search the catalogue and the website should
dynamically show those matching items as product cards (image, name, price and
short info). This is an API contract: the agent returns structured product
matches and the front end renders them on the website. I bet it will look cool,
so please ensure that is the case. After the dynamic product cards are loaded by
the new feature, make sure the single-item page behaviour built in Problem 3
still works: each product card — including the ones chat just put on the page —
should still open the detail view (large image and full information) when
clicked. Update `prompts/prompt.md` and `output/harness.md` so it is clear how
the search results reach the page.

### Follow-up prompt

None needed.

---

## Problem 8 — Customer Memory

### Prompt

Problem 8, title: "Customer Memory". When a shopper is logged in, save their
chat history in the database in an appropriate table and reload it when they
return — I don't want them to waste their time. The agent should know who is
chatting (name and email); put that in agent deps, or an equivalent clear
pattern, and/or tools the agent can call. Also pass enough page context that if
someone is on a product page and asks "do you have this in pink?", the agent
knows which item they mean — feel free to put the code in the agent context.
Guests can still chat, but history only needs to be saved for logged-in users.
Document in `output/harness.md` how the user chat history is stored, what
customer fields the agent sees, and how the page context is passed.

### Follow-up prompt

None needed.

---

## Problem 9 — Usability Improvements

### Prompt

Problem 9, title: "Usability improvements". Now that the core shop works,
improve it. Choose and implement: 1) two front-end usability improvements,
2) two agent/backend usability improvements. Front-end improvements are things
that make the site look better and easier to use. Agent/backend improvements are
things that make the agent output better, more accurate or safer — these could
be new agent tools, or things that make the agent run faster or cheaper. Write
`output/usability.md` before or as you build. For each improvement say: 1) what
you added, 2) why it helps a Campus Customs shopper or the business. After that,
ensure all improvements actually show up in the running app — graders will read
the write-up and look for the feature.

### Follow-up prompt

None needed.

---

## Problem 10 — Style the Website

### Prompt

Problem 10, title: "Style the website". Add a very creative and chic design so
the site feels like a real Campus Customs storefront: fonts, colour, hierarchy,
motion, product presentation and chat feel. Note that I will get more points if
I am creative and imaginative, so let's impress them — but we don't want to be
too much. I was thinking we can have Yale's Handsome Dan walking on the screen
of the customer, do you think this will work? Also write `output/design.md`:
what you changed and why it should help customers stick around and buy. Keep it
concrete and short.

### Follow-up prompt

None needed.

### Notes

Handsome Dan is built in CSS rather than as an image, per the project rule about
creating creatures code-natively.

The measurement that changed the design: sampling all 102 catalogue photos
showed 76 on pure black and 26 on pure white, with nothing in between. A warm
tile behind them produced a visible seam, so the photo fills the frame and
becomes the tile itself.

---

## Problem 11 — Site Testing (App Check)

### Prompt

Problem 11, title: "Site testing (app check)". Test the live site and document it
in `output/app_check.html`, which is a page you can double-click open. Include
clear screenshots and short captions for: 1) chat checking the inventory level of
an item (honest stock and price from the DB), 2) the dynamic search-result cards
appearing after a category question (e.g. hoodies), 3) one of the usability
features added in Problem 9. Make the HTML easy to grade: a heading for each
check, screenshots, and one or two sentences on what the screenshot proves. Put
the screenshot image files in `output/app_check_images/` and link them from
`app_check.html` with relative paths (for example `app_check_images/inventory.png`).

### Follow-up prompt

None needed.

### Notes

The test product for check 1 was chosen from the database first: Baseball Left
Chest Crewneck has M=5 and XL=0 at $58 — an awkward quantity plus a sold-out
size, so a guessed answer would be visibly wrong. Each agent claim is shown
beside the SQL that confirms it.

---

## Problem 12 — Audit Trail, Safety, Finish Harness

### Prompt

Problem 12, title: "Audit trail, safety, finish harness". Keep an append-only
`output/audit_trail.json` of agent-loop activity (the time, tool name, short
args/result, stop reason). Please don't wipe it between runs. Also, please think
of some safety rules that are reasonable and common and put them in
`prompts/prompt.md`. Finish `output/harness.md` so it is clear how the system
works: 1) model fields in `models.py` and why they were chosen, 2) tools and
abilities, 3) safety rules, 4) specs (loop limits, result caps, models and how
to run front and back).

### Follow-up prompt

None needed.

### Notes

The audit file is JSON Lines — one JSON object per line — because that is what
makes the append genuinely safe. A single JSON array would have to be rewritten
on every event, which is the operation that loses a file.

Tool calls are paired with their results by `tool_call_id`, never by tool name.
Matching on the name reports the last result for every call to the same tool —
a real bug from an earlier build, avoided here deliberately.

"Loop limits" were not previously enforced, so this problem added real ones via
PydanticAI's `UsageLimits` rather than just documenting an intention.

---

<!-- Sections for later problems get appended here as the work happens. -->
