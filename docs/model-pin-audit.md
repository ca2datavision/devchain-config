# Model-Pin Audit Runbook

Periodic check for **external staleness** — a provider retiring or withdrawing a
model this repo still pins. CI cannot catch this: `scripts/check-invariants.py`
runs with no credentials and makes no network calls, so it proves *internal
consistency* and never *external validity*. Every pin here could be withdrawn
tomorrow and all four CI invariants would stay green.

That is not hypothetical. `gemini-3.1-pro` sat pinned in production configs
returning **HTTP 404** and was found only by accident during an unrelated
review — the second silent-staleness incident. This runbook exists so the third
one is found on purpose.

**Cadence is not set here.** This document defines *how* to audit; when to run
it is an Epic Manager triage decision.

**No live-completion requirement** (user decision). The audit establishes
*ID validity*, *documentation presence*, and *allowlist agreement*. It does not
require any model to actually produce output — a 429 is a pass.

---

## What the audit covers

| # | Check | Answers |
|---|---|---|
| 1 | CLI ID-validity signal | Does the provider still recognise this ID? |
| 2 | Documentation cross-check | Is it still listed in official docs? |
| 3 | Allowlist comparison | Do pins and `scripts/approved-models.txt` agree? |

Record findings in `docs/audits/YYYY-MM-DD.md` (see template at the bottom).

---

## Step 0 — extract what is actually pinned

Never audit from memory or from the allowlist alone; read the configs.

```bash
grep -rhoE '\-\-model[= ][A-Za-z0-9][A-Za-z0-9._-]*' teams/ \
  | sed -E 's/--model[= ]//' | sort | uniq -c | sort -rn
```

---

## Step 1 — CLI ID-validity signal

### Trust guards — the obvious invocations do NOT work

Each CLI refuses to run in an untrusted directory, and the failures look
nothing like model errors. These guards cost debugging time on every audit,
so they are baked into the commands below.

| CLI | Guard needed | Failure if omitted |
|---|---|---|
| `codex` | `--skip-git-repo-check` **and** stdin from `/dev/null` | `Not inside a trusted directory`, exit 1; or blocks reading stdin |
| `gemini` | `--skip-trust` | `not running in a trusted directory`, exit 55 |
| `claude` | none | — |

### Copy-pasteable

```bash
# Anthropic
claude --model <id> -p "say ok"

# OpenAI / Codex
codex exec --skip-git-repo-check -m <id> "say ok" < /dev/null

# Google / Gemini
gemini --skip-trust -m <id> -p "say ok" < /dev/null
```

### Status semantics

| Signal | Verdict | Action |
|---|---|---|
| 2xx / normal reply | **OK** | none |
| **404 / unknown-model** | **STALE — defect** | flag immediately; the pin is broken in production |
| 429 / quota exceeded | **VALID-but-blocked** | record in the Known-Blocked Ledger |
| CLI missing / auth failure | **INCONCLUSIVE** | record as such — *never* as OK |

### Why 429 counts as a pass

Model validation happens **before** the quota gate. A bogus ID returns 404 and
never reaches quota, so a 429 proves the ID resolved. Verify this with a control
whenever the semantics are questioned:

```bash
gemini --skip-trust -m gemini-9.9-bogus-control -p "say ok" < /dev/null
# expect: ModelNotFoundError, code: 404  — NOT 429
```

If a deliberately bogus ID ever returns 429 instead of 404, this reasoning is
void and every 429 verdict in the ledger must be re-examined.

> **Gemini free-tier 429 is permanently expected** (user decision). The local
> CLI authenticates against a free tier with `limit: 0`. Gemini entries are
> expected to be VALID-but-blocked indefinitely; that is not a regression.

---

## Step 2 — documentation cross-check (pinned sources)

| Provider | Pinned source |
|---|---|
| Google Gemini | <https://ai.google.dev/gemini-api/docs/models> — canonical, per user decision |
| OpenAI | <https://platform.openai.com/docs/models> |
| Anthropic | <https://docs.anthropic.com/en/docs/about-claude/models/overview> |

### Match on an exact boundary — never a plain substring

```bash
curl -s -o /tmp/doc.html -w 'HTTP=%{http_code}\n' -L --max-time 25 "<url>"

python3 - "$MODEL_ID" <<'PY'
import re, sys
mid = sys.argv[1]
text = open('/tmp/doc.html', errors='replace').read()
# Same trailing-boundary rule as scripts/refresh-models.py. Without it,
# `gemini-3.1-pro` matches inside `gemini-3.1-pro-preview`.
print(len(re.findall(re.escape(mid) + r"(?![A-Za-z0-9._\-])", text)))
PY
```

**A plain `grep -F` here is wrong and has already produced a false positive.**
`gemini-3.1-pro` is a strict prefix of `gemini-3.1-pro-preview`, so a substring
search reports the retired ID as "present" when only its successor is listed.
This is the project's signature trap — the same one that forces exact-boundary
greps everywhere else, and that `scripts/refresh-models.py` solves with
`re.escape(OLD) + (?![A-Za-z0-9._-])`. Reuse that rule; do not re-derive it.

### Boundary matching is necessary but NOT sufficient — you are searching markup

Even a boundary-correct count over raw HTML counts **markup**, not model
listings. Observed on the real pages:

| What matched | Example | Is it a model listing? |
|---|---|---|
| Heading anchor | `id="gemini-3.1-pro"` (slug of the heading "Gemini 3.1 Pro") | **No** |
| Doc-page URL | `/gemini-api/docs/models/gemini-2.5-pro` | Indirectly |
| Vendor-prefixed ID | `anthropic.claude-opus-5` (Bedrock form) | Yes, different namespace |
| Embedded JSON payload | `{"id":"claude-opus-4-5@20251101"}` | Yes, versioned form |

So a raw-HTML count answers *"does this string appear in the page source"*, not
*"is this model listed as available"*. Treat the number as a **triage signal**:
zero means look harder, non-zero means **read the rendered page** to see which
section the entry sits in. Record the count *and* what it actually was.

### ⚠️ Finding class: SOURCE UNAVAILABLE

If a source returns non-200, redirects somewhere unrecognisable, or returns a
body that cannot be searched, record it as **SOURCE UNAVAILABLE** — its own
finding class.

**It must never be recorded as "no staleness found."** An unreachable source
produces zero matches for every model, which is textually identical to a clean
result and semantically its opposite. This is the single easiest way for an
audit to report a false all-clear.

Fallback: try the provider's changelog/deprecations page, or the CLI's own model
list. If still unavailable, record SOURCE UNAVAILABLE and carry it to the next
audit — do not let it silently lapse.

### ⚠️ Providers differ in how they treat withdrawn models

This is the key thing to know before reading any Step 2 result. Verified on the
real pages during the first audit (2026-07-26):

| Provider | Withdrawn models are… | Evidence |
|---|---|---|
| **Google** | **removed** from the model list | `gemini-3.1-pro` (live 404) appears **nowhere** as a model ID — only a leftover heading anchor `id="gemini-3.1-pro"` |
| **OpenAI** | **removed** | retired `gpt-5.2` and `gpt-5.5` → **0** boundary-matched occurrences |
| **Anthropic** | **retained** under an explicit **"Legacy models"** heading | `claude-opus-4-5` and `claude-opus-4-7` still listed there |

**A doc hit therefore means different things per provider:**

- **Google / OpenAI** — the list reflects current availability, so **absence is
  meaningful** and a hit is reasonable evidence the model is current.
- **Anthropic** — **presence proves nothing on its own.** A superseded model is
  still listed; you must check *which section* it sits in. A hit outside the
  Legacy heading is the meaningful signal.

Consequences for reading the two steps together:

- A documentation hit **cannot clear** a model that fails Step 1.
- A documentation miss **cannot condemn** a model that passes Step 1 — it may
  be newer than the page, or listed under a different heading.
- **Step 1 remains the stronger signal.** Step 2's distinct value is catching
  *announced* deprecations before they become 404s — the advance warning Step 1
  structurally cannot give.

Treat a Step 1 / Step 2 disagreement as a finding to investigate, never as
something to average out.

> **Note on the user's documentation-based ruling for Gemini.** Because Google
> removes withdrawn models, a boundary-correct doc check *does* give a genuine
> availability signal for Gemini — `gemini-3.1-pro` is absent, which is the
> correct reading for a withdrawn model. That makes documentation-based
> validation a stronger control for Gemini than for Anthropic, whose Legacy
> table keeps superseded IDs visible indefinitely.

---

## Step 3 — allowlist comparison

```bash
python3 - <<'PY'
import re, pathlib
pins = set()
for p in pathlib.Path('teams').rglob('*'):
    if p.is_file():
        pins |= set(re.findall(r'--model[= ]([A-Za-z0-9][A-Za-z0-9._-]*)',
                               p.read_text(errors='replace')))
allow = {l.split('#')[0].strip() for l in open('scripts/approved-models.txt')
         if l.split('#')[0].strip()}
print("pinned but NOT approved:", sorted(pins - allow) or "none")
print("approved but NOT pinned:", sorted(allow - pins) or "none")
PY
```

- **pinned but not approved** → CI should already be red; investigate why it is not.
- **approved but not pinned** → harmless, but prune retired entries so the
  allowlist does not accumulate models nobody uses.

---

## Known-Blocked Ledger

Carried forward between audits. Its purpose is to let the next run distinguish
**persisting known-blocked** from a **new regression** — without it, a
recurring 429 and a fresh outage look identical.

| Model | Since | Signal | Why blocked | Expected to clear? |
|---|---|---|---|---|
| `gemini-2.5-pro` | 2026-07-26 | 429 quota | Local CLI on free tier, `limit: 0` | No — permanent per user decision |
| `gemini-3.1-pro-preview` | 2026-07-26 | 429 quota | Same | No — same |

When adding an entry, record the **signal** (429 vs inconclusive), not just
"blocked". A 429 means the ID resolved; an auth failure means nothing was
established at all.

---

## Findings file convention

When your findings prose cites repo code, prefer symbol anchors (`<file>.py::<symbol>`)
over line numbers — see "How to cite code in docs" in [preset-changes.md](preset-changes.md).
Existing audit files are exempt from the citation check and are never retro-edited; this
applies to new prose you write.

Write each run to `docs/audits/YYYY-MM-DD.md`:

```markdown
# Model-Pin Audit — YYYY-MM-DD

**Auditor:** <agent/person> · **Repo state:** <commit> · **Epic:** <ref>

## Summary
<one line: N models audited, N OK, N known-blocked, N stale, N source-unavailable>

## Per-model verdicts
| Model | CLI signal | Verdict | Docs | Notes |
|---|---|---|---|---|

## Documentation sources
| Provider | URL | HTTP | Result |
|---|---|---|---|

## Allowlist comparison
## Known-blocked ledger changes
## Findings requiring action
<or: none>
```

**Every audit produces a file, including a clean one.** A missing file is
ambiguous between "audited, all clear" and "never ran" — and those need to be
distinguishable months later.
