# Testing

## Test Frameworks and Locations

- No formal test suite exists in this repository

## How to Verify Correctness

The primary verification method is **round-trip fidelity**:

1. Start with a known-good Devchain JSON export
2. `python3 decompose.py <preset>.json`
3. `python3 compose.py <preset-directory>`
4. Compare output JSON against the original -- they should be byte-identical

```bash
# Example verification
cp teams/claude-codex-advanced.json teams/claude-codex-advanced.json.bak
python3 decompose.py teams/claude-codex-advanced.json
python3 compose.py teams/claude-codex-advanced
diff teams/claude-codex-advanced.json teams/claude-codex-advanced.json.bak
```

## Coverage / Quality Gates

- Not applicable. No automated test suite or CI pipeline.

## Test Data / Fixtures

- The three preset JSON files under `teams/` (`claude-codex-advanced.json`, `claude-codex-gemini-advanced.json`, `requirements-team.json`) serve as de facto test fixtures for round-trip verification
