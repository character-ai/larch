# lib-larch-log.sh contract

Sourced-only library for `scripts/larch-log.sh`. No shebang; not invoked directly.

Full contract lives in `scripts/larch-log.md`. This stub satisfies the
sibling-contract rule for `lib-*.sh` files.

Key exports:

- `larch_log_root()` — returns `$LARCH_LOG_ROOT`, which callers set via
  `larch-log.sh --log-root <dir>` or export explicitly for test isolation. It
  fails closed when the variable is absent; there is no `$IMPLEMENT_TMPDIR` or
  repo-root fallback.
  `LARCH_LOG_REPO_ROOT` is resolved via `git -C "$PWD" rev-parse --show-toplevel`
  (consumer repo) at library load time. It remains empty outside a git worktree;
  `commit` fails with a descriptive error in that case.
- `larch_log_repo_run_dir(skill, run_id)` — always returns the canonical repo path
  (`$LARCH_LOG_REPO_ROOT/larch-logs/<skill>/<run_id>`), bypassing the tmpdir tier.
  Used by `larch-log.sh commit` to locate the copy destination.
- `larch_log_publish_breadcrumbs_shared(source_hint_dir, dest_dir, on_error)` —
  publishes committed `breadcrumbs/` artifacts from session-root quiet logs. The
  helper treats `source_hint_dir` as the live breadcrumbs-directory hint, derives the
  session root with `dirname "$source_hint_dir"`, stages matching
  `larch-quiet-<script>-<pid>.log` files from that session root, and ignores
  legacy `*.ndjson` stream files. A hint outside the active session tmpdir is a
  no-op; each staged quiet log must still stay under the active session tmpdir or
  publication fails closed.
- `larch_log_validate_batch_payload(batch, file)` — dispatches batch sanitizers.
  The `plan-goals` sanitizer requires a non-empty `## Implementation Plan`
  section and rejects pointer-only placeholders. The `json-lines` sanitizer
  accepts empty files and requires every non-empty line to parse as JSON. The
  `json-object` sanitizer requires the whole file to parse as a JSON object.
