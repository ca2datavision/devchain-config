#!/usr/bin/env python3
"""
decompose.py — Decompose a Devchain JSON config into human-readable files.

Usage: python3 decompose.py <config.json>

Creates a directory alongside the JSON (same name minus .json extension)
with prompts as editable Markdown, and everything else as small JSON files.

Directory layout produced:

    <name>/
    ├── _structure.json          # key order + source map (used by compose.py)
    ├── manifest.json            # _manifest block
    ├── config.json              # scalar / small top-level fields
    ├── statuses.json            # workflow statuses array
    ├── prompts/
    │   ├── 01-<slug>/
    │   │   ├── prompt.json      # metadata (id, title, version, tags …)
    │   │   └── content.md       # SOP / instruction body
    │   └── …
    ├── profiles/
    │   ├── 01-<slug>.json
    │   └── …
    ├── agents/
    │   ├── 01-<slug>.json
    │   └── …
    ├── watchers/
    │   ├── 01-<slug>.json
    │   └── …
    └── subscribers/
        ├── 01-<slug>.json
        └── …
"""

import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

# Sections that get their own directories (each item → separate file).
DIRECTORY_SECTIONS = {"prompts", "profiles", "agents", "watchers", "subscribers"}

# Sections that become a standalone JSON array file.
ARRAY_FILE_SECTIONS = {"statuses"}

# Keys that become their own top-level file.
STANDALONE_FILE_KEYS = {"_manifest"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str, max_len: int = 60) -> str:
    """Convert a human title into a filesystem-safe slug."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_len].rstrip("-")


def write_json(path: Path, data):
    """Write JSON with indent=2, real unicode, trailing newline."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def name_field(item: dict) -> str:
    """Return the best human-readable name for an item."""
    return item.get("title") or item.get("name") or item.get("label") or "unnamed"


# ---------------------------------------------------------------------------
# Section writers
# ---------------------------------------------------------------------------

def write_prompts(out_dir: Path, prompts: list):
    """Each prompt → its own subdirectory with prompt.json + content.md."""
    prompts_dir = out_dir / "prompts"
    prompts_dir.mkdir()
    for i, prompt in enumerate(prompts, 1):
        slug = slugify(name_field(prompt))
        prompt_dir = prompts_dir / f"{i:02d}-{slug}"
        prompt_dir.mkdir()

        # Separate content from metadata; record original key order.
        key_order = list(prompt.keys())
        meta = {"_keyOrder": key_order}
        for k, v in prompt.items():
            if k != "content":
                meta[k] = v
        write_json(prompt_dir / "prompt.json", meta)

        content = prompt.get("content", "")
        with open(prompt_dir / "content.md", "w", encoding="utf-8") as f:
            f.write(content)


def write_named_items(out_dir: Path, section: str, items: list):
    """Each item → a numbered JSON file inside <section>/."""
    section_dir = out_dir / section
    section_dir.mkdir()
    for i, item in enumerate(items, 1):
        slug = slugify(name_field(item))
        write_json(section_dir / f"{i:02d}-{slug}.json", item)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def decompose(json_path: str):
    json_path = Path(json_path).resolve()
    if not json_path.exists():
        print(f"Error: {json_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    out_dir = json_path.parent / json_path.stem
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir()

    # Build the structure map (tells compose.py where each key lives).
    top_keys = list(data.keys())
    structure_entries = []
    config_bucket = {}  # collects everything not handled specially

    for key in top_keys:
        if key in STANDALONE_FILE_KEYS:
            fname = key.lstrip("_") + ".json"  # _manifest → manifest.json
            structure_entries.append({"key": key, "source": fname})
        elif key in DIRECTORY_SECTIONS:
            structure_entries.append({"key": key, "source": f"{key}/"})
        elif key in ARRAY_FILE_SECTIONS:
            structure_entries.append({"key": key, "source": f"{key}.json"})
        else:
            structure_entries.append({"key": key, "source": "config.json"})
            config_bucket[key] = data[key]

    write_json(out_dir / "_structure.json", {
        "topLevelKeys": structure_entries,
        "jsonFormat": {"indent": 2, "ensureAscii": False, "trailingNewline": True},
    })

    # manifest.json
    if "_manifest" in data:
        write_json(out_dir / "manifest.json", data["_manifest"])

    # config.json  (version, exportedAt, initialPrompt, projectSettings, …)
    if config_bucket:
        write_json(out_dir / "config.json", config_bucket)

    # statuses.json
    if "statuses" in data:
        write_json(out_dir / "statuses.json", data["statuses"])

    # prompts/
    if "prompts" in data:
        write_prompts(out_dir, data["prompts"])

    # profiles/, agents/, watchers/, subscribers/
    for section in ("profiles", "agents", "watchers", "subscribers"):
        if section in data:
            write_named_items(out_dir, section, data[section])

    print(f"Decomposed: {json_path.name} → {out_dir.name}/")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <config.json>", file=sys.stderr)
        sys.exit(1)
    decompose(sys.argv[1])
