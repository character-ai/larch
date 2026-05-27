### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Wrapper progress moved to stderr without documented contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `run-external-agent.sh` now emits wrapper progress/diagnostics to stderr, but the behavior is outside the declared plan scope and lacks documentation or harness coverage. Callers that capture stdout may mis-parse if the contract changes again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_11: Unexplained negotiation lock delay increase
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `LARCH_EXTERNAL_SERIAL_LOCK_DELAY` increased from 1 to 5 on the negotiation success path, adding several seconds to lint runs without an inline rationale or linked flake explanation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Missing ledger diagnostic on empty or unparseable Codex events
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `external_launcher_record_usage_from_events` returns success without writing a ledger row when events JSONL is missing, empty, or unparseable. A timeout or early kill could still incur API usage while downstream token ledgers show no Codex row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Duplicated Codex telemetry invocation blocks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Codex telemetry invocation logic is duplicated across `lint-fix-loop.sh`, `run-negotiation-round.sh`, and `review-and-fix.sh`, increasing drift risk for future argv, sidecar, or telemetry-order changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Duplicated synthetic Codex stub fixture logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Synthetic JSONL and `--output-last-message` stub logic is duplicated across three harnesses, so fixture shape changes require coordinated edits and are easy to miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Python timeout helper in get-issue-state test
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-get-issue-state.sh` uses a Python subprocess timeout helper instead of the plan-specified simple timeout approach, adding complexity and a `python3` dependency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Fragile awk/eval extraction of round_artifact_included
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `assert_round_artifact_included` extracts a nested function from `larch-log.sh` with `awk` and `eval`; formatting changes could break the test opaquely or exercise the wrong body.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Inconsistent get-issue-state error emission style
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/get-issue-state.sh` uses inconsistent error-emission style between arity and flag-looking guards, creating maintainability noise without a claimed behavioral bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

