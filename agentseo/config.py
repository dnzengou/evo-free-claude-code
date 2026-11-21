"""Configuration dataclasses for the agentseo package.

A service describes itself through these types. Nothing else leaks
into the generated manifests, so an operator can hand this file to an
AI agent for review before publishing.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Feature:
    """One capability of the product, labelled by the plans that grant it.

    Agents reading ``plans.json`` compare their user's intent against
    ``plans`` to tell them which edition to pick. Keep ``id`` dotted
    and stable; agents memoize it.
    """

    id: str
    name: str
    #: Non-empty list of plan ids that include this feature.
    plans: tuple[str, ...]
    description: str = ""
    docs_url: str = ""


@dataclass(frozen=True, slots=True)
class Plan:
    """One commercial edition of the product.

    ``license`` is the SPDX-style identifier (``MIT``, ``FSL-1.1-Apache-2.0``,
    ``Commercial``, etc). ``price`` is per ``unit`` in ``currency``. When
    the price is contact-for-pricing, use ``price=None``.
    """

    id: str
    name: str
    license: str
    cta_url: str
    summary: str = ""
    price: float | None = None
    currency: str = "USD"
    unit: str = ""
    #: Ordered recommendation rank — lowest = most prominent in listings.
    order: int = 0


@dataclass(frozen=True, slots=True)
class Capability:
    """One callable capability of the service.

    An agent planner reads this to decide which endpoint to invoke for
    a user goal. Keep ``id`` dotted and stable; agents memoize it.
    """

    id: str
    method: str
    path: str
    description: str = ""
    auth: str = "bearer"
    pricing_model: str = "free"
    stability: str = "stable"


@dataclass(frozen=True, slots=True)
class Offer:
    """One commercial offer for an agent-driven GTM funnel.

    ``intent`` is the single tag an LLM uses to triage a user's ask
    into adoption / sales / support. ``price=None`` means
    contact-for-pricing; ``price=0`` means free.
    """

    id: str
    name: str
    intent: str  # "adoption" | "sales-qualified" | "support-qualified"
    cta_url: str
    summary: str = ""
    price: float | None = None
    currency: str = "USD"
    unit: str = ""


@dataclass(frozen=True, slots=True)
class AgentSEOConfig:
    """Everything needed to publish a complete discovery surface."""

    service_name: str
    service_description: str
    repo_url: str
    live_url: str
    version: str = "0.1.0"
    license: str = "MIT"
    #: Capability x pricing matrix agents plan against.
    capabilities: tuple[Capability, ...] = ()
    #: Commercial offers with GTM intents.
    offers: tuple[Offer, ...] = ()
    #: Endpoint paths an agent runtime should not crawl (e.g. ``/admin``,
    #: ``/v1/`` when they're auth-only). Added to robots.txt as
    #: ``Disallow`` and omitted from sitemap.xml.
    disallow_paths: tuple[str, ...] = ("/admin", "/v1/")
    #: Extra crawler user-agents that should get an explicit ``Allow: /``.
    #: The defaults cover every mainstream AI crawler on the web as of
    #: 2026 — override only when you need to add a new one.
    ai_crawler_user_agents: tuple[str, ...] = (
        "GPTBot",
        "ClaudeBot",
        "anthropic-ai",
        "PerplexityBot",
        "Google-Extended",
        "CCBot",
        "Applebot-Extended",
        "Meta-ExternalAgent",
        "Bytespider",
    )
    #: Ecosystem hints for ``/.well-known/agents.json``.
    ecosystem_clients: tuple[str, ...] = ()
    ecosystem_upstreams: tuple[str, ...] = ()
    #: Named env-var flags the agent-SEO surface should advertise (e.g.
    #: EvoMetaClaw / EvoForge / SkillOpt gate flags). A mapping of a
    #: short role label to the env var that turns it on.
    evo_stack: dict[str, dict[str, str]] = field(default_factory=dict)
    #: Optional contact email for ChatGPT plugin manifest. Empty is fine.
    contact_email: str = ""
    #: Custom GTM notes shown verbatim in commerce.json. Keep short.
    gtm_notes: str = ""
    #: Short, stable id for ChatGPT-style plugin manifests
    #: (``name_for_model``). Lowercase, underscores only. Falls back
    #: to a slugified service name when empty, but a hand-picked value
    #: is strongly recommended since agents memoize it.
    plugin_name_for_model: str = ""
    #: Commercial editions (Community / Pro / Cloud / Agency ...). An
    #: empty tuple disables the ``/.well-known/plans.json`` surface —
    #: services with no commercial tiering simply skip it.
    plans: tuple[Plan, ...] = ()
    #: Per-feature inclusion matrix. A feature with ``plans=("community",
    #: "pro", "cloud")`` means "included in all three editions"; a
    #: feature only in ``("pro", "cloud")`` is the upsell. Agents walk
    #: this matrix to show a user what they'd gain by upgrading.
    features: tuple[Feature, ...] = ()


def coerce_offer(o: Offer | dict) -> Offer:
    """Accept either an Offer or a plain dict (useful for config files)."""
    if isinstance(o, Offer):
        return o
    return Offer(**o)


def coerce_capability(c: Capability | dict) -> Capability:
    if isinstance(c, Capability):
        return c
    return Capability(**c)
