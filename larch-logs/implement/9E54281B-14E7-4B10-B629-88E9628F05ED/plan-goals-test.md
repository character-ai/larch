## Goal
Implement issue #3593: [IMPLEMENTING] [BUG] (URGENT) LARCH_QUIET_* session env leaks into harness subprocesses\n\n**Surface**: `scripts/run-relevant-checks-captured.sh` → `scripts/relevant-checks.sh` → pre-commit/make → `test-*.sh` harnesses, when invoked from inside a larch skill session..

## Implementation Plan
**Surface**: `scripts/run-relevant-checks-captured.sh` → `scripts/relevant-checks.sh` → pre-commit/make → `test-*.sh` harnesses, when invoked from inside a larch skill session.

Skill sessions export `LARCH_QUIET_DISABLE` / `LARCH_QUIET_ACTIVE` / `LARCH_QUIET_PID` / `LARCH_QUIET_LOG_FILE`, and the checks pipeline performs no scrub (zero `LARCH_QUIET` references in `run-relevant-checks-captured.sh`, `lint-fix-loop.sh`, or `relevant-checks.sh`), so harnesses asserting `scripts/lib-quiet.sh` behavior inherit foreign quiet state and fail in-session while passing in a clean shell and in CI.

**Incident evidence** (run `3876DC27-D694-4C99-B942-61A52A2554D7`): `scripts/test-launch-claude-subprocess.sh` failed `quiet log not created despite LARCH_QUIET_LOG_FILE being set` only under the Step 5 wrapper environment — inherited `LARCH_QUIET_DISABLE=1` made the subject skip quiet-log creation. The in-session failure fed the lint-fix attempt-cap stall loop. PR #3585 fixed that one harness with an `unset LARCH_QUIET_ACTIVE LARCH_QUIET_PID LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG LARCH_QUIET_DISABLE` guard; 6 harnesses now carry similar per-file guards — a recurring pattern that wants a central fix.

**Suggested fix**: scrub the `LARCH_QUIET_*` family once, centrally, before the checks pipeline spawns harnesses — either in `run-relevant-checks-captured.sh` (env -u / explicit unset before invoking `relevant-checks.sh`) or at `relevant-checks.sh` entry — so harnesses run hermetically regardless of the invoking session; keep existing per-harness guards as defense-in-depth; add a regression pin that runs one quiet-asserting harness with the full `LARCH_QUIET_*` family exported and expects green.

## Test plan
(no test plan section in plan-file)
