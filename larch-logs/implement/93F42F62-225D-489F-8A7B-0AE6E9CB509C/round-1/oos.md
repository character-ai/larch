### FINDING_11: [OUT_OF_SCOPE] Unrecoverable pause markers can force repeated resume attempts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Invalid or unrecoverable pause markers are retained on failure, so later `/design` runs may repeatedly attempt the same doomed resume with no fresh-start escape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add route-level bypass or explicit operator gate for unrecoverable marker errors (not in this PR).


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] `done` resume returns OK without terminal artifact verification
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: latent
- **Concern**: `resume.start == "done"` exits successfully without rerunning post-merge or verifying terminal artifacts, so corrupt persisted done state could mask incomplete finalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] Python merge-loop cap is one iteration looser than CI/bash cap
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-ci-loop-output.txt
- **Severity**: latent
- **Concern**: Python ship uses `iteration > MAX` while CI decision logic and Bash semantics use `>= MAX`, allowing one extra outer-loop pass in some resume/wait cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Address the concern above.
  - From dyn-ci-loop-output.txt: Align the merge-loop cap with `decide()` / bash by using `iteration >= config.SHIP_MERGE_LOOP_MAX_ITERATIONS`, or document and test that the outer cap is intentionally one step looser than the inner cap.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] Boolean state parsing is duplicated
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: nit
- **Concern**: Boolean parsing logic is duplicated between run-log and ship state paths, creating drift risk over time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] Pause-load git repo resolution ignores `--repo`
- **Reviewer(s)**: dyn-git-plumbing-output.txt, dyn-ci-loop-output.txt
- **Severity**: latent
- **Concern**: `design-pause-load.sh` derives `REPO_TOP` from the caller’s cwd while `--repo` only affects `gh`, so loading from another clone/worktree can read the wrong object database.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-plumbing-output.txt, dyn-ci-loop-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] Python fork-mode resume hardcodes base ref `main`
- **Reviewer(s)**: dyn-git-plumbing-output.txt
- **Severity**: latent
- **Concern**: The Python ship/resume refactor uses `base_ref = "main"` with an upstream remote in fork mode, which can miscompare CI/rebase for forks whose default branch is not `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-plumbing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] Terminal stalls normalize `PHASE=stalled`
- **Reviewer(s)**: dyn-ci-loop-output.txt
- **Severity**: nit
- **Concern**: Python terminal stalls write `PHASE=stalled` instead of the descriptive step token; prior rounds treated this as intentional, but it remains a behavioral normalization to be aware of.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-loop-output.txt: Address the concern above.

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_3: [OUT_OF_SCOPE] Per-path `git show` restore failure is not pinned by tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-mock-fidelity-output.txt
- **Severity**: latent
- **Concern**: The pause/resume harness implements `GIT_STUB_SHOW_FAIL`, but the extract-failure coverage only exercises `ls-tree` failure. A regression in the per-file `git show` guard could pass while enumeration failures remain covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-mock-fidelity-output.txt: Add a sibling case `GIT_STUB_SHOW_FAIL=1` (snapshot present, enumeration succeeds) expecting `ERROR=snapshot-extract-failed`, marker retained, and no `.resume-loaded`.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] Branch mixes unrelated ship/run-log work with pause/resume fix
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-ci-loop-output.txt, dyn-mock-fidelity-output.txt
- **Severity**: latent
- **Concern**: The branch includes unrelated Python ship/resume work and run-log flush commits alongside the design pause/resume commit, making the full branch diff harder to review in isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-ci-loop-output.txt, dyn-mock-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] Issue-anchored plan docs omit marker deletion semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `docs/issue-anchored-plan.md` does not describe the new post-success pause-marker deletion lifecycle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] Pause-load tests do not faithfully cover non-local/default ref restore paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-mock-fidelity-output.txt
- **Severity**: latent
- **Concern**: The stubbed pause-load tests can pass without validating real `FETCH_HEAD`, `origin/main`, or dynamic recovery-branch behavior because the git stub ignores or hardcodes ref handling; only one real-git local recovery path is covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-mock-fidelity-output.txt: Teach the stub to honor the ref argument (e.g. map `FETCH_HEAD` / `origin/main` / `larch-log-design-recovery-*` to committed objects under `$TMP/repo` or a ref→tree fixture), or add real-git cases that commit the snapshot on a fetched remote branch and on `main` with `larch-logs/ export-ignore`, then load without using `$SNAPSHOT_ROOT` as a fake object database.
  - From dyn-mock-fidelity-output.txt: Add stub-free subshell fixtures: (a) snapshot committed only on `larch-log-design-<RUN>` with marker pointing at that branch (exercises `FETCH_HEAD`), and (b) snapshot committed on `main` with no `LOG_RECOVERY_BRANCH` (exercises `origin/main`), both in repos with `larch-logs/ export-ignore`.
  - From dyn-mock-fidelity-output.txt: Derive the allowed ref from the marker’s `LOG_RECOVERY_BRANCH` / `RUN_ID` (or delegate `show-ref` to `$REAL_GIT` against `$TMP/repo` when that repo is populated).


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

