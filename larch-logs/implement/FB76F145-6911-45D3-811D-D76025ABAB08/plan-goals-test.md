## Goal
Emit Step 8 ledger marks before version bump so token-report.md has a Step 8 row

## Implementation Plan
## Implementation Plan

### Goal
Add `token-ledger.sh mark "Step 8 — version bump"` and `timing-ledger.sh mark "Step 8 — version bump"` calls (plus annotation comments) to `skills/implement/SKILL.md`'s Pre-bump log flush section. This creates the step anchor so the committed `token-report.md` includes a `Step 8 — version bump` row and token attribution for ship-pr.sh orchestration lands in Step 8 rather than Step 7a.

### Files to modify
- `skills/implement/SKILL.md` — Pre-bump log flush bash block: add 4 lines after `export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER` and before the `token-report.sh` call, following the exact pattern used by all other steps (0 through 7a).

### Lines to add (in order, after the export line, before token-report.sh)
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 8 — version bump" || true
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 8 — version bump" || true
# token-mark Step 8 — version bump
# timing-mark Step 8 — version bump
```

### Verification
- grep to confirm marks appear between Step 7a mark and token-report.sh call
- /relevant-checks clean

### Edge cases
- None: marks use `|| true`, fully additive, no other files affected

## Test plan
(no test plan section in plan-file)
