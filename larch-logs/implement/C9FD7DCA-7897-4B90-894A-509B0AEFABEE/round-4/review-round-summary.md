# Review Round 4

- Mode: `diff`
- 9 accepted, 15 rejected (2 neutral)

## Accepted Findings

### FINDING_11: Dispatch-panel prune-filter regression tests are incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `dispatch-panel.sh` lacks plan-required tests for fail-open rc, `PRUNE_FAIL_OPEN`, advisory WARN, out-of-window/window-normalization, normal success, and `PANEL_PRUNED_EMPTY` env-file behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_12: review-core tests do not assert prune env files on all flush paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests only assert prune env files for panel-pruned-empty, so removing `ensure_prune_decision_env` or `ensure_prune_nit_env` on other `flush_round_log` branches would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: review-and-fix ledger flush/failure tests are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no test for reviewer-prune-ledger `larch-log` batch writes or `append_log_write_failure` on write failure, so implement run-root audit regressions could be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_18: Concise design publish can leave stale excluded artifacts
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Concise publish skips excluded artifacts but does not remove stale excluded files already present in reused destinations, so raw findings/transcripts/diffs can remain committed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_25: Malformed round-meta can hide valid reviewer signals
- **Reviewer(s)**: dyn-ns-retry-orphan-dedup-output.txt
- **Severity**: important
- **Concern**: `_audit_reviewer_signals_jq` gates on any non-empty `reviewer_signals` but later slurps all round metadata together; one malformed `round-meta.json` can make extraction empty and emit `skip`, missing valid NS-retry signals from other rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ns-retry-orphan-dedup-output.txt: Address the concern above.


### FINDING_3: Failed prune-filter output can still trigger pruned-empty early exit
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Review and design dispatchers trust `PANEL_PRUNED_EMPTY=true` even when the prune filter exits nonzero / `PRUNE_STATUS=failed`, allowing a failed filter to skip the full review panel while reporting success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_4: Empty prune ledgers are not repaired before reuse
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Existing 0-byte or header-invalid reviewer prune ledgers are not repaired in design or implement paths, so resumed runs can fail-open and lose pruning/audit data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_5: Fluff-analysis corpus smoke thresholds fail on current corpus
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The committed-corpus smoke test hard-codes thresholds that do not match the current checkout’s analyzer output, so the registered target fails when live `larch-logs` data is present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: Design terminal snapshot can clobber dispatch-written prune-decision.env
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Design panel dispatch output is not parsed on nonzero exits, and terminal snapshot rewriting can overwrite accurate dispatch-written `prune-decision.env` with default/skipped values, especially after pruning followed by panel failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


