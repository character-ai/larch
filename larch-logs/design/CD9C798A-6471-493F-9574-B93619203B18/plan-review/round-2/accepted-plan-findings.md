### FINDING_1: step5-starting-round omits `clear_stale_pre_coder_snapshot_artifacts` for MAV subshell
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The planned change adds `clear_stale_pre_coder_snapshot_artifacts` to `run_implement_mav_apply`, but the `step5-starting-round` harness only `eval`s `pre_coder_snapshot_dir` from `"$SCRIPT"` (around line 2664) before sourcing `review-implement-step5-loop.sh`. The `mav-apply-relocated-pre-head` subshell runs `run_implement_mav_apply` under `set -euo pipefail` without loading full `review-and-fix.sh`, so the new helper will be undefined and the case will fail with `command not found` once production calls it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: mav-apply-relocated-pre-head subshell calls run_implement_mav_apply under set -e; clear_stale is undefined → command-not-found and test-review-and-fix-step5-starting-round fails after implementation Add eval "$(sed -n '/^clear_stale_pre_coder_snapshot_artifacts/,/^}/p' "$SCRIPT")" beside the existing pre_coder_snapshot_dir eval at 2664 (or inside the mav subshell before run_implement_mav_apply)
  - From Cursor-Innovation: In `step5-starting-round`, `eval` the new helper(s) from `"$SCRIPT"` with the same `sed -n '/^clear_stale_pre_coder_snapshot_artifacts/,/^}/p'` pattern used elsewhere (mirror line 2664)


### FINDING_2: post-coder-head `0444` coverage on MAV case cannot exercise production write/chmod
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Planned acceptance for `post-coder-head.txt` mode `0444` is tied to `mav-apply-relocated-pre-head`, but that case’s stub sets `CODER_STATUS=no-changes` (line 3077). Production only writes and chmods `post-coder-head.txt` when `CODER_STATUS=applied` (`review-implement-step5-loop.sh:412-413`; same pattern in `review-and-fix.sh`). The MAV path therefore never creates the file, so a mode-`444` assertion is vacuous, fails on a missing file, or leaves acceptance criterion 2 uncovered if implementers rely on this case alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Limit post-coder-head mode checks to fix-applied paths (e.g. run_orchestrator_case / carryover-orchestrator) or change the mav stub to emit CODER_STATUS=applied and assert the file exists before checking mode
  - From Cursor-Innovation: Either set the MAV stub to `CODER_STATUS=applied` (and assert `post-coder-head.txt` under `round_dir`), or assert `0444` only in dispatch `fix-applied` coverage (e.g. `run_orchestrator_case` / `fix-applied-not-overwritten` at ~2165) where the real write path runs
  - From Cursor-Requirements: Scope post-coder-head mode checks to an integration path that reaches review-and-fix.sh:1531-1532 or step5-loop:413 with CODER_STATUS=applied (e.g. extend run_orchestrator_case / fix-applied-not-overwritten); drop mav-apply-relocated-pre-head from post-coder-head 0444 coverage or change the stub to applied and exercise the real write+chmod sequence

