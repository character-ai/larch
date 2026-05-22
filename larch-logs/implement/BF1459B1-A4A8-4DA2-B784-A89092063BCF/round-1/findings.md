### FINDING_1: code-quality: scripts/test-ship-pr.sh:1426
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stub section comment still documents pre-bypass semantics Maintainers extending tests may believe a bypass env is still modeled in the stub Rewrite comment: stub refuses commit whenever post-merge sentinel exists; no bypass
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/test-ship-pr.sh:403
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stub stderr text still mentions bypass Confusing failure output when the stub refuses commit Rename stderr line to sentinel-present wording without bypass
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-ship-pr.sh:1438
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] First guardrail ok message still says without bypass Implies a remaining bypass path for other sentinel cases Rephrase ok string to sentinel-present refusal only
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/test-ship-pr.sh:1366-1391
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New no-commit assertion uses HEAD range but labels it orphan-on-main Success copy overstates what rev-list head_before..HEAD proves Reword messages to no new commits during postmerge or add origin/main fixture
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/test-ship-pr.sh:1456-1478
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] LARCH_NO_LOGS_COMMIT test title still references skipping post-merge commit Obsolete coupling; suggests flag still toggles removed behavior Rename comment/ok text to parity regression for postmerge ordering only
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/implement/SKILL.md:70
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] NEVER #19 title narrower than body Skim readers may think only larch-log paths are forbidden Align first sentence with full no-commit-after-merge scope
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: larch-logs/implement/3890E7C4-6C5E-4070-BD32-F9974BFA66DB/**
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Old committed run logs still discuss removed bypass Stale narrative inside historical logs only Optional hygiene; not introduced by this diff
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: skills/implement/SKILL.md:10
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Overview still promises post-merge scoped larch-log.sh commit for merged final-summary alignment, contradicting NEVER #19 and ship-pr behavior in the same change. Orchestrators or contributors read line 10 and believe a post-merge log commit is still part of the merge contract, conflicting with NEVER #19 and updated ship-pr docs/scripts. Rewrite the merge-path sentence to match no post-merge git commit; reference NEVER #19 and tmpdir + API comment refresh only.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/test-ship-pr.sh:1426
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Stale comment claims stub allows commit when bypass env is set. Maintainers “fix” the stub or tests based on wrong mental model of sentinel vs env var. Update comment to state sentinel always blocks commit; second subtest documents legacy env var is ignored.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-ship-pr.sh:1394
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Section header still says downstream includes commit skip. Minor confusion when scanning tests for post-merge ordering. Remove “and commit” from the header to match manifest then report only.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-ship-pr.sh:1366-1391
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Positive assertion uses head_before..HEAD and labels it origin/main orphan semantics. Plan text asked origin/main..HEAD; test proves no local HEAD movement, not relationship to origin/main; message overclaims branch identity. Align assertion with origin/main fixture or narrow ok/comment wording to HEAD delta only.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-ship-pr.sh:1456-1478
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] postmerge_no_logs_commit framing implies a post-merge commit to skip that no longer exists; expectations may duplicate default postmerge test. Redundant or misleading regression signal if LARCH_NO_LOGS_COMMIT no longer changes postmerge observables. Rename/assert a still-unique behavior or dedupe the test.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] architecture: CHANGELOG.md:762
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Historical changelog entry references old Step 18 post-merge push narrative. Not part of this branch diff. Optional follow-up changelog alignment only.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] risk-integration: larch-logs/implement/3890E7C4-6C5E-4070-BD32-F9974BFA66DB/round-2/*.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Archived prompts mention removed bypass. Pre-existing committed run logs; not runtime. None unless policy requires scrubbing historical prompts.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/test-ship-pr.sh:1366-1390
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Positive postmerge test uses head_before..HEAD count and messages claim origin/main orphan semantics. A regression that leaves local main ahead of origin/main without creating a new commit during the harnessed invocation could still satisfy head_before..HEAD==0 while violating the stated origin/main..HEAD==0 acceptance criterion from the feature text. Align the assertion with origin/main..HEAD after ensuring the disposable repo has a consistent origin/main, or narrow the ok/fail strings to the HEAD-delta invariant actually tested.
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: scripts/test-ship-pr.sh:1394
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Section comment still mentions skipping a post-merge commit alongside write-final-report. Maintainers may think a post-merge larch-log commit path still exists when manifest fails. Update the comment to only describe manifest vs write-final-report ordering.
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: scripts/test-ship-pr.sh:1426
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Stub header comment still claims a bypass env allows commit through the stub. The comment contradicts the stub and the following assertions, inviting future mistaken “fixes.” Rewrite the comment to describe unconditional sentinel refusal; keep the env var sub-test as negative coverage for legacy env.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/test-ship-pr.sh:1456-1478
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Test framing still describes skipping a post-merge commit under LARCH_NO_LOGS_COMMIT. Operators reading tests infer a post-merge commit knob that no longer exists in ship-pr.sh. Retitle/reword to the real remaining contract or dedupe the test if it no longer differs from the default postmerge path.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] code-quality: larch-logs/implement/3890E7C4-6C5E-4070-BD32-F9974BFA66DB/** (grep hits)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Committed historical run logs reference the removed bypass and old reviewer prompts. Noise only when grepping for the old env var; not introduced by this diff’s touched files. Leave as historical artifact or refresh logs in a dedicated chore if desired; not required for #2552 correctness.
- **Suggested revision**: Address the concern above.

### FINDING_20: code-quality: scripts/test-ship-pr.sh:119,1438
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Stub stderr and first guard ok text still say commit is refused without bypass, implying a bypass path remains in the test model. A contributor rereads the harness, believes bypass semantics still exist, and weakens or re-adds an env-gated commit escape. Rephrase to unconditional sentinel refusal wording in stub stderr and ok message.
- **Suggested revision**: Address the concern above.

### FINDING_21: code-quality: scripts/test-ship-pr.sh:1426
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Comment claims the stub blocks commit unless bypass env is set; production and stub now always refuse commit when the sentinel exists. Same as above: wrong behavioral spec next to the guard tests risks reintroducing the regression #2552 removed. Rewrite the comment to match unconditional sentinel refusal including under LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR=1.
- **Suggested revision**: Address the concern above.

### FINDING_22: code-quality: scripts/test-ship-pr.sh:1456-1478
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Comment and ok string describe LARCH_NO_LOGS_COMMIT as skipping a post-merge commit that no longer exists on any path. Future refactor may keep a meaningless test or delete the wrong assertion because the documented contract is stale. Rename comment and ok to assert manifest plus write-final-report without commit, or remove redundant coverage.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: scripts/test-ship-pr.sh:1364-1391
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] New orphan test uses head_before..HEAD and success text references local main; feature text asked for origin/main..HEAD. Harness passes while diverging from the written acceptance criteria, or the message overclaims relative to the assertion. Align rev-list range with origin/main..HEAD if valid in make_repo, or narrow the ok message to the actual comparison.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: scripts/test-ship-pr.sh:1386-1390
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] orphan_count falls back to the string error when rev-list fails. A broken git in CI yields a misleading failure string instead of the root cause. Handle rev-list failure explicitly with a clear fail message.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: skills/implement/SKILL.md:70
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] NEVER #19 forbids any post-merge git commit broadly but cites only larch-log.sh sentinel as load-bearing enforcement. A non-larch-log commit after merge would not hit the sentinel; the doc overstates mechanical coverage vs orchestrator discipline. Qualify the rule: sentinel gates larch-log commits; other commits remain policy-only unless additional guards exist.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: scripts/test-ship-pr.sh:1366-1390
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Positive postmerge assertion uses head_before..HEAD instead of the planned origin/main..HEAD orphan metric. Reviewers or release gates that literalize the written acceptance line (origin/main..HEAD == 0) will not find that probe encoded; the ok text also implies an origin/main orphan check the shell does not execute. Add origin/main to the disposable repo for this subtest and assert origin/main..HEAD, or amend the issue plan to require the head delta and align user-facing strings with the chosen metric.
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: scripts/test-ship-pr.sh:1426
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Stale harness comment still describes a bypass that was removed from the stub. Future edits might reintroduce bypass semantics in the stub because the comment contradicts the code. Rewrite the comment to describe unconditional sentinel refusal.
- **Suggested revision**: Address the concern above.

### FINDING_28: architecture: scripts/test-ship-pr.sh:1456-1478
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] LARCH_NO_LOGS_COMMIT postmerge prose still frames a post-merge commit skip that no longer exists in ship-pr.sh. Maintainers may think --no-logs-commit still toggles a post-merge commit path. Rename or narrow the test to the still-meaningful invariants, or dedupe with the default postmerge ordering coverage.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: scripts/test-ship-pr.sh:1394
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Section header still lists commit among skipped downstream steps for manifest failure. Readers may infer a post-merge commit attempt remains on failure paths. Update the header to mention only manifest vs write-final-report ordering.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] architecture: docs paths named only in pasted implementation plan §7
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Implementation plan §7 cited docs/larch-log.md and docs/ship-pr.md, which are not present in-tree. None for the merged code path; this is a planning-artifact inconsistency versus feature_description. Treat scripts/*.md as canonical or fix the planning template paths.
- **Suggested revision**: Address the concern above.

### FINDING_31: **risk-integration** `scripts/test-ship-pr.sh:1426` — The comment above the stub guard still claims the stub models production “unless bypass env is set,” but this branch changed the stub so post-merge sentinel always refuses `commit` even when `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR=1`, matching the real `scripts/larch-log.sh` behavior. Leaving the old wording is integration-hazardous because a reader may believe a bypass remains or that the stub and production diverge. **Suggested fix:** Rewrite the comment to state that both the stub and `larch-log.sh` enforce unconditional post-sentinel refusal, and that the second invocation only proves a stray `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR=1` cannot re-open the path.
- **Reviewer**: dyn-bypass-residue-output.txt
- **Concern**: - **risk-integration** `scripts/test-ship-pr.sh:1426` — The comment above the stub guard still claims the stub models production “unless bypass env is set,” but this branch changed the stub so post-merge sentinel always refuses `commit` even when `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR=1`, matching the real `scripts/larch-log.sh` behavior. Leaving the old wording is integration-hazardous because a reader may believe a bypass remains or that the stub and production diverge. **Suggested fix:** Rewrite the comment to state that both the stub and `larch-log.sh` enforce unconditional post-sentinel refusal, and that the second invocation only proves a stray `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR=1` cannot re-open the path.
- **Suggested revision**: Address the concern above.

### FINDING_32: **risk-integration** `scripts/test-ship-pr.sh:1456-1458` — The section header still frames `LARCH_NO_LOGS_COMMIT` as “skips the post-merge larch-log commit,” but `run_postmerge_phase` no longer invokes `larch-log.sh commit` at all, so that flag no longer toggles a distinct post-merge commit gate (only pre-existing/other phases still interpret it). The test remains useful for ordering, but the comment misstates the contract operators should internalize after #2552. **Suggested fix:** Retitle/recomment to describe the invariant under test (postmerge still runs manifest + full `write-final-report` without any `commit` call) and avoid implying `LARCH_NO_LOGS_COMMIT` is what suppresses a post-merge commit that no longer exists.
- **Reviewer**: dyn-bypass-residue-output.txt
- **Concern**: - **risk-integration** `scripts/test-ship-pr.sh:1456-1458` — The section header still frames `LARCH_NO_LOGS_COMMIT` as “skips the post-merge larch-log commit,” but `run_postmerge_phase` no longer invokes `larch-log.sh commit` at all, so that flag no longer toggles a distinct post-merge commit gate (only pre-existing/other phases still interpret it). The test remains useful for ordering, but the comment misstates the contract operators should internalize after #2552. **Suggested fix:** Retitle/recomment to describe the invariant under test (postmerge still runs manifest + full `write-final-report` without any `commit` call) and avoid implying `LARCH_NO_LOGS_COMMIT` is what suppresses a post-merge commit that no longer exists.
- **Suggested revision**: Address the concern above.

### FINDING_33: **risk-integration** `scripts/test-ship-pr.sh:1366-1388` — The new “no orphan” check uses `git rev-list --count "${head_before}..HEAD"` while the ok text claims “zero orphan commits on local main” and the issue/plan text called for asserting `origin/main..HEAD` is empty. `head_before..HEAD` only proves nothing advanced `HEAD` during that single `ship-pr.sh` invocation; it does not prove the branch is not ahead of `origin/main` (the usual “orphan on main” symptom #2182/#2552 targeted). **Suggested fix:** If `make_repo` always defines `origin/main` at the disposable repo tip, assert `git rev-list --count origin/main..HEAD` (or equivalent) is `0` after postmerge; otherwise narrow the ok/fail message to “no new commits during postmerge” so the test name matches what is actually enforced.
- **Reviewer**: dyn-bypass-residue-output.txt
- **Concern**: - **risk-integration** `scripts/test-ship-pr.sh:1366-1388` — The new “no orphan” check uses `git rev-list --count "${head_before}..HEAD"` while the ok text claims “zero orphan commits on local main” and the issue/plan text called for asserting `origin/main..HEAD` is empty. `head_before..HEAD` only proves nothing advanced `HEAD` during that single `ship-pr.sh` invocation; it does not prove the branch is not ahead of `origin/main` (the usual “orphan on main” symptom #2182/#2552 targeted). **Suggested fix:** If `make_repo` always defines `origin/main` at the disposable repo tip, assert `git rev-list --count origin/main..HEAD` (or equivalent) is `0` after postmerge; otherwise narrow the ok/fail message to “no new commits during postmerge” so the test name matches what is actually enforced.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] Under `scripts/`, `skills/**/*.md`, and `docs/**/*.md`, `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR` no longer appears except in `scripts/test-ship-pr.sh` (negative coverage) and the historical regression sentence in `skills/implement/SKILL.md` NEVER #19; `scripts/refresh-run-logs.sh` and `scripts/larch-log-flush.sh` do not set or reference that variable (they call `larch-log.sh commit` without it).
- **Reviewer**: dyn-bypass-residue-output.txt
- **Concern**: - Under `scripts/`, `skills/**/*.md`, and `docs/**/*.md`, `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR` no longer appears except in `scripts/test-ship-pr.sh` (negative coverage) and the historical regression sentence in `skills/implement/SKILL.md` NEVER #19; `scripts/refresh-run-logs.sh` and `scripts/larch-log-flush.sh` do not set or reference that variable (they call `larch-log.sh commit` without it).
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] There are no `docs/larch-log.md` / `docs/ship-pr.md` files in this tree; cross-refs landed under `scripts/larch-log.md`, `scripts/ship-pr.md`, and `scripts/larch-log-flush.md` per the diff.
- **Reviewer**: dyn-bypass-residue-output.txt
- **Concern**: - There are no `docs/larch-log.md` / `docs/ship-pr.md` files in this tree; cross-refs landed under `scripts/larch-log.md`, `scripts/ship-pr.md`, and `scripts/larch-log-flush.md` per the diff.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] Committed material under `larch-logs/implement/...` still contains older reviewer text about the bypass; that is historical run-log content, not runtime wiring from this change set.
- **Reviewer**: dyn-bypass-residue-output.txt
- **Concern**: - Committed material under `larch-logs/implement/...` still contains older reviewer text about the bypass; that is historical run-log content, not runtime wiring from this change set.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] Git history on the branch: `1337ef10 Fixes #2552: remove LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR post-merge commit bypass`.
- **Reviewer**: dyn-bypass-residue-output.txt
- **Concern**: - Git history on the branch: `1337ef10 Fixes #2552: remove LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR post-merge commit bypass`.
- **Suggested revision**: Address the concern above.

### FINDING_38: **correctness** `scripts/test-ship-pr.sh:1456-1487` — The `postmerge_no_logs_commit` block still frames success as “`LARCH_NO_LOGS_COMMIT` skips the post-merge larch-log commit” (comment, `ok` string, and the `! grep '^LARCH_LOG_ARGS=commit'` clause). After this branch, `run_postmerge_phase` never calls `larch-log.sh commit` for either `--no-logs-commit true` or `false`, so the “no commit” part of the assertion is no longer evidence that the flag is honored in postmerge; it is redundant with the default `postmerge_flush` path and would still pass if postmerge accidentally stopped exporting `LARCH_NO_LOGS_COMMIT` but never reintroduced a commit. **Suggested fix:** Reframe the test as a regression that `--no-logs-commit true` must not skip manifest + `write-final-report` in postmerge (drop or rewrite commit-centric wording), merge it with the default postmerge ordering test behind a small matrix, or replace the `! commit` check with something that still varies with the flag in this phase (if nothing does, delete the duplicate case).
- **Reviewer**: dyn-no-logs-commit-vacuous-output.txt
- **Concern**: - **correctness** `scripts/test-ship-pr.sh:1456-1487` — The `postmerge_no_logs_commit` block still frames success as “`LARCH_NO_LOGS_COMMIT` skips the post-merge larch-log commit” (comment, `ok` string, and the `! grep '^LARCH_LOG_ARGS=commit'` clause). After this branch, `run_postmerge_phase` never calls `larch-log.sh commit` for either `--no-logs-commit true` or `false`, so the “no commit” part of the assertion is no longer evidence that the flag is honored in postmerge; it is redundant with the default `postmerge_flush` path and would still pass if postmerge accidentally stopped exporting `LARCH_NO_LOGS_COMMIT` but never reintroduced a commit. **Suggested fix:** Reframe the test as a regression that `--no-logs-commit true` must not skip manifest + `write-final-report` in postmerge (drop or rewrite commit-centric wording), merge it with the default postmerge ordering test behind a small matrix, or replace the `! commit` check with something that still varies with the flag in this phase (if nothing does, delete the duplicate case).
- **Suggested revision**: Address the concern above.

### FINDING_39: **code-quality** `scripts/test-ship-pr.sh:1426` — The inline comment still says the stub “blocks commit unless bypass env is set”, but the stub was changed to refuse `commit` whenever `post-merge-sentinel` exists, with no bypass. **Suggested fix:** Rewrite the comment to state unconditional refusal after the sentinel (aligned with production `larch-log.sh` and NEVER #19).
- **Reviewer**: dyn-no-logs-commit-vacuous-output.txt
- **Concern**: - **code-quality** `scripts/test-ship-pr.sh:1426` — The inline comment still says the stub “blocks commit unless bypass env is set”, but the stub was changed to refuse `commit` whenever `post-merge-sentinel` exists, with no bypass. **Suggested fix:** Rewrite the comment to state unconditional refusal after the sentinel (aligned with production `larch-log.sh` and NEVER #19).
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] The new “no orphan commit” check uses `git rev-list --count "${head_before}..HEAD"` instead of `origin/main..HEAD` from the written plan; `make_repo` only runs `git init` plus one commit and does not define `origin`, so counting since `head_before` is a reasonable harness substitute rather than a functional bug.
- **Reviewer**: dyn-no-logs-commit-vacuous-output.txt
- **Concern**: - The new “no orphan commit” check uses `git rev-list --count "${head_before}..HEAD"` instead of `origin/main..HEAD` from the written plan; `make_repo` only runs `git init` plus one commit and does not define `origin`, so counting since `head_before` is a reasonable harness substitute rather than a functional bug.
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] Section heading at `scripts/test-ship-pr.sh:1394` still mentions skipping “commit” in the manifest-failure scenario; the `ok` text at `scripts/test-ship-pr.sh:1417` is already tighter. Aligning the heading with “write-final-report only” would reduce leftover wording from the old post-merge commit ordering.
- **Reviewer**: dyn-no-logs-commit-vacuous-output.txt
- **Concern**: - Section heading at `scripts/test-ship-pr.sh:1394` still mentions skipping “commit” in the manifest-failure scenario; the `ok` text at `scripts/test-ship-pr.sh:1417` is already tighter. Aligning the heading with “write-final-report only” would reduce leftover wording from the old post-merge commit ordering.
- **Suggested revision**: Address the concern above.

