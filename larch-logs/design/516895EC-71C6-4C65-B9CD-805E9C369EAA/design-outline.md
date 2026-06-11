## Proposed Design Outline

### Goals
- Eliminate all inline Bash logic from `skills/design/SKILL.md` fences: every fence becomes a single script call.
- Merge consecutive script-call fences (no LLM judgment between them) into one call.
- Move deferred-MAV adjudication prose and compress Step 5b OOS narrative to reference files.
- Replace CI inline-pattern assertions with a new single-call-per-fence lint.

### Non-goals
- Changing runtime behavior of `/design` (behavior parity is required).
- Refactoring internals of existing helper scripts not touched by fence extraction.
- Modifying any skills outside `skills/design/`.

### Approach sketch
- Create `skills/design/scripts/design-step*.sh` wrapper scripts: each absorbs the fence's source-env bootstrap, pause-check, sentinel writes, and the actual work.
- Step 0 becomes one `design-step0.sh` call covering 0-pre through 0b-init; the script writes `.design-step0-result.env` and the PPID-keyed symlink for subsequent steps.
- Subsequent fences use a self-rehydrating call: the session env path is passed as `--session-env-path "$HOME/.cache/larch/sessions/current-design-env-$PPID.sh"` (resolved by the fence shell, no prelude logic needed).
- Merge consecutive fences in Steps 3b, 4b, 5b, 6, and the Final summary block into one script call each.
- Update `test-design-structure.sh`: replace `assert_bash_fences_have_pause_check`, `assert_step2a_entry_simple_guard`, and `assert_postplan_thin_fence` with an assertion that every fence is a single `${CLAUDE_PLUGIN_ROOT}/.../design-step*.sh` invocation.

### Surfaces in scope
- `skills/design/SKILL.md` (all 41 fences)
- `skills/design/scripts/` (new wrapper scripts)
- `scripts/test-design-structure.sh` (CI pin rewrites)
- `skills/design/references/plan-review.md` (absorb deferred-MAV paragraph)
- `skills/design/references/` (possible update to discussion-rounds.md if prose duplicates file-design-oos.md)

### Open questions
- Session-env discovery mechanism: pass `--session-env-path "$HOME/.cache/larch/sessions/current-design-env-$PPID.sh"` vs keeping the 2-line prelude. The former achieves zero-inline-logic fences; the latter is simpler but still has `[ -f ] && source`.
