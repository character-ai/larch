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

### OOS_5: Aggregated rollup of 6 capped OOS items
- **Description**: Cap 5 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 6 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_1:**: - **Description**: Implement runs that bail before Step 7a may never flush vendor-failure-diagnostics. Scenario: Matches today’s session-transcript gap: diagnostics exist only in the session tmpdir af… [Files: docs/run-logs.md]
  - **OOS_2:**: - **Description**: [OUT_OF_SCOPE] dispatch-panel.sh not named in Files to modify. Scenario: Thin wrapper over dispatch-with-waterfall.sh; direct fixes to launch-review and compose-collector likely suf… [Files: dispatch-panel.sh dispatch-with-waterfall.sh skills/review/scripts/dispatch-panel.sh:1-80]
  - **OOS_1:**: - **Description**: Scout parse/validation failures log prose via `append-execution-issue.sh` only; `diag_file` is never flushed to committed run logs. Scenario: Standalone `/review` scout parse failur… [Files: append-execution-issue.sh skills/review/scripts/dispatch-panel.sh:330-365]
  - **OOS_2:**: - **Description**: Standalone `/review --run-id` has no batch slug for failure diagnostics. Scenario: Reviewer `*.failure-diag` files stay in `REVIEW_TMPDIR` after cleanup even when other review batch… [Files: skills/review/scripts/log-phase.sh:37-37]
  - **OOS_3:**: - **Description**: No planned SECURITY.md update for the new committed `*.failure-diag` surface. Scenario: Operators relying on SECURITY.md for publish boundaries may miss redaction/cap rules for the … [Files: SECURITY.md SECURITY.md:261-321]
  - **OOS_1:**: - **Description**: [SCOPE-REDUCTION] Triple durable flush surfaces per failure. Scenario: ${OUTPUT}.failure-diag plus vendor-failure-diagnostics.txt batch plus larch-log.sh scoped allowlist increases … [Files: larch-log.sh vendor-failure-diagnostics.txt]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 6 entries
- **Phase**: implement

