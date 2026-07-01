# Review Round 2

- Mode: `diff`
- 4 accepted, 5 rejected (1 neutral)

## Accepted Findings

### FINDING_1: session-id-drift blocks publish instead of warning-only capture skip
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-corpus-metrics, dyn-dyn-design-capture
- **Severity**: important
- **Concern**: When `source-env.sh` carries a non-empty `SESSION_ID` that disagrees with publish `--session-id`, `_capture_design_transcript()` logs that transcript capture was skipped but returns `False`, which makes `_run_log_publish_after_capture()` abort the whole publish with `PUBLISH_OK=false` and exit 5. That contradicts the helper docstring and the plan’s capture-skip contract: skip paths should leave the root transcript absent and still allow `design log-publish`. A resume or env drift therefore blocks log publication (and can leave a `[DESIGNED]` issue without a committed `larch-logs/design/<run-id>/` tree) instead of only losing reference-read telemetry for that run. Round-1 UUID cache validation does not fix this: drift still aborts publish rather than skipping capture with a warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: On drift log session-id-drift leave root transcript absent and return True so publish continues; reserve False for stale-root removal and hoist failure only.
  - From cursor-specialist-correctness: Align drift with other capture skips: warning only return True; keep SESSION_UUID cache invalidation.
  - From cursor-specialist-edge-cases: On drift warning only: leave root session-transcript.jsonl absent and return True so log-publish proceeds; add a test proving publish succeeds without capture
  - From dyn-dyn-corpus-metrics: **Suggested fix:** On `session-id-drift`, return `True` after the warning (same as other capture-skip statuses), or split publish-blocking hygiene failures from capture-only skips so drift never sets `PUBLISH_OK=false`.
  - From dyn-dyn-design-capture: **Suggested fix:** On `session-id-drift`, append the warning, leave root `session-transcript.jsonl` absent, and `return True` so `log-publish` still runs; only stale-root removal and post-success hoist failures should `return False`.


### FINDING_5: unvalidated snapshot materialization and wrong-session transcript fallback
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-generalist, dyn-dyn-corpus-metrics
- **Severity**: important
- **Concern**: Fresh snapshot materialization accepts any `token claude-source` stdout containing `TRANSCRIPT_PATH=` without checking that `SESSION_UUID` matches the requested design run id. `_materialize_claude_source_snapshot()` re-validates cached snapshots but not newly written ones. Meanwhile `token_claude_source()` falls back to the newest `*.jsonl` in the Claude project directory when `LARCH_TOKEN_SESSION_ID` is set but `{session_id}.jsonl` is missing; using larch `SESSION_ID` as `LARCH_TOKEN_SESSION_ID` can force that fallback. Publish can therefore capture and commit another Claude session’s transcript under `larch-logs/design/<run-id>/`, corrupting heatmap `reads_observed` and realized-cost attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Prefer LARCH_CLAUDE_SESSION_ID from env; fail closed or warn instead of silent latest-jsonl fallback; verify SESSION_UUID before hoist
  - From codex-generalist: **Suggested fix:** Parse `result.stdout` before writing `claude-source.env`; if `SESSION_UUID` is absent or differs from `session_id`, warn, keep the root transcript absent, and skip capture rather than writing or using that snapshot. Add a regression test where fake `token claude-source` returns `SESSION_UUID=OTHER` and assert `run-log capture-transcript` is not called.
  - From dyn-dyn-corpus-metrics: **Suggested fix:** After `token claude-source` returns, require `SESSION_UUID == session_id` before writing or reusing the snapshot; if the named session file is absent, treat materialization as skipped instead of accepting the mtime fallback.


### FINDING_7: load_run_manifest crashes on invalid UTF-8 in manifest.json
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: A corrupted manifest with a bad byte aborts scan or measurement instead of being skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Read with errors=replace or catch UnicodeDecodeError and skip the manifest


### FINDING_11: unanchored plugin-cache normalization accepts arbitrary paths
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: Unanchored plugin-cache normalization accepts arbitrary paths; e.g. `/tmp/anything/plugins/cache/larch-local/larch/1.2.3/skills/design/references/approval-gates.md` is treated as a trusted reference read and then preserved/measured, even though it is not a real repo or cache path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: require an approved cache-root prefix or parse path segments from the start; add a rejection regression test


