## Goal
Fix larch-log.sh and lib-larch-log.sh REPO_ROOT fallback to plugin tree outside consumer git worktree

## Implementation Plan

Fix larch-log.sh REPO_ROOT fallback and lib-larch-log.sh LARCH_LOG_REPO_ROOT fallback — both silently fall back to the plugin install directory when git rev-parse fails outside a consumer git worktree. The `commit` subcommand then runs git operations against the plugin tree.

### Changes

**scripts/larch-log.sh**
- Remove line 10: `[ -n "$REPO_ROOT" ] || REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"`
- Update comment on lines 7-8: remove "Falls back to script parent on non-git" — leave REPO_ROOT empty outside git.
- In the `commit)` case, immediately after `require_common`, add:
  `[ -n "$REPO_ROOT" ] || larch_log_fail 1 "commit requires a git worktree (PWD is not inside a git repo)"`

**scripts/lib-larch-log.sh**
- Remove line 11: `[ -n "$LARCH_LOG_REPO_ROOT" ] || LARCH_LOG_REPO_ROOT="$(cd "$LARCH_LOG_LIB_DIR/.." && pwd -P)"`
- Update comment on lines 7-9: remove "Falls back to the script's parent directory when invoked outside any git repo"

**scripts/larch-log.md**
- In the paragraph describing REPO_ROOT and LARCH_LOG_REPO_ROOT (lines 55-59): remove "both fall back to SCRIPT_DIR/.. outside a git repo" — replace with "commit fails with a descriptive error outside a git worktree"

**scripts/lib-larch-log.md**
- In the LARCH_LOG_REPO_ROOT bullet: remove mention of fallback to SCRIPT_DIR/..


## Test plan
- `make lint` (pre-commit + agent-lint) via /relevant-checks
- The commit subcommand is the only place REPO_ROOT is used for git operations, and only init/write/append/exists/manifest use LARCH_LOG_REPO_ROOT (via larch_log_repo_run_dir, called only from commit) — so leaving both empty on non-git paths is safe for all other verbs.
