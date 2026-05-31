### FINDING_1: MAV apply pre-coder head not written to snapshot dir
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `run_implement_mav_apply` in `review-implement-step5-loop.sh` still writes `pre-coder-head.txt` under `round_dir` (line 398), while the relocation plan repoints readers—including `collect_round_stage_paths` in `review-and-fix.sh` (~427), carryover guards, and step5 `structural_loc`—to `pre_coder_snapshot_dir`. When `/implement` Step 5 runs MAV apply (`--mode mav-apply`, e.g. after `main-agent-vote-required`), those readers will not see a pre-coder head in the snapshot directory. Manifest building then falls back to `capture_round_tracked_paths` instead of `round_coder_delta_paths` against the pre-dispatch HEAD, changing staged paths, commit scope, and outside-manifest checks versus today when pre-dispatch dirt exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `review-implement-step5-loop.sh` to the plan’s UPDATED bullets: `mkdir -p "$(pre_coder_snapshot_dir "$round_dir")"` and write `pre-coder-head.txt` there (same `rm -f` on rev-parse failure), matching the main snapshot call site in review-and-fix.sh ~1300
  - From Cursor-Pragmatic: Mirror the main round snapshot call site: `mkdir -p "$(pre_coder_snapshot_dir "$round_dir")"`, write `pre-coder-head.txt` there, and call `snapshot_pre_coder_tracked_state` before `apply_findings_with_coder` (or add a one-line note in the plan’s `review-implement-step5-loop.sh` section if intentionally deferred)

