### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md
- **Concern**: Review Step 0 snapshot wiring names the wrong session key and omits UUID validation. Scenario: Standalone review Step 0 already binds `LARCH_TOKEN_SESSION_ID`, not `SESSION_ID`. Running `token claude-source` without that key, or writing `claude-source.env` without checking `SESSION_UUID` against the bound session, can skip capture or attach another session's transcript. Acceptance for standalone review transcripts stays unmet.
- **Proposed resolution**: Mirror `design_publish._fetch_claude_source_snapshot`: gate on non-empty `LARCH_TOKEN_SESSION_ID`, export it for `token claude-source`, require `SESSION_UUID` to match, write `$REVIEW_TMPDIR/claude-source.env` from stdout, set `LARCH_CLAUDE_SOURCE_FILE` to that path.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/SKILL.md
- **Concern**: [SCOPE-REDUCTION] Plan mixes `review log-phase` and `run-log capture-transcript` for `session-transcript`. Scenario: Step 4 prose would add `session-transcript` to the `review log-phase` batch list, and `review_tally.py` would allow `review log-phase --batch session-transcript --action write`. `log-phase` delegates to `run-log write`; `session-transcript` uses sanitizer `none`, so that path bypasses the renderer policy. The wired capture path is only `run-log capture-transcript` plus `run-log commit`.
- **Proposed resolution**: Drop `python/larch/review/review_tally.py` and `python/tests/review/test_review_tally.py` changes. Do not add `session-transcript` to the Step 4 `review log-phase` list. Keep transcript staging on the Step 4 `capture-transcript` call and durability on `run-log commit`.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-18.sh
- **Concern**: [SCOPE-REDUCTION] Plan re-adds `execution-issues flush-safety-net` in Step 18 while finalize teardown already runs it. Scenario: `python/larch/state/finalize.py` `_teardown_log_flush` already calls `execution_issues.flush_execution_issues_safety_net` before log commit. Adding the same call in `step-18.sh` duplicates append-only work on every finalize path without improving transcript coverage.
- **Proposed resolution**: Limit Step 18 changes to `LARCH_RUN_ID` rehydration and `run-log capture-transcript`. Leave execution-issues flush to finalize teardown; update `step-18.md` and `test-step-18.sh` to match.



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



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/SKILL.md:75-75
- **Concern**: [SCOPE-REDUCTION] Drop the planned `review log-phase` path for `session-transcript`; keep only `run-log capture-transcript`.. Scenario: The Step 4 prose binds its batch enumeration to `review log-phase` calls that each take a `--payload-file`. `session-transcript` has no orchestrator payload and must be produced only by `run-log capture-transcript` (renderer-enforced v3 policy). The plan also adds `session-transcript` to `review_tally.py` log-phase allowlist (`python/larch/review/review_tally.py:1260-1261`), whose `sanitizer` is `none` in `run_log_batch.py:76`. Wiring both paths invites a generic `run-log write` that can stage arbitrary JSONL and bypass #3718/#5871, without completing any missing feature path.
- **Proposed resolution**: Remove `session-transcript` from the Step 4 log-phase batch list. Delete the `python/larch/review/review_tally.py` allowlist change and `python/tests/review/test_review_tally.py` additions. Keep standalone review capture solely on the planned `run-log capture-transcript` call plus the post-batch `run-log commit` before Step 5 cleanup.



### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/SKILL.md:75-106; python/larch/review/review_tally.py:1259-1273
- **Concern**: [SCOPE-REDUCTION] Do not add session-transcript to the generic review log-phase path. Scenario: The planned nested guard wraps direct capture and commit only. The existing RUN_ID log-phase block also runs for nested /review inside /implement, so adding session-transcript there can bypass the guard and write or attempt a raw review transcript under the parent run.
- **Proposed resolution**: Drop session-transcript from review log-phase allowlist, tests, and batch list. Rely only on the guarded standalone run-log capture-transcript call plus guarded commit.



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



### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-18.sh:213-241
- **Concern**: [SCOPE-REDUCTION] Plan re-adds `execution-issues flush-safety-net` in Step 18 though finalize teardown already runs it. Scenario: `python/larch/state/finalize.py` `_teardown_log_flush` already calls `flush_execution_issues_safety_net` before `run-log commit`. Re-adding it in `step-18.sh` duplicates append-only work and expands the transcript diff without helping `session-transcript.jsonl` capture
- **Proposed resolution**: Add only `run-log capture-transcript` (plus `LARCH_RUN_ID` rehydration) in Step 18. Omit `flush-safety-net` from the shell; update `step-18.md` and `test-step-18.sh` to assert transcript capture ordering, not flush duplication



### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:75,98; python/larch/report/run_log_corpus.py:39-46
- **Concern**: Standalone review logs remain invisible to the heatmap because the plan never creates a review manifest that the corpus scanner accepts. Scenario: Step 4 can write and commit larch-logs/review/$RUN_ID/session-transcript.jsonl, but review log-phase does not call run-log init, and run_log_corpus skips run dirs without manifest.json or without numeric issue_number. Real standalone review runs are not issue-anchored, so the planned review coverage row can be absent even after capture ships.
- **Proposed resolution**: Before review batch writes or transcript capture, initialize larch-logs/review/$RUN_ID/manifest.json, and update the corpus scanner or heatmap path to accept review manifests without issue_number while keeping safe_transcript_path checks. Add the planned review heatmap test with that real standalone review shape.



