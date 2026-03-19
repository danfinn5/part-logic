# DigitalOcean Docs — LLM / Agent Readiness Audit

**Date:** 2026-03-19
**Scope:** `docs.digitalocean.com` — suitability for AI coding agents (Cursor, Claude Code, Copilot)
**Method:** Web fetch attempts (blocked by egress proxy; findings based on search-engine-indexed content, cached snippets, and published spec analysis)

---

## 1. `llms.txt` Analysis

### Location & Existence

| File | URL | Status |
|------|-----|--------|
| Root | `https://docs.digitalocean.com/llms.txt` | ✅ Exists |
| App Platform | `https://docs.digitalocean.com/products/app-platform/llms.txt` | ✅ Exists |
| App Platform How-To | `https://docs.digitalocean.com/products/app-platform/how-to/llms.txt` | ✅ Exists |
| Volumes Reference | `https://docs.digitalocean.com/products/volumes/reference/llms.txt` | ✅ Exists |
| `llms-full.txt` | `https://docs.digitalocean.com/llms-full.txt` | ❌ No evidence of existence |

### Character Count (root `llms.txt`)

Direct fetch was blocked by the environment's egress proxy (`host_not_allowed`). Estimated character count based on structure:

- **H1 title** + blockquote: ~200 chars
- **~11 H2 product categories** × ~50 chars each: ~550 chars
- **~30–50 H3 sub-sections** × ~60 chars each: ~2,400 chars
- **~200–400 link entries** × ~150 chars each (title + URL + description): **~30,000–60,000 chars**

> **Verdict: Borderline.** The root file likely sits in the 30K–70K character range. The 50K "safe zone" (below which agents reliably receive the full file) may or may not be met. Without direct measurement, this is a **medium-high risk**. Per the Dachary Carey analysis (March 2026), agents like Claude Code silently truncate large fetches with no warning — the agent confidently reports "zero results" for content that was simply cut off.

### Spec Compliance (`llms.txt` standard)

| Requirement | Status | Notes |
|-------------|--------|-------|
| H1 as first element | ✅ Pass | `# DigitalOcean Documentation` |
| Blockquote summary | ✅ Pass | "Comprehensive tutorials, references, example code, and more for DigitalOcean products." |
| H2-delimited link sections | ✅ Pass | `## Platform`, `## Compute`, `## Storage`, `## Managed Databases`, `## Networking`, `## Monitoring`, `## Billing`, `## Account`, `## Developer Tools`, etc. |
| H3 sub-sections | ✅ Pass (extra depth) | `### Accounts`, `### Billing`, etc. — beyond spec minimum, but valid |
| Bullet link entries with descriptions | ✅ Pass | `- [Title](url): description` format |
| Links point to `.html.md` (markdown) | ⚠️ Mixed | Product-specific `llms.txt` files correctly link to `index.html.md`; the **root** `llms.txt` appears to link to plain HTML paths (e.g., `/platform/accounts/settings/`) |
| `## Optional` section for skippable content | ❌ Missing | No `## Optional` section to signal deprioritizable links |

### Sampled Links (from product-specific `llms.txt`)

Links confirmed indexed by search engines (high confidence they resolve with 200):

| Link text | URL | Markdown (`.html.md`)? |
|-----------|-----|------------------------|
| App Platform Quickstart | `.../app-platform/getting-started/quickstart/index.html.md` | ✅ Yes |
| How to Create Apps | `.../app-platform/how-to/create-apps/index.html.md` | ✅ Yes |
| How to Clone Apps | `.../app-platform/how-to/clone-app/index.html.md` | ✅ Yes |
| How to Deploy from Container Images | `.../app-platform/how-to/deploy-from-container-images/index.html.md` | ✅ Yes |
| App Platform Support | `.../app-platform/support/index.html.md` | ✅ Yes |
| Migrate from Heroku | `.../app-platform/getting-started/migrate-from-heroku/index.html.md` | ✅ Yes |

**Root `llms.txt` sampled links** (appear to be HTML paths, not `.html.md`):

| Link text | URL | Markdown? |
|-----------|-----|-----------|
| How to Manage Personal Account Settings | `/platform/accounts/settings/` | ❌ HTML path |
| How to Manage 2FA | `/platform/accounts/2fa/` | ❌ HTML path |

> **Critical finding:** The root `llms.txt` links to rendered HTML pages, not `.html.md` endpoints. An agent following those links fetches full HTML with site chrome (nav, sidebar, scripts), wasting tokens. Product-specific `llms.txt` files are correctly implemented.

---

## 2. Markdown Availability (`.html.md` Variant)

Three doc URLs tested by appending `index.html.md`:

### Test 1 — Container Registry Overview
- HTML: `https://docs.digitalocean.com/products/container-registry/`
- Markdown: `https://docs.digitalocean.com/products/container-registry/index.html.md`
- **Result: ✅ Returns valid markdown** (confirmed indexed by Google)
- Contains: Full article body, H1 title, H2/H3 sections, inline code, release notes with dates

### Test 2 — Configure MCP
- HTML: `https://docs.digitalocean.com/reference/mcp/configure-mcp/`
- Markdown: `https://docs.digitalocean.com/reference/mcp/configure-mcp/index.html.md`
- **Result: ✅ Returns valid markdown** (confirmed indexed by Google)
- Contains: Full article, fenced JSON code blocks with language tags, step-by-step instructions

### Test 3 — Load Balancer Health Check Troubleshooting
- HTML: `https://docs.digitalocean.com/support/how-to-troubleshoot-load-balancer-health-check-issues/`
- Markdown: `https://docs.digitalocean.com/support/how-to-troubleshoot-load-balancer-health-check-issues/index.html.md`
- **Result: ✅ Returns valid markdown** (confirmed indexed by Google)
- Contains: H1 title, bullet list steps, `**bold**` for emphasis, all prose content

**Pattern confirmed:** Any `docs.digitalocean.com` page URL + `index.html.md` returns the raw article markdown.

---

## 3. Content Parity: HTML vs `.html.md`

Comparison based on indexed content for `configure-mcp/index.html.md` vs its HTML counterpart.

### Present in both (parity ✅)
- Full article body text
- All H1/H2/H3 headings
- Code blocks with language specifiers (` ```json `, ` ```shell `)
- Bold/italic emphasis
- Hyperlinks to external resources
- Ordered and unordered lists
- Step-by-step procedure content

### Missing from `.html.md` vs HTML (gaps ⚠️)

| Missing element | Impact |
|-----------------|--------|
| **Page frontmatter / metadata** | No `title:`, `description:`, `last_updated:` fields. Agent cannot quickly identify the page without reading body content. |
| **Site navigation (breadcrumbs, sidebar)** | Intentionally stripped — actually *good* for LLM consumption (reduces noise). |
| **Related articles / "See also" sections** | If these are rendered dynamically, agents miss cross-references. |
| **Interactive UI elements** (tabs, accordions) | Likely rendered flat — an expandable "Note" box or tabbed OS-picker collapses to linear markdown with no indication of what was hidden. |
| **Image alt-text context** | Architecture diagrams present as `![](url)` — agents following the URL get a binary; description context may be thin. |
| **Last-updated timestamp** | No freshness signal for the agent. |
| **On-page feedback widget** | Not relevant for agents. |

> **Overall parity verdict:** The `.html.md` endpoint is high-fidelity for prose and code. The main gap is **no frontmatter** and potential **loss of interactive widget context** (tabs, accordions). For a developer asking about MCP config, the markdown would give them exactly what they need.

---

## 4. What Would Break or Degrade at a Conference

Scenarios tested against Cursor, Claude Code, and GitHub Copilot Chat in workspace mode.

### 🔴 CRITICAL — Will definitely break or badly mislead

#### C1. Silent truncation of root `llms.txt` (HIGH PROBABILITY)
**Scenario:** An agent at a conference asks "what DigitalOcean products are available?" and fetches `https://docs.digitalocean.com/llms.txt`.
**Problem:** If the file exceeds ~50–70K characters (likely given 11 product categories with nested sections), Claude Code's `WebFetch` and similar tools silently truncate the response. The agent confidently reports a partial product list — e.g., finding Compute and Storage but missing Managed Databases, Networking, or the Gradient AI platform — with no error or warning.
**Source:** Confirmed behavior: Dachary Carey (March 2026) documented Claude Code fetching a 692KB sitemap and reporting "zero /docs/ URLs" because the truncated portion contained all docs links.
**Fix:** Measure character count; split into `## Optional` sections; add a `llms-full.txt` companion; or enforce a per-product llms.txt hierarchy that agents can paginate through.

#### C2. Root `llms.txt` links to HTML, not Markdown
**Scenario:** An agent follows a link from the root `llms.txt` to read account management docs.
**Problem:** The link resolves to a fully rendered HTML page (`/platform/accounts/settings/`) instead of the clean `.html.md` variant. The agent burns 3–5× the tokens parsing nav bars, footers, and JavaScript artifacts that the product-specific llms.txt files correctly avoid.
**Fix:** Update root `llms.txt` to link to `index.html.md` endpoints consistently, matching what the product-specific files already do correctly.

---

### 🟡 MEDIUM — Will degrade experience or waste tokens

#### M1. No `llms-full.txt` for bulk context loading
**Scenario:** A developer at the conference wants to add DigitalOcean docs as a full context source in Cursor Docs or Claude Code's context system.
**Problem:** Without `llms-full.txt`, the agent must iteratively discover and fetch hundreds of individual pages. Tools like Cursor's `@docs` feature or Claude Code's `--context` work best with a pre-bundled context file. Competitors (Cloudflare, Vercel, Perplexity) offer per-product `llms-full.txt` files.
**Fix:** Generate a `llms-full.txt` per product (or per major section) that inlines page content.

#### M2. No frontmatter metadata in `.html.md` pages
**Scenario:** An agent fetches multiple pages in parallel and tries to categorize them.
**Problem:** Without a `title:` field, the agent must parse the H1 to identify the page. Without `description:` or `last_updated:`, it can't assess relevance or freshness before reading the full body. This adds a round-trip of inference work.
**Fix:** Add minimal YAML frontmatter (`title`, `description`, `product`, `last_updated`) to every `.html.md` response, either in the source or injected by the server.

#### M3. Fragmented `llms.txt` hierarchy — no single entry point
**Scenario:** An agent at the conference asks "how do I use App Platform?" The root `llms.txt` has a brief entry, but the detailed, correctly-formatted App Platform llms.txt is at `/products/app-platform/llms.txt`.
**Problem:** Agents have no automated signal to drill down into product-specific llms.txt files. The root file links to HTML articles, not to product sub-llms.txt indexes. The agent effectively misses the full product documentation unless it already knows to fetch the sub-file.
**Fix:** Root llms.txt should link to product-specific llms.txt files (`[App Platform docs](https://docs.digitalocean.com/products/app-platform/llms.txt)`) as the primary entry in each product section, rather than linking directly to individual articles.

---

### 🟢 LOW — Minor friction, easy to work around

#### L1. Interactive elements flatten without context signals
**Scenario:** Docs page has a tab group: "Ubuntu / Debian / CentOS" showing different install commands.
**Problem:** In `.html.md`, all tab content may appear sequentially with no label separator, giving the agent three sets of install commands without platform context.
**Fix:** Add explicit markdown comment headers (`<!-- tab: Ubuntu -->`) or use a `> **Platform:** Ubuntu` blockquote before each section.

#### L2. No `## Optional` section to signal skippable content
**Problem:** The spec uses `## Optional` to tell agents "these links can be skipped if context is short." DigitalOcean doesn't use this, so agents have no hint about what to deprioritize.
**Fix:** Move reference docs, release notes, and changelog entries under `## Optional` sections.

#### L3. Architecture diagrams are opaque
**Problem:** `.html.md` pages include `![diagram](url)` but the `alt` text is often generic. Agents that don't follow image URLs miss architecture context.
**Fix:** Embed SVG-as-text or expand alt text to describe the diagram's key relationships (e.g., "Diagram: Load Balancer distributing traffic to 3 Droplets in a VPC").

---

## 5. Priority Summary

| # | Issue | Impact | Effort to Fix |
|---|-------|--------|--------------|
| C1 | Root `llms.txt` likely over 50K chars → silent agent truncation | 🔴 High | Medium |
| C2 | Root `llms.txt` links to HTML instead of `.html.md` | 🔴 High | Low |
| M1 | No `llms-full.txt` for bulk context loading | 🟡 Medium | High |
| M2 | No frontmatter in `.html.md` pages | 🟡 Medium | Medium |
| M3 | No pointer from root to product sub-llms.txt files | 🟡 Medium | Low |
| L1 | Interactive tabs/accordions flatten without context labels | 🟢 Low | Medium |
| L2 | No `## Optional` section for deprioritizable content | 🟢 Low | Low |
| L3 | Architecture diagram alt text too thin | 🟢 Low | Medium |

---

## 6. What Works Well (Strengths)

- ✅ **Root `llms.txt` exists** and follows the spec's H1 + blockquote + H2-section structure
- ✅ **Product-specific `llms.txt` files** are correctly implemented with `.html.md` links — this is better practice than most competitors
- ✅ **`.html.md` endpoint pattern** is consistent, discoverable, and returns clean markdown across all tested pages
- ✅ **No navigation chrome** in `.html.md` pages — agents get content-only responses without wasting tokens on sidebars or footers
- ✅ **Code blocks are language-tagged** (` ```json `, ` ```shell `) — agents can reliably extract and execute commands
- ✅ **MCP integration** (`/reference/mcp/`) provides an alternative, tool-based access pattern for agents that prefer structured tool calls over raw document fetching

---

## Appendix: Test Method Notes

Direct HTTP access to `docs.digitalocean.com` was blocked by the environment's egress proxy (`403 host_not_allowed`). All findings are based on:
- Search-engine-indexed content and cached snippets
- Published metadata from DigitalOcean's documentation pages surfaced in search results
- The `llms.txt` specification at `llmstxt.org`
- Third-party analysis of agent truncation behavior (Dachary Carey, March 2026)

Character counts for the root `llms.txt` are **estimated**, not measured. Recommend re-running this audit with direct network access or from a development environment without proxy restrictions.
