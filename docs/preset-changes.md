# Preset-Change Verification Checklist

Techniques for verifying any change to a preset under `teams/`. Every item below was
independently rediscovered by two or more agents during the Phase 1 model refresh, and
several are actively dangerous to rediscover a third time — item 5 destructively so.

These are **review and execution techniques** applied to a change by a person or agent.
They are distinct from automated CI invariants (`scripts/`, `.github/`), which enforce a
subset of the same properties on every push.

Numbering is 1:1 with the source backlog item `071ce95e`.

**How to use:** work top to bottom before submitting a preset change for review. Each item
states the failure it catches, then the command that catches it. Commands assume the repo
root as the working directory unless stated otherwise.

Each item below deliberately checks a **property**, not that a command was run — see the
properties-not-actions table in [development-standards.md §13](development-standards.md#13-parallel-task-isolation)
for why that distinction matters and where checks written the other way have failed.

---

## 1. Substitution-only proof

**Catches:** reflow, key reordering, flag drift, and incidental edits riding along with an
intended change.

Apply the intended token rules to the **pre-change** artifact and diff against the
**post-change** artifact. Byte-identity proves the change contains the intended
substitutions *and nothing else* — by construction, rather than by reading the diff and
hoping to notice.

```bash
python3 - <<'PY'
import re, subprocess, pathlib
BOUNDARY = r"(?![A-Za-z0-9._-])"
RULES = [("gemini-3.1-pro", "gemini-3.1-pro-preview"),
         ("claude-opus-4-5", "claude-opus-5")]          # your rules here
BEFORE, PATH = "<pre-change-commit>", "teams/<preset>.json"

old = subprocess.run(["git", "show", f"{BEFORE}:{PATH}"],
                     capture_output=True, text=True, check=True).stdout
for o, n in RULES:
    old = re.sub(re.escape(o) + BOUNDARY, n, old)
print("substitution-only:", old == pathlib.Path(PATH).read_text())
PY
```

`True` means the diff is exactly the substitutions. `False` means something else changed —
find out what before proceeding.

## 2. Commit isolation assertion

**Catches:** files from another task swept into your commit — the shared-working-tree
hazard (`903ee649`), verified as an *outcome* instead of trusted to staging discipline.

```bash
# every file in the commit must be under this task's declared paths
if git show --name-only --first-parent --format='' <commit> | grep -v '^$' \
     | grep -v '^teams/<preset>\(/\|\.json$\)'; then
  echo "FOREIGN FILES ABOVE"; false
else
  echo "isolated"
fi
```

Three details, each of which has already shipped broken once:

- **Never suppress the output of a *negated* `grep` you are gating on.** In this environment
  `grep -qEv …` and `grep -Ev … > /dev/null` return `NOT(the pattern matched anywhere)`, which
  is wrong on exactly one input shape — a file list where the pattern matches *some* lines and
  not others. That is the only shape this assertion ever sees when a foreign file is staged.
  Capture to a file or variable, or count with `-c`/`-vc`. Mechanism, evidence and the four
  superseded characterisations: [development-standards.md §13 → Shell instrument
  hazards](development-standards.md#shell-instrument-hazards).
- **`if`/`else`, not `cmd && echo "BAD" || echo "ok"`.** That shorthand parses as
  `(A && B) || C` and always exits 0 — usable by a human reading output, useless to
  anything that checks a status code.
- **`--first-parent` is load-bearing.** Without it `git show --name-only` prints
  **nothing for a merge commit**, so the check reports `isolated` and exits 0 having
  examined zero files — vacuous on exactly the commits most able to sweep in foreign
  files. `--first-parent` reports what the merge brought *onto* the branch, which is what
  this check is asking. (`git diff-tree -r --name-only --no-commit-id` is blind the same
  way.)

The two are independent: the first controls how the result is *propagated*, the second what
is *measured*. Fixing one leaves the other live.

Run it against the commit you just made, not the staged index — the point is to check what
actually landed. If your task declares multiple paths, extend the filter to all of them.

## 3. Allowlist, not just denylist

**Catches:** a typo'd or unexpected model ID.

A denylist of retired IDs is *structurally incapable* of this: it can only confirm the
absence of failures you already thought of. Check every `--model` value against the
approved set instead.

```bash
python3 - <<'PY'
import re, pathlib, collections
# Prefer the tracked allowlist; fall back to an inline set if it is not present yet.
p = pathlib.Path("scripts/approved-models.txt")
APPROVED = set(p.read_text().split()) if p.exists() else {
    "claude-opus-5", "claude-fable-5", "gpt-5.6-terra",
    "gpt-5.6-sol", "gemini-3.1-pro-preview", "gemini-2.5-pro",
}
found = collections.Counter()
for jf in pathlib.Path("teams").rglob("*.json"):
    found.update(re.findall(r'--model[= ]([^\s"]+)', jf.read_text()))
stray = set(found) - APPROVED
print("values:", dict(found))
print("UNAPPROVED:", sorted(stray) or "NONE")
PY
```

If you edit the inline fallback instead of the file, you have created a second source of
truth — the exact failure this checklist exists to prevent. Update
`scripts/approved-models.txt` and delete the fallback once that file is in place.

**Allowlist-same-commit rule.** A model refresh **must** update
`scripts/approved-models.txt` in the *same commit* as the config change. Splitting them
reds CI on a legitimate refresh, which trains people to ignore the check — worse than not
having it. The allowlist is part of the change, not a follow-up to it.

## 4. State the round-trip direction explicitly

**Catches:** a composed JSON hand-edited into disagreement with its own sources.

"Round-trip" names two different guarantees, and only one catches that:

| Direction | Command | Proves |
|---|---|---|
| artifact→artifact (**weak**) | decompose the composed JSON, recompose it | the artifact is self-consistent. **Never reads `teams/<p>/`.** |
| sources→artifact (**strong**) | compose from `teams/<p>/`, compare to the committed JSON | sources and artifact agree |

Phase 1's acceptance criterion said only "round-trip"; the weak reading would have passed a
real defect. **Always say which direction you mean, and run the strong one.** Ideally run
both — they fail on different things.

```bash
# strong: sources -> artifact. Must be out-of-tree (item 5 explains why).
SCRATCH=$(mktemp -d)
git archive HEAD teams/<preset> | tar -x -C "$SCRATCH"     # lands at $SCRATCH/teams/<preset>
python3 compose.py "$SCRATCH/teams/<preset>"
cmp "$SCRATCH/teams/<preset>.json" teams/<preset>.json && echo "sources match artifact"
```

Note the `teams/` prefix is preserved by `git archive`, so the path passed to `compose.py`
is `$SCRATCH/teams/<preset>` — not `$SCRATCH/<preset>`.

## 5. Verify out-of-tree ⚠️

**Catches:** a "read-only" verification that silently mutates or destroys the repo.

Both scripts write into the tree:

- `compose.py` rewrites `teams/<preset>.json` **in place**.
- `decompose.py::decompose` `out_dir = json_path.parent / json_path.stem` computes the
  output directory, and then `decompose.py::decompose` `shutil.rmtree(out_dir)` deletes it.

> **⚠️ `python3 decompose.py teams/<preset>.json` DELETES the tracked directory
> `teams/<preset>/`.** It is not read-only. On a clean tree it is recoverable from git; with
> uncommitted work in that directory — including a *parallel agent's* uncommitted work — it
> is not.

Always copy to a scratch directory outside the repo first:

```bash
SCRATCH=$(mktemp -d)
git archive <commit> teams/<preset> teams/<preset>.json | tar -x -C "$SCRATCH"
# ...now run decompose.py / compose.py against "$SCRATCH" only
```

`git archive` also guarantees you are testing a *committed* state rather than whatever
happens to be in the working tree.

**This hazard is now mechanically guarded — but only where git can see it.**
`decompose.py::guard_rmtree`, called immediately before `decompose.py::decompose`
`shutil.rmtree(out_dir)`, refuses with a non-zero exit when the output directory is
git-tracked **and** has local
changes; untracked (`??`) and ignored (`!!`) entries count as changes, because those are
exactly what git cannot restore afterwards. `--force` overrides. Four cases, and the fourth
is the one to remember:

| Situation | Behaviour |
|---|---|
| tracked + dirty, git available | **refused** — the guard |
| tracked + clean | proceeds; git can restore it |
| untracked directory | proceeds, presumed scratch — the fully unrecoverable path, left open **deliberately** so throwaway use stays frictionless |
| **git absent, or target outside a repository** | **proceeds unguarded**, tracked-dirty content included |

The fourth case is not "behaviour is unchanged" — it is **the protection is absent**. Run
`decompose.py` where `git` is not on `PATH` and a tracked, dirty directory is deleted with no
refusal and no warning. Nothing has regressed; the guard simply never runs. A guard
implemented inside a tool feels like it travels with the tool, and this one does not.

## 6. Exact-boundary matching and single-pass substitution

**Catches:** false failures on correct output, and silent corruption.

`gemini-3.1-pro` is a strict substring of `gemini-3.1-pro-preview`. A naive grep both
false-fails against correct output and masks genuine `-preview-preview` corruption.

**Matching** — right-boundary lookahead, no left boundary (so `default-claude-opus-4-5`
still matches on the model portion):

```bash
grep -roP "\Qgemini-3.1-pro\E(?![A-Za-z0-9._-])" teams/ | wc -l
```

**Substituting** — one pass with negative lookahead, so no rule's *output* can be
re-matched by a later rule:

```python
re.sub(r"gemini-3\.1-pro(?!-preview)", "gemini-3.1-pro-preview", text)
```

A sequential `sed` chain is precisely what produces `gemini-3.1-pro-preview-preview`.
Always grep for doubled suffixes afterwards:

```bash
if grep -rn "preview-preview\|terra-terra\|sol-sol" teams/; then
  echo "CORRUPTION"; false
else
  echo "clean"
fi
```

## 7. Resolve agent pins through `profileId`

**Catches:** a false DANGLING verdict on clean work (this happened during Phase 1 review).

The resolution chain is:

```
agent.profileId  →  profile.id  →  profile.providerConfigs[].name  ⊇  agent.providerConfigName
```

**There is no `profileName` field on agents.** Agent objects carry exactly
`id`, `name`, `profileId`, `description`, and optionally `providerConfigName`. Keying on a
profile's *name* yields a dangling-reference verdict against a perfectly clean tree.

```bash
python3 - <<'PY'
import json, pathlib
for comp in sorted(pathlib.Path("teams").glob("*.json")):
    c = json.loads(comp.read_text())
    prof = {p["id"]: {x["name"] for x in p.get("providerConfigs", [])}
            for p in c.get("profiles", [])}
    for a in c.get("agents", []):
        ref = a.get("providerConfigName")
        if ref and ref not in prof.get(a["profileId"], set()):
            print(f"DANGLING {comp.name}: {a['name']} -> {ref}")
print("done")
PY
```

## 8. CLI trust guards for smoke tests

**Catches:** hours lost debugging environment errors as if they were model errors.

The obvious invocations do **not** run as written in this environment. Verified exit codes:

| CLI | Missing flag | Result |
|---|---|---|
| `codex exec` | `--skip-git-repo-check` | `Not inside a trusted directory`, **exit 1** — *but see below* |
| `codex exec` | stdin not redirected | blocks indefinitely — always add `</dev/null` |
| `gemini` | `--skip-trust` | `not running in a trusted directory`, **exit 55** |

None of these is a model error.

> **The codex row is trust-registry dependent, so do not use it as a diagnostic.** codex
> consults its own trusted-projects list. From a directory it does not recognise the call
> fails with exit 1 as above; from *any worktree of an already-trusted repo* — which is
> exactly the setup "Working in parallel" below recommends — it succeeds with exit 0 and no
> flag. Both behaviours were reproduced. Always pass `--skip-git-repo-check` so the result
> does not depend on invisible local state, and never infer anything about a model from its
> presence or absence.

Copy-pasteable block for all three providers:

```bash
claude -p "Reply with the single word: ok" --model <claude-model>

codex exec --skip-git-repo-check --model=<codex-model> \
  "Reply with the single word: ok" </dev/null

gemini --skip-trust --model <gemini-model> -p "Reply with the single word: ok" </dev/null
```

**Interpreting results.** `2xx`/a real completion = PASS. `404` / `ModelNotFoundError` /
unknown-model = FAIL. **`429` / quota-exceeded = PASS** — model resolution happens *before*
quota enforcement, so a quota error proves the ID is valid.

That last claim must be *earned*, not assumed. Run a **control probe** with a known-invalid
ID and confirm it returns a different error class:

```bash
gemini --skip-trust --model gemini-3.1-pro -p ok </dev/null   # -> ModelNotFoundError
gemini --skip-trust --model gemini-3.1-pro-preview -p ok </dev/null  # -> TerminalQuotaError
```

Different error classes prove the test discriminates. Without the control, a `429` is
merely *unfalsified* rather than positive evidence.

Finally, **extract the model strings from the committed config** rather than hardcoding
them in the test — otherwise you are re-testing your assumptions, not the artifact:

```bash
python3 -c "import re,pathlib,sys; print('\n'.join(sorted(set(
  re.findall(r'--model[= ]([^\s\"]+)', pathlib.Path(sys.argv[1]).read_text())))))" \
  teams/<preset>.json
```

**Audit freshness is judged by FILENAME, never by mtime.** `docs/audits/YYYY-MM-DD.md`
entries are dated from the filename because a git checkout does not preserve mtime — CI
clones fresh, so every file looks written seconds ago and an mtime-based check would report
a three-year-old audit as current. Enforced by `scripts/check-invariants.py --audit-staleness`.

## 9. Edit raw text, never `json.load` / `json.dump`

**Catches:** byte-identity failures from reflowed formatting.

A `json.load` → `json.dump` round-trip re-serialises the whole file to the dumper's
formatting. Where that differs from what is on disk, byte-identity breaks even though the
parsed data is unchanged.

**The rule is "preserve whatever formatting the file already uses" — not "make it
single-line".** Formatting is a per-file convention here, not a tooling invariant: neither
`decompose.py` nor `compose.py` special-cases `providerConfigs`. As of this writing:

| Preset | `providerConfigs` entries | On-disk style |
|---|---:|---|
| `claude-codex-gemini-advanced` | 77 | **single-line** (one object per line) |
| `requirements-team` | 21 | standard multi-line `indent=2` |
| `claude-codex-advanced` | 0 | no `providerConfigs` at all |

So edit the file as text — `re.sub` on the raw string, or a targeted replacement — and
confirm the style survived by comparing against the pre-change count rather than against a
fixed expectation:

```bash
# count single-line entries before and after your edit; the two numbers must match
grep -c '^    { "name"' teams/<preset>/profiles/<profile>.json
```

A result of `0` is correct for a multi-line preset and does **not** indicate a problem —
what matters is that the number is unchanged. The authoritative check is still item 4's
sources→artifact round-trip, which catches reflow regardless of which style a file uses.

The same rule applies to any editor or hook that "formats on save" — disable it for these
files.

---

## Working in parallel

When two tasks change presets at the same time, isolate them with **separate git
worktrees**, not with careful staging:

```bash
git worktree add <path-outside-repo> -b <branch> <base-commit>
git worktree remove <path>     # when the task completes
```

Two habits, both learned the hard way:

- **Declare your revision, not just your path.** A worktree can be correctly isolated and
  still stale. State `git rev-parse HEAD` before reporting any verification result — a
  stale checkout produces confident, wrong findings.
- **Remove your worktree when the task completes.** A leftover worktree is the stale
  checkout that misleads the next agent.

*Bootstrap precedent: Phases 4 and 5 ran concurrently in separate worktrees as the first
application of this isolation control, before its rule text existed — the rule below was
written from what actually worked rather than from theory.*

---

## How to cite code in docs

**Cite a symbol, never a line number.** Line numbers rot on every insertion above them,
silently and invisibly. Symbols rot only on rename, which is rarer and — because a rename
breaks the citation loudly — self-announcing.

```
decompose.py::decompose                                  symbol only
decompose.py::decompose `shutil.rmtree(out_dir)`         symbol + anchored snippet
```

- **Format:** `<file>.py::<symbol>`. The symbol must match `^\s*(def|class)\s+<symbol>\b`
  in that file. Decorated definitions match — the decorator sits on the previous line.
- **Anchored snippets:** a backtick snippet placed **on the same line, immediately after**
  the citation must appear verbatim in that file. Use one when you are pointing at a
  specific statement rather than a whole function.
- **Cite the definition alone** when the definition *is* the subject —
  `decompose.py::guard_rmtree` needs no snippet.
- **Writing about the scheme rather than using it?** Use metasyntactic placeholders, or the
  check will try to resolve your example as a real citation:
  - legacy form → `file.py:NNN` or `<file>.py:<line>` (placeholder digits never match `\d+`)
  - symbol form → `<file>.py::<symbol>` (the angle bracket breaks the `\w+` the check
    expects after `::`)

  This paragraph is the reason the convention exists. The first draft of this very note
  illustrated the format with a literal line-number example and a bare metasyntactic
  filename, and the check flagged all three occurrences — one as a legacy citation, two as
  citations naming a file that does not exist. The rewrite then tripped again, because the
  sentence *explaining* the mistake quoted the offending forms verbatim. Prefer a **real,
  resolving** example wherever you can; reach for placeholders only when the point is the
  shape rather than the target, and describe a bad form rather than reproducing it.

Enforced by `python3 scripts/check-invariants.py --doc-citations`, as its own CI step. A
legacy line-number citation anywhere in scope is RED; so is an unresolvable file or an
unknown symbol, each with its own message naming the expected format.

**Scope: `docs/` recursively, excluding `docs/audits/`.** Audit files are append-forever
records that legitimately quote tool output containing `file:line` text, and are never
retro-edited to satisfy a linter. The exemption is bounded rather than open-ended: parking
living guidance under `audits/` to dodge the check would be plainly visible in review.

### Two stated residuals — green does not mean these were checked

1. **Multi-line snippets are not validated.** Only a snippet on the *same line* as its
   citation is anchored and verified. A snippet in a following fenced block or on the next
   line is not associated with the citation and is not checked at all. If you anchor that
   way, a green run tells you nothing about it.
2. **Snippet-anywhere.** The snippet is matched against the whole file, not against the
   cited symbol's body. A citation whose snippet has since moved into a *different*
   function still passes.

As of this writing **no citation in this repository relies on either residual** — every
anchored snippet here sits inside the function it cites, verified when they were migrated.
That is worth preserving: if this sentence ever stops being true, someone will have had to
make it false deliberately, and the check will not tell them.
