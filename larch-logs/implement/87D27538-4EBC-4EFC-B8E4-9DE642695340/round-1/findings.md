### FINDING_1: code-quality: scripts/lint-fix-loop.sh:147-180
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Prefix forbidden-path matching is duplicated in post_dispatch_forbidden_revert and forbidden_paths_match_count. A later fix updates only one loop (e.g. path normalization); commit-content checks and working-tree reverts diverge, allowing forbidden submodule paths in one path but not the other. Extract one shared matcher used by both post_dispatch_forbidden_revert and forbidden_paths_match_count.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/test-lint-fix-loop.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Docs and acceptance require merge-base rejection of history rewrite but no amend/rebase harness case exists. commit --amend could regress to applied with LINT_FIX_HEAD_CHANGED=true without any test failing on main. Add a wrapper that amends or rewinds HEAD and assert head-changed-after-dispatch.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-lint-fix-loop.sh:83-219
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Five write_wrapper_* helpers duplicate identical external-agent argv parsing. Fixture churn copies the same parser block five times, increasing review burden and typo risk. Factor a write_stub_wrapper helper with a per-case body fragment.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/test-ship-pr.sh:3059-3354
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ci_per_job_head_changed duplicates ci_per_job_happy stubs and uses a misleading fixture name. Future CI recovery stub changes must be edited in two places; the name suggests stall behavior though the test now expects success. Share a write_per_job_ci_recovery_stubs helper and rename the repo/fixture.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/lint-fix-loop.sh:349-356
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Three identical fail_status calls for head-changed guards. Logs do not distinguish branch vs ancestor vs dirty-baseline failures without reading source. Combine guards into one compound if or a small reject helper.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/test-lint-fix-loop.sh:257-258
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Case 1 does not assert LINT_FIX_COMMIT_SHA equals git rev-parse HEAD. A bug emitting a stale or bogus SHA would still pass case 1. Assert kv commit sha matches rev-parse HEAD in the fixture repo.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: SECURITY.md:133
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ADOPTED validation paragraph is from #2878 not #2909. Unrelated security doc change rides the same PR diff. Split or note in PR description; no change required for #2909 logic.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] architecture: scripts/lint-fix-loop.sh:393-408
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Dirty baseline with unchanged HEAD can emit applied without commit SHA (pre-existing). Unrelated dirty-tree scenarios may still confuse operators; not regressed by this branch. Track separately if desired; out of scope for #2909.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] **Latent** `correctness` [`scripts/test-lint-fix-loop.sh`](scripts/test-lint-fix-loop.sh) — The plan and docs call out history rewrites (`commit --amend`, rebase) as fail-closed via `merge-base --is-ancestor`, but there is no dedicated regression case (unlike detached-HEAD, branch-switch, and dirty-baseline). **Suggested fix:** Add a wrapper that amends or rebases the tip commit and assert `FAILURE_REASON=head-changed-after-dispatch`.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Latent** `correctness` [`scripts/test-lint-fix-loop.sh`](scripts/test-lint-fix-loop.sh) — The plan and docs call out history rewrites (`commit --amend`, rebase) as fail-closed via `merge-base --is-ancestor`, but there is no dedicated regression case (unlike detached-HEAD, branch-switch, and dirty-baseline). **Suggested fix:** Add a wrapper that amends or rebases the tip commit and assert `FAILURE_REASON=head-changed-after-dispatch`.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] **Latent** `risk-integration` [`scripts/lint-fix-loop.sh:366-368`](scripts/lint-fix-loop.sh) — If a coder makes a valid commit and also leaves an uncommitted forbidden-path edit, `post_dispatch_forbidden_revert` fails with `forbidden-path-violation` while the good commit remains on HEAD unpushed; `ship-pr.sh` maps that to `dispatch-failed`, not the old `10-head-changed` stall. This is plan-intended fail-closed behavior, but it can still leave a good fix committed locally without push. **Suggested fix:** Only if product wants push-after-revert: emit `applied` after reverting residual working-tree forbidden edits when the commit-content check already passed (document the relaxed security tradeoff).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **Latent** `risk-integration` [`scripts/lint-fix-loop.sh:366-368`](scripts/lint-fix-loop.sh) — If a coder makes a valid commit and also leaves an uncommitted forbidden-path edit, `post_dispatch_forbidden_revert` fails with `forbidden-path-violation` while the good commit remains on HEAD unpushed; `ship-pr.sh` maps that to `dispatch-failed`, not the old `10-head-changed` stall. This is plan-intended fail-closed behavior, but it can still leave a good fix committed locally without push. **Suggested fix:** Only if product wants push-after-revert: emit `applied` after reverting residual working-tree forbidden edits when the commit-content check already passed (document the relaxed security tradeoff).
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: docs/linting.md:203
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Harness docs claim history-rewrite fail-closed coverage but no test implements amend/rebase/rewrite. merge-base guard could regress without CI failure while docs still promise protection. Add a history-rewrite fixture to test-lint-fix-loop.sh or remove rewrite from the documented pin list until covered.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-ship-pr.sh:3267-3354
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Removed negative per-job head-changed stall regression; only happy-path stub remains. _rcc_handle_fix_status or exit_stall 10-head-changed wiring could break with no test-ship-pr failure. Add a small stub case: failed + head-changed-after-dispatch → rc 4 and stall markers.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-lint-fix-loop.sh:239-262
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Coder-owned commit acceptance tested only at step3, not ship-pr-ci-per-job. Per-job site-specific regressions in forbidden-path or branch guards would not be caught by case 1. Add per-job case mirroring case 1 with --target-cmd-args-file.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-ship-pr.sh:3267-3354
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] ci_per_job_head_changed omits Phase B and relevant-checks assertions present in ci_per_job_happy. Push/CI replay could pass while local verification or step10 gate is skipped. Align assertions with ci_per_job_happy (env/make rerun counts, relevant-checks call log).
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] risk-integration: SECURITY.md:133
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Unrelated ADOPTED sentinel documentation from #2878 in the same diff. No direct impact on #2909 test obligations. Split or note in PR description; no test action required for #2909.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] correctness: scripts/lint-fix-loop.sh:366-369
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Working-tree forbidden violation after accepted coder commit does not reset HEAD. Coder commit could remain on branch while helper reports forbidden-path-violation; parent may take dispatch-failed path. Optional follow-up test/fix if product wants hard reset on that failure shape.
- **Suggested revision**: Address the concern above.

### FINDING_17: security: scripts/lint-fix-loop.sh:347-372
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Merge commits pass the new coder-owned commit acceptance gate. An external CI fixer on the same branch runs git merge evil-branch; baseline remains an ancestor and symbolic branch is unchanged, so LINT_FIX_STATUS=applied and ship-pr pushes the merge commit including foreign history. Require linear history (single new commit, no second parent) or reject merge commits explicitly before accepting HEAD movement.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] security: scripts/lint-fix-loop.sh:147-148,173-174
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Prefix forbidden-path matching allows sibling directory names (submod vs submod-evil). Pre-existing semantics shared by post_dispatch_forbidden_revert; not introduced by this branch. Harden prefix matching in a follow-up (e.g. require trailing slash boundary).
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/lint-fix-loop.sh:366-368
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Post-dispatch forbidden working-tree revert fails the run after a valid coder-owned commit is already on HEAD. Coder commits a passing fix then leaves a dirty forbidden path; revert succeeds but status is forbidden-path-violation, per-job returns dispatch-failed, and the good commit may never be pushed (variant of #2909). Keep fail-closed behavior but document it and/or add a harness case; consider whether revert-only violations should still emit applied when HEAD commit content is clean.
- **Suggested revision**: Address the concern above.

### FINDING_20: security: scripts/lint-fix-loop.sh:352-359
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Ancestor + same-branch checks allow merge commits, not only linear single commits. Coder runs git merge on the same branch; large unrelated diff range is accepted if no forbidden prefix matches. Tighten to single-parent/fast-forward only, or document and accept merge commits explicitly in SECURITY.md.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: scripts/lint-fix-loop.sh:361-363
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] git reset --hard on forbidden committed delta uses || true without verifying HEAD afterward. reset fails (lock/corruption); script emits forbidden-path-violation but repo may still be on the bad commit. Verify HEAD equals baseline after reset or fail with a distinct reason when reset does not restore baseline.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: scripts/lint-fix-loop.sh:347-372
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Accepted coder-commit path omits working-tree delta paths from LINT_FIX_DELTA_PATHS_FILE. Coder commits fix A and leaves allowlisted uncommitted untracked B; B may not be staged on push via delta allowlist (tracked dirt still handled in ship-pr). Union committed diff with delta_paths_after_dispatch if untracked carry-forward must be guaranteed.
- **Suggested revision**: Address the concern above.

### FINDING_23: code-quality: scripts/test-lint-fix-loop.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit]  No test for amend/rebase history-rewrite rejection despite plan edge-case list. Regression could slip if merge-base guard is loosened accidentally. Add wrapper fixture asserting head-changed-after-dispatch after amend or rebase.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/test-ship-pr.sh:3267-3353
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Per-job happy-path rewrite uses stub lint-fix only, not real git HEAD movement. Stub proves wiring; production coupling of applied + local commit + push is only covered in test-lint-fix-loop.sh. Optional end-to-end ship-pr fixture with real lint-fix-loop.sh copy.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:1600-1603
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] _stage_and_push_ci_fixes runs full relevant-checks lint-fix after per-job success. Extra external dispatches and failure modes after shard-local fix; pre-existing orchestration. Out of scope for #2909; tune separately if latency/recursion is a concern.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] correctness: scripts/lint-fix-loop.sh:313-317
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Pre-dispatch forbidden_paths_file not refreshed after coder adds new submodule entries. New submodule path in commit may evade list until CI relevant-checks fails post-push. Pre-existing gap acknowledged in plan.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] security: SECURITY.md:133
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] ADOPTED sentinel validation text is from another merged commit on this branch. Not part of e59c905d feature diff. Review under #2936, not #2909.
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: docs/linting.md:203
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Harness doc claims history-rewrite fail-closed is pinned, but no amend/rebase fixture exists. A future regression that breaks merge-base --is-ancestor could ship undetected while docs still claim harness coverage. Add a history-rewrite case to scripts/test-lint-fix-loop.sh or soften the docs/linting.md harness description.
- **Suggested revision**: Address the concern above.

