# Development Standards

## Table of Contents

- [1. Architecture Overview](#1-architecture-overview)
- [2. Project Principles](#2-project-principles)
- [3. Layer Responsibilities](#3-layer-responsibilities)
- [4. Data Contracts](#4-data-contracts)
- [5. Error Handling](#5-error-handling)
- [6. Logging Standards](#6-logging-standards)
- [7. Configuration Management](#7-configuration-management)
- [8. Testing Standards](#8-testing-standards)
- [9. Security and Compliance](#9-security-and-compliance)
- [10. Directory Layout](#10-directory-layout)
- [11. Design Principles](#11-design-principles)
- [12. Failure Handling and Resilience](#12-failure-handling-and-resilience)

---

## 1. Architecture Overview

- **Pattern:** Flat utility scripts -- no layered architecture
- **Components:** Two Python CLI scripts (`decompose.py`, `compose.py`) that transform between monolithic JSON and decomposed directory structures
- **Stack:** Python 3.6+ (standard library only)
- **Interaction:** Scripts read/write local files; output JSON is imported into the Devchain web platform

```
  Devchain JSON <--decompose.py--> Decomposed Directory (MD + JSON)
                <---compose.py---
```

## 2. Project Principles

- **Round-trip fidelity:** Decompose then compose must produce byte-identical JSON
- **Standard library only:** No third-party Python packages; zero install friction
- **Human readability:** SOP content as Markdown, config as small focused JSON files
- **Deterministic output:** Same input always produces same output; no randomness or timestamps injected
- **Minimal tooling:** Two scripts, no build system, no framework

## 3. Layer Responsibilities

This project has no traditional layers. Responsibilities are split by script:

| Script | Responsibility | Prohibited |
|---|---|---|
| `decompose.py` | Read JSON, write directory of files | Must not modify content; must preserve all data |
| `compose.py` | Read directory, write single JSON | Must not add/remove data; must honor `_structure.json` ordering |

- `_structure.json` is the contract between decompose and compose -- it defines key ordering and source mapping
- `_keyOrder` in prompt metadata preserves JSON key ordering within prompt objects

## 4. Data Contracts

### Devchain JSON Preset Format

- Top-level keys: `_manifest`, `version`, `exportedAt`, `prompts`, `profiles`, `agents`, `statuses`, `initialPrompt`, `projectSettings`, `watchers`, `subscribers`
- `prompts` array: objects with `content` (Markdown string) plus metadata fields
- `profiles` array: objects with `id`, `name`, `provider`, `options`, `instructions`, `temperature`, `maxTokens`
- `agents` array: objects with `id`, `name`, `profileId`, `description`
- `statuses` array: objects with `id`, `label`, `color`, `position`, `mcpHidden`

### Decomposed File Format

- JSON files: 2-space indent, `ensure_ascii=False`, trailing newline
- Markdown files: raw content from `prompts[].content`, no frontmatter added
- File naming: `{NN}-{slug}.json` or `{NN}-{slug}/` where NN is 1-indexed zero-padded

### Serialization

- All JSON serialization uses `json.dump(data, f, indent=2, ensure_ascii=False)` followed by `f.write("\n")`

## 5. Error Handling

- Scripts exit with code 1 and print to stderr on input errors (file not found, not a directory)
- No custom exception classes -- scripts are simple enough to use basic `sys.exit(1)`
- No error recovery -- scripts either succeed fully or fail fast

## 6. Logging Standards

- No logging framework
- Success: single line to stdout (`Decomposed: X -> Y/` or `Composed: X/ -> Y`)
- Errors: printed to stderr via `print(..., file=sys.stderr)`
- No debug/verbose mode

## 7. Configuration Management

- No configuration files for the scripts themselves
- All behavior is determined by the input file/directory structure
- `_structure.json` within each preset directory controls compose behavior
- `jsonFormat` block in `_structure.json` controls output formatting (indent, ASCII handling, trailing newline)

## 8. Testing Standards

### Current State

- No automated test suite exists

### Expected Testing Approach

- **Round-trip verification:** Decompose a known JSON, compose it back, diff against original
- **Test command:** `diff <(python3 compose.py <dir>) <original>.json`

### Coding Standards -- Validation Before Review

Before submitting changes for review, run:

```bash
# Verify Python syntax
python3 -m py_compile decompose.py
python3 -m py_compile compose.py

# Verify round-trip fidelity
python3 decompose.py teams/claude-codex-advanced.json
python3 compose.py teams/claude-codex-advanced
# Diff should show no changes from the original JSON
```

No linter or formatter is currently configured. If added, prefer:
- Python: `ruff check --fix .` and `ruff format .`

## 9. Security and Compliance

- **No secrets** stored in the repository
- Agent profiles reference provider names (`claude`, `openai`, `gemini`) but contain no API keys
- `.env` files: none exist; no environment variables needed
- SOP content may reference external platform URLs -- these are documentation, not credentials
- `.gitignore` excludes `drafts/` directory

## 10. Directory Layout

```
devchain-config/
├── decompose.py                        # JSON -> directory
├── compose.py                          # Directory -> JSON
├── teams/                              # All team presets
│   ├── claude-codex-advanced.json      # Composed 6-agent preset
│   ├── claude-codex-advanced/          # Decomposed 6-agent preset
│   │   ├── _structure.json
│   │   ├── manifest.json
│   │   ├── config.json
│   │   ├── statuses.json
│   │   ├── prompts/
│   │   ├── profiles/
│   │   ├── agents/
│   │   ├── watchers/
│   │   └── subscribers/
│   ├── claude-codex-gemini-advanced.json  # Composed 9-agent preset
│   ├── claude-codex-gemini-advanced/      # Decomposed 9-agent preset
│   │   └── (same structure)
│   ├── requirements-team.json          # Composed 3-agent Requirements Team preset
│   └── requirements-team/             # Decomposed Requirements Team preset
│       └── (same structure)
├── specs-flow-template/               # Specs pipeline template (VRD template, directory structure)
├── docs/                               # Project documentation
├── drafts/                             # Draft content (gitignored)
├── sop-*.md                            # SOP audit/validation docs
└── README.md                           # Project README
```

### File Naming Conventions

- Decomposed items: `{NN}-{slug}.json` (e.g., `01-brainstormer.json`)
- Prompt directories: `{NN}-{slug}/` containing `prompt.json` + `content.md`
- Slugs: lowercase, ASCII-only, hyphen-separated, max 60 chars

### Where to Place New Features

- New presets: create a new JSON under `teams/`, run `decompose.py` to generate the directory
- New agents/profiles/prompts: add numbered JSON/directory entries in the appropriate subdirectory under `teams/`
- Documentation: under `docs/`

## 11. Design Principles

- **One script, one job:** `decompose.py` only decomposes; `compose.py` only composes
- **No side effects:** Scripts don't modify inputs; they only create outputs
- **Explicit ordering:** Numbered prefixes and `_structure.json` make ordering deterministic and visible
- **Filesystem as interface:** All state is in files; no database, no API calls, no network
- **Convention over configuration:** Fixed directory structure, fixed file naming, fixed JSON format

### Naming Conventions

- Functions: `snake_case` (Python standard)
- Constants: `UPPER_SNAKE_CASE`
- Variables: `snake_case`
- Files: `kebab-case` for decomposed outputs, `snake_case.py` for scripts

### Code Review Checklist

- Round-trip fidelity preserved (decompose + compose = identical JSON)
- No third-party imports introduced
- `_structure.json` format maintained
- Numbered file prefixes are sequential and correct
- Slug generation is deterministic and filesystem-safe

## 12. Failure Handling and Resilience

- **No retry logic needed** -- scripts are single-shot local file operations
- **No circuit breakers** -- no external service calls
- **Failure mode:** Exit code 1 with stderr message on bad input; Python traceback on unexpected errors
- **Data safety:** `decompose.py` calls `shutil.rmtree()` on output dir before writing -- always commit work before re-decomposing
- **Idempotency:** Running decompose or compose multiple times on the same input produces identical results
