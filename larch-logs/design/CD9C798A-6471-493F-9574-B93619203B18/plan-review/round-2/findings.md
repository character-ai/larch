### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:2664-2667
- **Concern**: skills/review-and-fix/scripts/test-review-and-fix.sh:2664-2667. Scenario: Plan adds clear_stale_pre_coder_snapshot_artifacts to run_implement_mav_apply but step5-starting-round only eval-extracts pre_coder_snapshot_dir before sourcing review-implement-step5-loop.sh
- **Proposed resolution**: mav-apply-relocated-pre-head subshell calls run_implement_mav_apply under set -e; clear_stale is undefined → command-not-found and test-review-and-fix-step5-starting-round fails after implementation Add eval "$(sed -n '/^clear_stale_pre_coder_snapshot_artifacts/,/^}/p' "$SCRIPT")" beside the existing pre_coder_snapshot_dir eval at 2664 (or inside the mav subshell before run_implement_mav_apply)

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:43 / skills/review-and-fix/scripts/test-review-and-fix.sh:3073-3078
- **Concern**: Post-coder-head 444 coverage listed for mav-apply-relocated-pre-head but stub sets CODER_STATUS=no-changes. Scenario: run_implement_mav_apply only writes/chmods post-coder-head.txt when CODER_STATUS=applied (review-implement-step5-loop.sh:412-413); mode assertion in that case never runs or fails on missing file
- **Proposed resolution**: Limit post-coder-head mode checks to fix-applied paths (e.g. run_orchestrator_case / carryover-orchestrator) or change the mav stub to emit CODER_STATUS=applied and assert the file exists before checking mode

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:2664-2667
- **Concern**: `step5-starting-round` only `eval`s `pre_coder_snapshot_dir`, not the new `clear_stale_pre_coder_snapshot_artifacts` helper that `run_implement_mav_apply` will call. Scenario: After production adds `clear_stale…` before the MAV head write, `mav-apply-relocated-pre-head` subshell hits `clear_stale_pre_coder_snapshot_artifacts: command not found` under `set -euo pipefail` (step5 loop is sourced without loading full `review-and-fix.sh`)
- **Proposed resolution**: In `step5-starting-round`, `eval` the new helper(s) from `"$SCRIPT"` with the same `sed -n '/^clear_stale_pre_coder_snapshot_artifacts/,/^}/p'` pattern used elsewhere (mirror line 2664)

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:3073-3087
- **Concern**: Post-coder `0444` assertion is tied to `mav-apply-relocated-pre-head`, but the stub sets `CODER_STATUS=no-changes`. Scenario: Production only writes/chmods `post-coder-head.txt` when `CODER_STATUS=applied` (`review-implement-step5-loop.sh:409-414`); the MAV case never creates the file, so a mode-`444` check is vacuous or fails
- **Proposed resolution**: Either set the MAV stub to `CODER_STATUS=applied` (and assert `post-coder-head.txt` under `round_dir`), or assert `0444` only in dispatch `fix-applied` coverage (e.g. `run_orchestrator_case` / `fix-applied-not-overwritten` at ~2165) where the real write path runs

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:3051-3088
- **Concern**: Planned post-coder-head 0444 assertion targets mav-apply-relocated-pre-head but that case never runs the production write path. Scenario: run_implement_mav_apply only writes post-coder-head.txt when CODER_STATUS=applied; the stub sets no-changes (line 3077) so chmod at review-implement-step5-loop.sh:413 never runs and a mode-444 assertion would fail or be vacuous, leaving acceptance criterion 2 uncovered if implementers rely on this case alone
- **Proposed resolution**: Scope post-coder-head mode checks to an integration path that reaches review-and-fix.sh:1531-1532 or step5-loop:413 with CODER_STATUS=applied (e.g. extend run_orchestrator_case / fix-applied-not-overwritten); drop mav-apply-relocated-pre-head from post-coder-head 0444 coverage or change the stub to applied and exercise the real write+chmod sequence
