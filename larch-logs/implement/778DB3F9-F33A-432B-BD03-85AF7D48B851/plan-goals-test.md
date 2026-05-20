## Goal
Remove Codex from review panel (HARD and SIMPLE), raise dynamic archetype cap from 4 to 8

## Implementation Plan

Goal: Remove Codex static reviewer slots from both HARD and SIMPLE review panels; raise dynamic archetype cap from 4 to 8. Keep all Codex invocation machinery intact.

### Files to modify

**1. skills/review/scripts/dispatch-panel.sh**
- Update usage string: `[--dynamic-archetypes 0-4]` → `[--dynamic-archetypes 0-8]`
- Update cap validation case: `[0-4]` → change to accept 0-8 (using `[0-8]` in a case statement doesn't match two-digit numbers; use explicit match or regex)
  - Actually the case pattern `[0-4]` only matches single-character 0-4. Need `[0-9]` with a range check or explicitly: 0|1|2|3|4|5|6|7|8 — use `[0-8]` won't work for shell globs since `[0-8]` matches a single char 0-8; but 8 is still single digit so `[0-8]` works.
  - Change `[0-4])` → `[0-8])`
  - Change error message from "from 0 to 4" to "from 0 to 8"
- Comment at line 110-111: Update panel descriptions
- Remove Codex slot queuing (lines 122-131): remove the `if [[ "$PANEL" == "hard" ]]` Codex specialist block and the `else` Codex generalist block
- Update static_codex accounting (lines 411-419): always set to 0, remove hard/simple branch
- Update breadcrumb (lines 422-427): remove Codex specialist/generalist mention

**2. skills/review/scripts/review-core.sh**
- Update usage string: `[--dynamic-archetypes 0-4]` → `[--dynamic-archetypes 0-8]`
- Update cap validation case: `[0-4]` → `[0-8]`
- Update error message from "from 0 to 4" to "from 0 to 8"

**3. skills/review-and-fix/scripts/review-and-fix.sh**
- Update cap validation case: `[0-4]` → `[0-8]`
- Update error message from "from 0 to 4" to "from 0 to 8"

**4. skills/review/scripts/test-dispatch-panel.sh**
- Line 476: `for bad in 5 -1 abc` → `for bad in 9 -1 abc` (5-8 are now valid)

**5. skills/review/scripts/dispatch-panel.md**
- Update panel shape descriptions: Simple panel no longer has Codex generalist; Hard panel no longer has Codex specialists
- Update dynamic archetypes range from 0..4 to 0..8

**6. skills/review/SKILL.md**
- Update `--dynamic-archetypes must be 0..4` → `must be 0..8`

**7. skills/review/references/heavy-worker.md**
- Update `0..4` → `0..8` for dynamic archetypes

**8. skills/implement/SKILL.md**
- `--dynamic-archetypes <N>`: must be 0–4 → 0–8
- Step 0 caller inheritance: `[0-4])` → `[0-8])` and error message update
- Step 5 breadcrumb text: remove "Codex generalist on round 1 only" from simple panel description
- Step 5 normal breadcrumb: remove "6 Codex specialists" from hard panel description
- Comment at step 5 `<!-- step:5 ... (dynamic-archetypes cap=4) -->` → cap=8

**9. skills/shared/topology.tsv**
- Row `implement.review_and_fix.panel_hard`: update from "6 Cursor specialists + 6 Codex specialists" to "6 Cursor specialists only"

**10. docs/topology.md** (regenerate via `bash scripts/generate-topology-docs.sh`)

**11. scripts/test-quick-mode-docs-sync.sh**
- Remove "Codex generalist|sensitive" from POS_MARKERS (since generalist is no longer in the simple panel)

**12. README.md**, **docs/review-agents.md**, **docs/workflow-lifecycle.md**, **docs/skills.md**
- Remove "Codex generalist on round 1 only" references from simple panel descriptions


## Test plan
- `make lint-bash32` after script edits
- `bash skills/review/scripts/test-dispatch-panel.sh` to verify panel dispatch
- `bash scripts/test-quick-mode-docs-sync.sh` to verify docs sync
- Run `/relevant-checks` after all changes
