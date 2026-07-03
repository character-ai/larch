### FINDING_1: Avoid unbaselined direct subprocess in `materialize_implementation_diff`
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-dyn-Git Snapshot Correctness
- **Severity**: important
- **Concern**: The plan adds a third direct `subprocess.run` path in `materialize_implementation_diff` for HEAD resolution without accounting for the subprocess-via-runner ratchet. That can leave the new call unbaselined and make lint or CI fail even if the rest of the change is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Revise the plan to route the new HEAD resolution through the existing `larch.core.proc.run` seam, or explicitly include the required narrow subprocess-via-runner exemption/baseline update and corresponding lint check.
  - From Codex-Innovation: Use the existing larch.core.proc.run seam for the HEAD, merge-base, and diff calls in this helper, or otherwise avoid adding a new direct subprocess occurrence; update the focused test to monkeypatch that seam rather than adding baseline churn
  - From Codex-Pragmatic: Use larch.core.proc.run for the new HEAD resolution, or include the required inline suppression or baseline update and verify with make py-lint-checks-fast.
  - From Codex-dyn-Git Snapshot Correctness: Resolve HEAD through larch.core.proc.run or another existing compliant runner seam, and update the unit test to patch that seam. If direct subprocess.run is intentionally kept, include the required lint baseline or justified suppression and run py-lint.

### FINDING_2: Thread a frozen head through closeout and stale-note fallback
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements, Codex-dyn-Git Snapshot Correctness
- **Severity**: important
- **Concern**: The plan still lets live HEAD leak into `materialize_implementation_diff` and related fallback paths instead of carrying forward the head already pinned by closeout or durable-note metadata. That leaves a race where a note can be fingerprinted against a later HEAD and then judged stale or written with mismatched metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Thread a frozen expected head into _materialize_live_diff or materialize_implementation_diff for closeout and note_fingerprint_stale, or recheck HEAD before the live fallback and skip or fail closed when it differs.
  - From Codex-Requirements: Revise the plan so `note_fingerprint_stale` performs its fallback against a frozen expected head from durable metadata, for example by passing `HEAD_SHA` into a narrowly extended materialization helper, and add a focused test that the fallback diffs `<base_sha>..<durable HEAD_SHA>` rather than live `HEAD`.
  - From Codex-dyn-Git Snapshot Correctness: Thread the existing pinned head through the shared path. Let materialize_implementation_diff accept an optional frozen head SHA, or add an equivalent internal helper. Have pin_note_from_staged_for_current_head pass its head_sha and note_fingerprint_stale pass durable HEAD_SHA. Keep default live HEAD for CLI callers.
