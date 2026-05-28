## Decision 1: emit_breadcrumb category handling
- **Question**: When substituting `emit_breadcrumb --category=X TEXT` to `larch_err`, should the category be preserved?
- **Resolution**: Drop category, keep text verbatim. Existing visual prefixes (⚠ ⛔ →) already convey severity. `emit_breadcrumb_stderr --category=X FORMAT args...` becomes `larch_errf "FORMAT\n" args...` with explicit newline.
- **Source**: user

## Decision 2: monitor / streaming / lint / BASH_AUTHORING.md §4 scope
- **Question**: Per the issue scope text "retain monitor/sentinel/paired-PID compatibility until Piece 3", should Stage 2 leave scripts/breadcrumb-monitor.sh, scripts/lib-redact-streaming.sh, the Family-B portion of scripts/lint-foreground-markers.sh, and BASH_AUTHORING.md §4 entirely untouched?
- **Resolution**: Yes, leave all four untouched (defer to Piece 3). Stage 2 touches only callsites + lib-quiet (emit_breadcrumb API trim) + lib-larch-log.sh ndjson-loop fallback removal.
- **Source**: user

## Decision 3: scripts/test-lib-quiet.sh test handling
- **Question**: How should test cases for the removed APIs (emit_breadcrumb / emit_breadcrumb_stderr / larch_quiet_write_breadcrumb_record / larch_quiet_bc_valid_category) be handled?
- **Resolution**: Delete those test cases entirely. Tests for larch_err, larch_errf, emit, emit_kv, paired-PID, and sentinel machinery stay.
- **Source**: user

## Decision 4: Doc edit scope
- **Question**: Which docs should be updated in Stage 2 vs deferred to Piece 3?
- **Resolution**: Minimal — only docs co-located with edited scripts. Update scripts/lib-quiet.md (drop emit_breadcrumb API docs), sibling .md files for scripts where callsites change (ship-pr.md, ci-wait.md, collect-agent-results.md, review-and-fix.md, implement-finalize.md, lib-larch-log.md, larch-log.md, etc.), and scripts/test-lib-quiet.md. Leave AGENTS.md, BASH_AUTHORING.md, SECURITY.md for Piece 3.
- **Source**: user

## Decision 5: Coverage of all 26 callsite-bearing scripts
- **Question**: Are there any callsite-bearing scripts that should be skipped (e.g., archived / generated / submodule)?
- **Resolution**: Codebase grep found ~26 .sh files calling emit_breadcrumb/emit_breadcrumb_stderr (no submodule paths). Issue scope says "Repo-wide conversion of all callsites" — no exceptions. All 26 files in scope.
- **Source**: codebase

## Decision 6: legacy ndjson fallback in publish
- **Question**: What exactly is the "legacy stream fallback from publish" to remove?
- **Resolution**: In scripts/lib-larch-log.sh `larch_log_publish_breadcrumbs_shared`, the ndjson loop (lines 448-462) plus its `ndjson_source_ok` plumbing (lines 404, 409-427, 433, 448). The quiet-log loop (lines 464-478) stays as the authoritative source. The source_dir argument and on_error parameters are retained.
- **Source**: codebase
