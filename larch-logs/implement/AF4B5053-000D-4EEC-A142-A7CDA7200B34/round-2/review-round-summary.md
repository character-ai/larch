# Review Round 2

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Step 5 resume launcher can reuse stale result env or spawn duplicate bgjobs
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-plan-fidelity-forced
- **Severity**: major
- **Concern**: Step 5 resume launches can pick up a stale `implement-step5-resume.result.env` or start a duplicate daemon because the launcher lacks live-registry rejoin and stale result-env cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-plan-fidelity-forced: Address the concern above.


### FINDING_2: Step 6 entry launcher can reuse stale result env or spawn duplicate bgjobs
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-plan-fidelity-forced
- **Severity**: major
- **Concern**: Step 6 launcher always starts a fresh bgjob without registry rejoin or stale result-env cleanup, so re-entry can reuse an old `implement-step6-checks.result.env` or launch a duplicate checks daemon.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-plan-fidelity-forced: Address the concern above.

### FINDING_3 [OUT_OF_SCOPE]: Step 18 transcript recapture skips failed Step 7a runs
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Transcript recapture is suppressed by any Step 7a result-env file, even when the envelope is empty or failed, so `capture-transcript` can drop the session transcript from run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.

### FINDING_4 [OUT_OF_SCOPE]: Extinct-token harness misses acceptance tokens
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-plan-fidelity-forced
- **Severity**: major
- **Concern**: The extinct-token harness does not cover all acceptance #1 tokens, so retired guard/env/prose strings can return without CI failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-plan-fidelity-forced: Address the concern above.

### FINDING_5 [OUT_OF_SCOPE]: Step 6 in-flight check trusts any result env too early
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `_step6_in_flight` treats any result-env file as not in flight before checking registry liveness, so stale envs can trigger early Step 6 cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.

### FINDING_6 [OUT_OF_SCOPE]: Step 4 diagram gate still keys off `.completed/step-4`
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-plan-fidelity-forced
- **Severity**: major
- **Concern**: Diagram mode is still gated by `.completed/step-4` instead of the Step 4 bgjob result env, so Step 5b.5 can proceed on a sentinel touch rather than real completion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-plan-fidelity-forced: Address the concern above.


### FINDING_7: run-step-checks rejoin helper can delete a live registry
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The rejoin helper can unlink the registry while the daemon is still active, causing wrapper re-entry to start a duplicate checks bgjob and clobber its result env.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.

### FINDING_8 [OUT_OF_SCOPE]: Duplicate files keys in `lint-bg-wait-coverage`
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-plan-fidelity-forced
- **Severity**: minor
- **Concern**: The pre-commit config duplicates the `files` key for `lint-bg-wait-coverage`, making hook scope harder to audit and easier to drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-plan-fidelity-forced: Address the concern above.


