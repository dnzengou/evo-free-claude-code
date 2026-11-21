# Licensing & Editions — How-To Guide

**Audience:** maintainers deciding how to balance open source with a sustainable commercial tier.
**Tl;dr:** keep the proxy and every protocol surface MIT; put the **cross-tenant moat** (shared trajectory corpus, trained policies, hosted auto-forge, enterprise SSO/audit/SLA) behind a source-available license or a managed-service offering. Never re-license what you already shipped under MIT.

---

## 1. The five models that work in 2026

Five patterns cover ~95% of successful open-source-first companies. Each solves a different problem; most big players use a *combination*.

### 1.1 Open Core — MIT / Apache core + closed modules

| Who does it | What's open | What's closed |
|---|---|---|
| **GitLab** | Community Edition (CE) | Enterprise Edition (EE) features — advanced LDAP, audit events, portfolio management |
| **PostHog** | Core product MIT | SSO, advanced permissions, data pipelines (paid add-ons) |
| **Supabase** | Postgres + Auth + Realtime core Apache 2 | Managed cloud, Point-in-time recovery, custom SMTP, dedicated support |
| **Cal.com** | Core AGPL | Enterprise plugins (SSO, orgs, teams at scale) |

**Mechanics:** a plugin/extension architecture. The paid modules live in a separate repo under a commercial license. The core resolves plugins dynamically — no plugin, no feature, no runtime error.

**Pros:** truly open core; permissive for the free tier; low friction for community contribution.
**Cons:** you have to maintain a boundary that holds under refactoring. Clever users will reimplement enterprise features in the open version.

### 1.2 Business Source License (BSL) — source-available with a time-delay

| Who does it | Terms |
|---|---|
| **HashiCorp** (Terraform, Vault, Consul, Nomad, 2023) | Source available; prohibits competing with HashiCorp's managed service; auto-converts to MPL after 4 years |
| **CockroachDB** | 3-year delay before converting to Apache |
| **MariaDB MaxScale** | 2–4 year delay |

**Mechanics:** you publish the full source. Anyone can read, modify, self-host. You cannot run a competing managed service. After N years, each release auto-converts to a true open-source license (Apache / MPL), so the community benefits long-term.

**Pros:** full source visibility, long-term open commitment, protection against AWS-style resale.
**Cons:** OSI doesn't call this "open source". Some communities react strongly (HashiCorp's 2023 switch forked OpenTofu).

### 1.3 Functional Source License (FSL) — short, aggressive BSL

| Who does it | Terms |
|---|---|
| **Sentry** (2023) | Source available; prohibits competing commercial SaaS and prohibits incorporating into another product sold commercially; auto-converts to Apache after 2 years |
| **Keygen** | Same shape as Sentry's FSL |

**Mechanics:** like BSL but shorter window (2 years) and stricter restrictions (no using FSL code in *any* commercial product, not just a competing SaaS).

**Pros:** faster community conversion; cleaner legal text than BSL; well-written in plain English.
**Cons:** 2 years of restrictions is meaningful for enterprises that need a true OSS license today.

### 1.4 AGPL + Commercial Dual License

| Who does it | How |
|---|---|
| **MongoDB** (pre-2018) | AGPL for community, commercial license for anyone who doesn't want AGPL's copyleft obligations |
| **Grafana** | AGPL v3 core since 2021; Grafana Labs sells Grafana Cloud + Grafana Enterprise under separate commercial terms |
| **Plausible** | AGPL + managed cloud |
| **Dub.co** | AGPL + paid cloud |

**Mechanics:** community gets AGPL; any organization that needs to embed the code in a closed-source product or SaaS must buy a commercial license. AGPL's "run as a network service → publish source" clause is what forces the choice.

**Pros:** clean OSS status; the commercial pressure is self-regulating.
**Cons:** some enterprises refuse AGPL categorically, even behind their firewall — you lose that market without a commercial license. Also: AGPL enforcement is legally complex; most of the pressure is reputational.

### 1.5 Fair-code / Sustainable Use License

| Who does it | Terms |
|---|---|
| **n8n** (Sustainable Use License) | Free to self-host for internal use; prohibits building a hosted n8n-as-a-service |
| **Element Supernova** (various projects) | Similar "internal use only" terms |

**Mechanics:** source-available. Internal commercial use is free; selling access to others as a service is prohibited.

**Pros:** simple to understand; aligns incentives with self-hosters.
**Cons:** also not OSI-approved OSS; some governance frameworks (CNCF, OIN) won't accept it.

---

## 2. Which model fits which moat?

Pick the license that defends the *specific* thing that's hard to copy — not the code itself.

| If your moat is… | Best fit | Example |
|---|---|---|
| Code quality + developer brand | **MIT / Apache + hosted** | Supabase, Vercel |
| A specific feature only enterprises need (SSO, audit, SAML) | **Open Core** | GitLab EE, Cal.com Enterprise |
| The managed operation (uptime, SLA, operations) | **BSL / FSL + hosted** | HashiCorp, Sentry |
| A dataset or trained model you're compounding over time | **MIT core + proprietary data + hosted** | OpenAI (API), Anthropic |
| Broad adoption as a network good, with enterprise upsell | **AGPL + commercial dual** | MongoDB, Grafana, Plausible |
| Platform-level control preventing AWS resale | **SSPL / BSL** | Elastic, MongoDB (post-2018) |

**Rule of thumb:** the license should be as permissive as possible *given the thing you're trying to protect*. Over-licensing kills adoption; under-licensing gives the moat away.

---

## 3. Recommended structure for Free Claude Code

FCC's moat isn't the code — the proxy and the 18 transports are table stakes. The moat is:

1. **Operational maturity** (SkillOpt policies tuned against real multi-tenant traffic).
2. **Cross-tenant data network effect** (every deploy makes every other deploy's routing smarter).
3. **GTM integration** (wiring FCC into a specific product's commerce surface with the agent-SEO pack).
4. **SLA + support** (teams need someone to call at 2am).

Code is the entry point, not the moat. So:

### 3.1 Three tiers, three licenses

```
┌─────────────────────────────────────────────────────────────┐
│  Community Edition — MIT                                     │
│  (everything on `main` today)                                │
│   - FastAPI proxy + 18 provider transports                   │
│   - Local admin UI                                           │
│   - EvoMetaClaw local trajectory logger                      │
│   - EvoForge CLI (`python scripts/evoforge.py`)              │
│   - SkillOpt runtime routing from a local policy             │
│   - `agentseo/` standalone package                           │
│   - Discord / Telegram / voice adapters                      │
│                                                              │
│  How it grows: community PRs, free self-host, indie users.   │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│  Pro Edition — FSL-2026-Apache 2.0 (source available,        │
│  converts to Apache 2.0 after 2 years)                       │
│   - OIDC / SAML single sign-on for the admin UI              │
│   - Audit log (`/admin/api/audit`) with export to S3/GCS     │
│   - Cross-session SkillOpt policy diffing + A/B gates        │
│   - Prometheus / OpenTelemetry exporter for metrics          │
│   - Team-mode admin: per-user API keys, RBAC                 │
│   - Retention controls on the trajectory corpus              │
│                                                              │
│  How it grows: paid licenses per-instance / per-seat.        │
│  Source is visible; competitors can't sell it as a service.  │
│  After 2 years every release converts to Apache 2.0.         │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│  Cloud — commercial SaaS (closed)                            │
│   - Hosted gateway with 99.9% SLA                            │
│   - Managed EvoForge running on an aggregated multi-tenant   │
│     trajectory corpus — policies tuned against real          │
│     diverse traffic, not just your own. This is the true     │
│     moat: nobody else has it.                                │
│   - Enterprise connectors (Okta, Ping, Azure AD)             │
│   - Dedicated support + onboarding engineer                  │
│                                                              │
│  How it grows: per-instance monthly subscription + usage.    │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 The license picks

- **MIT for the core.** FCC is already MIT. Keeping it MIT is a promise to the community and the lowest adoption cost. Never re-license what you already shipped under MIT.
- **FSL for the Pro features.** A separate `free-claude-code-pro` repository under FSL-2026-Apache 2.0 (model: Sentry's FSL). Short 2-year conversion window keeps the social contract honest. Visible source. No competitor can resell it as a managed service.
- **Closed source for the SaaS.** The Cloud edition is normal proprietary code. What you're really selling is the *operation* (SLA, tuned policies, support), not the bits.

### 3.3 What NOT to do

- **Don't SSPL the core.** It alienates the `/admin` and FastAPI ecosystems. Elastic's reputation took years to recover.
- **Don't retro-relicense `main`.** Anyone can fork the last MIT release. HashiCorp's 2023 change produced OpenTofu within days. A fork is fine — a bitter fork is not.
- **Don't gate baseline features.** Rate limiting, CORS, logging, health probes all belong in the free tier. Enterprise users check "is the free thing production-grade" before they consider paying.
- **Don't hide the licensing choice.** List it at `/.well-known/plans.json` so agents and procurement teams can both read it programmatically.

---

## 4. Implementation — how to actually ship this

### 4.1 Mechanics

1. **Repo layout.** `free-claude-code` (MIT, this repo) + `free-claude-code-pro` (FSL, separate repo, private history visible only to paid licensees initially). The Pro repo depends on the OSS core as a regular pip dependency; nothing downstream has to change.
2. **Plugin boundary.** The core already discovers routers / providers at import time. Pro ships one or more plugin packages (`fcc_pro_sso`, `fcc_pro_audit`, `fcc_pro_otel`) that hook in through the same entry points. No special runtime branching.
3. **Capability declaration.** The free core reads `/.well-known/plans.json` as source of truth for which features it advertises; Pro and Cloud editions ship with extended manifests. Agents and procurement read the same file.
4. **License check (soft).** A single `fcc.license.verify()` on startup for the Pro tier. If missing, Pro plugins log a warning and refuse to load — *the core keeps working*. Never brick the user's gateway.
5. **Commercial surface.** `/.well-known/commerce.json` already lists `self-host`, `hosted-gateway`, `gtm-integration`, `support`. Agents reading this can route a user to the right plan.

### 4.2 Pricing shape (anchor, not gospel)

| Edition | Price | Billing | Who it's for |
|---|---|---|---|
| Community | $0 | — | Individuals, indie teams, OSS projects |
| Pro | ~$199 / instance / month | annual | Internal teams needing SSO + audit |
| Cloud | from ~$499 / month + usage | monthly | Teams who want ops done for them |
| Agency | custom | project | Studios integrating FCC into client products |

### 4.3 Bar for upgrading tiers

- Adoption → Pro: team of ~5+, needs SSO, needs audit log for compliance.
- Pro → Cloud: wants to stop operating the gateway themselves; wants the aggregated-corpus SkillOpt policies.

---

## 5. Onboarding this into the product

Three artifacts ship with v2.5.2 to make the model legible to humans *and* agents:

1. **`LICENSING.md`** (this file) — the strategy.
2. **`GET /.well-known/plans.json`** — a machine-readable feature × edition matrix. Rendered by the `agentseo` package. Agents helping a user adopt the gateway read this to show them what they get for free vs. paid.
3. **Admin-UI "Edition" card** — a loopback-only, small, dismissible card on first load that says *"You're running the Community edition — here's what you have, here's what Pro adds, here's how to upgrade."*. No telemetry, no blocking.

All three are driven from the same config object, so there's one place to edit when the plan evolves.

---

## 6. FAQ

**Q: We already shipped under MIT. Can we switch the whole repo to FSL now?**

No, and you shouldn't want to. Anyone can fork the last MIT commit and keep it MIT forever. If you need to move fast toward Pro: put the *new* paid-tier features in a separate repo under FSL, and keep the existing OSS repo on MIT. Everyone wins.

**Q: Is FSL really open source?**

Not by the OSI definition — "source available" is the term of art. In practice, most teams only care that (a) they can read the source, (b) they can self-host for internal use, (c) it converts to a true OSS license eventually. FSL answers all three.

**Q: What about AGPL instead of FSL for the Pro tier?**

Valid alternative. AGPL + commercial dual is proven (MongoDB, Grafana). Pick AGPL if you want *all* self-hosters to either release their modifications or buy a license. Pick FSL if you mainly want to prevent AWS/Azure-style resale while letting internal self-hosters run modified copies without legal friction.

**Q: Does the Cloud need to run on the same code as the OSS gateway?**

Yes, and should. The Cloud is OSS core + Pro plugins + proprietary ops + aggregated-corpus policies. If Cloud diverges from the OSS codebase, you lose the "easy to migrate off" promise that makes self-hosters trust the Cloud.

**Q: How do I prevent competitors from reselling the OSS core?**

If MIT, you can't — and trying ruins the community. Compete on operations: the Cloud's uptime, the aggregated corpus, the enterprise connectors, and the support SLA are hard to copy. HashiCorp's 2023 relicensing is a cautionary tale: the AWS risk turned out smaller than the community-exit cost.

**Q: Do we need a CLA?**

A DCO (Developer Certificate of Origin) is usually enough and lower friction than a CLA. Enterprises prefer DCO. Add a CLA only if you plan to re-license large portions of the code later.

**Q: What if a paying customer wants to see the Cloud's source?**

Offer a source-access addendum tied to the commercial contract. Most will not exercise it; those who do appreciate the option. Keep the Cloud code in a private repo with access granted per contract.

**Q: Will agent-SEO signals (`/.well-known/plans.json`, `commerce.json`) actually drive sales?**

They remove friction. An LLM inside Claude, ChatGPT, Perplexity, or Gemini that is helping a user adopt a gateway reads these manifests and quotes the right plan back. In 2026, that's the top-of-funnel. The alternative is not being discoverable at all.

**Q: How often should the plans change?**

Quarterly at most. Prices and tier contents are a trust surface. Ship a changelog in `plans.json` (version field) so agents can tell when something moved.

---

## 7. Further reading

- Sentry FSL announcement — https://sentry.io/_/open-source/
- HashiCorp BSL FAQ — https://www.hashicorp.com/bsl
- OpenTofu fork story — https://opentofu.org/manifesto/
- OSI "Open Source" definition — https://opensource.org/osd
- Grafana AGPLv3 retrospective — https://grafana.com/blog/2021/04/20/grafana-loki-tempo-relicensing-to-agplv3/
- n8n Sustainable Use License — https://docs.n8n.io/sustainable-use-license/
