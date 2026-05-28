## Decision 1: In-scope files
- **Question**: Which files are in scope for Stage 1?
- **Resolution**: `scripts/larch-log.sh`, `scripts/lib-larch-log.sh`, `scripts/larch-log.md`, `scripts/refresh-run-logs.sh`, `scripts/design-log-publish.sh`, `scripts/design-log-publish.md`, `scripts/implement-finalize.sh` commit/publish path only, and targeted tests `scripts/test-larch-log.sh`, `scripts/test-design-log-publish.sh`, `scripts/test-refresh-run-logs.sh`, `scripts/test-implement-finalize.sh`.
- **Source**: codebase (issue #3116 body)

## Decision 2: Out-of-scope for Stage 1
- **Question**: What is explicitly deferred to later stages?
- **Resolution**: `breadcrumb-monitor.sh`, `lib-redact-streaming.sh`, the Family-B portion of `lint-foreground-markers.sh`, `emit_breadcrumb` / `emit_breadcrumb_stderr` helpers in `lib-quiet.sh`, paired-PID / sentinel-inheritance machinery, the `LARCH_BREADCRUMB_*` env vars, BASH_AUTHORING.md §4, and the `env -u` sanitization barrier. All are removed in later stages, not Stage 1.
- **Source**: codebase (issue #3116 body)

## Decision 3: Fail-closed scope (resolved at Step 1c)
- **Question**: Where does fail-closed publish semantics get implemented?
- **Resolution**: Script-level hard exit. `design-log-publish.sh` exits non-zero on push/merge hard failures (post-push paths that leave remote state in an unclean condition). Pre-validation failures (invalid args, missing tools, missing tmpdir) remain soft (PUBLISH_OK=false + exit 0) so callers can parse stdout and recover.
- **Source**: user (Step 1c)

## Decision 4: Quiet-log sourcing format (resolved at Step 1c)
- **Question**: What lands in committed `larch-logs/<run-id>/breadcrumbs/`?
- **Resolution**: Per-script quiet logs as one file per script invocation (e.g., `larch-quiet-<script>-<pid>.log`) staged in addition to the existing depth-1 `*.ndjson` files. Both paths coexist during Stage 1.
- **Source**: user (Step 1c)

## Decision 5: Hard constraint — preserve existing forensics
- **Question**: What must not break?
- **Resolution**: The committed `larch-logs/<skill>/<run-id>/breadcrumbs/` directory must continue to receive depth-1 `*.ndjson` files from the legacy session breadcrumbs dir (existing `larch_log_publish_breadcrumbs_shared` path). The new quiet-log path is additive, not a replacement.
- **Source**: codebase (issue #3116 body — "transitional fallback")
