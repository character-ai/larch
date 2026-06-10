### OOS_11: [OUT_OF_SCOPE] risk-integration: new harnesses lack complete agent-lint and documentation registration
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New Makefile-only harnesses and `test-step-8-ship` are missing parts of the repo’s harness metadata surface: agent-lint exclusions, a sibling `.md` contract, and/or `docs/linting.md` discoverability. This can make `make agent-lint` fail and leave contributors without the expected harness contract documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### OOS_12: [OUT_OF_SCOPE] risk-integration: telemetry rehydration coverage is incomplete across commit/check wrappers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The harnesses do not adequately assert session-env telemetry rehydration for the commit wrappers and related telemetry-owning scripts after inline Step 4/7 fences were removed. Regressions in `read_session_key` or wrapper migration could silently break per-run token/timing ledger attribution while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


