### OOS_1: [OUT_OF_SCOPE] ERR trap recover prints banner without exiting
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `recover` prints recovery guidance without exiting; unrelated failures may continue afterward (pre-existing). Tightening global error handling may require `recover` to exit 1.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] recover() ERR trap and already-latest failure ordering
- **Reviewer(s)**: dyn-shell-upgrade-logic-output.txt
- **Severity**: nit
- **Concern**: `trap recover ERR` expands variables at call time; if `refresh_larch_marketplace` fails on already-latest repair, script aborts before printing misleading “Already at latest…” success line.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_11: [OUT_OF_SCOPE] Already-latest marketplace-only repair is contract-intentional
- **Reviewer(s)**: dyn-shell-upgrade-logic-output.txt, dyn-migration-path-risk-output.txt
- **Severity**: nit
- **Concern**: Counter-evidence: documented in upgrade-larch.md; repair without reinstall does not strand the user without an install the way upgrade-path remove-then-failed-add can; on success stamp/prune still run and exit 0.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_12: [OUT_OF_SCOPE] Round-1 migration from pre-sparse release
- **Reviewer(s)**: dyn-shell-upgrade-logic-output.txt
- **Severity**: latent
- **Concern**: First hop from older script on a version bump may still use prior marketplace logic until a second `/upgrade-larch` at latest stable; pre-existing migration class, not introduced by cone helpers alone.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_13: [OUT_OF_SCOPE] Test removal (Part 4) intentional
- **Reviewer(s)**: dyn-shell-upgrade-logic-output.txt, dyn-migration-path-risk-output.txt
- **Severity**: nit
- **Concern**: Harness deletion is plan-intentional; no additional in-scope shell defect from deletion alone for this focus area.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_14: [OUT_OF_SCOPE] Recovery contract documents manual rm -rf; gap is automation only
- **Reviewer(s)**: dyn-migration-path-risk-output.txt
- **Severity**: nit
- **Concern**: upgrade-larch.md and `recover()`/verification banners already document operator steps when remove+add fails.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_15: [OUT_OF_SCOPE] Mermaid path repointing otherwise consistent
- **Reviewer(s)**: dyn-mermaid-path-sync-output.txt
- **Severity**: nit
- **Concern**: Counter-evidence: lint script, Makefile, CI cache paths, and docs align on `mermaid-lint/`; `test-mermaid-fragments.sh` delegates without hardcoded root `node_modules`; setup-node cache pattern matches subdirectory lockfile.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_16: [OUT_OF_SCOPE] Legacy gitignored root node_modules not used by new resolution
- **Reviewer(s)**: dyn-mermaid-path-sync-output.txt
- **Severity**: nit
- **Concern**: Pre-move root `node_modules` may linger locally but is not used by updated resolution order and was not introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] lint-mermaid-fences.sh lazy ensure_mmdc refactor beyond minimal repoint
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Broader lazy `ensure_mmdc` refactor widens diff surface on an install-speed PR; defer or split if a smaller PR is preferred.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] test-mermaid-fragments accepts exit 2 when mmdc missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Shard 9 can pass without mermaid-lint toolchain for nested-fence case; pre-existing, not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_4: [OUT_OF_SCOPE] Wildcard Bash allowlist for all larch script paths unchanged
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Compromised or unexpected script under any cached version remains pre-authorized; narrow allowlist is a follow-up, not introduced here.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_5: [OUT_OF_SCOPE] Install-stamp prune contract lacks dedicated harness
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: After `test-upgrade-larch-prune` removal, future prune/stamp regressions lack CI signal (plan-accepted tradeoff).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_6: [OUT_OF_SCOPE] ERR trap after uninstall mid-upgrade leaves plugin uninstalled
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing failure mode unrelated to sparse-checkout changes; operator must run manual recover.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] Prune keeps eight stamped dirs; legacy fat versions age out slowly
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing; harness removal increases refactor risk without CI guard; plan-intentional test removal.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_8: [OUT_OF_SCOPE] CHANGELOG historical entries rewritten
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Removed test-upgrade-larch names from historical changelog entries; not required by plan; no functional impact.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] Cone matching likely correct for current git cone output
- **Reviewer(s)**: dyn-shell-upgrade-logic-output.txt, dyn-migration-path-risk-output.txt
- **Severity**: nit
- **Concern**: Counter-evidence: sorted `git sparse-checkout list` vs sorted `normalize_sparse_dirs` is order-robust; cone mode emits bare directory names, so string equality is not inherently format-broken for current git behavior.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

