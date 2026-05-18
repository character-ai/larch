### FINDING_1: **Important** `security` `scripts/redact-tmpdir-paths.sh:21-24` — The new bare operator-repo-root redaction still misses quoted JSON/string values, so a common committed-log shape remains unredacted. Concrete scenario: `{"cwd":"/Users/example/my.repo"}` passes through `scripts/redact-tmpdir-paths.sh` unchanged, leaking the operator username and repo path despite the new `SECURITY.md` guarantee for end-of-value repo roots. Extend the delimiter handling to capture and preserve quotes/JSON separators, and add regression tests in `scripts/test-redact-tmpdir-paths.sh` for quoted JSON values like `{"cwd":"/Users/example/my.repo"}` and `{"cwd":"/Users/example/my.repo","x":1}`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `security` `scripts/redact-tmpdir-paths.sh:21-24` — The new bare operator-repo-root redaction still misses quoted JSON/string values, so a common committed-log shape remains unredacted. Concrete scenario: `{"cwd":"/Users/example/my.repo"}` passes through `scripts/redact-tmpdir-paths.sh` unchanged, leaking the operator username and repo path despite the new `SECURITY.md` guarantee for end-of-value repo roots. Extend the delimiter handling to capture and preserve quotes/JSON separators, and add regression tests in `scripts/test-redact-tmpdir-paths.sh` for quoted JSON values like `{"cwd":"/Users/example/my.repo"}` and `{"cwd":"/Users/example/my.repo","x":1}`.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality: .claude/skills/bump-version/scripts/apply-bump.sh and scripts/ship-pr.sh (semver_lt duplication in branch diff)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Duplicate semver_lt implementations across scripts. Maintenance burden if comparison rules ever change; not part of the larch-log stale-dir feature. Optional shared helper in a sourced lib (follow-up refactor).
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: larch-logs/implement/**
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Large committed run-log tree in diff. Intentional per repo policy; not scoped as drift. N/A
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] correctness: repo-wide semver helpers
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Generic semver_lt numeric limitations predate broader policy. Not introduced solely by larch-log pathspec change. N/A unless hardening semver is in scope
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: branch vs merge-base..HEAD (diff.txt)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] The merge-base..HEAD range includes many changes outside the four-file implementation plan (version bump, ship-pr, redact helper, SECURITY, committed run logs). Complicates interpreting this branch as a pure implementation of only the pasted plan. Treat as separate workstreams or split PRs if strict plan-surface traceability is required.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] risk-integration: scripts/larch-log.sh:428-429
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Pipeline uses grep under set -e; missing grep fails the commit path Exotic broken PATH environments fail before git logic Pre-exists pathspec change; harden only if PATH-unavailable environments are a supported target
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: scripts/larch-log.sh:430-432
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Commit-pathspec inline comment omits the symlink-resolution rationale from Implementation Plan 1. Only documentation drift; scripts/larch-log.md still explains symlinks. Align the shell comment with scripts/larch-log.md:76-79 or the plan's stated motivation.
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: scripts/ship-pr.sh:2797-2807,.claude/skills/bump-version/scripts/apply-bump.sh:41-51
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate semver_lt implementations added in two scripts. Future semver edge-case fixes might update only one copy. Extract shared helper or add explicit sync comments.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: plan
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] docs/run-logs.md:378-383 Manifest status doc diverges from plan absolutist wording by allowing exceptions. Plan checklist may show false gap if read literally. Reconcile plan text with doc or accept as intentional accuracy improvement.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/larch-log.sh (commit case comment per branch diff)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Comment cites untracked-file omissions rather than stale sibling RUN_ID directories / broad pathspec risk. Maintainers may look for the wrong regression when touching commit pathspec logic. Reword comment to describe run-id scoped pathspec and stale-dir avoidance.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/larch-log.sh:2624-2627
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Commit-pathspec comment blames untracked omissions instead of wrong rel/parent staging. Maintainers may misread future regressions in git status vs pathspec scope. Reword comment to describe wrong pathspec/prefix-strip hazard.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/larch-log.sh:422-426
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Comment blames untracked-file omissions; actual bug was wrong/over-broad rel pathspec Maintainers may mis-diagnose future regressions Reword comment to describe wrong pathspec / sibling run inclusion
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: scripts/test-larch-log.sh:3156-3192
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale-run test duplicates plan-goals heredoc instead of reusing existing payload helper per plan. Two tests can drift if plan-goals validity rules tighten. Reuse shared payload file or tiny generator function.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: docs/run-logs.md (manifest.json section per branch diff)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Shipped manifest status prose contradicts implementation_plan §3 (qualified vs always in-progress). A reviewer treating the plan as normative flags a doc defect even though the new text matches tests that commit status=done. Align plan checklist and shipped doc to a single agreed contract.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: docs/run-logs.md:71-73
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Manifest status doc diverges from Implementation Plan 3: unplanned edit to the lead sentence plus added text that contradicts the plan's always in-progress / PR-merge completion rule. Stakeholders expecting the plan-approved wording get different semantics (exceptions, multi-signal completion, and rewritten intro line). Restore the plan's append-only clarification and exact status semantics, or update the formal plan to match the nuanced doc.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/ship-pr.sh:2809-2865
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] rewrite_reasoning_new_version always appends Rebase + Re-bump Correction on each successful replace Repeated correction could duplicate audit sections Make rewrite idempotent or detect existing correction block
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/ship-pr.sh:2967-2972
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Regression correction case *) keeps _corrected at stale new_version for unknown bump_type. Unexpected BUMP_TYPE with regression detected skips auto-correction until apply-bump fails. Normalize or reject unknown bump_type on the correction path.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/ship-pr.sh:2976-3024
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] If reasoning rewrite and fallback both fail, version-bump-reasoning larch-log write is skipped while apply-bump may succeed. Landed version correct in git but committed run log lacks refreshed reasoning batch. Fail closed on correction without publishable reasoning, or emit minimal stub without awk shape dependency.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/test-larch-log.sh (stale-run isolation test per branch diff)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] New stale-run test uses a bespoke payload instead of reusing $_spayload as the plan specified. Future edits to $_spayload could drift from the duplicated heredoc without failing until someone audits test fidelity. Reuse $_spayload or document structural coupling to $_spayload.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: scripts/test-larch-log.sh:195-224
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Regression test uses a new $_stale_payload heredoc instead of reusing the plan-named payload variable. Minor plan-fidelity and DRY drift; behavior of the test is still coherent. Reuse an in-scope payload path (e.g. $_cpayload) or adjust the plan's variable name to match the file.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: docs/run-logs.md:73
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Committed manifest status prose diverges from the implementation plan's simpler always-in-progress blockquote. Stakeholder signs off against the literal plan text and marks the doc bullet undelivered even though the shipped wording is more accurate. Reconcile the written plan or PR checklist with the nuanced paragraph, or revert to the plan wording only if that invariant is truly intended.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/ship-pr.sh (write_corrected_reasoning_fallback per branch diff)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Fallback reasoning snapshot path may persist after larch-log ingest. Repeated fallback usage could accumulate bump-version-reasoning-corrected-*.md files beside the real reasoning file. Delete fallback artifact after successful larch-log write or confine to IMPLEMENT_TMPDIR with cleanup.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/ship-pr.sh:2843-2865
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Fallback corrected reasoning temp file not deleted after use. Repeated corrections could litter IMPLEMENT_TMPDIR with bump-version-reasoning-corrected-*.md. Unlink after successful larch-log write or use mktemp with cleanup.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/ship-pr.sh:773-781
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] run_bump_phase maps only same-version apply-bump ERROR to exit 5; new version regression ERROR hits exit_stall 8 First bump after CI can stall at Step 8 when NEW_VERSION < origin/main even though run_rebase_rebump auto-corrects the same condition later; asymmetric recovery vs same-version race Extend case arm for version regression ERROR to same Exit 5 / sub-procedure routing or apply semver correction before apply-bump in run_bump_phase
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/test-larch-log.sh:220-226
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] New stale-run regression silences larch-log stdout and skips LOG_WRITTEN assertions used in the adjacent commit test. Subtle regressions produce less actionable harness diagnostics than the neighboring block. Capture commit stdout and assert_contains on LOG_WRITTEN=true like scripts/test-larch-log.sh:177-180.
- **Suggested revision**: Address the concern above.

