## Proposed Design Outline

### Goals
- Migrate every `emit_breadcrumb` / `emit_breadcrumb_stderr` callsite in tree to `larch_err`, `larch_errf`, or `emit` (quiet-log diagnostic).
- Drop the now-unused emit_breadcrumb API surface from `lib-quiet.sh` / `lib-quiet.md` / `test-lib-quiet.sh`.
- Remove the legacy ndjson loop from `larch_log_publish_breadcrumbs_shared`; quiet-log staging is authoritative.

### Non-goals
- Do not touch `breadcrumb-monitor.sh`, `lib-redact-streaming.sh`, the Family-B portion of `lint-foreground-markers.sh`, or BASH_AUTHORING.md §4 (Piece 3).
- Do not edit AGENTS.md, SECURITY.md, or docs/run-logs.md (Piece 3).
- Do not change paired-PID / sentinel / `LARCH_BREADCRUMB_*` / `LARCH_DONE_SENTINEL` / `LARCH_STATUS_FILE` / `LARCH_PAIRED_PID_FILE` env plumbing (Piece 3).

### Approach sketch
- Mechanical per-callsite replacement: `emit_breadcrumb [--category=X] TEXT` → `larch_err "TEXT"` (drop `--category`, drop redundant `>&2`); `emit_breadcrumb_stderr --category=X FORMAT args...` → `larch_errf "FORMAT\n" args...`.
- Remove the four lib-quiet helpers that have no remaining callers after migration: `emit_breadcrumb`, `emit_breadcrumb_stderr`, `larch_quiet_write_breadcrumb_record`, `larch_quiet_bc_valid_category`. Keep `larch_err`, `larch_errf`, `emit`, `emit_kv`, and the paired-PID / sentinel machinery.
- In `lib-larch-log.sh::larch_log_publish_breadcrumbs_shared`, delete the ndjson loop and its `ndjson_source_ok` plumbing; the quiet-log loop is the only staging path. Keep the function signature, the on-error helper, the under-tmpdir guard, and `larch_log_breadcrumb_source_dir` (still used to derive `session_root` via `dirname`).
- Trim `lib-quiet.md` / `test-lib-quiet.sh` / sibling `.md` files for scripts whose callsites change.

### Surfaces in scope
- `scripts/lib-quiet.sh`, `scripts/lib-quiet.md`, `scripts/test-lib-quiet.sh`
- `scripts/lib-larch-log.sh`, `scripts/lib-larch-log.md`
- `scripts/ship-pr.sh` (+ `.md`), `scripts/ci-wait.sh` (+ `.md`), `scripts/collect-agent-results.sh` (+ `.md`), `scripts/implement-finalize.sh` (+ `.md`), `scripts/implement-bootstrap.sh` (+ `.md`), `scripts/rebase-checkpoint-probe.sh` (+ `.md`), `scripts/phantom-probe-with-warn.sh` (+ `.md`), `scripts/lib-voter-parse-rate.sh`, `scripts/generate-code-reviewer-agent.sh`, `scripts/generate-pre-rendered-reviewer-prompts.sh`
- `skills/cleanup/scripts/cleanup.sh`, `skills/upgrade-larch/scripts/upgrade-larch.sh`, `skills/set-up-forked-open-source-repo/scripts/setup-forked-open-source-repo.sh`, `skills/report-tokens/scripts/run-analysis.sh`
- `skills/review/scripts/dispatch-panel.sh`, `skills/review/scripts/review-core.sh`, `skills/review-and-fix/scripts/review-and-fix.sh`, `skills/review-and-fix/scripts/review-implement-step5-loop.sh`
- `.claude/skills/bump-version/scripts/apply-bump.sh`
- Tests: `scripts/test-ship-pr.sh`, `scripts/test-apply-bump.sh`, `scripts/test-implement-structure.sh`, `scripts/test-lib-quiet.sh`, `skills/implement/scripts/test-implement-review-token-propagation.sh`, `skills/review-and-fix/scripts/test-review-and-fix.sh`

### Open questions
- None.
