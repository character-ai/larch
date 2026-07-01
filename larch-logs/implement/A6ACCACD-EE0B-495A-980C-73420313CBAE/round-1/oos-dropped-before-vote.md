### OOS_1: [OUT_OF_SCOPE] manifest-less run dirs skipped without operator warnings
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The shared corpus walk skips directories without accepted manifests but does not surface warnings, so operators cannot see why orphan UUID folders are excluded from `runs_observed` denominators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Pass warn callback into run_log_corpus.run_dirs from heatmap and realized-cost

### OOS_2: [OUT_OF_SCOPE] retro_v3_sweep still strips tool calls to prose-errors-only
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: `python/larch/report/retro_v3_sweep.py` still enforces prose-errors-only v3 transcripts. Re-sweeping committed logs would remove newly preserved Read blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update sweep policy before any corpus retro run

### OOS_3: [OUT_OF_SCOPE] skills with runs but no SKILL.md omitted from realized-cost output
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Skills that have validated runs but no current `SKILL.md` are omitted from realized-cost output instead of appearing with a zero floor or explicit skip warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Emit zero-floor row or explicit skip warning when SKILL.md missing

### OOS_4: [OUT_OF_SCOPE] duplicate reference-path normalization in renderer and tokens
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-design-capture
- **Severity**: latent
- **Concern**: Reference Read path normalization and scope rules are duplicated in `python/larch/report/tokens.py` and `python/larch/rendering/render_session_transcript.py`. Future path-rule changes can drift and cause renderer output that measurement no longer counts, or vice versa.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Extract one shared normalizer for renderer and metrics.
  - From dyn-dyn-design-capture: Extract one shared normalizer used by both measurement and rendering.

### OOS_5: [OUT_OF_SCOPE] token claude-source latest-mtime fallback under wrong SESSION_ID
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `token claude-source` falls back to the latest Claude jsonl when `SESSION_ID` does not name a file. Design `SESSION_ID` is a larch run uuid, not the Claude jsonl stem, so the wrong transcript may be captured under multi-session use.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Pass Claude session uuid explicitly; disable latest-mtime fallback on publish capture.

### OOS_6: [OUT_OF_SCOPE] run-log docs still describe prose-errors-only v3 transcripts
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `docs/run-logs.md` still describes prose-errors-only v3 transcripts, so operators may assume committed transcripts never contain Read tool blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Update docs for prose-errors-and-reference-reads policy.

### OOS_7: [OUT_OF_SCOPE] publish stale-root removal test does not pre-seed stale root transcript
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `test_publish_removes_stale_root_transcript_before_capture` does not pre-seed a stale root `session-transcript.jsonl` before publish. A bug that skips unlink yet still hoists could republish stale content without failing the current test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Pre-write stale JSONL at $DESIGN_TMPDIR/session-transcript.jsonl, run publish, assert final content equals hoisted capture output and not the stale bytes.

### OOS_8: [OUT_OF_SCOPE] manifest filtering changes LARCH_REPORT_TOKENS_LIMIT counting semantics
- **Reviewer(s)**: dyn-dyn-corpus-metrics, dyn-dyn-design-capture
- **Severity**: latent
- **Concern**: Moving manifest filtering into `run_log_corpus.run_dirs()` means `LARCH_REPORT_TOKENS_LIMIT` now counts only manifest-valid directories. Orphan siblings no longer consume limit slots. That behavior change for limited scans is not covered by a dedicated regression test and may surprise downstream tooling that relied on directory-order limits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-corpus-metrics: Moving manifest filtering into `run_dirs()` means `LARCH_REPORT_TOKENS_LIMIT` now counts only manifest-valid directories. Orphan siblings no longer consume limit slots. That is likely an improvement, but it is a behavior change for limited scans that is not covered by a dedicated regression test.
  - From dyn-dyn-design-capture: Document the new behavior or preserve old counting if downstream tooling relied on directory-order limits.

### OOS_9: [OUT_OF_SCOPE] historical committed transcripts not backfilled for absolute Read paths
- **Reviewer(s)**: dyn-dyn-transcript-sanitize
- **Severity**: latent
- **Concern**: Historical implement `session-transcript.jsonl` rows may already store v3 `tool_call` `Read` blocks with absolute `input.file_path` values. This branch parses them for metrics but does not backfill or rewrite committed logs.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_10: [OUT_OF_SCOPE] renderer tests lack direct normalization coverage
- **Reviewer(s)**: dyn-dyn-transcript-sanitize
- **Severity**: nit
- **Concern**: `python/tests/rendering/test_render_session_transcript.py` does not assert that absolute, cache, or `<OPERATOR_REPO_PATH>`-prefixed `Read` inputs normalize to repo-relative paths before emission. Coverage lives in `python/tests/report/test_tokens.py` against duplicate logic in `tokens.py`, not the renderer itself.
- **Suggested revisions (informational for voters; coder decides)**:

