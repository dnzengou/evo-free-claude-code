# `agentseo` — AI-agent-detectable SEO toolkit

Bolt-on package that publishes a complete **AI-agent discovery surface** for any HTTP service.

AI agents (Claude, ChatGPT, Perplexity, Gemini, generic LLM runtimes) read structured manifests at well-known paths to:

1. Learn what your service does (`llms.txt`, `llms-full.txt`).
2. Decide whether to call it (`/.well-known/ai-plugin.json`, `/.well-known/agents.json`, `/.well-known/mcp.json`).
3. Plan which capability to invoke and at what cost (`/.well-known/agents-registry.json`).
4. Match a user's commercial intent — *adopt / buy / get support* — to an offer (`/.well-known/commerce.json`).
5. Crawl only what you want indexed (`robots.txt`, `sitemap.xml`).

This package renders all nine endpoints from one dataclass. Zero framework lock-in: use it with FastAPI, as a static-site build step, or from a CLI.

---

## Install

For now, copy the folder into your project. A PyPI release is on the roadmap.

```bash
cp -r agentseo/ /path/to/your/project/
```

Requires Python ≥ 3.11. The CLI renderer has **no runtime dependencies**. The FastAPI router helper needs `fastapi` (already in most projects).

---

## Use

### 1. Mounted on a FastAPI app

```python
from fastapi import FastAPI
from agentseo import AgentSEOConfig, Capability, Offer, build_router

config = AgentSEOConfig(
    service_name="My Service",
    service_description="One sentence an LLM will quote.",
    repo_url="https://github.com/me/mine",
    live_url="https://mine.example.com",
    capabilities=[
        Capability(id="my.do", method="POST", path="/v1/do",
                   description="Do the thing."),
    ],
    offers=[
        Offer(id="free", name="Free tier", price=0.0,
              intent="adoption", cta_url="https://mine.example.com/signup"),
        Offer(id="pro",  name="Pro",       price=29.0,
              intent="sales-qualified",
              cta_url="https://mine.example.com/pro"),
    ],
)

app = FastAPI()
app.include_router(build_router(config))
```

Nine new endpoints appear immediately:

```
GET /llms.txt
GET /llms-full.txt
GET /sitemap.xml
GET /robots.txt
GET /.well-known/ai-plugin.json
GET /.well-known/agents.json
GET /.well-known/mcp.json
GET /.well-known/agents-registry.json
GET /.well-known/commerce.json
```

### 2. Rendered to static files (for Jekyll / Hugo / Next.js / a CDN)

```bash
python -m agentseo.cli \
    --config agentseo/example.json \
    --base-url https://mine.example.com \
    --out ./public
```

Produces `./public/llms.txt`, `./public/.well-known/*.json`, etc. Commit the folder, serve it statically, done.

### 3. From a non-Python framework

Import the pure renderers and wire them up yourself:

```python
from agentseo.manifests import render_manifests
for url_path, body in render_manifests(config, "https://mine.example.com").items():
    # write to disk, hand to Flask, push to S3, …
    ...
```

---

## Why

- **Sales / marketing / GTM rely on agents.** An LLM that can discover your service, learn your pricing, and route a user's intent to the right offer *is* your top-of-funnel now.
- **The alternative is nothing.** Services without this surface are invisible to agent planners; services with it get called directly.
- **No lock-in.** The dataclass is 40 lines. Swap the renderer, host it anywhere, replace us whenever.

---

## Design notes

- **Intent, not keywords.** `offers[].intent` is `adoption`, `sales-qualified`, or `support-qualified` — three buckets, every LLM can triage into them.
- **Capability × pricing matrix.** `agents-registry.json` tells planners which call to make *and* whether it will incur provider cost.
- **JSON-LD inside Markdown.** `llms-full.txt` embeds a `@type: WebAPI` block with `potentialAction: ConsumeAction`, so schema-aware extractors bind the API to the offer.
- **Deterministic renderers.** Every function is a pure `config → str` — trivial to snapshot-test.
- **One opt-in. One kill switch.** Don't want an endpoint? Drop it from the router. Don't want a disallow path? Override `AgentSEOConfig.disallow_paths`.

See [`example.json`](example.json) for a complete minimal config.

---

## License

MIT. Part of the [Free Claude Code](https://github.com/dnzengou/free-claude-code) project.
