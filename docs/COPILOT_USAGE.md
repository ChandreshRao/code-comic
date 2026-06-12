# Copilot Usage Notes

This file documents how GitHub Copilot (Agent mode) assisted development of `code-comic`.

- `src/ignore_handler.py`: implemented glob and `.code-comic-ignore` merging logic used to keep analysis focused and reduce token usage when running in `lightweight` mode.
- `src/html_renderer.py`: designed the Mermaid + HTML layout for comics so Copilot could suggest compact, portable markup for offline rendering.
- `src/renderer.py`: Copilot helped craft the fallback behavior (image → HTML) and the structured return payload used by the MCP tool.
- `tests/test_renderer.py`: used Copilot patterns for fake LLM/image clients and deterministic tests that avoid live API calls.
- `src/prompt_generator.py`: Copilot suggested prompt templates and scene-resolution logic to ensure stable, parseable LLM output.
- `docs/FOUNDRY_IQ.md`: Copilot scaffolded the Foundry IQ integration plan and a commented VS Code MCP stub for future KB lookup.
- `src/mcp_server.py` (Phase 2): high-level FastMCP tool wrappers were drafted to call existing `analyze_repository` and `ComicRenderer.render` without duplicating prompt logic.

Notes:
- These bullets map Copilot contributions to specific files and decisions. The goal is transparency about where and how an AI assistant influenced implementation details.
