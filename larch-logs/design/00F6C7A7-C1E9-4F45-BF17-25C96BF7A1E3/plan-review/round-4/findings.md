### FINDING_1:
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:616; skills/implement/references/stall-recovery.md:17; skills/implement/scripts/stall-recovery-report.sh:472-479
- **Concern**: Step-2 bail handoff only carries the reason, not the Step-2 context needed for recovery routing. Scenario: If a Step-2 envelope-invalid or wrapper-validation bail reaches Step 18a before ship-pr-state has STALL_STEP/PHASE, classify can emit dispatch-failure from --bail-reason but resume_hint_for sees empty step/phase and returns none, so the recovery issue is filed but Step 2 is not retried
- **Proposed resolution**: Add the minimum Step-2 context handoff: set in-memory STALL_STEP=2 and PHASE=implementation on these Step-2 hard-bail paths or make classify infer step2-impl for the closed Step-2 bail tokens; add the planned argv-only regression with no persisted step/phase and assert RESUME_HINT=step2-impl

### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:16
- **Concern**: Step-2 hard-bail handoff carries only bail reason, not step or phase evidence. Scenario: For memory-only Step-2 bails such as orchestrator-envelope-invalid or wrapper-validation-failure, classify can produce FAILURE_CLASS=dispatch-failure but RESUME_HINT remains none because resume_hint_for has no STALL_STEP=2 or phase input, so the dispatch-failure retry cap is never used
- **Proposed resolution**: Also carry Step-2 context into classification, e.g. set/pass STALL_STEP=2 or PHASE=implementation for these in-memory hard-bails, and assert wrapper-validation-failure with no disk state yields RESUME_HINT=step2-impl

### FINDING_3:
- **Reviewer(s)**: Codex-dyn-allowlist-lockstep
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:1000-1025,1071-1089
- **Concern**: The plan changes exit_code transforms in the TSV and markdown table but does not add any code_allowlist_lines or lint change that can represent integer-or-unknown.. Scenario: The proposed post-PR state can still drift: TSV/docs may say integer-or-unknown while the code heredoc/lint only tracks surface+field_key, so the required three-location allowlist lockstep is incomplete for the transform change.
- **Proposed resolution**: Add a minimal code-side transform parity step for the three exit_code rows, or extend code_allowlist_lines/tsv_allowlist_lines/doc_allowlist_lines to compare source+transform and list bug-body, bug-comment, and chat-print exit_code as integer-or-unknown.

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-step2-bail-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:29
- **Concern**: STALL_TRACKING left optional on STATUS=bailed hard-bail. Scenario: Dispatcher STATUS=bailed with REASON=wrapper-validation-failure sets FINAL_BAIL_REASON/IMPLEMENT_BAIL_REASON but orchestrator omits STALL_TRACKING; Step 18a fast-paths with no stall detected and stall report never shows bail reason
- **Proposed resolution**: Require unconditional STALL_TRACKING=true on the new STATUS=bailed bullet (match §2.1.5:616 and main-branch-post-dispatch:630), not if needed
