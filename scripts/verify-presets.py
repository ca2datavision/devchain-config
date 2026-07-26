#!/usr/bin/env python3
"""Verify DevChain preset config invariants. Exits non-zero on any violation.

Usage
-----
  scripts/verify-presets.py                    # all presets at HEAD
  scripts/verify-presets.py --ref <commit>     # a specific commit
  scripts/verify-presets.py --preset claude-codex-gemini-advanced
  scripts/verify-presets.py --dir <path>       # a standalone tree (no git)
  scripts/verify-presets.py --self-test        # prove the checks actually fail

Exit codes: 0 = all invariants hold, 1 = violation(s), 2 = usage/environment.

Invariants checked
------------------
1. ALLOWLIST -- every `--model` value in every profile appears in
   scripts/approved-models.txt. An allowlist, not a denylist: a denylist of
   retired IDs cannot catch a typo'd or newly-invented ID. Both option
   syntaxes are recognised (`--model=<id>` and `--model <id>`).

2. NO DANGLING PINS -- every agent `providerConfigName` resolves, via
   agent.profileId -> profile.id -> profile.providerConfigs[].name.
   NOTE: agents have NO `profileName` field. Keying on one yields a false
   DANGLING verdict on clean work (this happened during a Phase 1 review).

3. ROUND-TRIP, sources -> artifact -- compose from the tracked
   teams/<preset>/ directory and compare byte-for-byte with the committed
   teams/<preset>.json.
   Direction matters and is the whole point. artifact->artifact (decompose
   the composed JSON, then recompose it) proves only self-consistency and
   never reads the tracked source directory, so a composed file hand-edited
   away from its sources passes it. sources->artifact is the direction that
   catches that drift.

Safety
------
Verification NEVER mutates the tracked tree. compose.py writes
`<dir>.json` in place, so an in-tree "read-only" check would rewrite the
repo. Everything here runs against a throwaway copy materialised by
`git archive` (or a filesystem copy in --dir mode).

Do NOT reach for decompose.py in a checker: it computes
`out_dir = json_path.parent / json_path.stem` and `shutil.rmtree`s it, so
pointing it at `teams/<preset>.json` DELETES the tracked source directory.

Python 3 standard library only.
"""

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

MODEL_OPT = re.compile(r"--model[=\s]+([A-Za-z0-9][A-Za-z0-9._\-]*)")
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_ALLOWLIST = pathlib.Path(__file__).resolve().parent / "approved-models.txt"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def load_allowlist(path):
    approved = set()
    for raw in pathlib.Path(path).read_text().splitlines():
        entry = raw.split("#", 1)[0].strip()
        if entry:
            approved.add(entry)
    return approved


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def discover_presets(teams_dir):
    out = []
    for js in sorted(teams_dir.glob("*.json")):
        if (teams_dir / js.stem).is_dir():
            out.append(js.stem)
    return out


def materialise_from_git(ref, dest, repo=REPO_ROOT):
    """Extract compose.py + teams/ at `ref` into dest. Never touches the tree."""
    proc = subprocess.run(
        "git archive %s compose.py teams | tar -x -C %s" % (ref, dest),
        shell=True, cwd=str(repo), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("git archive failed: %s" % proc.stderr.strip())


def materialise_from_dir(src, dest):
    src = pathlib.Path(src)
    shutil.copytree(src / "teams", dest / "teams")
    compose = src / "compose.py"
    if not compose.exists():
        compose = REPO_ROOT / "compose.py"
    shutil.copy2(compose, dest / "compose.py")


# --------------------------------------------------------------------------
# invariant checks
# --------------------------------------------------------------------------

def check_allowlist(preset_dir, approved):
    """Invariant 1. Returns list of violation strings."""
    bad = []
    for path in sorted(preset_dir.glob("profiles/*.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            bad.append("%s: invalid JSON (%s)" % (path.name, exc))
            continue
        blobs = [data.get("options") or ""]
        for cfg in data.get("providerConfigs") or []:
            blobs.append(cfg.get("options") or "")
        for blob in blobs:
            for model in MODEL_OPT.findall(blob):
                if model not in approved:
                    bad.append("%s: model %r not in allowlist" % (path.name, model))
    return bad


def check_dangling(preset_dir):
    """Invariant 2. Resolve via profileId -> profile.id -> providerConfigs[].name."""
    bad = []
    profiles = {}
    for path in sorted(preset_dir.glob("profiles/*.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if data.get("id"):
            profiles[data["id"]] = data

    for path in sorted(preset_dir.glob("agents/*.json")):
        try:
            agent = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            bad.append("%s: invalid JSON (%s)" % (path.name, exc))
            continue
        pcn = agent.get("providerConfigName")
        if not pcn:
            continue  # preset without providerConfigs -- nothing to resolve
        profile = profiles.get(agent.get("profileId"))
        if profile is None:
            bad.append("%s: profileId %r matches no profile"
                       % (path.name, agent.get("profileId")))
            continue
        names = [c.get("name") for c in (profile.get("providerConfigs") or [])]
        if pcn not in names:
            bad.append("%s: providerConfigName %r not in profile %r"
                       % (path.name, pcn, profile.get("name")))
    return bad


def check_roundtrip(work, preset):
    """Invariant 3, sources -> artifact. `work` holds compose.py + teams/."""
    committed = work / "teams" / (preset + ".json")
    if not committed.exists():
        return ["%s.json missing" % preset]
    saved = work / (preset + ".committed.json")
    shutil.copy2(committed, saved)

    proc = run([sys.executable, str(work / "compose.py"),
                str(work / "teams" / preset)])
    if proc.returncode != 0:
        return ["compose.py failed: %s" % (proc.stderr.strip() or proc.stdout.strip())]

    if committed.read_bytes() != saved.read_bytes():
        return ["round-trip drift: composing teams/%s/ does not reproduce "
                "teams/%s.json byte-for-byte" % (preset, preset)]
    return []


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def verify(work, presets, approved, quiet=False):
    """Return a list of (preset, kind, message) for every violation found."""
    found = []
    for preset in presets:
        preset_dir = work / "teams" / preset
        problems = []
        problems += [("allowlist", m) for m in check_allowlist(preset_dir, approved)]
        problems += [("dangling-pin", m) for m in check_dangling(preset_dir)]
        problems += [("round-trip", m) for m in check_roundtrip(work, preset)]
        if problems:
            found += [(preset, k, m) for k, m in problems]
            if not quiet:
                print("FAIL %s" % preset)
                for kind, msg in problems:
                    print("    [%s] %s" % (kind, msg))
        elif not quiet:
            print("ok   %s" % preset)
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ref", default="HEAD", help="git ref to verify (default HEAD)")
    ap.add_argument("--dir", default=None,
                    help="verify a standalone tree containing teams/ (no git)")
    ap.add_argument("--preset", action="append", default=[],
                    help="limit to this preset; repeatable")
    ap.add_argument("--allowlist", default=str(DEFAULT_ALLOWLIST))
    ap.add_argument("--self-test", action="store_true",
                    help="seed one violation per class and assert each is caught")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test(args)

    approved = load_allowlist(args.allowlist)
    with tempfile.TemporaryDirectory(prefix="verify-presets-") as tmp:
        work = pathlib.Path(tmp)
        try:
            if args.dir:
                materialise_from_dir(args.dir, work)
            else:
                materialise_from_git(args.ref, work)
        except Exception as exc:                       # noqa: BLE001
            print("error: %s" % exc, file=sys.stderr)
            return 2

        presets = args.preset or discover_presets(work / "teams")
        if not presets:
            print("error: no presets found", file=sys.stderr)
            return 2
        failures = verify(work, presets, approved)

    print("\n%d violation(s)" % len(failures))
    return 1 if failures else 0


# --------------------------------------------------------------------------
# self-test: a checker that passes everything is indistinguishable from a
# checker that checks nothing, so prove each check FAILS on a seeded defect.
# --------------------------------------------------------------------------

def _seed_bad_model(preset_dir, equals_syntax):
    """Write a retired ID using one of the two option syntaxes."""
    for path in sorted(preset_dir.glob("profiles/*.json")):
        text = path.read_text()
        if equals_syntax and "--model=" in text:
            path.write_text(text.replace("--model=", "--model=RETIRED-", 1))
            return "%s (--model=<id>)" % path.name
        if not equals_syntax and re.search(r"--model ", text):
            path.write_text(re.sub(r"--model ", "--model RETIRED-", text, count=1))
            return "%s (--model <id>)" % path.name
    return None


def _seed_dangling(preset_dir):
    for path in sorted(preset_dir.glob("agents/*.json")):
        data = json.loads(path.read_text())
        if data.get("providerConfigName"):
            data["providerConfigName"] = "no-such-config-xyz"
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            return path.name
    return None


def _seed_drift(work, preset):
    """Hand-edit the COMPOSED json so it no longer matches its sources."""
    js = work / "teams" / (preset + ".json")
    data = json.loads(js.read_text())
    data["exportedAt"] = "DRIFTED-BY-SELF-TEST"
    js.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return js.name


def self_test(args):
    approved = load_allowlist(args.allowlist)
    print("SELF-TEST — each case must be CAUGHT (verify returns non-zero)\n")
    results = []

    def fresh(tmp, name):
        work = pathlib.Path(tmp) / name
        work.mkdir()
        materialise_from_git(args.ref, work)
        return work

    with tempfile.TemporaryDirectory(prefix="verify-selftest-") as tmp:
        probe = fresh(tmp, "probe")
        presets = discover_presets(probe / "teams")
        # prefer a preset that actually has agent pins, so the dangling case is real
        target = None
        for p in presets:
            if _has_pins(probe / "teams" / p):
                target = p
                break
        target = target or presets[0]
        print("  target preset: %s\n" % target)

        # Each seeded case must be caught by the SPECIFIC check it targets.
        # Asserting only "some violation fired" is too weak: mutating a source
        # file also perturbs the composed artifact, so round-trip alone would
        # report a violation for every case. That would let the allowlist and
        # dangling-pin checks rot to no-ops while the suite still went green.
        def expect(work, kind, label):
            hits = verify(work, [target], approved, quiet=True)
            kinds = sorted({k for _, k, _ in hits})
            ok = kind in kinds
            return (label, ok,
                    "caught by %s" % ("+".join(kinds) or "nothing")
                    if ok else "expected %s, got %s" % (kind, kinds or "nothing"))

        # 0. clean tree must PASS
        work = fresh(tmp, "clean")
        hits = verify(work, [target], approved, quiet=True)
        results.append(("clean preset returns zero", not hits,
                        "%d violation(s)" % len(hits)))

        # 1. retired ID, codex syntax --model=<id>
        work = fresh(tmp, "bad_eq")
        where = _seed_bad_model(work / "teams" / target, True)
        results.append(expect(work, "allowlist",
                              "retired ID via --model=<id>  [%s]" % where))

        # 2. retired ID, claude/gemini syntax --model <id>
        work = fresh(tmp, "bad_sp")
        where = _seed_bad_model(work / "teams" / target, False)
        results.append(expect(work, "allowlist",
                              "retired ID via --model <id>  [%s]" % where))

        # 3. dangling providerConfigName
        work = fresh(tmp, "dangling")
        where = _seed_dangling(work / "teams" / target)
        results.append(expect(work, "dangling-pin",
                              "dangling providerConfigName [%s]" % where))

        # 4. round-trip drift -- ONLY the composed artifact is touched, so no
        #    source-level check can fire and this isolates the round-trip check.
        work = fresh(tmp, "drift")
        where = _seed_drift(work, target)
        results.append(expect(work, "round-trip",
                              "round-trip drift [%s]" % where))

        # 5. refresh idempotency: second run is a no-op
        results.append(_idempotency_case(tmp, args.ref, target))

    print()
    ok = True
    for name, passed, detail in results:
        print("  [%s] %-52s %s" % ("PASS" if passed else "FAIL", name, detail))
        ok = ok and passed
    print("\nSELF-TEST %s" % ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


def _has_pins(preset_dir):
    for path in preset_dir.glob("agents/*.json"):
        try:
            if json.loads(path.read_text()).get("providerConfigName"):
                return True
        except json.JSONDecodeError:
            pass
    return False


def _idempotency_case(tmp, ref, target):
    """Apply a prefix-extending rule twice; the second run must change nothing."""
    work = pathlib.Path(tmp) / "idem"
    work.mkdir()
    materialise_from_git(ref, work)
    preset_dir = work / "teams" / target
    refresh = pathlib.Path(__file__).resolve().parent / "refresh-models.py"

    # A prefix-extending rule is the corruption-prone shape: naive repetition
    # yields gemini-3.1-pro-preview-preview.
    rule = "gemini-2.5-pro=gemini-2.5-pro-preview"
    cmd = [sys.executable, str(refresh), str(preset_dir),
           "--rule", rule, "--apply", "--no-allowlist-update"]

    first = run(cmd)
    if first.returncode != 0:
        return ("refresh idempotency", False, "first run failed: %s" % first.stderr.strip())
    snapshot = {p: p.read_bytes() for p in sorted(preset_dir.rglob("*.json"))}

    second = run(cmd)
    if second.returncode != 0:
        return ("refresh idempotency", False, "second run failed: %s" % second.stderr.strip())
    after = {p: p.read_bytes() for p in sorted(preset_dir.rglob("*.json"))}

    if snapshot != after:
        changed = [p.name for p in after if snapshot.get(p) != after[p]]
        return ("refresh idempotency (2nd run = empty diff)", False,
                "changed on 2nd run: %s" % ", ".join(changed))
    # and prove the first run actually did something, else this proves nothing
    did_work = any(b"gemini-2.5-pro-preview" in v for v in after.values())
    return ("refresh idempotency (2nd run = empty diff)", did_work,
            "1st run applied, 2nd run no-op" if did_work else "rule never matched")


if __name__ == "__main__":
    sys.exit(main())
