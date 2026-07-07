# Review Round 2

- Mode: `diff`
- 5 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_3: Missing main-health sidecar can silently skip merge gates
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Missing `main-health.env` or swallowed bootstrap copy failures can leave no durable probe evidence, so pre-merge and post-merge default-branch CI checks are skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Fail closed on missing durable main-health evidence whenever merge mode is enabled.
  - From codex-specialist-correctness: Fail closed when `main-health.env` is missing on merge paths, or write a verified error sidecar during bootstrap.
  - From cursor-specialist-edge-cases: Fail closed when preflight ran but `main-health.env` is missing; copy probe markers and surface bootstrap copy errors.
  - From codex-specialist-edge-cases: Treat `preflight-tmpdir.env` without `main-health.env` as a stall, or copy a durable probe sentinel and fail closed when the sidecar is missing.
  - From cursor-specialist-testing: Fail bootstrap closed write degraded `main-health.env` with `MAIN_CI_STATUS=error` or copy probe artifacts so gates stall; add OSError copy test.
  - From codex-specialist-testing: Fail closed whenever `main-health.env` is missing for merge/post-merge paths, or materialize a durable probe marker that cannot be lost silently; add a test for missing `main-health.env` with no stdout/stderr sidecar.


### FINDING_9: Pre-merge main-health gate is not commit-scoped
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The pre-merge main-health gate reads the current default branch instead of the exact base SHA, so a later success can be mistaken for the target commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Fetch and resolve `origin/<base_ref>`, pass that SHA as `head_sha`, and treat no matching run as pending/error.


### FINDING_10: Post-merge watch tracks origin/main instead of the merged SHA
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: The post-merge watch validates refreshed `origin/main` instead of the actual merged PR commit SHA, so a concurrent merge can make it validate an unrelated green push run while this merge's run is red.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Read merged commit from PR merge metadata and pass it to `wait_main_health`; use `origin/main` only as fallback.
  - From codex-specialist-correctness: Capture and persist the actual merged commit SHA from merge metadata, then wait on that SHA.
  - From codex-specialist-edge-cases: Capture and persist the actual merged commit SHA from merge metadata, then wait on that SHA.
  - From codex-specialist-testing: Persist the actual merged commit SHA from merge metadata or PR data, then pass that exact SHA to `wait_main_health`; add a regression test where `origin/main` advances to a different SHA before the watch.


### FINDING_11: Original-branch write guard can be bypassed
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The original-branch write guard depends on `SHIP_PR_STATE_FILE`, but the state path can be absent from the environment, so emergency repair can still commit or push on the forbidden original branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Export `SHIP_PR_STATE_FILE` from `ctx.state_file` or fall back to `$IMPLEMENT_TMPDIR/ship-pr-state.sh`.
  - From cursor-specialist-edge-cases: Enforce the flag in `stage_and_push` and emergency-repair commit paths before any git write.
  - From codex-specialist-edge-cases: Export `SHIP_PR_STATE_FILE` from the parsed `RunContext` or pass the state path directly into git and push guard APIs.


### FINDING_12: Repair handoff fields are not serialized
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Main-health handoff fields and repair markers cannot reach route-exit JSON, so repaired failures lose the matching base SHA and can re-enter `main-ci-fail`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Add ShipResult fields for main-health and emergency-repair data, populate them at gates, and serialize them.
  - From codex-specialist-edge-cases: Carry `MAIN_HEALTH_HEAD_SHA` into the handoff and write `MAIN_HEALTH_REPAIR_*` fields after the repair commit before relaunch.


