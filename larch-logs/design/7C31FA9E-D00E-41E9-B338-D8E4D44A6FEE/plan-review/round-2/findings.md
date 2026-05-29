### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-ship-pr.sh:11; skills/design/scripts/test-dispatch-plan-assessors.sh:5; skills/design/scripts/test-assess-plan-round.sh:5; skills/design/scripts/test-tally-plan-assessor.sh:5; skills/review/scripts/test-dispatch-panel.sh:12; skills/review-and-fix/scripts/test-review-and-fix.sh:11; skills/implement/scripts/test-run-step2-dispatch.sh:68
- **Concern**: Final grep gate lists LARCH_DONE_SENTINEL / LARCH_STATUS_FILE / LARCH_PAIRED_PID_FILE / LARCH_BREADCRUMB_STREAM but the file list omits these harness unset lines. Scenario: PR can pass skill/doc edits yet still fail the plan’s own zero-hit grep gate on test-only env hygiene
- **Proposed resolution**: Extend the plan file list (or add one “grep-gate harness sweep” step) to strip or narrow these unset lines in the same PR

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:5-53
- **Concern**: Plan scopes stall-recovery as “collapse the Family-B fence (1 ref)” but the file has no `breadcrumb-monitor.sh` fence—only contract/dispatch prose mandating background+monitor pairs and monitor-specific Exit 4 routing. Scenario: A fence-only pass leaves Step 18a `step5-review` / `step8-shippr` dispatch and Safety Constraints still prescribing deleted machinery; recovery can mis-route stalls after Stage 4
- **Proposed resolution**: Replace the listed edit with explicit prose rewrite: plain foreground `run-step5-review.sh` / `ship-pr.sh`, drop six-path exports and monitor-failure branch; align with FINDING_1 (use Bash exit code + `ship-pr-state.sh` only)

### FINDING_3:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:147-148
- **Concern**: Final grep gate omits test-harness paths that still reference removed symbols. Scenario: `LARCH_DONE_SENTINEL` / `LARCH_STATUS_FILE` / `LARCH_BREADCRUMB_STREAM` appear in `scripts/test-ship-pr.sh`, `skills/implement/scripts/test-run-step2-dispatch.sh`, `skills/review/scripts/test-dispatch-panel.sh`, `skills/review-and-fix/scripts/test-review-and-fix.sh`, and three `skills/design/scripts/test-*.sh` unset blocks; only `test-collect-agent-results.sh` C_DONE is listed
- **Proposed resolution**: PR lands with green unit tests but pre-close grep gate fails or implementer strips symbols ad hoc without a checklist Add an explicit harness pass: drop or rewrite sentinel env usage in those test files, or document a narrow grep exclusion for test-only `unset`/`env -u` isolation lines

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-xref-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:139
- **Concern**: Rebase Checkpoint Macro still cites deleted `scripts/lint-foreground-markers.sh` denylist. Scenario: Post-PR operators follow a dead script path for foreground-marker rules
- **Proposed resolution**: Add an explicit implement-SKILL edit to drop or replace the L139 denylist pointer (e.g. point at `rebase-checkpoint-probe.md` only)
