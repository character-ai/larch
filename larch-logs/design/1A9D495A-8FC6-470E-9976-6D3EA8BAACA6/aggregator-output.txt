### FINDING_1: Step 7a direct run-log commit bypasses the pre-terminal guard
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: major
- **Concern**: Step 7a still runs `run-log commit` after `flush_logs_pre()` reports the pre-terminal refusal/skip, so a staged stalled/bailed `final-summary.md` can still be published through the direct commit path instead of being blocked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add the shared parse/check helper to larch_log_commit_main (python/larch/report/run_log_commit.py) immediately before _commit_run: when the staged implement run_dir final-summary.md parses to a forbidden label, refuse commit with a bounded warning and non-zero exit. Keep finalize teardown commit_larch_logs unguarded. Add a regression test in python/tests/report/test_run_logs.py (or test_run_log_flush.py) that seeds a forbidden heading under log_root and asserts larch_log_commit_main does not commit. List python/larch/report/run_log_commit.py under ### UPDATED: if the guard lives there.
  - From Codex-Arch: Skip the commit call when `refresh.reason == config.REFRESH_SKIP_COMMIT_FAILED`, or gate the commit on `not refresh.skipped` after the flush result is checked.
  - From Cursor-Innovation: Add python/larch/implement/step_7a.py to the plan: call the shared _preterminal_outcome_refresh_skip (or equivalent) before run-log commit and skip commit when it fires; update skills/implement/scripts/test-step-7a.sh so pre-terminal refusal does not fall through to commit.
  - From Cursor-Pragmatic: Add the same shared pre-terminal check to larch_log_commit_main in python/larch/report/run_log_commit.py (skip commit with bounded warning, mirroring larch_log_flush_main), or teach step_7a to skip run-log commit when the refresh skip was caused by a forbidden label. List run_log_commit.py (and step_7a.py if branching there) under Files to modify/create and add a Step 7a regression test.
  - From Codex-Pragmatic: Add a firm plan step to guard the Step 7a direct commit path, either by applying the same pre-terminal label check in larch_log_commit_main() for implement tmpdirs before _commit_run(), or by making Step 7a skip the direct commit after this specific pre-terminal refusal, with a focused regression for that path.

### FINDING_2: Pre-terminal heading parser should target the run-summary line
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The new label parser could misread the first `##` section instead of the canonical `## /...` run heading in `final-summary.md`, which would let forbidden labels slip through or block neutral ones.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify that _parse_preterminal_outcome_label scans all lines for startswith("## /") (same contract as final_report._summary_stalled_heading_index), extracts the trailing label after : or em-dash, and add a unit test with prefixed ## Architectural sections before the run heading.

### FINDING_3: `capture_transcript_main()` also needs the pre-terminal guard
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The public `run-log capture-transcript` path can still commit a run tree whose `final-summary.md` is stalled/bailed when `--defer-commit false`, bypassing the new invariant outside the refresh/flush paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Apply the same pre-terminal guard before `_commit_run()` here too, or force this CLI onto the no-commit path whenever `final-summary.md` is present.

### FINDING_4: PR body must document the G-Orch-4/G-Obs-4 reference sweep
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Concern**: The change may satisfy code/tests but still miss the acceptance requirement to document the `G-Orch-4|G-Obs-4` reference sweep in the PR body.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a firm PR-description step that records the exact reference-sweep command and result in the PR body.
