### FINDING_1: Teardown catches unrelated `ShipError` values and masks invalid state
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The proposed teardown fallback catches `ShipError` around the entire `disposition_link_kind()` call. That helper can fail for malformed, missing, untrusted, partial, or internally inconsistent coverage and disposition artifacts—not only for the stale live-coverage mismatch. Falling back to `"closes"` in those cases can silently complete teardown, apply the `[DONE]` rename, and hide integrity failures that should remain fail-closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a mismatch-specific exception or predicate, fall back to "closes" only for that condition, and re-raise other ShipError values. Add regression coverage for invalid disposition errors.
  - From Cursor-Innovation: Resolve link kind in a helper: try load_live_coverage only inside try/except ShipError; on the mismatch message fall back; re-raise all other ShipError cases
  - From Codex-Innovation: Handle only the specific stale-live-fingerprint failure and re-raise other `ShipError` cases. Use a dedicated exception or a narrowly identified predicate while retaining the breadcrumb for the stale case.
  - From Cursor-Pragmatic: On ShipError from disposition_link_kind, handle only the live-input mismatch (message contains coverage artifact does not match live repository inputs). Then resolve link kind from persisted load_coverage plus load_disposition without load_live_coverage; default to closes only when persisted coverage or disposition is missing or invalid. Add a teardown regression where proceed-partial plus stale live skips rename.
  - From Codex-Pragmatic: Catch only the known stale-coverage mismatch and preserve other ShipError failures; keep the fallback breadcrumb for that specific case.
  - From Cursor-Requirements: In ### UPDATED: python/larch/state/finalize.py, limit fallback to stale live-coverage mismatch only (e.g. does not match live repository inputs in str(exc)), matching validate_disposition_for_ship at python/larch/implement/scope_disposition.py:1014; re-raise other ShipError from disposition_link_kind
  - From Codex-Requirements: Limit the fallback to the specific stale-coverage mismatch and re-raise other ShipError cases; retain the breadcrumb only for that degraded path


### FINDING_2: Teardown fallback loses persisted `proceed-partial` disposition
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Even when the failure is the specific stale live-coverage mismatch, always defaulting to `"closes"` ignores a persisted `proceed-partial` disposition. That can enter the `[DONE]` rename branch even though partial runs with follow-up work must retain the `part-of` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: On mismatch only, derive link kind from load_coverage plus load_disposition (persisted artifacts) before defaulting to closes; keep the breadcrumb
  - From Cursor-Pragmatic: On ShipError from disposition_link_kind, handle only the live-input mismatch (message contains coverage artifact does not match live repository inputs). Then resolve link kind from persisted load_coverage plus load_disposition without load_live_coverage; default to closes only when persisted coverage or disposition is missing or invalid. Add a teardown regression where proceed-partial plus stale live skips rename.


### FINDING_3: Missing regression coverage for non-mismatch teardown failures
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The planned tests cover stale-mismatch fallback but not the inverse case where a non-mismatch `ShipError` must still propagate. Without that test, a broad catch can regress unnoticed and allow corrupt disposition state to reach successful cleanup or the done rename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a test where disposition exists without trusted coverage (or disposition is malformed) and assert teardown still raises or fails instead of renaming to done
  - From Cursor-Pragmatic: Add a negative test (disposition present without trusted coverage, or malformed disposition with live match) asserting teardown does not reach done rename / successful cleanup.


### FINDING_4: Final-report coverage fallback suppresses integrity failures
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The proposed `final_report.py` fallback catches every `ShipError` from `load_live_coverage()` and returns an empty coverage line. That would suppress malformed, partial, unsafe, missing, mismatched, or otherwise invalid coverage artifacts, allowing report generation to succeed while omitting trusted validation evidence instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Catch only the coverage-mismatch condition, or introduce a typed stale-coverage exception and re-raise all other ShipError values. Add a test that integrity errors still propagate.
  - From Codex-Innovation: Limit the fallback to the exact stale-live-input mismatch. Preserve propagation of all other `ShipError` values.
  - From Codex-Pragmatic: Handle only the specific coverage-artifact/live-input mismatch, or introduce a narrowly typed exception for that condition. Re-raise all other ShipError values.
  - From Codex-Requirements: Catch only the coverage-versus-live mismatch, or re-raise all other ShipError cases before returning an empty summary line


### FINDING_1: Recovery can proceed without persisted coverage
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The stale-mismatch recovery path does not fail closed when its second `load_coverage(tmpdir)` call returns `None`. If coverage disappears during recovery, teardown can select `"closes"`, apply the `[DONE]` rename, and complete without validated persisted evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: After recovery calls `load_coverage(tmpdir)`, explicitly raise `ShipError` if it returns `None`. Add this case to the focused recovery test so the done rename and cleanup remain blocked


