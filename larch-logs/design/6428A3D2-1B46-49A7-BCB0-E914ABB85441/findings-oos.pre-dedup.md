### OOS_1: [OUT_OF_SCOPE] Oversize sidecar attachment is broader than the minimum bug fix
- **Description**: [OUT_OF_SCOPE] Oversize sidecar attachment is broader than the minimum bug fix. Scenario: The issue is complete once oversize logs record escalation with a specific skip token and no Tool Failure; sidecar creation, digest naming, no-follow source reads, and extra failure tests add substantial complexity solely to preserve optional evidence
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/state/stall_recovery.py
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Truncated sidecar evidence is not consumed by classify or Tier A compose-report
- **Description**: [OUT_OF_SCOPE] Truncated sidecar evidence is not consumed by classify or Tier A compose-report. Scenario: Even when record-escalation attaches a tmpdir sidecar in the ledger, classify and compose-report still read --failure-detail-log / classification FAILURE_DETAIL_LOG via _read_validated_failure_detail_log on the original oversize path, so auto-filed reports keep omitting lint-fix detail for the dominant oversize hypothesis
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/state/stall_recovery.py
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] New classifier missing token may diverge from legacy stderr text for absent files
- **Description**: [OUT_OF_SCOPE] New classifier missing token may diverge from legacy stderr text for absent files. Scenario: validate_failure_detail_log currently prints outside implement tmpdir for any non-file path; introducing a missing classifier suffix without an explicit stderr contract risks silent drift between ledger detail_log_skipped tokens and stderr diagnostics operators already know
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/state/stall_recovery.py
- **Phase**: design



