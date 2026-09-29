"""Append-only audit trail for the agent loop.

Every run writes to `output/audit_trail.json`: one event per tool call, then one
event closing the run with its stop reason. The file is **only ever appended
to** — nothing here opens it for writing, so a crash mid-run can damage at most
the final line, and history from earlier runs cannot be lost.

Format is JSON Lines: one complete JSON object per line. That is what makes the
append safe — a single JSON array would have to be rewritten on every event,
which is exactly the operation that loses a file.

Read it back with:

    import json
    events = [json.loads(line) for line in open("output/audit_trail.json")]

What is deliberately **not** recorded: the shopper's message text and their
email address. The loop is auditable — which tool ran, on what arguments, what
came back, why it stopped — without the log becoming a second copy of everyone's
conversations. Tool arguments are kept, since they carry the substance of the
request ("hoodie", "XL") without the person attached.
"""

from __future__ import annotations

import json
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
AUDIT_PATH = HERE.parent / "output" / "audit_trail.json"

# How much of any single argument or result is kept.
MAX_FIELD_CHARS = 220

# Writes are one line each; the lock keeps concurrent requests from interleaving.
_LOCK = threading.Lock()


def new_run_id() -> str:
    """A short id tying one run's events together."""
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _short(value: Any, limit: int = MAX_FIELD_CHARS) -> Any:
    """Compact a value to something readable and bounded."""
    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, str):
        text = value
    elif hasattr(value, "model_dump_json"):
        try:
            text = value.model_dump_json()
        except Exception:  # noqa: BLE001 — audit must never break a chat
            text = str(value)
    else:
        try:
            text = json.dumps(value, default=str)
        except Exception:  # noqa: BLE001
            text = str(value)

    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _short_args(args: Any) -> Any:
    """Tool arguments, each value trimmed, dropping empty ones for readability."""
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (ValueError, TypeError):
            return _short(args)
    if isinstance(args, dict):
        return {k: _short(v, 80) for k, v in args.items() if v not in ("", None, 0, 0.0)}
    return _short(args)


def append(event: dict) -> None:
    """Append one event. Never raises — a broken log must not break the shop."""
    try:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, default=str, ensure_ascii=False) + "\n"
        with _LOCK:
            # "a" is append-only: the file is never truncated or rewritten.
            with AUDIT_PATH.open("a", encoding="utf-8") as fh:
                fh.write(line)
    except Exception as exc:  # noqa: BLE001
        print(f"[audit] could not write event: {exc}", file=sys.stderr)


def tool_events(result, run_id: str) -> list[dict]:
    """Build one event per tool call, pairing each call with its own return.

    Calls and returns are matched by `tool_call_id`, never by tool name — a run
    that calls the same tool three times has three distinct ids, and matching on
    the name would report the last return for all three.
    """
    from pydantic_ai.messages import ToolCallPart, ToolReturnPart

    internal = {"final_result"}
    calls: list[tuple[str, Any]] = []      # (tool_call_id, part)
    returns: dict[str, Any] = {}           # tool_call_id -> part

    for message in result.all_messages():
        for part in getattr(message, "parts", []):
            if isinstance(part, ToolCallPart) and part.tool_name not in internal:
                calls.append((part.tool_call_id, part))
            elif isinstance(part, ToolReturnPart) and part.tool_name not in internal:
                returns[part.tool_call_id] = part

    events = []
    for seq, (call_id, call) in enumerate(calls, start=1):
        ret = returns.get(call_id)
        events.append(
            {
                "ts": _now(),
                "run_id": run_id,
                "event": "tool_call",
                "seq": seq,
                "tool": call.tool_name,
                "args": _short_args(call.args),
                "result": _short(ret.content) if ret is not None else None,
                "returned": ret is not None,
            }
        )
    return events


def run_event(
    *,
    run_id: str,
    stop_reason: str,
    started: float,
    ended: float,
    model: str,
    message_chars: int,
    signed_in: bool,
    user_id: int | None = None,
    tools: list[str] | None = None,
    tool_call_count: int = 0,
    reply_chars: int = 0,
    product_ids: int = 0,
    finish_reason: str | None = None,
    requests: int | None = None,
    total_tokens: int | None = None,
    error: str | None = None,
) -> dict:
    """The event that closes a run and records why the loop stopped."""
    return {
        "ts": _now(),
        "run_id": run_id,
        "event": "run_end",
        "stop_reason": stop_reason,
        "finish_reason": finish_reason,
        "model": model,
        "duration_ms": round((ended - started) * 1000),
        "tool_calls": tool_call_count,
        "tools": tools or [],
        "message_chars": message_chars,
        "reply_chars": reply_chars,
        "product_ids": product_ids,
        "signed_in": signed_in,
        "user_id": user_id,
        "model_requests": requests,
        "total_tokens": total_tokens,
        "error": error,
    }
