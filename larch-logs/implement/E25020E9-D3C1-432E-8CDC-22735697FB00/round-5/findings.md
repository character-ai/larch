### FINDING_1: Bash fence pause-check regex misses canonical prelude shape
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` rejects compliant `SKILL.md` Bash preludes because its regex does not allow the current canonical lines such as `LARCH_PAUSE_REQUIRE_SUCCESS=1` and the repo argument expansion before `exec`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: SECURITY.md misstates pause load ordering and delete-failure behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` says pause marker deletion happens before tmpdir install and implies delete failure prevents partial restore, but the loader installs first and then deletes the marker. This misdocuments the security and recovery behavior, especially for `marker-delete-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: marker-delete-failed can leave restored state and continue as a fresh run
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `design-pause-load.sh` copies the restored snapshot into `DESIGN_TMPDIR` before marker deletion; if marker deletion fails, Step 0b treats `LOAD_OK=false` as fresh-run continuation, leaving restored artifacts in place and allowing new run state to mix with stale restored state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Duplicate design step sentinel instructions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` contains duplicate success-boundary sentinel instructions for migrated steps, creating two write points for the same sentinels and maintenance ambiguity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_5: Divergent repo resolution helpers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `named-block-write.sh` and pause helpers carry separate `resolve_repo` implementations, risking inconsistent repo fallback behavior between plan block writes and pause save/load.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: SECURITY.md omits supported recovery branch prefix
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` documents only the `larch-log-design-RUN_ID` recovery branch path and omits the supported `larch-log-design-recovery-RUN_ID` local recovery branch accepted by `design-pause-load.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Duplicated marker malformed-classification logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Marker malformed-classification logic is duplicated between `plan-block-read.sh` and `named-block-write.sh`, so future marker grammar changes may require coordinated edits in multiple places.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: plan.txt validation is step-gated despite documented mandatory restore artifact
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `design-pause-load.sh` does not always require `plan.txt` for restored snapshots. Early or Step 2b resumes can report `LOAD_OK=true` without `plan.txt`, conflicting with the plan/harness expectation that missing restored artifacts fail or requiring explicit documentation of step-gated reconstruction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: /larch:pause arms deferral sentinel before synchronous save
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `skills/pause/SKILL.md` writes `.pause-requested` before directly invoking `design-pause-save.sh`, mixing synchronous pause behavior with deferred boundary handling and allowing double-save or later prelude failures after an inline pause failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: Pause publish loses recovery branch on log-branch worktree conflict
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `design-log-publish.sh` can fail with no `RECOVERY_BRANCH` when the log branch is checked out in another worktree, even if an existing remote branch could be reported for recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Pause restore lacks post-extract symlink and containment checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `design-pause-load.sh` extracts and copies restored snapshot contents without the post-extract symlink and path containment checks used on publish staging, allowing a compromised fetched log tree to place unsafe paths into the operator session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: Pause marker trust boundary allows same-issue snapshot swap
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The pause marker can be edited by anyone with issue-body edit rights, and the binding checks allow replacement with another snapshot for the same issue number, so a collaborator could redirect resume to a hostile same-issue snapshot without clear operator warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: Pause during Step 0b can skip clarify handling on resume
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A pause during Step 0b before Step 0c records `STEP=0c`; resume then skips Step 0b, including clarification handling, so pending `needs-design-clarification` work may never run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: Unloadable snapshot can leave a permanent pause marker
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If a snapshot is unrecoverable, such as `snapshot-not-found`, repeated `/design` runs retry load and then start fresh while the pause marker remains, requiring manual issue-body cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Marker deletion before route creates crash window
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: After a successful load, the marker is deleted before the orchestrator routes to the restored step. A crash in that window removes the issue-body resume pointer, making later `/design` unable to resume from the issue alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: Restore archive uses mutable FETCH_HEAD
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `design-pause-load.sh` archives from `FETCH_HEAD` after fetch; a concurrent fetch could repoint `FETCH_HEAD` and cause restore from the wrong snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Empty porcelain pause can succeed with stale manifest
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `design-log-publish.sh` can allow a pause with no porcelain delta when a manifest already exists by default, so re-pausing with `--run-id` may skip staging fresh sentinels while still writing a marker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
