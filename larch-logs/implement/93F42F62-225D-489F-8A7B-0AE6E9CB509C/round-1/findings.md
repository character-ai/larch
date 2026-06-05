### FINDING_1: BODY_HASH docs imply pause marker remains after successful restore
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-pause-load.md` still describes marker payload authority without clarifying that the HTML marker block is deleted after a successful body-drift resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Driver phase-sentinel allowlist is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/design-log-publish.sh` hardcodes the accepted driver phase sentinels separately from `design-driver.sh`, so future driver actions can break pause publishing unless both lists stay aligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Per-path `git show` restore failure is not pinned by tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-mock-fidelity-output.txt
- **Severity**: latent
- **Concern**: The pause/resume harness implements `GIT_STUB_SHOW_FAIL`, but the extract-failure coverage only exercises `ls-tree` failure. A regression in the per-file `git show` guard could pass while enumeration failures remain covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-mock-fidelity-output.txt: Add a sibling case `GIT_STUB_SHOW_FAIL=1` (snapshot present, enumeration succeeds) expecting `ERROR=snapshot-extract-failed`, marker retained, and no `.resume-loaded`.

### FINDING_4: Stale `archive_ref` variable name after archive removal
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-pause-load.sh` still uses `archive_ref` after replacing `git archive` restore, which can mislead future edits into assuming archive semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Branch mixes unrelated ship/run-log work with pause/resume fix
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-ci-loop-output.txt, dyn-mock-fidelity-output.txt
- **Severity**: latent
- **Concern**: The branch includes unrelated Python ship/resume work and run-log flush commits alongside the design pause/resume commit, making the full branch diff harder to review in isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-ci-loop-output.txt, dyn-mock-fidelity-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Issue-anchored plan docs omit marker deletion semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `docs/issue-anchored-plan.md` does not describe the new post-success pause-marker deletion lifecycle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Pause-load tests do not faithfully cover non-local/default ref restore paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-mock-fidelity-output.txt
- **Severity**: latent
- **Concern**: The stubbed pause-load tests can pass without validating real `FETCH_HEAD`, `origin/main`, or dynamic recovery-branch behavior because the git stub ignores or hardcodes ref handling; only one real-git local recovery path is covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-mock-fidelity-output.txt: Teach the stub to honor the ref argument (e.g. map `FETCH_HEAD` / `origin/main` / `larch-log-design-recovery-*` to committed objects under `$TMP/repo` or a ref→tree fixture), or add real-git cases that commit the snapshot on a fetched remote branch and on `main` with `larch-logs/ export-ignore`, then load without using `$SNAPSHOT_ROOT` as a fake object database.
  - From dyn-mock-fidelity-output.txt: Add stub-free subshell fixtures: (a) snapshot committed only on `larch-log-design-<RUN>` with marker pointing at that branch (exercises `FETCH_HEAD`), and (b) snapshot committed on `main` with no `LOG_RECOVERY_BRANCH` (exercises `origin/main`), both in repos with `larch-logs/ export-ignore`.
  - From dyn-mock-fidelity-output.txt: Derive the allowed ref from the marker’s `LOG_RECOVERY_BRANCH` / `RUN_ID` (or delegate `show-ref` to `$REAL_GIT` against `$TMP/repo` when that repo is populated).

### FINDING_8: Marker retention is not tested for all load-failure tokens
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests assert marker retention for some restore failures, but not for `snapshot-not-found` or restored issue/run/repo mismatch failures, so selective marker deletion could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Non-fatal marker-delete failure can leave resume marker stuck
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: After successful load, `clear_pause_marker` failure only emits a warning while leaving `LOAD_OK=true`. The stale `larch:design-pause` marker can cause later `/design` runs to keep attempting resume or require manual cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Retry delete in design-route after successful load, skip resume when [DESIGNED]+larch:plan exists, or treat WARN=marker-delete-failed as operator-blocking.
  - From dyn-resume-state-output.txt: Treat marker-delete failure as a distinct orchestrator-facing outcome (e.g., `LOAD_OK=true` plus a dedicated `MARKER_CLEARED=false` KV, or escalate to a loud operator halt) so resume success is not conflated with pointer cleanup.

### FINDING_10: Sentinel write failure can leave a partially installed tmpdir
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `cp -R` may populate `DESIGN_TMPDIR` before `.resume-loaded` write fails, leaving partial state that future retries overlay without rollback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Roll back DESIGN_TMPDIR contents on sentinel-write failure, or rename staging dir into place only after sentinel succeeds.

### FINDING_11: [OUT_OF_SCOPE] Unrecoverable pause markers can force repeated resume attempts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Invalid or unrecoverable pause markers are retained on failure, so later `/design` runs may repeatedly attempt the same doomed resume with no fresh-start escape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add route-level bypass or explicit operator gate for unrecoverable marker errors (not in this PR).

### FINDING_12: Python `open-pr` resume skips pending OOS disposition gate
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: `python/ship.py` can resume at `open-pr` and proceed to PR/CI/merge while persisted `OOS_PENDING=true` or accepted/security OOS artifacts remain unresolved, unlike the Bash ship path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: On any resume path where `OOS_PENDING=true` (or accepted-OOS / security-OOS artifacts are present), run the same disposition gate as the fresh `pr-create` path before `ensure_pr`; if disposition is incomplete, return `NEEDS_USER_INPUT` with `NEEDS_USER_OOS_FILING` instead of proceeding.

### FINDING_13: Python fresh-resume fallback resets persisted counters
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-ci-loop-output.txt
- **Severity**: important
- **Concern**: `_fresh_resume_plan` zeroes iteration/rebase/fix/transient counters when resume classification falls back to fresh, allowing a flaky or failed resume check to restore merge-loop budget.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Either stall with a structured resume error when classification fails but counters are non-zero, or carry forward persisted counters on “degrade to fresh” paths instead of unconditionally resetting them in `_fresh_resume_plan`.
  - From dyn-ci-loop-output.txt: If parity with bash resume is required, preserve `read_resume_counters` on gh-failure fallbacks that still have a valid `PR_NUMBER` in state (route to `blocked` / retry rather than `fresh`), or at minimum preserve `iteration` when re-entering the merge loop for an existing PR.

### FINDING_14: Python `gh_skipped` resume can trust stale PR identity
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: In `gh_skipped` mode, `_resume_plan` can classify `open-pr` using persisted `PR_NUMBER` and branch checkout without the `gh pr view` head-ref validation used in normal mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: In `gh_skipped` mode, require an additional local anchor (e.g., persisted `PR_URL` match, `manifest.json` / `parent-issue.md` cross-check, or explicit operator `--pr-number` override) before classifying `open-pr`, or fail closed to `NEEDS_USER_INPUT` when PR identity cannot be corroborated.

### FINDING_15: Python `gh_skipped` resume can treat local manifest `done` as merged
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: important
- **Concern**: In `gh_skipped` mode, manifest status `done` plus a PR number can route to post-merge finalization without remote merge confirmation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: In `gh_skipped` mode, require at least two independent merge signals (e.g., `PR_CLOSED=true` **and** `MERGE_RESULT` in post-merge set, or manifest `done` plus `post-merge-sentinel`) before selecting `merged`; otherwise stay on `open-pr` or stall.

### FINDING_16: [OUT_OF_SCOPE] `done` resume returns OK without terminal artifact verification
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: latent
- **Concern**: `resume.start == "done"` exits successfully without rerunning post-merge or verifying terminal artifacts, so corrupt persisted done state could mask incomplete finalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Python merge-loop cap is one iteration looser than CI/bash cap
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-ci-loop-output.txt
- **Severity**: latent
- **Concern**: Python ship uses `iteration > MAX` while CI decision logic and Bash semantics use `>= MAX`, allowing one extra outer-loop pass in some resume/wait cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Address the concern above.
  - From dyn-ci-loop-output.txt: Align the merge-loop cap with `decide()` / bash by using `iteration >= config.SHIP_MERGE_LOOP_MAX_ITERATIONS`, or document and test that the outer cap is intentionally one step looser than the inner cap.

### FINDING_18: [OUT_OF_SCOPE] Boolean state parsing is duplicated
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: nit
- **Concern**: Boolean parsing logic is duplicated between run-log and ship state paths, creating drift risk over time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Address the concern above.

### FINDING_19: Restored `.pause-requested` can trigger an immediate pause/save loop
- **Reviewer(s)**: dyn-git-plumbing-output.txt
- **Severity**: important
- **Concern**: Successful pause-load restore copies `.pause-requested` from the snapshot into `DESIGN_TMPDIR`; later pause checkpoints can interpret it as a fresh pause request and re-save instead of continuing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-plumbing-output.txt: After a successful install (and before or after marker delete), unconditionally `rm -f "$DESIGN_TMPDIR/.pause-requested"` in `design-pause-load.sh`, or exclude `.pause-requested` from pause publishes in `design-log-publish.sh` even when `--reason pause`; add a harness case that seeds `.pause-requested` in the snapshot and asserts it is absent post-load.

### FINDING_20: Multiple `WARN=` lines can lose `body-drift` under last-wins parsers
- **Reviewer(s)**: dyn-git-plumbing-output.txt
- **Severity**: latent
- **Concern**: When both `body-drift` and marker-delete failure occur, the loader emits two `WARN=` lines; callers using last-wins parsing can drop the earlier drift warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-plumbing-output.txt: Merge warnings into one comma-separated `WARN=body-drift,marker-delete-failed` value (or emit a single structured warning token) when both conditions apply, and extend the optional harness case to assert both tokens are visible on stdout.

### FINDING_21: [OUT_OF_SCOPE] Pause-load git repo resolution ignores `--repo`
- **Reviewer(s)**: dyn-git-plumbing-output.txt, dyn-ci-loop-output.txt
- **Severity**: latent
- **Concern**: `design-pause-load.sh` derives `REPO_TOP` from the caller’s cwd while `--repo` only affects `gh`, so loading from another clone/worktree can read the wrong object database.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-plumbing-output.txt, dyn-ci-loop-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Python fork-mode resume hardcodes base ref `main`
- **Reviewer(s)**: dyn-git-plumbing-output.txt
- **Severity**: latent
- **Concern**: The Python ship/resume refactor uses `base_ref = "main"` with an upstream remote in fork mode, which can miscompare CI/rebase for forks whose default branch is not `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-plumbing-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Terminal stalls normalize `PHASE=stalled`
- **Reviewer(s)**: dyn-ci-loop-output.txt
- **Severity**: nit
- **Concern**: Python terminal stalls write `PHASE=stalled` instead of the descriptive step token; prior rounds treated this as intentional, but it remains a behavioral normalization to be aware of.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-loop-output.txt: Address the concern above.
