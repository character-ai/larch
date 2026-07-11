# Review Round 2

- Mode: `diff`
- 13 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_1: correctness: skills/implement/scripts/run-step-checks.sh:142-149
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [major] post_publish_identity_matches only bypasses identity revalidation for COMMIT_ROUTE_OUTCOME=continue Pre-commit autofix during checks-failed changes the tree; post-publish check replaces NEXT_ACTION=checks-failed with identity-integrity-failed Skip post-publish validation for non-reusable terminals (checks-failed/stall) or persist post-checks identity on failure paths
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/implement/scripts/step-6-entry.sh:132-139
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [major] Step 6 shares the narrow continue-only post-publish bypass Checks pass after autofix then commit route seeds stall; post-publish mismatch emits identity-integrity-failed instead of NEXT_ACTION=stall Apply the same terminal-action carve-out as run-step-checks or limit post-publish validation to reusable success routes
- **Suggested revision**: Address the concern above.


### FINDING_3: correctness: skills/implement/scripts/run-step-checks.sh:324-336
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [minor] Live-registry identity-mismatch fail-closed path lacks subprocess regression A regression could rejoin or duplicate-launch when merge identity drifts under a live registry row Add subprocess test: live registry + mismatched merge env → exit 2 and no fresh start
- **Suggested revision**: Address the concern above.


### FINDING_4: correctness: skills/implement/scripts/run-step-checks.sh:223-229
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [minor] Mid-run repository mutation / pre-publish drift is not subprocess-tested Plan-required during-run drift behavior is unverified at launcher level Add stub checks child that mutates repo mid-flight; assert pre-publish-identity-mismatch and non-reusable classification
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: skills/implement/scripts/run-step-checks.sh:142-150
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [major] post_publish_identity_matches only bypasses validation on COMMIT_ROUTE_OUTCOME=continue Pre-commit autofix during checks can change the tree before checks-failed or stall; child then publishes identity-integrity-failed instead of the real terminal envelope Also bypass post-publish validation for legitimate terminal failure outcomes (checks-failed stall) or bind identity after the checks leg
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: skills/implement/scripts/step-6-entry.sh:132-140
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [major] Step 6 post_publish carve-out matches the narrow continue-only pattern Step 6 composites can autofix then fail or stall without continue; operators get identity-integrity-failed instead of skip-to-7a stall or checks-failed Mirror the expanded terminal-outcome bypass from run-step-checks.sh for all Step 6 composite routes
- **Suggested revision**: Address the concern above.


### FINDING_14: security: skills/implement/scripts/run-step-checks.sh:142-150
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [major] The COMMIT_ROUTE_OUTCOME=continue output marker bypasses all post-publication identity validation; the same bypass exists in skills/implement/scripts/step-6-entry.sh:132-140. An unrelated mutation after checks but before envelope publication can advance the workflow without proving the terminal tree matches the checked inputs. Persist an expected post-commit identity and validate it before publication; do not use stdout as a blanket exemption.
- **Suggested revision**: Address the concern above.


### FINDING_15: security: skills/implement/scripts/run-step-checks.sh:275-279
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [major] The merge-result env rejects symlinks but not directories or other non-regular files; the same gap exists in skills/implement/scripts/step-6-entry.sh:227-230. A directory merge env makes mv place the seed inside the directory, so the bgjob executes without the required identity-bearing merge envelope. Reject any existing non-regular merge env before seeding and add directory-envelope subprocess coverage.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: python/tests/implement/test_run_step_checks.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [major] Live-registry matching rejoin and identity-mismatch fail-closed paths lack subprocess tests Regressions in step_checks_live_registry_exists branches could rejoin wrong jobs or launch duplicates Extend stub-cli harness to cover live matching rejoin and mismatch exit 2 for run-step-checks and step-6-entry
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: python/tests/implement/test_run_step_checks.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [major] Plan-required launcher drift and successful-composite publication regressions are incomplete Staged/untracked/commit drift during-run and pre-publish paths plus post_publish_identity_matches carve-out are unverified at launcher level Add subprocess matrix per plan including successful COMMIT_ROUTE_OUTCOME=continue child publishing reusable identity envelope
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: python/tests/implement/test_checks_result_identity.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [minor] Completed-result hostile env cases from the plan remain untested Git failures duplicate keys and unreadable untracked inputs could regress classification silently Add unit tests for completed classify path mirroring live-seed hostile cases
- **Suggested revision**: Address the concern above.


### FINDING_27: **correctness** `skills/implement/scripts/run-step-checks.sh:142-149`, `skills/implement/scripts/step-6-entry.sh:132-139`, `python/larch/implement/dispatch_commit_route.py:963-971` — `post_publish_identity_matches` only bypasses identity revalidation when stdout contains `COMMIT_ROUTE_OUTCOME=continue`. Step 3/6 composites also take the `noop` commit path (`COMMIT_ROUTE_OUTCOME=noop` when the dispatcher already committed and the tree is clean), then still run folded `4.r`/`7.r` rebase checkpoints that can move `HEAD`. In that path the child runs pre-publish validation against the launch identity, sees drift, and publishes `NEXT_ACTION=identity-integrity-failed` instead of the composite’s terminal `NEXT_ACTION=continue`. External-implementer Step 3 runs hit this routinely (`--rebase-checkpoint-4r` is always on). **Suggested fix:** Treat authorized composite terminals as non-revalidating—e.g. skip pre-publish when stdout has `NEXT_ACTION=continue`, or also when `COMMIT_ROUTE_OUTCOME` is `continue`/`noop` and the composite exited successfully—or recompute and persist post-rebase identity before publication.
- **Reviewer**: dyn-dyn-checks-identity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/run-step-checks.sh:142-149`, `skills/implement/scripts/step-6-entry.sh:132-139`, `python/larch/implement/dispatch_commit_route.py:963-971` — `post_publish_identity_matches` only bypasses identity revalidation when stdout contains `COMMIT_ROUTE_OUTCOME=continue`. Step 3/6 composites also take the `noop` commit path (`COMMIT_ROUTE_OUTCOME=noop` when the dispatcher already committed and the tree is clean), then still run folded `4.r`/`7.r` rebase checkpoints that can move `HEAD`. In that path the child runs pre-publish validation against the launch identity, sees drift, and publishes `NEXT_ACTION=identity-integrity-failed` instead of the composite’s terminal `NEXT_ACTION=continue`. External-implementer Step 3 runs hit this routinely (`--rebase-checkpoint-4r` is always on). **Suggested fix:** Treat authorized composite terminals as non-revalidating—e.g. skip pre-publish when stdout has `NEXT_ACTION=continue`, or also when `COMMIT_ROUTE_OUTCOME` is `continue`/`noop` and the composite exited successfully—or recompute and persist post-rebase identity before publication.
- **Suggested revision**: Address the concern above.


### FINDING_28: **correctness** `skills/implement/scripts/run-step-checks.sh:142-149`, `skills/implement/scripts/step-6-entry.sh:132-139`, `python/larch/implement/checks_run_relevant.py:1098-1103` — Pre-publication validation still runs when the composite returns `NEXT_ACTION=checks-failed`. `checks run-relevant` may mutate the tree during failure (pre-commit autofix via `_record_precommit_self_edits`, then a non-zero exit). The child then fails `validate_child_identity` and emits `identity-integrity-failed`, replacing the real checks failure envelope and digest. Round-1’s `COMMIT_ROUTE_OUTCOME=continue` carve-out does not cover this checks-failed path. **Suggested fix:** Skip pre-publish identity comparison when composite stdout contains `NEXT_ACTION=checks-failed` (or when the checks leg recorded self-edits), since launch identity is meant to describe inputs at check start, not post-autofix state.
- **Reviewer**: dyn-dyn-checks-identity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/run-step-checks.sh:142-149`, `skills/implement/scripts/step-6-entry.sh:132-139`, `python/larch/implement/checks_run_relevant.py:1098-1103` — Pre-publication validation still runs when the composite returns `NEXT_ACTION=checks-failed`. `checks run-relevant` may mutate the tree during failure (pre-commit autofix via `_record_precommit_self_edits`, then a non-zero exit). The child then fails `validate_child_identity` and emits `identity-integrity-failed`, replacing the real checks failure envelope and digest. Round-1’s `COMMIT_ROUTE_OUTCOME=continue` carve-out does not cover this checks-failed path. **Suggested fix:** Skip pre-publish identity comparison when composite stdout contains `NEXT_ACTION=checks-failed` (or when the checks leg recorded self-edits), since launch identity is meant to describe inputs at check start, not post-autofix state.
- **Suggested revision**: Address the concern above.
