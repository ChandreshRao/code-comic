# Foundry IQ Integration (scaffold)

This document is a scaffold describing a potential Foundry IQ knowledge base integration for `code-comic`.

Overview:
- Reference: https://github.com/microsoft/iq-series
- Purpose: enable Copilot/Foundry IQ to search a KB of architecture patterns and map them to comic scene suggestions.

KB contents (suggested):
- Software architecture patterns (monolith, microservice, event-driven, serverless)
- Example comic scene structures and prompt templates
- Mapping from repo detections (language, package files) to candidate scene titles

Commented VS Code MCP server stub (for a future `foundry-iq` server):

```json
{
  "servers": {
    "foundry-iq": {
      "type": "http",
      "url": "https://<foundry-iq-host>/search",
      "headers": {
        "Authorization": "Bearer <ADMIN_KEY>"
      }
    }
  }
}
```

Demo prompt (example):
"Use Foundry IQ to find architecture patterns for this repo, then generate a comic with code-comic."

This file is descriptive only; no cloud resources are required for Phase 1.
