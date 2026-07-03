### FINDING_1: Review Step 0 binds the wrong session key for `claude-source`
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Standalone review Step 0 can skip or misbind the source snapshot because it uses `SESSION_ID` instead of the session key `token claude-source` expects, and it does not enforce `SESSION_UUID` matching before writing `claude-source.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror `design_publish._fetch_claude_source_snapshot`: gate on non-empty `LARCH_TOKEN_SESSION_ID`, export it for `token claude-source`, require `SESSION_UUID` to match, write `$REVIEW_TMPDIR/claude-source.env` from stdout, set `LARCH_CLAUDE_SOURCE_FILE` to that path.
  - From Codex-Pragmatic: Run token claude-source with LARCH_TOKEN_SESSION_ID="$SESSION_ID" and bind LARCH_CLAUDE_SOURCE_FILE only when SESSION_UUID matches SESSION_ID. Leave it empty and skip capture on mismatch.
  - From Cursor-Requirements: Drop the `SESSION_ID` binding. When `LARCH_CLAUDE_SOURCE_FILE` is empty, call `token claude-source` with `LARCH_TOKEN_SESSION_ID` from caller-env or host env when set; otherwise rely on the helper latest-mtime fallback. Write `$REVIEW_TMPDIR/claude-source.env` only when stdout contains `TRANSCRIPT_PATH`, matching `design_publish._materialize_claude_source_snapshot`

### FINDING_2: Design publish capture must not run on `--dry-run`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Concern**: Capturing the design transcript too early would run snapshot/hoist work during `--dry-run` invocations instead of only on the real publish path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Call `_capture_design_transcript` only on the non-dry-run path, after the dry-run early return and before `_publish_design_logs`.

### FINDING_3: Standalone review logs never reach the heatmap
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: Standalone review transcript commits are invisible to the heatmap because review run logs do not create an accepted manifest and the corpus scanner rejects review directories without a numeric `issue_number`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Before relying on coverage rows, either initialize an accepted review manifest before commit or make measure_references_heatmap use a narrow review-specific walker that counts safe committed review transcript dirs without requiring an issue manifest
  - From Codex-Innovation: Initialize the review run log before Step 4 writes and adjust the heatmap/run-log corpus path to count standalone review manifests without requiring `issue_number`, or otherwise populate a valid manifest field the existing reader accepts. Add the review heatmap test with a standalone review run that has no tracking issue.
  - From Codex-Requirements: Before review batch writes or transcript capture, initialize larch-logs/review/$RUN_ID/manifest.json, and update the corpus scanner or heatmap path to accept review manifests without issue_number while keeping safe_transcript_path checks. Add the planned review heatmap test with that real standalone review shape.

### FINDING_4: Review Step 4 adds a second transcript writer
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Step 4 risks bypassing the transcript renderer by adding a second session-transcript write path through `review log-phase` when `run-log capture-transcript` already exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Remove `session-transcript` from the Step 4 log-phase batch list. Drop the `review_tally.py` allowlist and `test_review_tally.py` additions. Keep one writer: `run-log capture-transcript` before cleanup, then best-effort `run-log commit`

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/SKILL.md
- **Concern**: [SCOPE-REDUCTION] Plan mixes `review log-phase` and `run-log capture-transcript` for `session-transcript`. Scenario: Step 4 prose would add `session-transcript` to the `review log-phase` batch list, and `review_tally.py` would allow `review log-phase --batch session-transcript --action write`. `log-phase` delegates to `run-log write`; `session-transcript` uses sanitizer `none`, so that path bypasses the renderer policy. The wired capture path is only `run-log capture-transcript` plus `run-log commit`.
- **Proposed resolution**: Drop `python/larch/review/review_tally.py` and `python/tests/review/test_review_tally.py` changes. Do not add `session-transcript` to the Step 4 `review log-phase` list. Keep transcript staging on the Step 4 `capture-transcript` call and durability on `run-log commit`.

### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-18.sh
- **Concern**: [SCOPE-REDUCTION] Plan re-adds `execution-issues flush-safety-net` in Step 18 while finalize teardown already runs it. Scenario: `python/larch/state/finalize.py` `_teardown_log_flush` already calls `execution_issues.flush_execution_issues_safety_net` before log commit. Adding the same call in `step-18.sh` duplicates append-only work on every finalize path without improving transcript coverage.
- **Proposed resolution**: Limit Step 18 changes to `LARCH_RUN_ID` rehydration and `run-log capture-transcript`. Leave execution-issues flush to finalize teardown; update `step-18.md` and `test-step-18.sh` to match.

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
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-18.sh:213-241
- **Concern**: [SCOPE-REDUCTION] Plan re-adds `execution-issues flush-safety-net` in Step 18 though finalize teardown already runs it. Scenario: `python/larch/state/finalize.py` `_teardown_log_flush` already calls `flush_execution_issues_safety_net` before `run-log commit`. Re-adding it in `step-18.sh` duplicates append-only work and expands the transcript diff without helping `session-transcript.jsonl` capture
- **Proposed resolution**: Add only `run-log capture-transcript` (plus `LARCH_RUN_ID` rehydration) in Step 18. Omit `flush-safety-net` from the shell; update `step-18.md` and `test-step-18.sh` to assert transcript capture ordering, not flush duplication
