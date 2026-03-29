# /specs/archived/

## Purpose
Storage for superseded and processed documents. Separated by source type.

## Structure

### `/archived/intake/`
Processed raw documents from `/intake/`:
- Original raw docs that have been triaged into VRDs
- Summary/metadata markdown for local-only docs (when original cannot be committed)

### `/archived/validated/`
Superseded VRDs:
- When a newer version of a VRD is created (e.g., v2), move v1 here
- Folder location signals "archived" status - no filename rename required

## Archive Rules
- **Moving here = archived** - no need to rename files
- Original filenames are preserved
- Documents should never be deleted (audit trail)

## Summary/Metadata Record for Local-Only Documents

When archiving a document that was stored locally (in `/_local/`), create a summary markdown with these required fields:

```markdown
# Summary: [Original Filename]

## Metadata
- **Source:** [Original filename and format]
- **Date:** [When received/created]
- **Owner:** [Who provided the document]
- **Storage:** [Where original is stored - e.g., "Client SharePoint Folder X" or ticket ID]
- **Redaction Notes:** [What was removed/sanitized, if any]

## Content Summary
[Brief description of what the document contains]
```
