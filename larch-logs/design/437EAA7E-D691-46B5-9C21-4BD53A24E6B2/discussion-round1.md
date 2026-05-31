## Decision 1: Fix location — the guard, not pre-coder-head
- **Question**: Does the issue's Fix 1 (reset `pre-coder-head.txt` in `run-step5-review.sh`) address the bug?
- **Resolution**: No. `pre-coder-head.txt` is written as `git rev-parse HEAD` at `review-and-fix.sh:1235`, immediately before each round's coder dispatch — it already equals current HEAD (including any main-agent manual commit). `run-step5-review.sh` never writes it. The real defect is the asymmetry between `round_coder_delta_paths` (manifest builder, which excludes pre-existing untouched dirt via the `pre-coder-path-diffs` snapshot) and `round_tracked_dirty_outside_manifest` (the guard, which has no such exclusion). The fix targets the guard.
- **Source**: user + codebase

## Decision 2: Scope boundary — files in scope
- **Question**: Which files are in scope for the fix?
- **Resolution**: `skills/review-and-fix/scripts/review-and-fix.sh` (the guard `round_tracked_dirty_outside_manifest` + its call site in `apply_findings_with_coder`), `skills/review-and-fix/scripts/test-review-and-fix.sh` (regression test), `skills/review-and-fix/scripts/review-and-fix.md` (contract doc update). NOT `scripts/run-step5-review.sh`, NOT `skills/review-and-fix/scripts/review-implement-step5-loop.sh`.
- **Source**: codebase

## Decision 3: Leftover pre-existing-dirt disposition
- **Question**: How should the fixed guard treat pre-existing untouched dirt present at coder dispatch?
- **Resolution**: Exclude it from the fail-closed check, commit only the coder's delta (already the manifest behavior), and emit an `larch_err` warning breadcrumb naming each carried-over path so the anomaly is surfaced (not silently dropped). The pre-existing dirt stays uncommitted (carries into later rounds), consistent with the manifest-only staging contract.
- **Source**: user

## Decision 4: Regression test required
- **Question**: Add a hermetic regression test?
- **Resolution**: Yes. A unit test mirroring the existing `manifest-outside-guard` pattern (sed-extract the guard function), with a `pre-coder-tracked-paths.txt` + `pre-coder-path-diffs/<path>.patch` snapshot fixture, asserting the guard does NOT fire for pre-existing carryover dirt. The existing genuinely-new-dirt test must continue to fire.
- **Source**: user

## Decision 5: Backward compatibility — genuinely-new dirt still fails closed
- **Question**: Must the guard still catch genuinely-unexpected coder dirt outside its delta?
- **Resolution**: Yes. Only paths that are (a) in `pre-coder-tracked-paths.txt`, (b) have a matching `pre-coder-path-diffs` snapshot, and (c) whose current diff vs `pre-coder-head` still equals that snapshot (unchanged by the coder) are excluded. New dirt with no snapshot still fails closed (`CODER_STATUS=failed`, return `2`). The clean-tree path is byte-for-byte unchanged. The existing `manifest-outside-guard` and `manifest-outside-orchestrator` tests must keep passing.
- **Source**: codebase

## Decision 6: Non-goals
- **Question**: What is explicitly out of scope?
- **Resolution**: Issue Fix 1 (pre-coder-head reset) — moot, not implemented. Issue Fix 3 (Bash 5.x launcher `&&`→`if`) — already merged in PR #3270, not re-done. No changes to `run-step5-review.sh` or `review-implement-step5-loop.sh`. No change to clean-tree behavior. No broader refactor of the snapshot machinery beyond what the guard needs.
- **Source**: user + codebase
