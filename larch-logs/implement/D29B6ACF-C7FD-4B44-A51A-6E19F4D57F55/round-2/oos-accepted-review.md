### OOS_1: [OUT_OF_SCOPE] `docs/linting.md` advertises removed targets and retired script names
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Linting docs still reference a removed `false-positive-keywords` target and retired voting script names. Operators following the docs can hit missing Makefile rules or stale script guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Deleted step-telemetry scripts leave stale Makefile and lint references
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The step-telemetry cleanup deleted scripts while leaving stale Makefile and `agent-lint.toml` references. This can make `make test-step-telemetry-mark` succeed without running the deleted harness or make lint/sync validation fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


