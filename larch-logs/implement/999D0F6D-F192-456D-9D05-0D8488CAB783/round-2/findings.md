### FINDING_1: correctness: scripts/ship-pr.sh:1932-1947
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] No-commit bail uses full baseline==vendor tree equality not vendor delta only If run_ci_fix_vendor starts with uncommitted CI fixes and Cursor exits 0 without further edits snapshots match and ship-pr bails to first-fixer-non-health skipping _stage_and_push_ci_fixes that would commit the fix Bail only when entry baseline was clean and vendor made no delta or compute explicit vendor-only delta while still staging pre-existing dirt
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/ship-pr.sh:1921-1962
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Implementation moved no-commit detection before _stage_and_push using tree cmp instead of post-stage final_head per plan Acceptance and plan describe HEAD check after successful stage; shipped code diverges causing doc/contract drift and different failure timing Restore post-stage HEAD gate with unknown guards or update ship-pr.md CHANGELOG and acceptance to match pre-stage tree equality
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/ship-pr.sh:1922-1935
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] vendor_tracked_file and baseline_tracked_file captured but not used in no-commit cmp Extra git diff --name-only work on every vendor attempt without affecting branch logic Remove unused captures or add cmp of tracked path lists to the predicate
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: scripts/ship-pr.sh:1932-1933
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Missing guard when baseline_head and vendor_head are both unknown Both rev-parse failures yield unknown==unknown and clean tree could false-trigger first-fixer-non-health Require baseline_head and vendor_head != unknown before the equality bail
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: CHANGELOG.md:68
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New lint listed under Fixed not Added Changelog readers may misread severity of the release Move bullet to ### Added or split added vs fixed
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/lint-awk-multibyte-regex.sh:82-330
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Large embedded awk scanner high maintenance surface Heredoc and single-quote span logic may regress without dedicated tests beyond current harness Defer unless adding another lint; then extract shared walk helpers
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] architecture: scripts/ship-pr.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Contract doc omits new no-commit vendor bail Operators relying on ship-pr.md alone miss #3134 routing Update ship-pr.md in a follow-up
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] correctness: scripts/lint-awk-multibyte-regex.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Lint does not detect ASCII POSIX classes in dynamic awk Original mawk [[:space:]] incident class not caught by multibyte-only rules Tracked as plan non-goals; separate issue if still needed
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/ship-pr.sh:1921-1948
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] No-commit detection runs on pre-verify vendor snapshot, not post-_stage_and_push_ci_fixes final_head as plan acceptance specifies If reverted to post-stage gating per plan, vendor exit 0 + no tree changes + locally failing verify would loop FIX_ATTEMPTS to exit 4 instead of first-fixer-non-health exit 3 (original #3134 stall) Update plan/acceptance/docs to match shipped pre-verify vendor snapshot; add post-stage guard only if lint-fix-loop-only commits without vendor deltas are still desired
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/ship-pr.sh:1932-1935
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Missing baseline_head/vendor_head unknown guard from plan If both rev-parse calls fail but symbolic-ref passes, unknown==unknown triggers first-fixer-non-health misclassification Wrap equality test with explicit != unknown checks on both heads
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/lint-awk-multibyte-regex.sh:211-214,277-281
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Rule 2 same-line conjoin and naive single-quote body close can miss split-line patterns Multi-line awk re assignment with em-dash on one line and $0 ~ re on next is not flagged; apostrophe in body line can end tracking early Document limits; extend matcher for cross-line re assignment or robust quote tracking
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-ship-pr.sh:4670-4694
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] #3134 test stubs commit in lint-fix-loop/refresh-run-logs but pre-verify bail never reaches them Refactor to post-stage check per plan would let stubs commit and test would pass while behavior regressed Remove dead commit stubs or add explicit post-stage HEAD assertion case
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: CHANGELOG.md:68
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] New lint listed under Fixed rather than Added No runtime impact Move bullet to Added or split Added vs Fixed
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] architecture: scripts/lint-awk-multibyte-regex.md:37
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Rule 2 example cites dac0d00c POSIX-class hypothesis commit Doc inconsistency with plan non-goals only Update historical example to #3144 em-dash family
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] code-quality: docs/linting.md:237
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Harness table omits round-1 test cases Doc lag vs scripts/test-lint-awk-multibyte-regex.sh Extend harness row to list added fixtures
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/ship-pr.sh:1932-1962
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No-op vendor bail runs before _verify_failed_jobs_locally and _stage_and_push_ci_fixes instead of post-stage HEAD compare per plan. Vendor exits 0 with no tree delta while lint-fix-loop would auto-fix and commit; ship-pr sets first-fixer-non-health and exit 3 without running lint-fix. Restore post-_stage_and_push_ci_fixes HEAD gate or add test/docs that lint-fix salvage is intentionally skipped.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/test-ship-pr.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness for vendor exit 0 with uncommitted tracked changes (diff cmp path from round 1). Vendor patches files but does not commit; HEAD unchanged but diffs differ; should continue to stage not bail as no-op. Add fix-loop case: launcher touches tracked file only, assert rc=0 and empty BAIL_REASON.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/test-ship-pr.sh:238-256
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Default write_stubs launchers always commit; tier-order tests use separate uncommitted-touch pattern. Staging/commit bugs after vendor may not be exercised by most fix-loop tests using default stubs. Limit default stub to non-committing touches where staging path must be tested.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/test-lint-awk-multibyte-regex.md:8-16
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Contract lists 12 harness cases; script has 17 after round 1. Future harness edits may drop cases without doc review catching it. Sync test-lint-awk-multibyte-regex.md with cases 13-17.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/test-ship-pr.sh:4679-4693
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] run_ship_pr_3134 stubs lint-fix-loop/refresh-run-logs to commit but early bail never reaches them. Dead stubs add noise; readers may think lint-fix path was tested. Remove unused stubs or assert lint-fix-loop was not called.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] risk-integration: scripts/lint-awk-multibyte-regex.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Lint does not detect mawk POSIX [[:class:]] in dynamic regex (plan non-goal). [[:space:]]-style mawk failures would not be caught at commit time. File follow-up lint or document limitation prominently if that class remains a concern.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/lint-awk-multibyte-regex.sh:15-41` — `--root PATH` allows scanning any directory’s `*.sh` / `*.awk` trees when invoked outside the default pre-commit path (same contract as `lint-bare-grep-probe.sh`). **Suggested fix:** Only relevant if a caller ever passes untrusted `--root`; keep invocation limited to repo root / harness tempdirs.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/lint-awk-multibyte-regex.sh:88` — `path="$ROOT/$rel"` does not canonicalize `..` or reject repo-internal symlinks that resolve outside the root; a malicious tree entry could cause the linter to read unexpected files (shared with the bare-grep-probe family). **Suggested fix:** Reject `rel` values containing `..` and/or resolve paths with a root-prefix check before `awk` reads them.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.sh:1932-1947` — If both `baseline_head` and `vendor_head` are the literal `unknown`, the equality branch fires and can misclassify as `first-fixer-non-health` (plan noted detached-HEAD guard makes this rare). **Suggested fix:** Require known SHAs (`!= unknown`) before the no-commit bail, matching the original plan guard.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/ship-pr.sh:1932-1948
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Pre-verify no-op vendor detection runs before _verify_failed_jobs_locally and _stage_and_push_ci_fixes, so lint-fix-loop never gets a chance when the vendor exits 0 without tree changes. CI fails on an auto-fixable lint issue; vendor returns LAUNCHER_EXIT=0 with no edits; lint-fix-loop would commit the fix during _stage_and_push_ci_fixes but the new branch sets first-fixer-non-health and exits 3 first. Gate bail on post-_stage_and_push_ci_fixes HEAD advance, or probe lint-fix-loop applicability before classifying as first-fixer-non-health.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: scripts/ship-pr.sh:1932-1935
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Missing guard against unknown HEAD values removed during round-1 refactor. git rev-parse fails for both snapshots, diffs are empty, baseline_head=vendor_head=unknown triggers false first-fixer-non-health. Require valid 40-char SHAs before treating identical heads as no-op vendor outcome.
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: scripts/lint-awk-multibyte-regex.sh:249-254,277-281
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Rule 2 single-quote body tracker closes on any apostrophe in a continuation line. Multiline awk body with # don't comment closes span early; em-dash match() on a later line is not scanned as awk body. Track quote depth/escaping or restore stricter close-delimiter matching for interior lines.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: scripts/lint-awk-multibyte-regex.sh:298-315
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Double-quoted awk programs are out of scope for Rule 2 body tracking. Non-ASCII dynamic regex added inside awk "..." (pattern used in launch-review.sh / launch-codex-implement.sh) bypasses the new lint. Extend Rule 2 to double-quoted awk bodies or add a separate check for that invocation form.
- **Suggested revision**: Address the concern above.

### FINDING_29: architecture: scripts/ship-pr.sh:1942-1944
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Breadcrumb/detail log say no commits but detection is pre-commit working-tree identity. Operator reads ci-fix-no-commit log expecting commit-level semantics while vendor may have left unstaged edits that pass the check. Reword messages to no working-tree changes for accuracy.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] code-quality: CHANGELOG.md:17-18
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] New lint listed under Fixed instead of Added/Changed. Misleading changelog categorization only; no runtime impact. Recategorize under Added or Changed in a follow-up docs commit.
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

### FINDING_34: correctness: scripts/lint-awk-multibyte-regex.sh:104-112
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] has_nonascii flags ASCII control chars; plan targets bytes outside 7-bit ASCII only. awk -v with ASCII control byte could false-positive as awk-v-nonascii. Detect only high-bit bytes per plan ([\x00-\x7F] complement).
- **Suggested revision**: Address the concern above.

### FINDING_35: architecture: scripts/test-ship-pr.sh:4375-4604
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Uses README.md not plan's sentinel-fix.txt for tier-order happy paths. None functionally; naming only. Optional rename to sentinel-fix.txt for traceability.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] architecture: scripts/test-ship-pr.sh:238-257
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Global make_repo launcher stubs auto-commit beyond plan's enumerated tier-order edits. Broader harness behavior change than plan listed. Document in test comments or narrow to cases that need it.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] architecture: docs/linting.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Harness cases 13-17 not reflected in docs row. Docs slightly under-describe harness scope. Add cases 13-17 to docs/linting.md and test-lint-awk-multibyte-regex.md if desired.
- **Suggested revision**: Address the concern above.

