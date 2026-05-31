### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:398
- **Concern**: `run_implement_mav_apply` still writes `pre-coder-head.txt` under `round_dir` but the plan only repoints readers (including `collect_round_stage_paths` at review-and-fix.sh:427) to `pre_coder_snapshot_dir`. Scenario: MAV `/implement` Step 5 (`--mode mav-apply`) will not see a pre-coder head after relocation; manifest building falls back to `capture_round_tracked_paths` instead of `round_coder_delta_paths`, changing commit scope vs today when pre-dispatch dirt exists
- **Proposed resolution**: Add `review-implement-step5-loop.sh` to the plan’s UPDATED bullets: `mkdir -p "$(pre_coder_snapshot_dir "$round_dir")"` and write `pre-coder-head.txt` there (same `rm -f` on rev-parse failure), matching the main snapshot call site in review-and-fix.sh ~1300

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:396-401
- **Concern**: `run_implement_mav_apply` still writes `pre-coder-head.txt` under `round_dir` but the plan repoints all readers (`collect_round_stage_paths`, carryover guards, step5 `structural_loc`) to `pre_coder_snapshot_dir`. Scenario: MAV `--mode mav-apply` runs (implement Step 5 after `main-agent-vote-required`) will not see a head in the snapshot dir; manifest building falls back to `capture_round_tracked_paths` instead of `round_coder_delta_paths` vs pre-dispatch HEAD, changing staged paths and outside-manifest checks vs today
- **Proposed resolution**: Mirror the main round snapshot call site: `mkdir -p "$(pre_coder_snapshot_dir "$round_dir")"`, write `pre-coder-head.txt` there, and call `snapshot_pre_coder_tracked_state` before `apply_findings_with_coder` (or add a one-line note in the plan’s `review-implement-step5-loop.sh` section if intentionally deferred)
