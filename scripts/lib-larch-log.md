# lib-larch-log.sh contract

Sourced-only library for `scripts/larch-log.sh`. No shebang; not invoked directly.

Full contract lives in `scripts/larch-log.md`. This stub satisfies the
sibling-contract rule for `lib-*.sh` files.

Key export: `larch_log_root()` — returns `$LARCH_LOG_ROOT` when set, otherwise
`$LARCH_LOG_REPO_ROOT/larch-logs`. `LARCH_LOG_REPO_ROOT` is resolved via
`git -C "$PWD" rev-parse --show-toplevel` (consumer repo) with fallback to
`SCRIPT_DIR/..`.
