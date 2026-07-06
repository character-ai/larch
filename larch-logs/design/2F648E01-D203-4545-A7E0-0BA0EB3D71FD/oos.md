### OOS_1: Design progress reporting still adds a separate claude-vote-output.txt voter and uses voter_external_total + 1
- **Description**: Design progress reporting still adds a separate claude-vote-output.txt voter and uses voter_external_total + 1. Scenario: After a three-row plan-voter-slots.ndjson, Step 3 breadcrumbs can show voters as N+1/4 instead of N/3; does not block voting or model-role cuts
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/progress_report.py:1486-1495
- **Phase**: design


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: Shipped voting protocol still documents Claude-first /design voters while public docs in the plan are updated elsewhere
- **Description**: Shipped voting protocol still documents Claude-first /design voters while public docs in the plan are updated elsewhere. Scenario: Operators and downstream skills reading the protocol see a different /design voter topology than config and docs after rollout
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/shared/voting-protocol.md:7-64
- **Phase**: design


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: Step 3 progress still adds a legacy `claude-vote-output.txt` voter on top of `plan-voter-slots.ndjson` row counts
- **Description**: Step 3 progress still adds a legacy `claude-vote-output.txt` voter on top of `plan-voter-slots.ndjson` row counts. Scenario: After voter-1 joins the manifest, status can show inflated voter totals such as 3/4 during plan voting even though only three judges ran
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/report/progress_report.py:1479-1495
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

