### FINDING_1: Write-once on result env does not protect `final-summary.md`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-race-correctness, Cursor-dyn-shell-risk
- **Severity**: important
- **Concern**: A concurrent or follow-up `design-publish.sh` / Step 5c invocation can still delete and re-render `final-summary.md` with `failed-publish` (via `SUMMARY_OUTCOME`, `stage_design_terminal_state`, and `render-final-summary.sh`) before or regardless of `write_result_env_and_emit` refusing to clobber `.design-publish-result.env` when it already has `PUBLISH_OK=true`. Step 5c then verbatim-emits the failed-publish summary while `read-result-env` may still read success, so the operator sees a false `failed-publish` report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Before SUMMARY_OUTCOME/render-final-summary read existing .design-publish-result.env; when PUBLISH_OK=true coerce approved outcome and skip failed-publish render
  - From Cursor-Innovation: Reuse result_env_publish_ok_is_true before the SUMMARY_OUTCOME block: when the existing env already has PUBLISH_OK=true treat the invocation as publish success (SUMMARY_OUTCOME=approved skip failed-publish staging) and do not re-render final-summary.md with failed-publish
  - From Cursor-Pragmatic: Before rendering failed-publish check whether .design-publish-result.env already has PUBLISH_OK=true and skip regressive summary overwrite or re-render approved after a skipped env write when the on-disk env still says true.
  - From Cursor-Requirements: Before log publish (or at publish-phase entry), short-circuit when .design-publish-result.env already has PUBLISH_OK=true: skip summary deletion, skip design-log-publish.sh, and keep or re-render approved summary; or apply the same write-once guard before render-final-summary.sh
  - From Cursor-dyn-race-correctness: Mirror the write-once guard for summary: if result_env_publish_ok_is_true before rm or render skip rm and render-final-summary when in-memory PUBLISH_OK is not true; or short-circuit the publish tail when the result env already records success
  - From Cursor-dyn-shell-risk: Before assigning SUMMARY_OUTCOME=failed-publish, calling stage_design_terminal_state failed-publish, or render-final-summary.sh, consult the planned result_env_publish_ok_is_true helper on $RESULT_ENV. When it is true, keep SUMMARY_OUTCOME=approved, skip failed-publish staging, and do not re-render final-summary.md for this invocation.


### FINDING_2: Merged-branch early exit is not limited to `REASON=final`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned merged-branch idempotent early exit is not gated to `REASON=final` only. A pause no-delta path that must stay fail-closed with `RECOVERY_BRANCH` could incorrectly become `PUBLISH_OK=true` silent success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Gate merge-base idempotent early exit to REASON=final only; keep pause semantics unchanged


### FINDING_3: Write-once allows true-success retry to clobber PR metadata
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Write-once preservation of `PUBLISH_OK=true` does not protect other result-env fields. An idempotent merged-branch early exit can return empty PR fields, and a full result-env replace can drop `PR_NUMBER` / `PR_URL` from the first successful run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When existing PUBLISH_OK=true skip entire write or merge preserved keys from existing result env before write


### FINDING_4: Result-env write-once check is not atomic under concurrency
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-dyn-race-correctness, Codex-dyn-shell-risk
- **Severity**: important
- **Concern**: The planned result-env write-once guard is check-then-write (TOCTOU), not mutually exclusive under concurrent Step 5c invocations. A failure process can observe no existing `PUBLISH_OK=true`, then a success process writes `PUBLISH_OK=true`, then the failure process resumes and overwrites it with `PUBLISH_OK=false` via `phase_driver_write_result_env` / `mv`. Sequential seed tests would not catch this interleaving.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Use a small shared lock or equivalent atomic compare/write around all .design-publish-result.env writes. Re-check existing PUBLISH_OK=true inside the lock before non-true writes.
  - From Codex-Innovation: Make the read-existing-success check and final write mutually exclusive for RESULT_ENV, for example with a small mkdir lock around check plus phase_driver_write_result_env
  - From Codex-dyn-race-correctness: Serialize only the RESULT_ENV read/write decision with a small lock, or add CAS-like writer behavior. Under that guard, re-read the last PUBLISH_OK before any non-true write. Add a focused interleaving regression.
  - From Codex-dyn-shell-risk: Put the existing-success check and phase_driver_write_result_env call inside a small RESULT_ENV critical section, or add an equivalent conditional write helper for this file. Serialize only the result-env write, not the publish flow. Keep symlink refusal delegated to phase_driver_write_result_env and leave the existing symlink test unchanged.


### FINDING_5: Merged-branch idempotency uses a possibly stale `origin/<default>` ref
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The planned merged-branch idempotency check compares against a possibly stale `origin/$ORIGIN_DEFAULT`. After `gh pr merge`, local `origin/main` may not include the merge if only the log branch was fetched. `merge-base --is-ancestor` can then miss an already-merged branch and fall through to concurrent/failure paths that still produce `PUBLISH_OK=false` or a false failed-publish summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Best-effort fetch origin/$ORIGIN_DEFAULT before merge-base, then run the ancestry check against the refreshed default ref.
  - From Codex-Innovation: Best-effort fetch origin/$ORIGIN_DEFAULT before the merge-base check, while keeping fetch failures non-fatal
  - From Codex-Pragmatic: Add a best-effort fetch of the default branch before the new merge-base check; make the planned merged-branch regression leave local origin/<default> stale until the script fetches it
  - From Codex-Requirements: Fetch origin/$ORIGIN_DEFAULT best-effort before the merge-base check, and add the merged-branch regression with a stale local origin/<default> ref so the idempotent success path proves it uses fresh default-branch state.


### FINDING_6: Merged-branch early exit uses a squash-incompatible ancestry predicate
- **Reviewer(s)**: Codex-dyn-shell-risk
- **Severity**: important
- **Concern**: Design-log PRs merge with `gh pr merge --squash --delete-branch`, so the remote branch head is not an ancestor of `origin/default` after a normal successful publish. Combined with fetching only the log branch (leaving `origin/default` stale), a retry can miss idempotent success and continue into the concurrent/failure path even when the run tree is already on the default branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-shell-risk: Fetch origin/default fail-soft along with the log branch, then base early success on the run tree being present or equal on refreshed origin/default instead of merge-base ancestry. Update the planned regression to simulate a squash-style default commit.


### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:347-391; skills/design/scripts/design-step5c.sh:227-259
- **Concern**: [SCOPE-REDUCTION] Write-once guard also preserves old success when the current run has no PUBLISH_OK. Scenario: design-step5c.sh reads result env file-first. After a plan-write failure or validator failure, it can load stale PLAN_WRITE_OK=true and PUBLISH_OK=true from a prior success.
- **Proposed resolution**: Limit the skip to publish failures that set PUBLISH_OK=false, or force stdout-only parse for rc1 and rc4 if preserving missing PUBLISH_OK remains required.


### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:3; plan.txt:19-22; scripts/design-log-publish.sh:884-887
- **Concern**: [SCOPE-REDUCTION] Merged-branch idempotency uses merge-base --is-ancestor but production merge is squash --delete-branch. Scenario: After a successful log publish gh pr merge uses squash and deletes the branch so the remote tip is not an ancestor of origin/main. The early exit never fires when the remote ref still exists or when only main holds the logs. RC-3 idempotency and the proposed harness miss the stated goal.
- **Proposed resolution**: Replace merge-base --is-ancestor with the existing main-tree probe: when origin/$ORIGIN_DEFAULT already contains larch-logs/design/$RUN_ID emit PUBLISH_OK=true and exit before the concurrent-worktree guard. Run this check even when REMOTE_BRANCH_EXISTS is false so it works after branch deletion.


### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:347-391
- **Concern**: [SCOPE-REDUCTION] Write-once guard is planned for every non-true or missing PUBLISH_OK, not just publish-attempt failures. Scenario: A retry that hits validation defects or plan-block write failure after an earlier success would keep the old PUBLISH_OK=true result env; design-step5c reads the file first on rc 1 or 4 and can mark step-5c complete and cleanup-eligible despite the current failure
- **Proposed resolution**: Narrow the skip-write condition to after plan write succeeded and a design-log-publish attempt ran, for example PLAN_WRITE_OK=true and SESSION_ID nonempty or an explicit PUBLISH_ATTEMPTED=true; let validation and plan-write failures overwrite stale success


### FINDING_10:
- **Reviewer(s)**: Codex-dyn-shell-risk
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:15-18; scripts/design-log-publish.sh:275-279; scripts/design-log-publish.sh:955-958; scripts/design-log-publish.md:159-161; scripts/test-design-log-publish.sh:930-960
- **Concern**: [SCOPE-REDUCTION] Unconditional REMOTE_BRANCH_EXISTS widens final-mode branch reuse. Scenario: REMOTE_BRANCH_EXISTS currently also controls WT_BASE_REF. Making it true for final mode causes final publishes with an unmerged remote log branch to base the worktree on origin/WT_BRANCH and push a fast-forward, instead of preserving the current final push/recovery path. That changes worktree creation and push flow outside the issue.
- **Proposed resolution**: Split remote detection from branch reuse. Keep the new remote-exists flag for recovery and idempotent checks, but gate WT_BASE_REF=origin/$WT_BRANCH to REASON=pause unless the early idempotent success already exited. Add or adjust a test that final mode with a remote branch ahead of default does not take the pause branch-reuse path.




### FINDING_4: Publish-tail can render failed-publish after peer records success
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan re-checks `result_env_publish_ok_is_true` before assigning `SUMMARY_OUTCOME` and staging failed-publish, but `render-final-summary.sh` runs outside the result-env lock. A fast second `design-publish.sh` can pass the re-check; the first invocation can write `PUBLISH_OK=true` before the second reaches render. The second still emits failed-publish and can overwrite an approved `final-summary.md` even though write-once later preserves the result env.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Hold the result-env lock from the pre-summary re-check through `SUMMARY_OUTCOME` selection and `render-final-summary` invocation (or re-read under the lock immediately before render and skip failed-publish when `PUBLISH_OK=true`); add a concurrent interleaving regression where publish-tail B passes the re-check then A writes success before B renders


### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:241-255
- **Concern**: [SCOPE-REDUCTION] Proposed final-mode idempotent success check treats any existing default-branch run-log tree as proof that final publish already completed. Scenario: A pause save uses scripts/design-pause-save.sh to publish the same larch-logs/design/$RUN_ID tree with --reason pause. After resume, final Step 5c would see that pause tree on origin/<default>, emit PUBLISH_OK=true before staging current final artifacts, and skip the required final log publish.
- **Proposed resolution**: Do not return success from a pre-worktree ls-tree path-exists probe alone. Keep final idempotency on the existing post-staging empty-porcelain path, or require proof that cannot be produced by pause before short-circuiting. Add a pause-publish then final-publish regression.



