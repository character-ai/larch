### FINDING_1: code-quality: scripts/lint-fix-loop.sh:147-180
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Prefix forbidden-path matching is duplicated in post_dispatch_forbidden_revert and forbidden_paths_match_count. A later fix updates only one loop (e.g. path normalization); commit-content checks and working-tree reverts diverge, allowing forbidden submodule paths in one path but not the other. Extract one shared matcher used by both post_dispatch_forbidden_revert and forbidden_paths_match_count.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: docs/linting.md:203
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Harness docs claim history-rewrite fail-closed coverage but no test implements amend/rebase/rewrite. merge-base guard could regress without CI failure while docs still promise protection. Add a history-rewrite fixture to test-lint-fix-loop.sh or remove rewrite from the documented pin list until covered.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: scripts/test-ship-pr.sh:3267-3354
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Removed negative per-job head-changed stall regression; only happy-path stub remains. _rcc_handle_fix_status or exit_stall 10-head-changed wiring could break with no test-ship-pr failure. Add a small stub case: failed + head-changed-after-dispatch → rc 4 and stall markers.
- **Suggested revision**: Address the concern above.


### FINDING_17: security: scripts/lint-fix-loop.sh:347-372
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Merge commits pass the new coder-owned commit acceptance gate. An external CI fixer on the same branch runs git merge evil-branch; baseline remains an ancestor and symbolic branch is unchanged, so LINT_FIX_STATUS=applied and ship-pr pushes the merge commit including foreign history. Require linear history (single new commit, no second parent) or reject merge commits explicitly before accepting HEAD movement.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: scripts/test-lint-fix-loop.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Docs and acceptance require merge-base rejection of history rewrite but no amend/rebase harness case exists. commit --amend could regress to applied with LINT_FIX_HEAD_CHANGED=true without any test failing on main. Add a wrapper that amends or rewinds HEAD and assert head-changed-after-dispatch.
- **Suggested revision**: Address the concern above.


### FINDING_20: security: scripts/lint-fix-loop.sh:352-359
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Ancestor + same-branch checks allow merge commits, not only linear single commits. Coder runs git merge on the same branch; large unrelated diff range is accepted if no forbidden prefix matches. Tighten to single-parent/fast-forward only, or document and accept merge commits explicitly in SECURITY.md.
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: scripts/lint-fix-loop.sh:361-363
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] git reset --hard on forbidden committed delta uses || true without verifying HEAD afterward. reset fails (lock/corruption); script emits forbidden-path-violation but repo may still be on the bad commit. Verify HEAD equals baseline after reset or fail with a distinct reason when reset does not restore baseline.
- **Suggested revision**: Address the concern above.


### FINDING_23: code-quality: scripts/test-lint-fix-loop.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit]  No test for amend/rebase history-rewrite rejection despite plan edge-case list. Regression could slip if merge-base guard is loosened accidentally. Add wrapper fixture asserting head-changed-after-dispatch after amend or rebase.
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: docs/linting.md:203
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Harness doc claims history-rewrite fail-closed is pinned, but no amend/rebase fixture exists. A future regression that breaks merge-base --is-ancestor could ship undetected while docs still claim harness coverage. Add a history-rewrite case to scripts/test-lint-fix-loop.sh or soften the docs/linting.md harness description.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: scripts/test-lint-fix-loop.sh:257-258
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Case 1 does not assert LINT_FIX_COMMIT_SHA equals git rev-parse HEAD. A bug emitting a stale or bogus SHA would still pass case 1. Assert kv commit sha matches rev-parse HEAD in the fixture repo.
- **Suggested revision**: Address the concern above.


