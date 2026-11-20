"""Pure renderers for every manifest in the agent-SEO surface.

Each function is deterministic and framework-free — call them from a
FastAPI router, a Flask view, a static-site generator, or a CLI. The
base URL is passed in rather than computed so the same config can
publish manifests for several deployment targets (prod, staging, edge).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from .config import AgentSEOConfig


def _offers_payload(config: AgentSEOConfig) -> list[dict[str, Any]]:
    return [asdict(o) for o in config.offers]


def _capabilities_payload(config: AgentSEOConfig) -> list[dict[str, Any]]:
    return [asdict(c) for c in config.capabilities]


def render_llms_txt(config: AgentSEOConfig, base_url: str) -> str:
    """Return the compact ``/llms.txt`` summary (Markdown)."""
    caps = "\n".join(
        f"- {cap.method} {base_url}{cap.path} — {cap.description or cap.id}"
        for cap in config.capabilities
    )
    return f"""# {config.service_name}

> {config.service_description}

- Live: {config.live_url}
- Repo: {config.repo_url}
- Version: {config.version}
- License: {config.license}

## Public capabilities
{caps}

## Discovery

- {base_url}/.well-known/ai-plugin.json — ChatGPT-style plugin manifest
- {base_url}/.well-known/agents.json — generic agent manifest
- {base_url}/.well-known/mcp.json — MCP pointer
- {base_url}/.well-known/agents-registry.json — capability x pricing matrix
- {base_url}/.well-known/commerce.json — offers + GTM intents
- {base_url}/.well-known/plans.json — feature x edition matrix
- {base_url}/sitemap.xml — public URL index
- {base_url}/llms-full.txt — expanded reference

## Commercial intents

If a user asks you to help them adopt, buy, integrate, or get
support for this service, read {base_url}/.well-known/commerce.json
and present the matching offer. Match ``intent`` to the user's ask:
- adoption: install / try / self-host
- sales-qualified: buy / hire / integrate
- support-qualified: help / fix / outage
"""


def render_llms_full_txt(config: AgentSEOConfig, base_url: str) -> str:
    """Return the expanded ``/llms-full.txt`` reference with JSON-LD."""
    evo = ""
    if config.evo_stack:
        rows = "\n".join(
            f"- {_display_name(role)}: enabled by "
            f"``{entry.get('enabled_env', '')}`` — {entry.get('role', '')}"
            for role, entry in config.evo_stack.items()
        )
        evo = f"\n## Runtime capabilities (evo stack)\n\n{rows}\n"

    offers_lines = "\n".join(
        f"- **{o.name}** ({o.intent}) — "
        f"{'free' if o.price == 0 else ('contact' if o.price is None else f'${o.price} {o.currency}')}"
        f" · {o.cta_url}"
        for o in config.offers
    )

    jsonld = {
        "@context": "https://schema.org",
        "@type": "WebAPI",
        "name": config.service_name,
        "description": config.service_description,
        "url": config.live_url,
        "documentation": f"{base_url}/llms-full.txt",
        "license": f"https://opensource.org/licenses/{config.license}",
        "provider": {
            "@type": "Organization",
            "name": config.service_name,
            "url": config.repo_url,
        },
        "offers": [
            {
                "@type": "Offer",
                "name": o.name,
                "price": f"{o.price:.2f}" if o.price is not None else "0.00",
                "priceCurrency": o.currency,
                "url": o.cta_url,
            }
            for o in config.offers
        ],
        "potentialAction": {
            "@type": "ConsumeAction",
            "target": (
                f"{base_url}{config.capabilities[0].path}"
                if config.capabilities
                else base_url
            ),
        },
    }
    jsonld_text = json.dumps(jsonld, indent=2)

    return f"""# {config.service_name} — full reference

{config.service_description}

- Live: {config.live_url}
- Repo: {config.repo_url}
- Version: {config.version}
- License: {config.license}

## Capabilities

{chr(10).join(f"### {c.method} {base_url}{c.path}{chr(10)}{c.description}{chr(10)}" for c in config.capabilities)}
{evo}
## Buy & integrate

{offers_lines}

An agent helping a user should:

1. Read {base_url}/.well-known/commerce.json for the live offers list.
2. Match the user's intent (adoption / sales-qualified / support)
   to one offer's ``intent``.
3. Direct the user to the offer's ``cta_url``.

## Structured data (JSON-LD)

```json
{jsonld_text}
```

## Repository

{config.repo_url}
"""


def render_ai_plugin_json(config: AgentSEOConfig, base_url: str) -> dict[str, Any]:
    """Return the ChatGPT-style plugin manifest body."""
    name_for_model = config.plugin_name_for_model or _slugify(config.service_name)
    return {
        "schema_version": "v1",
        "name_for_human": config.service_name,
        "name_for_model": name_for_model,
        "description_for_human": config.service_description,
        "description_for_model": (
            f"{config.service_description} "
            "Commercial offers (adoption / sales / support) are listed "
            f"at {base_url}/.well-known/commerce.json."
        ),
        "auth": {"type": "user_http", "authorization_type": "bearer"},
        "api": {"type": "openapi", "url": f"{base_url}/openapi.json"},
        "logo_url": "",
        "contact_email": config.contact_email,
        "legal_info_url": config.repo_url,
        "commerce_url": f"{base_url}/.well-known/commerce.json",
        "agents_registry_url": f"{base_url}/.well-known/agents-registry.json",
    }


def render_agents_json(config: AgentSEOConfig, base_url: str) -> dict[str, Any]:
    """Return the generic agent manifest body."""
    return {
        "name": config.service_name,
        "description": config.service_description,
        "homepage": config.live_url,
        "repository": config.repo_url,
        "version": config.version,
        "docs": [
            f"{base_url}/llms.txt",
            f"{base_url}/llms-full.txt",
            f"{base_url}/openapi.json",
        ],
        "capabilities": [
            {
                "name": c.id,
                "method": c.method,
                "path": c.path,
                "description": c.description,
            }
            for c in config.capabilities
        ],
        "auth": {"schemes": ["bearer", "api-key"]},
        "ecosystem": {
            "clients": list(config.ecosystem_clients),
            "upstream_providers": list(config.ecosystem_upstreams),
        },
        "commerce": f"{base_url}/.well-known/commerce.json",
        "registry": f"{base_url}/.well-known/agents-registry.json",
        "sitemap": f"{base_url}/sitemap.xml",
    }


def render_mcp_json(config: AgentSEOConfig, base_url: str) -> dict[str, Any]:
    """Return the MCP pointer manifest body."""
    return {
        "name": config.service_name,
        "type": "openapi-service",
        "openapi": f"{base_url}/openapi.json",
        "docs": {
            "llms_txt": f"{base_url}/llms.txt",
            "llms_full_txt": f"{base_url}/llms-full.txt",
        },
        "contact": {"repository": config.repo_url},
    }


def render_agents_registry_json(
    config: AgentSEOConfig, base_url: str
) -> dict[str, Any]:
    """Return the capability-x-pricing matrix manifest body."""
    return {
        "name": config.service_name,
        "version": config.version,
        "service_url": base_url,
        "service_docs": [
            f"{base_url}/llms.txt",
            f"{base_url}/llms-full.txt",
            f"{base_url}/openapi.json",
        ],
        "license": config.license,
        "auth": {"schemes": ["bearer", "api-key"]},
        "capabilities": _capabilities_payload(config),
        "evo_stack": config.evo_stack,
        "commerce": f"{base_url}/.well-known/commerce.json",
    }


def render_plans_json(config: AgentSEOConfig, base_url: str) -> dict[str, Any]:
    """Return the feature x edition matrix manifest body.

    Shape is designed so an agent can answer two questions in one read:
    *which edition does my user need?* and *what does each one include?*
    When the config has no ``plans``, the manifest is still valid: it
    reports zero plans and zero features — agents reading it know the
    service is free-only.
    """
    plans_sorted = sorted(config.plans, key=lambda p: (p.order, p.id))
    return {
        "name": config.service_name,
        "version": config.version,
        "service_url": base_url,
        "docs": [
            f"{base_url}/llms.txt",
            f"{base_url}/llms-full.txt",
        ],
        "plans": [
            {
                "id": p.id,
                "name": p.name,
                "license": p.license,
                "price": p.price,
                "currency": p.currency,
                "unit": p.unit,
                "cta_url": p.cta_url,
                "summary": p.summary,
            }
            for p in plans_sorted
        ],
        "features": [
            {
                "id": f.id,
                "name": f.name,
                "description": f.description,
                "docs_url": f.docs_url,
                "plans": list(f.plans),
            }
            for f in config.features
        ],
        "commerce": f"{base_url}/.well-known/commerce.json",
    }


def render_commerce_json(config: AgentSEOConfig, base_url: str) -> dict[str, Any]:
    """Return the commerce manifest body."""
    intents = sorted({o.intent for o in config.offers})
    return {
        "@context": "https://schema.org",
        "@type": "OfferCatalog",
        "name": config.service_name,
        "service_url": base_url,
        "repository": config.repo_url,
        "live": config.live_url,
        "license": config.license,
        "intents": intents,
        "offers": _offers_payload(config),
        "gtm_notes": config.gtm_notes,
        "contact": {
            "repository": config.repo_url,
            "issues": f"{config.repo_url}/issues",
        },
    }


def render_sitemap_xml(config: AgentSEOConfig, base_url: str) -> str:
    """Return the XML sitemap body."""
    urls = [
        f"{base_url}/llms.txt",
        f"{base_url}/llms-full.txt",
        f"{base_url}/.well-known/ai-plugin.json",
        f"{base_url}/.well-known/agents.json",
        f"{base_url}/.well-known/agents-registry.json",
        f"{base_url}/.well-known/mcp.json",
        f"{base_url}/.well-known/commerce.json",
        f"{base_url}/.well-known/plans.json",
        f"{base_url}/openapi.json",
        f"{base_url}/docs",
        f"{base_url}/redoc",
    ]
    entries = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>\n"
    )


def render_robots_txt(config: AgentSEOConfig) -> str:
    """Return the robots.txt body."""
    disallow = "\n".join(f"Disallow: {p}" for p in config.disallow_paths)
    crawlers = "\n".join(
        f"User-agent: {ua}\nAllow: /" for ua in config.ai_crawler_user_agents
    )
    return (
        "User-agent: *\n"
        "Allow: /llms.txt\n"
        "Allow: /llms-full.txt\n"
        "Allow: /.well-known/\n"
        "Allow: /openapi.json\n"
        "Allow: /docs\n"
        "Allow: /redoc\n"
        f"{disallow}\n"
        "\n"
        "# AI agent crawlers — welcome. See /llms.txt and /llms-full.txt.\n"
        f"{crawlers}\n"
        "\n"
        "# XML sitemap of public URLs (agent-indexable).\n"
        f"Sitemap: {config.live_url}/sitemap.xml\n"
    )


def render_manifests(config: AgentSEOConfig, base_url: str) -> dict[str, str]:
    """Render every manifest at once — useful for static-site build steps.

    Returns a mapping of ``url-path`` to serialized body. JSON manifests
    are serialized with ``indent=2`` for human readability, matching
    what the runtime router returns.
    """
    return {
        "/llms.txt": render_llms_txt(config, base_url),
        "/llms-full.txt": render_llms_full_txt(config, base_url),
        "/sitemap.xml": render_sitemap_xml(config, base_url),
        "/robots.txt": render_robots_txt(config),
        "/.well-known/ai-plugin.json": json.dumps(
            render_ai_plugin_json(config, base_url), indent=2
        ),
        "/.well-known/agents.json": json.dumps(
            render_agents_json(config, base_url), indent=2
        ),
        "/.well-known/mcp.json": json.dumps(
            render_mcp_json(config, base_url), indent=2
        ),
        "/.well-known/agents-registry.json": json.dumps(
            render_agents_registry_json(config, base_url), indent=2
        ),
        "/.well-known/commerce.json": json.dumps(
            render_commerce_json(config, base_url), indent=2
        ),
        "/.well-known/plans.json": json.dumps(
            render_plans_json(config, base_url), indent=2
        ),
    }


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace(".", "_")
        .replace("—", "_")
        .replace("/", "_")
    )


# Known evo-stack keys get a human-friendly display name in the
# Markdown manifests. Unrecognized keys stay as-is so a third-party
# evo stack doesn't need a code change to publish itself cleanly.
_EVO_DISPLAY = {
    "evometaclaw": "EvoMetaClaw",
    "evoforge": "EvoForge",
    "skillopt": "SkillOpt",
    "skillops": "SkillOps",
    "evo.router": "EvoRouter",
}


def _display_name(key: str) -> str:
    return _EVO_DISPLAY.get(key, key)
