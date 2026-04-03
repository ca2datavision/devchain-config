# Stack

## Languages and Versions

- **Python 3** -- tooling scripts (`decompose.py`, `compose.py`)
  - Source of truth: shebang lines (`#!/usr/bin/env python3`)
  - Standard library only; no third-party packages required

## Frameworks / Libraries

- None. Both scripts use only Python standard library modules: `json`, `re`, `shutil`, `sys`, `unicodedata`, `pathlib`

## Build Tools and Package Managers

- None. No `requirements.txt`, `pyproject.toml`, or package manager config exists
- Scripts are run directly with `python3`

## Datastores and Brokers

- Not applicable. Data is stored as JSON files and Markdown on the local filesystem

## Infrastructure as Code / Deployment Tooling

- Not applicable. This is local tooling; output JSON is manually imported into the Devchain web platform

## Observability

- Not applicable. Scripts produce stdout messages on success/error
