# Architecture

## System Shape

Standalone CLI tooling -- two Python scripts that perform bidirectional transformation between a monolithic Devchain JSON preset and a decomposed directory of human-readable files.

## Main Components

### `decompose.py`
- Reads a single Devchain JSON preset file
- Splits it into: `_structure.json` (key ordering/source map), `manifest.json`, `config.json`, `statuses.json`, and directories for `prompts/`, `profiles/`, `agents/`, `watchers/`, `subscribers/`
- Prompt content extracted into `.md` files; metadata into `.json` files
- Uses numbered prefixes (`01-`, `02-`) to preserve ordering

### `compose.py`
- Reads a decomposed directory using `_structure.json` as the reconstruction guide
- Merges `prompt.json` + `content.md` back into single prompt objects (respecting `_keyOrder`)
- Produces a byte-identical JSON file ready for Devchain import

### Configuration Presets
- `claude-codex-advanced` -- 6-agent Development Team, 2 providers (Claude, Codex/GPT)
- `claude-codex-gemini-advanced` -- 9-agent Development Team, 3 providers (Claude, Codex/GPT, Gemini)
- `requirements-team` -- 3-agent Requirements Team (Claude, Codex, Gemini) — produces validated VRDs consumed by the Dev Team

## Data Flow

```
Devchain JSON export
        |
  decompose.py
        |
  Directory of files (MD + JSON)
        |
  Human edits (Git-tracked)
        |
  compose.py
        |
  Devchain JSON import
```

## Cross-Cutting Concerns

- **Round-trip fidelity:** `_structure.json` stores original key ordering and source mapping so compose produces byte-identical output
- **Slug generation:** `slugify()` in `decompose.py` normalizes titles to filesystem-safe names
- **Key order preservation:** Prompt metadata stores `_keyOrder` array to reconstruct exact JSON key ordering

## Deployment Topology

Local-only. Output JSON is imported into the Devchain web platform (https://devchain.twitechlab.com/).
