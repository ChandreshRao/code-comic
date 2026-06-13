# Setup Guide

This guide walks through installing **code-comic** from scratch, configuring API keys, and running your first comic generation.

## Prerequisites

- **Python 3.10+**
- **Git** (to clone this repo and analyze local repositories)
- **[uv](https://docs.astral.sh/uv/)** (recommended) or `pip` + `venv`

## 1. Clone and install

Clone this repository, then install dependencies from the repo root:

Using `uv` (recommended):

```bash
uv sync
```

Or with a virtual environment:

```bash
python -m venv .venv
```

**Windows (PowerShell)**

```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
```

**macOS / Linux**

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Configure environment variables

Copy the example file and edit it:

**Windows**

```powershell
copy .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

Open `.env` in your editor. The variables below control LLM scene generation, image rendering, and fallbacks. See [What you need for each render mode](#what-you-need-for-each-render-mode) to decide which keys are required.

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Default LLM for comic scripts; secondary image fallback |
| `HF_TOKEN` or `HUGGINGFACE_API_KEY` | Primary image provider (Hugging Face Inference API) |
| `OPENAI_API_KEY` | Optional LLM/image provider if you configure OpenAI models |
| `CODE_COMIC_LLM_MODELS` | Comma-separated LLM models; first is primary, rest are fallbacks |
| `CODE_COMIC_IMAGE_MODELS` | Comma-separated image models; first is primary, rest are fallbacks |
| `CODE_COMIC_RENDER_MODE` | `html-mermaid` (default) or `html-image` |

Never commit `.env` to version control. It is listed in `.gitignore`.

## 3. Get a Gemini API key

**code-comic** uses Gemini by default to generate the 4-panel comic script. You also need a Gemini key for `html-image` mode when Hugging Face image generation fails (automatic fallback).

### Steps

1. Sign in at [Google AI Studio](https://aistudio.google.com/).
2. Open the [API Keys page](https://aistudio.google.com/app/apikey).
3. Click **Create API key** (choose an existing Google Cloud project or create a new one).
4. Copy the key immediately — it is shown in full only once.
5. Paste it into `.env`:

   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

### Reference

- [Using Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key) — official Google documentation
- [Google AI Studio](https://aistudio.google.com/) — playground and key management

### Notes

- The free tier is sufficient for trying **code-comic** on a few repositories.
- Restrict keys to the Gemini API in AI Studio for production use.
- If you use an older “Standard” key, migrate to an Auth key per [Google’s migration guidance](https://ai.google.dev/gemini-api/docs/api-key).

## 4. Get a Hugging Face access token

A Hugging Face token is required only when you use **`html-image`** render mode (AI-generated PNG panels). It is the primary image provider; Gemini is used as a secondary fallback.

### Steps

1. Create a free account at [huggingface.co](https://huggingface.co/join) if you do not have one.
2. Verify your email address (required before you can create tokens).
3. Go to [Access Tokens](https://huggingface.co/settings/tokens).
4. Click **New token**, give it a descriptive name (e.g. `code-comic-dev`), and choose **Read** permission (sufficient for inference).
5. Copy the token (starts with `hf_`) and add it to `.env`:

   ```
   HF_TOKEN=your_huggingface_token_here
   ```

   `HUGGINGFACE_API_KEY` is also accepted.

### Reference

- [User access tokens](https://huggingface.co/docs/hub/security-tokens) — official Hugging Face documentation
- [Hugging Face Inference API](https://huggingface.co/docs/api-inference/index) — how models are invoked
- Token settings: [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### Notes

- Some image models (e.g. `black-forest-labs/FLUX.1-schnell`) may require you to accept the model license on its Hugging Face model page before first use.
- If Hugging Face image generation fails, **code-comic** automatically tries Gemini, then falls back to `html-mermaid` (Mermaid diagrams, no images).

## What you need for each render mode

| Render mode | API keys needed | Cost profile |
|-------------|-----------------|--------------|
| `html-mermaid` (default) | `GEMINI_API_KEY` (or another LLM key you configure) | Low — LLM only, no image API calls |
| `html-image` | `GEMINI_API_KEY` + `HF_TOKEN` recommended | Higher — LLM + image generation per panel |

**Minimal start (no image APIs):**

```bash
python cli.py path/to/repo --render-mode html-mermaid --context-mode lightweight
```

**Full illustrated comic:**

```bash
python cli.py path/to/repo --render-mode html-image
```

## 5. First run

Analyze any local Git repository:

```bash
python cli.py path/to/your-repo
```

Outputs are written to `output/` by default (or `output-YYYYMMDD-HHMMSS/` depending on configuration). Open `{repo-name}-comic.html` in a browser.

Smoke-test without your own repo using the bundled fixture:

```bash
python cli.py tests/fixtures/sample-repo --output-dir output/sample-test
```

## 6. Verify your setup

Run the test suite (no live API calls required for most tests):

```bash
pytest tests
```

Optional live image test (requires `HF_TOKEN` and/or `GEMINI_API_KEY` in `.env`):

```bash
# Windows
set CODE_COMIC_RUN_LIVE=1
pytest tests/test_sample_repo.py::test_live_image_generation_from_sample_repo -v

# macOS / Linux
CODE_COMIC_RUN_LIVE=1 pytest tests/test_sample_repo.py::test_live_image_generation_from_sample_repo -v
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Gemini LLM request failed` / missing API key | `GEMINI_API_KEY` not set | Add key to `.env`; restart your shell |
| `Hugging Face image request failed` | Missing or invalid `HF_TOKEN` | Create a Read token at [settings/tokens](https://huggingface.co/settings/tokens) |
| Image model 403 / gated model | Model license not accepted | Visit the model page on Hugging Face and accept terms |
| Comic renders as Mermaid instead of PNG | Image APIs failed; auto-fallback kicked in | Check `.env` keys; run with `--debug` for details |
| `.env` not loaded | Wrong working directory | Run `cli.py` from the **code-comic** repo root |

Enable debug output:

```bash
python cli.py path/to/repo --debug
```

Or set `CODE_COMIC_DEBUG=1` in `.env`.

## Next steps

- Browse [example outputs](../examples/) — start with the [self-generated `code-comic` comic](code-comic/html-mermaid/code-comic-comic.html), then other repos under `tune-tailor/` and `vishwakarma/`.
- See [MCP_SETUP.md](MCP_SETUP.md) to use **code-comic** from VS Code Copilot agents.
- See [COPILOT_USAGE.md](COPILOT_USAGE.md) for development notes.
