from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api.app import create_app


def _client():
    return TestClient(create_app(lifespan_enabled=False))


# ── llms.txt ─────────────────────────────────────────────────────────


def test_llms_txt_is_public_and_markdown():
    r = _client().get("/llms.txt")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    body = r.text
    assert body.startswith("# Free Claude Code")
    assert "/v1/messages" in body
    assert "/.well-known/" in body


def test_llms_full_txt_is_public_and_expanded():
    r = _client().get("/llms-full.txt")
    assert r.status_code == 200
    body = r.text
    assert "Full reference" in body or "full reference" in body
    assert "EvoMetaClaw" in body
    assert "SkillOpt" in body


# ── /.well-known/ manifests ──────────────────────────────────────────


def test_ai_plugin_manifest_shape():
    r = _client().get("/.well-known/ai-plugin.json")
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "v1"
    assert body["name_for_model"] == "free_claude_code"
    assert body["api"]["type"] == "openapi"
    assert body["api"]["url"].endswith("/openapi.json")


def test_agents_manifest_lists_capabilities():
    r = _client().get("/.well-known/agents.json")
    assert r.status_code == 200
    body = r.json()
    names = {cap["name"] for cap in body["capabilities"]}
    assert "anthropic.messages" in names
    assert "anthropic.count_tokens" in names
    assert "anthropic.models" in names
    # ecosystem field surfaces our provider list for agent discovery
    assert "openai" in body["ecosystem"]["upstream_providers"]
    assert "claude-code" in body["ecosystem"]["clients"]


def test_mcp_manifest_points_to_openapi_and_docs():
    r = _client().get("/.well-known/mcp.json")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "openapi-service"
    assert body["openapi"].endswith("/openapi.json")
    assert body["docs"]["llms_txt"].endswith("/llms.txt")


# ── robots.txt ───────────────────────────────────────────────────────


def test_robots_txt_welcomes_ai_crawlers_and_blocks_admin():
    r = _client().get("/robots.txt")
    assert r.status_code == 200
    body = r.text
    assert "Disallow: /admin" in body
    assert "GPTBot" in body
    assert "ClaudeBot" in body


# ── OpenAPI reflects the renamed title ───────────────────────────────


def test_openapi_has_agent_friendly_title():
    r = _client().get("/openapi.json")
    assert r.status_code == 200
    spec = json.loads(r.text)
    assert "Free Claude Code" in spec["info"]["title"]
    assert spec["info"]["version"] == "2.5.0"


# ── public — no auth needed, no proxy env to set ─────────────────────


def test_discovery_endpoints_are_unauthenticated(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "shh")
    client = TestClient(create_app(lifespan_enabled=False))
    # auth-required routes return 401 without a token
    assert client.get("/v1/models").status_code in (401, 403)
    # discovery routes still return 200
    assert client.get("/llms.txt").status_code == 200
    assert client.get("/.well-known/agents.json").status_code == 200


# ── v2.5.0 agent-SEO additions ──────────────────────────────────────


def test_sitemap_xml_lists_public_urls():
    r = _client().get("/sitemap.xml")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/xml")
    body = r.text
    assert body.startswith('<?xml version="1.0"')
    assert "<urlset" in body
    assert "/llms.txt</loc>" in body
    assert "/.well-known/ai-plugin.json</loc>" in body
    assert "/.well-known/commerce.json</loc>" in body
    # no admin / auth-only URLs make it in
    assert "/admin" not in body
    assert "/v1/messages" not in body


def test_robots_txt_names_sitemap_and_new_crawlers():
    body = _client().get("/robots.txt").text
    assert "Sitemap:" in body
    assert "/sitemap.xml" in body
    # new crawlers whitelisted in v2.5.0
    for crawler in ("CCBot", "Applebot-Extended", "Meta-ExternalAgent"):
        assert crawler in body


def test_agents_registry_manifest_shape():
    r = _client().get("/.well-known/agents-registry.json")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Free Claude Code — Anthropic-compatible model gateway"
    assert body["version"] == "2.5.0"
    assert body["license"] == "MIT"
    cap_ids = {cap["id"] for cap in body["capabilities"]}
    assert {
        "anthropic.messages",
        "anthropic.count_tokens",
        "anthropic.models",
        "evoforge.policy",
    } <= cap_ids
    # evo stack is advertised to agents
    assert "evometaclaw" in body["evo_stack"]
    assert body["evo_stack"]["skillopt"]["enabled_env"] == "SKILLOPT_ENABLED"
    # commerce pointer present so adopting agents know where to look
    assert body["commerce"].endswith("/.well-known/commerce.json")


def test_commerce_manifest_lists_offers_with_intents():
    r = _client().get("/.well-known/commerce.json")
    assert r.status_code == 200
    body = r.json()
    assert body["@type"] == "OfferCatalog"
    offer_ids = {o["id"] for o in body["offers"]}
    assert "self-host" in offer_ids
    assert "hosted-gateway" in offer_ids
    assert "support" in offer_ids
    intents = {o["intent"] for o in body["offers"]}
    # agents driving GTM need exactly these three intents to triage.
    assert intents == {"adoption", "sales-qualified", "support-qualified"}
    # self-host is price=0, MIT — adoption lane
    self_host = next(o for o in body["offers"] if o["id"] == "self-host")
    assert self_host["price"] == 0.0
    assert self_host["currency"] == "USD"


def test_llms_full_txt_contains_json_ld_block():
    body = _client().get("/llms-full.txt").text
    # JSON-LD Service schema is embedded so structured-data extractors
    # (and LLMs with page-reader tools) can find offers and the API.
    assert '"@context": "https://schema.org"' in body
    assert '"@type": "WebAPI"' in body
    assert "ConsumeAction" in body


def test_llms_txt_calls_out_commercial_intents():
    body = _client().get("/llms.txt").text
    # the compact file points agents at commerce.json so GTM-adoption
    # agents can match a user's intent to the right offer
    assert "/.well-known/commerce.json" in body
    assert "Commercial intents" in body


def test_ai_plugin_manifest_links_commerce_and_registry():
    body = _client().get("/.well-known/ai-plugin.json").json()
    assert body["commerce_url"].endswith("/.well-known/commerce.json")
    assert body["agents_registry_url"].endswith("/.well-known/agents-registry.json")


def test_agents_manifest_lists_commerce_and_version():
    body = _client().get("/.well-known/agents.json").json()
    assert body["commerce"].endswith("/.well-known/commerce.json")
    assert body["registry"].endswith("/.well-known/agents-registry.json")
    assert body["sitemap"].endswith("/sitemap.xml")
    assert body["version"] == "2.5.0"
