### FINDING_1: Renamed-pair parity is defined but never exercised
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The harness adds a renamed-pair comparison helper, but the step-completion pair still is not invoked, so one-sided drift in `marker_step_completed` / `is_step_completed` can still slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After implementing compare_renamed_pair, invoke it from the script bottom with per-hook names, e.g. compare_renamed_pair "$BG_HOOK" marker_step_completed "$NO_PROGRESS_HOOK" is_step_completed; document the call in scripts/test-hook-clone-ownership-parity.md
  - From Cursor-Innovation: After defining compare_renamed_pair, add a harness call that extracts marker_step_completed from hook-bg-poll-guard.sh and is_step_completed from hook-no-progress-guard.sh, runs comment-stripped comparison, and fails on executable-body drift.
  - From Cursor-Requirements: After compare_renamed_pair is defined, call compare_renamed_pair marker_step_completed is_step_completed (or equivalent) alongside the existing compare_function invocations

### FINDING_2: bg-wait writer parity lint is too line-local for live writers
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The lint anchor only recognizes literal same-line `.bg-wait-active` plus write tokens, but live design writers emit `CLONE_PATH=` through temp-file / variable-backed write flows, so the repo-root acceptance test can false-fail or the rule can miss the actual write context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the plan rule to anchor on the writer function/block: treat a .bg-wait-active path assignment within the window as the anchor, or scan the enclosing function for CLONE_PATH= near write_text/printf/replace/mv marker promotion; keep the repo-root acceptance test as the gate
  - From Codex-Arch: Extend the plan rule to anchor on the writer function/block: treat a .bg-wait-active path assignment within the window as the anchor, or scan the enclosing function for CLONE_PATH= near write_text/printf/replace/mv marker promotion; keep the repo-root acceptance test as the gate
  - From Cursor-Innovation: Extend write-context detection: treat a ±15-line window around any of `write_text(`, `printf`, `>`, `.replace(`, or `mv` as an anchor when the same window also references `.bg-wait-active` (literal or via a marker variable assigned from it); require `CLONE_PATH=` inside that window. Add fixtures mirroring `design_core.py` and `design-step3-review.sh`.
  - From Codex-Innovation: Revise _has_clone_path_emission to treat marker variable assignment plus temp-to-marker mv/replace/write_text in the same function or nearby block as the write context, then require CLONE_PATH= within that block/window; add a fixture for this indirect temp-writer shape.
  - From Cursor-Pragmatic: Define anchors as a ±15 window around either (a) a write-indicator line or (b) an assignment to a `*.bg-wait-active` path, and require `CLONE_PATH=` in that window; treat `mv`/`replace` promotion from a temp file as write context. Add fixture regressions mirroring `design_core.py` and `design-step3-review.sh` shapes.
  - From Codex-Requirements: Define `_has_clone_path_emission` around writer blocks or functions: treat marker variable assignment plus temp write or mv, and Python marker Path plus write_text or replace, as qualifying writer blocks; require at least one qualifying writer block; make cleanup-only pass fixtures include a real writer elsewhere and add a no-write-anchor fixture that fails

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

### FINDING_5: Extracted `bg_wait.py` needs pyright-safe handling
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Moving the helper body into a new module can introduce pyright failures for ignored `write_text` / `unlink` results, and the imported underscored helper can also trip private-usage reporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add either exact pyright ignores or local unused-result assignments in bg_wait.py, and add an exact reportPrivateUsage ignore for the step_7a private-helper import or call

### FINDING_6: Step 7a test still references a symbol the extraction removes
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The test update asks `test_step_7a.py` to call `step_7a._write_bg_wait_marker` even though the extraction plan removes that symbol, so the test contract conflicts with the refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Update test_step7a_bg_wait_marker_copies_keepalive_clone_path to exercise larch.implement.bg_wait._write_bg_wait_marker directly or to enter step_7a._bg_wait_marker and assert the marker fields; do not require step_7a._write_bg_wait_marker to remain
