### FINDING_1: correctness: scripts/ship-pr.sh:1932-1947
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] No-commit bail uses full baseline==vendor tree equality not vendor delta only If run_ci_fix_vendor starts with uncommitted CI fixes and Cursor exits 0 without further edits snapshots match and ship-pr bails to first-fixer-non-health skipping _stage_and_push_ci_fixes that would commit the fix Bail only when entry baseline was clean and vendor made no delta or compute explicit vendor-only delta while still staging pre-existing dirt
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: scripts/ship-pr.sh:1932-1935
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Missing baseline_head/vendor_head unknown guard from plan If both rev-parse calls fail but symbolic-ref passes, unknown==unknown triggers first-fixer-non-health misclassification Wrap equality test with explicit != unknown checks on both heads
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: scripts/test-ship-pr.sh:4670-4694
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] #3134 test stubs commit in lint-fix-loop/refresh-run-logs but pre-verify bail never reaches them Refactor to post-stage check per plan would let stubs commit and test would pass while behavior regressed Remove dead commit stubs or add explicit post-stage HEAD assertion case
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: scripts/ship-pr.sh:1932-1962
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No-op vendor bail runs before _verify_failed_jobs_locally and _stage_and_push_ci_fixes instead of post-stage HEAD compare per plan. Vendor exits 0 with no tree delta while lint-fix-loop would auto-fix and commit; ship-pr sets first-fixer-non-health and exit 3 without running lint-fix. Restore post-_stage_and_push_ci_fixes HEAD gate or add test/docs that lint-fix salvage is intentionally skipped.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: scripts/test-ship-pr.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness for vendor exit 0 with uncommitted tracked changes (diff cmp path from round 1). Vendor patches files but does not commit; HEAD unchanged but diffs differ; should continue to stage not bail as no-op. Add fix-loop case: launcher touches tracked file only, assert rc=0 and empty BAIL_REASON.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: scripts/test-lint-awk-multibyte-regex.md:8-16
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Contract lists 12 harness cases; script has 17 after round 1. Future harness edits may drop cases without doc review catching it. Sync test-lint-awk-multibyte-regex.md with cases 13-17.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: scripts/ship-pr.sh:1921-1962
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Implementation moved no-commit detection before _stage_and_push using tree cmp instead of post-stage final_head per plan Acceptance and plan describe HEAD check after successful stage; shipped code diverges causing doc/contract drift and different failure timing Restore post-stage HEAD gate with unknown guards or update ship-pr.md CHANGELOG and acceptance to match pre-stage tree equality
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: scripts/test-ship-pr.sh:4679-4693
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] run_ship_pr_3134 stubs lint-fix-loop/refresh-run-logs to commit but early bail never reaches them. Dead stubs add noise; readers may think lint-fix path was tested. Remove unused stubs or assert lint-fix-loop was not called.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: scripts/ship-pr.sh:1932-1948
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Pre-verify no-op vendor detection runs before _verify_failed_jobs_locally and _stage_and_push_ci_fixes, so lint-fix-loop never gets a chance when the vendor exits 0 without tree changes. CI fails on an auto-fixable lint issue; vendor returns LAUNCHER_EXIT=0 with no edits; lint-fix-loop would commit the fix during _stage_and_push_ci_fixes but the new branch sets first-fixer-non-health and exits 3 first. Gate bail on post-_stage_and_push_ci_fixes HEAD advance, or probe lint-fix-loop applicability before classifying as first-fixer-non-health.
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: scripts/ship-pr.sh:1932-1935
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Missing guard against unknown HEAD values removed during round-1 refactor. git rev-parse fails for both snapshots, diffs are empty, baseline_head=vendor_head=unknown triggers false first-fixer-non-health. Require valid 40-char SHAs before treating identical heads as no-op vendor outcome.
- **Suggested revision**: Address the concern above.


### FINDING_31: correctness: scripts/ship-pr.sh:1921-1962
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Round 1 replaced plan's post-_stage_and_push_ci_fixes final_head check with pre-_verify_failed_jobs_locally vendor diff equality. Vendor exit 0 + empty tree while local verify would fail: plan returns ordinary verify failure; current code sets first-fixer-non-health Exit 3 before verify. Vendor no-op + lint-fix-loop commit: plan succeeds; current code bails early. Restore post-_stage_and_push_ci_fixes baseline_head vs final_head check with unknown guards; or amend plan and add harness cases for both edge paths.
- **Suggested revision**: Address the concern above.


### FINDING_32: correctness: scripts/ship-pr.sh:1932-1935
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Missing plan-required unknown HEAD guards on equality branch. baseline_head and vendor_head both unknown → equality fires → misclassified first-fixer-non-health. Add [ "$baseline_head" != "unknown" ] && [ "$vendor_head" != "unknown" ] (or final_head) before equality test.
- **Suggested revision**: Address the concern above.


### FINDING_33: correctness: scripts/test-ship-pr.sh:4634-4718
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] run_ship_pr_3134 stubs commit via lint-fix-loop/refresh-run-logs; plan specified no-diff lint-fix-loop only. Reverting ship-pr to plan-shaped post-stage HEAD check likely yields rc 0 while test expects rc 3. Stub lint-fix-loop as no-op; remove committing refresh-run-logs override; keep no-edit cursor launcher.
- **Suggested revision**: Address the concern above.


### FINDING_4: correctness: scripts/ship-pr.sh:1932-1933
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Missing guard when baseline_head and vendor_head are both unknown Both rev-parse failures yield unknown==unknown and clean tree could false-trigger first-fixer-non-health Require baseline_head and vendor_head != unknown before the equality bail
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/ship-pr.sh:1921-1948
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] No-commit detection runs on pre-verify vendor snapshot, not post-_stage_and_push_ci_fixes final_head as plan acceptance specifies If reverted to post-stage gating per plan, vendor exit 0 + no tree changes + locally failing verify would loop FIX_ATTEMPTS to exit 4 instead of first-fixer-non-health exit 3 (original #3134 stall) Update plan/acceptance/docs to match shipped pre-verify vendor snapshot; add post-stage guard only if lint-fix-loop-only commits without vendor deltas are still desired
- **Suggested revision**: Address the concern above.


