## Goal
Extend test-implement-timing-rehydration.sh Invariant B fence matcher to cover indented fenced blocks in SKILL.md

## Implementation Plan

Fix `scripts/test-implement-timing-rehydration.sh` Invariant B to match indented fenced bash blocks.

### Files to modify

1. **`scripts/test-implement-timing-rehydration.sh`**:
   - Line 40: change awk pattern `/^```bash$/` to `/^[[:space:]]*```bash$/`
   - Line 43: change awk pattern `/^```$/` to `/^[[:space:]]*```$/`
   - Update header comment line 8 to say "fenced ```bash block" covers both indented and column-1 variants

2. **`scripts/test-implement-timing-rehydration.md`**:
   - Update Invariant 2 description to mention that indented bash fences are covered by the adjacency check

### No other changes
- `skills/implement/SKILL.md`: no changes needed. The only indented bash fence with a timing call (line 201) already contains `export LARCH_TIMING_LEDGER="$IMPLEMENT_TMPDIR/timing-ledger.tsv"` (the Step 0 carve-out), so it will pass the updated matcher.


## Test plan
- Run `bash scripts/test-implement-timing-rehydration.sh` — must still PASS
- The awk change broadens the pattern so all previously-matched column-1 fences still match; only new coverage is indented variants
