# Review Round 2

- Mode: `diff`
- 2 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_5: Missing pytest for four `--no-fallback` DROPPED_SLOTS_FILE drop reasons
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Four of six plan-required `--no-fallback` `DROPPED_SLOTS_FILE` reasons lack pytest coverage (result-gate-miss, empty, collector-failure, result-unreadable). Voter dispatch and decompose use `--no-fallback`; a bug in an untested drop branch can ship green while slots are mis-dropped or mis-reasoned at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub-driven cases for each remaining reason; assert TSV reason column and ALL_SLOTS_DROPPED / partial-drop KVs.


### FINDING_6: Paths-file / dropped-slots temp creation can bypass ValidationError exit 2
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: In `python/agent_waterfall.py:588-621`, paths-file and dropped-slots temp creation can raise `OSError` before the `try` block, so an unwritable existing `--paths-file` parent exits with an uncaught traceback and rc 1 instead of the documented rc 2 validation failure. Concrete scenario: reviewers finish successfully, `--paths-file /existing-unwritable-dir/outputs.list` passes the parent `is_dir()` check, then `tempfile.mkstemp(..., dir=paths_dir)` raises `PermissionError`, bypassing `ValidationError` and the clean exit-code contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Move `mkstemp` inside the `try` in `_write_paths_file`, wrap `_write_drops` similarly, and convert these `OSError`s into `ValidationError("dispatch-with-waterfall.sh: paths-file not writable: ...")` or an equivalent dropped-slots sidecar diagnostic with exit 2.


