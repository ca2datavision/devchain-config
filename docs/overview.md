# Overview

## Purpose and Scope

This repository contains decomposed, human-readable configuration presets for Devchain. Devchain exports project configurations as monolithic JSON files; this repo splits them into editable Markdown SOPs, individual agent/profile JSON files, and provides round-trip tooling to recompose them.

## High-Level Capabilities

- **Decompose** a Devchain JSON preset into a directory of small, reviewable files
- **Compose** edited files back into a single JSON for Devchain import
- **Version-control** agent SOPs, profiles, statuses, and watchers with standard Git workflows
- **Customize** multi-agent team configurations (agents, prompts, profiles, watchers, subscribers)

## Primary Entry Points

- `decompose.py` -- CLI: splits a JSON preset into a directory structure
- `compose.py` -- CLI: reassembles a directory back into a single JSON file

## Project Shape

Standalone utility repository (not a service or library). Two Python scripts operate on JSON/Markdown configuration files. No runtime, no server, no database.

## Key Directories and Their Roles

| Directory | Purpose |
|---|---|
| `teams/` | All team preset directories and their composed JSON files |
| `teams/claude-codex-advanced/` | Decomposed 6-agent Development Team preset (Claude + Codex/GPT) |
| `teams/claude-codex-gemini-advanced/` | Decomposed 9-agent Development Team preset (Claude + Codex/GPT + Gemini) |
| `teams/requirements-team/` | Decomposed 3-agent Requirements Team preset (Claude + Codex + Gemini) — produces validated VRDs consumed by the Dev Team |
| `specs-flow-template/` | Template for the specs pipeline directory structure (`/specs/intake/` → `/specs/validated/`) and VRD template |
| `teams/*/prompts/` | SOP Markdown files and metadata per agent role |
| `teams/*/profiles/` | Agent runtime configs (provider, model, CLI options) |
| `teams/*/agents/` | Named agent roles pointing to profiles |
| `teams/*/watchers/` | Screen monitors (detect compaction, rate limits) |
| `teams/*/subscribers/` | Event-driven automations (auto-recover, auto-compact) |
| `drafts/` | Draft content (LinkedIn posts, etc.) |
