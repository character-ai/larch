### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/state/finalize.py:30-30; python/larch/implement/step_7a.py:22-22; python/larch/review/review_and_fix.py:34-34
- **Concern**: Require owner-module attributes on consumer modules for monkeypatch targets. Scenario: The plan retargets test_finalize.py, test_step_7a.py, and test_review_and_fix.py to patch finalize.run_log_manifest / finalize.run_log_commit, step_7a.run_log_flush (and related owner bindings), and review_and_fix.run_log_batch. The production sections for those files only say to import symbols from owner modules or route calls through run_log_batch/run_log_flush. A direct-symbol import (for example from larch.report.run_log_manifest import effective_run_id) leaves no consumer-module attribute, so monkeypatch.setattr on the named paths raises AttributeError or never intercepts the call path.
- **Proposed resolution**: For each consumer listed above, add an explicit plan step: bind owner modules on the consumer (from larch.report import run_log_manifest, run_log_commit, run_log_flush, run_log_batch as applicable) and call only through those attributes (run_log_manifest.effective_run_id, run_log_flush.flush_logs_pre, run_log_batch.append_execution_issue). Align with G-Py-14 by keeping typed fakes on the patched consumer binding.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/implement/test_implement_dispatch.py:8213-8215
- **Concern**: Direct test helper still calls run_logs.append_execution_issue after the facade shrink. Scenario: The #5219 warning-normalization test's fake_invoke delegates to run_logs.append_execution_issue at runtime; piece 4 removes that re-export, so the helper raises AttributeError even though implement_dispatch production code never imported run_logs
- **Proposed resolution**: Add ### UPDATED: python/tests/implement/test_implement_dispatch.py: import append_execution_issue from larch.report.run_log_batch (or call run_log_batch.append_execution_issue) inside fake_invoke; drop the unused run_logs import if nothing else needs it; include this module in the focused pytest list or run make py-test because CI executes the full suite



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/implement/test_implement_dispatch.py:46-8215
- **Concern**: Plan omits `test_implement_dispatch.py` while it still imports `run_logs` and calls `run_logs.append_execution_issue` in `test_append_warning_normalizes_plain_text_for_final_summary`. Scenario: After `append_execution_issue` is dropped from the shrunk `run_logs` facade, that regression test fails at setup with `AttributeError` even though dispatch production code never touches the facade
- **Proposed resolution**: Add `### UPDATED: python/tests/implement/test_implement_dispatch.py`: replace the `run_logs` import/call with `run_log_batch.append_execution_issue`, and include `python3 -m pytest python/tests/implement/test_implement_dispatch.py::test_append_warning_normalizes_plain_text_for_final_summary` in the focused test list **1. [correctness] `python/tests/implement/test_implement_dispatch.py:46-8215`** The plan lists consumer-binding retargets for `test_finalize.py`, `test_step_7a.py`, and `test_review_and_fix.py`, but not `test_implement_dispatch.py`. That file imports `run_logs` at line 46 and its `fake_invoke` helper calls `run_logs.append_execution_issue` at line 8213. Once `append_execution_issue` is no longer re-exported from the shrunk facade, `test_append_warning_normalizes_plain_text_for_final_summary` breaks even though `implement_dispatch` production code does not use the facade. **Suggested revision:** Add an `### UPDATED:` entry for `python/tests/implement/test_implement_dispatch.py` to call `run_log_batch.append_execution_issue` instead, and add that test (or the file) to the focused pytest list in the testing strategy.



