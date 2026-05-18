### FINDING_1: **Nit** `code-quality` docs/linting.md:22, docs/linting.md:167 — The docs still contain stale shard references after the 16-shard rebalance: line 22 says CI runs `make test-harnesses-1` through `make test-harnesses-13`, and the target table still has many fixed `via test-harnesses-N` entries that no longer match the Makefile, e.g. `test-check-mid-run-dirty-tree` is documented as shard 3 but now lives in `Makefile:64` shard 15. This can mislead maintainers trying to rerun the failing CI shard. Update the summary to `test-harnesses-16` and either refresh all explicit target-table shard IDs or replace them with shard-agnostic wording like the existing `test-harnesses-N` phrasing.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `code-quality` docs/linting.md:22, docs/linting.md:167 — The docs still contain stale shard references after the 16-shard rebalance: line 22 says CI runs `make test-harnesses-1` through `make test-harnesses-13`, and the target table still has many fixed `via test-harnesses-N` entries that no longer match the Makefile, e.g. `test-check-mid-run-dirty-tree` is documented as shard 3 but now lives in `Makefile:64` shard 15. This can mislead maintainers trying to rerun the failing CI shard. Update the summary to `test-harnesses-16` and either refresh all explicit target-table shard IDs or replace them with shard-agnostic wording like the existing `test-harnesses-N` phrasing.
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: docs/linting.md:187
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] test-upgrade-larch row still pins prerequisite shard 13. test-upgrade-larch moved off the old shard-13 line into test-harnesses-9 in Makefile; the table now falsely states which shard runs that harness under make lint. Update the shard citation to test-harnesses-9 or use generic shard-partition wording.
- **Suggested revision**: Address the concern above.


### FINDING_12: code-quality: docs/linting.md:22
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Usage CI bullet still caps the harness matrix at test-harnesses-13. Same document elsewhere and ci.yaml describe sixteen shards; operators reconciling CI vs docs can follow the wrong matrix span. Update the range to end at test-harnesses-16 or reference the workflow without a stale numeric cap.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: docs/linting.md:167-221+
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Reference-table shard suffixes (via test-harnesses-N) were not updated when Makefile shard membership moved under LPT. Example: docs claim test-design-driver is on shard 1 (line 194) but Makefile assigns it to test-harnesses-15; CI log correlation targets the wrong matrix cell. Refresh explicit per-target shard annotations from Makefile or replace with non-stale wording (Makefile / coverage harness as source of truth).
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: docs/linting.md:22
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Usage bullet still documents CI matrix as test-harnesses-1..13 after 16-shard rebalance. Reader concludes CI runs only 13 harness shards and contradicts updated docs / actual workflow matrix. Update the parenthetical to test-harnesses-1 through test-harnesses-16.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: docs/linting.md:22
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Usage CI bullet still documents harness matrix through shard 13 only. A reader uses the top-of-file CI description and believes CI runs 13 harness shards or that make test-harnesses-13 is the upper bound, conflicting with 16-way matrix and branch protection names test-harnesses (14)-(16). Update the phrase to make test-harnesses-1 through make test-harnesses-16 to match ci.yaml and the CI sharding section.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: docs/linting.md:22
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Usage CI bullet still caps harness matrix at test-harnesses-13. Reader believes CI only runs thirteen harness shards; contradicts ci.yaml and later doc sections. Update prose to test-harnesses-1 through test-harnesses-16 (or equivalent).
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: docs/linting.md:~167-221
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Many harness table rows still say via test-harnesses-N with pre-reshuffle N. Wrong shard when mapping a harness to a matrix job e.g. test-timing-ledger says shard 2 but Makefile assigns shard 7. Resync all via test-harnesses-* references from current Makefile shard lines or remove per-shard claims.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: docs/linting.md (harness table; e.g. lines for test-upgrade-larch test-ship-pr test-timing-report test-timing-ledger test-token-vendor-scrapers test-token-claude-source)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Prerequisite table still lists old test-harnesses-N shard IDs for many harnesses vs the reshuffled Makefile from this branch. Mapping a failing CI shard to the wrong local make test-harnesses-N target misses repro or runs unrelated harnesses. Regenerate via shard lines in Makefile or generalize wording away from brittle per-harness shard numbers.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: docs/linting.md:22
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] CI Usage bullet still caps harness matrix at test-harnesses-13 while ci.yaml runs shards 1-16. Readers believe CI only runs 13 harness shards and contradicts the rest of linting.md after the change. Update the prose to test-harnesses-16 or describe the matrix without a stale numeric cap.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: docs/linting.md:95-117
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] New harness shards need matching required status checks on main If branch protection still requires only test-harnesses (1)-(13), jobs (14)-(16) may be non-blocking so failures in those shards would not prevent merge while maintainers assume full matrix is gating Update GitHub branch protection or org rulesets to require test-harnesses (14), (15), and (16) before relying on this PR as the enforcement baseline; verify with a draft PR that intentionally fails one new shard
- **Suggested revision**: Address the concern above.


