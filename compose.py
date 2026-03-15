#!/usr/bin/env python3
"""
compose.py — Recompose a decomposed Devchain directory back into a single JSON.

Usage: python3 compose.py <directory>

Reads the directory produced by decompose.py and writes a single JSON file
next to it (same name + .json extension).
"""

import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------

def read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_prompts(prompts_dir: Path) -> list:
    """Read prompt subdirectories, merge prompt.json + content.md."""
    prompts = []
    subdirs = sorted(
        [d for d in prompts_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
    )
    for d in subdirs:
        meta = read_json(d / "prompt.json")

        with open(d / "content.md", "r", encoding="utf-8") as f:
            content = f.read()

        # Rebuild with original key order.
        key_order = meta.pop("_keyOrder", None)
        if key_order:
            prompt = {}
            for k in key_order:
                if k == "content":
                    prompt["content"] = content
                else:
                    prompt[k] = meta[k]
        else:
            # Fallback: insert content after title.
            prompt = {}
            for k, v in meta.items():
                prompt[k] = v
                if k == "title":
                    prompt["content"] = content

        prompts.append(prompt)
    return prompts


def read_named_items(section_dir: Path) -> list:
    """Read numbered JSON files from a directory, return as ordered list."""
    files = sorted(
        [f for f in section_dir.iterdir() if f.suffix == ".json"],
        key=lambda f: f.name,
    )
    return [read_json(f) for f in files]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def compose(dir_path: str):
    dir_path = Path(dir_path).resolve()
    if not dir_path.is_dir():
        print(f"Error: {dir_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    structure = read_json(dir_path / "_structure.json")
    fmt = structure.get("jsonFormat", {})
    entries = structure["topLevelKeys"]

    # Pre-load config.json (contains multiple top-level keys).
    config_path = dir_path / "config.json"
    config = read_json(config_path) if config_path.exists() else {}

    result = {}

    for entry in entries:
        key = entry["key"]
        source = entry["source"]

        if source == "config.json":
            result[key] = config[key]

        elif source.endswith("/"):
            # Directory-based section.
            section_dir = dir_path / source.rstrip("/")
            if key == "prompts":
                result[key] = read_prompts(section_dir)
            else:
                result[key] = read_named_items(section_dir)

        else:
            # Standalone JSON file.
            result[key] = read_json(dir_path / source)

    # Write output JSON.
    out_path = dir_path.parent / (dir_path.name + ".json")

    indent = fmt.get("indent", 2)
    ensure_ascii = fmt.get("ensureAscii", False)
    trailing_nl = fmt.get("trailingNewline", True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=indent, ensure_ascii=ensure_ascii)
        if trailing_nl:
            f.write("\n")

    print(f"Composed: {dir_path.name}/ → {out_path.name}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <directory>", file=sys.stderr)
        sys.exit(1)
    compose(sys.argv[1])
