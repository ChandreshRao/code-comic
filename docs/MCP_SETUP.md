# MCP Setup (Phase 2)

The `code-comic` MCP server exposes two tools: `analyze_repo` and `generate_comic`. It reuses the same `analyze_repository` and `ComicRenderer.render` code paths as `cli.py` — no duplicated prompt logic.

## Three ways to run it

| Client | Config location | Best for |
|--------|-----------------|----------|
| **VS Code Copilot Agent** | `.vscode/mcp.json` in this repo | Interactive demo in the IDE |
| **GitHub Copilot CLI** | Workspace `.vscode/mcp.json` (auto-discovered) or `~/.copilot/mcp-config.json` | Terminal-based agent testing |
| **Direct Python** | N/A | Debugging: `uv run python -m src.mcp_server` |

---

## 1. VS Code Copilot Agent (demo in this repo)

1. Open this repository in VS Code.
2. Start the MCP server defined in `.vscode/mcp.json` (Copilot Agent → Start server).
3. Ask the agent to call `generate_comic` with `repo_path` set to `tests/fixtures/sample-repo` and `render_mode=html-mermaid`.

**Low-cost default prompt:**

> Use `generate_comic` on `.` with `render_mode=html-mermaid` and `context_mode=lightweight`.

Preview output: [`examples/code-comic/html-mermaid/code-comic-comic.html`](../examples/code-comic/html-mermaid/code-comic-comic.html)

Or use the bundled fixture:

> Use `generate_comic` on `tests/fixtures/sample-repo` with `render_mode=html-mermaid` and `context_mode=lightweight`.

---

## 2. GitHub Copilot CLI (terminal)

The author validated the MCP server end-to-end from **Copilot CLI**, including the heavier path:

> Use `generate_comic` with `html-image` and `comprehensive` mode.

### Prerequisites

- [Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/about-copilot-cli) installed and signed in
- `uv` on your PATH (same as `.vscode/mcp.json`)
- For `html-image`: `GEMINI_API_KEY` and `HF_TOKEN` in `.env` — see [SETUP.md](SETUP.md)

### Steps

1. `cd` into the `code-comic` repo root (so Copilot CLI picks up `.vscode/mcp.json`).
2. Start Copilot CLI.
3. Run `/mcp show` — you should see `code-comic` with `analyze_repo` and `generate_comic`.
4. Prompt the agent, for example:

```
Use generate_comic on . with render_mode=html-image
and context_mode=comprehensive. Report output_dir, html_file, and whether fallback was used.
```

Preview of a prior run: [`examples/code-comic/html-image/code-comic-comic.html`](../examples/code-comic/html-image/code-comic-comic.html)

Or against the sample fixture:

```
Use generate_comic on tests/fixtures/sample-repo with render_mode=html-image
and context_mode=comprehensive. Report output_dir, html_file, and whether fallback was used.
```

### If the server is not auto-discovered

Add it manually in the CLI session with `/mcp add` (type: **stdio**), or append to `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "code-comic": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/code-comic", "python", "-m", "src.mcp_server"],
      "env": {}
    }
  }
}
```

Replace `/absolute/path/to/code-comic` with your clone path. Environment variables from your shell (including those loaded from `.env` if you export them) are inherited unless overridden in `env`.

**Official reference:** [Add MCP servers to Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers)

---

## 3. Any other repo (user-profile config)

When analyzing a project that is not the `code-comic` clone:

1. Install `code-comic` on your machine and note the absolute path to the clone.
2. In VS Code: `MCP: Open User Configuration` → point `code-comic-root` input to that path.
3. Start the `code-comic` server and pass `repo_path` or set `CODE_COMIC_REPO_PATH=${workspaceFolder}` in the MCP inputs.

Same idea in Copilot CLI: register the server with `--directory` pointing at your `code-comic` install, then pass `repo_path` to the target workspace.

---

## Tool parameters

### `analyze_repo`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `repo_path` | cwd or `CODE_COMIC_REPO_PATH` | Local Git repository to analyze |
| `context_mode` | `lightweight` | `lightweight` (README + docs) or `comprehensive` (full repo) |

### `generate_comic`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `repo_path` | cwd or `CODE_COMIC_REPO_PATH` | Local Git repository |
| `context_mode` | `lightweight` | `lightweight` or `comprehensive` |
| `render_mode` | `html-mermaid` | `html-mermaid` (Mermaid diagrams) or `html-image` (AI PNG panels) |
| `output_dir` | `code-comic-YYYYMMDD-HHMMSS` under target repo | Where artifacts are written |

Returns JSON with `output_dir`, `render_mode_used`, `html_file`, `scenes`, and `fallback` (if image mode degraded to Mermaid).

---

## Notes

- See [SETUP.md](SETUP.md) for API key configuration before using `render_mode=html-image`.
- Defaults are tuned for low-cost operation: `context_mode=lightweight`, `render_mode=html-mermaid` (no image API calls).
- `html-image` + `comprehensive` is the highest-cost combination — useful for integration testing, not everyday demos.
- When `output_dir` is omitted, `generate_comic` writes to `code-comic-YYYYMMDD-HHMMSS` under the target repo (each run gets a new folder).
- Author testing notes (VS Code + CLI): [COPILOT_USAGE.md](COPILOT_USAGE.md#4-end-to-end-mcp-validation-copilot-cli).

## Debugging

The MCP server logs to **stderr** (stdout is reserved for the MCP protocol). In VS Code, open **View → Output** and select the MCP / code-comic channel, or check the terminal where the server was started.

Set in your environment or `.env`:

- `CODE_COMIC_LOG_LEVEL=DEBUG` — verbose step-by-step logs (repo resolution, config, render progress).
- `CODE_COMIC_DEBUG=1` — same as `DEBUG` level; also includes tracebacks in tool error responses.

On failure, tools return structured errors with `error_type`, `hint`, and `repo_path`. Check stderr for the full traceback.
