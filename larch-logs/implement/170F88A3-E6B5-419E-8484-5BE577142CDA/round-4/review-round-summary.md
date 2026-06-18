# Review Round 4

- Mode: `diff`
- 4 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: correctness: python/closeout.py:46-54,157-161
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 16 uses local _read_key for LARCH_RUN_ID instead of session read-key empty-value/default semantics. When session-env.sh has LARCH_RUN_ID= blank but RUN_ID is set in the environment, write-rejected is invoked with --run-id "" and rejected-findings batches miss the real run id. Rehydrate via python/cli.py session read-key (or treat blank values as missing and apply the env default like read_key_main).
- **Suggested revision**: Address the concern above.


### FINDING_14: **risk-integration** `python/closeout.py:278-317` — `step_16_17` wraps both `step_16` and `step_17` in `contextlib.suppress(Exception)`, so an unexpected Python exception (for example a `TypeError`, import failure, or corrupted tmpdir read) is swallowed: the wrapper still exits `0`, no `run-log append-failure` Tool Failure is written, summary markers are skipped, and the operator gets no `execution-issues.md` breadcrumb. That is weaker than the retired Bash path, where `step-17.sh` failures were captured via `STEP17_RC=$?` and Step 17’s own `append_step17_failure` hook. **Suggested fix:** Remove the blanket `suppress(Exception)` around `step_16` and `step_17`; rely on their integer return codes, or catch only narrow I/O/subprocess errors and on any other exception call `_append_failure` (category `Tool Failures`) before returning `0` from the composed wrapper.
- **Reviewer**: dyn-closeout-flow-output.txt
- **Concern**: - **risk-integration** `python/closeout.py:278-317` — `step_16_17` wraps both `step_16` and `step_17` in `contextlib.suppress(Exception)`, so an unexpected Python exception (for example a `TypeError`, import failure, or corrupted tmpdir read) is swallowed: the wrapper still exits `0`, no `run-log append-failure` Tool Failure is written, summary markers are skipped, and the operator gets no `execution-issues.md` breadcrumb. That is weaker than the retired Bash path, where `step-17.sh` failures were captured via `STEP17_RC=$?` and Step 17’s own `append_step17_failure` hook. **Suggested fix:** Remove the blanket `suppress(Exception)` around `step_16` and `step_17`; rely on their integer return codes, or catch only narrow I/O/subprocess errors and on any other exception call `_append_failure` (category `Tool Failures`) before returning `0` from the composed wrapper.
- **Suggested revision**: Address the concern above.


### FINDING_2: risk-integration: python/checks.py:503-504
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] checks.py _DIRECT_TARGET_RULES omits closeout.py and final_report.py harness mappings required by the plan. Edits to closeout/final_report can pass relevant-checks without running test-step-16-17 or test-write-final-report, letting Step 17/final-report regressions slip through. Add closeout.py→test_closeout.py and final_report.py→test_final_report.py entries mapping to the Makefile harness targets.
- **Suggested revision**: Address the concern above.


### FINDING_7: risk-integration: python/checks.py:503-504
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] closeout.py and final_report.py lack explicit _DIRECT_TARGET_RULES rows though the plan requires checks.py updates for new modules A closeout-only edit during /implement runs full py-test via the python/*.py wildcard but skips targeted test-step-16-17 and test-write-final-report harnesses Add (python/closeout.py, python/test_closeout.py) -> test-step-16-17 and (python/final_report.py, python/test_final_report.py) -> test-write-final-report / test-step-18b-final-report rows matching preflight/finalize
- **Suggested revision**: Address the concern above.


