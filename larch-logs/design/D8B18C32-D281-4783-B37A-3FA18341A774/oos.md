### OOS_1:
- **Description**: Batch-key normalization into stall-recovery-issue.env remains prose-only with no harness pin despite being in-scope behavior. Scenario: On /issue dedup stdout (ISSUE_1_DUPLICATE=true without ISSUE_1_NUMBER) an orchestrator that skips the mapping leaves step 8 bug-comment without ISSUE_NUMBER and falls back to manual print
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/references/stall-recovery.md:59-71
- **Phase**: design


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

