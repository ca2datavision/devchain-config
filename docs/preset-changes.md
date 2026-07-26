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
git show --name-only --format='' <commit> | grep -v '^$' \
  | grep -v '^teams/<preset>\(/\|\.json$\)' \
  && echo "FOREIGN FILES ABOVE" || echo "isolated"
```

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
- `decompose.py` computes `out_dir = json_path.parent / json_path.stem`
  (`decompose.py:127`) and then `shutil.rmtree(out_dir)` (`decompose.py:129`).

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
grep -rn "preview-preview\|terra-terra\|sol-sol" teams/ && echo "CORRUPTION" || echo "clean"
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
