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
- [13. Parallel Task Isolation](#13-parallel-task-isolation)

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

# Verify round-trip fidelity (sources -> artifact) WITHOUT mutating the repo.
# Never run decompose.py against teams/<preset>.json in-tree: it computes
# out_dir = json_path.parent / json_path.stem and shutil.rmtree()s it
# (decompose.py:127,129), which DELETES the tracked teams/<preset>/ directory.
SCRATCH=$(mktemp -d)
git archive HEAD teams/claude-codex-advanced | tar -x -C "$SCRATCH"
python3 compose.py "$SCRATCH/teams/claude-codex-advanced"
cmp "$SCRATCH/teams/claude-codex-advanced.json" teams/claude-codex-advanced.json
# cmp silent = sources and committed artifact agree
```

No linter or formatter is currently configured. If added, prefer:
- Python: `ruff check --fix .` and `ruff format .`

For any change to a preset under `teams/`, follow the checklist in [preset-changes.md](preset-changes.md) -- nine verification techniques, including the round-trip *direction* that actually catches drift and a destructive `decompose.py` hazard the commands above do not warn about.

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
│   ├── claude-codex-gemini-advanced.json  # Composed 10-agent preset
│   ├── claude-codex-gemini-advanced/      # Decomposed 10-agent preset
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

---

## 13. Parallel Task Isolation

When two or more tasks change the same repository at the same time, isolation must be a
**mechanical control**, not discipline. Phase 1 ran two agents in one checkout and produced
cleanly-scoped commits only because each independently chose to stage by pathspec. That is
a good outcome from an uncontrolled process: a single `git add -A` by either would have
cross-committed the other's in-flight work and silently failed the one-commit-per-preset
criterion.

### Two compounding hazards

Both are specific to this repo's tooling and make a shared tree worse than it first appears:

- **`decompose.py` destroys sibling work.** It calls `shutil.rmtree()` on its output
  directory before writing (`decompose.py:127,129`). Anyone re-decomposing mid-flight
  destroys another task's uncommitted work in that directory outright.
- **Even verification mutates the tree.** `compose.py` rewrites `teams/<preset>.json` **in
  place**, so a run intended as a read-only check modifies shared state.

### The rule

1. **Parallel same-repo tasks run in separate git worktrees.**
   ```bash
   git worktree add <path-outside-repo> -b <branch> <base-commit>
   git worktree remove <path>          # when the task completes
   ```
2. **Where a worktree is not possible, stage by pathspec — never `git add -A`** — and run
   the foreign-file assertion below before committing.
3. **Run the foreign-file assertion regardless of which option you used.** A worktree
   prevents collisions with *other tasks*; it does not stop you from staging a file your
   own task never declared.
4. **Remove your worktree when the task completes.** A leftover worktree becomes the stale
   checkout that misleads the next agent (see below).

### Foreign-file assertion (pre-commit)

Its input is the task's **Declared Paths** field. Without that field the control has
nothing to filter against, which is why the field is mandatory in the sub-epic template.

```bash
# exits non-zero if anything outside the task's Declared Paths is staged
DECLARED='^(docs/preset-changes\.md|docs/development-standards\.md)$'
if git diff --cached --name-only | grep -Ev "$DECLARED"; then
  echo "FOREIGN FILES STAGED — do not commit"; false
else
  echo "clean: only Declared Paths staged"
fi
```

Re-run it against the commit afterwards, because what landed is the thing that matters:

```bash
if git show --name-only --format='' HEAD | grep -v '^$' | grep -Ev "$DECLARED"; then
  echo "FOREIGN FILES IN COMMIT"; false
else
  echo "commit isolated"
fi
```

> **Use `if`/`else`, not `cmd && { …; false; } || echo …`.** That shorthand parses as
> `(A && B) || C`: the `false` in the violation branch makes `||` fire, so the failure case
> prints the warning *and then* the success message and **exits 0** — an assertion that
> cannot fail. This exact bug shipped in an earlier revision of this section and was caught
> in review, not by the three people who ran it and saw `clean`. Whenever a check is meant
> to gate something, test the violation branch: a staged foreign file must produce a
> non-zero exit with no trailing success line.

### Untracked files are a separate sub-case

A new worktree is a **clean checkout** — untracked files in the main working tree do not
appear in it. But a task can create untracked files *inside* its own worktree (scratch
scripts, `__pycache__`, generated output), and `git add -A` there will sweep them in. This
is why rule 3 requires the assertion even when worktrees are used: **worktrees solve
concurrent edits to tracked files; only the assertion catches undeclared files.**

### Declare the revision, not just the paths

Declaring *paths* does not tell you *which revision* you are reading. Phase 2 lost a review
cycle to a worktree that was correctly isolated but pinned to a superseded commit —
verification run inside it produced confident, wrong results.

**Before reporting any verification result, state the commit you read:**

```bash
echo "cwd=$(pwd) branch=$(git rev-parse --abbrev-ref HEAD) HEAD=$(git rev-parse HEAD)"
```

### Check properties, not actions

The recurring defect behind several of these rules is an acceptance criterion that names an
**action** instead of the **property** the action is meant to produce. The action can
succeed while the property fails:

| Criterion names an action | The property that actually matters |
|---|---|
| "renamed via `git mv`" | `git log --follow` reaches the pre-rename path |
| "Declared Paths were listed" | nothing outside them is in the commit |
| "one commit per preset" | the work is durably published |

Two worked examples. A rename combined with a substantial rewrite in one commit records as
add/delete once similarity falls under git's default 50% threshold — Phase 2 measured 45%,
so `git mv` was used correctly and history was lost anyway; splitting the pure rename into
its own commit is what preserves it. And a rebase can re-derive commits, so `git log
--follow` must be **re-verified after any rebase or squash** rather than assumed to survive.

**A phase is not complete until its branch is pushed to `origin`. Verify at Review
dispatch, not at merge.** Phase 1 was reviewed, approved, and closed while its commits
existed only on one local disk.
