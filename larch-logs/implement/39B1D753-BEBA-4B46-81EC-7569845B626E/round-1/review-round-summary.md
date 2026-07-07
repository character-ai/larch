# Review Round 1

- Mode: `diff`
- 6 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: stale merged SHA can make post-merge health watch observe the wrong commit
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Post-merge watch can use a stale local view of `origin/main` or the feature branch instead of the actual merged commit, so `wait_main_health` may validate the wrong SHA and finalize while the real merged push run is red.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_4: ship_resume does not recognize emergency-repair or postmerge-push-watch
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing, dyn-dyn-main-health
- **Severity**: major
- **Concern**: `ship_resume.py` does not branch on `postmerge-push-watch`, `emergency-repair`, or `repair-shipped`, so interrupted post-merge repair sessions can resume as generic merged/postmerge runs and lose the state needed to finish the workflow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-main-health: Address the concern above.


### FINDING_5: missing main-health sidecar silently disables gates
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-main-health
- **Severity**: major
- **Concern**: If `$IMPLEMENT_TMPDIR/main-health.env` is absent, the pre-merge and post-merge main-health gates return early and silently skip the default-branch CI check; a swallowed bootstrap copy error can create exactly that missing sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-main-health: Address the concern above.


### FINDING_12: original-branch-forbidden is only a state flag, not a mechanical guard
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: `ORIGINAL_BRANCH_FORBIDDEN` is carried only in state; without a commit/push guard, emergency repair can still stage or push on the forbidden original feature branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_15: ship state validation tests are missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: `test_ship_state.py` is missing, so the new emergency-repair and repair-marker ship-state keys do not have dedicated write/patch/resume coverage or unknown-key rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_17: same-SHA flap detection can skip correlation when `headSha` is empty
- **Reviewer(s)**: dyn-dyn-main-health
- **Severity**: major
- **Concern**: If `gh` returns an empty `headSha` on the latest matching row, flap detection skips correlation entirely and can return `pass` on an ambiguous success row instead of treating it as `error`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-main-health: Address the concern above.
