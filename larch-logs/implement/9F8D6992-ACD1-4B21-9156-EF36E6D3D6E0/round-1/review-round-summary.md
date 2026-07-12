# Review Round 1

- Mode: `diff`
- 6 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Codex probe test doubles still return integers
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-probe-cache
- **Severity**: major
- **Concern**: `_run_codex_probes()` now dereferences `.rc` on `CodexProbeResult`, but many existing test mocks still return bare integers, causing `AttributeError` and preventing retry behavior from being tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update all _run_one_codex_probe monkeypatches to return CodexProbeResult (or add a test-only adapter if you must keep int mocks).
  - From codex-specialist-correctness: Update all _run_one_codex_probe fakes to return CodexProbeResult or add a compatibility adapter.
  - From cursor-specialist-edge-cases: Wrap mocked return codes as CodexProbeResult(rc) across all sibling mocks; fix the new test healthy leg at line 6119 the same way.
  - From codex-specialist-edge-cases: Update all affected doubles to return CodexProbeResult or preserve a narrow compatibility adapter.
  - From cursor-specialist-testing: Update all _run_one_codex_probe monkeypatches to return CodexProbeResult(rc) and rerun the check_reviewers shard
  - From codex-specialist-testing: Return CodexProbeResult from all fakes or normalize legacy integer results.
  - From dyn-dyn-probe-cache: Update every _run_one_codex_probe monkeypatch to return agents.CodexProbeResult(rc) (or CodexProbeResult(_AUTH_RETRY_RC) for auth paths, with gate_detail= when needed), and add one integration test that asserts degraded_tools_result() renders the upgrade string from a real gate handoff.


### FINDING_4: Invalid UTF-8 in gate-detail records can crash readers
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: minor
- **Concern**: Invalid UTF-8 in a gate-detail handoff raises `UnicodeDecodeError` instead of producing the generic probe-failed explanation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Catch UnicodeDecodeError and return no detail.


### FINDING_5: Failed gate-detail clearing can expose stale advice
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: minor
- **Concern**: If clearing a stale gate-detail record fails, later status output can continue showing obsolete CLI-upgrade advice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Record clear failure as invalidation or make readers reject records after unsuccessful clear.


### FINDING_9: Unrelated Codex runtime failures lack regression coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: No test verifies that a non-gate exit 99 remains `codex-runtime-failure` after retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add clean-tree Step 2 test with non-gate stderr asserting STATUS=bailed REASON=codex-runtime-failure and two launcher calls


### FINDING_11: Gate-detail handoff validation lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Expired, identity-mismatched, or malformed gate-detail handoffs are not covered by tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add unit tests for expired mtime identity mismatch and malformed JSON on gate-detail files


### FINDING_12: Salvage-before-gate precedence lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: No test protects the precedence rule that a salvageable manifest wins over gate diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add Step 2 test with gate diagnostics and salvageable manifest asserting salvage path wins
