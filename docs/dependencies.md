# Dependencies

## First-Party Packages / Services

| Component | Path | Role |
|---|---|---|
| `decompose.py` | `decompose.py` | Splits Devchain JSON into editable directory structure |
| `compose.py` | `compose.py` | Reassembles directory back into Devchain-importable JSON |

## Third-Party Dependencies

- **None.** Both scripts use only Python 3 standard library modules:
  - `json` -- JSON parsing/serialization
  - `re` -- regex for slug generation
  - `shutil` -- directory removal (`rmtree`)
  - `sys` -- CLI argument handling, exit codes
  - `unicodedata` -- Unicode normalization for slugs
  - `pathlib` -- filesystem path operations

## Critical Runtime Dependencies

| Dependency | Purpose |
|---|---|
| Python 3.6+ | Script runtime |
| Devchain platform | Target system for importing composed JSON presets |

## External Services

- **Devchain** (https://devchain.twitechlab.com/) -- the platform these configurations are designed for
- **Claude** (Anthropic), **Codex/ChatGPT** (OpenAI), **Gemini** (Google) -- AI providers referenced in agent profiles (not direct dependencies of this repo)
