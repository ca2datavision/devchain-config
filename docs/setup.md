# Setup

## Prerequisites

- **Python 3.6+** (uses f-strings, `pathlib`, `typing` hints)
- No additional packages or virtual environment needed

## Install Steps

```bash
git clone <repo-url>
cd devchain-config
```

No `pip install` required -- scripts use only the Python standard library.

## Environment Variables and Secrets

- None required. The scripts operate purely on local files.

## How to Run

### Decompose a Devchain JSON preset

```bash
python3 decompose.py claude-codex-gemini-advanced.json
```

Creates/overwrites the `claude-codex-gemini-advanced/` directory.

### Compose a directory back to JSON

```bash
python3 compose.py claude-codex-gemini-advanced
```

Writes `claude-codex-gemini-advanced.json` next to the directory.

## How to Verify Round-Trip

```bash
python3 decompose.py claude-codex-advanced.json
python3 compose.py claude-codex-advanced
# The resulting JSON should be byte-identical to the original
diff <(cat claude-codex-advanced.json) <(python3 -c "")  # or use sha256sum
```
