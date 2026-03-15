# Devchain Multi-Agent Configuration

Human-readable, versionable configuration presets for [Devchain](https://devchain.twitechlab.com/) — an AI-powered project management platform that orchestrates multiple AI agents to deliver software autonomously.

## Why Devchain

Devchain solves a problem that no other tool does well: **coordinating multiple AI agents as a real development team.** It gives each agent a role, an SOP, a communication channel, and a project board — then gets out of the way. The result is an AI team that plans, codes, reviews, and tests with minimal human intervention. The watcher/subscriber system that auto-recovers agents after context compaction is particularly brilliant — it turns fragile AI sessions into resilient autonomous workers.

## What This Repo Contains

Devchain project presets are exported as monolithic JSON files. These are powerful but hard to read, diff, or collaboratively edit. This repo provides:

1. **Decomposed configuration directories** — each JSON preset is split into human-readable files (Markdown SOPs, individual agent/profile/status JSON files)
2. **Tooling to round-trip** between the two formats
3. **Custom presets** that extend Devchain's built-in templates with additional agents and autonomy optimizations

### Presets

| Preset | Description |
|---|---|
| `claude-codex-advanced` | Original preset from [Devchain](https://devchain.twitechlab.com/). 6 agents across Claude and Codex/GPT providers. |
| `claude-codex-gemini-advanced` | Extended preset. 9 agents across 3 AI providers (Claude, Codex/GPT, Google Gemini). Optimized for autonomous operation. |

### Directory Structure (decomposed)

Each `.json` file has an associated directory with the same name:

```
claude-codex-gemini-advanced/
├── _structure.json              # Key ordering + source map (drives compose.py)
├── manifest.json                # Preset metadata (name, version, description)
├── config.json                  # Top-level settings (initial prompt, auto-clean, etc.)
├── statuses.json                # Board columns: Backlog → Draft → New → In Progress → Review → QA → Done → Blocked → Archive
├── prompts/
│   ├── 01-worker-ai-task-execution-sop-v1-0/
│   │   ├── prompt.json          # Metadata (id, title, version, tags)
│   │   └── content.md           # The actual SOP — human-readable Markdown
│   ├── 02-epic-master-sop-v1-0/
│   │   └── ...
│   └── ...                      # 11 SOPs total
├── profiles/                    # Agent runtime configs (provider, model, CLI options)
│   ├── 01-architect-planner-opus.json
│   └── ...                      # 10 profiles
├── agents/                      # Named roles pointing to profiles
│   ├── 01-brainstormer.json
│   └── ...                      # 9 agents
├── watchers/                    # Screen monitors (detect compaction, rate limits)
└── subscribers/                 # Event-driven automations (auto-recover, auto-compact)
```

## The Team (`claude-codex-gemini-advanced`)

9 agents across 3 AI providers:

| # | Agent | Provider | Role |
|---|---|---|---|
| 1 | Brainstormer | Claude | Plans and decomposes work into phases/epics/tasks. Coordinates parallel validation with SubBSM and Business Analyst. |
| 2 | Coder 1 | Claude | Implements tasks end-to-end. Runs in parallel with Coder 2. |
| 3 | Coder 2 | Claude | Second implementation agent for parallel task execution. |
| 4 | Epic Manager | Claude | Reviews delivered work, routes to QA, manages backlog, controls the full execution flow. |
| 5 | SubBSM | Codex/GPT | Technical Lead — validates plans against actual codebase before approval. |
| 6 | Code Reviewer | Codex/GPT | Audits completed phases against architectural standards. |
| 7 | Business Analyst | Gemini | Validates requirements completeness, acceptance criteria quality, and edge cases during planning. |
| 8 | Manual QA | Claude | Exploratory testing, acceptance criteria verification, UI/UX validation via Playwright. |
| 9 | Automated QA | Claude | Runs test suites, verifies builds, checks coverage, writes missing tests. |

> **Heads up:** This 9-agent configuration is designed for **large, complex projects** where the upfront cost pays off in autonomous delivery. It will consume significant tokens across all three providers and requires active subscriptions to **Claude (Anthropic), Codex/ChatGPT (OpenAI), and Gemini (Google)**. For smaller projects, consider Devchain's built-in 3-agent preset (Planner, Coder, Reviewer) which ships with the platform, or the `claude-codex-advanced` preset with 6 agents as a middle ground.

### Workflow

```
Planning:    Brainstormer ──┬── SubBSM (technical validation)
                            └── Business Analyst (requirements validation)  ── parallel
                            └── User approval

Execution:   Epic Manager assigns ──┬── Coder 1 ──┐
                                    └── Coder 2 ──┤  parallel
                                                  ▼
                                    Epic Manager reviews
                                                  ▼
                                    Automated QA ── Manual QA (if user-facing) ── Done

Code Review: Code Reviewer audits completed phases ── findings feed back as new tasks

Backlog:     When team has capacity ── Epic Manager triages ── Brainstormer plans ── cycle repeats
```

### Autonomy Features

- **Context Recovery Protocol** — every SOP includes instructions for agents to recover state after context compaction by re-reading their assigned tasks and checkpoint comments from Devchain
- **Checkpoint discipline** — agents post `STATUS:` comments at major milestones so progress survives compaction
- **Draft activation** — Epic Manager proactively picks up Draft epics instead of letting them sit idle
- **Backlog review** — when the team has capacity, Epic Manager automatically triages backlog items and sends them to Brainstormer for planning
- **Auto-compaction hooks** — watchers detect context limits and subscribers auto-recover agents with structured recovery prompts

## Tooling

### `decompose.py` — JSON to human-readable files

```bash
python3 decompose.py claude-codex-gemini-advanced.json
```

Splits a Devchain JSON preset into the directory structure above. Prompt content becomes editable Markdown files.

### `compose.py` — human-readable files back to JSON

```bash
python3 compose.py claude-codex-gemini-advanced
```

Reads the directory and produces a single JSON file ready to import into Devchain.

### Round-trip guarantee

Decomposing a JSON and composing it back produces a **byte-identical** file. Edit the decomposed files with confidence — `compose.py` will faithfully reconstruct the JSON.

## Usage

1. Edit SOPs, agents, profiles, or statuses in the decomposed directory
2. Run `python3 compose.py <directory>` to rebuild the JSON
3. Import the JSON into [Devchain](https://devchain.twitechlab.com/)

## Disclaimer

These configurations are provided **as-is**, without warranty of any kind, express or implied. The authors make no guarantees regarding the quality, correctness, completeness, or reliability of the output produced by AI agents using these presets. You are solely responsible for reviewing, validating, and supervising all AI-generated work. The authors shall not be held liable for any damages, losses, costs, or consequences — direct or indirect — arising from the use of these configurations or the code produced by AI agents operating under them. Use at your own risk and always review AI output before deploying to production.

## Credits

The original `claude-codex-advanced` preset was created using [Devchain](https://devchain.twitechlab.com/) by [Twitech Lab](https://twitechlab.com/). The extended presets and decompose/compose tooling were built on top of that foundation.

Built with Devchain. Powered by Claude, Codex, and Gemini.
