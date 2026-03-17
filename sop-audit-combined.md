# SOP Suite Audit — Combined Findings (2026-03-16)

> Comprehensive audit of all 9 agent SOPs. Findings from **Brainstormer** (B) and **Code Reviewer** (CR) merged and de-duplicated. No changes proposed yet — this is the diagnostic report.

---

## CRITICAL (4 findings)

### CR-00. Code Reviewer approval message not actionable by EM (observed in production)
**Found by:** User (real-world "team idle" incident, 2026-03-17)
**Files:**
- `04-autonomous-code-reviewer/content.md:45-47` — Phase 4 defines structured verdict `{epic_id, verdict, findings_ref}` but Code Reviewer sends free-text ("Verified commit... APPROVED and QA-ready")
- `02-epic-master-sop-v1-0/content.md:280-289` — Section 6.5 expects structured `{epic_id, verdict, findings_ref}` message
**Issue:** Two compounding gaps:
1. Code Reviewer sent conversational free-text instead of the structured verdict EM expects. EM didn't recognize it as a Section 6.5 trigger → no action → team idle.
2. Code Reviewer said "QA-ready" but parent epics don't go to QA (their sub-epics already did). If this was a sub-epic review, the Code Reviewer SOP doesn't define sub-epic reviews — that's EM's job (Section 3/5). Role boundary confusion.
**Risk:** Every code review cycle can stall the entire team. Observed in production.
**Relates to:** CR-01 (API contract mismatch), LO-04 (payload inconsistency)
**Fix options:**
a) Strengthen Code Reviewer SOP Phase 4 with explicit structured message templates (not just "notify EM" — show the exact devchain_send_message call with all parameters).
b) Add EM fallback parser: if a message from Code Reviewer contains "APPROVED" or "ISSUES FOUND", treat it as Section 6.5 trigger even if not perfectly structured.
c) Clarify Code Reviewer scope: parent epics ONLY (no sub-epic reviews). After approval → Done (not QA).

### CR-01. devchain_send_message API contract mismatch across 3+ SOPs
**Found by:** Both (B-C1, CR-Critical-1)
**Files:**
- `01-worker-ai-task-execution-sop-v1-0/content.md:160` — `to="Epic Manager"` (invalid param)
- `10-manual-qa-exploratory-verification-sop-v1-0/content.md:161,169` — same
- `11-automated-qa-test-suite-verification-sop-v1-0/content.md:184,191,199,207` — same + `agentName` in update calls
- `02-epic-master-sop-v1-0/content.md:172` — update call shape may differ from actual API
**Issue:** Multiple SOPs use `devchain_send_message(to="Epic Manager", ...)` but the API has no `to` parameter. Correct shape: `devchain_send_message(sessionId=..., recipient="agents", recipientAgentNames=["Epic Manager"], message=...)`. Some `devchain_update_epic` calls also use field names that may not match the actual API.
**Risk:** Every Coder→EM and QA→EM notification could fail at runtime, breaking the entire downstream flow (parent completion checks, next assignment routing, idle detection).

### CR-02. Parallel assignment vs sequential blocking deadlock
**Found by:** CR (CR-Critical-2), partially B (B-H5)
**Files:**
- `02-epic-master-sop-v1-0/content.md:215-217` — EM assigns first two sub-epics to Coder 1 + Coder 2 simultaneously
- `01-worker-ai-task-execution-sop-v1-0/content.md:44` — "Do not work on the selected task if the previous tasks assigned onto this parent id epic are not in Done state"
**Issue:** EM explicitly assigns parallel work. Worker AI explicitly refuses to work until predecessor is Done. These directly contradict each other.
**Risk:** Coder 2 will never start because Coder 1's task isn't Done yet. Systematic deadlock on every multi-coder phase.

### CR-03. Brainstormer Backlog Epic parentId contradiction
**Found by:** B (B-C2)
**File:** `03-reviewer-architect-plan-decomposition-sop-v1-0/content.md:137-140`
**Issue:** Section 4 says "Parent: `epic_id_phase`" (line 137) AND "Create as top-level (do not set parentId)" (line 140). Direct self-contradiction.
**Risk:** Unpredictable backlog container structure. If created as sub-epic, EM's `devchain_list_epics(statusName=Backlog)` may not find it. If top-level, no structural link to phase.

---

## HIGH (10 findings)

### HI-01. `devchain_create_epic` missing from EM tools list
**Found by:** B (B-C3)
**File:** `02-epic-master-sop-v1-0/content.md:20-28`
**Issue:** Section 1 lists tools but omits `devchain_create_epic`. Section 4 (line 149) explicitly calls it.
**Risk:** EM may refuse to create backlog epics, thinking the tool is unavailable.

### HI-02. `devchain_list_documents` is not a real tool
**Found by:** Both (B-M8, CR-Critical-3)
**File:** `03-reviewer-architect-plan-decomposition-sop-v1-0/content.md:26`
**Issue:** Listed as "required tool" but doesn't exist in the DevChain toolset. Likely should be `devchain_list_prompts` or file-system reads.
**Risk:** Brainstormer SOP starts with a non-executable mandatory step.

### HI-03. EM step 2 only handles sub-epics in Review
**Found by:** B (B-H1)
**File:** `02-epic-master-sop-v1-0/content.md:69-74`
**Issue:** Step 2 says "For each Epic in In Progress → process sub-epics" but only defines one action: "If Sub-Epic in Review → run Review Process." No guidance for sub-epics in New, Draft, Blocked, or no sub-epics in Review at all.
**Risk:** EM iterates through in-progress parents, finds nothing to review, and the flow from steps 2→3→4→5 is confusing. Step 6 catches some of this but the jump is unclear.

### HI-04. Code Reviewer hardcoded review standards + branch assumptions
**Found by:** Both (B-H2, CR-High-1, CR-High-7)
**File:** `04-autonomous-code-reviewer/content.md:27,33-39`
**Issue:** Phase 3 hardcodes Controller/Service/Repo layer separation, Dependency Injection, Zod schemas. Phase 2 assumes `git diff main...HEAD`. Neither references project-specific `docs/development-standards.md`.
**Risk:** False positives for non-matching architectures. Wrong diffs if default branch isn't `main`.

### HI-05. QA context recovery checks wrong status
**Found by:** CR (CR-High-2)
**Files:**
- `10-manual-qa-exploratory-verification-sop-v1-0/content.md:49,203`
- `11-automated-qa-test-suite-verification-sop-v1-0/content.md:57,243`
**Issue:** Intake sections correctly check for tasks in `QA` status. But context recovery says "For each task in Review" — should be `QA`.
**Risk:** After compaction, QA agents miss their active work and go idle.

### HI-06. Code Reviewer team roster says "After ALL phases complete"
**Found by:** Both (B-H6, CR-High-3)
**File:** `02-epic-master-sop-v1-0/content.md:48`
**Issue:** Roster says Code Reviewer is for "After ALL phases complete." Actual flow (step 7d) dispatches per parent epic as it reaches Review.
**Risk:** EM delays code review until all phases done — massive review backlog, defeats the purpose of incremental review.

### HI-07. Brainstormer quality checklist says sub-epics should be Draft
**Found by:** Both (B-H4, CR-High-4)
**File:** `03-reviewer-architect-plan-decomposition-sop-v1-0/content.md:153,208`
**Issue:** Section 5 creates sub-epics with Status: `New`. Section 7 checklist expects `Draft`.
**Risk:** Brainstormer either creates wrong status or fails own quality check.

### HI-08. Worker AI malformed syntax in key control paths
**Found by:** Both (B-M6/M7, CR-High-5)
**File:** `01-worker-ai-task-execution-sop-v1-0/content.md:38,49,81`
**Issue:** Broken quote nesting on line 38. Unclosed markdown bold on line 81. "Reassign it back" on line 81 doesn't specify to whom.
**Risk:** LLM misinterpretation in core task intake and execution paths.

### HI-09. Backlog retry policy not deterministic across compaction
**Found by:** Both (B-L8, CR-High-6)
**File:** `02-epic-master-sop-v1-0/content.md:252`
**Issue:** "3+ consecutive loops" cannot be tracked by an LLM — no persistent counter survives compaction.
**Risk:** Either retry storms or never-retry, depending on LLM interpretation.

### HI-10. EM step 7 preamble misleading
**Found by:** B (B-H3)
**File:** `02-epic-master-sop-v1-0/content.md:84`
**Issue:** "After completing a parent epic, immediately find the next work." But step 1 jumps here when there are NO assigned tasks (first-time entry). The preamble doesn't match the "no work yet" case.
**Risk:** LLM confusion about when/why step 7 runs.

---

## MEDIUM (12 findings)

### ME-01. Stale "Architect" / "Product Owner" / "Planning Agent" references
**Found by:** Both (B-M1, CR-Medium-2)
**Files:**
- `02-epic-master-sop-v1-0/content.md:192` — "how the Architect will verify"
- `02-epic-master-sop-v1-0/content.md:332` — "most recent Architect or Product Owner decision"
- `01-worker-ai-task-execution-sop-v1-0/content.md:32,189` — "the Architect's job"
- `03-reviewer-architect-plan-decomposition-sop-v1-0/content.md:1,12` — SOP title says "Reviewer/Architect"
**Issue:** Same role called "Architect", "Planning Agent", "Brainstormer" across SOPs. "Product Owner" is not a defined agent.

### ME-02. EM mission statement vs backlog creation ambiguity
**Found by:** CR (CR-Medium-1)
**File:** `02-epic-master-sop-v1-0/content.md:14,147-154`
**Issue:** Mission says "Never create Epics based on code reviews." Section 4 says create backlog epics from review findings. The word "code reviews" is ambiguous — it could mean Code Reviewer feedback OR EM's sub-epic review.
**Risk:** EM may refuse to create valid backlog items from its own review process.

### ME-03. Hardcoded agent names and counts
**Found by:** CR (CR-Medium-3)
**File:** `02-epic-master-sop-v1-0/content.md:41-48`
**Issue:** Fixed "Coder 1", "Coder 2" names and exactly 2 coders assumed throughout.
**Risk:** Not portable to projects with different team sizes.

### ME-04. No stale task detection / agent crash recovery
**Found by:** Both (B-L2, CR-Medium-4)
**Issue:** If an agent crashes mid-task, the epic stays assigned with no timeout/recovery mechanism.
**Risk:** Tasks can be stuck indefinitely.

### ME-05. No merge/conflict handling for parallel coders
**Found by:** Both (B-L1, CR-Medium-5)
**Issue:** EM assigns parallel work to 2 Coders but no SOP mentions branching strategy, merge conflict detection, or resolution ownership.
**Risk:** Integration failures near QA/review handoff.

### ME-06. Brainstormer validation can stall indefinitely
**Found by:** CR (CR-Medium-6)
**File:** `03-reviewer-architect-plan-decomposition-sop-v1-0/content.md:71-76`
**Issue:** "Wait for BOTH responses" from SubBSM + BA with no timeout or escalation.
**Risk:** Planning blocks forever if one reviewer goes offline.

### ME-07. EM Section 6.4 Type B conditional schema ambiguity
**Found by:** CR (CR-Medium-7)
**File:** `02-epic-master-sop-v1-0/content.md:273,275`
**Issue:** Type B schema shows `source_backlog_item_ids?` (optional), but the body says it's required for `backlog_plan`.
**Risk:** Agents may omit required fields.

### ME-08. QA report templates require branch/commit without retrieval method
**Found by:** CR (CR-Medium-8)
**Files:** `10.../content.md:113`, `11.../content.md:131-132`
**Issue:** Report templates include branch/commit fields but SOPs don't explain how to discover them.
**Risk:** Fabricated or placeholder values in evidence.

### ME-09. Brainstormer header "Hard Stop" contradicts EM-originated autonomous flow
**Found by:** B (B-M9)
**File:** `03-reviewer-architect-plan-decomposition-sop-v1-0/content.md:6`
**Issue:** Header says "Continue operating only from a master plan provided by the user or after discussing and explicitly approved by the user." Section 1.5 step 5 allows EM-originated plans without user approval.

### ME-10. Section numbering gaps across SOPs
**Found by:** Both (B-M2/M3, CR-Low-1)
**Files:** Worker AI (7→10), EM (9→11), Brainstormer (8→10)
**Issue:** Non-contiguous section numbers. Makes cross-references fragile.

### ME-11. Typos affecting parsing precision
**Found by:** Both (B-M4/M5, CR-Low-2)
**Files:**
- `03.../content.md:5` — "Run Run" (doubled)
- `03.../content.md:155` — "codding" → "coding"
- `03.../content.md:227` — "projects projects"
- `02.../content.md:133` — "codding standards"
- `02.../content.md:340` — "Baklog"

### ME-12. Worker AI task dependency ordering unclear
**Found by:** B (B-H5), related to CR-Critical-2
**File:** `01-worker-ai-task-execution-sop-v1-0/content.md:44`
**Issue:** "Previous tasks" is undefined — no explicit ordering mechanism (tag number? creation order?).

---

## LOW (7 findings)

### LO-01. Code Reviewer "nothing to do" case undefined
**Found by:** B (B-L3)
**File:** `04-autonomous-code-reviewer/content.md`
**Issue:** If Phase 1 finds no `code-review-pending` epics, no instruction for what to do.

### LO-02. Automated QA→Manual QA routing doesn't explicitly preserve status
**Found by:** B (B-L4)
**File:** `11-automated-qa-test-suite-verification-sop-v1-0/content.md:184`
**Issue:** Changes `agentName` to "Manual QA" without mentioning status stays QA. Works but is implicit.

### LO-03. Manual QA has no mechanism to discover app URL
**Found by:** B (B-L5)
**File:** `10-manual-qa-exploratory-verification-sop-v1-0/content.md`
**Issue:** Assumes app is running for Playwright but doesn't explain how to find URL or start dev server.

### LO-04. Notification payload style inconsistency
**Found by:** B (B-L6)
**Issue:** EM expects structured JSON from Code Reviewer and Brainstormer, but free-text from QA/Coders. No standard envelope.

### LO-05. SubBSM response threading not specified
**Found by:** B (B-L7)
**File:** `08-code-aware-technical-lead-sop-v1-0/content.md:87`
**Issue:** "Respond directly to the requesting agent" but doesn't mention using `threadId` for reply context.

### LO-06. Initialize Agent lacks fallback on profile not found
**Found by:** CR (CR-Low-3)
**File:** `05-initialize-agent/content.md:4`
**Issue:** Mandatory first action with no recovery path if `devchain_get_agent_by_name` fails or returns no match.

### LO-07. Brainstormer `devchain_list_documents` unknown tool
**Found by:** Both (duplicate of HI-02, included here for tracking)
**Note:** Already captured as HI-02. Removing from count.

---

## Summary

| Severity | Count | Breakdown |
|----------|-------|-----------|
| Critical | 3 | API mismatch, parallel deadlock, parentId contradiction |
| High | 10 | Missing tool, stale tool ref, flow gaps, syntax errors, non-deterministic retry |
| Medium | 12 | Stale names, ambiguity, no crash recovery, no git strategy, schema issues |
| Low | 6 | Undefined edge cases, implicit behaviors, missing context |
| **Total** | **31** | |

## Overlap Analysis

| Finding | Brainstormer | Code Reviewer |
|---------|:---:|:---:|
| API contract mismatch | yes | yes |
| Parallel vs sequential deadlock | partial | yes |
| Backlog parentId contradiction | yes | — |
| Missing devchain_create_epic | yes | — |
| Stale devchain_list_documents | yes | yes |
| EM step 2 only handles Review | yes | — |
| Code Reviewer hardcoded standards | yes | yes |
| QA context recovery wrong status | — | yes |
| Code Reviewer "ALL phases" trigger | yes | yes |
| Sub-epic Draft vs New | yes | yes |
| Worker AI syntax errors | yes | yes |
| Backlog retry non-deterministic | yes | yes |
| EM step 7 preamble | yes | — |
| Stale terminology | yes | yes |
| Mission statement ambiguity | — | yes |
| Hardcoded agent names | — | yes |
| Stale task recovery | yes | yes |
| Git/merge conflicts | yes | yes |
| Brainstormer validation stall | — | yes |
| Type B schema ambiguity | — | yes |
| QA report metadata | — | yes |
| Brainstormer Hard Stop contradiction | yes | — |
| Section numbering | yes | yes |
| Typos | yes | yes |

**13 findings** identified by both independently — high confidence these are real issues.
**8 findings** unique to Brainstormer.
**10 findings** unique to Code Reviewer.

---

## Suggested Priority Order for Remediation

1. **CR-01** (API mismatch) — affects runtime, easy to fix
2. **CR-02** (parallel deadlock) — affects runtime, design decision needed
3. **CR-03** (parentId contradiction) — affects runtime, pick one approach
4. **HI-01 + HI-02** (tool list corrections) — quick fixes
5. **HI-05** (QA context recovery) — quick fix, high impact
6. **HI-06** (Code Reviewer trigger wording) — quick fix
7. **HI-07** (Draft vs New) — quick fix
8. **HI-04** (Code Reviewer standards) — moderate effort
9. **HI-08** (Worker syntax) — quick fix
10. **HI-03 + HI-10** (EM flow clarity) — moderate rewrite
11. **ME-01 through ME-12** — batch copy-edit pass
12. **LO-01 through LO-06** — hardening pass
