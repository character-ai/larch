## Goal
Suppress an orphaned rebase log line on no-op paths, remove a redundant dirty-tree scan for Codex's read-only sandbox, and eliminate inline prose in `/implement`'s HAS_BUMP=false warning that duplicates the bump-version SKILL.md.

### Change A — Rebase Checkpoint Macro M1
Remove M1 (unconditional start log) from the Rebase Checkpoint Macro in `skills/implement/SKILL.md`. SKIPPED paths (SKIPPED_ALREADY_PUSHED / SKIPPED_ALREADY_FRESH) become silent; actual rebase still emits the completion line via M4.

### Change B — Codex dirty-tree sidecar guard
Add `CODEX_LAUNCH_MODE=read-only` variable in `_launch_codex` and guard `_write_dirty_tree_sidecar` in `_codex_exit_dispatcher` — skip when the sandbox is confirmed read-only.

### Change C — Bump-version prose removal
Remove "The skill should determine the current version, classify the bump type, compute the new version, edit the version file, and commit." from the HAS_BUMP=false warning in `skills/implement/SKILL.md`.

## Test plan
- `/relevant-checks` (pre-commit + agent-lint) green after changes
- `scripts/test-implement-rebase-macro.sh` still passes (pins call-site rows, not macro internals)
