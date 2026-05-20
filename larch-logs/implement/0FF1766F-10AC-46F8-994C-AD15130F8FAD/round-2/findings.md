### FINDING_1: [OUT_OF_SCOPE] correctness: scripts/rebase-push.sh:244-296
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] rebase-push uses raw git push not git-force-push.sh; no porcelain guard. A flow that force-pushes only via rebase-push.sh could still push with a dirty tree. Track separately if global invariant is desired; not introduced by this diff.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] risk-integration: scripts/git-force-push.sh (tests)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No new automated tests for git-force-push dirty path Behavior change in git-force-push.sh is not directly exercised by added tests Consider a small focused harness in a follow-up PR (optional; not a regression of existing tests)
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] risk-integration: scripts/git-push.sh:44
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Plain push path has no clean-tree guard Pre-existing gap relative to a maximal reading of issue #2434 before any push File not touched by this branch diff
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: scripts/ship-pr.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Issue names ship-pr.sh; diff guards lower scripts Orchestrator push paths still hit guarded helpers None; document layering if stakeholders insist on ship-pr wording
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: docs/workflow-lifecycle.md:171-173
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Lifecycle doc claims clean tree before any git push to origin via only create-pr and git-force-push. Readers assume CI-fix and fork rebase pushes are covered; they are not, so operational guidance is wrong. Tighten wording to actual guarded scripts or extend guards to all ship-pr push wrappers and update the section accordingly.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: docs/workflow-lifecycle.md:26-28
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc says /implement asserts clean tree Readers may look in SKILL instead of push scripts Reword to attribute guard to create-pr/git-force-push
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/create-pr.md:69-76
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Exit 2 table omits new git status inspection failure mode Operators reading only the table may not map exit 2 from git status failures Extend exit 2 documentation to include working-tree inspection failures before push
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/create-pr.sh:97-108 scripts/git-force-push.sh:59-73
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated clean-tree guard logic across two scripts. Future edits may update one copy only, causing inconsistent operator messaging or exit codes. Extract a shared assert-clean-working-tree helper sourced by both scripts (and future push wrappers).
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/test-create-pr.sh:199
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Clean-tree test redirects stderr to /dev/null Harness failure produces less actionable local output Save stderr to a file or remove the redirect
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/test-create-pr.sh:199-200
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Clean-tree test drops stderr via 2>/dev/null. Harness hides real failures during clean-tree regression, slowing diagnosis. Capture stderr to a file and assert empty or assert absence of dirty-tree errors on success.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: docs/workflow-lifecycle.md:171-173
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Wording implies all origin pushes are guarded while ship-pr still uses git-push.sh without a clean-tree check Operator trusts the doc and assumes no dirty-tree push is possible during CI-fix iterations; extra uncommitted files not staged by the lint-fix path can remain local-only while git-push succeeds Rephrase to only claim create-pr and git-force-push paths or document git-push.sh as a separate surface and align behavior if full coverage is required
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: feature_description vs branch diff
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Written acceptance names ship-pr.sh; diff only touches create-pr.sh and git-force-push.sh. Strict reading of the issue could reject the PR for not editing ship-pr.sh even though pushes are delegated. Document indirect coverage or add a redundant guard in ship-pr.sh if required.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/create-pr.sh:212-223;scripts/git-force-push.sh:59-73
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Check-then-act gap between porcelain snapshot and actual push Extremely narrow window where tree becomes dirty after the guard yet before push; push still omits new edits Document limitation or accept as inherent; optional follow-up only if product requires stronger guarantees
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/git-force-push.md:28 scripts/git-force-push.md:39-43
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Doc says exit 2 emits no stdout keys, but BRANCH is emitted before git status can fail with exit 2. Parsers or tests that treat any exit 2 as empty stdout mis-handle rare git status failures. Split exit-2 documentation into pre-BRANCH vs post-BRANCH failure semantics to match scripts/git-force-push.sh.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/git-force-push.md:28,43
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Docs say exit 2 emits no stdout keys. git status --porcelain fails after emit_kv BRANCH; script exits 2 with BRANCH= already printed, contradicting the contract bullets and table. Update the contract (split exit-2 meanings or move BRANCH emission after successful status).
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/implement-finalize.sh:896-913
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 8b infers failure only from STATUS in captured output; dirty-tree exit 1 omits STATUS. After a successful 8b rebase, an unstaged tracked edit causes git-force-push.sh to exit 1 with only BRANCH= plus dirty-list stderr; push_status is empty so the default arm mis-labels the failure as lease refusal. Branch on rc and/or match dirty-tree messages; or emit a dedicated STATUS for dirty-tree and handle it explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/test-create-pr.sh:471
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Clean-tree test redirects stderr to /dev/null. Early unexpected failures may be harder to diagnose in CI logs. Preserve stderr or assert it is empty.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/test-create-pr.sh:474-492
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Dirty-tree tests only assert non-zero exit, not exit code 1 A weaker contract allows silent semantic drift of exit codes Add explicit rc==1 assertions (and optionally ERROR: prefix) for both dirty scenarios
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: docs/workflow-lifecycle.md:173
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Prose ties the invariant to /implement only. Operators debugging ship-pr-only runs may misunderstand where enforcement lives. Name create-pr.sh / git-force-push.sh or mention ship-pr.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/git-force-push.sh:57-71
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] merge-pr error templates treat missing STATUS as unknown Dirty tree abort can look like force-push divergence in merge-pr diagnostics Add STATUS=dirty_worktree or merge-pr sentinel detection
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/git-force-push.sh:59-73
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness covers git-force-push clean-tree guard Direct-caller regressions slip past make lint until merge/implement paths Add tmp-repo tests mirroring create-pr dirty/clean cases
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/git-push.sh:1-86
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] CI-fix pushes from ship-pr use git-push.sh without a clean-tree guard. Operator has local uncommitted edits while ship-pr runs run_ci_fix_vendor; git-push.sh pushes commits but leaves edits unpushed; merged PR still misses those edits (same silent-loss class as #2434). Add the same git status --porcelain gate to git-push.sh (or a shared helper) before the retry loop; align exit codes with ship-pr failure handling.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/git-push.sh:44-46;scripts/ship-pr.sh:1166
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Plain pushes via git-push.sh bypass the new clean-tree guard used on create-pr/force-push paths Residual silent-exclusion risk for uncommitted edits on CI-fix push iterations if those edits fall outside the staged allowlist Add the same porcelain check to git-push.sh or document git-push as an explicit exception with rationale
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/merge-pr.sh:193-199
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Flush-recovery parses git-force-push stdout assuming exit 1 implies parseable PUSHED/STATUS; dirty-tree guard emits only BRANCH= Operator sees generic force-push failure with status=unknown during merge-pr flush recovery while the real issue is uncommitted local changes; wrong recovery narrative and harder debugging Treat dirty output distinctly: parse stderr/dirty sentinel, or emit STATUS=dirty_tree (or dedicated exit code) from git-force-push.sh; adjust merge-pr.sh branch logic
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/test-create-pr.sh:202-220
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Dirty-tree tests only assert nonzero exit and headline substring Regression dropping porcelain listing or using wrong exit class could pass Add rc==1 and grep for expected porcelain paths
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: skills/implement/references/rebase-rebump-subprocedure.md:124-129
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Doc still ties exit 1 solely to diverged_retry_failed and full PUSHED/STATUS contract Implementer following only the subprocedure mis-triages new dirty-tree exit 1 as lease/diverge failure Update subprocedure to document overloaded exit 1, absent PUSHED/STATUS on dirty path, and stderr cues; align with git-force-push.md
- **Suggested revision**: Address the concern above.

