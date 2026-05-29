Reviewing the cited locations to normalize concerns and confirm which findings describe the same risk.
### FINDING_1: Final grep gate omits test-harness paths that still reference removed breadcrumb symbols
- **Reviewer(s)**: Cursor-Arch, unknown-slot
- **Severity**: important
- **Concern**: The plan’s closing zero-hit grep gate targets `LARCH_DONE_SENTINEL`, `LARCH_STATUS_FILE`, `LARCH_PAIRED_PID_FILE`, and `LARCH_BREADCRUMB_STREAM`, but the scoped file list does not include the test scripts that still `unset` or `env -u` those names. A PR can satisfy skill/doc edits and pass unit tests while the pre-close grep still hits harness-only hygiene lines (or the implementer strips symbols ad hoc without a checklist). Affected paths include `scripts/test-ship-pr.sh`, `skills/implement/scripts/test-run-step2-dispatch.sh`, `skills/review/scripts/test-dispatch-panel.sh`, `skills/review-and-fix/scripts/test-review-and-fix.sh`, and `skills/design/scripts/test-dispatch-plan-assessors.sh`, `test-assess-plan-round.sh`, and `test-tally-plan-assessor.sh`; only `scripts/test-collect-agent-results.sh` (collector `C_DONE` usage) is explicitly listed in the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the plan file list (or add one “grep-gate harness sweep” step) to strip or narrow these unset lines in the same PR
  - From unknown-slot: PR lands with green unit tests but pre-close grep gate fails or implementer strips symbols ad hoc without a checklist Add an explicit harness pass: drop or rewrite sentinel env usage in those test files, or document a narrow grep exclusion for test-only `unset`/`env -u` isolation lines

### FINDING_2: `stall-recovery.md` still prescribes Family B background+monitor dispatch, not a fence collapse
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The plan scopes `skills/implement/references/stall-recovery.md` as collapsing a single Family-B fence reference, but the file has no `breadcrumb-monitor.sh` fence—only procedural contract text mandating background+monitor pairs for `run-step5-review.sh` / `ship-pr.sh`, six-path `LARCH_*` breadcrumb exports, and monitor-specific Exit 4 routing (e.g. Procedure step 5 and Safety Constraints). A fence-only edit leaves Step 18a `step5-review` / `step8-shippr` dispatch and safety rules pointing at removed machinery; stall recovery can mis-route after Stage 4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Replace the listed edit with explicit prose rewrite: plain foreground `run-step5-review.sh` / `ship-pr.sh`, drop six-path exports and monitor-failure branch; align with FINDING_1 (use Bash exit code + `ship-pr-state.sh` only)

### FINDING_3: Rebase Checkpoint Macro still cites deleted `lint-foreground-markers.sh`
- **Reviewer(s)**: Cursor-dyn-xref-sweep
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` line 139 still points operators at `scripts/lint-foreground-markers.sh` for foreground markers and denylist rules after that script is removed. Post-PR operators following the Rebase Checkpoint Macro can hit a dead path for foreground-marker enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-xref-sweep: Add an explicit implement-SKILL edit to drop or replace the L139 denylist pointer (e.g. point at `rebase-checkpoint-probe.md` only)
