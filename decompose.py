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
import subprocess
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

def _git(args, cwd):
    """Run a git command. Returns CompletedProcess, or None if git is absent."""
    try:
        return subprocess.run(["git", *args], cwd=str(cwd),
                              capture_output=True, text=True)
    except OSError:
        return None


def guard_rmtree(out_dir: Path, force: bool) -> None:
    """Refuse to delete a git-TRACKED output directory that has local changes.

    `decompose()` deletes `out_dir` outright before rewriting it. When that
    directory is a tracked source tree, the delete is unrecoverable for
    anything git is not already holding.

    The protection is deliberately ASYMMETRIC — do not "fix" the third case:

      tracked + dirty  -> REFUSE. Untracked (??) and ignored (!!) entries
                          count as dirty precisely because they are the
                          classes git cannot restore afterwards.
      tracked + clean  -> proceed. Everything is recoverable from git.
      untracked dir    -> proceed. Presumed scratch; this is the one fully
                          unrecoverable path, left open on purpose so
                          throwaway use stays frictionless.

    Degrades gracefully: if git is unavailable, or `out_dir` is not inside a
    repository, behaviour is identical to before this guard existed.
    Never prompts — refusal is non-interactive so headless runs cannot hang.
    """
    if force:
        return

    cwd = out_dir.parent

    tracked = _git(["ls-files", "--", str(out_dir)], cwd)
    if tracked is None or tracked.returncode != 0:
        return                        # git absent / not a repo -> pre-guard behaviour
    if not tracked.stdout.strip():
        return                        # untracked -> presumed scratch

    status = _git(["status", "--porcelain", "--ignored", "--", str(out_dir)], cwd)
    if status is None or status.returncode != 0:
        return
    dirty = [ln for ln in status.stdout.splitlines() if ln.strip()]
    if not dirty:
        return                        # tracked + clean -> git-recoverable

    shown = dirty[:10]
    more = len(dirty) - len(shown)
    print(
        f"Refusing to decompose: {out_dir} is tracked by git and has local changes.\n"
        f"\n"
        f"  RISK: decompose.py deletes this directory (shutil.rmtree) before\n"
        f"  rewriting it. Uncommitted edits, untracked (??) and ignored (!!)\n"
        f"  files inside it would be destroyed with NO recovery path — git\n"
        f"  cannot restore untracked or ignored content.\n"
        f"\n"
        f"  Local changes ({len(dirty)}):\n"
        + "".join(f"    {ln}\n" for ln in shown)
        + (f"    … and {more} more\n" if more else "")
        + f"\n"
        f"  Commit or stash them first, or re-run with --force to delete anyway:\n"
        f"    python3 {Path(sys.argv[0]).name} {json_path_display(out_dir)} --force",
        file=sys.stderr,
    )
    sys.exit(2)


def json_path_display(out_dir: Path) -> str:
    """The <config.json> argument that produced this out_dir, for the hint."""
    return f"{out_dir.name}.json"


def decompose(json_path: str, force: bool = False):
    json_path = Path(json_path).resolve()
    if not json_path.exists():
        print(f"Error: {json_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    out_dir = json_path.parent / json_path.stem
    if out_dir.exists():
        guard_rmtree(out_dir, force)
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
    argv = sys.argv[1:]
    force = "--force" in argv
    positional = [a for a in argv if a != "--force"]
    if len(positional) != 1:
        print(f"Usage: {sys.argv[0]} <config.json> [--force]", file=sys.stderr)
        sys.exit(1)
    decompose(positional[0], force=force)
