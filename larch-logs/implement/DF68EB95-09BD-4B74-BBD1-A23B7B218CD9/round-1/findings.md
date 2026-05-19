### FINDING_1: **Important** correctness: `skills/upgrade-larch/scripts/upgrade-larch.sh:294-314` and `skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:217-222` - the cap prune still only inspects the first `VERSION_COUNT - KEEP_LIMIT` sorted entries, so protected entries in that prefix are skipped without pruning replacement candidates. Concrete scenario: the new active-session case seeds `29.1.20`-`29.1.28`, installs `29.1.30`, and pins `29.1.21`; the script removes `29.1.20`, skips pinned `29.1.21`, and leaves 9 cached versions, while the updated test incorrectly expects `29.1.22` to remain. Fix the loop to continue pruning until the retained set is at most 8, skipping protected versions but removing later unpinned candidates, and update the test to assert `29.1.22` is removed in that case.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** correctness: `skills/upgrade-larch/scripts/upgrade-larch.sh:294-314` and `skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:217-222` - the cap prune still only inspects the first `VERSION_COUNT - KEEP_LIMIT` sorted entries, so protected entries in that prefix are skipped without pruning replacement candidates. Concrete scenario: the new active-session case seeds `29.1.20`-`29.1.28`, installs `29.1.30`, and pins `29.1.21`; the script removes `29.1.20`, skips pinned `29.1.21`, and leaves 9 cached versions, while the updated test incorrectly expects `29.1.22` to remain. Fix the loop to continue pruning until the retained set is at most 8, skipping protected versions but removing later unpinned candidates, and update the test to assert `29.1.22` is removed in that case.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: larch-logs/implement/DF68EB95-09BD-4B74-BBD1-A23B7B218CD9/plan-goals-test.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Embedded plan text understates cap removals for the pinned scenario. Readers of the run log may misunderstand retention. Update narrative in a future run log only if you care about log accuracy; not a product bug.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: skills/upgrade-larch/scripts/upgrade-larch.sh:324
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Cap-prune loop mutates SANITIZED_VERSIONS via pattern substitution on all array elements Unrelated to floor removal; long-standing pattern risk if version strings ever become substrings of each other Refactor only if you choose to harden pruning elsewhere; not required for this PR
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:273-307
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Inconsistent preserve-warning wording between the newer-than-stable branch and the cap-retention branch. Minor operator confusion only. Unify warning strings in a dedicated follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:318-325 (unchanged idiom)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Array shrink via "${SANITIZED_VERSIONS[@]/$version}" is easy to mis-substring-match; pre-existing. N/A unless refactoring prune loop. Leave as pre-existing or refactor array removal to index-based delete in a separate change.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] correctness: skills/upgrade-larch/scripts/upgrade-larch.sh:318-325
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Cap-prune rebuilds SANITIZED_VERSIONS via "${SANITIZED_VERSIONS[@]/$version}" which can mis-remove unrelated entries when one version is a substring of another. Rare plausible-looking wrong deletions or prune loop oddities if version strings collide. Replace with index-based or filtered array rebuild (separate change).
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:324
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Array element removal via pattern substitution is fragile for some version strings. Pre-existing; not introduced by floor removal. Consider a safer filter in a future refactor if versions ever stop matching the pattern assumptions.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: skills/upgrade-larch/scripts/test-upgrade-larch-prune.md:19-23
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Edit-in-sync footer still names SKILL/Makefile/docs for any pruning change while this change set is narrower. Minor contributor confusion about whether follow-up doc edits are mandatory. Narrow the footer wording or confirm no consumer-facing drift in those files.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:204-212
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] The harness still invokes run_case unparseable-session-prunes-normally while assertions require all seeded versions to remain. Future maintainers may select or copy the wrong scenario based on the misleading name. Rename the case to reflect under-cap retention (e.g. unparseable-session-keeps-under-cap).
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:248-251
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] run_case and fail strings still say unparseable-session-prunes-normally while the case now verifies no pruning under the cap Readers and log output suggest pruning still happens for unparseable roots Rename to unparseable-session-keeps-under-cap and update fail message labels
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: skills/upgrade-larch/scripts/upgrade-larch.md:29
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Active-session prune doc still claims malformed session-env does not block pruning in a way that implied the old floor sweep. Reader expects unused olds can still be deleted under the 8-cap with malformed session metadata; after floor removal under-cap caches retain those dirs. Reword to tie old-version deletion to exceeding the retention cap and the newer-than-stable sanitize pass.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:163-173 (per round-1 diff)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Over-cap active-session expectations only prune one directory while KEEP_LIMIT requires two removals from 10 cached versions. Cap-correct script removes 29.1.20 and 29.1.22 but test still requires 29.1.22 to exist → harness fails; or harness passes while cache stays >8 versions → false green. Assert absence of both pruned versions (or adjust seed/pins so only one removal is required); match current workspace if that is the intended final state.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:219-222;skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:265-267
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] active-session and crlf cap-prune assertions require 29.1.22 to remain after upgrade while only requiring 29.1.20 to be pruned 10 cached version dirs with KEEP_LIMIT=8 and only 29.1.21 pinned/executing: upgrade-larch.sh removes 29.1.20 then 29.1.22; the test loops still demand 29.1.22 exist so the harness fails on a correct run Add a second prune assertion for 29.1.22 (and remove it from the keep list), add a multi-pin variant, or seed fewer than 10 dirs if the intent is a single trim; align the written plan bullet with cap math
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: larch-logs/implement/DF68EB95-09BD-4B74-BBD1-A23B7B218CD9/manifest.json:10
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Committed manifest.json shows status in-progress for a flushed implement log bundle Downstream tooling or humans may treat the run as unfinished or trigger stale-run handling Set status to a terminal value when committing flushed logs or omit manifest fields that cannot be accurate
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:active-session-keeps-version (diff.txt hunk: loop keeps 29.1.22 after single prune of 29.1.20)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Cap loop removes two dirs (20 and 22) when ten cached versions exist, LATEST_STABLE is 30, only 21 is pinned, and INSTALLED_VERSION basename stays 21. CI/local harness fails: test expects 29.1.22 directory to remain after upgrade. Add assertion that 29.1.22 is pruned and remove 29.1.22 from the keep loop (or reduce seeded versions so only one eviction is needed).
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:crlf-session-root-keeps-version (diff.txt hunk: same keep list including 29.1.22)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Same cap arithmetic as active-session with CRLF-trimmed pin on 29.1.21. Same failure mode as active-session case for crlf-session-root-keeps-version. Mirror the active-session fix for the CRLF case.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:unparseable-session-prunes-normally (diff.txt)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Case name says prunes normally but under-cap behavior keeps all versions. Misleading name when debugging future prune regressions. Rename case and fail strings to reflect under-cap retention.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/upgrade-larch/scripts/test-upgrade-larch.sh (plan)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Diff does not show test-upgrade-larch.sh edits or proof the plan’s second harness ran. Cannot verify from diff alone that the broader upgrade harness still passes after the behavior change. Run test-upgrade-larch.sh in CI or before merge; add a change only if a failure appears.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/upgrade-larch/scripts/upgrade-larch.md (post-diff)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Limitations (Angle B) removed per plan; cross-train retention under cap no longer documented. Operators lose explicit note that non-current trains are not special-cased below the cap. Optional single-sentence retention note if product still wants that visibility.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/upgrade-larch/scripts/upgrade-larch.md:27-31
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Removing the former Limitations subsection drops the only explicit note that under the eight-version cap the cache is not aggressively minimized beyond removing versions newer than verified stable (and pins). An operator upgrades, sees several old patch directories still on disk with fewer than eight entries, and treats it as a failed prune or bug. Add a concise sentence under step 8 or a small Retention limits note describing under-cap behavior and what the cap loop does when count exceeds eight.
- **Suggested revision**: Address the concern above.

