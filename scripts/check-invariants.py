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
import datetime
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
VERIFY = HERE / "verify-presets.py"

# --- audit staleness ------------------------------------------------------
# Separate concern from the four invariants, and deliberately a SEPARATE CI
# step: the invariants judge the tree you just changed, this judges whether
# anyone has recently checked the pins against the outside world. A developer
# seeing one red step named for audit staleness beside green invariant steps
# diagnoses it in a second.
AUDIT_DIR = "docs/audits"

# Cadence is monthly plus two event triggers (Epic Manager's decision, recorded
# on epic 39de8b7b). 45 days leaves ~2 weeks of slack on a monthly cadence
# before CI objects, so a slightly late audit does not red the build.
AUDIT_STALE_DAYS = 45

# Audit filenames are hand-typed. A future-dated typo (2027 for 2026) would
# otherwise satisfy the freshness test forever and mask real staleness, so it
# is its own failure. One day of tolerance absorbs timezone skew between an
# author's local date and the UTC runner.
AUDIT_FUTURE_TOLERANCE_DAYS = 1

# Pattern-match FIRST, then date-validate. Anything not shaped exactly like
# YYYY-MM-DD.md is not an audit entry and is ignored outright -- README.md and
# any other companion file must be able to live in this directory without
# being mistaken for one.
AUDIT_NAME_RX = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.md$")

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


def audit_entries(root, ref):
    """Return (dates, ignored, dir_present) for docs/audits/.

    Dates are parsed from FILENAMES, never from mtime. A git checkout does not
    preserve mtime -- CI clones fresh, so every file looks written seconds ago
    and an mtime-based check would report a three-year-old audit as current.

    Precedence is pattern-match first, then date-validate: a name that is not
    YYYY-MM-DD.md is `ignored` (a companion README is legitimate), whereas a
    name that matches the shape but encodes an impossible date (2026-02-30) is
    a typo, not an audit, and cannot count as the newest entry.
    """
    if ref:
        proc = run(["git", "ls-tree", "--name-only", "%s:%s" % (ref, AUDIT_DIR)],
                   cwd=str(root))
        if proc.returncode != 0:
            return [], [], False
        names = [n.strip() for n in proc.stdout.splitlines() if n.strip()]
    else:
        d = root / AUDIT_DIR
        if not d.is_dir():
            return [], [], False
        names = sorted(p.name for p in d.iterdir() if p.is_file())

    dates, ignored = [], []
    for name in names:
        m = AUDIT_NAME_RX.match(name)           # 1. pattern
        if not m:
            ignored.append(name)
            continue
        try:                                     # 2. then validate
            dates.append(datetime.date(int(m.group(1)), int(m.group(2)),
                                       int(m.group(3))))
        except ValueError:
            ignored.append("%s (invalid date)" % name)
    return dates, ignored, True


def check_audit_staleness(root, ref, today=None):
    """Audit-recency check. Returns (ok, lines).

    Enforces only that SOMEONE HAS RUN THE AUDIT RECENTLY -- never what the
    audit found. A ledger full of known-blocked entries is a perfectly valid
    fresh audit. Runs no network calls and needs no credentials; checking the
    pins against reality requires provider access and stays the runbook's job.
    """
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    dates, ignored, present = audit_entries(root, ref)
    lines = []
    if ignored:
        lines.append("ignored (not YYYY-MM-DD.md): %s" % ", ".join(ignored))

    if not dates:
        why = ("%s/ contains no YYYY-MM-DD.md entries" % AUDIT_DIR if present
               else "%s/ does not exist" % AUDIT_DIR)
        lines += [
            "FAIL  no model-pin audit found — %s." % why,
            "      This check enforces that the audit has been RUN recently.",
            "      Remedy: follow docs/model-pin-audit.md, then commit its",
            "      result as %s/%s.md" % (AUDIT_DIR, today.isoformat()),
        ]
        return False, lines

    newest = max(dates)
    age = (today - newest).days

    if newest > today + datetime.timedelta(days=AUDIT_FUTURE_TOLERANCE_DAYS):
        lines += [
            "FAIL  future-dated audit file — check the filename.",
            "      newest entry %s is later than today (%s, UTC)."
            % (newest.isoformat(), today.isoformat()),
            "      Audit filenames are hand-typed; a future date would satisfy",
            "      this check forever and hide a genuinely stale audit.",
            "      Remedy: rename %s/%s.md to the date the audit actually ran."
            % (AUDIT_DIR, newest.isoformat()),
        ]
        return False, lines

    if age > AUDIT_STALE_DAYS:
        lines += [
            "FAIL  this failure is NOT caused by your change — the model-pin "
            "audit is stale.",
            "      newest audit %s is %d days old (threshold %d)."
            % (newest.isoformat(), age, AUDIT_STALE_DAYS),
            "      Remedy: follow docs/model-pin-audit.md, then commit its",
            "      result as %s/%s.md" % (AUDIT_DIR, today.isoformat()),
            "      a fresh %s/%s.md may ride this PR."
            % (AUDIT_DIR, today.isoformat()),
        ]
        return False, lines

    lines.append("ok   newest audit %s, %d day(s) old (threshold %d)"
                 % (newest.isoformat(), age, AUDIT_STALE_DAYS))
    return True, lines


def audit_self_test():
    """Prove the staleness check still fails on each seeded violation class.

    Same reasoning as the verifier's self-test: a check that passes everything
    is indistinguishable from a check that checks nothing. Each case below must
    be CAUGHT; the fresh and ignore cases must pass.
    """
    today = datetime.date(2026, 7, 26)          # fixed, so the suite is stable
    cases = [
        ("fresh audit passes",              ["2026-07-20.md"],                 True),
        ("README coexists, still fresh",    ["2026-07-20.md", "README.md"],    True),
        ("stale audit caught",              ["2026-01-01.md"],                 False),
        ("empty audit dir caught",          [],                                False),
        ("only non-matching files caught",  ["README.md", "notes.txt"],        False),
        ("future-dated caught",             ["2027-01-01.md"],                 False),
        ("invalid date not counted",        ["2026-02-30.md", "2026-01-01.md"], False),
    ]
    print("        AUDIT SELF-TEST — each violation case must be CAUGHT")
    ok_all = True
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)
        for label, names, expect_ok in cases:
            case_root = base / label.replace(" ", "_")
            (case_root / AUDIT_DIR).mkdir(parents=True)
            for n in names:
                (case_root / AUDIT_DIR / n).write_text("x\n")
            ok, _ = check_audit_staleness(case_root, None, today=today)
            good = (ok == expect_ok)
            ok_all &= good
            print("        [%s] %-34s expected %s" %
                  ("PASS" if good else "FAIL", label,
                   "GREEN" if expect_ok else "RED"))

        # missing directory entirely (distinct from an empty one)
        ok, _ = check_audit_staleness(base / "no_such_repo", None, today=today)
        good = (ok is False)
        ok_all &= good
        print("        [%s] %-34s expected RED" %
              ("PASS" if good else "FAIL", "missing audit dir caught"))

    print("        AUDIT SELF-TEST %s" % ("PASSED" if ok_all else "FAILED"))
    return ok_all


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ref", default=None,
                    help="git ref to check (default: the working tree)")
    ap.add_argument("--no-self-test", action="store_true",
                    help="skip the verifier self-test (NOT recommended in CI)")
    ap.add_argument("--audit-staleness", action="store_true",
                    help="run ONLY the model-pin audit recency check "
                         "(its own CI step; see docs/model-pin-audit.md)")
    args = ap.parse_args(argv)

    root = repo_root()
    if root is None:
        print("error: not inside a git checkout. These scripts resolve the "
              "repo from their own location, so run them from a checkout "
              "(e.g. after actions/checkout), not from a copied directory.",
              file=sys.stderr)
        return 2

    # --- audit staleness ----------------------------------------------------
    # Deliberately its OWN mode and its own CI step, never folded into the
    # invariants run. The two answer different questions and fail for unrelated
    # reasons: the invariants say "your change is inconsistent", this says
    # "nobody has checked the pins against reality lately". Merging them would
    # make a stale audit look like a broken change.
    if args.audit_staleness:
        print("Model-pin audit freshness — %s" % (args.ref or "working tree"))
        print("repo: %s\n" % root)
        ok, lines = check_audit_staleness(root, args.ref)
        for line in lines:
            print("        %s" % line)
        st_ok = True
        if not args.no_self_test:
            print("\n[self]  staleness-check self-test")
            st_ok = audit_self_test()
        print("\n" + "=" * 62)
        if not ok or not st_ok:
            print("RESULT: FAIL — %s" %
                  ("stale/missing/future-dated model-pin audit" if not ok
                   else "audit self-test"))
            return 1
        print("RESULT: PASS — model-pin audit is fresh; self-test green")
        return 0

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
