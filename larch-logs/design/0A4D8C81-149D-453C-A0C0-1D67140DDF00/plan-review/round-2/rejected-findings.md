### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:59 (plan _emit_round_timing_row)
- **Concern**: Rejected-count grep uses a trailing colon on FINDING_N headings. Scenario: Plan/_emit uses `^### \[Plan Review\] FINDING_[0-9]+:` but tally writes `### [Plan Review] FINDING_N` (no colon); per-round `rejected` stays 0 in JSON/run logs while tally shows rejections
- **Proposed resolution**: larch-logs/design/*/rejected-findings.md:1; skills/design/scripts/tally-plan-review.sh:499 Use `grep -cE '^### \[Plan Review\] FINDING_[0-9]+'` (no colon); align test-timing-report fixtures and docs with the same pattern


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-ledger-contract, Cursor-dyn-ledger-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:59
- **Concern**: skills/design/scripts/tally-plan-review.sh:499. Scenario: Design rejected-count grep requires a trailing colon after FINDING_N but tally writes headings without one
- **Proposed resolution**: `grep -cE '^### \[Plan Review\] FINDING_[0-9]+:'` on `rejected-findings.md` never matches; committed `rounds[].rejected` stays 0 while accepted counts look correct Use `grep -cE '^### \[Plan Review\] FINDING_[0-9]+'` (no trailing colon), matching `printf '### [Plan Review] %s\n\n' "$id"` in tally-plan-review.sh


### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-publish-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:59; skills/design/scripts/tally-plan-review.sh:499
- **Concern**: Rejected-count grep requires a colon the tally writer never emits. Scenario: Every design plan-review round records rejected=0 in ledger/committed timing JSON while accepted/OOS look correct
- **Proposed resolution**: Use `grep -cE '^### \[Plan Review\] FINDING_[0-9]+$'` (or `^### FINDING_[0-9]+:` on `rejected-findings.md` only); add a fixture/assert in `scripts/test-timing-report.sh`


