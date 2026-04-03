# AI Agents Guide

## Coding Conventions

- Python scripts use standard library only -- no third-party imports
- JSON files use 2-space indent, real unicode (`ensure_ascii=False`), trailing newline
- Prompt content is Markdown (`.md` files); metadata is JSON (`.json` files)
- Slugs are generated via `slugify()`: lowercase, ASCII-only, hyphens as separators, max 60 chars

## Where to Make Changes Safely

- **SOP content:** Edit `teams/*/prompts/*/content.md` freely -- these are the agent instruction Markdown files
- **Agent configuration:** Edit `teams/*/agents/*.json` to change agent names, descriptions, or profile links
- **Profiles:** Edit `teams/*/profiles/*.json` to change AI provider, model, CLI options, or temperature
- **Statuses:** Edit `teams/*/statuses.json` to modify board columns
- **Watchers/Subscribers:** Edit files in `teams/*/watchers/` and `teams/*/subscribers/` for automation config

## Do NOT Edit

- `teams/*/_structure.json` -- unless you understand the compose round-trip mechanism
- `_keyOrder` arrays in `teams/*/prompts/*/prompt.json` -- these preserve exact JSON key ordering
- Numbered prefixes on filenames -- changing these changes array ordering in composed output

## How to Run, Test, and Lint

```bash
# Decompose
python3 decompose.py teams/<preset>.json

# Compose
python3 compose.py teams/<preset-directory>

# Verify round-trip (no formal test suite)
diff original.json recomposed.json
```

No linter or formatter is configured for this repo.

## Diff/PR Guidance

- When reviewing diffs, focus on `content.md` changes (SOP text) and agent/profile JSON changes
- Large JSON preset files (`*.json` at root) are generated -- review the decomposed source files instead
- The `_structure.json` should rarely change unless new top-level keys are added to the Devchain format

## Guardrails

- No network access required -- all operations are local filesystem
- No secrets in the repo; agent profiles reference provider names, not API keys
- `decompose.py` destructively removes the output directory -- always commit before running on existing decomposed dirs
