### FINDING_1: [OUT_OF_SCOPE] code-quality: Makefile:5,519
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate .PHONY declaration for test-check-reviewer-failure-threshold Redundant but harmless; not part of this branch’s functional change Consolidate .PHONY lines when next touching Makefile organization
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] risk-integration: skills/review-and-fix/scripts/review-and-fix.md:122
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness prose still points only at make test-review-and-fix and omits the new section make targets. Readers of the skill contract may not discover how CI exercises the split harness. Not introduced by this diff extend the harness sentence when that file is next edited.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: Makefile:109-122
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Shard-count history comment is dense and non-monotonic (e.g. 16 then 14 then 18 then 20). Editors resharding or bisecting CI may misread which historical layout a sentence refers to and apply the wrong baseline. Shorten to current count plus pointer to docs/linting.md, or rewrite as a strict chronological timeline with issue references.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:233-1224
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Dispatch section body is not indented under if section_runs dispatch Maintainers must rely on fi markers alone to see section extent; edits are easier to mis-place near the dispatch/convergence seam Indent dispatch-only lines or wrap in a named function for consistent structure
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:10-20
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] New --section argv loop treats unknown tokens as ignorable via default shift. Typo or stray argv leaves SECTION empty so dispatch+convergence both run and can pass, hiding a miswired Makefile or manual command. Fail on unknown arguments or stop parsing at first non-option token so mis-invocations exit non-zero.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: Makefile:test-harnesses-3 (diff adds test-review-and-fix-convergence)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Shard 3 timing after hosting the full convergence harness is asserted in prose only no committed timing proof in the diff. If convergence dominates wall time shard 3 can exceed the intended per shard budget undermining the 18 to 20 rebalance goal. Re measure LARCH_HARNESS_TIMING for shard 3 after CI or local timing capture and reshuffle if needed.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: Makefile:test-harnesses-3 (~136)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Shard 3 grew by appending test-review-and-fix-convergence on an already long prerequisite list CI shard 3 could exceed the ≤40s rebalance target if timings slip; failures would be slow-CI noise not partition drift Re-measure LARCH_HARNESS_TIMING for shard 3 after CI and repack if needed
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: docs/linting.md branch protection list plus .github/workflows/ci.yaml matrix
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New shards 19 and 20 need required status checks aligned with branch protection or rulesets. If protection lists stop at 18 merges can stay green while new shard jobs fail or are non required. Update required checks for test-harnesses (19) and (20) per docs before relying on merge gates.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: docs/linting.md:104-126
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] CI matrix widened to 20 shards while required GitHub checks may still list only 1–18. Failing or skipped test-harnesses (19)/(20) may not block merge if branch protection/rulesets are not updated, giving a false sense of full harness gating. Add test-harnesses (19) and (20) to required checks (and rulesets); verify enforcement before relying on it.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-dispatch-code-voters.sh (plan verification)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan requires grep -Fq assertion count parity across the regression gate move but no automated guard encodes it in repo. A later refactor could drop grep assertions without CI catching the regression. Add a small structural check or extend an existing harness to assert stable assertion counts or section invariants.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:15-22
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] New --section argv loop uses *) shift ;; so unknown CLI tokens are dropped silently. A typoed flag or stray word changes effective behavior while the script can still exit 0 after the chosen section printing ok misleading green signal for CI or local runs. Reject unknown arguments with a clear error or document a strict argv terminator and enforce it.
- **Suggested revision**: Address the concern above.

