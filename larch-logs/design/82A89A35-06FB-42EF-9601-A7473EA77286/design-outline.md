## Goals
1. Add `claude_draft` to `raw=` enum in `scripts/token-ledger.md`
2. Fix stale "Agent tool" Claude voter reference in `skills/shared/voting-protocol.md` § Launching Voters
3. Fix `--repo-root "$PWD"` → `git -C "$PWD" rev-parse --show-toplevel` (fail loud on error) in `skills/design/SKILL.md` Step 2b drafter block
4. Annotate the SKILL.md Step 2b drafter Bash block to run with `timeout: 1800000`
5. Add `--variant step2b` to `skills/design/scripts/emit-design-plan-preview.sh`; update SKILL.md Step 2b display to call it; add test coverage; update `.md` sibling

## Non-goals
- Refactoring `launch-claude-drafter.sh` / `launch-claude-subprocess.sh` duplication
- Changing `MODE=baseline-delta` sidecar grammar
- Adding `dispatch-code-voters.sh` `--role` without `--model` test coverage
- Any behavioral change to the drafter's plan-writing path

## Surfaces
- `scripts/token-ledger.md` (doc-only)
- `skills/shared/voting-protocol.md` (doc-only)
- `skills/design/SKILL.md` (Step 2b: --repo-root fix, timeout annotation, display refactor)
- `skills/design/scripts/emit-design-plan-preview.sh` (add step2b variant)
- `skills/design/scripts/emit-design-plan-preview.md` (update docs)
- `skills/design/scripts/test-emit-design-plan-preview.sh` (add step2b tests)
