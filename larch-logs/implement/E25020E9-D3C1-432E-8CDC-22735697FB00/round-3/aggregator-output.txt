### FINDING_1: write-design-current-env misses repo binding
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Resume and 5.5-bis refresh `write-design-current-env.sh` without `--repo`, so cross-repo resume can lose the bound repo and pause/prelude operations may target the wrong GitHub issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: defensive pause prelude misses repo binding
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The Bash prelude invokes `design-pause-save.sh` without passing the pause-time `REPO`, so defensive `.pause-requested` saves can resolve the wrong repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: duplicated marker parsing logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `design-pause-save.sh` and `design-pause-load.sh` duplicate awk logic for stripping/parsing `larch:design-pause` markers, risking inconsistent behavior if marker grammar changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: restored artifacts installed before marker delete failure handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `design-pause-load.sh` installs restored artifacts into `DESIGN_TMPDIR` before deleting the pause marker. If marker deletion fails, Step 0b may continue as a fresh run with a polluted tmpdir while the marker remains, creating hybrid retry state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] duplicate completion sentinel instructions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Duplicate Step 1c/1d completion-sentinel prose can confuse authors or cause `.completed` to be written before step body work actually finishes, allowing resume to skip unfinished discussion work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: pause-state redaction runs twice
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `design-pause-save.sh` redacts pause-state twice on the recovery-branch path, adding minor redundant I/O.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] duplicated resolve_repo helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `resolve_repo` is copy-pasted across scripts, creating a pre-existing maintenance cost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] emit_fail exits successfully
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `design-pause-save.sh` reports `PAUSE_OK=false` while exiting 0, so shell wrappers or defensive preludes that check only `$?` can treat pause failure as success and continue the in-flight step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: pause sentinel has no shipped producer
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The defensive `.pause-requested` prelude is present, but shipped `/larch:pause` does not arm that sentinel, so mid-Bash deferral and `/loop` pause scenarios do not actually trigger outside tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: recovery-only publish reports pause success too quietly
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: When publish falls back to `RECOVERY_BRANCH`, `design-pause-save.sh` can still emit `PAUSE_OK=true` without a stdout warning, so operators may believe the default branch contains the latest snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: pause/resume test stub lacks manifest
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The offline publish stub in `test-design-pause-resume.sh` omits `manifest.json`, but `design-pause-load.sh` requires it, leaving the pause/resume harness red with `missing-restored-artifact`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: recovery branch validation is not tied to RUN_ID
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `LOG_RECOVERY_BRANCH` accepts any `larch-log-design-*` ref instead of requiring a branch derived from the validated `RUN_ID`, allowing attacker-controlled restored artifacts under a victim run id if an editor can modify the issue and push a branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: issue number is persisted too late for pause
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `ISSUE_NUMBER` is not written to session env until later substeps, so invoking `/larch:pause` after issue fetch but before rename can exit with nothing to pause while `/design` is mid-run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: manifest validation assumes jq exists
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `design-pause-load.sh` validates `manifest.json` with `jq` but does not guard for missing `jq`, producing a shell failure instead of structured `LOAD_OK=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: publish push failure omits recovery branch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `design-log-publish.sh` preserves a local recovery ref on push failure but does not emit `RECOVERY_BRANCH`, causing pause save to fail closed without surfacing the recoverable local commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] empty-porcelain pause publish may reuse stale manifest
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The empty-porcelain pause path can report success from an existing default-branch manifest, which may let pause-save write a marker that does not reflect the current tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] registry skips legacy step id 5
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The registry walk skips step id 5 while a row 5 finalize entry remains in the TSV, so legacy `.completed/step-5` state could produce incorrect resume selection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: missing registry-order resume test case
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The pause/resume harness lacks the plan-required case where only step-1c and step-2a sentinels exist, so a buggy max-completed-step walk could resume at the wrong step without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_19: missing force-with-lease remote branch reuse test
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-design-log-publish.sh` lacks the plan-required two-pass pause publish fixture for an existing remote `larch-log-design-<RUN_ID>` branch, so branch reuse regressions may not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] pause skill size differs from plan estimate
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Shipped `/larch:pause` prose is shorter than the plan estimate; reviewer reports no functional breakage and only optional documentation/spec alignment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
