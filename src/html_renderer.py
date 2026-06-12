from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Dict, List

from .utils import save_text


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def _panel_html(scene: Dict[str, str], index: int) -> str:
    title = _escape(scene.get("title", f"Panel {index}"))
    description = _escape(scene.get("description", ""))
    speech = _escape(scene.get("speech_bubble") or scene.get("panel_text", ""))
    mermaid = scene.get("mermaid", "").strip()
    if not mermaid:
        mermaid = 'flowchart TD\n    A["Architecture"] --> B["Details"]'

    return f"""
    <article class="panel" aria-label="Panel {index}">
      <header class="panel-header">
        <span class="panel-number">{index}</span>
        <h2>{title}</h2>
      </header>
      <div class="panel-body">
        <pre class="mermaid">{mermaid}</pre>
      </div>
      <p class="panel-description">{description}</p>
      <div class="speech-bubble">
        <p>{speech}</p>
      </div>
    </article>
    """


def render_comic_html(
    scenes: List[Dict[str, str]],
    metadata: Dict[str, Any],
    output_path: Path,
) -> Path:
    repo_path = metadata.get("path", "Repository")
    page_title = _escape(f"Code Comic: {repo_path}")
    languages = ", ".join(metadata.get("languages", [])) or "unknown"
    total_files = metadata.get("total_files", 0)

    panels = "\n".join(_panel_html(scene, idx) for idx, scene in enumerate(scenes[:4], start=1))

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{page_title}</title>
  <style>
    :root {{
      --ink: #1a1a2e;
      --paper: #fffef5;
      --accent: #e94560;
      --border: #1a1a2e;
      --bubble: #ffffff;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: "Comic Sans MS", "Chalkboard SE", "Segoe UI", sans-serif;
      background: var(--paper);
      background-image: radial-gradient(circle, #ddd 1px, transparent 1px);
      background-size: 12px 12px;
      color: var(--ink);
      min-height: 100vh;
      padding: 1.5rem;
    }}
    .comic-header {{
      text-align: center;
      margin-bottom: 1.5rem;
      border: 3px solid var(--border);
      background: white;
      padding: 1rem;
      box-shadow: 4px 4px 0 var(--border);
    }}
    .comic-header h1 {{
      font-size: 1.75rem;
      letter-spacing: 0.02em;
    }}
    .comic-header .meta {{
      margin-top: 0.5rem;
      font-size: 0.9rem;
      opacity: 0.85;
    }}
    .comic-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1.25rem;
      max-width: 1200px;
      margin: 0 auto;
    }}
    @media (max-width: 768px) {{
      .comic-grid {{ grid-template-columns: 1fr; }}
    }}
    .panel {{
      border: 3px solid var(--border);
      background: white;
      box-shadow: 5px 5px 0 var(--border);
      display: flex;
      flex-direction: column;
      min-height: 320px;
    }}
    .panel-header {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.6rem 0.75rem;
      border-bottom: 2px solid var(--border);
      background: #ffeaa7;
    }}
    .panel-number {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.75rem;
      height: 1.75rem;
      border: 2px solid var(--border);
      border-radius: 50%;
      font-weight: bold;
      background: var(--accent);
      color: white;
      flex-shrink: 0;
    }}
    .panel-header h2 {{
      font-size: 1rem;
      line-height: 1.2;
    }}
    .panel-body {{
      flex: 1;
      padding: 0.75rem;
      overflow: auto;
      background: #f8f9fa;
    }}
    .panel-body .mermaid {{
      background: transparent;
      border: none;
      font-family: inherit;
      font-size: 0.85rem;
      white-space: pre-wrap;
      margin: 0;
    }}
    .panel-description {{
      padding: 0.5rem 0.75rem;
      font-size: 0.8rem;
      font-style: italic;
      border-top: 1px dashed var(--border);
      color: #444;
    }}
    .speech-bubble {{
      position: relative;
      margin: 0.75rem;
      padding: 0.75rem 1rem;
      background: var(--bubble);
      border: 2px solid var(--border);
      border-radius: 1rem;
    }}
    .speech-bubble::after {{
      content: "";
      position: absolute;
      bottom: -12px;
      left: 24px;
      width: 0;
      height: 0;
      border-left: 10px solid transparent;
      border-right: 10px solid transparent;
      border-top: 12px solid var(--border);
    }}
    .speech-bubble p {{
      font-size: 0.9rem;
      line-height: 1.4;
    }}
    .comic-footer {{
      text-align: center;
      margin-top: 1.5rem;
      font-size: 0.75rem;
      opacity: 0.7;
    }}
  </style>
</head>
<body>
  <header class="comic-header">
    <h1>{page_title}</h1>
    <p class="meta">Languages: {_escape(languages)} &middot; {total_files} files analyzed</p>
  </header>
  <main class="comic-grid">
    {panels}
  </main>
  <footer class="comic-footer">Generated by code-comic</footer>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'neutral', securityLevel: 'strict' }});
  </script>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")

    for idx, scene in enumerate(scenes[:4], start=1):
        mermaid = scene.get("mermaid", "").strip()
        if mermaid:
            save_text(output_path.parent / f"panel-{idx}.mmd", mermaid)

    return output_path


def _panel_html_image(scene: Dict[str, str], index: int, image_rel_path: str) -> str:
    title = _escape(scene.get("title", f"Panel {index}"))
    description = _escape(scene.get("description", ""))
    speech = _escape(scene.get("speech_bubble") or scene.get("panel_text", ""))
    src = _escape(image_rel_path)

    return f"""
    <article class="panel" aria-label="Panel {index}">
      <header class="panel-header">
        <span class="panel-number">{index}</span>
        <h2>{title}</h2>
      </header>
      <div class="panel-body">
        <img src="{src}" alt="{title}" class="panel-image">
      </div>
      <p class="panel-description">{description}</p>
      <div class="speech-bubble">
        <p>{speech}</p>
      </div>
    </article>
    """


def render_comic_html_with_images(
    scenes: List[Dict[str, str]],
    metadata: Dict[str, Any],
    output_path: Path,
    image_rel_paths: List[str],
) -> Path:
    repo_path = metadata.get("path", "Repository")
    page_title = _escape(f"Code Comic: {repo_path}")
    languages = ", ".join(metadata.get("languages", [])) or "unknown"
    total_files = metadata.get("total_files", 0)

    panels = "\n".join(
        _panel_html_image(scene, idx, image_rel_paths[idx - 1])
        for idx, scene in enumerate(scenes[:4], start=1)
    )

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{page_title}</title>
  <style>
    :root {{
      --ink: #1a1a2e;
      --paper: #fffef5;
      --accent: #e94560;
      --border: #1a1a2e;
      --bubble: #ffffff;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: "Comic Sans MS", "Chalkboard SE", "Segoe UI", sans-serif;
      background: var(--paper);
      background-image: radial-gradient(circle, #ddd 1px, transparent 1px);
      background-size: 12px 12px;
      color: var(--ink);
      min-height: 100vh;
      padding: 1.5rem;
    }}
    .comic-header {{
      text-align: center;
      margin-bottom: 1.5rem;
      border: 3px solid var(--border);
      background: white;
      padding: 1rem;
      box-shadow: 4px 4px 0 var(--border);
    }}
    .comic-header h1 {{
      font-size: 1.75rem;
      letter-spacing: 0.02em;
    }}
    .comic-header .meta {{
      margin-top: 0.5rem;
      font-size: 0.9rem;
      opacity: 0.85;
    }}
    .comic-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1.25rem;
      max-width: 1200px;
      margin: 0 auto;
    }}
    @media (max-width: 768px) {{
      .comic-grid {{ grid-template-columns: 1fr; }}
    }}
    .panel {{
      border: 3px solid var(--border);
      background: white;
      box-shadow: 5px 5px 0 var(--border);
      display: flex;
      flex-direction: column;
      min-height: 320px;
    }}
    .panel-header {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.6rem 0.75rem;
      border-bottom: 2px solid var(--border);
      background: #ffeaa7;
    }}
    .panel-number {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.75rem;
      height: 1.75rem;
      border: 2px solid var(--border);
      border-radius: 50%;
      font-weight: bold;
      background: var(--accent);
      color: white;
      flex-shrink: 0;
    }}
    .panel-header h2 {{
      font-size: 1rem;
      line-height: 1.2;
    }}
    .panel-body {{
      flex: 1;
      padding: 0.75rem;
      overflow: auto;
      background: #f8f9fa;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .panel-body .panel-image {{
      max-width: 100%;
      height: auto;
      border: 2px solid var(--border);
    }}
    .panel-description {{
      padding: 0.5rem 0.75rem;
      font-size: 0.8rem;
      font-style: italic;
      border-top: 1px dashed var(--border);
      color: #444;
    }}
    .speech-bubble {{
      position: relative;
      margin: 0.75rem;
      padding: 0.75rem 1rem;
      background: var(--bubble);
      border: 2px solid var(--border);
      border-radius: 1rem;
    }}
    .speech-bubble::after {{
      content: "";
      position: absolute;
      bottom: -12px;
      left: 24px;
      width: 0;
      height: 0;
      border-left: 10px solid transparent;
      border-right: 10px solid transparent;
      border-top: 12px solid var(--border);
    }}
    .speech-bubble p {{
      font-size: 0.9rem;
      line-height: 1.4;
    }}
    .comic-footer {{
      text-align: center;
      margin-top: 1.5rem;
      font-size: 0.75rem;
      opacity: 0.7;
    }}
  </style>
</head>
<body>
  <header class="comic-header">
    <h1>{page_title}</h1>
    <p class="meta">Languages: {_escape(languages)} &middot; {total_files} files analyzed</p>
  </header>
  <main class="comic-grid">
    {panels}
  </main>
  <footer class="comic-footer">Generated by code-comic</footer>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path
