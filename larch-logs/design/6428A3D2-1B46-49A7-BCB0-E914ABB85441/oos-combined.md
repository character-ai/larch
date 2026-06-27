### OOS_2: [OUT_OF_SCOPE] Truncated sidecar evidence is not consumed by classify or Tier A compose-report
- **Description**: [OUT_OF_SCOPE] Truncated sidecar evidence is not consumed by classify or Tier A compose-report. Scenario: Even when record-escalation attaches a tmpdir sidecar in the ledger, classify and compose-report still read --failure-detail-log / classification FAILURE_DETAIL_LOG via _read_validated_failure_detail_log on the original oversize path, so auto-filed reports keep omitting lint-fix detail for the dominant oversize hypothesis
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/state/stall_recovery.py
- **Phase**: design
