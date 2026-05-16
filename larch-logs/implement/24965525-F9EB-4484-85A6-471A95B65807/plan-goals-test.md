## Goal
Remove the wholesale-rejection feature so zero accepted findings on a review round no longer stalls runs

## Implementation Plan

Remove the wholesale-rejection feature entirely. Zero accepted findings on a round is the normal convergence end-state; the Re-review gate and panel-failed already cover the real failure cases.

### Files to DELETE
1. `skills/review/scripts/detect-wholesale-rejection.sh`
2. `skills/review/scripts/detect-wholesale-rejection.md`
3. `skills/review/scripts/test-detect-wholesale-rejection.sh`
4. `skills/review/scripts/test-detect-wholesale-rejection.md`

### Files to MODIFY

#### `skills/review/scripts/review-core.sh`
- Remove line: `DETECT_WHOLESALE_SH="${REVIEW_CORE_DETECT_WHOLESALE_SH:-$SCRIPT_DIR/detect-wholesale-rejection.sh}"`
- Remove lines: `wholesale_out="$REVIEW_TMPDIR/review-core-wholesale.env"` / `"$DETECT_WHOLESALE_SH" --accepted-count "$accepted_count" > "$wholesale_out"` / `terminate_early=$(kv_get "$wholesale_out" TERMINATE_EARLY)`
- Change status assignment: remove `terminate_early == "true"` branch so `accepted_count == 0` maps to `status="ok"` (convergence path)

#### `skills/review-and-fix/scripts/review-and-fix.sh`
- Change `wholesale-rejected|panel-failed)` to `panel-failed)` in the `case "$core_status"` switch

#### `skills/implement/SKILL.md` (Step 5 Exit-2 handling)
- Remove: `` `wholesale-rejected` means specialists collectively voted the change in the wrong direction; `` and the associated `For those two statuses,` → `For that status,` simplification

#### `scripts/test-review-structure.sh`
- Remove `detect-wholesale-rejection` from the `review_scripts` array
- Update the expected-count assertion from 9 to 8

#### `skills/review-and-fix/scripts/test-review-and-fix.sh`
- Remove `wholesale-rejected)` case from the review-core-stub
- Remove the wholesale test block (work_wholesale setup + assertions)

#### Documentation files
- `skills/review/SKILL.md`: remove `detect-wholesale-rejection.*` file paths from script-contracts list; remove `wholesale-rejected`/`WHOLESALE_REJECTED` mentions from wrapper loop description
- `skills/review-and-fix/scripts/review-and-fix.md`: update exit-2 description to remove "wholesale rejection"
- `skills/review-and-fix/scripts/test-review-and-fix.md`: remove "wholesale-rejection exit 2" from test coverage description
- `scripts/dispatch-code-voters.md`: remove mention of `detect-wholesale-rejection.sh`


## Test plan
After changes: `git grep -l "wholesale-rejected\|wholesale-rejection"` should return zero hits in `skills/`, `scripts/`, `docs/`, `SECURITY.md`, `agents/`, `README.md` (CHANGELOG allowed).
Run `make lint` to confirm tests pass.
