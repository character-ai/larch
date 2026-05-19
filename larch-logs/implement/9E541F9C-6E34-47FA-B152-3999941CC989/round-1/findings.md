### FINDING_1: **Important** `risk-integration` `docs/linting.md:104` — The shard-count docs still describe the old CI shape in several operational places: `docs/linting.md:23-131` says the matrix runs through `test-harnesses-16`, uses `range(14)` in the rebalance snippet, lists branch protection checks only through `test-harnesses (14)`, and says the current hard-coded count is `16`; `scripts/test-harness-shards-coverage.md:26-27` still says the guard is currently in shard 12 and the umbrella runs through shard 16. Concrete breakage path: an admin following the branch-protection migration list after this PR would require only shards 1-14, so a later PR with a failing `test-harnesses-15` through `test-harnesses-18` job could still satisfy required checks. Update these docs to the current 18-shard matrix, including checks 15-18 and the current Makefile guard/shard inventory.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `docs/linting.md:104` — The shard-count docs still describe the old CI shape in several operational places: `docs/linting.md:23-131` says the matrix runs through `test-harnesses-16`, uses `range(14)` in the rebalance snippet, lists branch protection checks only through `test-harnesses (14)`, and says the current hard-coded count is `16`; `scripts/test-harness-shards-coverage.md:26-27` still says the guard is currently in shard 12 and the umbrella runs through shard 16. Concrete breakage path: an admin following the branch-protection migration list after this PR would require only shards 1-14, so a later PR with a failing `test-harnesses-15` through `test-harnesses-18` job could still satisfy required checks. Update these docs to the current 18-shard matrix, including checks 15-18 and the current Makefile guard/shard inventory.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality: scripts/test-harness-shards-coverage.md:26-27
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Sibling doc names wrong guard shard (12 vs Makefile 13) and umbrella 1..16 vs 18 shards. File not modified by this branch diff; plan did not list it. Update when next touching Makefile shard docs for Edit-In-Sync.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: scripts/test-harness-shards-coverage.md:26-27
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Sibling contract cites guard shard 12 and umbrella 1..16 vs Makefile guard on 13 and umbrella 1..18. Not in branch diff; misleads maintainers who read only the sibling doc. Refresh when touching shard layout per Edit-In-Sync with docs/linting.md.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/test-harness-shards-coverage.md:27
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Sibling doc still documents umbrella through test-harnesses-16 only. File not modified by this branch diff; stale vs 18-way Makefile/CI. Update ceiling when editing is allowed to stay in sync with Makefile.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] correctness: scripts/test-dispatch-code-voters.sh:362-367
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unknown or mistyped --section skips all gated tests yet the harness still prints PASS. Typos yield a false green same as the pre-two-section design not introduced by the new section gates alone. Add validation that SECTION is empty or matches a known section or assert at least one section ran.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] correctness: scripts/test-harness-shards-coverage.md:26
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc claims guard-owning shard is test-harnesses-12 but Makefile puts the guard first on test-harnesses-13. Misidentifies guard shard when reading only the md file not introduced by this branch diff. Update line 26 to test-harnesses-13 when editing that file.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: Makefile:57
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Shard 12 grows with rebase-push-force-lease and ballot-parse moved from shard 9. Not proven by diff; possible wall-time regression vs 40s goal. Re-profile shard 12 after CI and rebalance if it exceeds budget.
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: docs/linting.md:43
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Local parallelism example uses make -j16 with 18 shard targets. Minor mismatch for readers seeking max safe local parallelism. Use -j18 or describe parallelism relative to shard count.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: Makefile:109-114
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Historical rebalance comment still ends at 14 shards despite 18 test-harnesses-N rules. Maintainers misread evolution of shard count when debugging CI time. Extend or refresh the comment to mention shards 15-18 or current total.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: Makefile:19-24
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Historical shard-count comment ends at fourteen-shard narrative without noting eighteen-shard end state. Future editors misread why shard lines expanded and may revert or duplicate work. Append a short clause documenting the 18-shard voter split follow-on.
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

### FINDING_14: code-quality: docs/linting.md:43
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Local parallelism example uses make -j16 with 18 shard targets defined. Minor confusion when maxing local parallelism vs shard count. Use -j18 or document -jN for current shard count.
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: docs/linting.md:82-97
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] LPT example uses range(14) bins after nearby prose documents eighteen CI shards. Copy-paste rebalance produces 14-way packing while CI runs 18 shards. Change range(14) to range(18) or otherwise match documented shard count.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: docs/linting.md:126-131
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Changing the shard count section still documents sixteen shards and a ci.yaml matrix capped at 16. A maintainer follows this lockstep section and omits CI updates or believes only sixteen jobs exist causing Makefile or workflow drift. Update prose and embedded shard list to eighteen to match Makefile and ci.yaml.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: docs/linting.md:126-131
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Changing the shard count section still documents 16 shards and a matrix ending at 16. Lockstep edit instructions contradict Makefile and workflow after rebalance to 18. Update count adjective Makefile bullet and example matrix line to 18.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: docs/linting.md:23
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Usage CI bullet caps the matrix at test-harnesses-16. Readers see conflicting ceilings in the same doc versus the eighteen-shard CI sharding section and mis-map failures or automation. Update the range to test-harnesses-18 or avoid a hardcoded last index.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: docs/linting.md:23
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Usage CI bullet still ends harness range at test-harnesses-16 while CI and later linting.md prose use 18 shards. Maintainers read inconsistent shard cardinality and under-document the live matrix. Update the bullet to test-harnesses-18 and align wording with .github/workflows/ci.yaml.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: docs/linting.md:23
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] CI prose still caps the harness matrix at test-harnesses-16 while workflow/Makefile use 18 shards. Readers underestimate parallel matrix width or copy stale upper bound into automation. Update to test-harnesses-18 or avoid hard-coded last index.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: docs/linting.md:43
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Doc still suggests make -j16 for test-harnesses while 18 shard targets exist. Local parallel make leaves two shard targets waiting unnecessarily. Use -j18 or describe concurrency without a stale literal.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: docs/linting.md:90
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Bin-packing snippet uses range(14). Operators copy stale snippet and pack against 14 bins instead of 18. Use range(18) or derive bin count from discovered shard list.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: docs/linting.md:104-119
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Branch protection migration list stops at test-harnesses (14). Required status checks omit new jobs (15)-(18) so failing or skipped new shards may not block merges while the team assumes full matrix gating. Add bullets for test-harnesses (15) through (18) and remind admins to verify rulesets if used.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: docs/linting.md:104-120
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Branch protection checklist stops at test-harnesses (14); missing (15)-(18). Admin configures required checks from this list and leaves new matrix legs non-required so failures on shards 15-18 do not block merge. Add bullet lines for test-harnesses (15) through (18) before lint-mermaid.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: docs/linting.md:106-119
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Branch protection checklist stops at test-harnesses (14). Four new matrix jobs (15)-(18) are omitted from the admin checklist so branch protection can miss required checks for new shards. Append test-harnesses (15) through (18) before lint-mermaid.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: docs/linting.md:126-131
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Lockstep shard-count section still documents sixteen shards and a 1..16 ci.yaml example. Readers follow the doc’s own lockstep checklist and believe only two edit sites and sixteen matrix cells apply, missing the real third site and 18 cells. Refresh the count bullets and example matrix array to 18 or point solely at the checked-in Makefile and workflow.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: docs/linting.md:23
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Usage CI bullet still caps harness matrix at test-harnesses-16 while Makefile and ci.yaml implement 18 shards. Maintainers assume only 16 parallel harness legs exist and misalign monitoring, branch protection expectations, or capacity planning vs the real 18-way matrix. Update the prose to test-harnesses-18 or describe the matrix without a stale numeric ceiling.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: docs/linting.md:259
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Harness table pins test-quick-mode-docs-sync to test-harnesses-15 but Makefile places it on test-harnesses-5; branch adds real CI shard 15 for test-dispatch-code-voters-retry-claude. A maintainer maps a failing or skipped quick-mode harness to CI shard 15 and inspects the wrong job logs or assumes coverage relationship between unrelated harnesses. Regenerate shard column from Makefile or use generic test-harnesses-N wording like adjacent rows.
- **Suggested revision**: Address the concern above.

### FINDING_29: risk-integration: docs/linting.md:259
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Makefile targets table pins test-quick-mode-docs-sync to test-harnesses-15. Makefile schedules that harness on test-harnesses-5 and dedicates shard 15 to voter retry-claude; triage re-runs the wrong Actions cell. Correct the shard suffix to test-harnesses-5 or replace with generic test-harnesses-N wording.
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: docs/linting.md:43 docs/linting.md:82-94
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Local parallelism and LPT snippet still use -j16 and range(14). Authors rebalance using 14 bins or 16-way local parallelism while CI runs 18 shards, skewing bin-packing guidance. Update to -j18 and range(18) or compute bin count from Makefile-derived shard list.
- **Suggested revision**: Address the concern above.

### FINDING_31: risk-integration: scripts/test-dispatch-code-voters.sh:16-25,358
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Non-empty SECTION that matches no section_runs branch skips all tests yet exits 0 with PASS. A future typo or drift in Makefile --section argument yields a silent no-op pass. Validate SECTION against an allowlist when set; exit non-zero on unknown section.
- **Suggested revision**: Address the concern above.

