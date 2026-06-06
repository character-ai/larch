### FINDING_2: Missing / stale collector outer-retry regression coverage for `launch-codex-exec`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Collector `launch-codex-exec` outer-retry behavior lacks adequate harness coverage. `test-collect-agent-retry.sh` case-s2 still expects a stale fail-closed string after collector message changes; there is no positive fixture asserting collector re-invokes `launch-codex-exec.sh` with preserved sandbox/add-dir metadata. `test-collect-agent-results.sh` also lacks the planned codex-exec outer-retry fixture, so metadata validation / `CMD_JSON` fallback regressions can reach `/research` collection paths undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add launch-codex-exec retry fixture; update expected error strings; assert launcher re-entry not raw codex exec.
  - From cursor-specialist-correctness-output.txt: Add fixture asserting collector re-invokes `launch-codex-exec.sh` with preserved sandbox/add-dir metadata.
  - From cursor-specialist-testing-output.txt: Update expected reason; add positive launch-codex-exec outer-retry fixture.
  - From cursor-specialist-testing-output.txt: Add happy-path and invalid-metadata fixtures to `test-collect-agent-retry.sh`.
  - From cursor-specialist-edge-cases-output.txt: Add planned codex-exec outer-retry harness fixture.
  - From cursor-specialist-plan-fidelity-output.txt: Add the plan-pinned fixtures to each harness and update sibling harness `.md` contracts.



### FINDING_3: `test-run-negotiation-round.sh` missing plan-mandated auth/cleanup coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Negotiation Codex auth wiring (`OPENAI_API_KEY` modes, login/trust, temp `CODEX_HOME` cleanup, auth-prep exit 2) is not covered by the harness per plan acceptance criteria, so negotiation auth regressions can ship without automated detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add stub-based auth mode and cleanup assertions mirroring check-reviewers patterns.
  - From cursor-specialist-testing-output.txt: Extend stub logging and add env-key/login/auth-failure fixtures.
  - From cursor-specialist-plan-fidelity-output.txt: Add the plan-pinned fixtures to each harness and update sibling harness `.md` contracts.



