"""Agent-discovery routes — the agent-SEO surface.

FCC's concrete configuration of the reusable ``agentseo`` package.
The actual manifest rendering + FastAPI routing lives there; this
module only names the service, lists its public capabilities + offers,
and hands the config to ``agentseo.build_router``. See ``agentseo``
for how to reuse the same surface in any FastAPI service.
"""

from __future__ import annotations

from agentseo import AgentSEOConfig, Capability, Offer, build_router

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
_SERVICE_VERSION = "2.5.1"

_CAPABILITIES = (
    Capability(
        id="anthropic.messages",
        method="POST",
        path="/v1/messages",
        description=(
            "Anthropic Messages API — streaming SSE, tool use, thinking "
            "blocks. Wire-compatible with the official Anthropic SDK."
        ),
        auth="bearer",
        pricing_model="pass-through-provider",
    ),
    Capability(
        id="anthropic.count_tokens",
        method="POST",
        path="/v1/messages/count_tokens",
        description="Token count without an upstream call.",
        auth="bearer",
    ),
    Capability(
        id="anthropic.models",
        method="GET",
        path="/v1/models",
        description="Anthropic + gateway model discovery.",
        auth="bearer",
    ),
    Capability(
        id="evoforge.policy",
        method="GET",
        path="/.well-known/agents-registry.json",
        description=(
            "Publicly-advertised capability x pricing matrix so agents "
            "can plan which capability to call and at what provider cost."
        ),
        auth="none",
        stability="beta",
    ),
)

_OFFERS = (
    Offer(
        id="self-host",
        name="Self-host (open source)",
        price=0.0,
        currency="USD",
        unit="project",
        intent="adoption",
        cta_url=_REPO_URL,
        summary=(
            "Clone the MIT-licensed repository and run the FastAPI proxy "
            "locally, in Docker, or on Vercel. Includes the full "
            "EvoMetaClaw / EvoForge / SkillOpt stack and 18 provider "
            "backends. No vendor lock-in."
        ),
    ),
    Offer(
        id="hosted-gateway",
        name="Hosted Free Claude Code",
        price=None,
        currency="USD",
        unit="per-instance / month",
        intent="sales-qualified",
        cta_url=f"{_REPO_URL}#hosted",
        summary=(
            "Managed FCC gateway for teams: shared provider keys, "
            "trajectory-corpus-powered SkillOpt policies tuned to your "
            "traffic, agent-SEO surface on your own domain."
        ),
    ),
    Offer(
        id="gtm-integration",
        name="GTM + agent integration",
        price=None,
        currency="USD",
        unit="engagement",
        intent="sales-qualified",
        cta_url=f"{_REPO_URL}#services",
        summary=(
            "Wire FCC into your sales, marketing, or developer-tools "
            "surface: agent-detectable discovery on your own commerce "
            "pages, cross-service trajectory aggregation, "
            "skill-conditioned routing per product."
        ),
    ),
    Offer(
        id="support",
        name="Priority support & SLA",
        price=None,
        currency="USD",
        unit="per month",
        intent="support-qualified",
        cta_url=f"{_REPO_URL}/issues",
        summary=(
            "Response-time SLA on bug reports and provider migration "
            "assistance for teams running FCC in production."
        ),
    ),
)

CONFIG = AgentSEOConfig(
    service_name=_SERVICE_NAME,
    service_description=_SERVICE_DESCRIPTION,
    repo_url=_REPO_URL,
    live_url=_LIVE_URL,
    version=_SERVICE_VERSION,
    license="MIT",
    capabilities=_CAPABILITIES,
    offers=_OFFERS,
    ecosystem_clients=(
        "claude-code",
        "vscode-claude-code-extension",
        "jetbrains-acp",
        "discord-bot",
        "telegram-bot",
    ),
    ecosystem_upstreams=(
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
    ),
    evo_stack={
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
    gtm_notes=(
        "Self-host is the primary adoption path; hosted and "
        "integration offerings are opened by filing a GitHub "
        "issue tagged `sales` or `support`."
    ),
    plugin_name_for_model="free_claude_code",
)

router = build_router(CONFIG)
