### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md
- **Concern**: Review Step 0 snapshot wiring names the wrong session key and omits UUID validation. Scenario: Standalone review Step 0 already binds `LARCH_TOKEN_SESSION_ID`, not `SESSION_ID`. Running `token claude-source` without that key, or writing `claude-source.env` without checking `SESSION_UUID` against the bound session, can skip capture or attach another session's transcript. Acceptance for standalone review transcripts stays unmet.
- **Proposed resolution**: Mirror `design_publish._fetch_claude_source_snapshot`: gate on non-empty `LARCH_TOKEN_SESSION_ID`, export it for `token claude-source`, require `SESSION_UUID` to match, write `$REVIEW_TMPDIR/claude-source.env` from stdout, set `LARCH_CLAUDE_SOURCE_FILE` to that path.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/design/design_log_publish_flow.py
- **Concern**: Centralized capture hook is not scoped to the real publish branch. Scenario: `log_publish_main` returns early on `--dry-run` before `_publish_design_logs`. Inserting capture immediately after argv validation would run snapshot/hoist work on dry-run invocations.
- **Proposed resolution**: Call `_capture_design_transcript` only on the non-dry-run path, after the dry-run early return and before `_publish_design_logs`.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/tokens.py:1755-1764
- **Concern**: Standalone review transcripts are committed without a heatmap-visible run directory. Scenario: The plan commits review batches via run-log write/capture/commit, but those calls do not create manifest.json; measure_references_heatmap walks run_log_corpus.run_dirs, which skips dirs with missing manifests or no numeric issue_number, so new larch-logs/review/<RUN_ID>/session-transcript.jsonl files do not contribute to review coverage or reads
- **Proposed resolution**: Before relying on coverage rows, either initialize an accepted review manifest before commit or make measure_references_heatmap use a narrow review-specific walker that counts safe committed review transcript dirs without requiring an issue manifest

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:75; python/larch/report/run_log_corpus.py:36-45
- **Concern**: Standalone review transcripts remain invisible to the heatmap. Scenario: `run-log write` and `run-log capture-transcript` do not create `manifest.json`, and `measure_references_heatmap()` reaches runs through `run_log_corpus.run_dirs()`, which rejects manifests without a numeric `issue_number`. A standalone `/review` run can commit `larch-logs/review/<RUN_ID>/session-transcript.jsonl` but still produce no review coverage row.
- **Proposed resolution**: Initialize the review run log before Step 4 writes and adjust the heatmap/run-log corpus path to count standalone review manifests without requiring `issue_number`, or otherwise populate a valid manifest field the existing reader accepts. Add the review heatmap test with a standalone review run that has no tracking issue.

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:29-35; python/larch/report/tokens.py:1260-1293
- **Concern**: Standalone review source snapshot must be pinned to the current SESSION_ID. Scenario: token claude-source selects a requested transcript only from LARCH_CLAUDE_SESSION_ID or LARCH_TOKEN_SESSION_ID. If Step 0 only checks that TRANSCRIPT_PATH exists, it can bind the latest project transcript and commit another session's sanitized reads under this review RUN_ID.
- **Proposed resolution**: Run token claude-source with LARCH_TOKEN_SESSION_ID="$SESSION_ID" and bind LARCH_CLAUDE_SOURCE_FILE only when SESSION_UUID matches SESSION_ID. Leave it empty and skip capture on mismatch.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md
- **Concern**: Review Step 0 claude-source materialization names SESSION_ID instead of the Claude session key design uses. Scenario: `session setup` always emits larch `SESSION_ID` (tmpdir uuid). `token claude-source` resolves transcripts via `LARCH_TOKEN_SESSION_ID` / `LARCH_CLAUDE_SESSION_ID`, not that value. Exporting or passing larch `SESSION_ID` makes snapshot lookup fail with transcript-not-found and standalone review capture skips despite a live Claude session
- **Proposed resolution**: Drop the `SESSION_ID` binding. When `LARCH_CLAUDE_SOURCE_FILE` is empty, call `token claude-source` with `LARCH_TOKEN_SESSION_ID` from caller-env or host env when set; otherwise rely on the helper latest-mtime fallback. Write `$REVIEW_TMPDIR/claude-source.env` only when stdout contains `TRANSCRIPT_PATH`, matching `design_publish._materialize_claude_source_snapshot`

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/SKILL.md:75-109
- **Concern**: The plan adds a second session-transcript write path through `review log-phase` while Step 4 already calls `run-log capture-transcript`. Scenario: `review log-phase` delegates to `run-log write` with `session-transcript` sanitizer `none` in `run_log_batch.py`. A log-phase caller can stage arbitrary JSONL and bypass the renderer that enforces v3 policy. The wired standalone path only needs `capture-transcript` plus `run-log commit`
- **Proposed resolution**: Remove `session-transcript` from the Step 4 log-phase batch list. Drop the `review_tally.py` allowlist and `test_review_tally.py` additions. Keep one writer: `run-log capture-transcript` before cleanup, then best-effort `run-log commit`

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:75,98; python/larch/report/run_log_corpus.py:39-46
- **Concern**: Standalone review logs remain invisible to the heatmap because the plan never creates a review manifest that the corpus scanner accepts. Scenario: Step 4 can write and commit larch-logs/review/$RUN_ID/session-transcript.jsonl, but review log-phase does not call run-log init, and run_log_corpus skips run dirs without manifest.json or without numeric issue_number. Real standalone review runs are not issue-anchored, so the planned review coverage row can be absent even after capture ships.
- **Proposed resolution**: Before review batch writes or transcript capture, initialize larch-logs/review/$RUN_ID/manifest.json, and update the corpus scanner or heatmap path to accept review manifests without issue_number while keeping safe_transcript_path checks. Add the planned review heatmap test with that real standalone review shape.
