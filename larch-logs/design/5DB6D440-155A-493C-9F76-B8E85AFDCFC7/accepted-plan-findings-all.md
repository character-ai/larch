### FINDING_1: Security classifier text-surface mismatch
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Oos Security Router
- **Severity**: important
- **Concern**: The security-routing step is inconsistent about whether it classifies raw block_text or restored artifact_text, so the classifier can see a different body than the text ultimately routed to the OOS/public pools.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Read block once, build artifact_text via _artifact_text_for_item, and call voting.is_security_block_text(artifact_text) for the security flag passed to _record_plan_review_artifact_chunks
  - From Cursor-Innovation: Align plan_review_tally.py and Failure modes: classify security on raw block_text before attribution restoration; delete or rewrite the artifact_text bullet so implementers do not move classification after _artifact_text_for_item
  - From Cursor-Pragmatic: Classify security with voting.is_security_block_text(artifact_text) using the single block read; update the UPDATED bullet to match the Failure modes edge case
  - From Cursor-Requirements: In plan_review_tally.py compute artifact_text first, then call voting.is_security_block_text(artifact_text). Align the UPDATED plan wording with the Failure modes section.
  - From Cursor-dyn-Oos Security Router: Reorder: compute `artifact_text` first, then `security = voting.is_security_block_text(artifact_text)`; add a regression with neutralized attribution where security tags live only in restored reviewer context


### FINDING_4: Security classifier failures must fail closed
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-Oos Security Router, Codex-dyn-Oos Security Router
- **Severity**: important
- **Concern**: Read, decode, or classifier failures must abort closed instead of being converted into non-security, because returning False or using replacement-decoded text can route security-tagged OOS into public pools.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Replace _is_security with voting.is_security_block_text on artifact_text after _artifact_text_for_item; remove the SystemExit swallow and fail closed on read/OSError the same way review_tally._security_block raises instead of returning False
  - From Cursor-dyn-Oos Security Router: Delete _is_security entirely; classify with voting.is_security_block_text on the same text used for routing; do not catch SystemExit and return False; add a plan-review tally regression mirroring `test_tally_security_classifier_failure_fails_closed` / pool-skip coverage
  - From Codex-dyn-Oos Security Router: Read the block with strict UTF-8 or treat any decode/read failure as a hard error before classification; classify the exact text only after the read succeeds.


### FINDING_1: emit_tally preserve branch must run before oos.md rebuild
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The new preserve path needs to short-circuit before any `oos.md` serialize/rebuild branch. Otherwise, a re-entry after aggregate promotion can still rebuild from a lingering round `oos.md` and overwrite the authoritative promoted sink.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: State the preserve branch explicitly runs before any oos.md rebuild path, and add a regression where oos.md is present while sink_count exceeds OOS_ACCEPTED_COUNT.


### FINDING_2: fail-closed security regression is aimed at the wrong seam
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned security regression still assumes `Path.read_text` failure inside the old classifier surface, but the implementation now routes through `voting.is_security_block_text(artifact_text)`. The test needs to fail at the current block-read or classifier-call seam so the fail-closed behavior is actually exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Retarget the test to raise from block read in _artifact_text_for_item or from voting.is_security_block_text, and assert plan-review tally aborts non-zero without routing the item to public pools.


### FINDING_4: strict decode handling is needed before security classification
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `block.read_text(..., errors="replace")` can hide decode corruption, so an unreadable or malformed block may still get classified as non-security and leak into public OOS pools. The read/assembly step needs fail-closed semantics before calling the text classifier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Before `voting.is_security_block_text(artifact_text)`, read the block with strict decode semantics and raise on `OSError`/decode failure; update the planned regression to force failure at that read/assembly site, not inside `is_security_block_text`.


