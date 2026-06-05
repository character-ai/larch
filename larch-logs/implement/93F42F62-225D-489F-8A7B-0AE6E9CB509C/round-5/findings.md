### FINDING_1: Shared driver phase sentinel allowlist is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Driver phase sentinel basenames are duplicated across `design-log-publish.sh`, `design-driver.sh`, and tests. A future ACTION can re-break pause publish if the publisher allowlist is not updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Pause/resume harness git stub is monolithic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `test-design-pause-resume.sh` has grown a large inline git stub and many scenario blocks, making contract changes hard to isolate and reuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: `.completed` enumeration pattern is inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `.completed` staging uses process-substitution enumeration while sibling loops use mktemp capture, increasing audit complexity for `set -e` safety.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Combined body-drift plus marker-delete-failed loader warning is untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: There is no combined loader test for simultaneous `body-drift` and `marker-delete-failed`, so a regression dropping one WARN line could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Unrelated Python ship changes are bundled with pause/resume fix
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch includes large `python/ship.py`/run-log changes unrelated to the stated pause/resume plan, increasing review, bisect, and revert complexity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Marker-delete failure hides stderr
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `clear_pause_marker` reports `WARN=marker-delete-failed` without surfacing actionable delete failure details.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Dual WARN stdout contract may be lossy for consumers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Separate `WARN=` lines for combined body drift and marker delete failure may cause single-WARN parsers to miss one condition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: Missing route integration test for successful paused resume with lifecycle title
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no `design-route.sh` integration test proving `[DESIGNING]` title plus valid pause marker and successful restore routes to `resume@STEP` instead of title cancellation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: `LOAD_OK=false` pause loads fall through to normal routing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ship-resume-output.txt, dyn-route-contract-output.txt
- **Severity**: important
- **Concern**: When a pause marker is present and loader restore fails, `design-route.sh` can fall through to title filtering, `proceed`, or `already-planned` while the marker remains. This obscures pause-load failure guidance and can start fresh design work with a stale auto-resume pointer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-ship-resume-output.txt: Address the concern above.
  - From dyn-route-contract-output.txt: Address the concern above.

### FINDING_10: Successful restore can resume while stale pause marker remains
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ship-resume-output.txt, dyn-route-contract-output.txt
- **Severity**: important
- **Concern**: `LOAD_OK=true` with `MARKER_CLEARED=false` permits `resume@*` while the issue marker remains live, causing later `/design` invocations to reload stale snapshots or clobber newer tmpdir work without loud operator guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-ship-resume-output.txt: Address the concern above.
  - From dyn-route-contract-output.txt: Address the concern above.

### FINDING_11: Restore install failure can leave dirty tmpdir for retry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A failed `cp -R` install can leave partial files in `DESIGN_TMPDIR`; because the marker remains for retry, a later load into the same tmpdir can merge fresh snapshot files with orphaned partial content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Run-log flush commit is intentional artifact
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The `larch-logs` flush commit is surfaced as an intentional run-log artifact and not a pause/resume plan violation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: Non-retryable pause-load failures keep stale markers
- **Reviewer(s)**: dyn-ship-resume-output.txt
- **Severity**: important
- **Concern**: `emit_load_fail` keeps markers even for permanent validation or binding failures that retrying cannot fix, leaving operators stuck in repeated fail/fallthrough cycles unless they manually edit the marker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-resume-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Ship iteration cap guard is unreachable dead code
- **Reviewer(s)**: dyn-ship-resume-output.txt
- **Severity**: nit
- **Concern**: A post-monitor `iteration > SHIP_MERGE_LOOP_MAX_ITERATIONS` guard appears unreachable because the same check already occurs before monitoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-resume-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] SECURITY symlink wording may be stale
- **Reviewer(s)**: dyn-ship-resume-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` is reported as still claiming the loader rejects extracted symlinks, while the new restore path writes blob bytes and does not materialize git symlinks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-resume-output.txt: Address the concern above.

### FINDING_16: Ship state write validation omits persisted identity fields
- **Reviewer(s)**: dyn-state-hygiene-output.txt
- **Severity**: important
- **Concern**: `_validate_ship_state_value` does not validate fields like `REPO`, `ISSUE_NUMBER`, `RUN_ID`, and `PHASE` before persisting them, relying on later read-side checks instead of fail-closed write hygiene.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-hygiene-output.txt: Address the concern above.

### FINDING_17: Gh-skipped local merge quorum can be satisfied only by state file values
- **Reviewer(s)**: dyn-state-hygiene-output.txt
- **Severity**: important
- **Concern**: Resume logic can treat `local_merged` as true using only persisted `PR_CLOSED` and `MERGE_RESULT`, allowing corrupt or tampered state to advance post-merge finalization without non-state-file corroboration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-hygiene-output.txt: Address the concern above.

### FINDING_18: Ship state rewrites can drop `CONFLICT_FILES`
- **Reviewer(s)**: dyn-state-hygiene-output.txt
- **Severity**: latent
- **Concern**: `_write_ship_state` preserves some disk fields but drops previously persisted `CONFLICT_FILES` unless passed again, weakening conflict handoff metadata across routine rewrites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-hygiene-output.txt: Address the concern above.

### FINDING_19: Restore path lacks destination containment check
- **Reviewer(s)**: dyn-state-hygiene-output.txt
- **Severity**: important
- **Concern**: `design-pause-load.sh` checks relative path segments but does not verify the computed `dest` remains under `$restore_tmp` before writing blobs and copying into `DESIGN_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-hygiene-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] SECURITY symlink doc change is characterized as non-regression
- **Reviewer(s)**: dyn-state-hygiene-output.txt
- **Severity**: nit
- **Concern**: The pause/resume symlink behavior is described as a documentation-alignment point rather than a symlink-extraction regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-hygiene-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Collaborator-editable pause markers remain residual risk
- **Reviewer(s)**: dyn-state-hygiene-output.txt
- **Severity**: latent
- **Concern**: Collaborator-editable `larch:design-pause` markers can still redirect resume to another snapshot for the same issue; WI3 does not change that documented residual risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-hygiene-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Unknown resume fields are silently cleared
- **Reviewer(s)**: dyn-state-hygiene-output.txt
- **Severity**: nit
- **Concern**: Unknown `RESUME_PHASE` and `CALLER_KIND` values read from disk are silently cleared on write, which is conservative but may mask corrupt state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-hygiene-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Body-drift marker lifecycle docs may mislead
- **Reviewer(s)**: dyn-route-contract-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-pause-load.md` body-drift wording predates delete-on-success behavior and may mislead operators about whether successful loads clear the marker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-route-contract-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Simultaneous WARN propagation through route is unverified
- **Reviewer(s)**: dyn-route-contract-output.txt
- **Severity**: nit
- **Concern**: End-to-end propagation of simultaneous `WARN=body-drift` and `WARN=marker-delete-failed` through `design-route.sh` is not covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-route-contract-output.txt: Address the concern above.

### FINDING_25: Remote recovery FETCH_HEAD test does not assert restored result
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: important
- **Concern**: The remote-recovery `FETCH_HEAD` harness checks git stub calls but not `LOAD_OK=true`, restored artifacts, `.resume-loaded`, or marker lifecycle, so wrong ref extraction could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Address the concern above.

### FINDING_26: Git stub does not model commit-object extraction
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: important
- **Concern**: The git stub serves `ls-tree` and `show` from a mutable filesystem tree rather than a pinned commit object, so stub-backed tests can pass despite production ref/blob mismatches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Address the concern above.

### FINDING_27: Export-ignore regression test lacks archive negative control
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: latent
- **Concern**: The real-git export-ignore reproduction proves `ls-tree`/`show` succeeds but does not assert the old `git archive | tar` path fails or omits files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Address the concern above.

### FINDING_28: Local recovery branch test does not assert restored result
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: latent
- **Concern**: The local recovery branch case checks fetch behavior but not `LOAD_OK=true` or restored artifact presence, allowing a broken local restore path to pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Corrupt resume counter tests diverge from bash behavior
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: nit
- **Concern**: Python tests codify silent coercion of corrupt resume counters without comparing behavior against bash `ship-pr.sh` arithmetic on similar state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Ship resume tests rely on monkeypatches instead of gh fixtures
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: latent
- **Concern**: New ship resume tests use heavy monkeypatching rather than parsed `gh` CLI JSON fixtures, so real CLI serde drift would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Address the concern above.
