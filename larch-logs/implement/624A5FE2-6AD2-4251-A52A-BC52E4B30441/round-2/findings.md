### FINDING_1: architecture: skills/implement/references/rebase-rebump-subprocedure.md:36 vs scripts/ship-pr.sh:2490-2497
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Markdown sub-procedure step 1 continues on DROPPED=false while ship-pr run_rebase_rebump stalls. Step 8b prompt-driven recovery may proceed with a stale bump while Step 10/12 shell path exits 4 on the same drop-bump outcome. Align step 1 with ship-pr stall semantics or document and implement an explicit dual-policy split.
- **Suggested revision**: Address the concern above.

### FINDING_2: architecture: skills/implement/references/rebase-rebump-subprocedure.md:126-127 vs scripts/ship-pr.sh:529-535
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Sub-procedure step 4a says commit-changelog is best-effort; ship-pr is fail-closed. Prompt orchestrator may skip or ignore CHANGELOG failures that would stall the same branch under ship-pr re-bump. Update step 4a to require commit success or change ship-pr to match best-effort per caller family.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/implement-finalize.sh:563-653 and scripts/commit-changelog.sh:26-176
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicated Keep-a-Changelog awk for insert and replaces-version instead of plan reuse via write_changelog_entry. Future heading-format fixes must be applied twice; drift risks wrong stale-entry removal on CI re-bump. Extract shared lib-changelog-entry.sh used by write_changelog_entry and commit-changelog.sh.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: scripts/ship-pr.sh:532-534
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] ship_pr_commit_changelog_after_rebump stalls on COMMITTED=false even when exit 0 and CHANGELOG already correct after rebase replay. Benign re-bump after conflict resolution may exit 4 despite a valid separate CHANGELOG commit already at HEAD. Treat exit-0 COMMITTED=false as success when tree is clean and HEAD subject already matches new version.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/implement-finalize.sh:732-735,760-763
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate set +e around write_changelog_entry and commit-changelog calls. Readability only; no functional change. Remove redundant set +e pairs in maybe_update_changelog.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: scripts/ship-pr.sh:2486-2497
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] run_rebase_rebump stalls on any DROPPED=false without HAS_BUMP or no-bump-in-range guard HAS_BUMP=false repo on ci-wait ACTION=rebase with no bump in 20 commits: drop no-ops correctly but ship-pr exit 4 blocks valid rebase-only recovery Stall only when a bump candidate was found but refused; or skip stall when HAS_BUMP=false and no bump subject in walk window
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/ship-pr.sh:512-536
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] ship_pr_commit_changelog_after_rebump is best-effort but ship-pr.md claims fail-closed apply-bump updates plugin.json; commit-changelog returns COMMITTED=false; push proceeds with CHANGELOG section still at prior version Update ship-pr.md or fail-closed when ## [NEW_VERSION] is missing from CHANGELOG.md
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/ship-pr.sh:518-521
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Missing RRR_OLD_BUMP_VERSION skips --replaces-version so stale CHANGELOG headings can remain after re-bump Drop records SHA but subject parse fails; replayed CHANGELOG still ## [1.2.3] while plugin.json is 1.2.4; COMMITTED=false then WARN and push Fallback replaces-version from CHANGELOG scan or stall when NEW heading absent
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/references/rebase-rebump-subprocedure.md:35-36,126-127
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 1 continues on DROPPED=false but step 4a requires OLD_BUMP_SHA for --replaces-version Step 8b orchestrator continues after DROPPED=false; step 4a cannot strip stale CI CHANGELOG entries per FINDING_25 Gate replaces-version on DROPPED=true or align step 1 with ship-pr fail-closed drop
- **Suggested revision**: Address the concern above.

### FINDING_10: architecture: scripts/implement-finalize.sh:563-653
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Plan write_changelog_entry --replaces-version not implemented; logic duplicated in commit-changelog.sh Step 8a and re-bump paths diverge on category/Unreleased handling over time Share one CHANGELOG writer or document and test retitle-only re-bump contract
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/implement/references/conflict-resolution.md:29,41
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Phase 1 always ours on CHANGELOG.md may drop feature release notes before step 4a Rebase conflict: feature-only ## [X.Y.Z] bullets; ours keeps main; re-bump retitle cannot restore lost bullets Limit CHANGELOG trivial ours to Update CHANGELOG commits or use auto-resolve-changelog in Phase 1
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: .claude/skills/bump-version/scripts/classify-bump.sh:118
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Transparent walk depth 4 vs plan 1-3 Slightly wider BUMP_TYPE=NONE idempotency window Cap walk at 3 unless a fourth transparent shape is required
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] architecture: scripts/git-amend-add.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] No callers after refactor; script kept by plan None unless removing dead code is desired Remove or keep as documented unused primitive
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-ship-pr.sh:462-473
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] _install_rebump_dep_stubs sets commit-changelog.sh to exit 0 with no COMMITTED output. rebump_changelog_auto and similar cases run run_rebase_rebump with CHANGELOG.md present; ship-pr treats empty COMMITTED as success, so harness passes without validating separate CHANGELOG commit behavior. Stub COMMITTED=true when CHANGELOG exists, or assert commit-changelog invocation/output in rebump scenarios.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-ship-pr.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Missing symmetric stall test for commit-changelog failure on re-bump. Production fail-closed on COMMITTED=false (issue #2852 class) has no harness regression; drop-bump DROPPED=false is tested but changelog failure is not. Add rebump_commit_changelog_fail_stalls: stub COMMITTED=false or exit 1, assert ship-pr exits 4 after ACTION=rebase.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/implement/references/rebase-rebump-subprocedure.md:127
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Step 4a still documents CHANGELOG update as best-effort non-blocking while ship-pr is fail-closed. Step 8b orchestrator following Markdown may not stall on commit-changelog failure, reproducing silent push without matching CHANGELOG. Align step 4a with ship-pr.md fail-closed semantics and cross-reference ship_pr_commit_changelog_after_rebump.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/ship-pr.sh:528-535
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] ship_pr_commit_changelog_after_rebump accepts empty/missing COMMITTED after exit 0. Any caller or stub that exits 0 without COMMITTED=true skips changelog commit yet continues re-bump/merge. Require COMMITTED=true when CHANGELOG.md exists; treat empty/missing COMMITTED like COMMITTED=false.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/test-commit-changelog.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test for staged-only CHANGELOG.md dirty tree (plan Guard 1 parity). Step 8a may stage CHANGELOG before commit-changelog; unstaged-only path is covered but staged-only is not. Add Test 9: stage CHANGELOG edit only, assert COMMITTED=true and CHANGELOG-only commit.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/test-ship-pr.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No assertion that run_rebase_rebump passes --allow-changelog-only --max-depth 20 to drop-bump. Regression could drop flags and reintroduce CHANGELOG-only bump stall or depth exhaustion without failing CI. Add drop-bump stub that logs argv; assert both flags on re-bump invocation.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] risk-integration: scripts/implement-finalize.sh:563-733
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan write_changelog_entry --replaces-version not implemented; logic only in commit-changelog.sh. Step 8a bullet formatting vs re-bump retitle awk could diverge over time. Pre-existing architectural split; commit-changelog Tests 7-8 partially mitigate.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] risk-integration: scripts/drop-bump-commit.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] --max-depth 20 not stress-tested under 10+ CI-fix commits. Latent depth exhaustion (FINDING_42) if max-depth regresses to 10. Mitigation already in ship-pr.sh; out of scope for this diff’s test additions.
- **Suggested revision**: Address the concern above.

### FINDING_22: `6c3c24b2` — docs-only (#2873); no executable surface.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `6c3c24b2` — docs-only (#2873); no executable surface.
- **Suggested revision**: Address the concern above.

### FINDING_23: `8280e1c7` — #2852: `commit-changelog.sh`, `drop-bump-commit.sh --allow-changelog-only`, `ship-pr.sh` / `implement-finalize.sh` wiring, `classify-bump.sh` transparent-commit walk, docs/tests.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `8280e1c7` — #2852: `commit-changelog.sh`, `drop-bump-commit.sh --allow-changelog-only`, `ship-pr.sh` / `implement-finalize.sh` wiring, `classify-bump.sh` transparent-commit walk, docs/tests.
- **Suggested revision**: Address the concern above.

### FINDING_24: `a082ec6f` — round-1 hardening: diff-based transparent-commit checks in `classify-bump.sh`, `commit-changelog.sh` `--replaces-version` fallbacks, stall on `DROPPED=false`, harness coverage.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `a082ec6f` — round-1 hardening: diff-based transparent-commit checks in `classify-bump.sh`, `commit-changelog.sh` `--replaces-version` fallbacks, stall on `DROPPED=false`, harness coverage. **Trust-boundary / injection pass** on the changed shell: | Area | Assessment | |------|------------| | Command injection | `--version` / `--replaces-version` gated by `^[0-9]+\.[0-9]+\.[0-9]+$` before use in `awk -v` or `git-commit.sh -m`; no `eval`/`exec`; commit messages go through `git-commit.sh` temp file. | | Destructive git ops | `drop-bump-commit.sh` still requires bump subject regex + allowed-file guards; `--allow-changelog-only` only relaxes the CHANGELOG-only case and is passed from fixed callers (`ship-pr.sh`, sub-procedure), not exposed as a global default. | | Idempotency spoofing | Round-1 fix requires transparent commits to touch **only** `CHANGELOG.md` or `larch-logs/**`, not subject alone — closes subject-only bypass. | | State / version parsing | `RRR_OLD_BUMP_VERSION` derived from dropped commit subject with semver re-validation before `--replaces-version`. | | Secrets | No new hard-coded credentials in changed scripts; `larch-logs/**` in diff is intentional run output (out of scope per instructions). | | Conflict auto-resolve | Adding `CHANGELOG.md` to Phase 1 trivial files follows the same upstream-`ours` pattern as `plugin.json`, with step 4a refresh documented — no new auth/network boundary. | The `--allow-changelog-only` flag intentionally widens which bump-shaped commits may be dropped, but only for commits that already match the strict bump subject regex and a single-file `CHANGELOG.md` diff; callers with git-write access already exceed that threat model. No path was found where untrusted argv or unvalidated interpolation reaches a shell.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/ship-pr.sh:512-536
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] ship_pr_commit_changelog_after_rebump hard-fails on COMMITTED=false while Markdown step 4a is best-effort. Step 12 CI loop stalls after a good re-bump when commit-changelog legitimately no-ops. Align ship-pr with sub-procedure tolerance or update docs and add a no-op harness case.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: scripts/commit-changelog.sh:179-182
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] replaces-version path exits 1 when awk produces no diff. Post-rebase CHANGELOG already at NEW_VERSION causes ship-pr stall. Treat already-correct content as COMMITTED=false exit 0 or idempotent success.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: scripts/ship-pr.sh:2490-2497 vs skills/implement/references/rebase-rebump-subprocedure.md:35-36
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] ship-pr stalls on DROPPED=false; Markdown 8b sub-procedure continues. Step 8b may double-bump while Step 12 stalls on the same guard failure class. Document asymmetry or align 8b to stall when drop fails.
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: scripts/ship-pr.sh:512-536
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Re-bump never refreshes manifest bullets; only retitles CHANGELOG version. CI re-bump PR ships wrong changelog bullets for the final patch. Re-run write_changelog_entry before commit-changelog on re-bump or document limitation.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: scripts/implement-finalize.sh:761-786
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 8a does not require COMMITTED=true from commit-changelog. COMMITTED=false success could report updated without a CHANGELOG commit. Parse COMMITTED=true before marking CHANGELOG_STATUS=updated.
- **Suggested revision**: Address the concern above.

### FINDING_30: architecture: scripts/commit-changelog.sh:26-82 vs scripts/implement-finalize.sh:563-652
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Duplicate CHANGELOG writers; duplicate-heading guard only in implement-finalize. Messy history can get duplicate version sections from commit-changelog paths. Share one writer or port exit-4 duplicate detection.
- **Suggested revision**: Address the concern above.

### FINDING_31: code-quality: scripts/ship-pr.sh:2480
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Comment says drop-bump is non-fatal but DROPPED=false now stalls. Misleading for operators debugging stalls. Update comment to describe stall-on-false behavior.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/test-step-7a.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Harness markdown stale vs test-step-7a.sh (tracked #2862). Operator confusion when cross-walking docs. Fix in follow-up issue #2862.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] code-quality: larch-logs/implement/FC85DE8D-CBEF-4652-B425-FA0825CFDF24/
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Intentional implement run-log flush in PR. N/A per docs/run-logs.md. No action for this feature review.
- **Suggested revision**: Address the concern above.

### FINDING_34: correctness: scripts/ship-pr.sh:512-536
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Re-bump path fail-closes on commit-changelog COMMITTED=false despite plan requiring best-effort tolerance. After apply-bump succeeds, commit-changelog can exit 0 with COMMITTED=false when CHANGELOG already matches; ship-pr stalls Step 10/12. Treat exit 0 + COMMITTED=false as success; fail only on non-zero exit or remaining dirty CHANGELOG.md.
- **Suggested revision**: Address the concern above.

### FINDING_35: architecture: scripts/implement-finalize.sh:563-653
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan required --replaces-version to pass through write_changelog_entry; round 1 removed it and duplicated awk only in commit-changelog.sh. Stale-entry removal no longer shares write_changelog_entry with Step 8a; acceptance failure-mode #4 wording is inaccurate. Restore write_changelog_entry --replaces-version and call it from commit-changelog.sh, or update plan/docs to match the split implementation.
- **Suggested revision**: Address the concern above.

### FINDING_36: risk-integration: skills/implement/references/rebase-rebump-subprocedure.md:126-127 vs scripts/ship-pr.sh:512-536
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Sub-procedure 4a documents non-blocking CHANGELOG commit; ship-pr re-bump path is fail-closed. Prompt-side Step 8b recovery may continue while Step 10/12 ship-pr stalls on the same helper outcome. Align prose with ship-pr strictness or restore plan best-effort COMMITTED=false handling in ship_pr_commit_changelog_after_rebump.
- **Suggested revision**: Address the concern above.

### FINDING_37: correctness: scripts/ship-pr.sh:2490-2497 vs skills/implement/references/rebase-rebump-subprocedure.md:35-36
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] ship-pr stalls on drop-bump DROPPED=false; sub-procedure still says continue with warning. Step 12 shell path stalls where Markdown orchestration would proceed, diverging from sub-procedure contract. Document ship-pr stall semantics in step 1 or narrow DROPPED=false stall to non-recoverable cases only.
- **Suggested revision**: Address the concern above.

