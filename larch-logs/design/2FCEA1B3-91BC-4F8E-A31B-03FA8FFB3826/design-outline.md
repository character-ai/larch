## Proposed Design Outline

### Goals
- Add an in-flight guard to `design-step6-prelude.sh` and `design-step6-cleanup.sh`: when `.design-step5c-status.env` is absent but `.bg-wait-active` is present, emit a hard error instead of silently skipping.
- Add test coverage: structural checks in `test-design-structure.sh` and a functional harness `test-design-step6.sh`.

### Non-goals
- Changing SKILL.md orchestrator rules (anti-poll rule is already correct).
- Changing any other `design-step5c.sh` or `design-publish.sh` logic.
- Renaming or replacing the `.bg-wait-active` marker mechanism.

### Approach sketch
- In `design-step6-prelude.sh`: before the "missing sidecar; skipping" branch, check `[[ -f "$DESIGN_TMPDIR/.bg-wait-active" ]]`; if true, print a `**⚠ Step 6: ...in-flight...**` message and `exit 1`.
- In `design-step6-cleanup.sh`: same guard before the "missing sidecar; preserving" branch.
- Add `contains` checks for `.bg-wait-active` in `assert_step6_cleanup_wrappers` in `scripts/test-design-structure.sh`.
- Add `test-design-step6.sh` functional harness: creates tmpdir, sets up `.bg-wait-active` without `.design-step5c-status.env`, invokes prelude/cleanup, asserts exit 1 and in-flight message.
- Add `test-design-step6` Makefile target and add to `test-harnesses-6`.

### Surfaces in scope
- `skills/design/scripts/design-step6-prelude.sh`
- `skills/design/scripts/design-step6-cleanup.sh`
- `skills/design/scripts/test-design-step6.sh` (new)
- `scripts/test-design-structure.sh`
- `Makefile`

### Open questions
- None.
