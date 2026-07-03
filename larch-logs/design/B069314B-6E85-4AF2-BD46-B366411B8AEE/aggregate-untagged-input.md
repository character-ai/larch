### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py:372-381
- **Concern**: Cached snapshot reuse must verify the transcript path exists, not only KV key presence. Scenario: The firm `design_publish.py` update validates `TRANSCRIPT_PATH` / `SESSION_DIR` / `SESSION_UUID` keys only. Edge cases require not reusing older `claude-source.env` unless it points at a real file. A stale cache with dead `TRANSCRIPT_PATH` would skip refetch and leave publish/implement capture failing for the whole tmpdir.
- **Proposed resolution**: In `_reuse_cached_claude_source_snapshot`, reuse only after `_validate_snapshot_replay` succeeds (or equivalent `TRANSCRIPT_PATH.is_file()` plus containment check). Otherwise unlink the cache and refetch.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/design/test_design_publish.py:1647-1735
- **Concern**: Publish-path regression for SESSION_UUID != larch run-id should be firm, not optional. Scenario: The issue failure is `design_publish._fetch_claude_source_snapshot` rejecting `SESSION_UUID != session_id` after overriding `LARCH_TOKEN_SESSION_ID` with the larch run-id. `test_tokens.py` covers resolver logic only; `MAY_UPDATE` lets implementers skip an integration test and accidentally keep the publish rejection branch.
- **Proposed resolution**: Move the `_capture_design_transcript` success-when-`SESSION_UUID`!=`ctx.session_id` assertion from `MAY_UPDATE` to a firm `### UPDATED:` `test_design_publish.py` item, with fake CLI stdout returning a Claude UUID distinct from `RUN1`.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py:372-440; python/larch/state/bootstrap.py:347-357
- **Concern**: Cached `claude-source.env` is still reusable without proving it resolves to a live transcript.. Scenario: The plan drops the run-id equality check, but it never adds a live-file check before reusing the cache. A resumed or retried design/implement tmpdir can keep an older broken snapshot, so publish or bootstrap will keep pointing at a dead transcript path and transcript capture will skip again instead of recovering.
- **Proposed resolution**: Before reusing a cached snapshot, parse it, require `TRANSCRIPT_PATH` to exist, and unlink/rebuild the file when it does not.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py:372-381
- **Concern**: Reuse-cache validation contradicts the plan edge case: UPDATED text only requires KV keys, but edge cases require a real on-disk TRANSCRIPT_PATH. Scenario: After relaxing `_reuse_cached_claude_source_snapshot` to stop matching `SESSION_UUID` to the larch run-id, a stale `claude-source.env` with populated keys but a missing or stale transcript file can be reused and `_fetch_claude_source_snapshot` is skipped; capture then exits with transcript-path-missing and the run commits no `session-transcript.jsonl` with no refetch attempt
- **Proposed resolution**: In `_reuse_cached_claude_source_snapshot`, parse the snapshot and reuse `_validate_snapshot_replay` (or equivalent path-under-project-dir checks); if validation fails, unlink the snapshot and return None so `_fetch_claude_source_snapshot` runs; add a focused test in `python/tests/design/test_design_publish.py` for stale-cache refetch [OUT_OF_SCOPE] python/larch/report/tokens.py:1257-1271 — Optional `_requested_claude_session_id` helper is extra surface; an ordered two-key loop with the existing fail-closed `break` after the first configured sid (even when `<sid>.jsonl` is absent) matches current structure with less indirection. [OUT_OF_SCOPE] docs/linting.md:266 — The `make test-token-claude-source` harness description still documents `LARCH_CLAUDE_SESSION_ID` override behavior and does not mention `CLAUDE_CODE_SESSION_ID` or dropping `LARCH_TOKEN_SESSION_ID` from transcript resolution; update when tests change to avoid operator confusion.

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py:372-455; python/larch/state/bootstrap.py:347-357
- **Concern**: Cached claude-source.env is still trusted on file presence alone. Scenario: Resumed design or implement/review sessions can keep replaying a stale or dead snapshot instead of refreshing through the fixed token lookup, so transcript capture still silently skips or can point at the wrong transcript.
- **Proposed resolution**: Revalidate the cached snapshot before reuse. Require TRANSCRIPT_PATH to exist and the snapshot to pass the same live-transcript checks as the fresh token path, or delete the file and rerun token claude-source when validation fails.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/bootstrap.py:347-352
- **Concern**: Edge cases require refusing stale snapshots unless TRANSCRIPT_PATH is readable, but the bootstrap UPDATED step keeps the unconditional early return on any non-empty claude-source.env.. Scenario: Implement resume or retry in the same IMPLEMENT_TMPDIR can keep a broken pre-fix snapshot (or a snapshot whose TRANSCRIPT_PATH was deleted) and never re-run token claude-source; Step 7a then skips capture and acceptance still fails for that run.
- **Proposed resolution**: In bootstrap.py, replace the size-only early return with the same rule as design publish: reuse only when parsed TRANSCRIPT_PATH is a readable file (reuse _validate_snapshot_replay or an equivalent is_file check); otherwise delete or ignore the file and fetch again.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py:372-381
- **Concern**: Reuse-cache wording only requires SESSION_UUID KV presence, weaker than the plan Edge cases rule that cached snapshots must point at a real transcript path.. Scenario: After dropping SESSION_UUID == session_id checks, design pause/resume or a second publish pass can reuse claude-source.env whose TRANSCRIPT_PATH no longer exists; materialize returns the stale snapshot and capture fails with transcript-path-missing instead of refetching.
- **Proposed resolution**: In _reuse_cached_claude_source_snapshot, require TRANSCRIPT_PATH to resolve to a readable file (and optionally SESSION_DIR/SESSION_UUID shape) before reuse; unlink and refetch when validation fails. ## Findings ### 1. [correctness] `python/larch/state/bootstrap.py:347-352` — bootstrap stale-cache handling contradicts Edge cases The plan’s Edge cases say not to reuse cached `claude-source.env` unless it points at a real transcript. The bootstrap `UPDATED` section still says to keep current behavior, which includes returning early whenever `claude-source.env` is non-empty (`351-352`), with no `TRANSCRIPT_PATH` validation. On implement resume in the same tmpdir, a stale or broken snapshot can block refetch; Step 7a then skips capture silently when `LARCH_CLAUDE_SOURCE_FILE` points at dead data. **Suggested revision:** Align bootstrap with design publish: validate `TRANSCRIPT_PATH` on disk before reuse; otherwise delete/ignore and call `token claude-source` again. ### 2. [correctness] `python/larch/design/design_publish.py:372-381` — `_reuse_cached_claude_source_snapshot` should enforce readable paths The plan correctly removes `SESSION_UUID == session_id` rejection (that check caused the zero-transcript failure). The replacement validation is underspecified: “has `TRANSCRIPT_PATH`, `SESSION_DIR`, and `SESSION_UUID`” means KV presence only, not that the transcript file exists. Edge cases already require a real transcript path; the firm `UPDATED` step should match. **Suggested revision:** Before reusing cache, parse the snapshot and require `Path(TRANSCRIPT_PATH).is_file()` (reuse `_validate_snapshot_replay` from `tokens.py` if convenient). Unlink and refetch on failure. --- **Note:** The core fix is sound and minimum-change: stop treating `LARCH_TOKEN_SESSION_ID` as a Claude transcript sid in `_find_latest_claude_transcript`, stop injecting larch run-ids into `token claude-source`, and drop the `SESSION_UUID == session_id` publish guard. Planned regression tests (sid-hit, sid-miss, no-sid fallback, legacy run-id isolation) match the failure mode described in the issue scope anchor.

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-Transcript Lifecycle
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py:500-516
- **Concern**: _capture_design_transcript still aborts on source-env.sh SESSION_ID drift before the new Claude UUID lookup runs. Scenario: test_capture_session_id_drift_uses_warning_label only checks the warning label, so a reused design tmpdir with stale source-env.sh will still skip snapshot materialization and ship without session-transcript.jsonl
- **Proposed resolution**: Move the drift check after snapshot materialization or downgrade it to a warning that does not return early

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-Transcript Lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/state/bootstrap.py:347-357,299-306,457-458
- **Concern**: _write_claude_source_snapshot returns immediately for any non-empty claude-source.env and never validates the cached transcript before session-env materialization. Scenario: test_write_base_session_env_preserves_claude_source_and_dynamic_keys never touches this helper, so a stale snapshot from an older broken run can keep propagating a dead LARCH_CLAUDE_SOURCE_FILE and suppress implement transcript capture
- **Proposed resolution**: Parse the existing snapshot first and rewrite it when TRANSCRIPT_PATH is missing or stale, instead of treating any non-empty file as valid

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-Transcript Lifecycle
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/review/SKILL.md:37-37
- **Concern**: The updated Step 0 prose still says to leave LARCH_CLAUDE_SOURCE_FILE empty on SESSION_UUID mismatch and to materialize only under LARCH_TOKEN_SESSION_ID. Scenario: Standalone review with a real Claude UUID that differs from the larch run-id will still skip capture, so review transcripts never land
- **Proposed resolution**: Remove the mismatch clause and bind LARCH_CLAUDE_SOURCE_FILE whenever token claude-source returns TRANSCRIPT_PATH=
