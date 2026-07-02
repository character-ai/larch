### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:499-501
- **Concern**: Refresh accepts corrupt staged fingerprints once repo refresh is available. Scenario: The plan removes the live/staged fingerprint equality bail but only keeps a non-empty DIFF_FINGERPRINT check. In production ship passes repo_root, so a sidecar whose DIFF_FINGERPRINT does not match the staged MATERIALIZED_DIFF would be rewritten to the live fingerprint and pinned as recovered drift, even though the staged provenance was already corrupt.
- **Proposed resolution**: Before rewriting, prove the existing staged snapshot is internally valid: read MATERIALIZED_DIFF as a regular non-symlink and require diff_fingerprint(snapshot_text) == stored_fp. Return False otherwise; only then allow stored_fp != live_fp recovery and rewrite with the live fingerprint.



### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:495-501
- **Concern**: Refresh would recover any non-empty staged fingerprint without proving it matches the staged diff snapshot.. Scenario: A corrupted sidecar with a bogus DIFF_FINGERPRINT and usable repo_root would be rewritten to the live fingerprint, then pinned as a valid durable note. That regresses the corrupt-fingerprint drop path and can ship a stale or misbound guideline note.
- **Proposed resolution**: Before rewriting on drift, read the staged materialized diff snapshot and require diff_fingerprint(snapshot_text) == stored_fp. Return False when the snapshot is missing, unreadable, or mismatched. Add a focused test for non-empty corrupt fingerprint with repo_root.



