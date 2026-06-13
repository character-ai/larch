# Review Round 4

- Mode: `diff`
- 8 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_11: Teardown-gate regression coverage missing from `test-design-failure-report.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-design-reporting-output.txt
- **Severity**: important
- **Concern**: Plan-mandated teardown-gate scenarios are largely absent from the harness. A regression in sentinel precedence (terminal vs escalation, operator-action repair) or panel-degradation escalation paths could ship without CI failure despite acceptance criteria requiring those behaviors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Expand `test-design-failure-report.sh` to cover the plan checklist: terminal-wins-over-escalation, no-ledger skip, each `failed-*` terminal outcome through the gate, invalid terminal state fail-closed, and operator-action sentinel repair.


### FINDING_12: Publish-tail integration untested in `design-step5c.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Publish-tail integration (`abort_failed_publish_tail`) is not exercised by any test. Wiring bugs in rc=2/unexpected abort paths could skip terminal staging or final-summary ordering while unit tests on `design-stage-terminal-state.sh` still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add an offline `design-step5c.sh` harness with stubbed `design-publish.sh` returning rc 2/unexpected; assert terminal state, sidecar logs, and `failed-publish-tail` render call.


### FINDING_13: Validator autofix escalation and operator-cancel paths untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Validator autofix escalation recording and `--operator-cancel` audit paths have no tests; `relevant-checks` routes to an unrelated auto-fix harness. Validator Cancel might stop writing operator-action sentinels, allowing escalation-success filing on a later approved run contrary to plan invariants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a dedicated harness for `design-step-validator-autofix.sh` and map `relevant-checks.sh` to it; cover record-escalation statuses and `--operator-cancel` sentinel/chat/run-log writes.


### FINDING_18: Tier B `gh issue create` bypasses sensitive-corpus gate
- **Reviewer(s)**: codex-generic-output.txt, dyn-tierb-safety-output.txt
- **Severity**: important
- **Concern**: In `file-failure-report-cross-repo.sh`, Tier B duplicate-comment paths validate via `reject_tier_b_comment_if_unsafe`, but the initial `gh issue create --body-file` path posts the full Tier B report with no equivalent validation. If `--publication-tier tier-b` is used without `--sensitive-corpus-file`, the helper may also skip corpus defaulting/validation. Safety then depends entirely on upstream `compose-report` having already run `sensitive_token_rejects_file`; a regression there could publish an unvetted body to the public larch repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: For all Tier B paths, resolve the default corpus before lookup/create, require it to be readable, and run `validate-tier-b-public-file` on `body_file` before `gh issue create`.
  - From dyn-tierb-safety-output.txt: Before `gh issue create` when `publication_tier=tier-b`, run the same `reject_tier_b_comment_if_unsafe` (or a shared `validate-tier-b-public-file` wrapper) against `body_file`, failing closed to `fallback-print-required` on rejection.


### FINDING_19: Report-gate sidecars hidden from orchestrator chat
- **Reviewer(s)**: codex-generic-output.txt, dyn-design-reporting-output.txt
- **Severity**: important
- **Concern**: Publish paths run `render-final-summary.sh --post-publish-only` with stdout redirected to `/dev/null`, so `print_report_gate_sidecars` never reaches chat. `design-step5c.sh` rebuilds sidecars into `design-report-gate-sidecars.md` and emits `REPORT_GATE_SIDECARS_FILE`, but `SKILL.md` Step 5c only instructs the orchestrator to emit `final-summary.md`, not the sidecar handoff. On `failed-plan-write` / `failed-publish`, fallback chat-print and operator-action audit can be written under `$DESIGN_TMPDIR` but never shown to the operator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Add a mandatory Step 5c handoff to read and emit `REPORT_GATE_SIDECARS_FILE` after `final-summary.md`, or change the driver contract so the sidecar bodies are printed by the orchestrator-visible path.
  - From dyn-design-reporting-output.txt: Either stop discarding `render-final-summary.sh` stdout in `design-publish.sh`, or document and enforce in `SKILL.md` that Step 5c must read `REPORT_GATE_SIDECARS_FILE` (when present) and emit it verbatim after the summary body. Add a harness asserting publish-failure paths surface sidecar content end-to-end.


### FINDING_20: Operator-action sentinel globally suppresses terminal failure reporting
- **Reviewer(s)**: dyn-design-reporting-output.txt
- **Severity**: important
- **Concern**: `design-failure-report.sh` treats any existing `design-failure-operator-action.env` as a global skip before the `failed-*` terminal branch runs. Validator Cancel at Step 2b / Gate B / discussion-round2 writes that sentinel and returns to Gate A while the run continues. If the run later ends in a real terminal outcome (`failed-publish`, `failed-plan-write`, etc.), the gate exits with `operator-action` and never files the terminal report. The plan only requires the sentinel to block escalation-success on a later approved teardown, not to suppress terminal failure reporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-reporting-output.txt: Narrow the operator-sentinel short-circuit to escalation-success only (or to non-`failed-*` outcomes). Keep terminal reporting on `failed-*` outcomes even when an operator-action sentinel exists from an earlier validator cancel.


### FINDING_23: Tier B sensitive-corpus leak vectors untested for design artifacts
- **Reviewer(s)**: dyn-tierb-safety-output.txt
- **Severity**: important
- **Concern**: The implementation plan required Tier B regression coverage that `design-failure-sensitive-corpus.env` rejects leaked `issue-body.txt` and `source-env.sh` content, but `test-design-failure-report.sh` only checks terminal/escalation/cancel/fallback paths. `test-stall-recovery-report.sh` case 25 exercises generic `/design` titles without seeding those design-specific sensitive files. The expanded corpus paths are unverified for the primary leak vectors called out in SECURITY.md.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tierb-safety-output.txt: Add hermetic cases that place unique markers in `issue-body.txt`, `feature-description.txt`, and `source-env.sh`, run `design-failure-report.sh` (or generic `compose-report --surface chat-print`) on a consumer-tree path, and assert compose fails or falls back to `fallback-print-required` rather than emitting/filing a body containing the marker.


### FINDING_3: Clarify hard halt has no mechanical terminal staging hook
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `failed-clarify` terminal staging is documented in `SKILL.md` Step 0b but not wired through a Step 0b script fence. Clarify-loop exhaustion or unrecovered clarify helper failure leaves `SUMMARY_OUTCOME=failed-clarify` without `design-failure-terminal-state.env`, so the teardown gate fail-closes to fallback chat instead of filing a terminal report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Invoke `design-stage-terminal-state.sh` from a Step 0b script fence or dedicated helper.
  - From cursor-specialist-edge-cases-output.txt: Wire mechanical staging into the clarify hard-halt path before `SUMMARY_OUTCOME=failed-clarify`.


