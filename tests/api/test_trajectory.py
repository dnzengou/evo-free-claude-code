from __future__ import annotations

import json

from api import trajectory


def _enable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAJECTORY_LOG_ENABLED", "1")
    monkeypatch.setenv("FCC_CACHE_DIR", str(tmp_path))
    trajectory.reload_config()
    trajectory.clear()


def test_disabled_by_default_is_a_noop(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("TRAJECTORY_LOG_ENABLED", raising=False)
    monkeypatch.setenv("FCC_CACHE_DIR", str(tmp_path))
    trajectory.reload_config()
    trajectory.clear()

    trajectory.record(
        request_id="r1",
        provider_id="openai",
        model="gpt-4o",
        skill="chat",
        thinking_enabled=False,
        input_tokens=10,
        output_tokens=5,
        latency_ms=42.0,
        cost_usd=0.001,
        status="ok",
    )

    assert trajectory.summary()["total"] == 0
    assert not (tmp_path / "trajectories.jsonl").exists()


def test_record_persists_and_summary_rolls_up(monkeypatch, tmp_path) -> None:
    _enable(monkeypatch, tmp_path)

    trajectory.record(
        request_id="r1",
        provider_id="openai",
        model="gpt-4o",
        skill="edit",
        thinking_enabled=True,
        input_tokens=100,
        output_tokens=50,
        latency_ms=125.4,
        cost_usd=0.0002,
        status="ok",
    )
    trajectory.record(
        request_id="r2",
        provider_id="openai",
        model="gpt-4o-mini",
        skill="chat",
        thinking_enabled=False,
        input_tokens=20,
        output_tokens=10,
        latency_ms=90.0,
        cost_usd=0.00001,
        status="ok",
    )

    summary = trajectory.summary()
    assert summary["enabled"] is True
    assert summary["total"] == 2
    assert summary["per_skill"] == {"edit": 1, "chat": 1}
    assert summary["per_provider"] == {"openai": 2}
    assert summary["tokens_in"] == 120
    assert summary["tokens_out"] == 60

    log = tmp_path / "trajectories.jsonl"
    assert log.exists()
    rows = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    assert len(rows) == 2
    assert rows[0]["skill"] == "edit"
    assert rows[1]["model"] == "gpt-4o-mini"


def test_rotation_kicks_in_at_byte_cap(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAJECTORY_LOG_ENABLED", "1")
    monkeypatch.setenv("FCC_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("TRAJECTORY_LOG_MAX_BYTES", "300")
    trajectory.reload_config()
    trajectory.clear()

    for i in range(20):
        trajectory.record(
            request_id=f"r{i}",
            provider_id="openai",
            model="gpt-4o",
            skill="chat",
            thinking_enabled=False,
            input_tokens=1,
            output_tokens=1,
            latency_ms=1.0,
            cost_usd=0.0,
            status="ok",
        )

    log = tmp_path / "trajectories.jsonl"
    rotated = tmp_path / "trajectories.jsonl.1"
    assert log.exists()
    assert rotated.exists()


def test_infer_skill_probe_when_tiny_and_no_tools() -> None:
    assert trajectory.infer_skill([], None, 10) == "probe"


def test_infer_skill_edit_from_tool_names() -> None:
    tools = [{"name": "Edit"}, {"name": "TodoWrite"}]
    assert trajectory.infer_skill([{"content": "x"}], tools, 5000) == "edit"


def test_infer_skill_question_from_leading_word() -> None:
    messages = [{"role": "user", "content": "what does this function do"}]
    assert trajectory.infer_skill(messages, None, 5000) == "question"


def test_infer_skill_plan_from_keyword() -> None:
    messages = [{"role": "user", "content": "plan the migration in three phases"}]
    assert trajectory.infer_skill(messages, None, 5000) == "plan"


# ── v2.5.0 — commercial signals ─────────────────────────────────────


def test_fingerprint_from_user_agent_classifies_known_clients() -> None:
    assert trajectory.fingerprint_from_user_agent("claude-code/1.2.3") == "claude-code"
    assert (
        trajectory.fingerprint_from_user_agent(
            "anthropic-sdk-python/0.26.1 (Python 3.14)"
        )
        == "python-sdk"
    )
    assert (
        trajectory.fingerprint_from_user_agent("Mozilla/5.0 (claude.ai; chrome)")
        == "claude-ai"
    )
    assert trajectory.fingerprint_from_user_agent("ChatGPT/4.0 iPhone") == "chatgpt"
    assert trajectory.fingerprint_from_user_agent("PerplexityBot/1.0") == "perplexity"
    assert (
        trajectory.fingerprint_from_user_agent("vscode/1.95.0 (electron)") == "vscode"
    )
    assert (
        trajectory.fingerprint_from_user_agent("JetBrains IntelliJ IDEA") == "jetbrains"
    )
    assert trajectory.fingerprint_from_user_agent("curl/8.6.0") == "curl"
    assert trajectory.fingerprint_from_user_agent("axios/1.6.0") == "node-sdk"


def test_fingerprint_from_user_agent_handles_empty_and_unknown() -> None:
    assert trajectory.fingerprint_from_user_agent(None) == "unknown"
    assert trajectory.fingerprint_from_user_agent("") == "unknown"
    # Unknown but non-empty → "other"
    assert trajectory.fingerprint_from_user_agent("quibbler/1.0") == "other"


def test_record_captures_agent_and_channel_fields(monkeypatch, tmp_path) -> None:
    _enable(monkeypatch, tmp_path)

    trajectory.record(
        request_id="r-agent",
        provider_id="openai",
        model="gpt-4o",
        skill="chat",
        thinking_enabled=False,
        input_tokens=1,
        output_tokens=1,
        latency_ms=1.0,
        cost_usd=0.0,
        status="ok",
        agent_fingerprint="claude-code",
        channel="enterprise",
    )

    log = tmp_path / "trajectories.jsonl"
    data = json.loads(log.read_text().strip())
    assert data["agent_fingerprint"] == "claude-code"
    assert data["channel"] == "enterprise"

    rollup = trajectory.summary()
    assert rollup["per_agent"] == {"claude-code": 1}
    assert rollup["per_channel"] == {"enterprise": 1}


def test_record_contextvars_used_when_args_absent(monkeypatch, tmp_path) -> None:
    _enable(monkeypatch, tmp_path)
    trajectory.set_request_context(agent_fingerprint="perplexity", channel="org-demo")
    try:
        # Simulate service._metered_stream reading from contextvars when
        # record() is called without explicit kwargs.
        trajectory.record(
            request_id="r-ctx",
            provider_id="openai",
            model="gpt-4o",
            skill="chat",
            thinking_enabled=False,
            input_tokens=1,
            output_tokens=1,
            latency_ms=1.0,
            cost_usd=0.0,
            status="ok",
            agent_fingerprint=trajectory.current_agent_fingerprint(),
            channel=trajectory.current_channel(),
        )
    finally:
        trajectory.reset_request_context()

    data = json.loads((tmp_path / "trajectories.jsonl").read_text().strip())
    assert data["agent_fingerprint"] == "perplexity"
    assert data["channel"] == "org-demo"
    # After reset, lookups return None again — leak-free.
    assert trajectory.current_agent_fingerprint() is None
    assert trajectory.current_channel() is None


def test_record_without_commercial_fields_stays_backwards_compatible(
    monkeypatch, tmp_path
) -> None:
    _enable(monkeypatch, tmp_path)
    trajectory.reset_request_context()

    trajectory.record(
        request_id="r-plain",
        provider_id="openai",
        model="gpt-4o",
        skill="chat",
        thinking_enabled=False,
        input_tokens=1,
        output_tokens=1,
        latency_ms=1.0,
        cost_usd=0.0,
        status="ok",
    )
    data = json.loads((tmp_path / "trajectories.jsonl").read_text().strip())
    # Old-shape rows (no commercial signals) must stay intact — EvoForge
    # rows written before v2.5.0 keep working.
    assert "agent_fingerprint" not in data
    assert "channel" not in data
    # Summary falls back to "unknown" / "default" buckets for them.
    rollup = trajectory.summary()
    assert rollup["per_agent"] == {"unknown": 1}
    assert rollup["per_channel"] == {"default": 1}
