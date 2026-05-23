### FINDING_1: Regression test can green if file-level `LARCH_EXECUTION_ISSUES_LOG` unset is removed while inner `bash -c` still unsets before `exec`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The leak/regression case runs `aggregate-findings` under a subprocess that unsets `LARCH_EXECUTION_ISSUES_LOG` before `exec`, so the SUT may not see a deliberately exported sentinel the way a top-level harness invocation would. Removing or weakening only the file-level unset prelude (e.g. lines 7–8) can still leave the case green while real harness shapes leak again; coverage is weaker than “inherited env visible to aggregate-findings” / plan step 4 wording implies unless supplemented (e.g. negative control without inner unset, whole-run guard, or documenting that the case pins only part of the contract).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Add a whole-script or no-inner-unset subprocess assertion that fails when entrypoint unset is removed, or document that this case only pins the duplicated prelude string.
  - From cursor-specialist-edge-cases-output.txt: Invoke AGG with env LARCH set and no inner unset plus assert artifacts under --review-tmpdir only, or spawn a subshell that only applies the harness entry unset (not a full inner prelude) so the test fails if entry unset is removed.


### FINDING_2: Sentinel/dispatch assertions do not prove `append_warning` wrote into execution-issues under `--review-tmpdir`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The regression asserts an empty sentinel and `REASON=dispatch-failed` but not that `execution-issues` under `--review-tmpdir` received an aggregator warning line; `append_warning` could regress to a no-op while dispatch KV output still looks failed and the sentinel-oriented test still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


