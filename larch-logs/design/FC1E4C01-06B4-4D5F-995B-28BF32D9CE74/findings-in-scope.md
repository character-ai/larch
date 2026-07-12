### FINDING_1: Rejected-analysis must preserve `updated_at` fallback
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: Migrating rejected-analysis to the shared `run_started_at` helper with its default `allow_updated_at_fallback=False` would exclude runs whose only usable timestamp is `updated_at`, changing date-window filtering, survivor counts, and ordering. The migration must also preserve first-valid-object stop semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `rejected_analysis.py`, call `run_started_at(..., allow_updated_at_fallback=True)` (and keep first-valid-object stop semantics). Add a regression fixture with only `updated_at` set to lock date-window inclusion.
  - From Cursor-Requirements: Add an explicit rejected-analysis line: use `run_started_at(..., allow_updated_at_fallback=True)` with `continue_on_empty=False`, preserving first-valid-object stop when both timestamp fields are empty.

### FINDING_2: Include committed run-log discovery in the repoint set
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: `python/larch/design/design_step_log.py` still discovers committed runs with a raw `larch-logs/implement/*/manifest.json` glob. This bypasses the shared containment and manifest-acceptance policy and conflicts with the planned adoption ratchet.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_3: Repoint committed plan-review classification traversal
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: `_design_plan_review_round_dirs` still enumerates committed `plan-review/round-*` directories with a raw glob, leaving a committed corpus walk outside the shared API and potentially bypassing containment and symlink policy.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_4: Specify file-level safety for classification artifacts
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: The classification helpers do not specify whether returned TSV artifacts must be regular, non-symlink files contained within the run directory. A symlink such as `findings-classification.tsv` could otherwise point outside the committed corpus.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_5: Preserve manifest-only metadata policy in fluff analysis
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Fluff analysis currently reads only `manifest.json`, while default shared metadata helpers may also read `run-manifest.json`. Repointing without an explicit manifest scope would include run-manifest-only runs and change period bucketing, version filtering, and counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin fluff to `manifest.json`-only reads (add a `manifest_candidates`/`single_candidate` helper option, or keep the existing single-file read for enumeration filters) and extend corpus harness fixtures for run-manifest-only directories.
  - From Cursor-Pragmatic: Use the same manifest.json-only candidate scope as GC for fluff started-at reads (allow_updated_at_fallback=False is not enough), and extend the existing period-bucketing harness to cover run-manifest-only fixtures.

### FINDING_6: Preserve rejected-analysis classification round ordering
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: Rejected-analysis currently sorts classification TSVs lexically, whereas the shared classification helper may apply a different round-order policy. An unspecified policy could reorder multi-round runs and change findings or ledger ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pass the lexical `round_sort` policy in the rejected-analysis repoint and lock it in `python/tests/issue/test_rejected_analysis.py`.

### FINDING_7: Name `map_runs_main` in the audit-runs migration
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The audit-runs plan does not explicitly cover the unsafe corpus globs in `map_runs_main`. Missing this helper could leave symlinked run directories reachable or cause the new ratchet to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Name `map_runs_main` explicitly: enumerate via `safe_child_run_dirs`, then check `parent-issue.md` / `manifest.json` inside each contained run dir; add a symlink run-dir regression beside the planned audit-runs test.

### FINDING_8: Account for GC recursive safety and sizing walks
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: GC retains recursive `os.walk` calls for escape-symlink detection and directory sizing. The planned ratchet appears to reject such committed-corpus walks, so the plan must distinguish validated per-run inspection from unsafe corpus traversal without creating a broad exemption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Define and test a narrow exemption/category for recursive inspection inside an already validated run directory, or move the reusable safe recursive inspection into `run_log_corpus.py`; do not add a broad GC-file exemption.

### FINDING_9: Add required regression files to the firm file list
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The plan requires difficulty-calibration, fluff-analysis, voter-calibration, and final-report regression coverage but does not list the corresponding test and harness files under `Files to modify/create`. Implementations could omit those checks while still claiming the stated validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the exact affected test and harness paths to `Files to modify/create`, including `python/tests/calibration/test_difficulty_calibration.py`, the fluff and voter shell harnesses, and `python/tests/report/test_final_report.py` if its metadata boundary changes.

### FINDING_10: Preserve alternate-manifest fallback in strict ground-truth reads
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Strict ground-truth discovery continues to the alternate manifest when `manifest.json` is valid but lacks `started_at`. A default first-object stop in the shared helper would exclude runs whose timestamp exists only in `run-manifest.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add continue_on_empty=True to the strict ground-truth run_started_at call (or an equivalent helper flag) and lock it with a fixture where manifest.json is a valid object without started_at and run-manifest.json supplies it.

### FINDING_11: Preserve GC’s manifest.json-only timestamp policy
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: GC currently reads `started_at` only from `manifest.json` before falling back to Git dates. Default shared metadata discovery could start accepting `run-manifest.json`, changing retention and slimming dates for runs that were previously handled by Git fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit manifest-candidate scope to the shared metadata helpers (for example candidates=("manifest.json",) or allow_alternate_manifest=False) and use manifest.json-only mode in gc_run_logs.py; add a regression where manifest.json is absent and run-manifest.json has started_at to prove Git fallback is unchanged.

### FINDING_12: Preserve difficulty-calibration error-counter semantics
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Replacing the local child-directory scan with `safe_child_run_dirs` can change how root `OSError` cases are classified. Resolve failures and child-enumeration failures must continue mapping to their existing counters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Pin the adapter: map resolve failures to missing_skill_roots and child-enumeration OSError to unreadable_skill_roots, and assert both counters in test_difficulty_calibration.py.

### FINDING_13: Account for existing committed-corpus walkers in `tokens.py`
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Existing `tokens.py` iterators use recursive and per-skill committed `larch-logs` globs but are outside the repoint set. The new ratchet could fail immediately, or the plan could leave these walkers outside the shared containment policy without documenting a narrowly justified exception.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Repoint both iterators through safe_child_run_dirs (and contained per-run artifact checks) or add a narrowly justified exemption with negative lint fixtures; include tokens.py in the firm file set and add focused lint coverage.
  - From Cursor-Requirements: Spell out ratchet treatment in the lint plan: either document these as allowed fixed-artifact lookups in the rule/tests, or add a narrow grandfather/exclusion for tokens.py panel/checks-digest iterators.

### FINDING_14: Extend the pre-commit ratchet to skill scanner scripts
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Concern**: The pre-commit hook currently filters only `python/.*\.py`, so changes to the in-scope skill scanner scripts would not trigger the run-log-walker ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add the two scanner-script paths to the hook filter, or scope the hook to every tracked Python source that the ratchet scans.

### FINDING_15:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/final_report.py:267-271
- **Concern**: [SCOPE-REDUCTION] `final_report.py` firm update appears unnecessary. Scenario: The listed reads are session-local `implement_tmpdir/.../manifest.json` lookups for token/outcome recovery, not committed `larch-logs` walks or dual-manifest loops. They are already excluded by the plan’s session-manifest carve-out and are not ratchet targets. Drop `### UPDATED: python/larch/report/final_report.py` and the associated `test_final_report.py` corpus-boundary work unless a concrete committed-corpus call site is identified.
- **Proposed resolution**:
