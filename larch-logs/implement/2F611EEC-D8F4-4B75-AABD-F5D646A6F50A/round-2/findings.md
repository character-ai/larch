### FINDING_1: **Nit** `code-quality` `scripts/test-harness-shards-coverage.md:27` still documents the current umbrella range as `test-harnesses-1` through `test-harnesses-13`, but this branch changes the Makefile and CI matrix to 16 shards. This sibling contract explicitly says shard layout changes must update it alongside `docs/linting.md`, so update the line to `test-harnesses-1` through `test-harnesses-16`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `code-quality` `scripts/test-harness-shards-coverage.md:27` still documents the current umbrella range as `test-harnesses-1` through `test-harnesses-13`, but this branch changes the Makefile and CI matrix to 16 shards. This sibling contract explicitly says shard layout changes must update it alongside `docs/linting.md`, so update the line to `test-harnesses-1` through `test-harnesses-16`. I found no out-of-scope observations. I could not run `make test-harness-shards-coverage` directly because the read-only sandbox blocked `mktemp`, but a read-only equivalent of the guard found no missing, duplicate, orphan, or `.PHONY` issues in the Makefile shard partition.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: CHANGELOG.md (historical entries)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Older changelog bullets still describe 13-shard era. None for this PR; historical record. No change required for rebalance correctness.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: scripts/test-harness-shards-coverage.md:27
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Companion markdown still caps shards at 13; unchanged by this diff. Contributors following only that doc get stale shard-count guidance next to the coverage script. Update the prose in a follow-up commit touching that doc.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] correctness: docs/linting.md LPT Python snippet
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] LPT loop uses bins.index on a mutated tuple/list pair; fragile if copied. Mis-binning if someone pastes the snippet without understanding Python reference semantics. Out of scope unless rewriting the example; only range(16) changed here.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: scripts/test-harness-shards-coverage.md:27
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Umbrella range text still ends at test-harnesses-13 after Makefile moves to 16 shards; conflicts with Edit-In-Sync in same doc. A maintainer uses the sibling contract as the shard ceiling and misconfigures branch protection or local parallel runs expecting 13 matrix legs. Update line 27 to reference test-harnesses-16 (and re-scan the file for any other stale shard counts).
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: docs/linting.md (Makefile targets table; multiple rows in the rebalance diff)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Concrete via test-harnesses-N shard hints replaced by generic partition wording. Harder to jump from a failing harness name to the correct matrix cell without Makefile grep. Optionally restore selective shard numbers or add a short pointer to Makefile grep / test-harness-shards-coverage for lookup.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: Makefile:32 and Makefile:57
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Duplicate Shard-12 guard comment; the copy above umbrella test-harnesses mis-anchors the note. Readers think the umbrella line is special-cased as shard 12 . Remove or relocate the line-32 duplicate so the Shard-12 comment only precedes test-harnesses-12 .
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: Makefile:32-33 Makefile:57-58
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate Shard-12 partition-guard banner; first copy sits above umbrella aggregate not the guarded shard line. Readers see the same comment twice and the top copy no longer annotates the rule directly beneath it, which dilutes the sentinel-shard signal during edits. Remove the redundant banner above test-harnesses: or keep a single comment only adjacent to test-harnesses-12.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: docs/linting.md:167-252
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Broad replacement of explicit per-shard doc hints with generic test-harnesses-N wording exceeds the plan’s enumerated doc edits. Operators lose one-hop mapping from a failing harness name to the CI matrix shard without Makefile ripgrep, slowing reruns and ownership triage. Restore explicit test-harnesses-<k> suffixes in the table or add a single authoritative pointer to Makefile plus coverage guard.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: docs/linting.md:252
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] test-quick-mode-docs-sync row uses legacy prerequisite phrasing while sibling rows use the new shard-partition clause. Doc table looks half-migrated and no longer matches the Makefile shard (test-harnesses-15) for that harness. Match the surrounding clause style and optionally name the concrete shard index.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: docs/linting.md:253
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] test-harness-shards-coverage row genericizes placement of the partition guard. Text no longer reflects the Makefile’s deliberate first-slot placement on test-harnesses-12, hiding the sentinel-shard contract the Makefile comment documents. Name test-harnesses-12 (or state first prerequisite of that shard) on this row only.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: docs/linting.md:94-130
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Shard expansion adds three new matrix-derived status check names that must be required on main. If branch protection is not updated before merge, merges can succeed while test-harnesses (14)/(15)/(16) are non-required or failing, weakening CI gating on those shards. Update GitHub branch protection required checks to include test-harnesses (14), (15), and (16) before merging (per Branch protection migration in the same doc).
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-harness-shards-coverage.md:27
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Umbrella doc still ends at test-harnesses-13 and conflicts with Makefile 16-shard layout; violates this file s Edit-In-Sync rule with docs/linting.md. Maintainer or automation derived from the sibling contract omits shards 14-16 from branch protection or mis-states CI coverage. Update line 27 to test-harnesses-16 and sweep the file for stale shard-count literals; keep in sync on every shard-count edit per Edit-In-Sync.
- **Suggested revision**: Address the concern above.

