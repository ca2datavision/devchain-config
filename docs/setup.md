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

**Optional local pre-commit hook.** A hook that runs the config invariants when you stage
anything under `teams/` or `scripts/` is available but **not installed by clone** — git
does not allow cloned content to activate itself as a hook, so it costs one command per
clone. Install, verify, uninstall, bypass, and the precise semantics (it checks the working
tree, which can diverge from what you are committing) are documented in the header of
`scripts/pre-commit.sample`, which is the canonical source for all of it.

## Environment Variables and Secrets

- None required. The scripts operate purely on local files.

## How to Run

### Decompose a Devchain JSON preset

```bash
python3 decompose.py teams/claude-codex-gemini-advanced.json
```

Creates/overwrites the `teams/claude-codex-gemini-advanced/` directory.

### Compose a directory back to JSON

```bash
python3 compose.py teams/claude-codex-gemini-advanced
```

Writes `teams/claude-codex-gemini-advanced.json` next to the directory.

## How to Verify Round-Trip

```bash
python3 decompose.py teams/claude-codex-advanced.json
python3 compose.py teams/claude-codex-advanced
# The resulting JSON should be byte-identical to the original
diff <(cat teams/claude-codex-advanced.json) <(python3 -c "")  # or use sha256sum
```
