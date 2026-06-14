# Review Round 2

- Mode: `diff`
- 1 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Missing pytest coverage for high-risk Step 2 dispatcher branches
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-dispatch-parity-output.txt
- **Severity**: important
- **Concern**: The branch retires `skills/implement/scripts/test-step2-dispatch.sh` in favor of `python/test_implement_dispatch.py`, but several dispatcher transitions the shell harness pinned are not ported. `python/implement_dispatch.py` implements paths such as `REASON=cap_hit`, Codex `LAUNCHER_EXIT` nonzero salvage (`WARN_CODEX_NONZERO_EXIT`), `dirty-state-after-timeout`, `wrapper-validation-failure`, `coder-mismatch-tmpdir-reuse`, corrupt resume-count → `manifest-schema-invalid`, `detached-head-prohibited`, `REASON=qa-loop-exceeded`, `SCOUT_CODER_MANIFEST` / `SCOUT_CODER_STATUS` stdout, and Step 7a.1 undeclared-path warnings — yet pytest does not assert them. A regression in retry, salvage, scout, warning, or bail routing can ship with green `py-test`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add pytest cases mirroring the deleted test-step2-dispatch.sh scenarios for each branch.
  - From cursor-specialist-testing-output.txt: Add stub-launcher test: LAUNCHER_EXIT!=0 + valid complete manifest → STATUS=complete + WARN_CODEX_NONZERO_EXIT=true + commit
  - From dyn-dispatch-parity-output.txt: Port the retired harness cases into `python/test_implement_dispatch.py` with the same KV assertions (including single `ORCHESTRATOR_EDIT_AUTHORITY` line and `allowed` iff `STATUS=claude_fallback`).


