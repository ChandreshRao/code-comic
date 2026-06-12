# MCP Setup (Phase 2)

Two modes:

1. Demo in this repo

   - Open this repository in VS Code.
   - Start the MCP server defined in `.vscode/mcp.json` (Code: Copilot Agent → Start server).
   - Use the tool `generate_comic` with `repo_path` set to `tests/fixtures/sample-repo` and `render_mode=html`.

2. Any other repo (user-profile config)

   - Install `code-comic` on your machine and note the absolute path to the clone.
   - In VS Code: `MCP: Open User Configuration` → point `code-comic-root` input to that path.
   - Start the `code-comic` server and pass `repo_path` or set `CODE_COMIC_REPO_PATH=${workspaceFolder}` in the MCP inputs.

Notes:
- Defaults are tuned for low-cost operation: `context_mode=lightweight`, `render_mode=html` (no image API calls).
- The MCP tool calls the existing `analyze_repository` and `ComicRenderer.render` functions; no prompt logic is duplicated.
