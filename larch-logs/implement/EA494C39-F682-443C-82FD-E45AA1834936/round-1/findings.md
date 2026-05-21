### FINDING_1: correctness: .claude-plugin/plugin.json:4
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Marketplace description still claims different code-review panel sizes for SIMPLE vs HARD paths. Consumers and strict-permissions readers infer cheaper 7-reviewer /implement code review for SIMPLE workflow, but Step 5 now always launches review-and-fix with --panel hard for SIMPLE and HARD POST_PLAN_WORKFLOW_PATH. Rewrite description so SIMPLE/HARD only describe post-plan/design depth and explicitly state Step 5 is always unified --panel hard with the documented round cap and dynamic archetypes.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/compose-review-findings.sh:59-200;scripts/test-compose-review-findings.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Large JSONL category-extraction and regression-test changes bundled into the same branch as /implement review unification. Unrelated regressions in compose-review-findings could block or complicate landing the review-flow change; reviewers must reason about two feature stories at once. Split compose-review-findings changes into their own PR/commit with dedicated changelog and review narrative.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/persist-implement-run-flags.sh:1-65;skills/implement/scripts/write-final-report.sh:101
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] QUICK_MODE is still written and read but appears unused in final summary rendering after quick mode removal. Maintainers think quick mode remains a first-class persisted flag; dead IO adds noise and risks future accidental reintroduction. Remove QUICK_MODE from run-flags contract and write-final-report reader once tmpdir backward compatibility is no longer needed, or wire it into display explicitly with a deprecation comment.
- **Suggested revision**: Address the concern above.

### FINDING_4: risk-integration: CHANGELOG.md:8-14
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New changelog section is boilerplate-only and changelog head lags plugin.json 29.8.64. Humans comparing installed version to changelog see mismatched semver and no prose for a major behavior change. Add user-facing bullets for the unified Step 5 contract and add the missing 29.8.64 section or align bump sequencing.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/test-quick-mode-docs-sync.sh:1-50
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Historical harness name says quick-mode while enforcing unified Step 5 contract. Future contributors may search for quick-mode tooling and miss this harness or mis-edit it thinking it is obsolete. Rename harness and references or add an explicit historical-name banner tied to Makefile wiring.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/check-changelog-present.md:3
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Doc example still references removed /imaq alias. Minor confusion only when reading that contract doc; not part of this branch diff. Reword example to a shipped skill path on next edit.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/review-and-fix/scripts/review-and-fix.md:45-52
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Flags table documents orchestrator default dynamic-archetypes=4 but the narrative paragraph and review-and-fix.sh use 6 for implement-tmpdir mode. An operator or LLM reads only the short flags list and configures or explains runs expecting a default cap of 4 while the shell path actually defaults to 6, causing mismatched cost/latency expectations and contradictory internal docs. Update line 45 to 6 and align any other table bullets with scripts/review-and-fix.sh.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: scripts/compose-review-findings.sh:63-179 and scripts/compose-review-findings.md
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plan-review accepted category extraction is now strict-canonical; JSONL category can be empty or shift vs older first-heading heuristics. Downstream analytics or issue miners that bucket accepted plan-review JSONL by the first ## heading string can miscount or mis-route rows when prose titles precede canonical ## focus-area lines or when no canonical tag exists. Announce contract change, audit external consumers, and keep docs/tests explicit about empty-category acceptance.
- **Suggested revision**: Address the concern above.

### FINDING_9: architecture: scripts/compose-review-findings.sh; scripts/test-compose-review-findings.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Material compose helper + harness changes are not listed in the implementation plan for the unify-review-flow work. Reviewers relying only on the plan miss a behavior-changing miner/JSONL surface that ships in the same branch. Split to its own PR or fold into the plan/CHANGELOG with explicit rationale.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/persist-implement-run-flags.sh:1-12
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Header still frames QUICK_MODE as the headline sanctioned field though /implement quick mode is removed and QUICK_MODE defaults false. Maintainers may think quick mode remains a first-class persisted knob. Reword comments to describe legacy QUICK_MODE=false persistence only.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/test-quick-mode-docs-sync.sh:68-72
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Edit-in-sync comment still names Step 5 quick-mode contract. Future edits may reintroduce stale quick-mode wording near the harness. Update comment to reference the unified hard-panel Step 5 contract.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] architecture: git history on branch
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Branch stacks larch-log flush, version bump, and unrelated docs commits with the unify change. Review burden and bisect noise; not a functional bug in the feature diff itself. Narrow PR scope or document commit intent in the PR body.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: .claude-plugin/plugin.json:10
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plugin JSON description still describes SIMPLE-vs-HARD review topology and design quick mode though runtime unified Step 5 to hard panel and removed /implement --quick. Consumers read inaccurate capability text in marketplace or plugin metadata. Rewrite description to match unified hard panel 5 rounds and current design sketch language in same PR.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/compose-review-findings.sh;scripts/test-compose-review-findings.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-review accepted JSONL category semantics changed and heavily re-tested but change is orthogonal to unify-review-flow scope. Downstream JSONL consumers or reviewers bisecting regressions get unrelated behavior change in same merge. Split PR or add explicit compatibility / changelog note for category field semantics.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-implement-structure.sh:6683-6686
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Removed quick-mode structural grep without a narrower replacement pin on unified Step 5 prose. Mis-edits to implement SKILL Step 5 / adjacent sections could slip if docs-sync harnesses are skipped locally. Add a minimal replacement substring assertion for unified Step 5 contract.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] architecture: larch-logs/implement/* (commit 2b485ff2)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Large run-log flush noise in branch diff. Obscures functional commit in review; not a CI failure mode. None for this review scope.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] architecture: docs/issue-anchored-plan.md (commit cf64c286)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc addition unrelated to review-flow unify. No testing gap vs provided unify plan. None for this review scope.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/fix-issue/scripts/test-fix-issue-bail-detection.sh:108-133
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Removed CI assertion (old a6) that Step 5a must not forward --quick. A future edit could reintroduce --quick into the Step 5a Skill args without failing CI, resurrecting a removed /implement flag path for /fix-issue-driven runs. Add assert_not_contains or equivalent negative check on the Step 5a block for forbidden tokens like --quick.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/test-implement-structure.sh:57-61
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Removed grep asserting quick-mode skip wording before Larch-log batches. SKILL.md could reorder or dilute Step 1 vs batches guidance without failing this harness, increasing orchestrator confusion risk (doc-only, not exploit). Add a replacement invariant anchored to the current unified-flow wording.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/compose-review-findings.sh:177-179
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Plan-review accepted rows use strict category scanning; category may be empty while schema_version remains 2. Downstream JSONL consumers expecting non-empty category for accepted plan findings could mis-aggregate or error. Document behavior and migration expectations or bump schema_version add explicit field for category strictness.
- **Suggested revision**: Address the concern above.

### FINDING_21: code-quality: scripts/persist-implement-run-flags.sh:1-11
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Header still frames QUICK_MODE as primary sanctioned writer concern after quick mode removal. Maintainers may think QUICK_MODE is still user-controlled for /implement. Reword header to mark QUICK_MODE as legacy and point to write-final-report consumption only.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] security: larch-logs/implement/*/session-transcript.jsonl
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Committed transcripts expand repo secret blast radius if scrubbing regresses. Any redaction bug would affect many historical logs too, not unique to this diff’s logic. Keep existing redaction pipeline tests; treat as operational hygiene outside this PR’s script edits.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: .claude-plugin/plugin.json:10
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Marketplace description still describes distinct SIMPLE vs HARD code-review panel sizes after Step 5 was unified to --panel hard for both workflow paths. Operators and consumers read the plugin card and believe SIMPLE runs a smaller specialist panel than HARD; contradicts run-step5-review.sh and updated SKILL/docs. Rewrite plugin.json description to match unified hard-panel Step 5 and current sketch/plan-review facts.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: scripts/run-step5-review.sh:6428-6437
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] HARD workflow base round cap reduced from 7 to 5 alongside SIMPLE. HARD-tagged runs silently lose up to two review rounds vs previous behavior; may exit the loop earlier under marginal quality. Document the intentional cap change in user-facing release notes and/or emit an explicit operator-visible breadcrumb for HARD sessions.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: skills/fix-issue/scripts/test-fix-issue-bail-detection.sh:7606-7688
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Removed CI assertion that Step 5a must not unconditionally forward --quick. A future mistaken edit could reintroduce --quick on the /implement invocation without failing this harness until runtime or a different check trips. Reintroduce a narrow negative grep on the Step 5a invocation line forbidding a bare --quick token.
- **Suggested revision**: Address the concern above.

### FINDING_26: architecture: scripts/compose-review-findings.sh:6228-6233
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Plan-review accepted findings now use strict canonical ## scanning for category; category may be empty. Downstream JSONL consumers that assumed non-empty category for plan-review accepted rows may mis-bucket or drop records. Document the contract change; adjust any consumer to tolerate empty category and use prose_body/id keys.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] code-quality: scripts/test-quick-mode-docs-sync.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness filename and comments still say quick-mode while enforcing unified Step 5 anchors. Maintainer confusion only; no runtime impact. Rename or add a one-line clarifying comment in a follow-up if desired.
- **Suggested revision**: Address the concern above.

### FINDING_28: architecture: scripts/test-compose-review-findings.sh:6533-6638
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Compose-review JSONL harness gains new plan-review category rules and fixtures not listed in the unify-review-flow implementation plan. Plan-to-diff traceability breaks: reviewers cannot tell whether extra harness behavior was intended for this feature or is unrelated drift; rollback/revert of the main story becomes harder. Split unrelated harness work to its own PR or extend the written plan/PR summary to explicitly own these changes.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: skills/implement/SKILL.md:8148-8157
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] plan-review-tally write-tally invocation still documents --mode <simple|hard> while text says only hard for inline paths after quick removal. A literal-reading orchestrator might still emit --mode simple for a batch where the contract is unified hard semantics. Replace <simple|hard> with hard-only wording or explicitly forbid simple for this batch under /implement.
- **Suggested revision**: Address the concern above.

### FINDING_30: code-quality: scripts/persist-implement-run-flags.sh:6291-6293
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Header comment still centers QUICK_MODE as a primary sanctioned field after /implement quick removal. Maintainers may assume quick mode remains a first-class persisted knob. Reword header to reflect legacy QUICK_MODE=false default and primary consumers (NO_ISSUES/WORKFLOW_PATH).
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] architecture: docs/issue-anchored-plan.md / version bump commits on branch
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Diff includes doc/version commits outside the unify-review-flow plan scope. Noise when checking plan completeness only. Treat as orthogonal when reviewing this plan; no change required for plan fidelity of the review-flow item list.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] architecture: larch-logs/implement/**
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Committed run-log flush per repo policy. Not a plan omission for the unify work. Ignore for plan-fidelity except where log content is explicitly part of acceptance.
- **Suggested revision**: Address the concern above.

