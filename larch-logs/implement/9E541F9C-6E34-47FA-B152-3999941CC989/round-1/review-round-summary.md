# Review Round 1

- Mode: `diff`
- Accepted findings: 10
- Rejected findings: 0
- Exonerated findings: 15
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Important** `risk-integration` `docs/linting.md:104` — The shard-count docs still describe the old CI shape in several operational places: `docs/linting.md:23-131` says the matrix runs through `test-harnesses-16`, uses `range(14)` in the rebalance snippet, lists branch protection checks only through `test-harnesses (14)`, and says the current hard-coded count is `16`; `scripts/test-harness-shards-coverage.md:26-27` still says the guard is currently in shard 12 and the umbrella runs through shard 16. Concrete breakage path: an admin following the branch-protection migration list after this PR would require only shards 1-14, so a later PR with a failing `test-harnesses-15` through `test-harnesses-18` job could still satisfy required checks. Update these docs to the current 18-shard matrix, including checks 15-18 and the current Makefile guard/shard inventory.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `docs/linting.md:104` — The shard-count docs still describe the old CI shape in several operational places: `docs/linting.md:23-131` says the matrix runs through `test-harnesses-16`, uses `range(14)` in the rebalance snippet, lists branch protection checks only through `test-harnesses (14)`, and says the current hard-coded count is `16`; `scripts/test-harness-shards-coverage.md:26-27` still says the guard is currently in shard 12 and the umbrella runs through shard 16. Concrete breakage path: an admin following the branch-protection migration list after this PR would require only shards 1-14, so a later PR with a failing `test-harnesses-15` through `test-harnesses-18` job could still satisfy required checks. Update these docs to the current 18-shard matrix, including checks 15-18 and the current Makefile guard/shard inventory.
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: Makefile:31-32 Makefile:56-57
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Duplicate Shard-13 guard banner mis-anchors above umbrella and above test-harnesses-12 while guard runs first on test-harnesses-13. Editors attach invariant-guard meaning to the wrong shard line during the next Makefile edit. Keep one accurate comment adjacent to test-harnesses-13 or reword to remove shard-12 ambiguity.
- **Suggested revision**: Address the concern above.


### FINDING_12: code-quality: docs/linting.md:126-131
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Lockstep shard-count section still documents 16 shards and a 1..16 matrix literal. Next reshard follows wrong baseline and under-edits Makefile vs ci.yaml. Rewrite count prose to 18 and show shard: [1,...,18] matching .github/workflows/ci.yaml.
- **Suggested revision**: Address the concern above.


### FINDING_13: code-quality: docs/linting.md:23
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] CI usage prose still caps harness matrix at test-harnesses-16 while workflow/Makefile use 18 shards. Contributors or tooling assume only 16 parallel harness shards and mis-map CI failures or omit shards 17-18. Update the range to test-harnesses-18 or describe the matrix without a stale upper bound tied to Makefile discovery.
- **Suggested revision**: Address the concern above.


### FINDING_15: code-quality: docs/linting.md:82-97
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] LPT example uses range(14) bins after nearby prose documents eighteen CI shards. Copy-paste rebalance produces 14-way packing while CI runs 18 shards. Change range(14) to range(18) or otherwise match documented shard count.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: docs/linting.md:104-119
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Branch protection migration list stops at test-harnesses (14). Required status checks omit new jobs (15)-(18) so failing or skipped new shards may not block merges while the team assumes full matrix gating. Add bullets for test-harnesses (15) through (18) and remind admins to verify rulesets if used.
- **Suggested revision**: Address the concern above.


### FINDING_28: risk-integration: docs/linting.md:259
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Harness table pins test-quick-mode-docs-sync to test-harnesses-15 but Makefile places it on test-harnesses-5; branch adds real CI shard 15 for test-dispatch-code-voters-retry-claude. A maintainer maps a failing or skipped quick-mode harness to CI shard 15 and inspects the wrong job logs or assumes coverage relationship between unrelated harnesses. Regenerate shard column from Makefile or use generic test-harnesses-N wording like adjacent rows.
- **Suggested revision**: Address the concern above.


### FINDING_31: risk-integration: scripts/test-dispatch-code-voters.sh:16-25,358
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Non-empty SECTION that matches no section_runs branch skips all tests yet exits 0 with PASS. A future typo or drift in Makefile --section argument yields a silent no-op pass. Validate SECTION against an allowlist when set; exit non-zero on unknown section.
- **Suggested revision**: Address the concern above.


### FINDING_8: architecture: docs/linting.md:43
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Local parallelism example uses make -j16 with 18 shard targets. Minor mismatch for readers seeking max safe local parallelism. Use -j18 or describe parallelism relative to shard count.
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: Makefile:109-114
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Historical rebalance comment still ends at 14 shards despite 18 test-harnesses-N rules. Maintainers misread evolution of shard count when debugging CI time. Extend or refresh the comment to mention shards 15-18 or current total.
- **Suggested revision**: Address the concern above.


