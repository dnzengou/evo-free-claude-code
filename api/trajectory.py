"""EvoMetaClaw trajectory logger — the moat.

Every completed proxy request emits one JSONL record with the metadata
needed for SkillOpt-style trajectory-based fine-tuning:

    * request routing (provider, model, thinking flag)
    * outcome (status, latency, input/output tokens, cost estimate)
    * a skill tag inferred from the request (edit / plan / question / probe)

The write path is opt-in via ``TRAJECTORY_LOG_ENABLED``. Storage is a
bounded newline-delimited JSON file with a byte cap; when the cap is
reached, the file is rotated to ``<name>.1`` so the newest cap-worth of
data always stays hot. Serverless-safe: on a read-only filesystem the
writer disables itself for the process (same pattern as
``configure_logging`` / ``health_history``).

The moat: OpenClaw can copy a provider registry. They cannot copy the
trajectory corpus that this file accumulates over months of real usage,
nor the SkillOpt fine-tunes trained on it. Registry parity is a
commodity; trajectory data is not.
"""

from __future__ import annotations

import contextvars
import json
import os
import threading
import time
from collections import Counter, deque
from pathlib import Path
from typing import Any

_ENABLED = os.environ.get("TRAJECTORY_LOG_ENABLED", "").lower() in {
    "1",
    "true",
    "yes",
}
_MAX_BYTES = int(os.environ.get("TRAJECTORY_LOG_MAX_BYTES") or 5_000_000)
_MAX_MEMORY_ENTRIES = 500

_LOCK = threading.Lock()
_MEMORY: deque[dict[str, Any]] = deque(maxlen=_MAX_MEMORY_ENTRIES)
_WRITER_DISABLED = False
_LOG_PATH: Path | None = None

# Per-request commercial attribution set by the FastAPI route before
# ``ClaudeProxyService.create_message`` runs. A contextvar is the right
# tool: it is both asyncio-task-safe and automatically propagated to the
# streaming async-generator that ``_metered_stream`` consumes, without
# any threading of extra parameters through unrelated service layers.
_AGENT_FINGERPRINT_CTX: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "fcc_agent_fingerprint", default=None
)
_CHANNEL_CTX: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "fcc_channel", default=None
)


def set_request_context(
    *, agent_fingerprint: str | None = None, channel: str | None = None
) -> None:
    """Attach commercial-attribution tags to the current request's trajectory row."""
    _AGENT_FINGERPRINT_CTX.set(agent_fingerprint)
    _CHANNEL_CTX.set(channel)


def current_agent_fingerprint() -> str | None:
    """Return the agent fingerprint for the current request, if any."""
    return _AGENT_FINGERPRINT_CTX.get()


def current_channel() -> str | None:
    """Return the GTM channel for the current request, if any."""
    return _CHANNEL_CTX.get()


def reset_request_context() -> None:
    """Clear per-request attribution tags (for tests)."""
    _AGENT_FINGERPRINT_CTX.set(None)
    _CHANNEL_CTX.set(None)


def _log_path() -> Path:
    base = os.environ.get("FCC_CACHE_DIR")
    root = Path(base) if base else Path.home() / ".fcc-cache"
    return root / "trajectories.jsonl"


def is_enabled() -> bool:
    """Return whether the trajectory log is currently accepting writes."""
    return _ENABLED and not _WRITER_DISABLED


def infer_skill(
    messages: list[Any] | None,
    tools: list[Any] | None,
    input_tokens: int | None = None,
) -> str:
    """Cheap skill-tag heuristic. Precise enough for SkillOpt bucketing.

    ``input_tokens`` is optional — when unknown (pre-routing), the "probe"
    short-circuit uses the raw text length instead. The remaining branches
    only look at messages + tools.
    """
    approx_tokens = (
        input_tokens if input_tokens is not None else _approx_tokens(messages)
    )
    if approx_tokens <= 128 and not tools:
        return "probe"
    if tools:
        tool_names = _tool_names(tools)
        if any(name in _EDIT_TOOL_NAMES for name in tool_names):
            return "edit"
        if any(name in _PLAN_TOOL_NAMES for name in tool_names):
            return "plan"
    text = _first_user_text(messages).lower()
    if any(w in text for w in _EDIT_KEYWORDS):
        return "edit"
    if any(w in text for w in _PLAN_KEYWORDS):
        return "plan"
    if text.endswith("?") or text.startswith(("why ", "how ", "what ", "when ")):
        return "question"
    return "chat"


def _approx_tokens(messages: list[Any] | None) -> int:
    """Rough char/4 estimate — good enough for the probe threshold."""
    if not messages:
        return 0
    total_chars = 0
    for m in messages:
        if isinstance(m, dict):
            content = m.get("content")
        else:
            content = getattr(m, "content", None)
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                total_chars += len(_block_text(block))
    return total_chars // 4


_EDIT_TOOL_NAMES = frozenset(
    {"str_replace_editor", "text_editor", "Edit", "Write", "NotebookEdit"}
)
_PLAN_TOOL_NAMES = frozenset({"TodoWrite", "Plan", "TaskCreate"})
_EDIT_KEYWORDS = ("fix ", "refactor", "rewrite", "modify ", "update ")
_PLAN_KEYWORDS = ("plan ", "design ", "outline ", "propose ")


def _tool_names(tools: list[Any]) -> list[str]:
    names: list[str] = []
    for tool in tools:
        if isinstance(tool, dict) and isinstance(tool.get("name"), str):
            names.append(tool["name"])
        else:
            name = getattr(tool, "name", None)
            if isinstance(name, str):
                names.append(name)
    return names


def _first_user_text(messages: list[Any] | None) -> str:
    if not messages:
        return ""
    first = messages[0]
    if isinstance(first, dict):
        content = first.get("content")
    else:
        content = getattr(first, "content", None)
    if isinstance(content, str):
        return content[:512]
    if isinstance(content, list):
        for block in content:
            text = _block_text(block)
            if text:
                return text[:512]
    return ""


def _block_text(block: Any) -> str:
    """Return the text of a content block whether it's a dict or Pydantic model."""
    if isinstance(block, dict):
        if block.get("type") != "text":
            return ""
        text = block.get("text", "")
        return text if isinstance(text, str) else ""
    if getattr(block, "type", None) != "text":
        return ""
    text = getattr(block, "text", "")
    return text if isinstance(text, str) else ""


# Client fingerprint classifier — used both to tag trajectory rows for
# GTM analytics and to let an agent reason about *which* client is
# calling. Kept deterministic and dependency-free; order matters since
# `claude-code` substrings also appear in generic user-agents.
_FINGERPRINT_RULES: tuple[tuple[str, str], ...] = (
    ("claude-code", "claude-code"),
    ("anthropic-sdk-python", "python-sdk"),
    ("anthropic-sdk", "anthropic-sdk"),
    ("claude-ai", "claude-ai"),
    ("claude.ai", "claude-ai"),
    ("gpt-", "chatgpt"),
    ("chatgpt", "chatgpt"),
    ("perplexity", "perplexity"),
    ("vscode", "vscode"),
    ("jetbrains", "jetbrains"),
    ("intellij", "jetbrains"),
    ("discord", "discord"),
    ("telegram", "telegram"),
    ("curl/", "curl"),
    ("httpie/", "curl"),
    ("python-requests", "python-sdk"),
    ("python-httpx", "python-sdk"),
    ("node-fetch", "node-sdk"),
    ("axios", "node-sdk"),
)


def fingerprint_from_user_agent(user_agent: str | None) -> str:
    """Classify a raw ``User-Agent`` header into a known commercial channel.

    Returns ``"other"`` when nothing matches. The classifier is
    deliberately conservative and case-insensitive so a single rule file
    covers CLI tools, IDE extensions, bots, and SDKs without needing to
    track upstream UA format changes.
    """
    if not user_agent:
        return "unknown"
    lowered = user_agent.lower()
    for needle, fp in _FINGERPRINT_RULES:
        if needle in lowered:
            return fp
    return "other"


def record(
    *,
    request_id: str,
    provider_id: str,
    model: str,
    skill: str,
    thinking_enabled: bool,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    cost_usd: float,
    status: str,
    agent_fingerprint: str | None = None,
    channel: str | None = None,
) -> None:
    """Append one trajectory row. No-op when the log is disabled.

    ``agent_fingerprint`` and ``channel`` are optional commercial-intent
    tags. They let EvoForge be re-aggregated later per channel (which
    agents/surfaces convert) without a schema change — rows missing the
    fields are tolerated by every consumer.
    """
    if not _ENABLED:
        return
    entry: dict[str, Any] = {
        "ts": time.time(),
        "request_id": request_id,
        "provider_id": provider_id,
        "model": model,
        "skill": skill,
        "thinking": thinking_enabled,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": round(latency_ms, 1),
        "cost_usd": cost_usd,
        "status": status,
    }
    if agent_fingerprint:
        entry["agent_fingerprint"] = agent_fingerprint
    if channel:
        entry["channel"] = channel
    with _LOCK:
        _MEMORY.append(entry)
        _append_locked(entry)


def _append_locked(entry: dict[str, Any]) -> None:
    global _WRITER_DISABLED, _LOG_PATH
    if _WRITER_DISABLED:
        return
    if _LOG_PATH is None:
        _LOG_PATH = _log_path()
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if _LOG_PATH.exists() and _LOG_PATH.stat().st_size >= _MAX_BYTES:
            rotated = _LOG_PATH.with_suffix(_LOG_PATH.suffix + ".1")
            _LOG_PATH.replace(rotated)
        with _LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False))
            fh.write("\n")
    except OSError:
        _WRITER_DISABLED = True


def summary(limit: int = 500) -> dict[str, Any]:
    """Return an in-memory rollup safe to expose in the admin UI."""
    with _LOCK:
        entries = list(_MEMORY)[-limit:]
    total = len(entries)
    per_skill: Counter[str] = Counter(entry["skill"] for entry in entries)
    per_provider: Counter[str] = Counter(entry["provider_id"] for entry in entries)
    per_agent: Counter[str] = Counter(
        entry.get("agent_fingerprint", "unknown") for entry in entries
    )
    per_channel: Counter[str] = Counter(
        entry.get("channel", "default") for entry in entries
    )
    cost = round(sum(entry["cost_usd"] for entry in entries), 6)
    tokens_in = sum(entry["input_tokens"] for entry in entries)
    tokens_out = sum(entry["output_tokens"] for entry in entries)
    return {
        "enabled": is_enabled(),
        "total": total,
        "per_skill": dict(per_skill),
        "per_provider": dict(per_provider),
        "per_agent": dict(per_agent),
        "per_channel": dict(per_channel),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost,
        "log_path": str(_LOG_PATH) if _LOG_PATH else None,
    }


def clear() -> None:
    """Reset process state (for tests)."""
    global _WRITER_DISABLED, _LOG_PATH
    with _LOCK:
        _MEMORY.clear()
        _WRITER_DISABLED = False
        _LOG_PATH = None


def reload_config() -> None:
    """Re-read the env-driven flags (for tests)."""
    global _ENABLED, _MAX_BYTES, _WRITER_DISABLED, _LOG_PATH
    _ENABLED = os.environ.get("TRAJECTORY_LOG_ENABLED", "").lower() in {
        "1",
        "true",
        "yes",
    }
    _MAX_BYTES = int(os.environ.get("TRAJECTORY_LOG_MAX_BYTES") or 5_000_000)
    _WRITER_DISABLED = False
    _LOG_PATH = None
