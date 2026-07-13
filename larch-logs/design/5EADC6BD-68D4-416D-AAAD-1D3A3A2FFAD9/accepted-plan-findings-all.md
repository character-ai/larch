### FINDING_1: Filtered baseline checks falsely report out-of-scope stale rows
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Guarded Baseline Io
- **Severity**: major
- **Concern**: Filtered checks compare a partial live scan against the full baseline, so rows outside the selected path scope can produce false stale warnings or strict-stale failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add one rule: when paths= is set in check mode, ignore baseline rows outside the selected path set for stale detection and matching, or reject baseline+paths= in check mode (mirror the filtered-write guard). Add a test for the chosen behavior
  - From Cursor-Innovation: For paths-filtered check mode, scope baseline rows to the selected path set before new/stale comparison (directory selectors include descendants), or hard-reject baseline_path together with paths= except for the already-planned write refusal
  - From Cursor-Pragmatic: In Approach and Edge cases, state that stale detection applies only to baseline rows whose `path` is within the effective scanned set (respecting directory selectors). Ignore off-filter baseline rows for stale/warn/strict-stale. Add a test: baseline rows for `b.py` stay silent when checking only `a.py`.
  - From Codex-Pragmatic: Restrict stale comparison to selected paths and add a filtered-check test
  - From Cursor-Requirements: In Approach/Edge cases and tests, state that stale detection considers only baseline rows whose `path` matches the effective scan scope (same selector logic as `_filter_tracked_paths`), or require `paths=None` whenever a baseline is loaded. Add a filtered-check stale test with out-of-scope baseline rows.
  - From Cursor-dyn-Guarded Baseline Io: Define filtered-check stale scope: either ignore baseline identities whose `path` is outside the selected `paths=` set for stale purposes, or document and test that filtered check requires a baseline containing only those paths; align stderr stale output with the chosen rule.


### FINDING_3: Generic deduplication can erase distinct symbol identities
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: Existing generic deduplication can collapse symbol-metric findings that differ only by symbol before projection-identity duplicate validation runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make deduplication projection-aware, preserve distinct symbol identities, and reject duplicate projected identities before indexing.
  - From Cursor-Requirements: State that baseline/check/write paths must dedupe/sort on projection identity keys (generic vs symbol-metric), and keep the current generic dedupe only when no baseline option is supplied; add a test with same path/line/message but distinct `qualified_symbol` values.


### FINDING_7: Generic baseline rows lack line-range validation
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: Invalid zero or negative line values may be accepted as baseline state instead of producing exit 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Require non-boolean integer line values greater than or equal to 1 when validating generic rows


### FINDING_12:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py:404-414
- **Concern**: [SCOPE-REDUCTION] Duplicate live projection identity policy conflicts with scan-only backward-compat contract. Scenario: Plan requires failing on duplicate live projection identities instead of last-row wins, yet also requires retaining existing scan-only tests. test_dedupe_sort_render_and_optional_fields emits duplicate generic identities and expects EXIT_FINDINGS with deduped stdout; universal duplicate enforcement would return EXIT_ERROR and break the no-baseline path
- **Proposed resolution**: Scope duplicate-identity enforcement to baseline-active modes only (baseline path supplied for check or write). Keep current first-win dedupe and sort for the no-baseline path; document that split explicitly in Approach and engine.py bullets


### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/io.py:172-257
- **Concern**: [SCOPE-REDUCTION] The concurrent-change fail-closed promise exceeds the specified atomic no-follow write contract. Scenario: trusted_atomic_write performs an unconditional replace, so a pre-write re-read cannot prevent a later race; meeting the promise requires new CAS or locking machinery
- **Proposed resolution**: Remove the concurrent-change promise and retain atomic publication plus guarded read-back


### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/io.py:224-257
- **Concern**: [SCOPE-REDUCTION] The blanket requirement that every failed write preserve the prior baseline conflicts with post-publication validation. Scenario: A read-back mismatch occurs after os.replace has published the new file; rollback can overwrite a concurrent update and cannot guarantee restoration
- **Proposed resolution**: Limit unchanged-baseline assertions to pre-publication failures; for read-back failures require exit 2 and cleanup without rollback


