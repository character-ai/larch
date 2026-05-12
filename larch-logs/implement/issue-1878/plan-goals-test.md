## Goal
Add a Stop-hook guard for the post-`/bump-version` halt boundary (issue #1878): prevent the model from ending its turn between `/bump-version`'s return and `postbump-state.sh` being written.

## Implementation Plan

1. `scripts/check-bump-version.sh` — in `--mode pre` when `HAS_BUMP=true`, write `$IMPLEMENT_TMPDIR/.bump-version-armed` sentinel (best-effort; skipped when `IMPLEMENT_TMPDIR` is unset).
2. `skills/implement/scripts/hook-stop-fail-close.sh` — add a third block: if `.bump-version-armed` exists but `postbump-state.sh` absent, block session stop with next-step instructions.
3. Sibling docs updated: `scripts/check-bump-version.md`, `skills/implement/scripts/hook-stop-fail-close.md`.
4. `skills/implement/SKILL.md` — add NEVER #11, update Step 8 anti-halt note with Stop-hook enforcement.
5. `scripts/test-check-bump-version.sh` — 6 new sentinel test cases; `scripts/test-check-bump-version.md` updated.

## Test plan

- Run `bash scripts/test-check-bump-version.sh` — all 49 tests must pass.
- Run `/relevant-checks` — pre-commit + agent-lint must pass.
