### OOS_1: Shared Gate B filter logic lives in the accepted-audit module while `compose_review.py` imports it.
- **Description**: Shared Gate B filter logic lives in the accepted-audit module while `compose_review.py` imports it.. Scenario: That couples general findings composition to a Gate C audit package and invites circular-import pressure if compose grows audit-adjacent helpers.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/review/plan_review_accepted_audit.py
- **Phase**: design



### OOS_2: [SCOPE-REDUCTION] `plan-before-review.txt` will be copied into committed design logs
- **Description**: [SCOPE-REDUCTION] `plan-before-review.txt` will be copied into committed design logs. Scenario: The durable snapshot is only needed for Gate C comparison inside `$DESIGN_TMPDIR`. `design_log_publish_flow._copy_tree_redacted` copies every non-excluded top-level file; the plan adds keep-set docs for the audit artifact but never excludes the superseded-plan baseline.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_log_publish_flow.py:140-150
- **Phase**: design



### OOS_3: [SCOPE-REDUCTION] Exclude intermediate `plan-before-review.txt` from top-level design-log publish
- **Description**: [SCOPE-REDUCTION] Exclude intermediate `plan-before-review.txt` from top-level design-log publish. Scenario: The publisher copies every non-excluded top-level tmpdir file. `plan-before-review.txt` is only a Gate C comparison baseline, so committed logs would retain superseded plan text unrelated to the persisted audit artifact.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/design/design_log_publish_flow.py:140-150
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] Audit sidecar can become an extra stale design-log artifact
- **Description**: [OUT_OF_SCOPE] Audit sidecar can become an extra stale design-log artifact. Scenario: The mild or strong path writes accepted-plan-findings-audit.input.sidecar under DESIGN_TMPDIR; design-log publishing copies non-excluded top-level files, so a later clean Gate C rerun can overwrite accepted-plan-findings-audit.md but still publish the older sidecar alongside it
- **Reviewer**: Codex-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: plan.txt:118-120
- **Phase**: design



