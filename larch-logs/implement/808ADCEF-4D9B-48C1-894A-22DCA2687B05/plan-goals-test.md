## Goal
Fix three bugs causing larch-log writes after the pre-bump flush to remain as untracked (uncommitted) files and land under the wrong run-ID directory.

## Goal
Fix three bugs causing larch-log writes after the pre-bump flush to remain
as untracked (uncommitted) files and land under the wrong run-ID directory.

## Implementation Plan

### Bug 3 — wrong run_id in write_version_reasoning_fragment
File: scripts/implement-finalize.sh
Location: write_version_reasoning_fragment(), ~line 410

The fallback chain `"${LARCH_RUN_ID:-${RUN_ID:-}}"` resolves to empty when
neither env var is set (normal orchestrator context), then falls back to
`$(basename "$IMPLEMENT_TMPDIR")` stripped after the last dash — which
produces the short random suffix of the tmpdir name (e.g. "8XA0Hi") instead
of the UUID-format RUN_ID. The state file, loaded by
load_and_validate_postbump_state(), already contains the correct RUN_ID.

Fix: extend the fallback chain to `${LARCH_RUN_ID:-${RUN_ID:-$(read_state RUN_ID)}}`.

### Bug 1 — larch-log writes after pre-bump flush never committed on happy path
File: scripts/ship-pr.sh
Location: run_ci_phase(), ci-merge phase entry

After the pre-bump log flush (Step 7a tail), three batches are written to
larch-logs but never committed on the happy path:
  - version-bump-reasoning.md  (written at postbump / implement-finalize.sh)
  - oos-issues, run-statistics, token-report, timing-report (written at Step 9a.1)
  - execution-issues.ndjson (written at Step 11)

The rebase-rebump sub-procedure step 1b already commits these on any rebase
path; the gap is the happy path (no rebase, first-time CI green → merge).
The ci-merge phase runs after Step 11 and before merge-pr.sh — it's the
correct insertion point.

Fix: in run_ci_phase(), after the REPO_UNAVAILABLE early-return block, add a
larch-log flush for phase=ci-merge. Use larch-log.sh commit (with push) so
the commit reaches the remote branch before merge-pr.sh merges it.

### Bug 2 — teardown never commits/cleans up pending larch-log writes
File: scripts/implement-finalize.sh
Location: run_teardown(), before kill_session_background_processes

For stalled/failed runs (where the ci-merge flush never ran), larch-log
writes remain untracked in larch-logs/implement/RUN_ID/. Additionally, Bug 3
can leave stale directories for OTHER run IDs. Teardown is the right
collection point.

Fix: in run_teardown(), before the existing cleanup block:
  1. Commit pending larch-log writes for the current run (--no-push; best-effort)
  2. Remove any untracked larch-logs/implement/ subdirs that don't match the
     current RUN_ID (these are stale artifacts from bugs or failed runs).
     Safety: the single-runner invariant means no concurrent runs own these dirs.

## Test / Verification
- /relevant-checks after implementation
- Manual trace: confirm write_version_reasoning_fragment reads correct RUN_ID
  via read_state; the basename fallback is never reached
- Manual trace: confirm run_ci_phase adds the flush before ci-wait.sh in
  ci-merge phase
- The untracked files issue (8XA0Hi/ and execution-issues.ndjson) would not
  appear after these fixes on the next /implement run
