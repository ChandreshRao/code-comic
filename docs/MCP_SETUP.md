# MCP Setup (Phase 2)



Two modes:



1. Demo in this repo



   - Open this repository in VS Code.

   - Start the MCP server defined in `.vscode/mcp.json` (Code: Copilot Agent → Start server).

   - Use the tool `generate_comic` with `repo_path` set to `tests/fixtures/sample-repo` and `render_mode=html-mermaid`.



2. Any other repo (user-profile config)



   - Install `code-comic` on your machine and note the absolute path to the clone.

   - In VS Code: `MCP: Open User Configuration` → point `code-comic-root` input to that path.

   - Start the `code-comic` server and pass `repo_path` or set `CODE_COMIC_REPO_PATH=${workspaceFolder}` in the MCP inputs.



Notes:

- Defaults are tuned for low-cost operation: `context_mode=lightweight`, `render_mode=html-mermaid` (no image API calls).

- Use `render_mode=html-image` to generate PNG panels in `images/` referenced from `{repo-name}-comic.html`.

- The MCP tool calls the existing `analyze_repository` and `ComicRenderer.render` functions; no prompt logic is duplicated.

## Debugging

The MCP server logs to **stderr** (stdout is reserved for the MCP protocol). In VS Code, open **View → Output** and select the MCP / code-comic channel, or check the terminal where the server was started.

Set in your environment or `.env`:

- `CODE_COMIC_LOG_LEVEL=DEBUG` — verbose step-by-step logs (repo resolution, config, render progress).
- `CODE_COMIC_DEBUG=1` — same as `DEBUG` level; also includes tracebacks in tool error responses.

On failure, tools return structured errors with `error_type`, `hint`, and `repo_path`. Check stderr for the full traceback.

