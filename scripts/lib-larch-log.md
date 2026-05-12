# lib-larch-log.sh contract

Sourced-only library for `scripts/larch-log.sh`. No shebang; not invoked directly.

Full contract lives in `scripts/larch-log.md`. This stub satisfies the
sibling-contract rule for `lib-*.sh` files.

Key exports:

- `larch_log_root()` — three-tier precedence: `$LARCH_LOG_ROOT` (explicit override) >
  `$IMPLEMENT_TMPDIR/larch-logs` (staging during a run) >
  `$LARCH_LOG_REPO_ROOT/larch-logs` (canonical repo destination).
  `LARCH_LOG_REPO_ROOT` is resolved via `git -C "$PWD" rev-parse --show-toplevel`
  (consumer repo) using a two-assignment pattern to avoid `(A || B) && C`
  shell-precedence issues; falls back to `SCRIPT_DIR/..`.
- `larch_log_repo_run_dir(skill, run_id)` — always returns the canonical repo path
  (`$LARCH_LOG_REPO_ROOT/larch-logs/<skill>/<run_id>`), bypassing the tmpdir tier.
  Used by `larch-log.sh commit` to locate the copy destination.
