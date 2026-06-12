from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.config import Config
from src.renderer import ComicRenderer


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze a local GitHub repo and generate a 4-scene comic explaining its architecture."
    )
    parser.add_argument("repo_path", help="Local path to the GitHub repository")
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to write scene and image outputs",
    )
    parser.add_argument(
        "--no-image",
        action="store_true",
        help="Generate only the comic descriptions, no image files",
    )
    parser.add_argument(
        "--context-mode",
        choices=["lightweight", "comprehensive"],
        default="lightweight",
        help="Context gathering mode: 'lightweight' (README + docs, minimal tokens) or "
        "'comprehensive' (full repo analysis, more tokens). Default: lightweight",
    )
    parser.add_argument(
        "--ignore-pattern",
        action="append",
        dest="ignore_patterns",
        help="Additional glob patterns to ignore (can be repeated). "
        "Built-in patterns: node_modules, .venv, __pycache__, etc.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug information during generation",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    config = Config.from_env(
        output_dir=args.output_dir,
        debug=args.debug,
        context_mode=args.context_mode,
        repo_root=args.repo_path,
    )

    # Override ignore patterns from CLI args if provided
    if args.ignore_patterns:
        config.ignore_patterns = (config.ignore_patterns or []) + args.ignore_patterns

    renderer = ComicRenderer(config)

    try:
        result = renderer.render(args.repo_path, generate_images=not args.no_image)
        print(f"Saved comic to: {result['output_dir']}")
        for scene in result["scenes"]:
            print(f"- {scene['title']}: {scene['description']}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        if args.debug:
            raise
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
