# Risks

## Known Risks and Gaps

- **No automated tests** -- round-trip correctness relies on manual verification
- **No CI/CD pipeline** -- no automated validation on push or PR
- **Destructive decompose** -- `decompose.py` calls `shutil.rmtree()` on the output directory before writing, which destroys any local-only edits not committed to Git
- **No input validation** -- scripts assume well-formed Devchain JSON input; malformed JSON will crash with a Python traceback

## Security and Secrets Handling

- No secrets are stored in this repository
- Agent profiles reference AI provider names but contain no API keys or tokens
- The `.claude.json` file at repo root contains Devchain project configuration (not secrets)

## Fragile Areas / Hard-to-Change Parts

- **`_structure.json` and `_keyOrder`** -- these metadata files drive round-trip fidelity. Manual edits to these can break compose output
- **Numbered file prefixes** (`01-`, `02-`) -- ordering is significant; renaming or reordering files changes the composed JSON array order
- **Slug generation** -- if `slugify()` behavior changes, decompose will create different directory names, breaking existing edits

## Unknowns and Open Questions

- Devchain's JSON schema is not formally documented in this repo; changes to Devchain's export format could break decompose/compose
- No versioning strategy for tracking which Devchain platform version a preset is compatible with beyond `minDevchainVersion` in manifest
