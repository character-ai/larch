## Goal
Upgrade actions/cache@v4 to actions/cache@v5 in .github/workflows/ci.yaml to fix Node 20 deprecation warnings in CI

## Implementation Plan

Goal: Fix Node.js 20 deprecation warnings in CI by upgrading the explicit `actions/cache@v4` at `.github/workflows/ci.yaml:198` to `actions/cache@v5`.

Files to modify: `.github/workflows/ci.yaml`

Changes:
1. Line 198: `uses: actions/cache@v4` → `uses: actions/cache@v5` (ripgrep binary cache step in `test-harnesses` job)
2. The comment at lines 23-24 references `actions/cache@v4 carried inside actions/setup-node` — this is the transitive dependency used internally by actions/setup-node, not our direct usage. Leave the comment unchanged since it remains accurate.

Verification: Run /relevant-checks (pre-commit + agent-lint). The Node 20 deprecation warning will only disappear in CI, not locally.

## Test plan
(no test plan section in plan-file)
