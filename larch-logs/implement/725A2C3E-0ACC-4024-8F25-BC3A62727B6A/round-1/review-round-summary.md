# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Stale preserved terminal state blocks Tier-A failure report after failed publish
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-design-report-integrity-output.txt, dyn-publish-preservation-output.txt
- **Severity**: important
- **Concern**: `|| true` on the failed-publish `stage_design_terminal_state` call lets `design-publish.sh` finish with `SUMMARY_OUTCOME=failed-publish` when staging returns `STAGED=false` because an older terminal state is preserved (e.g. `failed-plan-write` from a prior attempt in the same `DESIGN_TMPDIR` on resume). The new `ROOT_CAUSE_HINT=environment` is not written to `design-failure-terminal-state.env`. `design-failure-report.sh` then sees `FAILURE_OUTCOME` / `SUMMARY_OUTCOME` mismatch, hits `terminal-state-outcome-mismatch`, and falls back to chat-only output instead of filing the Tier-A report with `verdict=environment` and Run ID from `source-env.sh`, even though publish teardown and `final-summary.md` may succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reconcile preserved vs live outcome for reporting, or upgrade/clear stale terminal state before failed-publish staging; add design-failure-report integration test on preserved-state fixture
  - From cursor-specialist-edge-cases-output.txt: Clear or supersede `design-failure-terminal-state.env` when plan-block write succeeds (or when entering the publish path after recovery), or teach preservation to merge upgrade fields (`ROOT_CAUSE_HINT`, `FAILURE_OUTCOME`) when the new outcome is strictly later in the publish pipeline; add a harness that runs `design-failure-report.sh` on the preserved-state scenario.
  - From dyn-design-report-integrity-output.txt: On `STAGED=false`, persist the intended hint/outcome in a sidecar (for example `.design-publish-result.env` or `execution-issues.md`) and have `design-failure-report.sh` consult it when the terminal file was not updated.
  - From dyn-publish-preservation-output.txt: When `stage_design_terminal_state` logs `STAGED=false` on the publish-failure path, either align `SUMMARY_OUTCOME`/report `--outcome` with the preserved `FAILURE_OUTCOME`, merge compatible fields such as `ROOT_CAUSE_HINT` into the preserved state, or emit an explicit operator-visible warning that auto-report will mismatch and treat the preserved terminal state as authoritative.


### FINDING_6: `ROOT_CAUSE_HINT=environment` not verified on design-publish failed-publish call path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `ROOT_CAUSE_HINT=environment` is only tested via direct staging in `test-design-failure-report.sh` D6b, not through `design-publish.sh`'s failed-publish path. Removing the environment argument from `design-publish.sh`'s failed-publish `stage_design_terminal_state` call would not fail CI; acceptance that `verdict=environment` reaches the public report when staged on publish failure is unverified on the production call path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a test-design-publish integration case: fresh tmpdir, publish stub fails, assert design-failure-terminal-state.env contains ROOT_CAUSE_HINT=environment; optionally chain design-failure-report.sh and assert verdict=environment in the public artifact.


