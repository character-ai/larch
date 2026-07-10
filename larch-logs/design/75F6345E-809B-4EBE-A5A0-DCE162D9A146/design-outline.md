## Proposed Design Outline

### Goals
- Route `checks repair-loop` exhaustion (`LOOP_STATUS=exhausted`) to `NEXT_ACTION=main-agent-edit` instead of `stall`, so the main agent always gets a repair opportunity on supported sites.
- Soften the stall-recovery classifier so a legitimately-exhausted step3/step6 stall gets a recoverable resume hint instead of an unconditional `contract-failure/none`.
- Cover both changes with unit tests; verify the repair-loop reference doc still matches.

### Non-goals
- No change to ship-pr-ci-* exhaustion contract (`NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX`).
- No new ledger trigger token; reuse `main-agent-required`.
- No change to genuine main-agent-declared contract-failure classification.

### Approach sketch
- In `checks_lint_fix.py`, add an `exhausted` branch to `_repair_loop_action` that populates the ledger and returns `main-agent-edit`, gated on the existing `_NO_CHANGES_STALE_MAIN_AGENT_SITES` set.
- Generalize `_populate_no_changes_stale_ledger` (or add a thin parallel helper) so it also fires for `exhausted`.
- In `_classify.py` `_classify_text`, make the `step in {"3","6"}` short-circuit conditional: recoverable lint/checks-exhaustion text yields a resume hint; genuine contract failures still return `contract-failure/none`.
- Add tests for `exhausted → main-agent-edit` on step3 and step6, plus a classifier test for the softened path.

### Surfaces in scope
- `python/larch/implement/checks_lint_fix.py`
- `python/larch/state/_classify.py`
- `python/tests/implement/test_checks.py` (+ the `_classify` test module if separate)
- `skills/implement/references/checks-repair-loop.md` (verify only)

### Open questions
- Exact resume-hint token/class for softened step3/step6 exhaustion — resolve during drafting from existing `_classify_text` lint-failure conventions.
