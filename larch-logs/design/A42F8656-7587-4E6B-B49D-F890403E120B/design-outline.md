## Proposed Design Outline

### Goals
- Add per-script quiet-log files to committed `larch-logs/<skill>/<run-id>/breadcrumbs/` so post-hoc forensics survives breadcrumb deprecation.
- Make `design-log-publish.sh` fail-closed on hard publish failures (post-push paths) by exiting non-zero, while still emitting `PUBLISH_OK=false` for stdout-parseable contract compatibility.
- Preserve the existing legacy `*.ndjson` breadcrumb forensics path as a transitional fallback during Stage 1.

### Non-goals
- No removal of `breadcrumb-monitor.sh`, `lib-redact-streaming.sh`, `emit_breadcrumb*` helpers, paired-PID accounting, or `LARCH_BREADCRUMB_*` env plumbing — all deferred to later stages.
- No changes to `lint-foreground-markers.sh` Family-B portion or BASH_AUTHORING.md §4.
- No changes to existing pre-validation soft-fail paths in `design-log-publish.sh` (invalid args, missing tools, missing tmpdir, slug validation).

### Approach sketch
- Extend `larch_log_publish_breadcrumbs_shared` (or a sibling helper) in `lib-larch-log.sh` to also stage per-PID `larch-quiet-<script>-<pid>.log` files from the session tmpdir alongside the existing `*.ndjson` files.
- Update `larch-log.sh` `commit` to invoke the new sourcing path, redacting quiet-log content through the same redaction pipeline used for ndjson.
- In `design-log-publish.sh`, classify failures into hard (post-push: git push / gh pr / merge / branch-state corruption) vs soft (pre-validation). Hard failures emit `PUBLISH_OK=false` then `exit 1`; soft failures keep `exit 0`.
- Mirror the same hard-exit treatment in `implement-finalize.sh`'s commit/publish path so `/implement` benefits from the same fail-closed posture for log publish.
- Update `refresh-run-logs.sh` so directory-tree iteration handles both `*.ndjson` and `*.quiet.log` artifact classes in `breadcrumbs/`.

### Surfaces in scope
- `scripts/larch-log.sh`, `scripts/lib-larch-log.sh`, `scripts/larch-log.md`
- `scripts/refresh-run-logs.sh`
- `scripts/design-log-publish.sh`, `scripts/design-log-publish.md`
- `scripts/implement-finalize.sh` commit/publish path only
- `scripts/test-larch-log.sh`, `scripts/test-design-log-publish.sh`, `scripts/test-refresh-run-logs.sh`, `scripts/test-implement-finalize.sh`

### Open questions
- Should the new quiet-log staging share `larch_log_publish_breadcrumbs_shared`'s symlink/hardlink rejection and per-line redaction, or use a thinner copy path? Default: share — same forensics surface, same redaction posture.
- Should `implement-finalize.sh` callers parse a non-zero exit from publish as a separate signal, or rely on existing `PUBLISH_OK=false` parsing? Default: existing stdout parsing remains authoritative; non-zero exit is additive signal for ops dashboards / hook visibility.
