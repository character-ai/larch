# Review Round 1

- Mode: `diff`
- 8 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Fresh replacement is blocked by stale dead registry entries
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-adapter-races
- **Severity**: major
- **Concern**: Explicit replacement and fresh-attempt paths reject proven-dead in-budget registry entries instead of clearing them before invalidating completed results and launching a replacement job.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-adapter-races: Address the concern above.


### FINDING_2: Session environment can override the validated plugin root
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Direct session-env paths can supply an attacker-controlled `CLAUDE_PLUGIN_ROOT`, redirecting wrapper CLI execution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_4: Clear-on-fresh removes the completion marker too early
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-adapter-races
- **Severity**: major
- **Concern**: The completion marker is cleared before final result checks and daemon startup succeed, so a late result or startup failure can leave completion state inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-adapter-races: Address the concern above.


### FINDING_5: Required Step 3 adapter behavioral tests are missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: CI lacks coverage for session-env launch, replacement resume, marker clearing, terminal routes, and merge-failure behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_6: Step 5c refusal-path fresh-attempt tests are missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Validator, size, and assessment refusal reruns lack coverage for replacement and merged result rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_7: Orchestrator-fence adapter assertions are missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Planned resume and marker-preservation assertions are absent from the named fence harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_8: Live-job preservation coverage is missing
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: There is no regression test ensuring `clear_on_fresh` preserves the completion marker and avoids launching when a live job can be reattached.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


### FINDING_9: Unsafe session-env coverage is missing
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: Wrong-PID and unsafe-symlink session-env sources lack regression coverage for `BGJOB_ERROR=session-env-unsafe`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
