### FINDING_1:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-run-external-agent.sh (planned accept case)
- **Concern**: Accept test must mirror launcher fd2 redirect, not only pass --stderr-sink. Scenario: Plan requires a failing default-mode child whose stderr is in the sink, but the harness helper run_subject always sends wrapper stderr to RUN_STDERR. Passing --stderr-sink alone leaves the sink empty while wrapper stderr goes elsewhere; the test can pass via .sidecar/.diag fallback and miss the custom-sink contract.
- **Proposed resolution**: Invoke the wrapper with an explicit 2>sink redirect (same shape as launch-codex-implement.sh:324-338), e.g. "$WRAPPER" ... --stderr-sink "$sink" ... 2>"$sink" -- bash -c '...'; assert .stderr-tail is sourced from agent lines in $sink.

