"""The Campus Customs shop assistant — a PydanticAI agent.

    run_agent(message, history) -> AgentRunResult

`main.py` imports this and nothing else from the agent side. The system prompt
lives in `prompts/prompt.md` and is read at run time, so editing that file
changes the assistant's behaviour without touching any code.

Model access goes through Portkey, using `PORTKEY_API_KEY` from a `.env` file.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import RunContext

import audit
import tools
from models import (
    AgentReply,
    AlternativesLookup,
    CatalogueOverview,
    CustomerContext,
    PageContext,
    ProductLookup,
    SearchResults,
    StockLookup,
)


@dataclass
class ShopDeps:
    """Everything the agent knows about *this* conversation.

    Passed to `agent.run(deps=...)` and reachable inside any tool via
    `ctx.deps`. Two things live here:

      * `customer` — who is chatting, or None for a guest
      * `page`     — what they are looking at, so "this" has a referent
    """

    customer: CustomerContext | None = None
    page: PageContext | None = None

HERE = Path(__file__).resolve().parent
PROMPT_PATH = HERE / "prompts" / "prompt.md"

# The .env may sit next to this file, in the homework folder, or further up in
# the course folder. Load whichever exists; the first value found wins.
for _candidate in (HERE, *HERE.parents[:5]):
    _env = _candidate / ".env"
    if _env.is_file():
        load_dotenv(_env, override=False)

MODEL_NAME = os.environ.get("PORTKEY_MODEL", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.environ.get("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
REQUEST_TIMEOUT = 60.0

# How many earlier turns to replay. Enough for "do you have that in navy?" to
# make sense, short enough to keep each call cheap.
MAX_HISTORY_TURNS = 8

# Loop limits. A shop question needs a handful of lookups; anything beyond this
# is a model stuck in a cycle, and the run is stopped rather than left to spend.
MAX_MODEL_REQUESTS = 6
MAX_TOOL_CALLS = 10

_FALLBACK_PROMPT = (
    "You are the Campus Customs shop assistant. Use your tools to look up real "
    "products before answering. Never invent a product, price or size. Keep "
    "replies to two or three sentences."
)


@dataclass
class AgentRunResult:
    """What one turn produced."""

    reply: str
    product_ids: list[str] = field(default_factory=list)
    result_summary: str = ""
    show_on_page: bool = False
    tools_used: list[str] = field(default_factory=list)
    error: str | None = None


def system_prompt() -> str:
    """Read the prompt from disk on every run, so edits take effect at once."""
    if PROMPT_PATH.is_file():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return _FALLBACK_PROMPT


def api_key() -> str:
    return os.environ.get("PORTKEY_API_KEY", "")


def build_agent():
    """Construct the agent and register its tools.

    Imports are local so that importing this module — and therefore `main.py` —
    never requires a configured API key. The site's product and auth routes keep
    working even when the assistant cannot run.
    """
    from openai import AsyncOpenAI
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    key = api_key()
    client = AsyncOpenAI(
        api_key=key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": key},
        timeout=REQUEST_TIMEOUT,
    )
    model = OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))

    agent = Agent(
        model,
        output_type=AgentReply,
        deps_type=ShopDeps,
        system_prompt=system_prompt(),
        retries=2,
    )

    @agent.instructions
    def who_and_where(ctx: RunContext[ShopDeps]) -> str:
        """Per-run context appended to the system prompt.

        Built fresh on every call, so it reflects the page the shopper is on at
        the moment they hit send.
        """
        lines: list[str] = []

        customer = ctx.deps.customer if ctx.deps else None
        if customer:
            greeting = customer.first_name or customer.name
            lines.append(
                f"You are speaking with {customer.name} ({customer.email}), who is "
                f"signed in. You may greet them as {greeting}. Their conversation "
                f"is saved, so earlier turns may be from a previous visit."
            )
        else:
            lines.append(
                "You are speaking with a guest who is not signed in. Do not ask "
                "for personal details; they can create an account if they want "
                "their conversation kept."
            )

        page = ctx.deps.page if ctx.deps else None
        if page and page.product_id:
            product = tools.get_product(page.product_id)
            if product.found:
                lines.append(
                    f"THE SHOPPER IS CURRENTLY VIEWING: {product.name} "
                    f"(product_id: {product.product_id}, {product.price_display}, "
                    f"colours: {', '.join(product.colors) or 'not listed'}). "
                    f"If they say \"this\", \"it\" or \"this one\" without naming a "
                    f"product, they mean this item. Look it up before answering "
                    f"rather than assuming."
                )
        elif page and page.path:
            where = {
                "/": "the home page",
                "/products": "the full catalogue",
                "/about": "the About Us page",
            }.get(page.path, f"the page {page.path}")
            lines.append(f"The shopper is browsing {where}.")

        return "\n\n".join(lines)

    @agent.tool
    def current_product(ctx: RunContext[ShopDeps]) -> ProductLookup:
        """The product the shopper currently has open on screen.

        Call this when they refer to "this", "it" or "this one" without naming
        a product. Returns found=false when they are not on a product page.
        """
        page = ctx.deps.page if ctx.deps else None
        if not page or not page.product_id:
            return ProductLookup(
                found=False,
                product_id="",
                error="The shopper is not on a product page, so there is no 'this'. Ask which item they mean.",
            )
        return tools.get_product(page.product_id)

    # Tool bodies live in tools.py; these wrappers exist only to register them
    # and to record which ones were called.
    @agent.tool_plain
    def search_products(
        query: str = "",
        garment_type: str = "",
        color: str = "",
        max_price: float = 0.0,
        min_price: float = 0.0,
        limit: int = tools.MAX_SEARCH_RESULTS,
    ) -> SearchResults:
        """Search the Campus Customs catalogue.

        Args:
            query: free text — a college, a sport, a phrase on the garment.
            garment_type: hoodie, crewneck, t-shirt, quarter-zip, jacket.
            color: navy, gray, white and so on.
            max_price: only at or below this price; 0 for no limit.
            min_price: only at or above this price; 0 for no limit.
            limit: how many to return, capped at 12.
        """
        return tools.search_products(query, garment_type, color, max_price, min_price, limit)

    @agent.tool_plain
    def get_product(product_id: str) -> ProductLookup:
        """Look up one product: full description, exact price, and stock by size.

        Call this for any question about what a specific item is, what it costs,
        or what it is made of. Never state a price you have not read from here.

        Args:
            product_id: the catalogue id, e.g. "yale-dad-t-shirt".
        """
        return tools.get_product(product_id)

    @agent.tool_plain
    def check_availability(product_id: str, size: str = "") -> StockLookup:
        """Check stock for a product, by size.

        Call this for "do you have it in medium?" and any other availability
        question. The result lists sizes_in_stock and sizes_out_of_stock
        separately — tell the shopper about the sold-out ones.

        Args:
            product_id: the catalogue id.
            size: XS, S, M, L, XL or XXL. Empty to get every size.
        """
        return tools.check_availability(product_id, size)

    @agent.tool_plain
    def find_alternatives(product_id: str, size: str, limit: int = 4) -> AlternativesLookup:
        """Similar items that ARE in stock in the size the shopper needs.

        Call this whenever you must tell someone their size is sold out, so the
        answer offers a way forward instead of ending the conversation.

        Args:
            product_id: the item they wanted.
            size: the size they need, e.g. "XL".
            limit: how many to suggest, at most 6.
        """
        return tools.find_alternatives(product_id, size, limit)

    @agent.tool_plain
    def list_garment_types() -> CatalogueOverview:
        """What kinds of garment the shop sells, and the overall price range."""
        return tools.list_garment_types()

    return agent


def _message_history(history: list) -> list:
    """Turn stored turns into PydanticAI messages.

    Accepts anything with `.role` and `.content` (the ChatMessageIn model, or a
    sqlite3.Row from chat_messages).
    """
    from pydantic_ai.messages import (
        ModelRequest,
        ModelResponse,
        TextPart,
        UserPromptPart,
    )

    messages = []
    for item in history[-MAX_HISTORY_TURNS:]:
        role = getattr(item, "role", None) or (item["role"] if "role" in item.keys() else None)
        content = getattr(item, "content", None) or (
            item["content"] if "content" in item.keys() else None
        )
        if not role or not content:
            continue
        if role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=str(content))]))
        elif role == "assistant":
            messages.append(ModelResponse(parts=[TextPart(content=str(content))]))
    return messages


# PydanticAI implements structured output as an internal tool call. It is
# plumbing, not one of the shop's tools, so keep it out of what we report.
_INTERNAL_TOOLS = {"final_result"}


def _tools_used(result) -> list[str]:
    """Which of the shop's tools the model actually called during this run."""
    from pydantic_ai.messages import ToolCallPart

    names: list[str] = []
    for message in result.all_messages():
        for part in getattr(message, "parts", []):
            if (
                isinstance(part, ToolCallPart)
                and part.tool_name not in _INTERNAL_TOOLS
                and part.tool_name not in names
            ):
                names.append(part.tool_name)
    return names


def _finish_reason(result) -> str | None:
    """Why the provider stopped generating, from the last model response."""
    from pydantic_ai.messages import ModelResponse

    for message in reversed(result.all_messages()):
        if isinstance(message, ModelResponse):
            reason = getattr(message, "finish_reason", None)
            return str(reason) if reason is not None else None
    return None


def _usage(result):
    """The run's usage record. It is an attribute in PydanticAI 2.x and a method
    in older releases, so accept either rather than pinning to one."""
    try:
        usage = getattr(result, "usage", None)
        return usage() if callable(usage) else usage
    except Exception:  # noqa: BLE001 — usage is nice to have, never required
        return None


def _usage_field(result, name: str) -> int | None:
    """One usage counter, if the provider reported it."""
    usage = _usage(result)
    return getattr(usage, name, None) if usage is not None else None


def _total_tokens(result) -> int | None:
    """Input plus output tokens. There is no single total field to read."""
    usage = _usage(result)
    if usage is None:
        return None
    parts = [getattr(usage, "input_tokens", None), getattr(usage, "output_tokens", None)]
    known = [p for p in parts if isinstance(p, int)]
    return sum(known) if known else None


async def run_agent(
    message: str,
    history: list | None = None,
    deps: ShopDeps | None = None,
) -> AgentRunResult:
    """Answer one shopper message.

    Never raises: a failure comes back as a polite reply plus an `error` field,
    so the chat widget degrades rather than showing the shopper a stack trace.
    """
    from pydantic_ai.usage import UsageLimits

    deps = deps or ShopDeps()
    customer = deps.customer
    run_id = audit.new_run_id()
    started = time.perf_counter()

    def close(stop_reason: str, **extra) -> None:
        """Write the run's closing audit event. Never raises."""
        audit.append(
            audit.run_event(
                run_id=run_id,
                stop_reason=stop_reason,
                started=started,
                ended=time.perf_counter(),
                model=MODEL_NAME,
                message_chars=len(message),
                signed_in=customer is not None,
                user_id=customer.user_id if customer else None,
                **extra,
            )
        )

    if not api_key():
        close("not_configured", error="PORTKEY_API_KEY is not set")
        return AgentRunResult(
            reply=(
                "The shop assistant is not configured right now, so I cannot look "
                "anything up. The Products page has the full catalogue in the meantime."
            ),
            error="PORTKEY_API_KEY is not set",
        )

    try:
        agent = build_agent()
        result = await agent.run(
            message,
            message_history=_message_history(history or []),
            deps=deps,
            # Stops a runaway loop from calling tools forever.
            usage_limits=UsageLimits(
                request_limit=MAX_MODEL_REQUESTS,
                tool_calls_limit=MAX_TOOL_CALLS,
            ),
        )
    except Exception as exc:  # noqa: BLE001 — surfaced to the UI, never raised
        # A usage limit is a distinct outcome from a provider failure, and the
        # audit trail should say which one happened.
        kind = type(exc).__name__
        stop = "usage_limit_exceeded" if "UsageLimit" in kind else "error"
        close(stop, error=f"{kind}: {exc}")
        return AgentRunResult(
            reply=(
                "Sorry — I could not look that up just now. Please try again in a "
                "moment, or browse the Products page."
            ),
            error=f"{kind}: {exc}",
        )

    # One event per tool call, paired by tool_call_id.
    events = audit.tool_events(result, run_id)
    for event in events:
        audit.append(event)

    output: AgentReply = result.output
    tools_used = _tools_used(result)
    close(
        "completed",
        finish_reason=_finish_reason(result),
        tools=tools_used,
        tool_call_count=len(events),
        reply_chars=len(output.reply or ""),
        product_ids=len(output.product_ids or []),
        requests=_usage_field(result, "requests"),
        total_tokens=_total_tokens(result),
    )

    return AgentRunResult(
        reply=output.reply,
        product_ids=list(output.product_ids or []),
        result_summary=(output.result_summary or "").strip(),
        # Only meaningful when there are products to show.
        show_on_page=bool(output.show_on_page and output.product_ids),
        tools_used=tools_used,
    )
