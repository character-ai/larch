# Review Round 5

- Mode: `diff`
- 5 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_1: correctness: Cursor model-args preflight bundle missing prompt sidecar and OUTER_LAUNCHER metadata
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Cursor model-args preflight writes preflight bundle without prompt sidecar or OUTER_LAUNCHER metadata, unlike Codex. Collector NS-retry on model-args failure lacks ${output}.prompt and outer meta; retry validation fails at collect-agent-results.sh prompt-sidecar check. Cursor vs Codex model-args preflight bundles are asymmetric despite plan requiring same contract, causing inconsistent retry/diagnostics behavior across vendors on configuration errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_12: security: retry-metadata injection via unvalidated risk and timing_task_kind in .meta
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_review_append_outer_meta` writes raw `risk` and `timing_task_kind` values into the line-oriented `.meta` retry contract. `--timing-task-kind` only rejects empty or flag-shaped values, so `ok\nOUTER_LAUNCHER_WORKDIR=/tmp` passes validation and is parsed later by `scripts/collect-agent-results.sh:584-587`, overriding the real workdir before retry launch at `scripts/collect-agent-results.sh:810-822`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Reject control characters for `--timing-task-kind` and `--risk`, coerce risk to `high|low` before writing metadata, and add a retry-metadata injection regression test.


### FINDING_5: risk-integration: argv reject paths lack parametrized integration test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan and launcher-argv-test-coverage rule require pytest for every argv reject path but only two CLI-level parser tests exist. _validate_meta_path or argparse regressions for unsafe paths, invalid caps, or timing-task-kind could ship without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_6: risk-integration: cap-hit contract lacks end-to-end CLI test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Cap-hit contract lacks end-to-end CLI test for --token-budget-cap and LARCH_TOKEN_BUDGET_CAP_REVIEW. launch_review_main could stop writing cap-hit sidecars or fail to skip vendor launch while unit helper tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: risk-integration: Codex --description-text prompt sidecar shape untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test asserts Codex --description-text writes full prompt sidecar instead of compact sentinel. Collector retry could receive wrong .prompt shape if description_text branch regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


