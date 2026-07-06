### FINDING_2: Register the new plan-review stdout helpers
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The new plan-review helpers need explicit machine-stdout registration so their stdout contracts remain enforceable and the CLI port tests cover both the persistence helper and the skip-filter helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the `cli.py` update, require adding `("plan-review", "persist-accepted-audit")` to `_MACHINE_STDOUT_KEYS` unconditionally, and assert it in `test_design_cli_ports.py` alongside registry coverage.
  - From Cursor-Pragmatic: Register `("plan-review", "filter-gate-b-skipped")` in `_MACHINE_STDOUT_KEYS`. Pin it in `test_design_cli_ports.py` the same way `persist-design-assessment` is pinned today.
  - From Cursor-Pragmatic: Add `("plan-review", "persist-accepted-audit")` to `_MACHINE_STDOUT_KEYS`. Extend `test_design_cli_ports.py` to assert registry and machine-stdout membership for `persist-accepted-audit` and `filter-gate-b-skipped`, mirroring `ARCHITECTURAL_GUIDELINES_EXPECTED`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Shared Gate B filter logic lives in the accepted-audit module while `compose_review.py` imports it.
- **Description**: Shared Gate B filter logic lives in the accepted-audit module while `compose_review.py` imports it.. Scenario: That couples general findings composition to a Gate C audit package and invites circular-import pressure if compose grows audit-adjacent helpers.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/review/plan_review_accepted_audit.py
- **Phase**: design




Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_2: [SCOPE-REDUCTION] `plan-before-review.txt` will be copied into committed design logs
- **Description**: [SCOPE-REDUCTION] `plan-before-review.txt` will be copied into committed design logs. Scenario: The durable snapshot is only needed for Gate C comparison inside `$DESIGN_TMPDIR`. `design_log_publish_flow._copy_tree_redacted` copies every non-excluded top-level file; the plan adds keep-set docs for the audit artifact but never excludes the superseded-plan baseline.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_log_publish_flow.py:140-150
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: [SCOPE-REDUCTION] Exclude intermediate `plan-before-review.txt` from top-level design-log publish
- **Description**: [SCOPE-REDUCTION] Exclude intermediate `plan-before-review.txt` from top-level design-log publish. Scenario: The publisher copies every non-excluded top-level tmpdir file. `plan-before-review.txt` is only a Gate C comparison baseline, so committed logs would retain superseded plan text unrelated to the persisted audit artifact.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/design/design_log_publish_flow.py:140-150
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_4: [OUT_OF_SCOPE] Audit sidecar can become an extra stale design-log artifact
- **Description**: [OUT_OF_SCOPE] Audit sidecar can become an extra stale design-log artifact. Scenario: The mild or strong path writes accepted-plan-findings-audit.input.sidecar under DESIGN_TMPDIR; design-log publishing copies non-excluded top-level files, so a later clean Gate C rerun can overwrite accepted-plan-findings-audit.md but still publish the older sidecar alongside it
- **Reviewer**: Codex-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: plan.txt:118-120
- **Phase**: design

Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

