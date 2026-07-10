## Decision 1: Include the secondary _classify.py softening
- **Question**: Should the plan also modify _classify_text's step3/step6 → contract-failure/none hard-code, or stay scoped to the primary _repair_loop_action fix?
- **Resolution**: Include it. Soften the `step in {"3","6"}` hard-code so a legitimately-exhausted (helper) stall gets a recoverable classification with a resume hint, while a genuine main-agent-declared contract violation still classifies as contract-failure/none. This is a defense-in-depth change in addition to the primary fix.
- **Source**: user

## Decision 2: Site coverage for exhausted → main-agent-edit
- **Question**: Which sites route `exhausted` → `main-agent-edit`?
- **Resolution**: Reuse the existing `_NO_CHANGES_STALE_MAIN_AGENT_SITES` set ({step3, step5-self-review, step5-mav, step6}). Ship-pr-ci-* sites keep their existing exhaustion contract (NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX / stall). Mirrors the existing no-changes-stale routing exactly; smallest, most consistent change.
- **Source**: codebase

## Decision 3: Ledger trigger token for exhausted
- **Question**: Should the exhausted ledger use a distinct `ledger_trigger` token, or reuse "main-agent-required"?
- **Resolution**: Reuse "main-agent-required" (via the existing `_ledger_trigger_for_lint_site` mapping). The main agent already handles this trigger identically to the desired exhausted behavior (read failure log, apply inline edits, re-run checks), so no downstream consumer changes are required.
- **Source**: codebase

## Hard constraints (must not break)
- Ship-pr-ci-* exhaustion behavior must remain unchanged.
- Genuine main-agent-declared contract failures on step3/step6 must still classify as contract-failure/none (RESUME_HINT=none) after the _classify.py change.
- Existing no-changes-stale → main-agent-edit routing and its ledger fields must remain byte-for-byte behavior-compatible.
