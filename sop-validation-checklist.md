# SOP Flow Validation Checklist (2026-03-17)

> **Purpose:** Systematic validation of the entire multi-agent workflow after applying audit fixes.
> Run each scenario mentally or in production and verify every checkpoint passes.
> Mark each checkpoint `[x]` when verified.

---

## Legend

- **Agent abbreviations:** EM = Epic Manager, CR = Code Reviewer, BSM = Brainstormer, SubBSM = Code-Aware Technical Lead, BA = Business Analyst, C1/C2 = Coder 1/Coder 2, AQA = Automated QA, MQA = Manual QA
- **Status abbreviations:** BL = Backlog, DR = Draft, NW = New, IP = In Progress, RV = Review, QA = QA, DN = Done, BK = Blocked, AR = Archive
- **Severity:** Each scenario tagged `[CRITICAL]`, `[HIGH]`, `[MEDIUM]`, `[LOW]` based on production impact if it fails

---

## SECTION 1: HAPPY PATH — End-to-End Lifecycle

### S1.1 — New Project: User → Plan → Phase → Tasks → Code → QA → Code Review → Done `[CRITICAL]`

**Precondition:** User provides a feature request to Brainstormer. No existing epics.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | User | Provides feature request to BSM | — | [ ] BSM receives request |
| 2 | BSM | Runs Section 11 (Documentation validation) | docs/ created if new project | [ ] docs/development-standards.md exists |
| 3 | BSM | Runs Section 1.4 (Pre-Draft Verification) | — | [ ] BSM reads actual codebase files, not assumptions |
| 4 | BSM | Drafts Master Plan | — | [ ] Plan has verified facts and file:line references |
| 5 | BSM | Sends Draft Plan to SubBSM AND BA in parallel | Messages sent | [ ] Both SubBSM and BA receive the plan simultaneously |
| 6 | BSM | HARD STOP — waits for both responses | — | [ ] BSM does NOT present plan to user yet |
| 7 | SubBSM | Returns technical feedback | — | [ ] Feedback uses Section 1/2/3 format |
| 8 | BA | Returns requirements feedback | — | [ ] Feedback covers acceptance criteria + edge cases |
| 9 | BSM | Incorporates feedback, may re-send for round 2 | — | [ ] Max 10 validation rounds |
| 10 | BSM | Presents final plan to USER for approval | — | [ ] Only final validated plan, no intermediate drafts |
| 11 | User | Approves plan | — | [ ] BSM proceeds to epic creation |
| 12 | BSM | Creates Phase Epic | Phase epic: DR | [ ] Title: `Phase N: <outcome>`, Tags: `Phase, Phase:1`, agentName empty |
| 13 | BSM | Creates Backlog Epic | Backlog epic: BL | [ ] Title: `BACKLOG: Phase N: ...`, Tags: `Backlog, Phase:1, phaseId:<phaseEpicId>`, top-level (no parentId) |
| 14 | BSM | Creates Sub-Epics under Phase Epic | Sub-epics: NW | [ ] Each has `parentId=phaseEpicId`, Tags: `Phase:1, Task:N`, agentName empty |
| 15 | BSM | Each sub-epic follows template | — | [ ] Has: Title, TODO WORK DETAILS, Context, File References, Prereads (incl development-standards.md), DoD, Notes |
| 16 | BSM | Runs Quality Checklist (Section 7) | — | [ ] All items pass |
| 17 | BSM | Calls ExitPlanMode | — | [ ] BSM does NOT start implementing |
| 18 | EM | Step 7c: finds DR phase epic | — | [ ] EM picks it up in Draft scan |
| 19 | EM | Draft Activation (Section 2.1) | Phase: NW→IP | [ ] Phase moved to In Progress, EM assigns self |
| 20 | EM | Assigns first sub-epic to C1 | Sub-epic 1: agentName=C1 | [ ] C1 gets assignment |
| 21 | EM | Assigns second sub-epic to C2 | Sub-epic 2: agentName=C2 | [ ] C2 gets assignment (parallel work) |
| 22 | C1 | Checks dependencies (Task:1 has none) | Sub-epic 1: IP | [ ] C1 starts work |
| 23 | C1 | Implements task, posts evidence comment | — | [ ] Comment has ✅ WORK COMPLETED sections |
| 24 | C1 | Moves to Review | Sub-epic 1: RV, agentName=EM | [ ] Status=Review, reassigned to parent's agentName |
| 25 | EM | Reviews sub-epic 1 evidence | — | [ ] Reads evidence against TODO WORK DETAILS |
| 26 | EM | Approves → routes to QA | Sub-epic 1: QA, agentName=AQA | [ ] Posts STATUS: IMPLEMENTATION APPROVED |
| 27 | EM | Immediately assigns next sub-epic to C1 | Sub-epic 3: agentName=C1 | [ ] Does NOT wait for QA result |
| 28 | AQA | Runs test suite | — | [ ] Build, tests, lint, typecheck, coverage all run |
| 29 | AQA | APPROVED + user-facing → routes to MQA | Sub-epic 1: agentName=MQA (status stays QA) | [ ] Status stays QA, only agentName changes |
| 30 | MQA | Runs acceptance criteria + exploratory tests | — | [ ] Uses Playwright for UI validation |
| 31 | MQA | APPROVED → marks Done | Sub-epic 1: DN | [ ] Notifies EM |
| 32 | EM | Checks parent completion | — | [ ] Not all sub-epics Done yet → continues |
| 33 | ... | Repeat for all sub-epics | All sub-epics: DN | [ ] Every sub-epic goes through full cycle |
| 34 | EM | All sub-epics Done → parent to Review | Phase epic: RV | [ ] Parent moves to Review |
| 35 | EM | Step 7d: dispatches Code Review | Tag: `code-review-pending` added | [ ] Tag added BEFORE sending message to CR |
| 36 | EM | Continues to step 7e (does NOT wait) | — | [ ] EM proceeds to check Backlog |
| 37 | CR | Phase 1: finds epic with `code-review-pending` tag | — | [ ] Filters correctly |
| 38 | CR | Phase 2-3: analyzes code, reviews against standards | — | [ ] References docs/development-standards.md |
| 39 | CR | Phase 4: APPROVED | — | [ ] Sends structured JSON: `{epic_id, verdict: "APPROVED", findings_ref: null}` |
| 40 | EM | Section 6.5: receives verdict | — | [ ] Recognizes structured message |
| 41 | EM | Removes `code-review-pending` tag | Tag removed | [ ] Tag removed via `removeTags` |
| 42 | EM | Moves parent to Done | Phase epic: DN | [ ] Terminal state, never reopened |

---

### S1.2 — Non-User-Facing Task: Skip Manual QA `[HIGH]`

**Precondition:** Sub-epic is pure backend/refactoring (not user-facing).

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | AQA | Determines task is non-user-facing | — | [ ] Checks task description + parent epic |
| 2 | AQA | APPROVED → marks Done directly | Sub-epic: DN | [ ] Does NOT route to MQA |
| 3 | AQA | Notifies EM | Message sent | [ ] Uses correct devchain_send_message API |

---

### S1.3 — EM-Originated Backlog Plan (No User Involvement) `[HIGH]`

**Precondition:** EM finds Backlog items in step 7e. No user interaction needed.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | EM | Step 7e: finds Backlog items without `planning-requested` tag | — | [ ] Skips items already tagged |
| 2 | EM | Tags items `planning-requested` | Tags added | [ ] Uses `addTags` API |
| 3 | EM | Sends grouped items to BSM | Message sent | [ ] Message includes item list + "do not wait for user input" |
| 4 | BSM | Drafts plan, runs SubBSM + BA validation | — | [ ] Full validation loop runs |
| 5 | BSM | Sends plan to EM (not user) | Message sent | [ ] Format: `{message_type: "plan_for_approval", plan_type: "backlog_plan", source_backlog_item_ids: [...]}` |
| 6 | EM | Section 6.4 Type A: reviews plan | — | [ ] EM recognizes message_type |
| 7 | EM | Approves plan | Reply sent | [ ] "Plan approved. Proceed." |
| 8 | BSM | Creates Phase + Sub-Epics | Epics created | [ ] Status: Phase=DR, Sub-Epics=NW |
| 9 | BSM | Sends creation confirmation to EM | Message sent | [ ] Format: `{message_type: "creation_confirmation", plan_type: "backlog_plan", source_backlog_item_ids: [...], created_epic_ids: [...]}` |
| 10 | EM | Section 6.4 Type B: archives source backlog items | Source items: AR | [ ] Only archives items in `source_backlog_item_ids` |
| 11 | EM | Step 7c: picks up new DR phase epic | — | [ ] Continues normal flow |

---

## SECTION 2: CODE REVIEW SCENARIOS

### S2.1 — Code Review: Issues Found → Remediation → Re-Review `[CRITICAL]`

**Precondition:** CR finds critical architecture violations in completed phase.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | CR | Phase 4: ISSUES FOUND | — | [ ] Sends structured JSON to EM: `{epic_id, verdict: "ISSUES FOUND", findings_ref: "..."}` |
| 2 | CR | Synthesizes remediation plan | — | [ ] Uses output template format |
| 3 | CR | Sends plan to BSM | Message sent | [ ] Includes: "Tag all remediation epics with `remediates:<epic_id>`. Do NOT wait for User approval." |
| 4 | EM | Section 6.5: receives ISSUES FOUND verdict | — | [ ] Removes `code-review-pending` tag |
| 5 | EM | Moves parent to Blocked | Phase epic: BK | [ ] NOT left in Review (prevents re-dispatch loop) |
| 6 | BSM | Creates remediation parent epic | New epic: DR | [ ] Title: `Code Review Remediation N: <Phase Name>`, Tag: `remediates:<originalParentEpicId>` |
| 7 | BSM | Creates remediation sub-epics | Sub-epics: NW | [ ] Under new remediation parent, NOT original phase |
| 8 | BSM | Sends confirmation to EM | Message sent | [ ] Format: `{message_type: "creation_confirmation", plan_type: "remediation_plan", created_epic_ids: [...]}` |
| 9 | EM | Section 6.4 Type B: receives confirmation | — | [ ] Does NOT archive anything (remediation_plan, not backlog_plan) |
| 10 | EM | Step 7c: picks up remediation DR epic | Remediation epic: IP | [ ] Normal Draft→New→IP flow |
| 11 | ... | Coders implement remediation tasks | Sub-epics: DN | [ ] Normal implementation cycle |
| 12 | EM | All remediation sub-epics Done | Remediation parent: RV | [ ] Moves to Review |
| 13 | EM | Section 6.6: detects `remediates:<parentId>` tag | — | [ ] Identifies this as remediation completion |
| 14 | EM | Original parent: BK→RV | Original phase epic: RV | [ ] Unblocked for re-review |
| 15 | EM | Step 7d: re-dispatches code review | Tag: `code-review-pending` re-added | [ ] CR reviews the original phase again |
| 16 | CR | Re-reviews (including remediation changes) | — | [ ] Checks both original + remediation code |
| 17 | CR | APPROVED | — | [ ] Sends structured verdict |
| 18 | EM | Section 6.5: APPROVED | Original phase: DN | [ ] Both remediation + original phase reach Done |

---

### S2.2 — Code Review Dispatch Idempotency `[CRITICAL]`

**Precondition:** EM loops through step 7 multiple times while CR is still reviewing.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | EM | Step 7d: finds phase in Review | — | [ ] Checks tags |
| 2 | EM | Phase already has `code-review-pending` tag | — | [ ] EM skips dispatch |
| 3 | EM | Continues to step 7e | — | [ ] Does NOT send duplicate message to CR |
| 4 | EM | Next loop: same phase still in Review with tag | — | [ ] Still skips — no infinite loop |

---

### S2.3 — Code Review: Free-Text Message Handling `[CRITICAL]`

**Precondition:** CR sends approval in non-structured format (the CR-00 production incident).

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | CR | Sends: "Verified commit abc123 — APPROVED and QA-ready" | — | [ ] CR SOP MUST enforce structured format |
| 2 | EM | Receives message | — | [ ] EM MUST be able to parse verdict from message |
| 3 | — | — | — | [ ] **Fix validation:** CR SOP explicitly states JSON format is mandatory, with example |
| 4 | — | — | — | [ ] **Fix validation:** EM has fallback parsing for common free-text patterns (optional defense-in-depth) |

---

### S2.4 — Multiple Phases in Review Simultaneously `[HIGH]`

**Precondition:** Two phases complete around the same time. Both in Review.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | EM | Step 7d: finds Phase 1 in Review (no tag) | — | [ ] Dispatches review for Phase 1 |
| 2 | EM | Step 7d: finds Phase 2 in Review (no tag) | — | [ ] Dispatches review for Phase 2 in same loop |
| 3 | CR | Receives both review requests | — | [ ] CR processes them sequentially or identifies both |
| 4 | CR | Sends verdict for Phase 1 | — | [ ] EM handles Phase 1 verdict |
| 5 | CR | Sends verdict for Phase 2 | — | [ ] EM handles Phase 2 verdict independently |
| 6 | — | — | — | [ ] No cross-contamination between reviews |

---

## SECTION 3: TASK ASSIGNMENT & PARALLEL WORK

### S3.1 — Two Coders Working in Parallel `[CRITICAL]`

**Precondition:** Phase has 4 sub-epics (Task:1 through Task:4). C1 and C2 available.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | EM | Assigns Task:1 to C1 | Task:1 agentName=C1 | [ ] C1 starts work |
| 2 | EM | Assigns Task:2 to C2 | Task:2 agentName=C2 | [ ] C2 starts work |
| 3 | C2 | Checks dependencies for Task:2 | — | [ ] **CRITICAL:** Task:2 must NOT be blocked by Task:1 unless explicitly dependent |
| 4 | C1 | Completes Task:1 → Review | Task:1: RV | [ ] EM assigns Task:3 to C1 |
| 5 | C2 | Completes Task:2 → Review | Task:2: RV | [ ] EM assigns Task:4 to C2 |
| 6 | — | — | — | [ ] No deadlock: C2 was not waiting for C1's Task:1 to be Done |

**Dependency rule validation:**
- [ ] Worker AI SOP clarifies: "previous tasks" = only tasks explicitly listed as dependencies, NOT all tasks with lower Task:N numbers
- [ ] OR: EM only assigns independent tasks in parallel and sequential tasks one at a time

---

### S3.2 — Coder Availability Notification `[HIGH]`

**Precondition:** C1 finishes all assigned tasks and becomes idle.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | C1 | Completes last assigned task → Review | — | [ ] Moves to Review |
| 2 | C1 | Sends availability message to EM | Message sent | [ ] Uses correct API: `recipient="agents", recipientAgentNames=["Epic Manager"]` |
| 3 | EM | Section 6.2: receives availability | — | [ ] Recognizes the message |
| 4 | EM | Finds next unassigned NW sub-epic | — | [ ] Assigns to C1 |
| 5 | — | — | — | [ ] C1 does NOT go idle |

---

### S3.3 — All Tasks Assigned, Coder Becomes Available `[MEDIUM]`

**Precondition:** All sub-epics in current phase are assigned or completed. C1 finishes.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | C1 | Sends availability message | Message sent | [ ] EM receives |
| 2 | EM | No unassigned NW sub-epics in current phase | — | [ ] EM checks other phases |
| 3 | EM | If other phases have work → assigns from there | — | [ ] Cross-phase assignment works |
| 4 | EM | If no work anywhere → C1 waits | — | [ ] EM does NOT terminate, keeps looping |

---

### S3.4 — Coder Reports Task Blocked `[HIGH]`

**Precondition:** C1 encounters a blocker during implementation.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | C1 | Posts blocker in comment | — | [ ] Comment explains blocker clearly |
| 2 | C1 | Moves task to Blocked | Task: BK | [ ] Updates status |
| 3 | C1 | Notifies EM | Message sent | [ ] Includes task ID + blocker reason |
| 4 | EM | Validates blocker | — | [ ] Creates CONCERN in backlog if needed |
| 5 | EM | Assigns C1 to another task | — | [ ] C1 does NOT go idle |
| 6 | — | — | — | [ ] Blocked task counted when checking parent completion (prevents premature parent→Review) |

---

## SECTION 4: QA FLOW SCENARIOS

### S4.1 — Automated QA Fails → Coder Rework → Re-QA `[HIGH]`

**Precondition:** AQA finds test failures in sub-epic.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | AQA | Runs tests → failures found | — | [ ] Full error output captured |
| 2 | AQA | Posts QA report with NEEDS FIXES | — | [ ] Report includes all failures + analysis |
| 3 | AQA | Reassigns to original Coder | Task: IP, agentName=C1 | [ ] Correctly identifies original Coder from comments |
| 4 | AQA | Notifies EM | Message sent | [ ] EM knows task needs rework |
| 5 | C1 | Fixes issues, re-submits | Task: RV | [ ] New evidence comment posted |
| 6 | EM | Re-reviews, approves | Task: QA, agentName=AQA | [ ] Second QA cycle starts |
| 7 | AQA | Re-runs tests → all pass | — | [ ] Routes appropriately (MQA or Done) |

---

### S4.2 — Manual QA Fails → Coder Rework `[HIGH]`

**Precondition:** MQA finds acceptance criteria failures.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | MQA | Tests acceptance criteria → FAIL | — | [ ] Clear reproduction steps documented |
| 2 | MQA | Posts QA report with NEEDS FIXES | — | [ ] Includes screenshots if UI issue |
| 3 | MQA | Reassigns to original Coder | Task: IP, agentName=C1 | [ ] Correctly identifies Coder |
| 4 | MQA | Notifies EM | Message sent | [ ] Uses correct API |
| 5 | — | — | — | [ ] Task goes through full cycle again: C1→RV→EM→QA→AQA→MQA |

---

### S4.3 — AQA Build Failure (Immediate Block) `[MEDIUM]`

**Precondition:** `npm run build` fails during AQA.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | AQA | Build fails | — | [ ] AQA stops immediately (does not run tests) |
| 2 | AQA | Reports blocking build failure | — | [ ] Full error output included |
| 3 | AQA | Reassigns to Coder | Task: IP | [ ] Coder gets build errors to fix |

---

## SECTION 5: BACKLOG & PLANNING SCENARIOS

### S5.1 — Backlog Triage Deduplication `[HIGH]`

**Precondition:** EM loops step 7e twice. Same backlog items exist.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | EM | First loop: finds 3 Backlog items | — | [ ] None have `planning-requested` tag |
| 2 | EM | Tags all 3 with `planning-requested` | Tags added | [ ] Uses `addTags` API |
| 3 | EM | Sends to BSM | Message sent | [ ] Items grouped and described |
| 4 | EM | Second loop: same 3 items still in BL status | — | [ ] All have `planning-requested` tag |
| 5 | EM | Skips all 3 | — | [ ] No duplicate message to BSM |

---

### S5.2 — Backlog Item Already Done (Exact Duplicate) `[MEDIUM]`

**Precondition:** Backlog item describes work that's already completed in another epic.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | EM | Step 7e: triages backlog item | — | [ ] Recognizes exact same work already Done |
| 2 | EM | Discards (archives) the duplicate | Item: AR | [ ] Only when work is EXACTLY the same |
| 3 | — | — | — | [ ] Does NOT discard similar-but-different work |

---

### S5.3 — Stale `planning-requested` Tag Recovery `[MEDIUM]`

**Precondition:** BSM crashed after receiving backlog items. Tag exists but no plan was created.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | EM | Step 7e: finds BL item with `planning-requested` tag | — | [ ] Tag exists |
| 2 | EM | Checks tag age / time since added | — | [ ] If tag added > N hours/days ago |
| 3 | EM | Re-sends to BSM | Message re-sent | [ ] Stale detection works |
| 4 | — | — | — | [ ] Counter-based detection ("3+ loops") is NOT used (not trackable across compaction) |

---

### S5.4 — Brainstormer Validation Timeout `[MEDIUM]`

**Precondition:** BSM sends plan to SubBSM and BA. BA never responds.

| Step | Actor | Action | Expected State Change | Checkpoint |
|------|-------|--------|----------------------|------------|
| 1 | BSM | Sends plan to SubBSM + BA | Messages sent | [ ] Both receive |
| 2 | SubBSM | Responds with feedback | — | [ ] BSM receives SubBSM feedback |
| 3 | BA | Never responds (crashed/offline) | — | [ ] BSM is stuck at HARD STOP |
| 4 | — | — | — | [ ] **Fix needed:** Timeout/escalation mechanism defined |
| 5 | — | — | — | [ ] BSM can escalate to user or EM after N hours |

---

## SECTION 6: STATE TRANSITION INTEGRITY

### S6.1 — Done is Terminal `[CRITICAL]`

| Check | Checkpoint |
|-------|------------|
| No SOP instruction moves a Done epic to any other status | [ ] Verified in EM SOP |
| No SOP instruction moves a Done epic to any other status | [ ] Verified in CR SOP |
| No SOP instruction moves a Done epic to any other status | [ ] Verified in BSM SOP |
| No SOP instruction moves a Done epic to any other status | [ ] Verified in Worker AI SOP |
| No SOP instruction moves a Done epic to any other status | [ ] Verified in AQA SOP |
| No SOP instruction moves a Done epic to any other status | [ ] Verified in MQA SOP |

---

### S6.2 — Valid State Transitions Matrix `[CRITICAL]`

Every status transition in all SOPs must match this allowed matrix:

| From | To | Allowed? | Who triggers | SOP reference |
|------|----|----------|--------------|---------------|
| Backlog | Draft | Yes | EM (triage) | EM Step 7e |
| Backlog | Archive | Yes | EM (duplicate/obsolete) | EM Step 7e |
| Draft | New | Yes | EM (Draft Activation) | EM Section 2.1 |
| Draft | In Progress | Yes | EM (shortcut) | EM Step 7c |
| New | In Progress | Yes | Coder (starts work) | Worker AI |
| In Progress | Review | Yes | Coder (submits) | Worker AI |
| In Progress | Blocked | Yes | Coder (blocker) | Worker AI |
| Review | QA | Yes | EM (approves) | EM Section 5 |
| Review | In Progress | Yes | EM (revision) | EM Scenario B |
| Review | Done | Yes | EM (parent, after CR) | EM Section 6.5 |
| Review | Blocked | Yes | EM (remediation needed) | EM Section 6.5 |
| QA | Done | Yes | AQA/MQA (approved) | AQA/MQA SOP |
| QA | In Progress | Yes | AQA/MQA (needs fixes) | AQA/MQA SOP |
| Blocked | Review | Yes | EM (remediation done) | EM Section 6.6 |
| Blocked | In Progress | Yes | EM (blocker resolved) | EM |
| Done | (any) | **NO** | — | Terminal |
| Archive | (any) | **NO** | — | Terminal |

**Checkpoint:** [ ] Every `devchain_update_epic(statusName=...)` call in every SOP follows this matrix.

---

### S6.3 — Parent Epic Status Depends on Sub-Epics `[HIGH]`

| Condition | Expected Parent Status | Checkpoint |
|-----------|----------------------|------------|
| Any sub-epic in IP, RV, QA, or BK | Parent stays IP | [ ] EM does not move parent to Review |
| All sub-epics in DN or AR | Parent moves to RV | [ ] EM triggers parent Review |
| Sub-epics in NW or DR remain | EM assigns them first | [ ] Does not skip unstarted work |
| Parent in RV + CR approved | Parent → DN | [ ] Terminal |
| Parent in RV + CR issues found | Parent → BK | [ ] Awaits remediation |

---

## SECTION 7: MESSAGE CONTRACT VALIDATION

### S7.1 — devchain_send_message API Shape `[CRITICAL]`

Every `devchain_send_message` call in every SOP must use this shape:

```
devchain_send_message(
  sessionId=<sessionId>,
  recipientAgentNames=["<Agent Name>"],
  message="..."
)
```

Use `recipient="user"` only for direct messages to the user. Do NOT use `recipient="agents"` or `to="Agent Name"`.

**NOT:** `devchain_send_message(to="Agent Name", message="...")`

| SOP | Correct API used? | Checkpoint |
|-----|-------------------|------------|
| Worker AI (Coder) | | [ ] All calls verified |
| Epic Manager | | [ ] All calls verified |
| Brainstormer | | [ ] All calls verified |
| Code Reviewer | | [ ] All calls verified |
| Automated QA | | [ ] All calls verified |
| Manual QA | | [ ] All calls verified |
| SubBSM | | [ ] All calls verified |
| Business Analyst | | [ ] All calls verified |

---

### S7.2 — Code Reviewer → EM Verdict Format `[CRITICAL]`

CR MUST send structured message. EM MUST parse it.

**Required format:**
```json
{
  "epic_id": "<id>",
  "verdict": "APPROVED" | "ISSUES FOUND",
  "findings_ref": null | "<summary>"
}
```

| Check | Checkpoint |
|-------|------------|
| CR SOP explicitly shows this JSON format | [ ] |
| CR SOP says "use EXACTLY this format" or equivalent | [ ] |
| CR SOP does NOT allow free-text verdicts | [ ] |
| EM Section 6.5 handler parses this format | [ ] |
| EM has no fallback parsing (strict = good, forces compliance) | [ ] |

---

### S7.3 — Brainstormer → EM Plan Messages `[HIGH]`

**Type A: Plan for Approval**
```json
{
  "message_type": "plan_for_approval",
  "plan_type": "backlog_plan",
  "source_backlog_item_ids": ["<id1>", "<id2>"],
  "plan_content": "<plan>"
}
```

**Type B: Creation Confirmation**
```json
{
  "message_type": "creation_confirmation",
  "plan_type": "backlog_plan" | "remediation_plan",
  "source_backlog_item_ids": ["<id1>"],  // only for backlog_plan
  "created_epic_ids": ["<id1>", "<id2>"]
}
```

| Check | Checkpoint |
|-------|------------|
| BSM SOP shows both message formats | [ ] |
| EM Section 6.4 handles both Type A and Type B | [ ] |
| EM only archives backlog items for `plan_type: "backlog_plan"` | [ ] |
| EM does NOT archive for `plan_type: "remediation_plan"` | [ ] |

---

### S7.4 — QA → EM Notification `[HIGH]`

| Check | Checkpoint |
|-------|------------|
| AQA notifies EM after every finalization (APPROVED or NEEDS FIXES) | [ ] |
| MQA notifies EM after every finalization | [ ] |
| Notification includes task_id and verdict | [ ] |
| Uses correct API shape (not `to="Epic Manager"`) | [ ] |

---

## SECTION 8: TAG LIFECYCLE VALIDATION

### S8.1 — `code-review-pending` Tag `[CRITICAL]`

| Phase | Actor | Action | Checkpoint |
|-------|-------|--------|------------|
| Creation | EM | Adds tag when dispatching CR (step 7d) | [ ] `addTags: ["code-review-pending"]` |
| Guard | EM | Checks tag before dispatching (prevents double-dispatch) | [ ] Skips if tag exists |
| Removal | EM | Removes tag when receiving CR verdict (Section 6.5) | [ ] `removeTags: ["code-review-pending"]` |
| Re-add | EM | Re-adds tag when re-dispatching after remediation (Section 6.6→7d) | [ ] Fresh tag for re-review |

**Invariant:** At any point in time, an epic has `code-review-pending` if and only if a code review is actively in progress.

---

### S8.2 — `planning-requested` Tag `[HIGH]`

| Phase | Actor | Action | Checkpoint |
|-------|-------|--------|------------|
| Creation | EM | Adds tag to BL items sent to BSM (step 7e) | [ ] `addTags: ["planning-requested"]` |
| Guard | EM | Skips BL items with this tag (prevents duplicate planning) | [ ] |
| Cleanup | EM | Archives BL item when plan confirmed (Section 6.4 Type B) | [ ] Tag becomes moot (item archived) |
| Stale detection | EM | Re-sends if tag is old and no plan received | [ ] Time-based, not counter-based |

---

### S8.3 — `remediates:<parentId>` Tag `[HIGH]`

| Phase | Actor | Action | Checkpoint |
|-------|-------|--------|------------|
| Creation | BSM | Tags remediation parent epic | [ ] Format: `remediates:<originalParentEpicId>` |
| Detection | EM | Section 6.6: finds tag on completed remediation epic | [ ] Extracts parentId from tag |
| Action | EM | Unblocks original parent (BK→RV) | [ ] Original parent returns to Review for re-review |

---

## SECTION 9: CONTEXT RECOVERY (POST-COMPACTION)

### S9.1 — EM Context Recovery `[CRITICAL]`

**Precondition:** EM's context is compacted mid-workflow.

| Step | Action | Checkpoint |
|------|--------|------------|
| 1 | Re-reads full EM SOP | [ ] All rules refreshed |
| 2 | Calls `devchain_list_assigned_epics_tasks(agentName=...)` | [ ] Knows current assignments |
| 3 | For each epic: reads ALL comments | [ ] Reconstructs checkpoint from STATUS comments |
| 4 | Checks sub-epic statuses | [ ] Knows which sub-epics are where |
| 5 | Resumes from last checkpoint | [ ] Does NOT re-send messages already sent |
| 6 | Does NOT re-dispatch code reviews already dispatched | [ ] Checks `code-review-pending` tag |

---

### S9.2 — Coder Context Recovery `[HIGH]`

| Step | Action | Checkpoint |
|------|--------|------------|
| 1 | Re-reads Worker AI SOP | [ ] |
| 2 | Calls `devchain_list_assigned_epics_tasks(agentName=...)` | [ ] Finds assigned tasks |
| 3 | For each task: reads ALL comments | [ ] Finds last STATUS checkpoint |
| 4 | Resumes implementation from checkpoint | [ ] Does NOT restart from scratch |

---

### S9.3 — CR Context Recovery `[HIGH]`

| Step | Action | Checkpoint |
|------|--------|------------|
| 1 | Re-reads CR SOP | [ ] |
| 2 | Calls `devchain_list_epics(statusName="Review")` + filters `code-review-pending` | [ ] Finds pending reviews |
| 3 | For each epic: reads ALL comments | [ ] Knows what phase of review |
| 4 | Does NOT re-send reviews already delivered to BSM | [ ] Checks comment history |

---

### S9.4 — BSM Context Recovery `[HIGH]`

| Step | Action | Checkpoint |
|------|--------|------------|
| 1 | Re-reads BSM SOP | [ ] |
| 2 | Calls `devchain_list_assigned_epics_tasks(agentName=...)` | [ ] Finds planning epics |
| 3 | Reads ALL epic comments | [ ] Finds validation stage (SubBSM? BA? Approval?) |
| 4 | Checks for pending messages from SubBSM + BA | [ ] Feedback may have arrived during compaction |
| 5 | Does NOT re-send validation requests if feedback already received | [ ] |

---

### S9.5 — QA Context Recovery `[MEDIUM]`

| Step | Action | Checkpoint |
|------|--------|------------|
| 1 | Re-reads QA SOP | [ ] |
| 2 | Calls `devchain_list_assigned_epics_tasks(agentName=...)` | [ ] |
| 3 | Checks for tasks in **QA** status (not Review!) | [ ] SOP must say QA, not Review |
| 4 | Reads all comments to find test progress | [ ] |

---

## SECTION 10: EDGE CASES & ERROR SCENARIOS

### S10.1 — Agent Crash Mid-Task (Stale Assignment) `[MEDIUM]`

**Precondition:** C1 crashes while working on a task. Task stays IP with agentName=C1.

| Check | Checkpoint |
|-------|------------|
| EM has a mechanism to detect stale tasks | [ ] Time-based detection defined |
| EM can reassign stale tasks to another Coder | [ ] Reassignment procedure defined |
| OR: stale detection is explicitly deferred (documented as known gap) | [ ] |

---

### S10.2 — EM Receives Unknown Message Type `[MEDIUM]`

**Precondition:** Agent sends message EM doesn't recognize.

| Check | Checkpoint |
|-------|------------|
| EM has fallback handling for unrecognized messages | [ ] Logs/comments and continues |
| EM does NOT crash or halt on unknown message | [ ] |
| EM does NOT silently ignore (leading to team idle) | [ ] |

---

### S10.3 — Circular Remediation (Issues Found on Remediation) `[HIGH]`

**Precondition:** CR reviews remediation code and finds MORE issues.

| Step | Actor | Action | Checkpoint |
|------|-------|--------|------------|
| 1 | CR | Reviews remediation epic → ISSUES FOUND | [ ] Sends new remediation plan |
| 2 | BSM | Creates new remediation epic (Remediation 2) | [ ] New epic, not appended to first |
| 3 | EM | Original parent stays BK | [ ] Only unblocked when ALL remediation passes |
| 4 | — | — | [ ] System converges (no infinite remediation loop) |
| 5 | — | — | [ ] **Optional:** Max remediation depth defined |

---

### S10.4 — No Work Anywhere (System Idle) `[MEDIUM]`

**Precondition:** All phases Done. No Backlog. No Draft. No New. Nothing in progress.

| Step | Actor | Action | Checkpoint |
|------|-------|--------|------------|
| 1 | EM | Step 7a-7e: all return empty | — |
| 2 | EM | Step 7f: waits for incoming messages | — |
| 3 | — | — | [ ] EM does NOT terminate |
| 4 | — | — | [ ] EM does NOT declare "all done" |
| 5 | — | — | [ ] EM waits for new user requests or backlog items |

---

### S10.5 — Sub-Epic Already Implemented by Another Task `[MEDIUM]`

**Precondition:** C1 discovers Task:3 was already handled by Task:2's implementation.

| Step | Actor | Action | Checkpoint |
|------|-------|--------|------------|
| 1 | C1 | Recognizes work already done | — |
| 2 | C1 | Posts comment explaining overlap | — |
| 3 | C1 | Reassigns back to parent epic owner | [ ] Specifies: agentName = parent epic's agentName |
| 4 | EM | Reviews overlap claim | [ ] Validates and moves to Done or reassigns differently |

---

### S10.6 — Two Coders on Same Files (Merge Conflict) `[LOW]`

**Precondition:** C1 and C2 both modify the same file.

| Check | Checkpoint |
|-------|------------|
| Git branching strategy defined | [ ] Each task gets own branch |
| OR: tasks are decomposed to avoid file overlap | [ ] BSM avoids co-editing same files |
| OR: known gap documented with conflict resolution procedure | [ ] |

---

### S10.7 — devchain_update_epic API: tags vs addTags/removeTags `[CRITICAL]`

**Precondition:** All tag operations must use `addTags`/`removeTags`, not raw `tags` field.

| SOP | Uses addTags/removeTags correctly? | Checkpoint |
|-----|-----------------------------------|------------|
| Epic Manager | | [ ] All tag ops verified |
| Code Reviewer | | [ ] (if any tag ops) |
| Brainstormer | | [ ] (epic creation tags are different — those use `tags` on create) |

---

## SECTION 11: CROSS-SOP CONSISTENCY

### S11.1 — Terminology Consistency `[MEDIUM]`

| Term | Should be | Check in all SOPs |
|------|-----------|------------------|
| Planner role | "Brainstormer" | [ ] No "Architect", "Planning Agent", "Planner" references |
| Epic Manager role | "Epic Manager" | [ ] Consistent naming |
| Code review agent | "Code Reviewer" | [ ] No "Review Agent" etc. |
| "Product Owner" | Should not appear (undefined role) | [ ] Not referenced |

---

### S11.2 — Section Numbering `[LOW]`

| SOP | Sequential numbering? | Checkpoint |
|-----|----------------------|------------|
| EM SOP | No gaps (no jump 9→11) | [ ] |
| Worker AI SOP | No gaps (no jump 7→10) | [ ] |
| BSM SOP | No gaps | [ ] |
| CR SOP | N/A (uses Phases) | [ ] |

---

### S11.3 — Tool Lists Match Usage `[HIGH]`

| SOP | All tools listed that are used? | All listed tools exist? | Checkpoint |
|-----|-------------------------------|------------------------|------------|
| EM | `devchain_create_epic` listed? | | [ ] |
| BSM | `devchain_list_documents` → should be `devchain_list_prompts`? | | [ ] |
| CR | Tool list matches Phase 1-4 usage? | | [ ] |

---

### S11.4 — Status Names Match Canonical List `[MEDIUM]`

Canonical: `Backlog`, `Draft`, `New`, `In Progress`, `Review`, `QA`, `Done`, `Blocked`, `Archive`

| Check | Checkpoint |
|-------|------------|
| No SOP uses non-canonical status names | [ ] |
| Case matches exactly (e.g., "In Progress" not "IN PROGRESS") | [ ] |
| Exception: BACKLOG is sometimes used as `BACKLOG` — verify API accepts both cases | [ ] |

---

## SECTION 12: PERFORMANCE & LIVENESS

### S12.1 — EM Never Idles `[CRITICAL]`

| Scenario | EM behavior | Checkpoint |
|----------|------------|------------|
| All work in progress | Monitors, reviews incoming | [ ] Loops step 2→7 |
| No assigned work | Hunts step 7a→7f | [ ] Finds next work |
| All steps empty | Waits for messages (step 7f) | [ ] Does NOT terminate |
| CR reviewing (slow) | EM continues other work (step 7e+) | [ ] Does NOT wait for CR |
| BSM planning (slow) | EM continues other work | [ ] Does NOT wait for BSM |

---

### S12.2 — No Agent Goes Idle Without Reason `[HIGH]`

| Agent | Idle only when... | Checkpoint |
|-------|------------------|------------|
| EM | Step 7f: literally nothing to do | [ ] |
| C1/C2 | All tasks assigned to them are blocked + EM notified | [ ] |
| CR | No `code-review-pending` epics exist | [ ] |
| AQA | No tasks in QA assigned to AQA | [ ] |
| MQA | No tasks in QA assigned to MQA | [ ] |
| BSM | No planning requests pending | [ ] |
| SubBSM | No validation requests pending | [ ] |
| BA | No validation requests pending | [ ] |

---

### S12.3 — Work Priority Order `[HIGH]`

EM's step 7 must check in this exact order:

| Priority | What | Why | Checkpoint |
|----------|------|-----|------------|
| 1st | In Progress (7a) | Active work first | [ ] |
| 2nd | New (7b) | Ready-to-start work | [ ] |
| 3rd | Draft (7c) | Needs activation | [ ] |
| 4th | Review (7d) | Code review dispatch | [ ] |
| 5th | Backlog (7e) | Future work planning | [ ] |
| Last | Wait (7f) | Nothing to do | [ ] |

---

## SUMMARY

| Section | Scenarios | Critical | High | Medium | Low |
|---------|-----------|----------|------|--------|-----|
| 1. Happy Path | 3 | 1 | 2 | 0 | 0 |
| 2. Code Review | 4 | 3 | 1 | 0 | 0 |
| 3. Task Assignment | 4 | 1 | 2 | 1 | 0 |
| 4. QA Flow | 3 | 0 | 2 | 1 | 0 |
| 5. Backlog & Planning | 4 | 0 | 1 | 3 | 0 |
| 6. State Transitions | 3 | 2 | 1 | 0 | 0 |
| 7. Message Contracts | 4 | 2 | 2 | 0 | 0 |
| 8. Tag Lifecycle | 3 | 1 | 2 | 0 | 0 |
| 9. Context Recovery | 5 | 1 | 3 | 1 | 0 |
| 10. Edge Cases | 7 | 1 | 1 | 4 | 1 |
| 11. Cross-SOP | 4 | 0 | 1 | 2 | 1 |
| 12. Performance | 3 | 1 | 2 | 0 | 0 |
| **Total** | **47** | **13** | **20** | **12** | **2** |

---

> **Next step:** After fixing audit findings, run through each scenario and mark checkpoints. Any unchecked box = remaining gap.
