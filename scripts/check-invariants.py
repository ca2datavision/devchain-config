#!/usr/bin/env python3
"""CI entrypoint: enforce the four DevChain config invariants on the final tree.

Usage
-----
  scripts/check-invariants.py              # check the working tree (CI default)
  scripts/check-invariants.py --ref <sha>  # check a specific commit's tree
  scripts/check-invariants.py --no-self-test

Exit codes: 0 = all invariants hold · 1 = violation(s) · 2 = usage/environment.

The four invariants
-------------------
  1. ROUND-TRIP, sources -> artifact (out-of-tree)
  2. NO DANGLING providerConfigName  (profileId -> profile.id -> configs[].name)
  3. ZERO RETIRED model IDs          (exact-boundary, incl. composed artifacts)
  4. MODEL ALLOWLIST                 (read from scripts/approved-models.txt)

1, 2 and 4 are delegated to verify-presets.py, which owns their implementation.
3 is implemented here because it is a distinct guarantee -- see below.

Then the verifier's own SELF-TEST runs. That is not optional: without it the
invariant checks can degrade into no-ops while CI stays green, which is
indistinguishable from having no CI at all.

Why invariant 3 exists separately from invariant 4
--------------------------------------------------
The allowlist (4) fails anything not approved, so it already rejects retired
IDs -- as long as the allowlist itself is correct. Invariant 3 is defence in
depth against the allowlist being wrong: if someone re-adds `gemini-3.1-pro`
to approved-models.txt, invariant 4 passes and only invariant 3 objects.
They fail independently, which is the point.

Invariant 3 also scans WIDER than 4. The allowlist check reads profile
sources; invariant 3 scans everything under `teams/`, INCLUDING the composed
`<preset>.json` artifacts. That is deliberate and load-bearing:

    During the Phase 2 rebase, git auto-merged the composed artifact. The
    decomposed sources were entirely correct; only the composed file was
    stale, carrying 94 retired IDs including `gemini-3.1-pro` -- the HTTP-404
    pin that motivated the whole effort. Every per-file review and source-tree
    diff passed. Committing it would have silently undone Phase 1.

Final-tree semantics (not per-commit)
-------------------------------------
This asserts on the RESULTING tree, never on each commit in a range. A rebase
legitimately replays commits that were correct when written but carry stale
values relative to newer history -- checking those individually produces false
positives. Only the final state gives the right answer.

Python 3 standard library only. Runs no network calls and needs no credentials;
external staleness (an ID that was valid but has since been withdrawn) is the
audit runbook's job, not CI's.
"""

import argparse
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
VERIFY = HERE / "verify-presets.py"

# Historical ledger of withdrawn / superseded model IDs. Append when a model is
# retired; never remove an entry -- the whole point is that a retired ID stays
# rejected even if it is mistakenly re-added to the allowlist.
RETIRED_MODEL_IDS = [
    "claude-opus-4-5",    # retired 2026-07-26, epic 055b0226 -> claude-opus-5
    "claude-opus-4-7",    # retired 2026-07-26, epic 055b0226 -> claude-fable-5
    "gpt-5.2",            # retired 2026-07-26, epic 055b0226 -> gpt-5.6-terra
    "gpt-5.5",            # retired 2026-07-26, epic 055b0226 -> gpt-5.6-sol
    "gemini-3.1-pro",     # retired 2026-07-26, epic 055b0226 -> gemini-3.1-pro-preview
                          #   INVALID: returned HTTP 404 while pinned in production
]

# Exact-boundary matching. `gemini-3.1-pro` is a strict substring of
# `gemini-3.1-pro-preview`; a naive search both false-fails on correct output
# and masks genuine `-preview-preview` corruption. The trailing boundary is the
# same rule refresh-models.py uses, for the same reason.
IDENT_TAIL = r"[A-Za-z0-9._\-]"


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def repo_root():
    """Resolve the checkout root. Scripts must run from INSIDE a checkout."""
    proc = run(["git", "rev-parse", "--show-toplevel"], cwd=str(HERE))
    if proc.returncode != 0:
        return None
    return pathlib.Path(proc.stdout.strip())


def check_retired(root, ref):
    """Invariant 3. Scans ALL of teams/, composed artifacts included."""
    violations = []
    patterns = [(mid, re.compile(re.escape(mid) + "(?!" + IDENT_TAIL + ")"))
                for mid in RETIRED_MODEL_IDS]

    if ref:
        proc = run(["git", "ls-tree", "-r", "--name-only", ref, "teams/"],
                   cwd=str(root))
        if proc.returncode != 0:
            return [("<git>", "ls-tree failed: %s" % proc.stderr.strip())]
        names = [n for n in proc.stdout.splitlines() if n.strip()]
        def read(n):
            p = run(["git", "show", "%s:%s" % (ref, n)], cwd=str(root))
            return p.stdout if p.returncode == 0 else ""
    else:
        teams = root / "teams"
        names = [str(p.relative_to(root)) for p in sorted(teams.rglob("*"))
                 if p.is_file()]
        def read(n):
            try:
                return (root / n).read_text(errors="replace")
            except OSError:
                return ""

    for name in names:
        text = read(name)
        if not text:
            continue
        for mid, rx in patterns:
            hits = len(rx.findall(text))
            if hits:
                violations.append((name, "%s x%d" % (mid, hits)))
    return violations


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ref", default=None,
                    help="git ref to check (default: the working tree)")
    ap.add_argument("--no-self-test", action="store_true",
                    help="skip the verifier self-test (NOT recommended in CI)")
    args = ap.parse_args(argv)

    root = repo_root()
    if root is None:
        print("error: not inside a git checkout. These scripts resolve the "
              "repo from their own location, so run them from a checkout "
              "(e.g. after actions/checkout), not from a copied directory.",
              file=sys.stderr)
        return 2

    print("DevChain config invariants — %s" % (args.ref or "working tree"))
    print("repo: %s\n" % root)
    failed = []

    # --- invariants 1, 2, 4 -------------------------------------------------
    # Tree selection must match invariant 3 exactly. verify-presets.py defaults
    # to --ref HEAD (the COMMITTED tree), so passing no selector here would
    # silently check a different tree than invariant 3 scans. In CI the two
    # coincide (checkout == HEAD == working tree) and the mismatch is invisible;
    # in the pre-commit hook it is not -- the hook exists to judge uncommitted
    # work, and would have skipped round-trip drift in exactly the staged change
    # it was invoked to police. Always pass an explicit selector.
    cmd = [sys.executable, str(VERIFY)]
    cmd += ["--ref", args.ref] if args.ref else ["--dir", str(root)]
    print("[1,2,4] round-trip (sources->artifact) / dangling pins / allowlist")
    proc = run(cmd, cwd=str(root))
    for line in (proc.stdout or "").rstrip("\n").split("\n"):
        if line.strip():
            print("        %s" % line)
    if proc.returncode == 2:
        print(proc.stderr, file=sys.stderr)
        return 2
    if proc.returncode != 0:
        failed.append("round-trip / dangling-pin / allowlist")

    # --- invariant 3 --------------------------------------------------------
    print("\n[3]     retired model IDs (exact-boundary, incl. composed JSON)")
    retired = check_retired(root, args.ref)
    if retired:
        failed.append("retired-model-id")
        for name, detail in retired:
            print("        FAIL %s: %s" % (name, detail))
    else:
        print("        ok   0 retired IDs across teams/")

    # --- self-test ----------------------------------------------------------
    if not args.no_self_test:
        print("\n[self]  verifier self-test (proves the checks still fail on "
              "seeded defects)")
        st = run([sys.executable, str(VERIFY), "--self-test"], cwd=str(root))
        for line in (st.stdout or "").rstrip("\n").split("\n"):
            if line.strip() and ("[" in line or "SELF-TEST" in line):
                print("        %s" % line.strip())
        if st.returncode != 0:
            failed.append("self-test")

    print("\n" + "=" * 62)
    if failed:
        print("RESULT: FAIL — %s" % ", ".join(failed))
        return 1
    print("RESULT: PASS — all four invariants hold; self-test green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
