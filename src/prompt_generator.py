from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def _sanitize_mermaid_id(name: str) -> str:
    """Convert a file/entry name to a valid Mermaid node ID."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if cleaned and cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"
    return cleaned or "node"


_INVALID_TITLE_PATTERNS = (
    r"```",
    r"^\[\s*\{",
    r'"title"\s*:',
    r"^\}\s*\]",
    r"^\[ \{",
)

_GENERIC_TITLE_PATTERNS = (
    r"^meet the repository$",
    r"^how code organizes$",
    r"^dependencies and tools$",
    r"^developer journey$",
)


def _scene_title_looks_invalid(title: str) -> bool:
    if not title or len(title.strip()) < 2:
        return True
    for pattern in _INVALID_TITLE_PATTERNS:
        if re.search(pattern, title.strip()):
            return True
    return False


def _scene_text_looks_invalid(text: str) -> bool:
    if not text:
        return True
    if "```" in text or '"title"' in text or text.strip() in ("[ {", "} ]", "{"):
        return True
    return False


def _looks_like_image_prompt(text: str) -> bool:
    if len(text) > 150:
        return True
    image_cues = (
        "standing next to",
        "a user typing",
        "a friendly",
        "a stylized arrow",
        "depicted as",
        "terminal window",
        "magnifying glass",
        "represented as",
        "icon labeled",
    )
    lowered = text.lower()
    return any(cue in lowered for cue in image_cues)


def _looks_bland(title: str, speech_bubble: str) -> bool:
    if any(re.match(pat, title.strip(), re.IGNORECASE) for pat in _GENERIC_TITLE_PATTERNS):
        return True
    if speech_bubble.strip().endswith(".") and len(speech_bubble) > 120:
        return True
    bland_phrases = (
        "explain a repository concept",
        "show the repo architecture",
        "introduce the project structure",
    )
    combined = f"{title} {speech_bubble}".lower()
    return any(phrase in combined for phrase in bland_phrases)


def _extract_project_name(metadata: Dict[str, Any]) -> str:
    content = metadata.get("content", {})
    for filename, filecontent in content.items():
        if "readme" in filename.lower() and filecontent:
            for line in filecontent.splitlines():
                line = line.strip().lstrip("#").strip()
                if line and not line.startswith("["):
                    return line.split("\n")[0][:40]
    path = metadata.get("path", "")
    if path:
        return Path(path).name.replace("-", " ").replace("_", " ").title()
    return "this codebase"


def _extract_json_from_text(raw_text: str) -> Optional[Any]:
    """Extract a JSON value from raw LLM output, including markdown-fenced payloads."""
    text = raw_text.strip()
    if not text:
        return None

    candidates: List[str] = [text]

    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        candidates.insert(0, fence_match.group(1).strip())

    array_match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
    if array_match:
        candidates.insert(0, array_match.group(0))

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    return None


def _creative_guidelines() -> str:
    path = Path(__file__).resolve().parent / "prompts" / "creative_guidelines.txt"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return (
        "Write like a witty tech comic, not a README summary. "
        "Each panel is one beat in a story arc: (1) hook the reader, (2) show how requests flow, "
        "(3) reveal the clever core logic, (4) land the payoff for a new contributor. "
        "Use punchy titles with personality (wordplay welcome). "
        "speech_bubble must be a short, spoken line — max 20 words, first-person or conversational, "
        "never a visual art direction or image prompt. "
        "description is the narrator caption under the panel — vivid but concise (1-2 sentences). "
        "CRITICAL: every concrete noun in speech_bubble or description (function names, file names, "
        "library names) must come verbatim from the repository details below. "
        "You may invent personality, voice, and metaphor freely — but never invent a file, "
        "function, dependency, or feature that isn't listed."
    )


def _prompt_template_path(render_mode: str) -> Path:
    folder = Path(__file__).resolve().parent / "prompts"
    filename = "html_scene_prompt.md" if render_mode == "html" else "scene_prompt.md"
    return folder / filename


def _load_prompt_template(render_mode: str) -> str:
    path = _prompt_template_path(render_mode)
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            pass
    return ""


def _render_template(template: str, mapping: Dict[str, str]) -> str:
    try:
        return template.format(**mapping)
    except Exception:
        return template


def build_scene_prompt(repo_metadata: Dict[str, Any], render_mode: str = "image") -> str:
    project = _extract_project_name(repo_metadata)
    bullets: List[str] = []
    bullets.append(f"Project name: {project}")
    bullets.append(f"Repository path: {repo_metadata.get('path')}")
    bullets.append(
        f"Top-level entries: {', '.join(repo_metadata.get('top_level', [])) or 'none'}"
    )
    bullets.append(
        f"Detected languages: {', '.join(repo_metadata.get('languages', [])) or 'unknown'}"
    )
    bullets.append(f"Package files: {', '.join(repo_metadata.get('package_files', [])) or 'none'}")
    bullets.append(
        f"Sample files: {', '.join(repo_metadata.get('sample_files', [])[:8]) or 'none'}"
    )
    bullets.append(f"Total files: {repo_metadata.get('total_files', 0)}")
    if repo_metadata.get("detected_features"):
        bullets.append(f"Special markers: {', '.join(repo_metadata['detected_features'])}")

    context_mode = repo_metadata.get("context_mode", "lightweight")
    if context_mode == "comprehensive":
        files_analyzed = repo_metadata.get("files_analyzed", 0)
        if files_analyzed > 0:
            bullets.append(
                f"Analysis scope: Comprehensive ({files_analyzed} files analyzed)"
            )
    else:
        bullets.append("Analysis scope: Lightweight (README and key documentation)")

    guidelines = _creative_guidelines()
    repo_details = "\n".join(bullets)

    content_summary = ""
    if repo_metadata.get("content"):
        content = repo_metadata.get("content", {})
        if content:
            content_summary = "Repository Content Summary:\n"
            content_summary += "=" * 50 + "\n"
            files_to_include: List[tuple[str, str]] = []
            for filename, filecontent in content.items():
                if "readme" in filename.lower():
                    files_to_include.append((filename, filecontent))
                    break

            for filename, filecontent in content.items():
                if len(files_to_include) >= 5:
                    break
                if "readme" not in filename.lower():
                    files_to_include.append((filename, filecontent))

            for filename, filecontent in files_to_include[:5]:
                if filecontent:
                    display_content = (
                        filecontent[:500] + "\n[... truncated ...]"
                        if len(filecontent) > 500
                        else filecontent
                    )
                    content_summary += f"\n--- File: {filename} ---\n{display_content}\n"

    template = _load_prompt_template(render_mode)
    if template:
        return _render_template(
            template,
            {
                "project": project,
                "guidelines": guidelines,
                "repo_details": repo_details,
                "content_summary": content_summary,
            },
        )

    if render_mode == "html":
        prompt = (
            f"You are a developer-turned-cartoonist creating a 4-panel comic about '{project}'. "
            f"{guidelines} "
            "For each scene provide: title, description, speech_bubble, mermaid. "
            "mermaid must be valid flowchart syntax (max 8 nodes, no spaces in node IDs) "
            "and illustrate that panel's specific idea using real file/module names. "
            "Return ONLY a raw JSON array with exactly four objects. "
            "Do NOT wrap in markdown code fences. "
            "Keys per object: title, description, speech_bubble, mermaid.\n\n"
            "Repository details:\n"
            + repo_details
        )
    else:
        prompt = (
            f"You are a developer-turned-cartoonist creating a 4-panel comic about '{project}'. "
            f"{guidelines} "
            "For each scene provide: title, description, panel_text. "
            "panel_text is a brief visual note for an illustrator (1 sentence max), not the speech bubble. "
            "Return ONLY a raw JSON array with exactly four objects. "
            "Do NOT wrap in markdown code fences. "
            "Keys per object: title, description, panel_text.\n\n"
            "Repository details:\n"
            + repo_details
        )

    if content_summary:
        prompt += f"\n\n{content_summary}"

    return prompt


def _normalize_scene(scene: Dict[str, Any], idx: int) -> Dict[str, str]:
    title = str(scene.get("title", f"Scene {idx + 1}"))
    description = str(scene.get("description", ""))
    speech_bubble = str(
        scene.get("speech_bubble") or scene.get("panel_text") or description
    )
    panel_text = str(scene.get("panel_text") or speech_bubble)
    mermaid = str(scene.get("mermaid", ""))
    return {
        "title": title,
        "description": description,
        "panel_text": panel_text,
        "speech_bubble": speech_bubble,
        "mermaid": mermaid,
    }


def parse_scene_output(raw_text: str) -> List[Dict[str, str]]:
    payload = _extract_json_from_text(raw_text)
    if payload is not None:
        if isinstance(payload, list):
            scenes_raw = payload
        elif isinstance(payload, dict) and "scenes" in payload:
            scenes_raw = payload["scenes"]
        else:
            scenes_raw = None

        if isinstance(scenes_raw, list) and scenes_raw:
            normalized = [_normalize_scene(scene, idx) for idx, scene in enumerate(scenes_raw[:4])]
            while len(normalized) < 4:
                normalized.append(_normalize_scene({}, len(normalized)))
            return normalized

    sections = [part.strip() for part in re.split(r"Scene\s+\d+", raw_text, flags=re.IGNORECASE) if part.strip()][:4]
    if not sections:
        sections = [part.strip() for part in raw_text.split("Scene") if part.strip()][:4]

    scenes = []
    for index, section in enumerate(sections, start=1):
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        title = lines[0] if lines else f"Scene {index}"
        description = " ".join(lines[1:3]) if len(lines) > 1 else ""
        panel_text = " ".join(lines[3:5]) if len(lines) > 3 else description
        scenes.append(
            {
                "title": title,
                "description": description,
                "panel_text": panel_text,
                "speech_bubble": panel_text,
                "mermaid": "",
            }
        )

    while len(scenes) < 4:
        scenes.append(
            {
                "title": f"Scene {len(scenes) + 1}",
                "description": "Explain a repository concept.",
                "panel_text": "Show the repo architecture as a friendly illustration.",
                "speech_bubble": "Show the repo architecture as a friendly illustration.",
                "mermaid": "",
            }
        )

    return scenes


def scenes_are_valid(scenes: List[Dict[str, str]]) -> bool:
    if len(scenes) != 4:
        return False
    invalid_titles = sum(1 for scene in scenes if _scene_title_looks_invalid(scene.get("title", "")))
    if invalid_titles >= 1:
        return False
    invalid_bubbles = sum(
        1 for scene in scenes if _scene_text_looks_invalid(scene.get("speech_bubble", ""))
    )
    if invalid_bubbles >= 2:
        return False
    return True


def _build_repo_structure_mermaid(metadata: Dict[str, Any]) -> str:
    top_level = metadata.get("top_level", [])[:4]
    nodes = ["Repo[Repository]"]
    edges = []
    for entry in top_level:
        node_id = _sanitize_mermaid_id(entry)
        label = entry.replace('"', "'")
        nodes.append(f'{node_id}["{label}"]')
        edges.append(f"Repo --> {node_id}")
    return "flowchart TD\n    " + "\n    ".join(nodes + edges)


def _build_code_flow_mermaid(metadata: Dict[str, Any]) -> str:
    sample_files = metadata.get("sample_files", [])
    main_files = [f for f in sample_files if f.replace("\\", "/").endswith("main.py")]
    service_files = [
        f
        for f in sample_files
        if f.endswith(".py")
        and "__init__" not in f.replace("\\", "/")
        and not f.replace("\\", "/").endswith("main.py")
    ]

    if main_files and service_files:
        main_path = main_files[0].replace("\\", "/")
        service_path = service_files[0].replace("\\", "/")
        main_id = _sanitize_mermaid_id(Path(main_path).stem)
        service_id = _sanitize_mermaid_id(Path(service_path).stem)
        main_label = Path(main_path).name
        service_label = Path(service_path).name
        return (
            "flowchart LR\n"
            f'    User["User / CLI"] --> {main_id}["{main_label}"]\n'
            f'    {main_id} --> {service_id}["{service_label}"]\n'
            f'    {service_id} --> Output["Output"]'
        )

    py_files = [f.replace("\\", "/") for f in sample_files if f.endswith(".py")][:4]
    if len(py_files) >= 2:
        ids = [_sanitize_mermaid_id(Path(path).stem) for path in py_files]
        lines = ["flowchart LR"]
        for path, node_id in zip(py_files, ids):
            lines.append(f'    {node_id}["{Path(path).name}"]')
        for i in range(len(ids) - 1):
            lines.append(f"    {ids[i]} --> {ids[i + 1]}")
        return "\n".join(lines)

    return 'flowchart TD\n    A["Source"] --> B["Application"]'


def _build_dependencies_mermaid(metadata: Dict[str, Any]) -> str:
    package_files = metadata.get("package_files", [])[:3]
    pkg_nodes = []
    edges = []
    for i, pkg in enumerate(package_files or ["requirements.txt"]):
        node_id = f"pkg{i}"
        pkg_nodes.append(f'{node_id}["{pkg}"]')
        edges.append(f"Tools --> {node_id}")
    return "flowchart TD\n    Tools[Dev Tools]\n    " + "\n    ".join(pkg_nodes + edges)


def _build_developer_journey_mermaid(metadata: Dict[str, Any]) -> str:
    languages = ", ".join(metadata.get("languages", ["unknown"]))
    return (
        "flowchart TD\n"
        f'    Dev["Developer"] --> Read["Read docs"]\n'
        f'    Read --> Code["Write {languages} code"]\n'
        f'    Code --> Ship["Ship changes"]'
    )


def _build_calculation_mermaid(metadata: Dict[str, Any]) -> str:
    sample_files = metadata.get("sample_files", [])
    calc_files = [f for f in sample_files if "calc" in f.replace("\\", "/").lower() and f.endswith(".py")]
    if calc_files:
        calc_path = calc_files[0].replace("\\", "/")
        calc_id = _sanitize_mermaid_id(Path(calc_path).stem)
        calc_label = Path(calc_path).name
        return (
            "flowchart TD\n"
            f'    Input["Operands"] --> {calc_id}["{calc_label}"]\n'
            f'    {calc_id} --> Add["add()"]\n'
            f'    {calc_id} --> Sub["subtract()"]\n'
            f'    Add --> Result["Result"]\n'
            f'    Sub --> Result'
        )
    return _build_code_flow_mermaid(metadata)


def _build_fallback_mermaid(metadata: Dict[str, Any], panel_index: int) -> str:
    builders = (
        _build_repo_structure_mermaid,
        _build_code_flow_mermaid,
        _build_calculation_mermaid,
        _build_developer_journey_mermaid,
    )
    if 0 <= panel_index < len(builders):
        return builders[panel_index](metadata)
    return _build_developer_journey_mermaid(metadata)


def _build_mermaid_for_scene(scene: Dict[str, str], metadata: Dict[str, Any], idx: int) -> str:
    text = f"{scene.get('title', '')} {scene.get('description', '')}".lower()
    if any(keyword in text for keyword in ("meet", "intro", "repository", "structure", "overview", "mighty", "welcome")):
        return _build_repo_structure_mermaid(metadata)
    if any(keyword in text for keyword in ("flow", "cli", "main", "gateway", "workflow", "entry", "request")):
        return _build_code_flow_mermaid(metadata)
    if any(keyword in text for keyword in ("calc", "core", "logic", "operation", "math", "brain")):
        return _build_calculation_mermaid(metadata)
    if any(keyword in text for keyword in ("depend", "tool", "package", "pyproject", "foundation")):
        return _build_dependencies_mermaid(metadata)
    if any(keyword in text for keyword in ("developer", "journey", "contribut", "ship", "result", "payoff")):
        return _build_developer_journey_mermaid(metadata)
    return _build_fallback_mermaid(metadata, idx)


def render_fallback_scenes(repo_metadata: Dict[str, Any]) -> List[Dict[str, str]]:
    project = _extract_project_name(repo_metadata)
    languages = ", ".join(repo_metadata.get("languages", ["unknown"]))
    package_files = ", ".join(repo_metadata.get("package_files", ["none"]))
    top_level = repo_metadata.get("top_level", [])
    main_file = next(
        (f for f in repo_metadata.get("sample_files", []) if f.replace("\\", "/").endswith("main.py")),
        "main.py",
    )
    core_file = next(
        (
            f
            for f in repo_metadata.get("sample_files", [])
            if f.endswith(".py") and "main" not in f.replace("\\", "/").lower() and "__init__" not in f
        ),
        "core module",
    )

    templates = [
        {
            "title": f"Enter the {project} Universe",
            "description": (
                f"Every saga starts somewhere — for {project}, it starts with "
                f"{', '.join(top_level[:3]) or 'a handful of well-named folders'}."
            ),
            "speech_bubble": f"Ah, {project}! Small repo, big personality. Let me show you around.",
        },
        {
            "title": "The Command Line Sends a Hero",
            "description": (
                f"A user invokes `{main_file}` and the runtime wakes up — parsing args, "
                "routing work, and refusing to panic."
            ),
            "speech_bubble": "You type the command. I parse the args. Teamwork!",
        },
        {
            "title": "Where the Real Magic Happens",
            "description": (
                f"Deep inside `{core_file}`, the core logic does the heavy lifting while "
                f"{main_file} stays lean and friendly."
            ),
            "speech_bubble": "Leave the math to me — I live for add() and subtract()!",
        },
        {
            "title": "Output, Applause, Repeat",
            "description": (
                f"Results hit stdout, configs live in {package_files}, and a new dev "
                f"knows exactly where to start hacking on {project}."
            ),
            "speech_bubble": "Print the answer, commit the fix, grab coffee. Developer loop complete.",
        },
    ]

    scenes = []
    for idx, template in enumerate(templates):
        mermaid = _build_fallback_mermaid(repo_metadata, idx)
        scenes.append(
            {
                "title": template["title"],
                "description": template["description"],
                "speech_bubble": template["speech_bubble"],
                "panel_text": template["speech_bubble"],
                "mermaid": mermaid,
            }
        )
    return scenes


def enrich_scenes(scenes: List[Dict[str, str]], metadata: Dict[str, Any]) -> List[Dict[str, str]]:
    """Fill missing mermaid diagrams and repair bland or broken scene fields."""
    fallback_scenes = render_fallback_scenes(metadata)
    enriched: List[Dict[str, str]] = []

    for idx, scene in enumerate(scenes[:4]):
        fallback = fallback_scenes[idx]
        merged = dict(fallback)

        for key, value in scene.items():
            if value and not _scene_text_looks_invalid(str(value)):
                merged[key] = value

        if _scene_title_looks_invalid(merged.get("title", "")):
            merged["title"] = fallback["title"]

        if not merged.get("description") or _scene_text_looks_invalid(merged.get("description", "")):
            merged["description"] = fallback["description"]

        bubble = merged.get("speech_bubble", "")
        if (
            not bubble
            or _scene_text_looks_invalid(bubble)
            or _looks_like_image_prompt(bubble)
            or bubble.strip() == merged.get("description", "").strip()
        ):
            merged["speech_bubble"] = fallback["speech_bubble"]

        if _looks_like_image_prompt(merged.get("panel_text", "")):
            merged["panel_text"] = merged["speech_bubble"]
        elif not merged.get("panel_text"):
            merged["panel_text"] = merged["speech_bubble"]

        if not merged.get("mermaid", "").strip():
            merged["mermaid"] = _build_mermaid_for_scene(merged, metadata, idx)

        enriched.append(_normalize_scene(merged, idx))

    while len(enriched) < 4:
        enriched.append(fallback_scenes[len(enriched)])

    return enriched


def resolve_scenes(raw_output: str, metadata: Dict[str, Any], render_mode: str = "image") -> List[Dict[str, str]]:
    """Parse LLM output, validate scenes, and fall back or enrich using repository metadata."""
    if raw_output.startswith("[Fallback LLM]"):
        return render_fallback_scenes(metadata)

    scenes = parse_scene_output(raw_output)
    if not scenes_are_valid(scenes):
        return render_fallback_scenes(metadata)

    bland_count = sum(
        1 for scene in scenes if _looks_bland(scene.get("title", ""), scene.get("speech_bubble", ""))
    )
    if bland_count >= 3:
        return render_fallback_scenes(metadata)

    needs_enrichment = (
        render_mode == "html"
        or any(not scene.get("mermaid", "").strip() for scene in scenes)
        or any(
            _looks_like_image_prompt(scene.get("speech_bubble") or scene.get("panel_text", ""))
            for scene in scenes
        )
        or bland_count >= 1
    )
    if needs_enrichment:
        return enrich_scenes(scenes, metadata)

    return scenes


def generate_image_prompts_from_repo(repo_path: str, output_dir: str, llm_client: Any) -> List[str]:
    """Generate per-scene image prompt text files from repository context."""
    from .analyzer import analyze_repository
    from .utils import ensure_output_dir, save_text

    metadata = analyze_repository(repo_path)
    scene_request = build_scene_prompt(metadata)
    raw_output = llm_client.generate_text(scene_request)
    scenes = resolve_scenes(raw_output, metadata)

    out_dir = ensure_output_dir(output_dir)
    paths: List[str] = []
    for idx, scene in enumerate(scenes, start=1):
        p = out_dir / f"prompt-{idx}.txt"
        panel_text = scene.get("panel_text", "")
        save_text(p, panel_text)
        paths.append(str(p))

    return paths
