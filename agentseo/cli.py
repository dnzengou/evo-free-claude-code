"""CLI: render every agent-SEO manifest to a folder.

Use this to publish the discovery surface from a static-site build or a
CDN:

    python -m agentseo.cli --config agentseo.json --base-url https://x.com --out ./public

The config file is a JSON object with the fields of
:class:`agentseo.AgentSEOConfig` — ``capabilities`` and ``offers`` are
plain lists of dicts matching those dataclasses.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import (
    AgentSEOConfig,
    Feature,
    Plan,
    coerce_capability,
    coerce_offer,
)
from .manifests import render_manifests


def _coerce_feature(f: Feature | dict) -> Feature:
    if isinstance(f, Feature):
        return f
    data = dict(f)
    if "plans" in data and isinstance(data["plans"], list):
        data["plans"] = tuple(data["plans"])
    return Feature(**data)


def _coerce_plan(p: Plan | dict) -> Plan:
    return p if isinstance(p, Plan) else Plan(**p)


def _load_config(path: Path) -> AgentSEOConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["capabilities"] = tuple(
        coerce_capability(c) for c in raw.get("capabilities", [])
    )
    raw["offers"] = tuple(coerce_offer(o) for o in raw.get("offers", []))
    raw["plans"] = tuple(_coerce_plan(p) for p in raw.get("plans", []))
    raw["features"] = tuple(_coerce_feature(f) for f in raw.get("features", []))
    for k in (
        "disallow_paths",
        "ai_crawler_user_agents",
        "ecosystem_clients",
        "ecosystem_upstreams",
    ):
        if k in raw and isinstance(raw[k], list):
            raw[k] = tuple(raw[k])
    return AgentSEOConfig(**raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agentseo", description=__doc__)
    parser.add_argument(
        "--config", type=Path, required=True, help="Path to agentseo.json"
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="Public base URL this manifest set will be served from",
    )
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    args = parser.parse_args(argv)

    config = _load_config(args.config)
    manifests = render_manifests(config, args.base_url.rstrip("/"))
    args.out.mkdir(parents=True, exist_ok=True)
    for url_path, body in manifests.items():
        target = args.out / url_path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
