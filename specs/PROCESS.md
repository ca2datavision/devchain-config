# Specs Flow Process

> **Version:** 1.0
> **Last Updated:** 2026-07-10
> **Purpose:** Define the requirements intake and validation pipeline for all DevChain projects.

---

## Pipeline Overview

```
Client Docs → /specs/intake/ → BA Triage → /specs/wip/ → /specs/validated/ → Brainstormer → Epics → EM Approval → Execution
```

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────────────┐
│  Client Docs    │────▶│   /intake/   │────▶│    /wip/     │────▶│  /validated/   │
│  (raw input)    │     │  (untriaged) │     │   (drafts)   │     │ (Gate 1 pass)  │
└─────────────────┘     └──────────────┘     └──────────────┘     └────────────────┘
                              │                                          │
                              ▼                                          ▼
                        ┌──────────────┐                          ┌────────────────┐
                        │  /archived/  │                          │  Brainstormer  │
                        │   /intake/   │                          │   (planning)   │
                        └──────────────┘                          └────────────────┘
                                                                         │
                                                                         ▼
                                                                  ┌────────────────┐
                                                                  │  Draft Epics   │
                                                                  │  (execution)   │
                                                                  └────────────────┘
```

---

## Directory Structure

| Directory | Purpose | Owner |
|-----------|---------|-------|
| `/specs/intake/` | Raw, unprocessed client materials | User deposits / BA triages |
| `/specs/intake/_local/` | Sensitive docs (gitignored) | User deposits / BA triages |
| `/specs/wip/` | Draft VRDs in progress | Business Analyst |
| `/specs/validated/` | Gate 1 passed VRDs | Business Analyst |
| `/specs/archived/intake/` | Processed raw docs or summaries | Business Analyst |
| `/specs/archived/validated/` | Superseded VRDs | Business Analyst |

---

## Naming Conventions

### Intake Documents
```
YYYY-MM-DD-[Source]-[OriginalName].[ext]
```
**Examples:**
- `2026-03-29-ClientEmail-FeatureRequest.pdf`
- `2026-03-29-Meeting-UIWireframes.zip`

### Sidecar Summaries (for non-text files)
```
[basename].summary.md
```
**Required for:** PDF, DOCX, images, ZIP, and all binary formats.

### VRDs (Validated Requirements Documents)
```
[FeatureName]-v[N]-[STATUS].md
```
- `v[N]` = single integer version (v1, v2, v3...)
- `[STATUS]` = DRAFT | VALIDATED | ARCHIVED

**Examples:**
- `User-Authentication-v1-DRAFT.md`
- `Payment-Integration-v2-VALIDATED.md`

---

## Status Definitions

| Status | Location | Meaning |
|--------|----------|---------|
| INTAKE | `/intake/` | Raw document, not yet processed |
| DRAFT | `/wip/` | VRD in progress, not ready for planning |
| VALIDATED | `/validated/` | Gate 1 passed, ready for epic creation |
| ARCHIVED | `/archived/` | Superseded or processed |

### Status Lifecycle
- **Source of truth:** Highest version with `-VALIDATED` in `/validated/`
- When superseded: move old version to `/archived/validated/` (no rename needed)

---

## Confidentiality Guidance

### What Can Be Committed
- Sanitized/redacted documents
- Summaries and metadata records
- Public or internal-only materials

### What CANNOT Be Committed
Store in `/intake/_local/` (gitignored):
- Documents containing PII
- Contracts and legal agreements
- Credentials, API keys, passwords
- Confidential business data

### Local-Only Document Archival
When archiving a local-only document, create a summary/metadata markdown with:

| Field | Description |
|-------|-------------|
| **Source** | Original filename and format |
| **Date** | When received/created |
| **Owner** | Who provided the document |
| **Storage** | Where original is stored (SharePoint, ticket ID, etc.) |
| **Redaction Notes** | What was removed/sanitized |
| **Content Summary** | Brief description of contents |

---

## Three-Gate Review Process

### Gate 1: Intake Triage (Business Analyst)

**Trigger:** New documents appear in `/intake/`

**Process:**
1. **Initial Review:** Understand scope, identify source, check conflicts
2. **Consolidation:** Combine related documents into single VRD in `/wip/`
3. **Gap Analysis:** Identify ambiguities, missing edge cases, untestable criteria
4. **Validation:** Move complete VRD to `/validated/`, archive raw to `/archived/intake/`

**Output:** Validated Requirements Document (VRD) in `/specs/validated/`

### Gate 2: Plan Approval (Epic Manager)

**Trigger:** Brainstormer presents decomposed epics

**Process:**
1. Review epic structure and acceptance criteria
2. Verify proper scope and testability
3. Approve or request revisions

**Output:** Approved epics ready for Coder assignment

### Gate 3: Outcome Conformance (Outcome Conformance Reviewer)

**Scope:** applies only to projects created from the claude-codex-gemini-advanced (10-agent) preset. Only that preset ships the `Conformance` status and the Outcome Conformance Reviewer agent — projects on other presets end the epic lifecycle at Gate 2 plus code review.

**Trigger:** All child tasks of an epic are `Done` and code review has approved the epic (status `Conformance`)

**Process:**
1. Follow the epic's `Source:` link to the VRD; reconstruct the intended outcome and its principles
2. Compare the built epic against them, holistically — not per-task
3. Classify drift (implementation / specification / scope) and post a distilled Conformance Report

**Output:**
- CONFORMS → epic closes (`Done`)
- CONFORMS WITH NOTES → epic closes, YELLOWs logged for Epic Manager follow-up
- DOES NOT CONFORM → build fix (implementation drift) or stakeholder decision (specification drift / ambiguity)

This closes the backward-traceability loop: the `Source:` link on every epic is finally *read* at the end of the line.

---

## Manual Handoff Definitions

| Step | Actor | Action | Output |
|------|-------|--------|--------|
| 1 | User | Deposits documents | Docs in `/intake/` |
| 2 | BA | Triages and creates VRD | VRD in `/wip/` then `/validated/` |
| 3 | BA | Archives raw docs | Docs in `/archived/intake/` |
| 4 | Brainstormer | Creates epics from VRD | Draft epics in DevChain |
| 5 | Brainstormer | Adds epic IDs to VRD | VRD updated with traceability |
| 6 | EM | Approves epics | Epics ready for execution |
| 7 | Outcome Conformance Reviewer | Verifies completed epic against source VRD | Conformance verdict; epic closed or routed for fix/decision |

---

## Traceability Requirements

### Epic → VRD (Forward Link)
Every epic description must include:
```
Source: /specs/validated/[FeatureName]-v[N]-VALIDATED.md
```

### VRD → Epic (Backward Link)
Every VRD must be updated with created epics:
```
## Created Epics
| Epic ID | Title | Status |
|---------|-------|--------|
| abc123 | Phase 1: User Auth | In Progress |
```

---

## Project Initialization

### Phase 0: Project Initialization

Every new DevChain project starts with this structure. To bootstrap:

1. Copy `/app/specs-flow-template/` to `./specs/` in the project
2. Change directory permissions to 755 (rwxr-xr-x) for all directories under ./specs/
3. Change file permissions to 644 (rw-r--r--) for all files under ./specs/
4. Configure any project-specific paths in this PROCESS.md
5. Verify directory structure exists

**Responsibility:**
- Epic Manager checks for `/specs/` before first epic
- Business Analyst verifies infrastructure before first triage
- Brainstormer checks Phase 0 completion before creating Phase 1

---

## Quick Reference

```
/specs/
├── intake/              # Raw client docs
│   ├── _local/          # Sensitive (gitignored)
│   │   └── .gitignore
│   └── README.md
├── wip/                 # Draft VRDs
│   └── README.md
├── validated/           # Gate 1 passed VRDs
│   ├── _TEMPLATE-VRD.md
│   └── README.md
├── archived/
│   ├── intake/          # Processed raw docs
│   ├── validated/       # Superseded VRDs
│   └── README.md
└── PROCESS.md           # This file
```
