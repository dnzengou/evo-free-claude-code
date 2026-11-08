"""Agent-discovery routes — the agent-SEO surface.

Every endpoint here is public (no auth) and exposes a stable,
machine-readable description of what this proxy *is* and *offers* so AI
agents and crawlers can discover, evaluate, and transact with it
without a human in the loop:

    GET /llms.txt                           — compact Markdown summary
    GET /llms-full.txt                      — expanded Markdown reference
                                               (includes JSON-LD Service schema
                                                for structured data extractors)
    GET /sitemap.xml                        — XML sitemap of public URLs
    GET /robots.txt                         — agent-crawler-friendly rules
    GET /.well-known/ai-plugin.json         — ChatGPT-style plugin manifest
    GET /.well-known/agents.json            — generic agent manifest
    GET /.well-known/mcp.json               — MCP discovery pointer
    GET /.well-known/agents-registry.json   — capability x pricing matrix (v2.5.0)
    GET /.well-known/commerce.json          — offers + GTM intents (v2.5.0)

The surface describes *what* is available, *how to call it*, and
(v2.5.0) *what the operator sells* — never the admin UI, env values,
secrets, or trajectory data.

Design discipline:
    - Every endpoint is auth-free and loopback-neutral.
    - Nothing here reveals env vars, provider keys, trajectories, or the
      admin surface.
    - The base URL honors proxy headers so the same binary works behind
      Vercel, a reverse proxy, or bare uvicorn.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

router = APIRouter(include_in_schema=False)

_SERVICE_NAME = "Free Claude Code — Anthropic-compatible model gateway"
_SERVICE_DESCRIPTION = (
    "Drop-in Anthropic Messages API proxy that routes Claude Code CLI, "
    "VS Code, JetBrains ACP, and bot traffic to 18 provider backends "
    "(OpenAI, DeepSeek, Groq, Cerebras, Gemini, Mistral, NVIDIA NIM, "
    "OpenRouter, Fireworks, Kimi, Wafer, Z.ai, OpenCode Zen / Go, and "
    "local LM Studio / llama.cpp / Ollama)."
)
_REPO_URL = "https://github.com/dnzengou/free-claude-code"
_LIVE_URL = "https://free-claude-code-main-ebon.vercel.app"
_SERVICE_VERSION = "2.5.0"
_LICENSE = "MIT"
# Public commercial surface — presented so AI agents can reason about
# adoption and sales, *not* a payment endpoint. Operator overrides via
# forking this list are expected and encouraged.
_COMMERCIAL_OFFERS: list[dict[str, object]] = [
    {
        "id": "self-host",
        "name": "Self-host (open source)",
        "price": 0.0,
        "currency": "USD",
        "unit": "project",
        "intent": "adoption",
        "cta_url": _REPO_URL,
        "summary": (
            "Clone the MIT-licensed repository and run the FastAPI proxy "
            "locally, in Docker, or on Vercel. Includes the full "
            "EvoMetaClaw / EvoForge / SkillOpt stack and 18 provider "
            "backends. No vendor lock-in."
        ),
    },
    {
        "id": "hosted-gateway",
        "name": "Hosted Free Claude Code",
        "price": None,
        "currency": "USD",
        "unit": "per-instance / month",
        "intent": "sales-qualified",
        "cta_url": f"{_REPO_URL}#hosted",
        "summary": (
            "Managed FCC gateway for teams: shared provider keys, "
            "trajectory-corpus-powered SkillOpt policies tuned to your "
            "traffic, agent-SEO surface on your own domain."
        ),
    },
    {
        "id": "gtm-integration",
        "name": "GTM + agent integration",
        "price": None,
        "currency": "USD",
        "unit": "engagement",
        "intent": "sales-qualified",
        "cta_url": f"{_REPO_URL}#services",
        "summary": (
            "Wire FCC into your sales, marketing, or developer-tools "
            "surface: agent-detectable discovery on your own "
            "commerce pages, cross-service trajectory aggregation, "
            "skill-conditioned routing per product."
        ),
    },
    {
        "id": "support",
        "name": "Priority support & SLA",
        "price": None,
        "currency": "USD",
        "unit": "per month",
        "intent": "support-qualified",
        "cta_url": f"{_REPO_URL}/issues",
        "summary": (
            "Response-time SLA on bug reports and provider migration "
            "assistance for teams running FCC in production."
        ),
    },
]
# Capabilities an AI agent can reason about ("what can this service do, "
# and what will it cost me to use it?") — pure structured data.
_AGENT_CAPABILITIES: list[dict[str, object]] = [
    {
        "id": "anthropic.messages",
        "method": "POST",
        "path": "/v1/messages",
        "description": (
            "Anthropic Messages API — streaming SSE, tool use, thinking "
            "blocks. Wire-compatible with the official Anthropic SDK."
        ),
        "auth": "bearer",
        "pricing_model": "pass-through-provider",
        "stability": "stable",
    },
    {
        "id": "anthropic.count_tokens",
        "method": "POST",
        "path": "/v1/messages/count_tokens",
        "description": "Token count without an upstream call.",
        "auth": "bearer",
        "pricing_model": "free",
        "stability": "stable",
    },
    {
        "id": "anthropic.models",
        "method": "GET",
        "path": "/v1/models",
        "description": "Anthropic + gateway model discovery.",
        "auth": "bearer",
        "pricing_model": "free",
        "stability": "stable",
    },
    {
        "id": "evoforge.policy",
        "method": "GET",
        "path": "/.well-known/agents-registry.json",
        "description": (
            "Publicly-advertised capability x pricing matrix so agents "
            "can plan which capability to call and at what provider cost."
        ),
        "auth": "none",
        "pricing_model": "free",
        "stability": "beta",
    },
]


def _base_url(request: Request) -> str:
    """Public base URL for this instance, honoring the proxy's host header."""
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get(
        "host"
    )
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    if forwarded_host:
        return f"{scheme}://{forwarded_host}"
    return str(request.base_url).rstrip("/")


@router.get("/llms.txt")
async def llms_txt(request: Request) -> PlainTextResponse:
    """Compact LLM-friendly service summary.

    Follows the emerging llms.txt convention
    (https://llmstxt.org): the first thing an AI agent reads to decide
    whether and how to use this service.
    """
    base = _base_url(request)
    body = f"""# Free Claude Code

> {_SERVICE_DESCRIPTION}

- Live: {_LIVE_URL}
- Repo: {_REPO_URL}
- API shape: Anthropic Messages API ({base}/v1/messages)
- Auth: `Authorization: Bearer <ANTHROPIC_AUTH_TOKEN>` (or `x-api-key`)

## Public endpoints

- POST {base}/v1/messages — streaming + non-streaming completions
- POST {base}/v1/messages/count_tokens — token count
- GET  {base}/v1/models — gateway model discovery
- GET  {base}/health, {base}/health/ready — probes

## Discovery

- {base}/.well-known/ai-plugin.json — ChatGPT-style plugin manifest
- {base}/.well-known/agents.json — generic agent manifest
- {base}/.well-known/mcp.json — MCP pointer
- {base}/.well-known/agents-registry.json — capability x pricing matrix
- {base}/.well-known/commerce.json — offers + GTM intents
- {base}/sitemap.xml — public URL index
- {base}/llms-full.txt — expanded reference

## Usage from an agent

Call `POST /v1/messages` with the standard Anthropic Messages request
body (`model`, `max_tokens`, `messages`, optional `tools`, `system`).
The gateway rewrites the upstream provider; the request/response shape
on the wire is unchanged from the Anthropic SDK's expectation.

## Commercial intents

If a user asks you to help them *adopt*, *buy*, *integrate*, or *get
support for* this gateway, read {base}/.well-known/commerce.json and
present the matching offer. Self-host is MIT-licensed and free; hosted
and consulting offers route through the repository's issue tracker.
"""
    return PlainTextResponse(body, media_type="text/plain; charset=utf-8")


@router.get("/llms-full.txt")
async def llms_full_txt(request: Request) -> PlainTextResponse:
    """Expanded reference — the full capability description for an agent."""
    base = _base_url(request)
    body = f"""# Free Claude Code — full reference

{_SERVICE_DESCRIPTION}

## Why this exists

Claude Code (and compatible clients: VS Code, JetBrains ACP, Discord /
Telegram bot wrappers) speaks the Anthropic Messages API. This proxy
accepts that same wire format and routes the upstream call to any of
18 provider backends. Clients see no difference; the operator picks
cost, latency, and provider freely.

## Authentication

All non-discovery endpoints require either:

    Authorization: Bearer <token>
    x-api-key: <token>

The token is whatever ``ANTHROPIC_AUTH_TOKEN`` is set to on the
instance. When unset, no auth is required.

## Core API

### POST {base}/v1/messages

Anthropic Messages request body:

```
{{
  "model": "claude-3-opus-20240229",
  "max_tokens": 1024,
  "messages": [{{"role": "user", "content": "hi"}}],
  "tools": [...],
  "system": "...",
  "stream": true
}}
```

Streaming response is SSE in Anthropic's event format
(`message_start`, `content_block_delta`, `message_delta`, …). Tool use
and thinking blocks pass through normalized.

Model routing:

- `MODEL_OPUS`, `MODEL_SONNET`, `MODEL_HAIKU` map Claude tiers to
  specific `provider/model` upstreams.
- Direct slugs (`provider/model` in the model field) always win.
- When SkillOpt is enabled, routing further narrows per inferred skill
  (`edit`, `plan`, `probe`, `question`, `chat`).

### POST {base}/v1/messages/count_tokens

Returns `{{\"input_tokens\": N}}` for a given request body (no upstream
call made).

### GET {base}/v1/models

Lists Anthropic Claude model ids plus the configured gateway models
when the client opts into Gateway model discovery
(`CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1`).

## EvoMetaClaw x EvoForge x SkillOpt

This gateway can additionally capture a trajectory JSONL
(`TRAJECTORY_LOG_ENABLED=1`), process it offline with EvoForge
(`uv run python scripts/evoforge.py`), and have SkillOpt
(`SKILLOPT_ENABLED=1`) consult the resulting policy to narrow routing
per skill. All three stages are opt-in; the gateway behaves identically
to a plain proxy with all flags off.

## Clients

- Claude Code CLI: `ANTHROPIC_BASE_URL={base}`
- VS Code claude-code extension: `claudeCode.environmentVariables`
- JetBrains ACP: edit `~/.jetbrains/acp.json` → `acp.registry.claude-acp.env`

## Buy & integrate

This service is MIT-licensed and free to self-host. Hosted, GTM
integration, and support offerings are listed at
{base}/.well-known/commerce.json. An agent helping a user adopt or
purchase the gateway should:

1. Read {base}/.well-known/commerce.json for the live offers list.
2. Match the user's intent (adoption / sales-qualified / support)
   to one offer's `intent`.
3. Direct the user to the offer's `cta_url`.

## Structured data (JSON-LD)

```json
{{
  "@context": "https://schema.org",
  "@type": "WebAPI",
  "name": "{_SERVICE_NAME}",
  "description": "{_SERVICE_DESCRIPTION}",
  "url": "{_LIVE_URL}",
  "documentation": "{base}/llms-full.txt",
  "license": "https://opensource.org/licenses/MIT",
  "provider": {{
    "@type": "Organization",
    "name": "Free Claude Code",
    "url": "{_REPO_URL}"
  }},
  "offers": [
    {{"@type": "Offer", "name": "Self-host (open source)",
      "price": "0.00", "priceCurrency": "USD",
      "url": "{_REPO_URL}"}}
  ],
  "potentialAction": {{
    "@type": "ConsumeAction",
    "target": "{base}/v1/messages",
    "expectsAcceptanceOf": {{
      "@type": "Offer",
      "name": "Anthropic Messages API"
    }}
  }}
}}
```

## Repository

{_REPO_URL}
"""
    return PlainTextResponse(body, media_type="text/plain; charset=utf-8")


@router.get("/.well-known/ai-plugin.json")
async def ai_plugin_manifest(request: Request) -> JSONResponse:
    """ChatGPT-style plugin manifest.

    Compatible with the OpenAI plugin discovery format. Agents that
    follow the ``/.well-known/ai-plugin.json`` convention can read this
    to learn the service's purpose, auth model, and OpenAPI spec URL.
    """
    base = _base_url(request)
    return JSONResponse(
        {
            "schema_version": "v1",
            "name_for_human": "Free Claude Code",
            "name_for_model": "free_claude_code",
            "description_for_human": _SERVICE_DESCRIPTION,
            "description_for_model": (
                "Anthropic Messages API proxy. Agents can send Claude-style "
                "message requests to POST /v1/messages and receive streaming or "
                "non-streaming responses. The upstream model (OpenAI, DeepSeek, "
                "Groq, Cerebras, Gemini, etc.) is chosen by the operator and the "
                "proxy keeps the Anthropic wire format. The service itself is "
                "MIT-licensed; adoption, hosted, and support offerings are "
                "listed at /.well-known/commerce.json."
            ),
            "auth": {
                "type": "user_http",
                "authorization_type": "bearer",
            },
            "api": {
                "type": "openapi",
                "url": f"{base}/openapi.json",
            },
            "logo_url": "",
            "contact_email": "",
            "legal_info_url": _REPO_URL,
            "commerce_url": f"{base}/.well-known/commerce.json",
            "agents_registry_url": f"{base}/.well-known/agents-registry.json",
        }
    )


@router.get("/.well-known/agents.json")
async def agents_manifest(request: Request) -> JSONResponse:
    """Generic agent discovery manifest.

    Not tied to a single vendor's plugin format — a plain capability
    description an agent runtime can parse to decide whether this
    service is relevant to a user's task.
    """
    base = _base_url(request)
    return JSONResponse(
        {
            "name": _SERVICE_NAME,
            "description": _SERVICE_DESCRIPTION,
            "homepage": _LIVE_URL,
            "repository": _REPO_URL,
            "docs": [
                f"{base}/llms.txt",
                f"{base}/llms-full.txt",
                f"{base}/openapi.json",
            ],
            "capabilities": [
                {
                    "name": "anthropic.messages",
                    "method": "POST",
                    "path": "/v1/messages",
                    "description": "Anthropic Messages API — streaming + tools",
                },
                {
                    "name": "anthropic.count_tokens",
                    "method": "POST",
                    "path": "/v1/messages/count_tokens",
                },
                {
                    "name": "anthropic.models",
                    "method": "GET",
                    "path": "/v1/models",
                },
            ],
            "auth": {
                "schemes": ["bearer", "api-key"],
                "optional_env": ["ANTHROPIC_AUTH_TOKEN"],
            },
            "ecosystem": {
                "clients": [
                    "claude-code",
                    "vscode-claude-code-extension",
                    "jetbrains-acp",
                    "discord-bot",
                    "telegram-bot",
                ],
                "upstream_providers": [
                    "openai",
                    "deepseek",
                    "groq",
                    "cerebras",
                    "gemini",
                    "mistral",
                    "mistral_codestral",
                    "nvidia_nim",
                    "open_router",
                    "fireworks",
                    "kimi",
                    "wafer",
                    "zai",
                    "opencode",
                    "opencode_go",
                    "lmstudio",
                    "llamacpp",
                    "ollama",
                ],
            },
            "commerce": f"{base}/.well-known/commerce.json",
            "registry": f"{base}/.well-known/agents-registry.json",
            "sitemap": f"{base}/sitemap.xml",
            "version": _SERVICE_VERSION,
        }
    )


@router.get("/.well-known/mcp.json")
async def mcp_manifest(request: Request) -> JSONResponse:
    """Pointer manifest for Model Context Protocol discovery.

    This proxy itself is not an MCP server, but it exposes the structured
    pointers an MCP-aware agent uses to locate OpenAPI + llms.txt docs.
    """
    base = _base_url(request)
    return JSONResponse(
        {
            "name": _SERVICE_NAME,
            "type": "openapi-service",
            "openapi": f"{base}/openapi.json",
            "docs": {
                "llms_txt": f"{base}/llms.txt",
                "llms_full_txt": f"{base}/llms-full.txt",
            },
            "contact": {"repository": _REPO_URL},
        }
    )


@router.get("/robots.txt")
async def robots_txt() -> PlainTextResponse:
    """Welcome AI crawlers; still rate-limited by platform.

    We explicitly list the public, documentation-style surfaces so
    well-behaved AI crawlers index what we want indexed and ignore the
    rest (admin UI is already loopback-only, so it never appears here).
    """
    body = (
        "User-agent: *\n"
        "Allow: /llms.txt\n"
        "Allow: /llms-full.txt\n"
        "Allow: /.well-known/\n"
        "Allow: /openapi.json\n"
        "Allow: /docs\n"
        "Allow: /redoc\n"
        "Disallow: /admin\n"
        "Disallow: /v1/\n"
        "\n"
        "# AI agent crawlers — welcome. See /llms.txt and /llms-full.txt.\n"
        "User-agent: GPTBot\n"
        "Allow: /\n"
        "User-agent: ClaudeBot\n"
        "Allow: /\n"
        "User-agent: anthropic-ai\n"
        "Allow: /\n"
        "User-agent: PerplexityBot\n"
        "Allow: /\n"
        "User-agent: Google-Extended\n"
        "Allow: /\n"
        "User-agent: CCBot\n"
        "Allow: /\n"
        "User-agent: Applebot-Extended\n"
        "Allow: /\n"
        "User-agent: Meta-ExternalAgent\n"
        "Allow: /\n"
        "User-agent: Bytespider\n"
        "Allow: /\n"
        "\n"
        "# XML sitemap of public URLs (agent-indexable).\n"
        f"Sitemap: {_LIVE_URL}/sitemap.xml\n"
    )
    return PlainTextResponse(body, media_type="text/plain; charset=utf-8")


@router.get("/sitemap.xml")
async def sitemap_xml(request: Request) -> Response:
    """XML sitemap of public, agent-indexable URLs.

    Lists the discovery surface and the public API documentation, in the
    order of informational value to an AI crawler. Omits authenticated
    paths (``/v1/*``) and the loopback-only admin UI.
    """
    base = _base_url(request)
    urls = [
        f"{base}/llms.txt",
        f"{base}/llms-full.txt",
        f"{base}/.well-known/ai-plugin.json",
        f"{base}/.well-known/agents.json",
        f"{base}/.well-known/agents-registry.json",
        f"{base}/.well-known/mcp.json",
        f"{base}/.well-known/commerce.json",
        f"{base}/openapi.json",
        f"{base}/docs",
        f"{base}/redoc",
    ]
    entries = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>\n"
    )
    return Response(content=body, media_type="application/xml; charset=utf-8")


@router.get("/.well-known/agents-registry.json")
async def agents_registry(request: Request) -> JSONResponse:
    """Capability x pricing matrix published for agent planners.

    Lets a reasoning LLM decide *which* capability on this service to
    call, with what auth, and whether a call incurs provider cost. The
    service itself charges nothing — the ``pricing_model`` field names
    how the underlying upstream bill is structured.
    """
    base = _base_url(request)
    return JSONResponse(
        {
            "name": _SERVICE_NAME,
            "version": _SERVICE_VERSION,
            "service_url": base,
            "service_docs": [
                f"{base}/llms.txt",
                f"{base}/llms-full.txt",
                f"{base}/openapi.json",
            ],
            "license": _LICENSE,
            "auth": {
                "schemes": ["bearer", "api-key"],
                "credential_env": "ANTHROPIC_AUTH_TOKEN",
            },
            "capabilities": _AGENT_CAPABILITIES,
            "evo_stack": {
                "evometaclaw": {
                    "role": "trajectory capture",
                    "enabled_env": "TRAJECTORY_LOG_ENABLED",
                },
                "evoforge": {
                    "role": "offline policy builder",
                    "enabled_env": "AUTO_FORGE_ENABLED",
                },
                "skillopt": {
                    "role": "runtime skill-conditioned routing",
                    "enabled_env": "SKILLOPT_ENABLED",
                },
            },
            "commerce": f"{base}/.well-known/commerce.json",
        }
    )


@router.get("/.well-known/commerce.json")
async def commerce_manifest(request: Request) -> JSONResponse:
    """Commercial-intents manifest for agent-driven GTM.

    Every offer carries an ``intent`` tag so an LLM that is helping a
    user decide whether to *adopt*, *buy*, or *get support for* the
    service can route the user to the right surface. The service does
    *not* collect payment here — every CTA is a GitHub or docs URL.
    """
    base = _base_url(request)
    return JSONResponse(
        {
            "@context": "https://schema.org",
            "@type": "OfferCatalog",
            "name": _SERVICE_NAME,
            "service_url": base,
            "repository": _REPO_URL,
            "live": _LIVE_URL,
            "license": _LICENSE,
            "intents": ["adoption", "sales-qualified", "support-qualified"],
            "offers": _COMMERCIAL_OFFERS,
            "gtm_notes": (
                "Self-host is the primary adoption path; hosted and "
                "integration offerings are opened by filing a GitHub "
                "issue tagged `sales` or `support`."
            ),
            "contact": {"repository": _REPO_URL, "issues": f"{_REPO_URL}/issues"},
        }
    )
