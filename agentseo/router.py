"""FastAPI router factory for the agent-SEO surface.

Keeps the FastAPI import local so the rest of the package stays
framework-free. Everything here is a thin wrapper around the pure
renderers in :mod:`agentseo.manifests`.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from . import manifests
from .config import AgentSEOConfig


def _base_url(request: Request) -> str:
    """Public base URL honoring proxy headers."""
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get(
        "host"
    )
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    if forwarded_host:
        return f"{scheme}://{forwarded_host}"
    return str(request.base_url).rstrip("/")


def build_router(config: AgentSEOConfig) -> APIRouter:
    """Return an ``APIRouter`` serving every agent-SEO endpoint.

    Mount it on your FastAPI app::

        app.include_router(build_router(my_config))
    """
    router = APIRouter(include_in_schema=False)

    @router.get("/llms.txt")
    async def llms_txt(request: Request) -> PlainTextResponse:
        body = manifests.render_llms_txt(config, _base_url(request))
        return PlainTextResponse(body, media_type="text/plain; charset=utf-8")

    @router.get("/llms-full.txt")
    async def llms_full_txt(request: Request) -> PlainTextResponse:
        body = manifests.render_llms_full_txt(config, _base_url(request))
        return PlainTextResponse(body, media_type="text/plain; charset=utf-8")

    @router.get("/sitemap.xml")
    async def sitemap_xml(request: Request) -> Response:
        body = manifests.render_sitemap_xml(config, _base_url(request))
        return Response(content=body, media_type="application/xml; charset=utf-8")

    @router.get("/robots.txt")
    async def robots_txt() -> PlainTextResponse:
        return PlainTextResponse(
            manifests.render_robots_txt(config),
            media_type="text/plain; charset=utf-8",
        )

    @router.get("/.well-known/ai-plugin.json")
    async def ai_plugin(request: Request) -> JSONResponse:
        return JSONResponse(manifests.render_ai_plugin_json(config, _base_url(request)))

    @router.get("/.well-known/agents.json")
    async def agents_manifest(request: Request) -> JSONResponse:
        return JSONResponse(manifests.render_agents_json(config, _base_url(request)))

    @router.get("/.well-known/mcp.json")
    async def mcp_manifest(request: Request) -> JSONResponse:
        return JSONResponse(manifests.render_mcp_json(config, _base_url(request)))

    @router.get("/.well-known/agents-registry.json")
    async def agents_registry(request: Request) -> JSONResponse:
        return JSONResponse(
            manifests.render_agents_registry_json(config, _base_url(request))
        )

    @router.get("/.well-known/commerce.json")
    async def commerce(request: Request) -> JSONResponse:
        return JSONResponse(manifests.render_commerce_json(config, _base_url(request)))

    @router.get("/.well-known/plans.json")
    async def plans(request: Request) -> JSONResponse:
        return JSONResponse(manifests.render_plans_json(config, _base_url(request)))

    return router
