## Decision 1: Fix approach
- **Question**: Issue #3181 lists three fix options (merge-in-writer / re-pass-flags / defensive-consumers); which should the plan take?
- **Resolution**: Approach #1 — make `write-design-current-env.sh` preserve the four reviewer presence/availability keys (`CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_AVAILABLE`, `CURSOR_AVAILABLE`) from the existing `source-env.sh` on a no-flag refresh. SKILL.md refresh blocks stay untouched.
- **Source**: user

## Decision 2: Backstop scope
- **Question**: Also add a defensive default for empty presence flags where the env is consumed (Step 3 driver / Step 3.6)?
- **Resolution**: No. Writer fix only — change `scripts/write-design-current-env.sh`, its `.md` sibling, and `skills/design/scripts/test-write-design-current-env.sh`. No consumer-side or SKILL.md changes.
- **Source**: user

## Decision 3: MANUAL_REQUESTED semantics (hard constraint, from codebase)
- **Question**: Does the merge change `MANUAL_REQUESTED` clear-on-omit behavior?
- **Resolution**: No. Test Case 12 proves omitting `--manual-requested` must clear a stale `true`. The merge is scoped to the four presence/availability keys only; `MANUAL_REQUESTED`, `REPO`, and `ISSUE_NUMBER` keep their current write-or-omit semantics.
- **Source**: codebase
