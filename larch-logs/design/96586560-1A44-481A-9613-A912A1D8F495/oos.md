### OOS_1:
- **Description**: [OUT_OF_SCOPE] Flag parser can spin forever when `--issue` or `--repo` is the final argv. Scenario: With `set -u` but not `set -e`, `${2:-}` assigns empty and `shift 2` fails without consuming `$1`, so the while loop repeats and emits shift errors indefinitely
- **Reviewer**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/get-issue-state.sh:35-38
- **Phase**: design


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### OOS_2:
- **Description**: No SECURITY.md touch for security-motivated sentinel hardening. Scenario: SECURITY.md documents tracking-issue-read.sh read-path mitigations but not sentinel ISSUE_NUMBER/RUN_ID charset validation or no-echo ERROR policy
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: security
- **Location**: SECURITY.md:126 vs plan.txt:1-107
- **Phase**: design


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=1 Result=neutral

