### OOS_1:
- **Description**: [OUT_OF_SCOPE] Five near-identical local append_launch_failure helpers could be one shared sourced helper with tmpdir resolution. Scenario: Duplicated give-up wiring raises parity drift risk but is not required to fix the empty execution-issues fenced block
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/launch-review.sh:60-84
- **Phase**: design

### OOS_2:
- **Description**: [OUT_OF_SCOPE] Research validation lane uses run-external-agent.sh but has no design/implement log-publish path in this plan. Scenario: Audit row can mark inherits for saved/logged via run-external-agent health-gate and resolver callers; no committed flush unless research gains a publish pipeline
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/research/references/validation-phase.md:101-101
- **Phase**: design

### OOS_3:
- **Description**: No doc update for newly committed `*.failure-diag` publish surface. Scenario: SECURITY.md documents stderr-tail redaction and design publish exclusions; adding committed failure diagnostics changes the public run-log boundary but the plan’s sibling-doc list omits SECURITY.md
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/SECURITY.md:261-321
- **Phase**: design

### OOS_4:
- **Description**: Wrapper-only validation failures lack an explicit plan touchpoint besides subprocess changes. Scenario: `launch-claude-review.sh` exits before `launch-claude-subprocess.sh` on argv/ctx validation errors; subprocess `write_failure_diag` never runs. Rare, and dispatch voters partially capture `.launcher-stderr`
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/launch-claude-review.sh:205-225
- **Phase**: design

### OOS_1:
- **Description**: Implement runs that bail before Step 7a may never flush vendor-failure-diagnostics. Scenario: Matches today’s session-transcript gap: diagnostics exist only in the session tmpdir after an early stall
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/run-logs.md (existing); plan Step 7 / flush helpers
- **Phase**: design

### OOS_2:
- **Description**: [OUT_OF_SCOPE] dispatch-panel.sh not named in Files to modify. Scenario: Thin wrapper over dispatch-with-waterfall.sh; direct fixes to launch-review and compose-collector likely suffice
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/dispatch-panel.sh:1-80
- **Phase**: design

### OOS_1:
- **Description**: Scout parse/validation failures log prose via `append-execution-issue.sh` only; `diag_file` is never flushed to committed run logs. Scenario: Standalone `/review` scout parse failures remain hard to diagnose post-cleanup even after launcher fixes
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/dispatch-panel.sh:330-365
- **Phase**: design

### OOS_2:
- **Description**: Standalone `/review --run-id` has no batch slug for failure diagnostics. Scenario: Reviewer `*.failure-diag` files stay in `REVIEW_TMPDIR` after cleanup even when other review batches commit; post-mortem gap outside design/implement publish paths
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/log-phase.sh:37-37
- **Phase**: design

### OOS_3:
- **Description**: No planned SECURITY.md update for the new committed `*.failure-diag` surface. Scenario: Operators relying on SECURITY.md for publish boundaries may miss redaction/cap rules for the new artifact class
- **Reviewer**: Cursor-Edge
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: SECURITY.md:261-321
- **Phase**: design

### OOS_1:
- **Description**: [SCOPE-REDUCTION] Triple durable flush surfaces per failure. Scenario: ${OUTPUT}.failure-diag plus vendor-failure-diagnostics.txt batch plus larch-log.sh scoped allowlist increases double-commit and drift risk beyond SIMPLE minimum; issue only requires committed distinguishable diagnostics
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt approach 6-8
- **Phase**: design

