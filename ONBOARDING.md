# Onboarding — Free Claude Code

**Goal:** zero to proxying Claude Code through your own provider in under two minutes.

This is the shortest path. For every knob, every provider, and the Discord/Telegram/voice extras, read [README.md](README.md). For the moat architecture (EvoMetaClaw / EvoForge / SkillOpt), read [BLUEPRINT.md](BLUEPRINT.md). For deployment shapes, read [ECOSYSTEM.md](ECOSYSTEM.md).

---

## 2-minute quick start

### Prerequisites

- **Python 3.14** (installed by the script below if missing)
- **`uv`** package manager (installed by the script below if missing)
- **One provider API key** — pick one: OpenAI, DeepSeek, Groq, Cerebras, Gemini, Mistral, NVIDIA NIM, OpenRouter, Fireworks, Kimi, Wafer, Z.ai, OpenCode. (Or none — LM Studio, llama.cpp, Ollama all work locally for free.)

### 1. Install

```bash
curl -fsSL https://github.com/dnzengou/free-claude-code/raw/main/scripts/install.sh | sh
```

### 2. Configure

Pick one, export the key, pick a model. Three lines:

```bash
export MODEL=openai/gpt-4o            # or deepseek/deepseek-chat, groq/llama-3.3-70b-versatile, ...
export OPENAI_API_KEY=sk-...          # the key for that provider
export ANTHROPIC_AUTH_TOKEN=freecc    # any string; shared secret between proxy and clients
```

### 3. Run

```bash
uv run uvicorn server:app --host 127.0.0.1 --port 8082
```

### 4. Point Claude Code at it

In a second terminal:

```bash
export ANTHROPIC_BASE_URL=http://localhost:8082
export ANTHROPIC_AUTH_TOKEN=freecc
claude
```

Done. Every Claude Code request now flows through your proxy.

---

## Pick a provider (3-second guide)

| Want | Pick |
|---|---|
| **Free-ish, fast, strong quality** | `openai/gpt-4o-mini` or `deepseek/deepseek-chat` |
| **Fastest inference** | `groq/llama-3.3-70b-versatile` or `cerebras/llama3.1-8b` |
| **Zero marginal cost, offline** | `lmstudio/<your-model>` or `ollama/<your-model>` |
| **One key, 100+ models** | `open_router/anthropic/claude-3-5-sonnet` (and set `OPENROUTER_API_KEY`) |

Full provider list: `README.md` → *Choose a Provider*.

---

## Enable the moat (opt-in, one env var each)

| Capability | Flag | Effect |
|---|---|---|
| **Trajectory logging** (EvoMetaClaw) | `TRAJECTORY_LOG_ENABLED=1` | Every request writes one JSONL row. Local only. Rotated at 5 MB. |
| **Auto-forge** (EvoForge) | `AUTO_FORGE_ENABLED=1` | Every 24h aggregates the corpus into `skillopt_policy.json`. |
| **Skill-conditioned routing** (SkillOpt) | `SKILLOPT_ENABLED=1` | Reads the policy and narrows routing per inferred skill (`edit`, `plan`, `probe`, `question`, `chat`). |

Flip all three and the proxy quietly learns which provider is cheapest + fastest + most reliable **per skill**, from your own traffic, and routes accordingly. Nothing calls home.

---

## Agent-SEO (publish your service for AI crawlers)

The proxy serves a complete discovery surface with no setup:

- `GET /llms.txt` — compact summary for AI agents
- `GET /llms-full.txt` — full reference with JSON-LD WebAPI schema
- `GET /sitemap.xml` — index of public URLs
- `GET /.well-known/ai-plugin.json` — ChatGPT plugin manifest
- `GET /.well-known/agents.json` — generic agent manifest
- `GET /.well-known/mcp.json` — MCP pointer
- `GET /.well-known/agents-registry.json` — capability × pricing matrix
- `GET /.well-known/commerce.json` — offers + GTM intents
- `GET /robots.txt` — AI-crawler-welcoming rules

**Reuse this on your own service:** the surface lives in the standalone `agentseo/` package:

```python
from fastapi import FastAPI
from agentseo import AgentSEOConfig, Capability, Offer, build_router

app = FastAPI()
app.include_router(build_router(AgentSEOConfig(
    service_name="My Service",
    service_description="One sentence an LLM will quote back.",
    repo_url="https://github.com/me/mine",
    live_url="https://mine.example.com",
    capabilities=[Capability(id="my.do", method="POST", path="/v1/do")],
    offers=[Offer(id="free", name="Free", price=0.0, intent="adoption",
                 cta_url="https://mine.example.com/signup")],
)))
```

Or render to static files (Jekyll / Hugo / Next.js / CDN):

```bash
python -m agentseo.cli --config agentseo.json --base-url https://x.com --out ./public
```

---

## Production checklist

Tick these before shipping to real users:

- [ ] `ANTHROPIC_AUTH_TOKEN` set to a strong random string (default `freecc` is dev-only).
- [ ] Provider keys set as environment variables, never in files committed to git.
- [ ] `FAILOVER_MODELS` set to at least one backup provider (e.g. `openai/gpt-4o,open_router/openai/gpt-4o`) so a provider outage is transparent.
- [ ] `EVO_ROUTING=1` if you're running multiple providers — the fitness tracker demotes flaky ones automatically.
- [ ] For hosted: a reverse proxy (Caddy, nginx, Vercel) terminates TLS. The proxy's admin UI stays loopback-only — no extra firewall rules needed.
- [ ] Health probe: `GET /health` (unauth) for liveness, `GET /health/ready` (auth required) for Vercel env verification.
- [ ] Monitor the **Metrics** tab in `/admin` locally, or scrape `GET /admin/api/metrics` through an SSH tunnel.
- [ ] Decide on the trajectory corpus: on a read-only FS (Vercel Lambda), the logger auto-disables; set `FCC_CACHE_DIR=/var/lib/fcc` on a writable volume if you want persistence.

---

## Admin UI (local only)

Open `http://localhost:8082/admin` in a browser on the machine running the proxy. The UI is loopback-only — remote hosts get a 403. To use it from a VPS, SSH-tunnel:

```bash
ssh -L 8082:localhost:8082 user@your-vps
```

Then open `http://localhost:8082/admin`.

In the Admin UI you can:
- Edit provider keys / model routing without restarting
- Validate each provider key with one click
- See per-request latency + cost
- See the SkillOps analytics panel (`/admin/api/skillops/analytics`) — estimated USD savings of your current SkillOpt policy vs. the uniform-pick baseline

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `401 Unauthorized` on `/v1/messages` | Client is missing `ANTHROPIC_AUTH_TOKEN` or it doesn't match the proxy's. |
| `provider configuration: no API key` | Set the right `*_API_KEY` env var for your `MODEL` provider. |
| Admin UI returns 403 | Access it from `127.0.0.1` / `localhost`. Use an SSH tunnel on a remote host. |
| `No space left on device` on a Lambda | The read-only FS tripped the trajectory writer; it auto-disables for that process. Set `FCC_CACHE_DIR` to a writable volume. |
| `read_documentation` says a connector is missing | You're in a Claude session; follow its link to reconnect the connector and retry. |

---

## Next steps

- Read [BLUEPRINT.md](BLUEPRINT.md) if you want to understand (or contribute to) EvoMetaClaw / EvoForge / SkillOpt.
- Read [LICENSING.md](LICENSING.md) if you're deciding what to open-source vs. license commercially — strategy, best-in-class examples, and the FCC Community/Pro/Cloud editions model.
- Read [ECOSYSTEM.md](ECOSYSTEM.md) if you're deploying across multiple products.
- Read [agentseo/__init__.py](agentseo/__init__.py) if you want to bolt agent-SEO onto another service in your stack.
- File an issue tagged `sales` or `support` for the hosted / integration offerings in `/.well-known/commerce.json`.
