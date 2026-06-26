## Proposed Design Outline

### Goals
- Prevent security-tagged dropped OOS blocks from reaching the public `oos-dropped-before-vote.md` artifact committed to `larch-logs`
- Provide a local-only sidecar (`oos-dropped-security-local.md`) for security-tagged dropped OOS blocks
- Reuse existing security detection logic on in-memory strings without a temp-file round-trip

### Non-goals
- Change `gate.dropped_count` semantics (stays total count for backward compat)
- Modify `_ROUND_ARTIFACT_ALLOW` in `run_logs.py` (new sidecar is already excluded by the allowlist-only model)
- Alter `_copy_gate_audit_to_parent` behavior (already copies the now-filtered public file)

### Approach sketch
- Add `voting.is_security_block_text(text: str) -> bool` extracting detection logic from `voting.is_security_block`; refactor `is_security_block` to delegate to it
- In `_apply_pre_vote_oos_gate`, partition `dropped_blocks` into `public_blocks` and `security_blocks` using the new helper
- Write only `public_blocks` to `oos-dropped-before-vote.md`; write `security_blocks` to `oos-dropped-security-local.md`
- Update `SECURITY.md` to document the `oos-dropped-security-local.md` boundary

### Surfaces in scope
- `python/voting.py` — new `is_security_block_text`
- `python/review_pipeline.py` — `_apply_pre_vote_oos_gate` block-partition logic
- `python/test_voting.py` — test for `is_security_block_text` on strings
- `python/test_review_pipeline.py` — test for security-block filtering
- `SECURITY.md` — policy update for pre-vote dropped OOS

### Open questions
- None.
