### FINDING_1: Terminal success drops post-publish emits
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Centralizing the terminal publish path can commit the summary but drop the post-publish side effects that the local render path still performs, so the `larch:final-summary` tracking comment and report-gate sidecars can go missing on cancelled/failed terminal outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After successful terminal log-publish (or when reusing an on-disk final-summary.md), call the same disk upsert helper planned for clarify (tracking-issue upsert-summary with --content-file final-summary.md). Keep approved / approved-partition on the existing local render path.
  - From Cursor-Pragmatic: After successful terminal log-publish, reuse the same disk upsert helper as clarify (`tracking-issue upsert-summary` from `final-summary.md`) before emitting readiness markers; fail closed when upsert fails if rename/success semantics require it.
  - From Cursor-Requirements: After centralized publish succeeds, keep the existing pair: `_emit_final_summary_marked_from_disk` plus `_emit_report_gate_sidecars_from_disk` before touching `.completed/step-final-summary`.


### FINDING_2: Dry-run render ordering still lacks a production change
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Design Publish Lifecycle, Codex-dyn-Design Publish Lifecycle
- **Severity**: important
- **Concern**: The plan adds dry-run ordering coverage, but the production dry-run branch still returns before `_render_final_summary_before_copy`, so the new test cannot pass and the ordering regression remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/larch/design/design_log_publish_flow.py: invoke _render_final_summary_before_copy in the --dry-run branch before emitting PUBLISH_OK=true (no git/gh side effects), or narrow the test plan to the existing non-dry-run ordering test only.
  - From Codex-Arch: Add python/larch/design/design_log_publish_flow.py to the plan and move or call _render_final_summary_before_copy on the dry-run success path before emitting PUBLISH_OK=true, while keeping publish side effects disabled.
  - From Cursor-Innovation: Add a firm ### UPDATED: python/larch/design/design_log_publish_flow.py step calling _render_final_summary_before_copy in the --dry-run branch before emitting PUBLISH_OK=true, or drop the dry-run ordering test from the plan.
  - From Codex-Innovation: Add an UPDATED entry for python/larch/design/design_log_publish_flow.py. In the dry-run success path, compute outcome and call _render_final_summary_before_copy before emitting PUBLISH_OK=true, while keeping real publish side effects skipped.
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/design/design_log_publish_flow.py` calling `_render_final_summary_before_copy` in the `--dry-run` branch (or drop that assertion from the plan).
  - From Codex-Pragmatic: Add a firm UPDATED section for python/larch/design/design_log_publish_flow.py that computes outcome and calls _render_final_summary_before_copy in dry-run after validation and before PUBLISH_OK=true, without real publish side effects
  - From Cursor-Requirements: Add `### UPDATED: python/larch/design/design_log_publish_flow.py` to call `_render_final_summary_before_copy` in the dry-run path (non-fatal on failure, mirror non-dry-run) before emitting `PUBLISH_OK=true`.
  - From Codex-Requirements: Add `### UPDATED: python/larch/design/design_log_publish_flow.py` and render the final summary on the dry-run success path before returning, while preserving no publish, copy, push, or PR side effects.
  - From Cursor-dyn-Design Publish Lifecycle: Add `### UPDATED: python/larch/design/design_log_publish_flow.py` calling `_render_final_summary_before_copy` in the dry-run success path (mirroring 506-512, still no push/PR), or drop the dry-run render assertion from the test plan.
  - From Codex-dyn-Design Publish Lifecycle: Either add the small dry-run render call to the plan’s file list or drop the test requirement.


### FINDING_3: Clarify publish can still report success on recovery or upsert failure
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Design Publish Lifecycle
- **Severity**: important
- **Concern**: Clarify’s publish flow can still be marked successful even when the log-publish stdout says recovery was needed or the follow-up summary upsert fails, which can leave `CLARIFY_PUBLISH_STATUS=ok` on a stale or incomplete summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In _publish_clarify_log_and_summary parse RECOVERY_BRANCH from log-publish stdout alongside PUBLISH_OK; treat any non-empty RECOVERY_BRANCH as publish failure (PUBLISH_OK=false, no rename, failure status such as log-publish-recovery).


### FINDING_4: Centralized terminal publish can rerun already-published outcomes
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-Design Publish Lifecycle
- **Severity**: blocking
- **Concern**: The centralized terminal helper can invoke `log_publish_main` again on outcomes already published elsewhere, which can repeat worktree/PR operations and break sentinel creation or leave recovery state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Narrow the predicate to issue-scoped outcomes (`cancelled-*` and `failed-publish-tail`) or skip centralized publish when prior publish artifacts exist (e.g. `.design-log-publish-metadata.env` / clarify publish env).
  - From Cursor-dyn-Design Publish Lifecycle: Exclude outcomes already published in clarify (`cancelled-clarify` always when `SESSION_ID` is set; `failed-clarify` when `design-log-publish.stdout` or `.design-log-publish-metadata.env` exists). For those, keep the approved-path pattern: local `--post-publish-only` render / readiness emit from `final-summary.md`, not a second `log_publish_main`.


### FINDING_5: failed-publish-tail still lives in step5c, not the Final summary block
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-Design Publish Lifecycle
- **Severity**: blocking
- **Concern**: The plan updates the Final summary block, but the live `failed-publish-tail` outcome is produced in `step5c_core` after `publish_core` fails, so the actual branch still bypasses the centralized publish path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add a firm update to python/larch/design/design_step5c.py to call the centralized terminal publish path for this branch, and adjust the existing Step 5c failed-publish-tail tests to assert centralized publish and no local render
  - From Cursor-Requirements: Add `### UPDATED: python/larch/design/design_step5c.py` (and focused tests) for the `publish_rc` 2/unexpected branch: reuse disk `final-summary.md` after `design log-publish` when logs were published, or invoke the same centralized publish helper before emit; do not rely on `step_final_summary_core` alone.
  - From Codex-Requirements: Add `### UPDATED: python/larch/design/design_step5c.py` and route the publish-tail abort through the centralized publish path with `--outcome failed-publish-tail`, with matching lifecycle test coverage.
  - From Codex-dyn-Design Publish Lifecycle: Update the failed-publish-tail branch in design_step5c to call the same centralized log-publish helper after staging terminal state, parse PUBLISH_OK, require a non-empty final-summary.md before emitting, and test that step5c_core path.


### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_terminal.py:849-909
- **Concern**: [SCOPE-REDUCTION] Broad cancelled-* / failed-* terminal log-publish will double-invoke design log-publish on outcomes that already published in clarify or Step 5c. Scenario: _is_terminal_publish_outcome uses startswith("cancelled-") or startswith("failed-"). Clarify publish already calls design log-publish for cancelled-clarify and failed-clarify (clarify.py:1188-1240). Step 5c publish_core can call log-publish for failed-plan-write (design_publish.py:832-847) and always attempts it on the approved tail before failed-publish-tail (design_publish.py:992-1008). Final summary still runs for those SUMMARY_OUTCOME values (skills/design/SKILL.md). A second log-publish hits git worktree add -b larch-logs/design-{run_id} on an existing branch and fails, or creates duplicate publish work.
- **Proposed resolution**: Replace prefix routing with an explicit allowlist of outcomes that never ran log-publish earlier (e.g. cancelled-outline, cancelled-already-planned, cancelled-decompose, cancelled-plan-size, cancelled-sprawl, cancelled-title-filter, failed-postplan, failed-judge-panel). For already-published outcomes, skip log-publish and only emit readiness markers from existing final-summary.md (and disk upsert if still needed). Fix failed-publish-tail render ordering in design_step5c.py instead of terminal re-publish.


### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:60-75; python/larch/design/clarify.py:1188-1196
- **Concern**: [SCOPE-REDUCTION] Terminal publish predicate covers every failed-* outcome instead of the issue-scoped failed-publish-tail path. Scenario: The clarify failure path already calls design log-publish for failed-clarify; a later final-summary pass under the proposed startswith("failed-") rule can retry the same run-id publish, collide with the existing log branch or PR, and turn a handled clarify failure into a terminal summary failure
- **Proposed resolution**: Limit the terminal centralized publish predicate to cancelled-* and failed-publish-tail, or list only outcomes that do not already publish logs elsewhere.


### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_terminal.py:849-909
- **Concern**: [SCOPE-REDUCTION] Blanket cancelled-/failed-* terminal routing will re-run log-publish after clarify already published. Scenario: Clarify publish always calls design log-publish in _publish_clarify_log_and_summary (outcomes cancelled-clarify and failed-clarify) before the orchestrator runs the Final summary block with the same SUMMARY_OUTCOME. _is_terminal_publish_outcome matching every cancelled-* and failed-* would invoke log_publish_main again and can open a second run-log PR or branch.
- **Proposed resolution**: Narrow terminal centralized publish to outcomes that never already called log-publish in-session (e.g. cancelled-outline, cancelled-decompose, failed-judge-panel). Exclude cancelled-clarify and failed-clarify, or skip publish when .design-log-publish-metadata.env is already populated and only emit readiness markers from final-summary.md.


### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_terminal.py:849-908
- **Concern**: [SCOPE-REDUCTION] Terminal publish matches every failed-* outcome, not just the scoped failed-publish-tail path. Scenario: Clarify label-remove failure already runs design log-publish with outcome failed-clarify, then exports SUMMARY_OUTCOME=failed-clarify. The planned failed-* terminal predicate would run design log-publish a second time for the same run id, risking a duplicate log PR/branch failure and a failed final-summary fence after the clarify publish already succeeded.
- **Proposed resolution**: Narrow the terminal publish predicate to cancelled-* plus exact failed-publish-tail, or only exact failed outcomes proven not to have already published logs. Keep failed-clarify local after clarify publish.


### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_terminal.py:849-909
- **Concern**: [SCOPE-REDUCTION] Terminal publish routing exceeds the issue anchor. Scenario: The binding scope targets cancellation and `failed-publish-tail` bypass of centralized pre-copy render. Routing every `failed-*` outcome through log-publish fixes extra tails (`failed-plan-write`, `failed-postplan`, `failed-judge-panel`, `failed-publish`) that the issue did not require and compounds duplicate-publish risk.
- **Proposed resolution**: Limit `_is_terminal_publish_outcome` to `outcome.startswith("cancelled-") or outcome == "failed-publish-tail"` unless a named outcome is shown to never have called log-publish earlier in the run.


### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_terminal.py:849-909
- **Concern**: [SCOPE-REDUCTION] The proposed terminal predicate routes every `failed-*` outcome through log publish, beyond the issue scope.. Scenario: The issue names cancellations and `failed-publish-tail`; routing `failed-plan-write`, `failed-postplan`, `failed-clarify`, and `failed-judge-panel` adds new log-PR and upsert failure surfaces to unrelated failure paths.
- **Proposed resolution**: Narrow the predicate to `outcome.startswith("cancelled-") or outcome == "failed-publish-tail"` and keep other failed outcomes on the current local render path unless a separate issue expands scope.


### FINDING_12:
- **Reviewer(s)**: Codex-dyn-Design Publish Lifecycle
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:60-75; python/larch/design/clarify.py:1188-1196; python/larch/design/clarify.py:1218-1226; python/larch/design/clarify.py:1233-1241; skills/design/SKILL.md:153-154
- **Concern**: [SCOPE-REDUCTION] Broad terminal publish predicate re-publishes clarify outcomes that already ran log-publish. Scenario: The planned predicate matches every cancelled-* and failed-* outcome, but clarify publish already calls design log-publish for cancelled-clarify and failed-clarify before the Final summary block. The final-summary fence can then try a second larch-logs/design-{run_id} publish, creating duplicate log PR or recovery-branch risk after a successful clarify publish.
- **Proposed resolution**: Exclude already-published clarify outcomes from the terminal publisher. For cancelled-clarify and failed-clarify, require the existing non-empty final-summary.md, emit the readiness markers, and touch the sentinel without rerendering or republishing.


### FINDING_1: Centralized publish must fail on `RECOVERY_BRANCH`
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Centralized terminal and step5c publish paths only gate on `PUBLISH_OK`, so a non-empty `RECOVERY_BRANCH` can still mark completion even though recovery work is pending and logs are incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In _publish_terminal_final_summary (and any shared wrapper), parse RECOVERY_BRANCH from captured stdout the same way as PUBLISH_OK. Treat any non-empty RECOVERY_BRANCH as publish failure even when PUBLISH_OK=true. Propagate that through step_final_summary_core and step5c failed-publish-tail before disk upsert or sentinel writes.
  - From Cursor-Pragmatic: Parse RECOVERY_BRANCH from centralized publish stdout in design_terminal.py and design_step5c.py, treat any non-empty value as publish failure, and apply the same gate in tests for terminal and failed-publish-tail paths.


### FINDING_2: Shared disk-upsert helper must not live in `clarify.py`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The shared disk-upsert helper is planned in `clarify.py`, but terminal and step5c also need it; importing it from there would create a module-load cycle through `design_lifecycle` / `design_terminal`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Place a neutral helper such as upsert_final_summary_from_disk in design_summary.py next to the existing tracking-issue upsert block (~628-638). Have clarify.py, design_terminal.py, and design_step5c.py import it from there.
  - From Cursor-Innovation: Place the shared disk-upsert helper in design_summary.py (or design_terminal.py) and import it from clarify.py, design_terminal.py, and design_step5c.py. Do not import clarify from design_terminal.
  - From Cursor-Pragmatic: Disk-upsert helper is planned only in clarify.py but reused from design_terminal.py and design_step5c.py clarify.py already imports design_lifecycle, which imports design_terminal and design_step5c. Top-level imports of the clarify helper from those modules create a circular import at module load. Place the shared disk-upsert helper in a neutral module such as design_summary.py (alongside existing upsert logic) or design_core.py, and import it from clarify, design_terminal, and design_step5c.
  - From Cursor-Requirements: Define one shared `_upsert_final_summary_from_disk(...)` in `design_summary.py` (or `design_core.py`) and call it from clarify, terminal, and step5c. Do not make `design_terminal` import `clarify`.


### FINDING_3: Disk-upsert failure must fail closed
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Terminal and step5c centralized paths can still complete after a successful log publish even if the follow-up disk upsert fails, which leaves the final-summary tracking comment stale or missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After centralized log publish succeeds, require the disk-upsert helper to return true before _emit_final_summary_marked_from_disk, sidecar emit, or sentinel touch. On upsert failure, append an execution issue, return non-zero, and skip completion. Apply the same success contract in step5c failed-publish-tail (centralized attempt fails if upsert fails; only then fall back to local render).
  - From Cursor-Pragmatic: Require disk upsert to return success before _emit_final_summary_marked_from_disk, report-gate sidecars, or completion sentinel writes; return non-zero and skip completion on upsert failure.
  - From Cursor-Requirements: Treat disk-upsert failure like clarify: return non-zero, keep PUBLISH_OK=false, skip .completed/step-final-summary, and on the step5c `failed-publish-tail` path fall back to `_step5c_render_final_summary` when upsert fails after centralized publish succeeds.


### FINDING_6: `cancelled-clarify` and `failed-clarify` still re-render after clarify publish
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The Final summary block still re-renders for clarify outcomes that already published and upserted, which can drift the GitHub comment away from the committed log summary or hide a failed second upsert.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: For cancelled-clarify and failed-clarify, when a non-empty final-summary.md already exists after clarify publish, skip render_final_summary_main and only run _emit_final_summary_marked_from_disk plus _emit_report_gate_sidecars_from_disk from disk.


### FINDING_7: Nonstandard plan heading may hide the `design_step5c.py` update
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The step5c fix may be missed by plan tooling because the heading format is not one of the recognized wire-format headings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Change the heading to `### UPDATED: python/larch/design/design_step5c.py` while keeping the existing body.


### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_step5c.py:555-569; python/larch/design/design_publish.py:992-1008
- **Concern**: [SCOPE-REDUCTION] The step5c retry plan can re-run log-publish after publish_core already attempted it.. Scenario: When approved publish reaches _run_log_publish_after_capture and returns rc 5, step5c enters the planned failed-publish-tail branch even though design log-publish already ran. The planned retry with outcome failed-publish-tail can create a second log-publish attempt for the same run id, violating the plan's no-double-publish scope.
- **Proposed resolution**: Narrow the step5c centralized retry to catastrophic exits with no prior log-publish evidence. If publish stdout or result env already contains PUBLISH_OK, PR_URL, or RECOVERY_BRANCH from design log-publish, skip the centralized retry and keep the local-render fallback.

