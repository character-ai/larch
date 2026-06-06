### FINDING_1: Step-2 hard-bail lacks step/phase context for recovery routing
- **Reviewer(s)**: Codex-Arch, Codex-Requirements, Codex-Pragmatic
- **Severity**: important
- **Concern**: Step-2 hard-bail handoff carries only the bail reason, not the Step-2 context (`STALL_STEP` / `PHASE`) needed for recovery routing. For memory-only Step-2 bails (e.g. orchestrator-envelope-invalid, wrapper-validation-failure), if classification reaches Step 18a before `ship-pr-state` has `STALL_STEP`/`PHASE`, `classify` can emit `FAILURE_CLASS=dispatch-failure` from `--bail-reason` but `resume_hint_for` sees empty step/phase and returns `none`. The recovery issue may be filed, but Step 2 is not retried and the dispatch-failure retry cap is never used.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the minimum Step-2 context handoff: set in-memory STALL_STEP=2 and PHASE=implementation on these Step-2 hard-bail paths or make classify infer step2-impl for the closed Step-2 bail tokens; add the planned argv-only regression with no persisted step/phase and assert RESUME_HINT=step2-impl
  - From Codex-Requirements: Add the minimum Step-2 context handoff: set in-memory STALL_STEP=2 and PHASE=implementation on these Step-2 hard-bail paths or make classify infer step2-impl for the closed Step-2 bail tokens; add the planned argv-only regression with no persisted step/phase and assert RESUME_HINT=step2-impl
  - From Codex-Pragmatic: Also carry Step-2 context into classification, e.g. set/pass STALL_STEP=2 or PHASE=implementation for these in-memory hard-bails, and assert wrapper-validation-failure with no disk state yields RESUME_HINT=step2-impl

### FINDING_2: exit_code transform change lacks three-location allowlist lockstep
- **Reviewer(s)**: Codex-dyn-allowlist-lockstep
- **Severity**: important
- **Concern**: The plan changes `exit_code` transforms in the TSV and markdown table but does not add any `code_allowlist_lines` or lint change that can represent `integer-or-unknown`. The proposed post-PR state can still drift: TSV/docs may say `integer-or-unknown` while the code heredoc/lint only tracks `surface+field_key`, so the required three-location allowlist lockstep is incomplete for the transform change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-allowlist-lockstep: Add a minimal code-side transform parity step for the three exit_code rows, or extend code_allowlist_lines/tsv_allowlist_lines/doc_allowlist_lines to compare source+transform and list bug-body, bug-comment, and chat-print exit_code as integer-or-unknown.

### FINDING_3: STALL_TRACKING optional on STATUS=bailed hard-bail skips stall report
- **Reviewer(s)**: Cursor-dyn-step2-bail-coverage
- **Severity**: important
- **Concern**: `STALL_TRACKING` is left optional on `STATUS=bailed` hard-bail. Scenario: dispatcher `STATUS=bailed` with `REASON=wrapper-validation-failure` sets `FINAL_BAIL_REASON`/`IMPLEMENT_BAIL_REASON` but the orchestrator omits `STALL_TRACKING`; Step 18a fast-paths with no stall detected and the stall report never shows the bail reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-step2-bail-coverage: Require unconditional STALL_TRACKING=true on the new STATUS=bailed bullet (match §2.1.5:616 and main-branch-post-dispatch:630), not if needed
