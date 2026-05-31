### FINDING_1: Duplicated pre-coder head resolution
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Two residue functions duplicate pre-coder head loading logic, risking silent divergence between carryover and follow-up behavior if one path is updated without the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Inconsistent pre-coder head path construction
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Pre-coder head path construction is inconsistent across call sites, so future readers may assemble the path incorrectly and miss the relocated snapshot directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Snapshot location invariant overclaims protection from coder grants
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-boundary-output.txt
- **Severity**: important
- **Concern**: The documented or tested invariant focuses on snapshots being outside `round_dir`, but does not fully ensure they are outside `$PWD` or other Codex/Cursor write grants. If `IMPLEMENT_TMPDIR` is inside the repo or another granted root, relocated snapshots may remain writable and the tamper-resistance claim is overstated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-boundary-output.txt: Address the concern above.

### FINDING_4: Location test only checks subdirectory case
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The location test verifies only that the snapshot directory is not under `round_dir/`; a broken helper returning exactly `round_dir` could still pass unless the test checks the full prefix inequality expected by the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Missing Step 5 structural_loc coverage for relocated pre-coder head
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: No test asserts that `review-implement-step5-loop.sh` reads `pre-coder-head.txt` from the relocated snapshot directory when computing `structural_loc`. A regression could leave `structural_loc=0`, causing substantial-round or bulk-skip gates to misfire without current tests failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] In-repo tmpdir leaves snapshots inside granted repo root
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-boundary-output.txt
- **Severity**: important
- **Concern**: If `IMPLEMENT_TMPDIR` or snapshot storage is under the repository, snapshots may remain reachable through Codex/Cursor write roots such as `--add-dir "$PWD"` or the workspace, so relocation alone does not guarantee snapshot integrity. Several reviewers classify this as a separate hardening or sandbox-boundary follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-boundary-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Parser shard lacks review-and-fix helper source
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: A parser test shard sources `step5-loop` without the review-and-fix helpers, so a future parser test calling `run_implement_loop` could hit an undefined `pre_coder_snapshot_dir`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Cross-version resume may miss legacy round_dir snapshots
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Resuming mid-round from an older layout can leave the relocated snapshot pre-coder head empty while legacy snapshots remain under `round_dir`, causing full dirty capture and possible carryover of paths that old code would have excluded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Test invariant does not enforce separation from all coder grants
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-snapshot-boundary-output.txt
- **Severity**: latent
- **Concern**: The test only proves snapshots are not under `round_dir`; it does not prove they are outside `$PWD`, the fixture repo root, or all coder grant roots. A nested or repo-local tmpdir could satisfy the current assertion while remaining writable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-snapshot-boundary-output.txt: Address the concern above.

### FINDING_10: MAV apply head relocation lacks dedicated test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `run_implement_mav_apply` has no dedicated test proving it writes the relocated `pre-coder-head.txt`; a regression could write back to `round_dir` and keep `structural_loc=0` for MAV resume paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Full dispatch carryover test does not assert snapshot file placement
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The carryover-orchestrator test does not assert that pre-coder artifacts are created under the snapshot directory and absent from `round_dir`, so a writer placement regression might escape unit coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Carryover tests remain dispatch-shard only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No Makefile or CI shard change was made for additional carryover coverage; full harness execution remains manual unless new Step 5 tests are assigned to a shard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Post-coder head remains coder-writable telemetry input
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-snapshot-boundary-output.txt
- **Severity**: latent
- **Concern**: `post-coder-head.txt` remains in coder-writable `round_dir` and feeds `structural_loc` or bulk-skip telemetry. This does not affect the carryover commit guard but could skew loop telemetry if tampered with.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-snapshot-boundary-output.txt: Address the concern above.

### FINDING_14: Snapshot diff errors are swallowed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Snapshot `git diff` failures are masked with `|| true`; while this may fail closed for commit safety, it gives no indication that snapshot I/O partially failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Shared tmp snapshot permissions may allow local tampering
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Snapshots stored on shared `/tmp`-like locations may not be owner-only or immutable, allowing another local process to edit `.pre-coder-snapshots` before carryover checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Default implement path likely benefits from relocation
- **Reviewer(s)**: dyn-snapshot-boundary-output.txt
- **Severity**: nit
- **Concern**: The default `/implement` path places `IMPLEMENT_TMPDIR` under `~/.cache/larch/sessions/`, outside the clone, so the branch likely improves the happy-path trust boundary even if other grant layouts remain a concern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-snapshot-boundary-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Main implement Codex grant is wider than Step 5 grant
- **Reviewer(s)**: dyn-snapshot-boundary-output.txt
- **Severity**: latent
- **Concern**: `scripts/launch-codex-implement.sh` grants the entire session tmpdir via `--add-dir "$SESSION_TMPDIR"`, unlike the narrower Step 5 grant; this is pre-existing and outside this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-snapshot-boundary-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] MAV rounds preserve prior fail-closed behavior
- **Reviewer(s)**: dyn-snapshot-boundary-output.txt
- **Severity**: nit
- **Concern**: `run_implement_mav_apply` relocates only `pre-coder-head.txt` and does not call `snapshot_pre_coder_tracked_state`, preserving prior fail-closed carryover behavior for tracked paths on MAV rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-snapshot-boundary-output.txt: Address the concern above.
