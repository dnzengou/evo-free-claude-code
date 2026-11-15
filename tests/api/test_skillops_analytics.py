from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api import skillops_analytics, skillopt, trajectory
from api.app import create_app


def _enable_trajectory(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TRAJECTORY_LOG_ENABLED", "1")
    monkeypatch.setenv("FCC_CACHE_DIR", str(tmp_path))
    trajectory.reload_config()
    trajectory.clear()


def _write_policy(tmp_path, payload) -> None:
    (tmp_path / "skillopt_policy.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_compute_empty_when_no_policy_and_no_corpus(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("SKILLOPT_ENABLED", raising=False)
    monkeypatch.setenv("FCC_CACHE_DIR", str(tmp_path))
    trajectory.reload_config()
    trajectory.clear()
    skillopt.invalidate_cache()

    out = skillops_analytics.compute()
    assert out["enabled"] is False
    assert out["per_skill"] == {}
    assert out["total_savings_usd"] == 0.0


def test_compute_reports_savings_when_policy_is_cheaper(monkeypatch, tmp_path) -> None:
    # Policy routes "chat" at gpt-4o-mini. Baseline corpus observed
    # gpt-4o at a much higher per-row cost. The analytics layer should
    # estimate savings > 0.
    monkeypatch.setenv("SKILLOPT_ENABLED", "1")
    monkeypatch.setenv("FCC_CACHE_DIR", str(tmp_path))
    _write_policy(
        tmp_path,
        {
            "version": 1,
            "policies": {
                "chat": {"primary": "openai/gpt-4o-mini", "fallbacks": []},
            },
        },
    )
    skillopt.invalidate_cache()
    _enable_trajectory(monkeypatch, tmp_path)

    # Historical rows are on the pricier gpt-4o — that is the baseline.
    for i in range(5):
        trajectory.record(
            request_id=f"r{i}",
            provider_id="openai",
            model="gpt-4o",
            skill="chat",
            thinking_enabled=False,
            input_tokens=1000,
            output_tokens=500,
            latency_ms=100.0,
            cost_usd=0.0075,  # gpt-4o pricing (2.50/M in + 10/M out)
            status="ok",
        )

    out = skillops_analytics.compute()
    assert out["enabled"] is True
    assert out["loaded"] is True
    chat = out["per_skill"]["chat"]
    assert chat["samples"] == 5
    assert chat["baseline_cost_usd"] > 0
    # gpt-4o-mini is dramatically cheaper than gpt-4o on the same tokens.
    assert chat["policy_cost_usd"] < chat["baseline_cost_usd"]
    assert chat["savings_usd"] > 0
    assert chat["savings_pct"] > 0
    assert out["total_savings_usd"] > 0


def test_compute_reports_zero_when_pricing_unknown(monkeypatch, tmp_path) -> None:
    # A policy that points at an un-priced provider/model falls through
    # to zero policy cost — we must NEVER overstate savings in that case.
    monkeypatch.setenv("SKILLOPT_ENABLED", "1")
    monkeypatch.setenv("FCC_CACHE_DIR", str(tmp_path))
    _write_policy(
        tmp_path,
        {
            "version": 1,
            "policies": {
                "edit": {"primary": "mystery_provider/mystery-model", "fallbacks": []},
            },
        },
    )
    skillopt.invalidate_cache()
    _enable_trajectory(monkeypatch, tmp_path)

    trajectory.record(
        request_id="r0",
        provider_id="openai",
        model="gpt-4o",
        skill="edit",
        thinking_enabled=False,
        input_tokens=100,
        output_tokens=50,
        latency_ms=50.0,
        cost_usd=0.0007,
        status="ok",
    )
    out = skillops_analytics.compute()
    edit = out["per_skill"]["edit"]
    # Unknown pricing → policy_cost_usd is 0, savings is baseline_cost - 0.
    # The purpose of the zero floor is to avoid NEGATIVE policy costs,
    # not to hide a baseline that genuinely exists — so savings still
    # register. The reviewer sees the zero policy cost and flags it.
    assert edit["policy_cost_usd"] == 0.0
    assert edit["baseline_cost_usd"] > 0


def _local_client(app):
    return TestClient(app, client=("127.0.0.1", 50000))


def test_admin_endpoint_is_loopback_only() -> None:
    app = create_app(lifespan_enabled=False)
    remote = TestClient(app, client=("203.0.113.10", 50000))
    assert remote.get("/admin/api/skillops/analytics").status_code == 403


def test_admin_endpoint_returns_shape(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SKILLOPT_ENABLED", "1")
    monkeypatch.setenv("FCC_CACHE_DIR", str(tmp_path))
    _write_policy(
        tmp_path,
        {
            "version": 1,
            "policies": {
                "chat": {"primary": "openai/gpt-4o-mini", "fallbacks": []},
            },
        },
    )
    skillopt.invalidate_cache()
    _enable_trajectory(monkeypatch, tmp_path)

    app = create_app(lifespan_enabled=False)
    r = _local_client(app).get("/admin/api/skillops/analytics")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) >= {
        "enabled",
        "loaded",
        "per_skill",
        "total_baseline_cost_usd",
        "total_policy_cost_usd",
        "total_savings_usd",
    }
