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
# in decompose.py::decompose `shutil.rmtree(out_dir)`, which DELETES the
# tracked teams/<preset>/ directory.
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
  directory before writing — `decompose.py::decompose` `shutil.rmtree(out_dir)`. Anyone
  re-decomposing mid-flight destroys another task's uncommitted work in that directory
  outright. **This is now REFUSED by a guard** when the target is git-tracked and dirty
  (`--force` overrides); see the four-case table in
  [preset-changes.md item 5](preset-changes.md#5-verify-out-of-tree-️) for which cases are
  protected and which deliberately are not.
- **`compose.py` has no equivalent guard, deliberately — decision closed, do not re-open.**
  The two hazards differ in *kind*: `compose.py` overwrites a single generated file that git
  can restore, whereas `decompose.py` deletes an entire directory including untracked and
  ignored content git has never seen. A guard on a tool that runs constantly gets routed
  around within a week, and a guard people bypass is worse than none because it trains
  bypassing generally.
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

**This assertion is agent-run, and cannot be automated as a repo hook.** Its input is the
current task's Declared Paths — context that lives in the task, not in the repository — so a
repo-global hook has nothing to filter against and would have to guess. Running it is a
Worker SOP obligation, not something the tooling does for you. The pre-commit hook described
below is a *different* control and does **not** perform this check.

Run it unquieted, in an `if`/`else`, exactly as written below.

> **Never gate on a silenced *negated* `grep`.** In this environment `grep` is a shell
> function, and a negated match with stdout discarded — `grep -qEv …` or
> `grep -Ev … > /dev/null` — **returns `NOT(the pattern matched anywhere)` instead of the
> correct `-v` answer.** It is wrong on exactly one input shape: a list where the pattern
> matches *some* lines but not others. That is the only shape a Declared-Paths gate ever sees
> in anger, and it is the shape that makes the assertion print `clean` while a foreign file is
> staged.
>
> Earlier revisions of this note said "inverts", then "returns non-zero regardless of input".
> Both were generalised from inputs where the pattern always matched. See
> [Shell instrument hazards](#shell-instrument-hazards) for the measured mechanism, the full
> table, and why four characterisations of this program were each true of something.
>
> The unquieted form below is correct; so is capturing to a variable or a file, counting with
> `-c`/`-vc`, and any *positive* quieted match (`grep -qE …`). It is `-v` **combined with
> discarded output** that fails.
>
> **The hazard is scoped to the interactive shell, not to hook execution.** The pre-commit
> hook's own trigger uses `grep -qE` and is nonetheless sound: git runs hooks via `/bin/sh`,
> where the shim is not defined and the real GNU grep resolves — verified in both directions
> (`teams/` staged → fires; docs-only → does not). Same construct, different environment,
> opposite verdict. So do not "fix" the hook's `-qE`, and do not conclude from it that this
> warning is overcautious: it applies to the commands *you* type, not to what git executes.

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
if git show --name-only --first-parent --format='' HEAD | grep -v '^$' \
     | grep -Ev "$DECLARED"; then
  echo "FOREIGN FILES IN COMMIT"; false
else
  echo "commit isolated"
fi
```

> **`--first-parent` is load-bearing — do not drop it.** Without it, `git show
> --name-only` prints **nothing for a merge commit**, so the assertion reports
> `commit isolated` and exits 0 having examined zero files. It is correct on ordinary
> commits and silently vacuous on merges — which are precisely the commits most able to
> sweep in foreign files. `--first-parent` reports what the merge brought *onto* this
> branch, which is the question this assertion asks. (`-m` also produces output, but it
> lists contents relative to each parent separately — a different measurement, not a
> stricter one.)

### The pre-commit hook (`scripts/pre-commit.sample`)

**What it enforces:** the **config-invariants suite** — `scripts/check-invariants.py` — and
nothing else. It fires **only when a file under `teams/` or `scripts/` is staged**. A
docs-only commit does not trigger it at all, including one that breaks a doc citation; those
are caught by CI on push. Do not read a green commit as "the invariants were checked" unless
your commit actually staged something in scope.

**What it does not enforce:** the **foreign-file / Declared Paths assertion above.** That
check needs the current task's Declared Paths, which a repo-global hook cannot know, so it
cannot be automated this way and remains an agent obligation. An earlier revision of this
section described the hook as the preferred implementation of that assertion; that was wrong
in substance, not merely imprecise.

**Enforcement status, honestly:** the hook is **opt-in until someone installs it**, and an
uninstalled hook enforces nothing while looking like a control. The canonical install,
verify, uninstall and bypass commands live in the header of `scripts/pre-commit.sample` —
read them there rather than from a copy, so there is one source of truth. Installing once
into the **common gitdir** covers every worktree. **CI on push is the enforced authority**;
the hook is a faster local signal, not a replacement for it.

**It checks the working tree, not the staged index — and those differ in both directions.**
Git commits the *index*; the hook inspects the *working tree*. Because rule 2 above mandates
staging by pathspec, partial staging is the norm here, not an edge case:

| Situation | Result |
|---|---|
| Staged change is clean, unstaged WIP violates | **FALSE BLOCK** — refused for something you are not committing |
| Staged change violates, working tree already fixed | **FALSE PASS** — committed; CI catches it on push |

Remedies, in order of preference: commit everything when that is practical; expect the block
and clear the WIP otherwise; or `git commit --no-verify` and let CI arbitrate. The last is
legitimate here precisely because CI is the authority — but say so in the commit message.

**A block may have nothing to do with your change.** The hook runs the *whole* suite, so a
pre-existing failure — a day-45 stale model-pin audit, someone else's broken citation —
blocks your unrelated commit. Three things make that diagnosable rather than baffling: the
staleness message opens by saying it is **not caused by your change**; citation failures
**name the offending file and line**; and the remedy commit for a stale audit adds a file
under `docs/audits/`, which is **not** in the hook's trigger scope, so fixing it is never
blocked by the thing you are fixing.

**Worktrees help with one half of this only.** Isolation removes *tree-state* false blocks —
another task's WIP is not in your working tree. It does **not** remove whole-suite blocks: a
pristine worktree still runs the same suite against shared repository content, so a stale
audit or a broken citation elsewhere blocks you there too. Those are answered by the
self-identifying messages above, not by isolation.

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

### Shell instrument hazards

This section exists because one shell builtin was characterised **four different ways in one
day**, each characterisation true of something and none true of the program. It is written to
be re-derived, not believed: every number below is reproducible with the commands shown.

#### The rule

**Suppressed output is safe. Suppressed output *plus* `-v` is not.** Capture to a file or a
variable, or count with `-c` / `-vc`, and compare the value.

The reason, now known: the divergence lands on **mixed input** — a list where the pattern
matches some lines and not others. That is precisely what a Declared-Paths gate sees when a
foreign file is staged, and nothing else. Toy probes over one-line inputs miss it every time.

#### The mechanism

`grep` here is a shell function that execs the Claude binary as `ugrep` with `-G`:

```
grep () {
    ...
    ( exec -a ugrep "$_cc_bin" -G --ignore-files --hidden -I --exclude-dir=.git ... "$@" )
}
```

With `-v` **and** suppressed output, the exit status becomes `NOT(pattern matched anywhere)` —
the inversion is applied to the *status* rather than to the *selection*. Correct `-v`
semantics are "did any line fail to match"; this answers "did any line match", negated.

That explains why it agrees on the easy inputs: when the pattern matches nothing, both answers
are 0; when it matches everything, both are 1. Only mixed input separates them.

#### The evidence

Pattern `^docs/`. Correct `-v` exit is 0 when at least one line is *not* matched.

| form | none | all | some | expected | verdict |
|---|---|---|---|---|---|
| `grep -qEv` | 0 | 1 | **1** | 0/1/0 | **diverges on `some`** |
| `grep -Ev … > /dev/null` | 0 | 1 | **1** | 0/1/0 | **diverges on `some`** |
| `grep -Ev … > file` | 0 | 1 | 0 | 0/1/0 | agrees |
| `out=$(grep -Ev …)` | 0 | 1 | 0 | 0/1/0 | agrees |
| `n=$(grep -cEv …)` | 0 | 1 | 0 | 0/1/0 | agrees |
| `grep -qE` (positive) | 1 | 0 | 0 | 1/0/0 | agrees |

Count *values* agree too: `none` 2/2, `all` 0/0, `some` 1/1 (shim vs `/usr/bin/grep`).

**The three input shapes are applied to the recommended forms as well, not only the broken
one.** Validating a safe form only on inputs where the bug cannot appear is the exact sampling
error that produced two of the wrong characterisations below.

**`/bin/sh` control** — every form above agrees with `/usr/bin/grep` on all three inputs.
`/bin/sh -c 'type grep'` reports `/usr/bin/grep`: the function is a bash-interactive
construct and does not exist there. This upgrades "hooks are immune" from asserted to
measured — git runs hooks via `/bin/sh`.

**Environment fingerprint** (re-capture before trusting the table on a different machine):

```
command grep --version   -> grep (GNU grep) 3.8
/usr/bin/grep --version  -> grep (GNU grep) 3.8
grep --version           -> ugrep 7.5.0        <- the SHIM reporting on itself
ugrep on PATH            -> NOT FOUND
shell                    -> bash 5.2.15
```

**`grep --version` answers for the shim, not for the binary it dispatches to.** When naming a
tool, run `command grep --version`.

#### CI is unaffected — which is the trap

There is no shim in CI. Anyone who reproduces the hazard there concludes it does not exist.
It is present exactly where controls get authored and absent exactly where they get tested.

#### The hook's `-qE` is sound — do not "fix" it

`scripts/pre-commit.sample` gates on `grep -qE`, which looks like the forbidden form and is
not. Two independent reasons: it is a **positive** match, so it never enters the divergent
path; and hooks run under `/bin/sh`, where the shim is undefined. Both measured above.

#### History — four characterisations, each true of something

| claim | true of | wrong because |
|---|---|---|
| "ugrep quiet mode" | the shim's self-reported version | no `ugrep` binary is installed |
| "`/usr/bin/grep` is ugrep" | the shim | that path is GNU grep 3.8 |
| "any quieted grep inverts" | negated forms | positive quieted matches are correct |
| "stuck at 1 regardless of input" | inputs where the pattern matched | returns 0 when it matches nothing |

A fifth in the same family, on a different subject: "the version line silently reports
current" — actually loud, and only for ordered comparison.

**Three agent-shell non-reproductions were recorded before the mechanism was known** (two
during the original investigation, one appended by the Business Analyst). All three used
single-line inputs where the pattern matched nothing, so all three returned the correct answer
**by coincidence**. Arithmetic: 3 non-reproductions, 3 explained, 0 outstanding.

It resolved when someone **read the source** rather than probing behaviour, and the confirming
probe was the first one built to *discriminate between hypotheses* rather than confirm one.
Probing tells you what happened; only the source tells you why — and without the why you
cannot tell which observations generalise.

One further caution from the same investigation: a transcript that displays output from one
run and an exit status from another proves nothing about either. Capture both from the same
invocation, into named variables.

#### Repo sweep

Run verbatim; the trailing filter excludes the two documents that teach the rule by quoting it:

```bash
grep -rnE 'grep +-[a-zA-Z]*q[a-zA-Z]*v|grep +-[a-zA-Z]*v[a-zA-Z]* [^|]*> */dev/null' \
  --include='*.sh' --include='*.sample' --include='*.py' --include='*.md' . \
  | grep -v 'development-standards.md\|preset-changes.md'
```

Result at the commit that introduced this section: **0 occurrences.**

#### Appendable measurements

Add an entry when you measure this on a new machine, shell, or binary version. Include the
fingerprint block — a result without one cannot be compared against another.

1. **Business Analyst**, agent shell — non-reproduction on single-line input; explained above
   as a `none`-shape coincidence.
2. **Coder 1**, agent shell + `/bin/sh`, bash 5.2.15 / GNU grep 3.8 / shim ugrep 7.5.0 — the
   six-form × three-input table above, including the safe forms on all three shapes.

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
