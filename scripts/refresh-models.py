#!/usr/bin/env python3
"""Refresh model pins across a DevChain preset directory.

Usage
-----
  # dry run (default) -- prints what would change, touches nothing
  scripts/refresh-models.py teams/claude-codex-gemini-advanced \\
      --rule gemini-3.1-pro=gemini-3.1-pro-preview \\
      --rule gpt-5.2=gpt-5.6-terra

  # apply, and record the new IDs in scripts/approved-models.txt
  scripts/refresh-models.py teams/<preset> --rule OLD=NEW --apply --epic 055b0226

  # rules from a file (one OLD=NEW per line, # comments allowed)
  scripts/refresh-models.py teams/<preset> --rules-file rules.txt --apply

After applying, run compose.py on the preset and verify with verify-presets.py.
This script never touches the composed <preset>.json -- that is generated.

Two properties make this more than a sed loop; both were rediscovered
independently by two agents during the Phase 1 model refresh, so they are
documented here rather than left to be rediscovered a third time.

1. SINGLE-PASS ALTERNATION.
   All rules are compiled into one alternation and applied in a single
   re.sub pass, so each source position is rewritten at most once. A
   sequential chain (rule 1, then rule 2 over rule 1's output) lets a later
   rule re-match an earlier rule's output. That is what produces
   `gemini-3.1-pro-preview-preview`.

2. RAW-TEXT EDITING, never json.load/json.dump.
   The repo's `providerConfigs` entries are hand-maintained single-line JSON
   objects. A load/dump round-trip reflows them, which breaks byte-identity
   with the committed composed JSON and fails the round-trip check.

Boundary rule (subtle, and the reason this is not a plain string replace):

  * A TRAILING boundary is required: `claude-opus-4-5(?![A-Za-z0-9._-])`.
    It gives exact-boundary matching (so `gpt-5.2` never matches inside
    `gpt-5.25`) and, for free, cross-run IDEMPOTENCY when a rule extends its
    own input as a prefix -- `gemini-3.1-pro` -> `gemini-3.1-pro-preview`.
    On a second run the text reads `gemini-3.1-pro-preview`; the character
    after `gemini-3.1-pro` is `-`, which is in the boundary class, so it does
    not match. No special-casing needed per rule.

  * A LEADING boundary must NOT be required. Provider-config names embed the
    model ID as a suffix (`default-claude-opus-4-5`), so the match is preceded
    by `-`. Requiring a leading boundary would silently skip every config
    rename -- which is exactly the rename the refresh is supposed to perform.

Python 3 standard library only.
"""

import argparse
import datetime
import pathlib
import re
import sys

# Characters that may continue a model identifier. Used for the trailing
# boundary; see the module docstring for why there is no leading boundary.
IDENT_TAIL = r"[A-Za-z0-9._\-]"

# Matches both option syntaxes:
#   codex-style   --model=gpt-5.6-terra
#   claude/gemini --model gpt-5.6-terra
MODEL_OPT = re.compile(r"--model[=\s]+([A-Za-z0-9][A-Za-z0-9._\-]*)")

# Subdirectories whose *.json files carry model pins / config references.
TARGET_GLOBS = ("profiles/*.json", "agents/*.json")


def parse_rule(text):
    if "=" not in text:
        raise argparse.ArgumentTypeError(
            "rule must be OLD=NEW (got %r)" % text)
    old, new = text.split("=", 1)
    old, new = old.strip(), new.strip()
    if not old or not new:
        raise argparse.ArgumentTypeError("rule has an empty side: %r" % text)
    return (old, new)


def load_rules_file(path):
    rules = []
    for raw in pathlib.Path(path).read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            rules.append(parse_rule(line))
    return rules


def build_pattern(rules):
    """Compile all rules into ONE alternation -> single-pass, no cascading."""
    parts = []
    for i, (old, _new) in enumerate(rules):
        parts.append("(?P<r%d>%s(?!%s))" % (i, re.escape(old), IDENT_TAIL))
    return re.compile("|".join(parts))


def rewrite(text, rules, pattern):
    counts = {}

    def _sub(m):
        idx = int(m.lastgroup[1:])
        counts[idx] = counts.get(idx, 0) + 1
        return rules[idx][1]

    return pattern.sub(_sub, text), counts


def iter_targets(preset_dir):
    for glob in TARGET_GLOBS:
        for path in sorted(preset_dir.glob(glob)):
            yield path


def update_allowlist(allowlist_path, rules, epic, today):
    """Drop retired IDs, add new ones. Comment-preserving, append-only."""
    if not allowlist_path.exists():
        print("  ! allowlist not found, skipping: %s" % allowlist_path)
        return 0, 0

    lines = allowlist_path.read_text().splitlines()
    retired = {old for old, _ in rules}
    incoming = {new for _, new in rules}

    kept, removed = [], 0
    for line in lines:
        entry = line.split("#", 1)[0].strip()
        if entry and entry in retired and entry not in incoming:
            removed += 1
            continue
        kept.append(line)

    present = set()
    for line in kept:
        entry = line.split("#", 1)[0].strip()
        if entry:
            present.add(entry)

    ref = (", epic %s" % epic) if epic else ""
    added = 0
    for new in sorted(incoming - present):
        kept.append("%-25s # added %s%s" % (new, today, ref))
        added += 1

    text = "\n".join(kept).rstrip("\n") + "\n"
    allowlist_path.write_text(text)
    return added, removed


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Refresh model pins in a DevChain preset directory.")
    ap.add_argument("preset_dir",
                    help="path to teams/<preset>/ (the decomposed directory)")
    ap.add_argument("--rule", type=parse_rule, action="append", default=[],
                    metavar="OLD=NEW", help="substitution rule; repeatable")
    ap.add_argument("--rules-file", help="file of OLD=NEW lines")
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default is a dry run)")
    ap.add_argument("--allowlist", default=None,
                    help="path to approved-models.txt "
                         "(default: alongside this script)")
    ap.add_argument("--epic", default=None,
                    help="epic ref recorded in new allowlist entries")
    ap.add_argument("--no-allowlist-update", action="store_true",
                    help="do not touch approved-models.txt")
    args = ap.parse_args(argv)

    rules = list(args.rule)
    if args.rules_file:
        rules.extend(load_rules_file(args.rules_file))
    if not rules:
        ap.error("no rules given (use --rule OLD=NEW or --rules-file)")

    preset_dir = pathlib.Path(args.preset_dir)
    if not preset_dir.is_dir():
        print("error: not a directory: %s" % preset_dir, file=sys.stderr)
        return 2

    pattern = build_pattern(rules)
    totals = {}
    changed = 0

    for path in iter_targets(preset_dir):
        original = path.read_text()
        updated, counts = rewrite(original, rules, pattern)
        if updated == original:
            continue
        changed += 1
        for k, v in counts.items():
            totals[k] = totals.get(k, 0) + v
        detail = ", ".join("%s->%s x%d" % (rules[k][0], rules[k][1], v)
                           for k, v in sorted(counts.items()))
        print("  %-58s %s" % (path.relative_to(preset_dir), detail))
        if args.apply:
            path.write_text(updated)

    print("\nfiles changed: %d" % changed)
    for k in sorted(totals):
        print("  %-24s -> %-24s %d" % (rules[k][0], rules[k][1], totals[k]))

    if args.apply and not args.no_allowlist_update:
        allow = (pathlib.Path(args.allowlist) if args.allowlist
                 else pathlib.Path(__file__).resolve().parent
                 / "approved-models.txt")
        today = datetime.date.today().isoformat()
        added, removed = update_allowlist(allow, rules, args.epic, today)
        print("allowlist %s: +%d entry(ies), -%d retired"
              % (allow.name, added, removed))

    print("MODE: %s" % ("APPLIED" if args.apply else "DRY-RUN"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
