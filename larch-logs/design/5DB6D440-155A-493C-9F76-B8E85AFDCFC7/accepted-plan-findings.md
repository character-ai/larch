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


