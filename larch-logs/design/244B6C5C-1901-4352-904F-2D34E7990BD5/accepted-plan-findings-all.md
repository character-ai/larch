### FINDING_2: Live-module helper migration is incomplete
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Progress Retirement Correctness
- **Severity**: major
- **Concern**: Deleting `_progress_report_live.py` before relocating the retained dataclass/helper chain would break the import/export path for phase-detail rendering and round-meta writers, because the keep list omits helpers still referenced by the retained surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the keep list (or the pre-delete audit checklist) with `_PhaseRound`, `_add_round_vendor_cost_row`, `_round_vendor_cost_argv`, and `_path_mtime`; verify with `rg` on `progress_report.py` after the import block is removed.
  - From Cursor-Innovation: Replace the hand-picked keep list with a mechanical rule: after removing mid-run-only imports, relocate every symbol still referenced by `render_phase_detail`, round-meta writers, or `_render_phase_detail_best_effort`
  - From Cursor-Pragmatic: Extend the keep list to name _PhaseRound, _add_round_vendor_cost_row, and _round_vendor_cost_argv explicitly, and verify _round_vendor_cost still resolves after the import block is removed
  - From Cursor-dyn-Progress Retirement Correctness: Extend the audit step to move _PhaseRound and the full _round_vendor_cost helper chain into progress_report.py before deleting _progress_report_live.py


### FINDING_4: Legacy report-test migration is missing fixtures and retained-surface coverage
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Codex-dyn-Progress Retirement Correctness
- **Severity**: major
- **Concern**: The plan can delete `test_progress_report.py` without moving the phase-detail/round-meta tests and the shared fixtures they depend on, which would drop retained-surface coverage and can break collection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the `test_review_phase_detail.py` section, require porting (or locally redefining) the fixture helpers the migrated tests call before deleting `test_progress_report.py`.
  - From Cursor-Innovation: Extend migration to those kept-surface tests, or change REWRITTEN to in-place deletion of live/_report tests only
  - From Cursor-Requirements: Add an explicit test migration step: move surviving round-meta writer tests and the non-live fixture helpers they share with render_phase_detail tests into test_review_phase_detail.py (or a small sibling module), and keep pytest commands for write_implement_round_meta edge cases in Testing strategy
  - From Codex-dyn-Progress Retirement Correctness: Move the writer-focused tests into test_review_phase_detail.py or another retained report test module before dropping test_progress_report.py.


### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-Progress Retirement Correctness
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/report/test_progress_report.py:98-229,2297-2314,2317+
- **Concern**: [SCOPE-REDUCTION] render_phase_detail test migration must carry shared fixtures. Scenario: The plan names test functions to move but the render_phase_detail block depends on local helpers (_write_slot_manifest, _write_round_timing, _write_vendor_timing, _write_round_meta); moving tests without fixtures breaks the mandated test_review_phase_detail.py migration
- **Proposed resolution**: State in test_review_phase_detail.py that relocated tests must copy or re-localize those helpers; do not delete test_progress_report.py until the moved block is self-contained


### FINDING_1: Retained Gantt tests are missing from the migration list
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The rewrite uses `test_render_phase_detail_no_rounds` as a delete boundary, but retained pre-boundary tests that still exercise `render_phase_detail` Gantt helpers are not all listed for migration, so important unit coverage can be dropped by a literal line-based delete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the line-number boundary with an explicit live-only delete manifest; add `test_progress_label_fallbacks_and_manifest_precedence` and the three non-cap `test_progress_vendor_rows_*` tests to the required migration list (keep cap-reservation rows on the delete list per OOS_1)
  - From Cursor-Requirements: Add those four tests to the explicit migration list (or state that every pre-boundary test targeting symbols still referenced by `render_phase_detail`/round-meta must move), and narrow the rewrite delete rule to live/mid-run tests only—not blanket deletion above the `test_render_phase_detail_no_rounds` line.


### FINDING_2: Mid-run helpers in `progress_report.py` are not fully covered by Step 2 deletion and verification
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The Step 2 delete manifest and post-delete `rg` only cover the live-discovery import surface, but several mid-run wrappers and design freshness helpers already defined in `progress_report.py` can survive as unreachable dead code after the live import block is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend Step 2 with those wrappers/helpers on the delete manifest; broaden post-delete verification to `rg '_render_implement|_render_design|_render_step5|_render_design_plan_review|_render_inflight_gantt|_render_review_detail|_render_design_review_detail|LiveRun|_discover_live_run|_report\(' python/larch/report/progress_report.py` and require zero matches
  - From Cursor-Innovation: Add those symbols to the Step 2 delete inventory and extend post-removal verification with an rg pass that asserts they are absent from progress_report.py (not only that the live import block is gone)
  - From Cursor-Pragmatic: Add those wrappers (and the design freshness helpers they call) to the explicit Step 2 delete list, drop `_call_render_phase_detail` with them, and extend the post-delete `rg` audit to match `_render_(review|design_review)_detail|_call_render_phase_detail|_prior_immediate_round_end_s`.


### FINDING_3: The import audit needs the repository Python path
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Concern**: The post-removal import audit is run from the repo root without `PYTHONPATH=python` or a `python/` working directory, so it can fail before it actually imports `larch.report.progress_report`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Change the command to set PYTHONPATH=python, or run it from the python/ directory, before importing larch.report.progress_report


