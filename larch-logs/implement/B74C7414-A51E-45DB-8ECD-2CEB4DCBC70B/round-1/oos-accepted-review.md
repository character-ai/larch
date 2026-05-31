### FINDING_12: [OUT_OF_SCOPE] Carryover tests remain dispatch-shard only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No Makefile or CI shard change was made for additional carryover coverage; full harness execution remains manual unless new Step 5 tests are assigned to a shard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_13: [OUT_OF_SCOPE] Post-coder head remains coder-writable telemetry input
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-snapshot-boundary-output.txt
- **Severity**: latent
- **Concern**: `post-coder-head.txt` remains in coder-writable `round_dir` and feeds `structural_loc` or bulk-skip telemetry. This does not affect the carryover commit guard but could skew loop telemetry if tampered with.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-snapshot-boundary-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_15: [OUT_OF_SCOPE] Shared tmp snapshot permissions may allow local tampering
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Snapshots stored on shared `/tmp`-like locations may not be owner-only or immutable, allowing another local process to edit `.pre-coder-snapshots` before carryover checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_16: [OUT_OF_SCOPE] Default implement path likely benefits from relocation
- **Reviewer(s)**: dyn-snapshot-boundary-output.txt
- **Severity**: nit
- **Concern**: The default `/implement` path places `IMPLEMENT_TMPDIR` under `~/.cache/larch/sessions/`, outside the clone, so the branch likely improves the happy-path trust boundary even if other grant layouts remain a concern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-snapshot-boundary-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_17: [OUT_OF_SCOPE] Main implement Codex grant is wider than Step 5 grant
- **Reviewer(s)**: dyn-snapshot-boundary-output.txt
- **Severity**: latent
- **Concern**: `scripts/launch-codex-implement.sh` grants the entire session tmpdir via `--add-dir "$SESSION_TMPDIR"`, unlike the narrower Step 5 grant; this is pre-existing and outside this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-snapshot-boundary-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_18: [OUT_OF_SCOPE] MAV rounds preserve prior fail-closed behavior
- **Reviewer(s)**: dyn-snapshot-boundary-output.txt
- **Severity**: nit
- **Concern**: `run_implement_mav_apply` relocates only `pre-coder-head.txt` and does not call `snapshot_pre_coder_tracked_state`, preserving prior fail-closed carryover behavior for tracked paths on MAV rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-snapshot-boundary-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_6: [OUT_OF_SCOPE] In-repo tmpdir leaves snapshots inside granted repo root
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-boundary-output.txt
- **Severity**: important
- **Concern**: If `IMPLEMENT_TMPDIR` or snapshot storage is under the repository, snapshots may remain reachable through Codex/Cursor write roots such as `--add-dir "$PWD"` or the workspace, so relocation alone does not guarantee snapshot integrity. Several reviewers classify this as a separate hardening or sandbox-boundary follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-boundary-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_7: [OUT_OF_SCOPE] Parser shard lacks review-and-fix helper source
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: A parser test shard sources `step5-loop` without the review-and-fix helpers, so a future parser test calling `run_implement_loop` could hit an undefined `pre_coder_snapshot_dir`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_9: [OUT_OF_SCOPE] Test invariant does not enforce separation from all coder grants
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-snapshot-boundary-output.txt
- **Severity**: latent
- **Concern**: The test only proves snapshots are not under `round_dir`; it does not prove they are outside `$PWD`, the fixture repo root, or all coder grant roots. A nested or repo-local tmpdir could satisfy the current assertion while remaining writable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-snapshot-boundary-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


