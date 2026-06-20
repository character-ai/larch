### OOS_9: [OUT_OF_SCOPE] Missing make target for pytest step5c matrix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The `design_lifecycle.py` direct-target rule runs `make test-design-step5c`, which after this PR is only thin bash delegation smoke. The rc-matrix orchestration moved to `pytest -k step5c` in `python/test_design_lifecycle.py`, but there is no dedicated make target for that subset (unlike `test-design-step-final-summary`, which runs `pytest -k step_final_summary`). Relevant-checks therefore exercise the wrapper stub, not the pytest matrix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a `make test-design-step5c-py` target and include it in the `design_lifecycle.py` direct-target rule so relevant-checks exercise the pytest matrix, not only the wrapper stub.


### OOS_10: [OUT_OF_SCOPE] No test for read_result_env failure after continuing publish rc
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-scope-output.txt
- **Severity**: important
- **Concern**: No test covers the `rre_rc != 0` abort path when `read_result_env_main` fails after `publish_core` returns a continuing rc (`0`/`1`/`3`/`4`), even though `step5c_core` documents returning `1` with the unreadable-result-env warning. Current tests cover happy stdout parsing and rc `1`/`3`/`4` success paths only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a test with corrupt/empty captured publish stdout so `read_result_env_main` fails and assert rc `1` plus the diagnostic.
  - From dyn-harness-scope-output.txt: Add a test where `publish_core` returns `0` but captured stdout lacks allowed keys (or monkeypatch `read_result_env_main` to return non-zero) and assert `step5c_core` exits `1`, emits the unreadable-result-env warning, and still writes `.completed/step-5c-terminal`.


