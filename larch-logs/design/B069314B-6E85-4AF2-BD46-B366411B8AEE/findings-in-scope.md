### FINDING_1: Validate cached transcript snapshots before reuse
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-dyn-Transcript Lifecycle
- **Severity**: important
- **Concern**: Cached `claude-source.env` reuse can still accept stale or broken snapshots whose `TRANSCRIPT_PATH` no longer points at a real transcript, so design publish/bootstrap paths keep pointing at dead data instead of refetching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `_reuse_cached_claude_source_snapshot`, reuse only after `_validate_snapshot_replay` succeeds (or equivalent `TRANSCRIPT_PATH.is_file()` plus containment check). Otherwise unlink the cache and refetch.
  - From Codex-Arch: Before reusing a cached snapshot, parse it, require `TRANSCRIPT_PATH` to exist, and unlink/rebuild the file when it does not.
  - From Cursor-Innovation: In `_reuse_cached_claude_source_snapshot`, parse the snapshot and reuse `_validate_snapshot_replay` (or equivalent path-under-project-dir checks); if validation fails, unlink the snapshot and return None so `_fetch_claude_source_snapshot` runs; add a focused test in `python/tests/design/test_design_publish.py` for stale-cache refetch
  - From Codex-Innovation: Revalidate the cached snapshot before reuse. Require TRANSCRIPT_PATH to exist and the snapshot to pass the same live-transcript checks as the fresh token path, or delete the file and rerun token claude-source when validation fails.
  - From Cursor-Pragmatic: In bootstrap.py, replace the size-only early return with the same rule as design publish: reuse only when parsed TRANSCRIPT_PATH is a readable file (reuse _validate_snapshot_replay or an equivalent is_file check); otherwise delete or ignore the file and fetch again.
  - From Cursor-Pragmatic: In `_reuse_cached_claude_source_snapshot`, require `TRANSCRIPT_PATH` to resolve to a readable file (and optionally `SESSION_DIR`/`SESSION_UUID` shape) before reuse; unlink and refetch when validation fails.
  - From Codex-dyn-Transcript Lifecycle: Parse the existing snapshot first and rewrite it when TRANSCRIPT_PATH is missing or stale, instead of treating any non-empty file as valid

### FINDING_2: Promote the SESSION_UUID mismatch regression test to firm coverage
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The publish-path mismatch case is still parked as optional coverage, so the bad `SESSION_UUID != session_id` rejection path can regress without a hard integration test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Move the `_capture_design_transcript` success-when-`SESSION_UUID`!=`ctx.session_id` assertion from `MAY_UPDATE` to a firm `### UPDATED:` `test_design_publish.py` item, with fake CLI stdout returning a Claude UUID distinct from `RUN1`.

### FINDING_3: Do not abort design capture on source-env SESSION_ID drift
- **Reviewer(s)**: Codex-dyn-Transcript Lifecycle
- **Severity**: blocking
- **Concern**: `_capture_design_transcript` can still return early on stale `source-env.sh` session drift before the new Claude UUID lookup can recover, so resumed design tmpdirs skip materialization and ship without `session-transcript.jsonl`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Transcript Lifecycle: Move the drift check after snapshot materialization or downgrade it to a warning that does not return early

### FINDING_4: Stop gating standalone review capture on LARCH_TOKEN_SESSION_ID
- **Reviewer(s)**: Codex-dyn-Transcript Lifecycle
- **Severity**: blocking
- **Concern**: The review Step 0 prose still ties transcript materialization to `LARCH_TOKEN_SESSION_ID` and `SESSION_UUID` matching, so standalone review runs with a real Claude UUID can still leave `LARCH_CLAUDE_SOURCE_FILE` empty and skip capture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Transcript Lifecycle: Remove the mismatch clause and bind LARCH_CLAUDE_SOURCE_FILE whenever token claude-source returns TRANSCRIPT_PATH=
