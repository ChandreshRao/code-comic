# Foundry IQ integration

This document describes how `code-comic` addresses the **Microsoft IQ** criterion in [`requirement.md`](../requirement.md).

## IQ layer chosen

| Option in `requirement.md` | Used here? |
|----------------------------|------------|
| **Foundry IQ** — agentic knowledge retrieval, cited grounded answers | **Yes** |
| Work IQ — Microsoft 365 work context | No |
| Fabric IQ — Microsoft Fabric semantic layer | No |

**Foundry IQ** fits this project: before generating a 4-panel architecture comic, the tool can query an enterprise knowledge base of software patterns (monolith, microservices, event-driven, etc.) and feed cited snippets into the LLM prompt — reducing hallucinated architecture claims.

References:

- [What is Foundry IQ?](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/what-is-foundry-iq)
- [Microsoft IQ series](https://github.com/microsoft/iq-series)

## What is implemented in this repo

| Piece | Location | Role |
|-------|----------|------|
| Config | `src/config.py` | Reads `FOUNDRY_IQ_*` from environment |
| Client | `src/foundry_client.py` | POSTs a query; parses text snippets from the response |
| Pipeline hook | `src/renderer.py` | If configured, retrieves knowledge and adds `metadata['content']['__foundry_iq.txt']` before `build_scene_prompt` |
| Tests | `tests/test_foundry_client.py` | Unit test with mocked HTTP (no live Azure) |

Flow:

```
analyze repo → (optional) Foundry IQ retrieve → build_scene_prompt → LLM → render comic
```

## Submission scope (honest)

**Judges should expect:**

- A clear Foundry IQ **design** and **optional code path** aligned with `requirement.md`.
- **No live Foundry IQ** in the bundled demo: `examples/` and default `pytest` runs do not provision or call an Azure knowledge base.
- The app runs fully without `FOUNDRY_IQ_*` env vars (same behavior as before IQ was added).

**Not claimed:**

- A deployed Azure AI Search knowledge base in this submission.
- End-to-end validation against Microsoft's production retrieve API (the client is a thin, generic HTTP wrapper; see [Production API](#production-api-notes) below).

This is intentional: Foundry IQ requires an Azure subscription and knowledge-base setup. The submission demonstrates **integration architecture** without requiring paid cloud resources for judges.

## Optional enablement

Add to `.env` at the repo root (only if you have an Azure AI Search knowledge base):

```text
FOUNDRY_IQ_ENDPOINT=https://<service>.search.windows.net/knowledgebases('<kb-name>')/retrieve?api-version=2026-04-01
FOUNDRY_IQ_API_KEY=<search-query-or-admin-key>
FOUNDRY_IQ_TIMEOUT=10
```

When both `FOUNDRY_IQ_ENDPOINT` and `FOUNDRY_IQ_API_KEY` are set, `python cli.py` and MCP `generate_comic` will attempt retrieval before scene generation. On failure or empty results, generation continues without IQ enrichment.

### Suggested knowledge base contents

- Software architecture patterns and trade-offs
- Comic scene templates and prompt examples
- Mappings from repo signals (language, `package.json`, `docker-compose.yml`, etc.) to scene titles

### Azure prerequisites (for live use)

You do **not** need a Foundry Agent for this hook — only a **knowledge base** on Azure AI Search:

1. Azure subscription ([free trial](https://azure.microsoft.com/free/) available).
2. Azure AI Search resource (free tier available for POC).
3. Knowledge base with indexed architecture-pattern documents (portal: Microsoft Foundry → Build → Knowledge, or Azure AI Search APIs).
4. Query via the knowledge base [retrieve API](https://learn.microsoft.com/en-us/azure/search/search-agentic-retrieval-how-to-retrieve).

Costs are consumption-based; POC testing can use free-tier Search and free agentic-retrieval token allocation. A full Foundry Agent (Cosmos DB, Storage, deployed models) is optional and not required for `code-comic`.

## Production API notes

Microsoft's retrieve API expects a body such as:

```json
{
  "intents": [{ "type": "semantic", "search": "event-driven Python microservice patterns" }]
}
```

with an `api-key` header (or Entra bearer token). The current `FoundryClient` posts `{"query": "...", "top_k": N}` with `Authorization: Bearer <key>` for flexibility during development. Point `FOUNDRY_IQ_ENDPOINT` at your retrieve URL and adjust the client if you need strict API-version compatibility.

## Future: MCP knowledge-base tool

Each Azure AI Search knowledge base can expose an [MCP endpoint](https://learn.microsoft.com/en-us/azure/search/search-agentic-retrieval-how-to-retrieve#call-the-mcp-endpoint). A future version could register that server beside `code-comic` in `.vscode/mcp.json` so Copilot Agent queries the KB directly:

```json
{
  "servers": {
    "foundry-iq": {
      "type": "http",
      "url": "https://<service>.search.windows.net/knowledgebases/<kb-name>/mcp?api-version=2026-04-01",
      "headers": {
        "api-key": "<search-api-key>"
      }
    }
  }
}
```

Example agent prompt:

> Use Foundry IQ to find architecture patterns for this repo, then call `generate_comic` with `context_mode=comprehensive`.

This stub is **not** wired in the current `.vscode/mcp.json`; the in-process `FoundryClient` hook is the shipped integration point.
