### FINDING_2: Update finalize consumer-binding tests
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Facade Binding Auditor, Codex-dyn-Facade Binding Auditor
- **Severity**: major
- **Concern**: `test_finalize.py` patches facade bindings that `finalize.py` will no longer resolve. Recovery, initialization, and teardown tests may fail before running or pass without exercising the intended failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/tests/state/test_finalize.py`: retarget imports and `monkeypatch.setattr` to the module finalize resolves (`finalize`, `run_log_manifest`, `run_log_commit`, or `run_log_flush` per call site). Include `python3 -m pytest python/tests/state/test_finalize.py` in Testing strategy.
  - From Cursor-Innovation: Add `### UPDATED: python/tests/state/test_finalize.py`: retarget `init_run`/`effective_run_id`/manifest patches to finalize's owner-module bindings (or `run_log_manifest`)
  - From Codex-Innovation: Add these focused test files to the plan and retarget their monkeypatches to the owner-module bindings introduced by the caller changes.
  - From Cursor-Pragmatic: Add `### UPDATED: python/tests/state/test_finalize.py` to repoint patches and types to `run_log_manifest` / `run_log_commit` bindings resolved by `finalize.py`.
  - From Cursor-Requirements: Add `### UPDATED python/tests/state/test_finalize.py`, `### UPDATED python/tests/implement/test_step_7a.py`, and `### UPDATED python/tests/review/test_review_and_fix.py` mirroring `test_run_logs.py`: retarget imports and `monkeypatch.setattr`/`patch.object` to the module each production file resolves (`run_log_manifest`, `run_log_flush`, `run_log_batch`); keep only residual `run_logs` coverage in `test_run_logs.py`
  - From Cursor-dyn-Facade Binding Auditor: Add `### UPDATED: python/tests/state/test_finalize.py`; patch `finalize`’s imported module bindings (e.g. `finalize.run_log_manifest.load_or_recover_manifest_checked`) and drop direct `run_logs.init_run` calls where `init_run` leaves the facade
  - From Codex-dyn-Facade Binding Auditor: Add these test files to the plan and repoint every reference and monkeypatch to the exact binding resolved by the migrated caller.


### FINDING_3: Update step_7a consumer-binding tests
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Facade Binding Auditor, Codex-dyn-Facade Binding Auditor
- **Severity**: major
- **Concern**: `test_step_7a.py` patches `step_7a.run_logs` flush and diagnostic helpers even though production will resolve those through owner modules. Tests may raise `AttributeError` or invoke real flush and commit code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `### UPDATED: python/tests/implement/test_step_7a.py`: move monkeypatch targets to `step_7a.run_log_flush` (and proc) per resolved runtime bindings
  - From Codex-Innovation: Add these focused test files to the plan and retarget their monkeypatches to the owner-module bindings introduced by the caller changes.
  - From Cursor-Pragmatic: Add `### UPDATED: python/tests/implement/test_step_7a.py` with instructions to patch `step_7a.run_log_flush` / `step_7a.run_log_batch` (and `RefreshSkip` from `run_log_manifest`) per the plan’s binding rule.
  - From Cursor-Requirements: Add `### UPDATED python/tests/state/test_finalize.py`, `### UPDATED python/tests/implement/test_step_7a.py`, and `### UPDATED python/tests/review/test_review_and_fix.py` mirroring `test_run_logs.py`: retarget imports and `monkeypatch.setattr`/`patch.object` to the module each production file resolves (`run_log_manifest`, `run_log_flush`, `run_log_batch`); keep only residual `run_logs` coverage in `test_run_logs.py`
  - From Cursor-dyn-Facade Binding Auditor: Add `### UPDATED: python/tests/implement/test_step_7a.py`; retarget patches to the bindings step_7a resolves at runtime (e.g. `step_7a.run_log_flush`) per the edge-case monkeypatch rule
  - From Codex-dyn-Facade Binding Auditor: Add these test files to the plan and repoint every reference and monkeypatch to the exact binding resolved by the migrated caller.


### FINDING_4: Update review_and_fix consumer-binding tests
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Cursor-dyn-Facade Binding Auditor, Codex-dyn-Facade Binding Auditor
- **Severity**: major
- **Concern**: The warning-path test patches `review_and_fix.run_logs.append_execution_issue`, but production will resolve the function through `run_log_batch`. The intended fail-open `OSError` path will not be exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `### UPDATED: python/tests/review/test_review_and_fix.py`: patch `review_and_fix.run_log_batch.append_execution_issue` (or the module-level binding `review_and_fix` resolves)
  - From Codex-Innovation: Add these focused test files to the plan and retarget their monkeypatches to the owner-module bindings introduced by the caller changes.
  - From Cursor-Requirements: Add `### UPDATED python/tests/state/test_finalize.py`, `### UPDATED python/tests/implement/test_step_7a.py`, and `### UPDATED python/tests/review/test_review_and_fix.py` mirroring `test_run_logs.py`: retarget imports and `monkeypatch.setattr`/`patch.object` to the module each production file resolves (`run_log_manifest`, `run_log_flush`, `run_log_batch`); keep only residual `run_logs` coverage in `test_run_logs.py`
  - From Cursor-dyn-Facade Binding Auditor: Add `### UPDATED: python/tests/review/test_review_and_fix.py`; patch `review_and_fix.run_log_batch.append_execution_issue` (or the exact alias step_7a-style imports use)
  - From Codex-dyn-Facade Binding Auditor: Add these test files to the plan and repoint every reference and monkeypatch to the exact binding resolved by the migrated caller.


### FINDING_6: Avoid re-export leakage from residual run_logs helpers
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: Residual `run_logs.py` helpers may continue using bare imports that recreate removed facade attributes, undermining the intended facade shrink.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify shrinking `run_logs` to import `run_log_batch`/`run_log_manifest`/`run_log_commit`/`run_log_flush` as modules and call qualified attributes only; drop bare re-export imports entirely


### FINDING_2: Implement-dispatch test still depends on removed facade export
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `test_implement_dispatch.py` still calls `run_logs.append_execution_issue`; removing that re-export will cause the warning-normalization regression test to fail with `AttributeError`, despite production dispatch code not using the facade.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: python/tests/implement/test_implement_dispatch.py: import append_execution_issue from larch.report.run_log_batch (or call run_log_batch.append_execution_issue) inside fake_invoke; drop the unused run_logs import if nothing else needs it; include this module in the focused pytest list or run make py-test because CI executes the full suite
  - From Cursor-Pragmatic: Add `### UPDATED: python/tests/implement/test_implement_dispatch.py`: replace the `run_logs` import/call with `run_log_batch.append_execution_issue`, and include `python3 -m pytest python/tests/implement/test_implement_dispatch.py::test_append_warning_normalizes_plain_text_for_final_summary` in the focused test list **1. [correctness] `python/tests/implement/test_implement_dispatch.py:46-8215`** The plan lists consumer-binding retargets for `test_finalize.py`, `test_step_7a.py`, and `test_review_and_fix.py`, but not `test_implement_dispatch.py`. That file imports `run_logs` at line 46 and its `fake_invoke` helper calls `run_logs.append_execution_issue` at line 8213. Once `append_execution_issue` is no longer re-exported from the shrunk facade, `test_append_warning_normalizes_plain_text_for_final_summary` breaks even though `implement_dispatch` production code does not use the facade. **Suggested revision:** Add an `### UPDATED:` entry for `python/tests/implement/test_implement_dispatch.py` to call `run_log_batch.append_execution_issue` instead, and add that test (or the file) to the focused pytest list in the testing strategy.

