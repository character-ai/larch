# Review Round 1

- Mode: `diff`
- 1 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Policy-rejection scan missing on normal child exit
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-lintfix-prompt
- **Severity**: important
- **Concern**: Policy-rejection detection runs only inside the poll-timeout branch (`subprocess.TimeoutExpired`), not after a normal non-zero child exit. If Codex logs a policy rejection to the events stream and exits before the next poll, no `POLICY_REJECTION` / `FAILURE_CLASS=policy-rejection` marker is written, `.diag` may lack the marker, `_policy_rejection_marker_present` may not short-circuit (it only inspects `.diag`, not events), and `_run_external_agent_with_auth_retries` can still treat the failure as auth or unclassified-empty and relaunch the same deterministic denial.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Run a final events (and optionally sidecar/diag) scan immediately after wait() returns; write markers and skip retries when matched.
  - From codex-specialist-correctness: Run the scan once more before returning any non-zero Codex exit, or move marker creation into a shared post-wait failure path.
  - From cursor-specialist-edge-cases: Run a final events-tail policy scan after `wait()` returns and/or teach `_policy_rejection_marker_present` to apply the same dual-family detector to `${output}.events.jsonl` before retry logic.
  - From codex-specialist-edge-cases: run the rejection scan on every non-zero exit path before auth classification, or factor it into a shared post-wait check that executes whether the child timed out or exited early.
  - From dyn-dyn-lintfix-prompt: After the wait loop returns (and before auth-retry classification), run one final `_codex_policy_rejection_excerpt` scan over the events file when `stdout_path` is set and append the same marker block when matched, regardless of whether exit was timeout-driven or a natural child exit.


