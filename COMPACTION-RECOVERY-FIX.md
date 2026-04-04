# Compaction Recovery Fix - All Team Templates

**Date:** 2026-04-03
**Priority:** High
**Impact:** Agent identity loss after context compaction across all projects using these templates

---

## Problem Summary

The compaction recovery mechanism is **broken** across all team templates. Agents lose their identity and SOP instructions after context compaction because:

1. **Invalid event name**: Templates use `watcher.conversation.compact_requestnotified` which **does not exist** in the Devchain codebase
2. **Missing Codex coverage**: No watcher for Codex compaction detection
3. **Missing Claude hook-based recovery**: The more reliable Claude-native hook mechanism is not configured

---

## Affected Templates

| Template | Current Status |
|----------|---------------|
| `claude-codex-advanced` | Broken - uses non-existent event |
| `claude-codex-gemini-advanced` | Broken - uses non-existent event |
| `requirements-team` | Uses `watcher.conversation.compacted` - needs verification |

---

## Required Changes

### 1. Fix Watcher: `watchers/01-compacted-ctrl-o-to-see-full-summary.json`

**Applies to:** `claude-codex-advanced`, `claude-codex-gemini-advanced`

**Current (broken):**
```json
{
  "name": "Compacted (ctrl+o to see full summary)",
  "enabled": false,
  "eventName": "watcher.conversation.compact_requestnotified"
}
```

**Fixed:**
```json
{
  "id": "3a3f251d-8d3d-4171-9b9c-50369394777d",
  "name": "Claude Compacted",
  "description": "Detects when Claude completes context compaction",
  "enabled": true,
  "scope": "provider",
  "scopeFilterName": "claude",
  "pollIntervalMs": 5000,
  "viewportLines": 30,
  "condition": {
    "type": "regex",
    "pattern": "(?:Compacted \\(ctrl\\+o|Auto-compact: Compacting conversation)"
  },
  "cooldownMs": 60000,
  "cooldownMode": "time",
  "eventName": "watcher.claude.compacted"
}
```

**Key changes:**
- `enabled`: `false` → `true`
- `eventName`: `compact_requestnotified` → `watcher.claude.compacted`
- `pollIntervalMs`: `60000` → `5000` (faster detection)
- `condition.pattern`: Updated to match actual Claude compaction messages
- `condition.type`: `contains` → `regex` (more flexible)

---

### 2. Fix Subscriber: `subscribers/01-compacted.json`

**Applies to:** `claude-codex-advanced`, `claude-codex-gemini-advanced`

**Current (broken):**
```json
{
  "eventName": "watcher.conversation.compact_requestnotified"
}
```

**Fixed:**
```json
{
  "id": "1e580c53-650c-41f7-ba49-0833a7788c25",
  "name": "Compacted - Recovery Message",
  "description": "Sends recovery instructions after context compaction",
  "enabled": true,
  "eventName": "watcher.claude.compacted",
  "eventFilter": null,
  "actionType": "send_agent_message",
  "actionInputs": {
    "text": {
      "source": "custom",
      "customValue": "Your agent session id (sessionId): {{sessionIdShort}}\nYour agent name: {{agentName}}\n! Important: Re-load your agent profile by using devchain_get_agent_by_name to refresh SOP instructions and continue working !\n\n[CONTEXT RECOVERY] Your conversation was compacted. Follow your SOP's Context Recovery Protocol:\n1. Re-load your agent profile: devchain_get_agent_by_name(name='{{agentName}}')\n2. Check your assigned tasks: devchain_list_assigned_epics_tasks(agentName='{{agentName}}')\n3. For each in-progress task, read the full epic and ALL comments to recover context\n4. Resume work from your last checkpoint comment"
    },
    "submitKey": {
      "source": "custom",
      "customValue": "Enter"
    },
    "immediate": {
      "source": "custom",
      "customValue": "true"
    }
  },
  "delayMs": 3000,
  "cooldownMs": 60000,
  "retryOnError": false,
  "groupName": null,
  "position": 0,
  "priority": 10
}
```

**Key changes:**
- `eventName`: Match the watcher's new event name
- `delayMs`: `0` → `3000` (wait for compaction to fully complete)
- `cooldownMs`: `5000` → `60000` (prevent spam)
- `priority`: `0` → `10` (higher priority than other subscribers)

---

### 3. NEW: Add Codex Compaction Watcher

**Create file:** `watchers/04-codex-compacted.json`

**Applies to:** `claude-codex-advanced`, `claude-codex-gemini-advanced`

```json
{
  "id": "codex-compacted-watcher",
  "name": "Codex Compacted",
  "description": "Detects when Codex completes context compaction",
  "enabled": true,
  "scope": "provider",
  "scopeFilterName": "codex",
  "pollIntervalMs": 5000,
  "viewportLines": 30,
  "condition": {
    "type": "contains",
    "pattern": "Context compacted"
  },
  "cooldownMs": 60000,
  "cooldownMode": "time",
  "eventName": "watcher.codex.context_compacted"
}
```

---

### 4. NEW: Add Codex Recovery Subscriber

**Create file:** `subscribers/06-codex-compacted-recovery.json`

**Applies to:** `claude-codex-advanced`, `claude-codex-gemini-advanced`

```json
{
  "id": "codex-compacted-recovery",
  "name": "Codex Compacted - Recovery Message",
  "description": "Sends recovery instructions after Codex context compaction",
  "enabled": true,
  "eventName": "watcher.codex.context_compacted",
  "eventFilter": null,
  "actionType": "send_agent_message",
  "actionInputs": {
    "text": {
      "source": "custom",
      "customValue": "Your agent session id (sessionId): {{sessionIdShort}}\nYour agent name: {{agentName}}\n! Important: Re-load your agent profile by using devchain_get_agent_by_name to refresh SOP instructions and continue working !\n\n[CONTEXT RECOVERY] Your conversation was compacted. Follow your SOP's Context Recovery Protocol:\n1. Re-load your agent profile: devchain_get_agent_by_name(name='{{agentName}}')\n2. Check your assigned tasks: devchain_list_assigned_epics_tasks(agentName='{{agentName}}')\n3. For each in-progress task, read the full epic and ALL comments to recover context\n4. Resume work from your last checkpoint comment"
    },
    "submitKey": {
      "source": "custom",
      "customValue": "Enter"
    },
    "immediate": {
      "source": "custom",
      "customValue": "true"
    }
  },
  "delayMs": 3000,
  "cooldownMs": 60000,
  "retryOnError": false,
  "groupName": null,
  "position": 0,
  "priority": 10
}
```

---

### 5. NEW: Add Claude Hook-Based Recovery (Most Reliable)

**Create file:** `subscribers/07-claude-hook-recovery.json`

**Applies to:** All teams with Claude provider

This uses Claude's native hook system which is more reliable than viewport-based detection.

```json
{
  "id": "claude-hook-recovery",
  "name": "Claude Hook - Session Recovery",
  "description": "Uses Claude native hooks to detect resume/clear/compact and send recovery instructions",
  "enabled": true,
  "eventName": "claude.hooks.session.started",
  "eventFilter": {
    "field": "source",
    "operator": "regex",
    "value": "resume|clear|compact"
  },
  "actionType": "send_agent_message",
  "actionInputs": {
    "text": {
      "source": "custom",
      "customValue": "Your agent session id (sessionId): {{sessionIdShort}}\nYour agent name: {{agentName}}\n! Important: Re-load your agent profile by using devchain_get_agent_by_name to refresh SOP instructions and continue working !"
    },
    "submitKey": {
      "source": "custom",
      "customValue": "Enter"
    },
    "immediate": {
      "source": "custom",
      "customValue": "false"
    }
  },
  "delayMs": 3000,
  "cooldownMs": 2000,
  "retryOnError": false,
  "groupName": null,
  "position": 0,
  "priority": 5
}
```

**Why this is important:**
- Claude Code fires a `SessionStart` hook with `source: "compact"` when compaction completes
- This is more reliable than viewport pattern matching
- Also handles `resume` and `clear` events (session resume, context clear)

---

### 6. Update `requirements-team` Template

The requirements-team uses `watcher.conversation.compacted` which may or may not work. Apply the same fixes:

1. Verify the watcher pattern matches actual compaction output
2. Add the Claude hook-based recovery subscriber
3. Add Codex compaction watcher if Codex is used

---

## Gemini Note

Gemini CLI **does not support compaction** yet (confirmed in Devchain codebase: `gemini-json.parser.ts:439`). No action needed for Gemini-specific compaction handling.

---

## Testing Checklist

After applying fixes, test each scenario:

- [ ] Claude manual `/compact` command triggers recovery message
- [ ] Claude auto-compact (at threshold) triggers recovery message
- [ ] Claude session resume triggers recovery message
- [ ] Codex compaction triggers recovery message
- [ ] Recovery message includes correct `{{agentName}}` and `{{sessionIdShort}}`
- [ ] Agent successfully reloads SOP after receiving recovery message

---

## Files Summary

### Modify:
- `*/watchers/01-compacted-ctrl-o-to-see-full-summary.json` - Fix event name, enable, update pattern
- `*/subscribers/01-compacted.json` - Fix event name

### Create:
- `*/watchers/04-codex-compacted.json` - Codex compaction detection
- `*/subscribers/06-codex-compacted-recovery.json` - Codex recovery message
- `*/subscribers/07-claude-hook-recovery.json` - Claude hook-based recovery

---

## Related

- Devchain seeder `0005_seed_renew_instructions_subscriber` creates hook-based subscriber per project
- SOPs already have "Context Recovery Protocol" sections - infrastructure just needs to trigger them
