# code-comic
A Python CLI application that analyzes a GitHub repository architecture and generates a 4-scene comic explanation.

## Features
- Analyze a local Git repository path
- Extract repository metadata and code structure
- Generate a 4-scene comic script using an LLM prompt
- Create placeholder panel images via an image API or fallback renderer

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
- `--no-image`: generate only text panels, not images
- `--debug`: print debug details and re-raise exceptions

## Environment

Recommended environment variables for provider integration:
- `CODE_COMIC_LLM_API_KEY` or `OPENAI_API_KEY`
- `CODE_COMIC_IMAGE_API_KEY` or `OPENAI_API_KEY`
- `CODE_COMIC_LLM_PROVIDER` (default: `openai`)
- `CODE_COMIC_IMAGE_PROVIDER` (default: `openai`)

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
- `panel-1.png` through `panel-4.png` (or `.txt` fallback files)

## Tests

```bash
pytest tests
```
