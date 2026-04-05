# /specs/validated/

## Purpose
**Gate 1 passed** VRDs (Validated Requirements Documents) - approved and ready for planning.

Only documents that have passed Business Analyst validation belong here.

## Owner
Business Analyst (validates and moves here)

## Status Lifecycle
- Only `-VALIDATED` files live here
- **Highest version is the source of truth**
- When superseded, move old version to `/archived/validated/`

## Naming Convention
```
[FeatureName]-v[N]-VALIDATED.md
```

**Examples:**
- `User-Authentication-v1-VALIDATED.md`
- `Payment-Integration-v3-VALIDATED.md`

## Traceability
When epics are created from a VRD:
1. Epic description includes: `Source: /specs/validated/[filename]`
2. VRD is updated with: `Created Epics: [epic-id-1, epic-id-2, ...]`

## What Happens Next
1. Brainstormer reads VRD from this folder
2. Brainstormer creates Phase Epic and Sub-Epics
3. Epic Manager approves for execution
4. VRD remains here as source of truth until superseded
