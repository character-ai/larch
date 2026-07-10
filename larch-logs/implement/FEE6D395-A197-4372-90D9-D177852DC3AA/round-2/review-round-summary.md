# Review Round 2

- Mode: `diff`
- 9 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Structural `head-changed-after-dispatch` outcomes stall instead of requiring main-agent recovery
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-waterfall-state
- **Severity**: major
- **Concern**: `head-changed-after-dispatch` is mapped to a distinct `head-changed` loop status, but `_repair_loop_action()` has no corresponding recovery branch. Structural integrity failures can therefore terminate as `stall` instead of taking the reserved `main-agent-edit` path, and available ledger or stderr evidence may be lost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-waterfall-state: Treat `head-changed-after-dispatch` like other structural integrity failures: set `loop.status="main-agent-required"` (or add an explicit `_repair_loop_action()` branch that returns `main-agent-edit` for `head-changed` on pre-ship sites), and preserve any available `tier_ledger_path` / stderr evidence on the loop result.


### FINDING_2: Structural dispatch failures are routed to stall instead of main-agent recovery
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: Repair-loop `dispatch-failed` outcomes, including redaction or integrity failures, default to `stall` even when the failure is structural and should be handled through the main-agent-required path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_3: Categorized execution-issue evidence is incomplete for authentication, preflight, missing-binary, and anomalous exits
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-waterfall-state
- **Severity**: major
- **Concern**: Known authentication, preflight, missing-binary, and runtime-launch failures collapse into `launcher-failure`; execution-issue recording is conditional on nonzero launcher status; and a missing `.done` sidecar can be treated as exit `0`. The ledger and run-log surfaces therefore cannot reliably distinguish anomalous outcomes or preserve evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Classify known authentication, preflight, and missing-binary outcomes before recording the ledger row and execution issue.
  - From codex-specialist-edge-cases: Return or derive a bounded auth/preflight classification and persist it in the tier ledger and execution issue.
  - From dyn-dyn-waterfall-state: Classify outcomes before ledger write (`timeout`, `missing-binary`, `authentication-preflight`, `launcher-failure`, `no-op`) from launcher metadata/preflight results, always append a bounded execution-issue row for anomalous classes, and stop treating a missing `.done` file as exit `0` when launcher stdout lacks `LAUNCHER_EXIT=`.


### FINDING_4: Ledger initialization and append failures bypass fail-closed repair handling
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Errors while initializing or appending the tier ledger can escape from the dispatch boundary, preventing the next-tier decision, execution-issue recording, and terminal result envelope from being produced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Catch initialization and append failures at the dispatch boundary, record bounded execution-issue evidence where possible, and return a structural failed FixOutcome.


### FINDING_5: Post-initialization structural returns can omit `tier_ledger_path`
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Structural failures after ledger initialization may return a `FixOutcome` without `tier_ledger_path`, even though the ledger contains the attempt evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Route all returns after ledger initialization through a helper that preserves `tier_ledger_path`.


### FINDING_6: Stderr-tail paths can expose unredacted launcher output
- **Reviewer(s)**: codex-specialist-edge-cases, dyn-dyn-waterfall-state
- **Severity**: major
- **Concern**: `_coder_stderr_tail()` and repair-loop output can retain or emit raw stderr-tail paths, allowing timed-out or failed tiers to expose unredacted vendor output through `STDERR_TAIL_PATH`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Redact and validate stderr tails before retaining or emitting paths; emit only safe redacted regular-file paths and fail closed on redaction failure.
  - From dyn-dyn-waterfall-state: Redact stderr-tail artifacts the same way as attempt logs (write a bounded `.redacted` sibling, validate containment, and emit only the redacted path in `STDERR_TAIL_PATH` / `FixOutcome.stderr_tail_path`).


### FINDING_8: Focused implementation tests are failing and do not verify the waterfall state machine
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-waterfall-state
- **Severity**: major
- **Concern**: The focused `test_checks.py` module reports 25 failures, including tier dispatch, repair-loop routing, snapshot handling, and ship-pr handoff cases. Stale stub git sequences and obsolete routing expectations prevent CI from validating reservation accounting, tier advancement, stall envelopes, evidence propagation, and handoffs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update stubs expectations and add missing plan-required coverage until suite passes.
  - From cursor-specialist-edge-cases: Update StubRunner git sequences for per-attempt snapshots, fix timeout and routing expectations, and add the plan-listed coverage cases.
  - From cursor-specialist-testing: Update stub sequences and repair-loop assertions then run the full `test_checks` module to green.
  - From dyn-dyn-waterfall-state: Refresh stub call sequences for the new baseline/attempt snapshot contract, replace obsolete main-agent-edit expectations with stall/named-reason envelopes, add integration tests for `lint-fix-budget-exhausted`, execution-issue emission, isolated attempt directories, and ship-pr `main-agent-required` handoff, and keep `test_checks.py` green before merge.


### FINDING_9: Plan-required regression coverage for timeout, budgets, ledgers, execution issues, envelopes, and ship-pr handoffs is incomplete
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The plan-required test matrix is largely absent or stale. Timeout configuration, lane reservation and budget exhaustion, final-tier eligibility, tier-ledger rows, execution issues, isolated artifacts, terminal stall envelopes, and ship-pr preservation are not comprehensively asserted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Implement the full plan test matrix with faithful git stubs and integration assertions on checks_repair_loop_main stdout.
  - From cursor-specialist-testing: Add plan-listed targeted tests and assert config.FIXER_LANE_TIMEOUT_SEC in argv builders.
  - From codex-specialist-testing: Assert str(config.FIXER_LANE_TIMEOUT_SEC) and add equivalent Claude and Cursor argv coverage.
  - From codex-specialist-testing: Add focused tests for every listed plan-required reservation, routing, ledger, isolation, execution-issue, and ship-pr scenario.


### FINDING_10: Structural harnesses were not updated for the new stall contract
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: The plan-required structure and fence-shape harness changes are missing, so CI does not mechanically prevent reintroducing pre-ship exhaustion-to-main-agent-edit prose or dropping stall and tier-ledger evidence keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add plan-specified require/forbid checks for stall tokens, tier-ledger evidence, and ship-pr carve-out; update test-implement-fence-shape.sh similarly.
  - From cursor-specialist-testing: Add the plan-specified structure and fence-shape assertions for the new pre-ship stall contract.
