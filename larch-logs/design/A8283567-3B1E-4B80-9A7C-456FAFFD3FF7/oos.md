### OOS_1:
- **Description**: Skipping run_ci_fix_vendor omits append-token-record after tier win. Scenario: Token/timing artifacts may diverge from historical ship-pr runs for billing or audit
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:1429-1432
- **Phase**: design


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### OOS_2:
- **Description**: Optional grep pin for ship-pr-ci-per-job. Scenario: New site not structurally pinned
- **Reviewer**: Cursor-Edge
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/test-implement-structure.sh:165-172
- **Phase**: design


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### OOS_3:
- **Description**: FAILED_JOBS and reasons may echo untrusted CI job names into logs or bail strings. Scenario: If a job name or matrix label were crafted to contain newlines or control bytes parsers or downstream prompts could mis-split lines
- **Reviewer**: Cursor-dyn-fd3-capture
- **Severity**: latent
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:39-42 and proposed scripts/ci-failed-jobs.sh KV and TSV rows
- **Phase**: design


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

