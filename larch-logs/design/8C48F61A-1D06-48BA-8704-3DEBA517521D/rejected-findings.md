### [Plan Review] FINDING_1

### FINDING_1: Drift recovery must reject corrupt staged fingerprints before rewrite
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan removes the `fingerprint != stored_fp` bail in `refresh_staged_assessment_for_current_head` (~lines 499–501) so ship-time drift can recover, but it only gates on a non-empty `DIFF_FINGERPRINT`. When `repo_root` is available (normal ship path), a sidecar whose `DIFF_FINGERPRINT` does not match the staged `MATERIALIZED_DIFF` snapshot could still be rewritten to the live fingerprint and pinned as recovered drift. That regresses the corrupt-fingerprint drop path and can ship a stale or misbound guideline note.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Before rewriting, prove the existing staged snapshot is internally valid: read MATERIALIZED_DIFF as a regular non-symlink and require diff_fingerprint(snapshot_text) == stored_fp. Return False otherwise; only then allow stored_fp != live_fp recovery and rewrite with the live fingerprint.
  - From Codex-Pragmatic: Before rewriting on drift, read the staged materialized diff snapshot and require diff_fingerprint(snapshot_text) == stored_fp. Return False when the snapshot is missing, unreadable, or mismatched. Add a focused test for non-empty corrupt fingerprint with repo_root.

