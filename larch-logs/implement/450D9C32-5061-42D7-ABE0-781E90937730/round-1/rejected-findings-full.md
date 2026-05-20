### [rejected] FINDING_17

### FINDING_17: risk-integration: scripts/ship-pr.sh:999-1008
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Post-create write-final-report.sh is best-effort only. PR exists but tracking-issue final-summary can stay PR N/A until later refresh if API fails; old path stalled here. Optional retry or stronger failure surfacing if stale comment is unacceptable; else document operator expectation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_18

### FINDING_18: risk-integration: scripts/ship-pr.sh:999-1008
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Best_effort_post_write-final-report_can_leave_tracking_comment_at_PR_N/A If_pre-PR_API_succeeds_and_post-API_fails_PR_exists_but_larch_final-summary_can_still_show_N_A Document_edge_case_add_retry_or_stronger_failure_handling_if_canonical_URL_must_be_guaranteed
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_6

### FINDING_6: architecture: scripts/ship-pr.sh:964-977
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Empty flush_run_id skips pre-PR larch-log commit. Push #1 may omit committed final-summary.md though pre-create write succeeded; edge path. Warn on skip or document alongside LARCH_NO_LOGS_COMMIT.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_8

### FINDING_8: code-quality: scripts/ship-pr.sh:951-1008
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated write-final-report invocation pattern. Future edits may miss updating one of two copies. Optional factor shared block if consistent with rest of ship-pr.sh style.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

