### FINDING_1: Renamed-pair parity is defined but never exercised
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The harness adds a renamed-pair comparison helper, but the step-completion pair still is not invoked, so one-sided drift in `marker_step_completed` / `is_step_completed` can still slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After implementing compare_renamed_pair, invoke it from the script bottom with per-hook names, e.g. compare_renamed_pair "$BG_HOOK" marker_step_completed "$NO_PROGRESS_HOOK" is_step_completed; document the call in scripts/test-hook-clone-ownership-parity.md
  - From Cursor-Innovation: After defining compare_renamed_pair, add a harness call that extracts marker_step_completed from hook-bg-poll-guard.sh and is_step_completed from hook-no-progress-guard.sh, runs comment-stripped comparison, and fails on executable-body drift.
  - From Cursor-Requirements: After compare_renamed_pair is defined, call compare_renamed_pair marker_step_completed is_step_completed (or equivalent) alongside the existing compare_function invocations


### FINDING_3: step_7a still needs explicit duplicate-helper cleanup
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The dedup plan leaves room for local copies of the bg-wait helpers to survive in `step_7a.py`, preserving a second drift surface even after `dispatch_commit_route.py` is cleaned up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add explicit step_7a cleanup: remove the local `_clear_no_progress_sidecars`, `_read_keepalive_clone_path`, and `_write_bg_wait_marker` bodies and import them from `larch.implement.bg_wait` (keep only the local `_bg_wait_marker` / `_write_terminal_sentinel` context wrapper).
  - From Cursor-Requirements: Mirror the dispatch_commit_route.py instructions: remove the three duplicate helpers from step_7a.py and import _write_bg_wait_marker from larch.implement.bg_wait inside the local _bg_wait_marker context manager


### FINDING_4: `time` is still live in the Step 5 resume path
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan treats `time` as removable, but `step5_resume_main` still uses `int(time.time())`, so removing the import would raise `NameError` on the Step 5 resume path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Revise the plan to keep import time unless the final diff proves all non-marker uses are gone


### FINDING_6: Step 7a test still references a symbol the extraction removes
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The test update asks `test_step_7a.py` to call `step_7a._write_bg_wait_marker` even though the extraction plan removes that symbol, so the test contract conflicts with the refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Update test_step7a_bg_wait_marker_copies_keepalive_clone_path to exercise larch.implement.bg_wait._write_bg_wait_marker directly or to enter step_7a._bg_wait_marker and assert the marker fields; do not require step_7a._write_bg_wait_marker to remain


