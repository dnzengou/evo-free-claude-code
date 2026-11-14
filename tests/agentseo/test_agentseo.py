"""Tests for the standalone ``agentseo`` package.

These tests pin the package's contract — a product's generated
discovery surface must stay stable even when the host service evolves.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentseo import (
    AgentSEOConfig,
    Capability,
    Offer,
    build_router,
    render_manifests,
)


def _demo_config() -> AgentSEOConfig:
    return AgentSEOConfig(
        service_name="Demo Service",
        service_description="One sentence an LLM will quote.",
        repo_url="https://github.com/me/demo",
        live_url="https://demo.example.com",
        version="1.0.0",
        license="Apache-2.0",
        capabilities=(
            Capability(
                id="demo.hello",
                method="POST",
                path="/v1/hello",
                description="Say hello.",
            ),
        ),
        offers=(
            Offer(
                id="free",
                name="Free tier",
                price=0.0,
                intent="adoption",
                cta_url="https://demo.example.com/signup",
                summary="No cost, no strings.",
            ),
            Offer(
                id="pro",
                name="Pro",
                price=29.0,
                intent="sales-qualified",
                cta_url="https://demo.example.com/pro",
            ),
        ),
        evo_stack={
            "evo.cache": {"role": "cache", "enabled_env": "CACHE_ON"},
        },
    )


def test_render_manifests_covers_every_endpoint() -> None:
    config = _demo_config()
    out = render_manifests(config, "https://demo.example.com")
    expected = {
        "/llms.txt",
        "/llms-full.txt",
        "/sitemap.xml",
        "/robots.txt",
        "/.well-known/ai-plugin.json",
        "/.well-known/agents.json",
        "/.well-known/mcp.json",
        "/.well-known/agents-registry.json",
        "/.well-known/commerce.json",
    }
    assert set(out.keys()) == expected


def test_llms_txt_names_service_and_capability() -> None:
    body = render_manifests(_demo_config(), "https://demo.example.com")["/llms.txt"]
    assert body.startswith("# Demo Service")
    assert "POST https://demo.example.com/v1/hello" in body
    assert "commerce.json" in body


def test_commerce_manifest_respects_intents() -> None:
    body = render_manifests(_demo_config(), "https://demo.example.com")[
        "/.well-known/commerce.json"
    ]
    data = json.loads(body)
    assert data["@type"] == "OfferCatalog"
    assert set(data["intents"]) == {"adoption", "sales-qualified"}
    assert {o["id"] for o in data["offers"]} == {"free", "pro"}


def test_robots_txt_lists_default_crawlers_and_sitemap() -> None:
    body = render_manifests(_demo_config(), "https://demo.example.com")["/robots.txt"]
    for crawler in (
        "GPTBot",
        "ClaudeBot",
        "PerplexityBot",
        "CCBot",
        "Applebot-Extended",
        "Meta-ExternalAgent",
        "Bytespider",
    ):
        assert crawler in body
    assert "Sitemap:" in body
    assert "/sitemap.xml" in body


def test_sitemap_xml_omits_disallowed_paths() -> None:
    config = _demo_config()
    body = render_manifests(config, "https://demo.example.com")["/sitemap.xml"]
    assert body.startswith('<?xml version="1.0"')
    for disallowed in config.disallow_paths:
        assert f"loc>https://demo.example.com{disallowed}" not in body


def test_agents_registry_has_capability_matrix() -> None:
    body = render_manifests(_demo_config(), "https://demo.example.com")[
        "/.well-known/agents-registry.json"
    ]
    data = json.loads(body)
    assert data["name"] == "Demo Service"
    assert data["version"] == "1.0.0"
    assert data["license"] == "Apache-2.0"
    ids = {c["id"] for c in data["capabilities"]}
    assert ids == {"demo.hello"}
    assert "evo.cache" in data["evo_stack"]


def test_llms_full_txt_embeds_json_ld() -> None:
    body = render_manifests(_demo_config(), "https://demo.example.com")[
        "/llms-full.txt"
    ]
    assert '"@context": "https://schema.org"' in body
    assert '"@type": "WebAPI"' in body
    assert "ConsumeAction" in body


def test_build_router_serves_all_endpoints() -> None:
    config = _demo_config()
    app = FastAPI()
    app.include_router(build_router(config))
    client = TestClient(app)
    for path in (
        "/llms.txt",
        "/llms-full.txt",
        "/sitemap.xml",
        "/robots.txt",
        "/.well-known/ai-plugin.json",
        "/.well-known/agents.json",
        "/.well-known/mcp.json",
        "/.well-known/agents-registry.json",
        "/.well-known/commerce.json",
    ):
        r = client.get(path)
        assert r.status_code == 200, f"{path} returned {r.status_code}"


def test_cli_writes_every_file(tmp_path: Path) -> None:
    from agentseo.cli import main

    config_path = tmp_path / "agentseo.json"
    config_path.write_text(
        json.dumps(
            {
                "service_name": "Demo",
                "service_description": "Demo.",
                "repo_url": "https://example.com/r",
                "live_url": "https://example.com",
                "capabilities": [{"id": "demo.ping", "method": "GET", "path": "/ping"}],
                "offers": [
                    {
                        "id": "free",
                        "name": "Free",
                        "price": 0.0,
                        "intent": "adoption",
                        "cta_url": "https://example.com/get",
                    }
                ],
            }
        )
    )
    out = tmp_path / "public"
    rc = main(
        [
            "--config",
            str(config_path),
            "--base-url",
            "https://example.com",
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    assert (out / "llms.txt").exists()
    assert (out / ".well-known" / "commerce.json").exists()
    # the sitemap carries the right base url
    sitemap = (out / "sitemap.xml").read_text()
    assert "https://example.com/llms.txt" in sitemap
