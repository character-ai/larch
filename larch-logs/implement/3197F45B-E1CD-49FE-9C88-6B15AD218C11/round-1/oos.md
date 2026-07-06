### FINDING_4: [OUT_OF_SCOPE] Implement shell writer misses the arm-time clear
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `skills/implement/scripts/run-step-checks.sh` still omits the new `no-progress-stop-block-emitted` arm-time clear. A second implement bg-wait in the same tmpdir may therefore fail to Stop-block again. This is outside the design task-output clamp scope, but the stale-state problem is the same class of bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Parity lint does not cover the new sidecar clears
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-hook-state
- **Severity**: minor
- **Concern**: `python/larch/lint/lint_bg_wait_writer_parity.py` still tracks bg-wait writers only for `CLONE_PATH=` emission, so the new arm-time sidecar clears are not mechanically enforced. That leaves Bash writer drift unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-hook-state: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] Stop-block emission is brittle when the touch fails
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: In `scripts/hook-no-progress-guard.sh`, Stop-block emission depends on the `stop-block-emitted` touch succeeding. If that touch fails, the breaker may arm but the direct Stop JSON never appears, so only `UserPromptSubmit` can still block. That makes Stop support platform-sensitive in a way the hook should not silently rely on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Arm-time tests still miss the Bash Step 3 path
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-hook-state
- **Severity**: minor
- **Concern**: The arm-time coverage in `scripts/test-hook-no-progress-guard.sh` and `scripts/test-hook-bg-poll-guard.sh` only exercises the Python bg-wait helpers, not the Bash Step 3 writer. That means the shell-path stale-sidecar regression can still ship without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-hook-state: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] `task_output_read_clamp` only updates the first matching marker
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `scripts/hook-bg-poll-guard.sh` updates only the first matching design-step marker and returns. In the rare case of overlapping design markers, later markers can under-count the clamp budget, which skews the read side of the notification recovery path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Marker exit cleanup leaves sidecars behind
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Sidecar reset on marker removal still depends on the marker surviving discovery. If the EXIT trap deletes the marker without that discovery path running first, the sidecars can remain until a manual clear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_12: [OUT_OF_SCOPE] Stop handling can emit duplicate JSON when multiple markers trip together
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The Stop handler can emit more than one block JSON when multiple live markers reach threshold in the same event. That is an old multi-marker edge, but it can still produce malformed multi-envelope Stop output in rare same-clone sessions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Step 3 wrapper exit does not clear sidecars
- **Reviewer(s)**: dyn-dyn-hook-state
- **Severity**: minor
- **Concern**: `skills/design/scripts/design-step3-review.sh` removes `.bg-wait-active` on wrapper exit but does not clear the no-progress or task-output-read sidecars itself. Cleanup still depends entirely on hook liveness paths, which makes stale-sidecar windows wider when Bash re-arm omits the new clears.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-state: Address the concern above.
Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

