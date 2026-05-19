### FINDING_1: [OUT_OF_SCOPE] code-quality: Makefile:19-25
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Dense historical rebalance comment. Reader confusion only; no runtime effect. Optional prose clarification later.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality: Makefile:19-25
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Historical rebalance comment is dense (16 then 14 then 18). Reader confusion only; no runtime impact. Optional prose clarification in a follow-up edit.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: docs/linting.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Residual per-row shard index drift possible in untouched table rows. Triage might target the wrong Actions shard from an outdated row. Broader table refresh or generic wording; not specific to this diff.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: docs/linting.md (Makefile targets table, unchanged rows)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Possible residual per-row shard index drift predates this diff’s limited table edits. Mis-routing triage to the wrong Actions matrix cell when a row names a stale shard. Broader table refresh or genericize rows; not required to validate this PR’s shard split itself.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/test-dispatch-code-voters.sh:155-167
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Happy-path assertions use bare grep pipelines without unified FAIL messages. Harder local diagnosis when a happy assertion regresses; behavior unchanged by this branch’s gating work. Optional follow-up: align assertion style with later sections (pre-existing surface).
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/test-dispatch-code-voters.sh:17-21
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Unknown CLI tokens are silently consumed via default case shift. Typos like --sectoin do not fail fast; pre-existing before this branch’s section gates. Out of scope for this rebalance; consider strict arg parsing in a dedicated follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] correctness: scripts/test-dispatch-code-voters.sh:17-21
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Trailing --section can trip set -u on missing $2. Running bash scripts/test-dispatch-code-voters.sh --section with no value errors. Pre-existing argv loop; tighten with guard if desired later.
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: scripts/test-dispatch-code-voters.sh:23-30 + Makefile:216-226 + scripts/test-dispatch-code-voters.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Section names are triplicated across harness, Makefile, and doc. A typo in one site can desync CI invocation from the harness allowlist or confuse operators. Optional: centralize names or add a structural grep guard in an existing coverage script.
- **Suggested revision**: Address the concern above.

### FINDING_9: architecture: scripts/test-dispatch-code-voters.sh:23-31
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Unknown --section validation added; not enumerated in implementation plan File 1. Typo or experimental section value now exits 1 instead of running ambiguously; no impact on Makefile/CI wiring. Optional: document in plan or scripts/test-dispatch-code-voters.md; no code change required.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: Makefile:19-25
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Shard-count history comment is chronologically confusing (16 then 14 then 18). A maintainer misreads which shard era an old failure log belongs to when bisecting CI layout changes. Rewrite as a linear timeline or shorten to “see docs/linting.md”.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: Makefile:19-25
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Historical shard-count narrative stacks 16 then 14 then 18 without era labels. Readers may misread the timeline as contradictory and mis-edit shard history comments during the next rebalance. Clarify chronology (issue IDs/dates) or shorten to the current fact plus a pointer to docs/linting.md.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: Makefile:19-25
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Shard rebalance history comment mixes non-monotonic shard counts (16 then 14 then 18). Editors resharding may misread which era a sentence refers to and apply the wrong mental model when editing shard lines. Rewrite the comment as a clear time-ordered summary or drop superseded intermediate numbers.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: scripts/test-dispatch-code-voters.sh:7-31 and scripts/test-dispatch-code-voters.sh:23-31
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Section names are documented in the header and duplicated again in the validation case list. A future rename can update comments but forget the case arm (or vice versa), reintroducing unknown-section false passes or confusing errors. Single-source section identifiers (one list driving both docs text and validation).
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: .github/workflows/ci.yaml (test-harnesses matrix) + docs/linting.md:102-126
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Four additional matrix shards require matching required status checks. If branch protection/rulesets omit (15)-(18), failing jobs may not block merge though the matrix looks complete. Follow branch protection migration (and rulesets) before relying on enforcement; verify with a deliberate failing shard if needed.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: .github/workflows/ci.yaml docs/linting.md:102-124
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Four new matrix jobs (shards 15–18) need matching required GitHub checks like any shard expansion. Branch protection still requiring only (1)–(14) allows merges when shard 15–18 jobs fail or are skipped as non-required. Add required checks for test-harnesses (15)–(18) (and rulesets if used) before merge.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: Makefile:4 Makefile:519
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] New dispatch-code-voters retry targets are .PHONY on the secondary block but omitted from the mega .PHONY line the plan referenced. Ad-hoc tooling that only parses the first .PHONY line could treat the new targets differently from other harness recipes. Append test-dispatch-code-voters-retry-* to the line-4 mega .PHONY list.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: Makefile:56
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Shard 12 gained test-rebase-push-force-lease and test-ballot-parse while already hosting many harnesses; timing goal may regress. CI shard 12 could exceed the intended ~40s ceiling even though functional tests pass, weakening the rebalance objective. Re-check LARCH_HARNESS_TIMING after CI; adjust shard assignment or split further if shard 12 spikes.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: Makefile:56
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Shard 12 grows with rebase-push-force-lease and ballot-parse moved from shard 9. Shard 12 may exceed the intended ~40s CI ceiling while staying green. Re-check LARCH_HARNESS_TIMING; rebalance if shard 12 regresses.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: Makefile:test-harnesses-12 line (~52)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Shard 12 gained test-rebase-push-force-lease and test-ballot-parse on an already heavy shard row. CI shard wall time could exceed the ≤40s target while remaining structurally valid; slow merges erode the rebalance goal. Re-check LARCH_HARNESS_TIMING for test-harnesses-12 after CI runs; repack if the shard becomes a new straggler.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: docs/linting.md (branch protection migration / rulesets note)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] CI matrix grows to 18 shards; merge gating may omit new jobs If required checks are not extended to test-harnesses (15)-(18), merges can pass without those four harnesses running as gate Admin: add the four new check names to branch protection and any rulesets before relying on merge gates
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: docs/linting.md:102-126 / .github/workflows/ci.yaml:26-65
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Four new matrix checks (15)-(18). Non-required new checks let failing shards slip through merges. Add required status checks (15)-(18); verify rulesets if applicable.
- **Suggested revision**: Address the concern above.

