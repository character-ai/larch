### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/design-log-publish.sh:286-294; plan.txt:23-38
- **Concern**: The rebuild-on-default helper is not explicitly limited to `--reason final`.. Scenario: The plan resets the disposable branch onto freshly fetched `origin/<default>` immediately before push, but pause mode must keep worktree creation from `origin/larch-log-design-<RUN_ID>` and `--force-with-lease` reuse. Running the same reset/overlay path for pause would discard pause-branch history and break the documented pause contract.
- **Proposed resolution**: State in the helper contract that it runs only for `REASON=final`; leave the existing pause commit/push path unchanged.


### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:966-969
- **Concern**: Final-mode push stays plain -u while pause uses --force-with-lease. Scenario: Incremental republish after a stuck or open larch-log-design-<RUN_ID> remote ref: rebuilt commit is on fresh default but remote tip is a stale divergent branch; push is rejected and recovery repeats the stuck-PR pattern
- **Proposed resolution**: Add final-mode push rule: when origin/larch-log-design-<RUN_ID> exists use --force-with-lease (same family as pause); document in design-log-publish.md


### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:842-938
- **Concern**: Rebuild plan overlays the desired snapshot without deleting paths absent from that snapshot. Scenario: When default already has an earlier run snapshot with an artifact absent from the new redacted snapshot, reset-to-default plus copy-over leaves the old file in the final branch, so the PR is not the final snapshot and stale excluded files can survive
- **Proposed resolution**: After resetting to origin default, replace the run directory or sync with delete semantics before copying the snapshot; preserve the default manifest only for the manifest-only comparison, then git add the whole run path so deletions are committed


### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:870-942
- **Concern**: Rebuild overlay does not define how paths already on default but absent from the desired snapshot are removed. Scenario: The plan resets the worktree to origin/default then overlays the snapshot into larch-logs/design/$RUN_ID. A copy-only overlay leaves excluded or stale files that remain on default (today design_publish_remove_stale_excluded plus commit record deletions). Republish or incremental flush can keep codex-primary-plan-arch-output.txt or round findings.md on the PR branch while the session snapshot omits them
- **Proposed resolution**: After reset and before the delta check, replace $WT_DIR/$rel with the snapshot tree (for example rm -rf then cp -a), or run design_publish_remove_stale_excluded on $WT_DIR/$rel and stage deletions with git add -A -- $rel


### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:966-977
- **Concern**: The rebuild-before-push plan is silent on how final mode updates an existing remote larch-log-design-<RUN_ID> ref after the commit is rebuilt on a fresh default. Scenario: Stuck re-flushes (#4241/#4244) leave a divergent remote log branch; today final mode uses a plain git push (pause alone uses --force-with-lease) and scripts/test-design-log-publish.sh:2045 expects PUBLISH_OK=false on non-fast-forward. A rebuilt commit cannot replace the stale remote branch, so the incremental re-publish path still fails before gh pr create
- **Proposed resolution**: Specify final-mode push when REMOTE_BRANCH_EXISTS or push would be non-fast-forward: e.g. git push --force-with-lease after the rebuild, document the contract in design-log-publish.md, and flip the RUNBASE1 harness to assert PUBLISH_OK=true with branch-only sentinel absent from default


### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:594-608; skills/design/scripts/design-publish.md:60-63
- **Concern**: The plan changes design-log-publish.sh but leaves the caller's existing PUBLISH_OK=true short-circuit before design-log-publish.sh. Scenario: An early snapshot publish can write PUBLISH_OK=true, then a later Step 5c re-entry with final-only artifacts skips the new late content-based idempotency path entirely, so Fix C still drops the final snapshot delta
- **Proposed resolution**: Narrow the caller skip so existing success only protects result-env overwrite and failed-publish reporting after a current publish attempt. Still render timing and invoke design-log-publish.sh, then let its no-delta path decide. Update design-publish.md and add a focused test-design-publish.sh case with existing PUBLISH_OK=true plus a changed snapshot that asserts design-log-publish.sh is called.


### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-stale-base-correctness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:966-969
- **Concern**: Plan adds pre-push rebuild but leaves final-mode push as plain `git push -u` while pause uses `--force-with-lease`. Scenario: After a stuck re-flush, `origin/larch-log-design-<RUN_ID>` often still exists (#4241/#4244). A clean commit rebased onto fresh default cannot fast-forward that remote ref; push fails and only recovery metadata is emitted, so a newer final snapshot never reaches one mergeable PR
- **Proposed resolution**: Specify final-mode push when `REMOTE_BRANCH_EXISTS=true`: force-with-lease onto `larch-log-design-<RUN_ID>` (or delete the stale remote ref first), then reuse the open PR via existing `gh pr list` recovery


### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-publish-risk-integration
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/design-log-publish.sh:286-289,967-968,skills/design/references/plan.txt (Files to modify/create)
- **Concern**: Pre-push rebuild helper is not scoped to `--reason final` only. Scenario: The plan says the rebuild runs immediately before every push while also requiring pause keep `origin/$WT_BRANCH` worktree base and `--force-with-lease` (`scripts/design-log-publish.md:172-174`). Resetting the disposable branch to `origin/<default>` before pause push would replace log-branch-parent commits and can break pause empty-porcelain fail-closed paths that emit `RECOVERY_BRANCH=$WT_BRANCH` (`scripts/design-log-publish.sh:877-889`) and existing pause reuse tests (`scripts/test-design-log-publish.sh:890-966`)
- **Proposed resolution**: Scope the rebuild-and-overlay helper to `REASON==final` only. For pause, keep the current commit-on-log-branch-base plus force-with-lease path; at most fetch refreshed `origin/<default>` without the full reset-and-overlay sequence


### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-publish-risk-integration
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:928-975,plan.txt (Files to modify/create)
- **Concern**: Plan does not say the current pre-push `git commit` is replaced by the rebuild commit. Scenario: The live script commits staged content on the initial worktree base (`scripts/design-log-publish.sh:928-941`) then pushes that SHA (`975-996`). If the rebuild helper is inserted after that commit without removing or superseding it, push can still send a stale-base commit while the rebuilt tree never ships
- **Proposed resolution**: Move final-mode commit creation into the rebuild helper only: stage and scrub to snapshot, rebuild on fetched `origin/<default>`, delta-check, then single commit immediately before push. Do not push a pre-rebuild commit


### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-publish-risk-integration
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-log-publish.sh:2050-2076
- **Concern**: Existing harness case contradicts new incremental republish semantics. Scenario: Test `final idempotent success after squash merge` seeds default with `plan.txt` content `merged log` then publishes tmpdir `plan.txt` `new attempt` and asserts no `pr create` (`2072-2074`). Removing the early ls-tree skip (`scripts/design-log-publish.sh:248-253`) and adding late delta detection requires a PR for that differing snapshot, which is the #4212 fix
- **Proposed resolution**: Retire or rewrite the RUNIDEM1 case to expect `gh pr create` when snapshot differs from default. Keep no-PR assertions only for byte-identical reruns such as `final no-delta succeeds idempotently` (`726-760`)


### FINDING_11:
- **Reviewer(s)**: Codex-dyn-publish-risk-integration
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-publish.sh:594-600; <TMPDIR>/plan.txt:12-47
- **Concern**: Existing success-result short-circuit bypasses the planned late idempotency check. Scenario: A re-entry after an early successful publish sees .design-publish-result.env PUBLISH_OK=true and skips scripts/design-log-publish.sh entirely, so final-only artifacts are never compared or published despite the plan moving idempotency into design-log-publish.sh
- **Proposed resolution**: Include a minimal design-publish.sh change so prior PUBLISH_OK=true does not skip the publish call; let design-log-publish.sh perform the late no-delta check, while preserving the existing write-once fallback when a later publish attempt fails


### FINDING_12:
- **Reviewer(s)**: Codex-dyn-publish-risk-integration
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:842-903; scripts/test-design-log-publish.sh:2133-2165; <TMPDIR>/plan.txt:23-33
- **Concern**: Rebuild helper overlays the desired snapshot without requiring deletion-aware sync. Scenario: After the helper resets to the freshly fetched default branch, files already present under larch-logs/design/$RUN_ID but absent from the desired snapshot can survive. This can regress the existing stale-excluded cleanup contract asserted by the harness.
- **Proposed resolution**: Make the rebuild step replace or rsync --delete $WT_DIR/$rel from the scrubbed snapshot, then run the existing stale-excluded cleanup before the porcelain check. Treat non-manifest deletions as real delta.


