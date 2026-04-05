# /specs/intake/

## Purpose
Raw, unprocessed client materials awaiting Business Analyst triage.

## Owner
- **Deposit:** User (or client)
- **Triage:** Business Analyst

## Naming Convention
```
YYYY-MM-DD-[Source]-[OriginalName].[ext]
```

**Examples:**
- `2026-03-29-ClientEmail-FeatureRequest.pdf`
- `2026-03-29-Meeting-UIWireframes.zip`
- `2026-03-29-Slack-RequirementsUpdate.docx`

## Non-Text Files (Binary Formats)
For non-text files (PDF, DOCX, images, ZIP, etc.), create a **sidecar summary**:
```
[basename].summary.md
```

**Example:**
- `2026-03-29-Meeting-UIWireframes.zip`
- `2026-03-29-Meeting-UIWireframes.summary.md` (describes contents)

## Confidentiality Rules

**Sensitive documents must go in `/_local/` subfolder:**
- Documents containing PII (names, addresses, SSN, etc.)
- Contracts and legal agreements
- Credentials, API keys, passwords
- Confidential business data

**Only sanitized/redacted versions may be committed to the repository.**

## What Happens Next
1. BA reviews documents in this folder
2. BA consolidates into a VRD (Validated Requirements Document) in `/wip/`
3. Once validated, VRD moves to `/validated/`
4. Original intake docs are archived to `/archived/intake/` (or summary for local-only)
