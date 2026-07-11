### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ship_pr.py:332-338
- **Concern**: Do not silently convert every post-merge flush skip into success. Scenario: The proposed any-reason rule also suppresses `redaction-failed` and `recovery-failed`, which indicate that log finalization or manifest recovery failed. The ship driver would report `Outcome.OK` and write `PHASE=done` even though required terminal artifacts may be missing or unsafe to publish, weakening the existing failure contract
- **Proposed resolution**: Ignore only best-effort skips caused by checkout drift or commit/refresh conditions. Preserve the existing stalled/error path for redaction and recovery failures, and add regression coverage for those fatal reasons



### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_pr.py:331-339
- **Concern**: [SCOPE-REDUCTION] Treating every RefreshSkip as silent success broadens the fix beyond the reported checkout-drift case. Scenario: Recovery, redaction, rendering, or other substantive post-merge refresh failures can now produce DONE/OK without warning or stall metadata, leaving logs or terminal artifacts incomplete and hiding an actionable failure
- **Proposed resolution**: Narrow the new success path to the checkout-drift or other explicitly benign skip reasons; preserve the existing stalled outcome for substantive refresh failures, and add regression coverage for both classes



