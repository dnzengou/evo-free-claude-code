"""agentseo — AI-agent-detectable SEO toolkit.

Bolt-on package that publishes a complete discovery surface for any
HTTP service so AI agents (Claude, ChatGPT, Perplexity, Gemini,
generic LLM runtimes) can find it, reason about its capabilities,
match a user's commercial intent to an offer, and call it — without a
human in the loop.

Two ways to use it:

1. Mounted on a FastAPI app::

    from fastapi import FastAPI
    from agentseo import AgentSEOConfig, Offer, Capability, build_router

    config = AgentSEOConfig(
        service_name="My Service",
        service_description="One sentence an LLM will quote.",
        repo_url="https://github.com/me/myservice",
        live_url="https://myservice.example.com",
        capabilities=[Capability(id="my.api", path="/v1/do", method="POST")],
        offers=[Offer(id="self-host", name="Open source", price=0.0,
                     intent="adoption", cta_url="https://github.com/me/myservice")],
    )
    app = FastAPI()
    app.include_router(build_router(config))

2. Rendered as static files (for Jekyll, Hugo, Next.js, a CDN,
   or any non-Python site)::

    python -m agentseo.cli --config agentseo.toml --out ./public

The config is a plain dataclass — serialize it with ``json.dumps`` or
load from any format. No framework dependency beyond the optional
``build_router`` helper. No single point of failure.
"""

from .config import AgentSEOConfig, Capability, Feature, Offer, Plan
from .manifests import (
    render_agents_json,
    render_agents_registry_json,
    render_ai_plugin_json,
    render_commerce_json,
    render_llms_full_txt,
    render_llms_txt,
    render_manifests,
    render_mcp_json,
    render_plans_json,
    render_robots_txt,
    render_sitemap_xml,
)

__all__ = [
    "AgentSEOConfig",
    "Capability",
    "Feature",
    "Offer",
    "Plan",
    "build_router",
    "render_agents_json",
    "render_agents_registry_json",
    "render_ai_plugin_json",
    "render_commerce_json",
    "render_llms_full_txt",
    "render_llms_txt",
    "render_manifests",
    "render_mcp_json",
    "render_plans_json",
    "render_robots_txt",
    "render_sitemap_xml",
]


def build_router(config: AgentSEOConfig):
    """Return a FastAPI ``APIRouter`` serving the discovery surface.

    Imported lazily so the package stays usable in environments that
    don't have FastAPI installed (e.g. the CLI renderer).
    """
    from .router import build_router as _build

    return _build(config)


__version__ = "0.1.0"
