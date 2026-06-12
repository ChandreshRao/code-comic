# code-comic
A Python CLI application that analyzes a GitHub repository architecture and generates a 4-scene comic explanation.

## Features
- Analyze a local Git repository path
- Extract repository metadata and code structure
- Generate a 4-scene comic script using an LLM prompt
- Generate comic panel images via Hugging Face (`huggingface_hub`) by default, with Gemini as secondary fallback, and HTML/Mermaid fallback on total failure

## Installation

```bash
uv venv
.venv\Scripts\activate
```

```bash
uv pip install -r requirements.txt
```

Or using `uv sync` (recommended):

```bash
uv sync
```

## Usage

```bash
python cli.py path/to/repo
```

Optional arguments:
- `--output-dir`: directory to write outputs (default: `output`)
- `--render-mode`: output format — `image` (PNG panels via Hugging Face Inference API by default, Gemini fallback; auto-fallback to HTML only when all image APIs fail), `html` (Mermaid diagram comic, no image API calls), or `text` (text panels only). Default: `image`
- `--no-image`: alias for `--render-mode text`
- `--context-mode`: `lightweight` (README + docs, minimal tokens) or `comprehensive` (full repo analysis)
- `--debug`: print debug details and re-raise exceptions

## Environment

Recommended environment variables for provider integration (set in `.env`; loaded automatically):
- `HF_TOKEN` or `HUGGINGFACE_API_KEY` (default image provider via Hugging Face Inference API)
- `GEMINI_API_KEY` (secondary image fallback and default LLM when no provider-specific key is set)
- `CODE_COMIC_LLM_API_KEY` or `OPENAI_API_KEY`
- `CODE_COMIC_IMAGE_API_KEY` (overrides provider-specific image keys when set)
- `CODE_COMIC_LLM_MODELS` (comma-separated list; first item is default)
- `CODE_COMIC_IMAGE_MODELS` (comma-separated list; first item is default, rest are fallbacks). Example: `black-forest-labs/FLUX.1-schnell,gemini-2.5-flash-image`
- `CODE_COMIC_LLM_PROVIDER` and `CODE_COMIC_IMAGE_PROVIDER` are optional; when omitted the provider will be inferred from the model identifier (e.g., `black-forest-labs/...` → Hugging Face, `gemini-...` → Gemini).
- `CODE_COMIC_RENDER_MODE`: `image`, `html`, or `text` (default: `image`)

### Virtual environment & .env

Create and activate a virtual environment (recommended):

- Windows

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

- macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the example environment file and populate secrets from `.env.example`:

- Windows

```powershell
copy .env.example .env
```

- macOS / Linux

```bash
cp .env.example .env
```

Edit `.env` and set provider API keys and other values before running the CLI.

## Output

The CLI saves:
- `repo_metadata.json`
- `comic_scenes.json`
- `prompt-1.txt` through `prompt-4.txt` (caption/prompt files for each panel)
- `panel-1.png` through `panel-4.png` (default `--render-mode image` when Hugging Face or Gemini image API succeeds)
- `comic.html` (when `--render-mode html`, or only when image generation fails and auto-fallback kicks in)
- `panel-1.mmd` through `panel-4.mmd` (Mermaid source for each panel, HTML mode only)
- `panel-1.txt` through `panel-4.txt` (when `--render-mode text` or `--no-image`)

For lowest token usage, use lightweight context and HTML rendering:

```bash
python cli.py path/to/repo --context-mode lightweight --render-mode html
```

## Tests

```bash
pytest tests
```

## GitHub Copilot

- See `docs/COPILOT_USAGE.md` for a short, file-oriented summary of how Copilot helped implement features and tests.

## Use with GitHub Copilot (MCP)

- Phase 2 (MCP) provides a thin stdio server exposing two tools: `analyze_repo` and `generate_comic`.
- See `docs/MCP_SETUP.md` for setup and usage instructions (VS Code Copilot Agent integration).

### Sample repo fixture

A minimal TinyCalc project lives at `tests/fixtures/sample-repo/` for smoke-testing the full pipeline.

**Offline smoke test** (no API keys; generates placeholder PNG panels):

```bash
pytest tests/test_sample_repo.py::test_renderer_generates_png_panels_from_sample_repo -v
```

**Manual CLI run** against the fixture:

```bash
python cli.py tests/fixtures/sample-repo --output-dir output/sample-test
```

**Live image generation test** (requires `HF_TOKEN` and/or `GEMINI_API_KEY` in `.env`):

```bash
set CODE_COMIC_RUN_LIVE=1
pytest tests/test_sample_repo.py::test_live_image_generation_from_sample_repo -v
```

If the image API is unavailable, the test skips with a message; the CLI still produces `comic.html` via auto-fallback.
