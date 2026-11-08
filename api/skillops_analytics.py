"""SkillOps analytics — estimated savings from the active SkillOpt policy.

A read-only companion to ``api/skillopt.py`` and ``api/trajectory.py``.
Compares, per skill, the primary provider/model the live policy chose
against a *uniform-pick baseline* (the average cost observed across every
candidate for the same skill). The output is an estimate — it uses the
historical corpus ``trajectory.summary`` already summarises in memory,
plus the pricing catalog in ``api/pricing.py``.

Loopback-only by its admin route. Nothing here mutates state.

The field names mirror EvoForge's: callers can diff a policy's score
against its observed savings without renaming anything.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from . import pricing, skillopt, trajectory


def _average_cost_per_sample(
    rows: list[dict[str, Any]],
) -> tuple[float, int]:
    """Return ``(avg_cost_per_row, samples)`` across the given rows."""
    if not rows:
        return (0.0, 0)
    total = sum(float(r.get("cost_usd") or 0.0) for r in rows)
    return (total / len(rows), len(rows))


def _policy_cost_for_rows(
    primary_ref: str,
    rows: list[dict[str, Any]],
) -> float:
    """Re-price every row as if it had been routed through ``primary_ref``.

    If the primary's pricing is unknown the sum is zero — this is
    *estimated* savings, not accounting. We never overstate a win.
    """
    if "/" not in primary_ref:
        return 0.0
    provider_id, model = primary_ref.split("/", 1)
    total = 0.0
    for row in rows:
        total += pricing.estimate_cost_usd(
            provider_id,
            model,
            int(row.get("input_tokens") or 0),
            int(row.get("output_tokens") or 0),
        )
    return round(total, 6)


def compute() -> dict[str, Any]:
    """Return the per-skill savings estimate snapshot."""
    policy_snapshot = skillopt.snapshot()
    rollup = trajectory.summary(limit=_SAMPLE_WINDOW)
    rows_by_skill: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in _recent_entries(limit=_SAMPLE_WINDOW):
        rows_by_skill[entry.get("skill", "chat")].append(entry)

    policies = policy_snapshot.get("policies") if policy_snapshot.get("loaded") else {}
    policies = policies or {}

    per_skill: dict[str, dict[str, Any]] = {}
    total_baseline = 0.0
    total_policy = 0.0
    for skill, entry in policies.items():
        rows = rows_by_skill.get(skill, [])
        if not rows:
            per_skill[skill] = {
                "primary": entry.get("primary"),
                "samples": 0,
                "baseline_cost_usd": 0.0,
                "policy_cost_usd": 0.0,
                "savings_usd": 0.0,
                "savings_pct": 0.0,
            }
            continue
        avg_cost, samples = _average_cost_per_sample(rows)
        baseline_cost = round(avg_cost * samples, 6)
        policy_cost = _policy_cost_for_rows(entry.get("primary", ""), rows)
        savings = round(baseline_cost - policy_cost, 6)
        pct = round((savings / baseline_cost) * 100, 2) if baseline_cost > 0 else 0.0
        per_skill[skill] = {
            "primary": entry.get("primary"),
            "samples": samples,
            "baseline_cost_usd": baseline_cost,
            "policy_cost_usd": policy_cost,
            "savings_usd": savings,
            "savings_pct": pct,
        }
        total_baseline += baseline_cost
        total_policy += policy_cost

    total_savings = round(total_baseline - total_policy, 6)
    total_pct = (
        round((total_savings / total_baseline) * 100, 2) if total_baseline > 0 else 0.0
    )

    return {
        "enabled": policy_snapshot.get("enabled", False),
        "loaded": policy_snapshot.get("loaded", False),
        "trajectory_total": rollup.get("total", 0),
        "per_skill": per_skill,
        "total_baseline_cost_usd": round(total_baseline, 6),
        "total_policy_cost_usd": round(total_policy, 6),
        "total_savings_usd": total_savings,
        "total_savings_pct": total_pct,
    }


# How many of the most recent rows to score. 500 is the in-memory cap in
# ``trajectory._MEMORY``, so this covers the entire visible window — a
# larger number than that just lands on the deque's cap.
_SAMPLE_WINDOW = 500


def _recent_entries(limit: int) -> list[dict[str, Any]]:
    """Return a snapshot of the in-memory trajectory rows.

    Pulled through a small helper so tests can monkeypatch it without
    touching the private deque.
    """
    return list(trajectory._MEMORY)[-limit:]
