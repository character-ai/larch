# Review Round 1

- Mode: `diff`
- 5 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: design_publish aborts capture when source-env refresh fails
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-testing, dyn-dyn-design-capture
- **Severity**: important
- **Concern**: After `claude-source.env` snapshot materialization succeeds, a failed `session write-design-env` refresh is treated as a full capture skip, so `run-log capture-transcript` is never invoked even though the snapshot exists. Publish can proceed to `log-publish` without `session-transcript.jsonl`, leaving reference-read telemetry at zero for that run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Still call capture-transcript with --source-file when snapshot exists; treat refresh failure as non-blocking warning only
  - From codex-specialist-testing: Log the refresh failure but continue to run-log capture-transcript with the snapshot path; only block on snapshot materialization or hoist failures.
  - From dyn-dyn-design-capture: Decouple refresh from capture: log refresh failure as a warning, then still call `capture-transcript` with `--source-file` pointing at the materialized snapshot; only skip capture on true snapshot/capture skip statuses.


### FINDING_2: design_publish session ID drift can hoist the wrong transcript
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-design-capture
- **Severity**: important
- **Concern**: Snapshot lookup uses `SESSION_ID` from `source-env.sh`, while capture/hoist uses `ctx.session_id`, and cached `claude-source.env` is reused without validating `SESSION_UUID`. Resume/retry or env drift can render one Claude session into another run's `larch-logs/design/<run-id>/session-transcript.jsonl`, corrupting heatmap and realized-cost attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Use one canonical session ID for claude-source capture and hoist paths
  - From cursor-specialist-edge-cases: Validate SESSION_UUID on reuse or delete claude-source.env before rematerializing, parallel to stale transcript cleanup.
  - From cursor-specialist-edge-cases: Fail closed when ids differ; use a single canonical session id for snapshot, capture, hoist, and publish.
  - From dyn-dyn-design-capture: Before reusing a cached snapshot, parse and require `SESSION_UUID == session_id` (and `source_session_id == ctx.session_id`); otherwise delete/regenerate the snapshot via `token claude-source`, or fail closed with a publish-blocking warning.


### FINDING_5: cache-path normalizer accepts arbitrary `/larch/` substrings
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-generalist
- **Severity**: important
- **Concern**: The read-path normalizer treats any absolute path containing `/larch/<segment>/...` as a plugin-cache path, not only real repo, operator-repo, or installed plugin-cache paths. Unrelated paths such as `/tmp/larch/foo/skills/design/references/approval-gates.md` normalize to in-scope repo-relative paths, inflating heatmap and realized-cost metrics and allowing untrusted transcript paths to be preserved into committed logs via the mirrored renderer logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Restrict cache normalization to the actual Claude plugin-cache path shape instead of matching any /larch/... substring.
  - From codex-specialist-edge-cases: anchor cache normalization to the real Claude cache layout, or share a helper that first verifies the known cache prefix or exact repo-root prefix before stripping, then only accepts the two reference scopes.
  - From codex-generalist: Anchor cache normalization to the real plugin-cache shape, for example `.../plugins/cache/larch-local/larch/<version>/`, including the redacted `<OPERATOR_REPO_PATH>/plugins/cache/...` form, and reject other absolute paths.


### FINDING_8: run_log_corpus manifest parsing drifts from report_tokens_scan safe_int
- **Reviewer(s)**: codex-generalist, dyn-dyn-corpus-metrics
- **Severity**: important
- **Concern**: `load_run_manifest()` gates runs with private `_safe_int()` that is not equivalent to `safe_int()` in `report_tokens_scan.py`. `_safe_int(True)` becomes `1` and accepts the manifest, while `_record()` builds `RunRecord.number` with `safe_int(True) == 0`; padded or comma-separated strings are accepted by one path and rejected by the other. This can change `runs_observed`, `invocations`, and `issues_observed` versus pre-branch `/report-tokens analyze` on edge-case manifests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: Reject `bool` before `int(value)`, or reuse `report_tokens_models.safe_int`, and keep a positive-number check at the shared manifest gate.
  - From dyn-dyn-corpus-metrics: Reuse `report_tokens_models.safe_int` (or a shared helper with identical semantics) inside `load_run_manifest()` for `issue_number` parsing, and add regression tests for bool, padded-string, and comma-separated `issue_number` values.


### FINDING_10: committed publish copies claude-source.env with operator-identifying paths
- **Reviewer(s)**: dyn-dyn-transcript-sanitize
- **Severity**: important
- **Concern**: Publish materializes `$DESIGN_TMPDIR/claude-source.env` with `TRANSCRIPT_PATH`, `SESSION_DIR`, and `SESSION_UUID` from `token claude-source` and copies it into committed `larch-logs/design/<run_id>/` because it is not in `_PUBLISH_EXCLUDE_*`. `redact tmpdir-paths` only replaces `<OPERATOR_REPO_PATH>/` with `<OPERATOR_REPO_PATH>/`, so committed files can still re-expose the operator username, an encoded absolute repo path, and the live Claude session id outside the sanitized `session-transcript.jsonl` contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-transcript-sanitize: Add `claude-source.env` (and, per `SECURITY.md` Tier-A sensitivity for `source-env.sh`, `source-env.sh`) to `_PUBLISH_EXCLUDE_NAMES` so only the hoisted, renderer-sanitized `session-transcript.jsonl` is committed; keep snapshot materialization ephemeral under `$DESIGN_TMPDIR` and do not flat-copy machine sidecars into the published run tree.


