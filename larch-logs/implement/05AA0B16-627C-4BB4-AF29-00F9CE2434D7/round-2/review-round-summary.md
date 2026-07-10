# Review Round 2

- Mode: `diff`
- 9 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: stale prior-run pointer remains visible during fresh startup
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Both `/design` Step 0 and implement startup leave the previous run’s current progress pointer active while session setup, environment writing, and reviewer probing proceed. A prior run can therefore remain visible in the statusline until the new run is activated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_2: design environment is written before the refreshed reviewer probe
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Design Step 0 writes `source-env.sh` before the separate `check-reviewers` probe, allowing persisted tool-availability values to disagree with the values used for degraded-tools routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_3: cancelled or failed clarify bypasses run-matched cleanup
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The cancelled-clarify and failed-clarify fast paths return before run-matched cleanup. A cancelled run with an existing final summary and no live background job can leave its current pointer active and render stale status in a later session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_4: Step 6 does not guard against all same-run live background jobs
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Step 6 checks only the Step 5c registry entry before deactivation. A live in-budget background job for the same run under another step can be missed, allowing current progress to be cleared while work continues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_5: run-aware writers fail to resolve identity from persisted session state
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Review, CI, ship, and timing writers resolve the run ID only from the environment rather than from persisted `session-env.sh` in `IMPLEMENT_TMPDIR`. Background-job children or custom effective run IDs that are not exported can silently lose progress breadcrumbs and timing marks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_6: progress lifecycle and cross-run race coverage is incomplete
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Required regression coverage is missing for ownership mismatches, A/B interleaving, captured-reset races, run-scoped liveness, unrelated live jobs, stale-writer isolation, and related progress lifecycle behavior. Regressions could allow late cleanup or SessionStart to clear a newer run, suppress stale status incorrectly, or contaminate another run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_7: Step 0 abort cleanup lacks pointer-clearing assertions
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Step 0 abort-cleanup tests do not assert that the current progress pointer is cleared, leaving a regression path where operator aborts leave stale current state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_14: custom persisted run IDs lack abandoned-job recovery coverage
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: There is no regression test proving that abandoned-job recovery uses a custom `LARCH_RUN_ID` persisted in session state rather than falling back to a tmpdir-hash registry key.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


### FINDING_15: finalization derives the progress clone from ambient cwd
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: Teardown liveness checks and deactivation derive the progress clone from the ambient working directory. Finalization invoked outside the consumer clone can therefore inspect or clear the wrong pointer and leave the real run stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
