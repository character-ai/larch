## Decision 1: Scope — items 3 and 5 already addressed
- **Question**: Items 3 (test harness wiring) and 5 (timing-kind registration) in the issue — are they still open?
- **Resolution**: Both are already addressed by #3820. Makefile `test-launch-claude-drafter` target exists; `agent-lint.toml` references the files; `claude-plan-draft` is in `lib-timing-kinds.sh`. No changes needed for these two.
- **Source**: codebase

## Decision 2: Item 4 scope — use emit-design-plan-preview.sh for Step 2b display
- **Question**: Should Item 4 (Step 2b summary threshold duplication) be fixed in this issue?
- **Resolution**: Yes. Add `--variant step2b` to `emit-design-plan-preview.sh` and update SKILL.md Step 2b drafter display to call it.
- **Source**: user

## Decision 3: --repo-root fallback behavior
- **Question**: If `git rev-parse --show-toplevel` fails in the SKILL.md drafter block, should it fall back to $PWD or fail loud?
- **Resolution**: Fail loud — abort the drafter if not in a git repo. Drafter should not run outside a git repository.
- **Source**: user
