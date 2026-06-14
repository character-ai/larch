## Proposed Design Outline

### Goals
- Guard `plan auto-fix-commands` against empty `composed-plan.md` (zero-byte file satisfies `is_file` but is a composition failure, not a validator defect).
- Correct `approval-gates.md` line 232: Fix-and-retry does NOT re-enter via `--skip-validate`; only Override and autofix-success do.
- Correct `flags.md` line 73: `--skip-validate` skips only command validation; the missing-or-empty guard in `design-publish.sh` is always enforced.

### Non-goals
- No behavioral changes to `design-publish.sh` — its `[[ -s ... ]]` guard already works correctly.
- No changes to test harnesses or CI configuration.
- No changes to SKILL.md prose (items 2 and 3 are purely in the reference docs).

### Approach sketch
- In `python/plan_quality.py cmd_auto_fix_commands`: add `or plan.stat().st_size == 0` to the pre-dispatch guard at line 1827; emit `AUTOFIX_STATUS=unavailable` (or a new `empty-target` status) and return early.
- In `skills/design/references/approval-gates.md`: update the single sentence at line 232 to state that only Override and autofix-success use `--skip-validate`; Fix-and-retry re-runs `design-step5c.sh` without `--skip-validate`.
- In `skills/design/references/flags.md`: update the sentence at line 73 to clarify that the proceed-anyway path (`--skip-validate`) skips only command validation; the missing-or-empty check at the top of `design-publish.sh` is unconditional.

### Surfaces in scope
- `python/plan_quality.py` — `cmd_auto_fix_commands` function, pre-dispatch guard
- `skills/design/references/approval-gates.md` — line 232 state-invariant sentence
- `skills/design/references/flags.md` — line 73 validation semantics sentence

### Open questions
- None.
