### OOS_1: Duplicated step3 pre-arm cleanup blocks may drift again
- **Description**: Duplicated step3 pre-arm cleanup blocks may drift again. Scenario: After the fix, stale-sidecar unlink logic will exist in both run_step_checks_main and checks_commit_route_main with no shared helper; future edits could fix one entrypoint and miss the other, repeating Item 1
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/implement/dispatch_commit_route.py:1084-1092; checks_commit_route_main (planned cleanup)
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral
- **Filed URL**: https://github.com/character-ai/larch/issues/6339
### OOS_2: Duplicated step3 pre-arm cleanup may drift again
- **Description**: Duplicated step3 pre-arm cleanup may drift again. Scenario: After the fix, stale-sidecar unlink logic lives in both run_step_checks_main and checks_commit_route_main with no shared helper; a future edit could fix one entrypoint and miss the other
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/implement/dispatch_commit_route.py:1084-1092; checks_commit_route_main (planned cleanup)
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_3: Hardcoded 15600 duplicates CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS // 1000
- **Description**: Hardcoded 15600 duplicates CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS // 1000. Scenario: Future leg-budget edits could desync marker TIMEOUT_S from the SKILL 15600000 ms fence without a compile-time link
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/implement/dispatch_commit_route.py:87
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_4: Step 3 stale cleanup would be duplicated inline in checks_commit_route_main and again in run_step_checks_main
- **Description**: Step 3 stale cleanup would be duplicated inline in checks_commit_route_main and again in run_step_checks_main. Scenario: Two copies of the same unlink pair can drift on the next hardening pass
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/larch/implement/bg_wait.py
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_5: 10800 timeout is still a duplicated magic number
- **Description**: 10800 timeout is still a duplicated magic number. Scenario: Post-change timeout lives in _checks_commit_route_marker, run_step_checks_main, and run-step-checks.sh; a partial edit can reintroduce Item 2 skew
- **Reviewer**: Cursor-dyn-Bg Wait Invariants
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/implement/dispatch_commit_route.py:87-1091
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_6: Pre-arm cleanup will be duplicated in two Python entrypoints
- **Description**: Pre-arm cleanup will be duplicated in two Python entrypoints. Scenario: run_step_checks_main already unlinks the same two paths; a shared helper would DRY but is not required for correctness
- **Reviewer**: Cursor-dyn-Bg Wait Invariants
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/implement/dispatch_commit_route.py:1084-1087
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_7: No negative test that non-step3 composite leaves stale step-3 sidecars untouched
- **Description**: No negative test that non-step3 composite leaves stale step-3 sidecars untouched. Scenario: Edge case is documented but only the step3 positive path is in the testing strategy; a missing checks_site guard could delete artifacts on step6/step5 paths without failing CI
- **Reviewer**: Cursor-dyn-Bg Wait Invariants
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/tests/implement/test_implement_dispatch.py:3748-3812
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected
