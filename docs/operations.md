# Operations

## Common Tasks

| Task | Command |
|---|---|
| Decompose preset | `python3 decompose.py <preset>.json` |
| Compose preset | `python3 compose.py <preset-directory>` |
| Verify round-trip | Decompose then compose; diff output against original JSON |

## Typical Workflow

1. Edit SOP Markdown files, agent JSON, profile JSON, or statuses in the decomposed directory
2. Run `python3 compose.py <directory>` to rebuild the JSON
3. Import the resulting JSON into Devchain

## Maintenance Routines

- After editing a Devchain JSON export, re-run `decompose.py` to refresh the directory
- After editing decomposed files, run `compose.py` before importing

## Troubleshooting

| Issue | Fix |
|---|---|
| `Error: <path> not found` | Verify the JSON file path or directory path is correct |
| `Error: <path> is not a directory` | `compose.py` expects a directory, not a JSON file |
| Key ordering mismatch after compose | Check `_structure.json` and `_keyOrder` in prompt.json files are intact |
| New directory not appearing | `decompose.py` deletes and recreates the output directory on each run |

## Logs / Metrics

- Scripts print a single line on success: `Decomposed: X → Y/` or `Composed: X/ → Y`
- Errors go to stderr
