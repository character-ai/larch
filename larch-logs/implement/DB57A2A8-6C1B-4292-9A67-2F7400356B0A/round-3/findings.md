### FINDING_1: code-quality: scripts/test-launch-review.sh:86-90,1075-1083
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Duplicate assert_regex definitions in two subshells Maintenance drift if one copy is fixed and the other is not Extract shared helper or accept duplication with a one-line comment rationale
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/test-launch-review.sh:86-90,1075-1084
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] assert_regex duplicated verbatim in two subshells Future signature or message tweaks need two edits Accept as harness pattern or dedupe if the file gains a shared prelude
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-launch-review.sh:906-907,948-949,993-995,2213-2214
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Entry counts use grep -c over the tool name substring on the full execution-issues log If captured output ever contains codex-review or cursor-review outside the header line counts can exceed 1 or stay >0 on success paths and fail assertions despite correct launcher behavior Count only header lines e.g. anchor on ^-\\s\\*\\*Step review Step 2 — codex-review
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/test-launch-review.sh:952-996
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Literal implementation_plan assert (c) said failure line must not contain transient-retries= but tests require transient-retries=1 Plan-diff or reviewers following the old bullet literally report a mismatch even though behavior matches the stated observability goal Update the authoritative plan or issue text to match the shipped assertion and M=1 semantics
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: scripts/test-launch-review.sh:906-908,948-949,994-995,2213-2215
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Entry counts use grep -c on tool substring across full execution-issues.md If the fenced diagnostic body contains codex-review or cursor-review the count exceeds 1 and assert_eq fails spuriously Restrict grep to header lines only or rely on assert_regex for cardinality
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: implementation_plan SL-transient-obs-nontransient (c) vs scripts/test-launch-review.sh:996
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan bullet (c) said failure line must not contain transient-retries= but tests assert transient-retries=1 Operators following the stale plan text would expect a different log shape than the shipped feature Update plan/issue item (c) to match M=1 documented semantics
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: scripts/append-tool-failure.md:50-56 (plan text in prompt)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Earlier plan bullet contradicted final M=1 transient-retries semantics. Reviewers may incorrectly flag the non-transient test as violating the plan. Align issue/plan text with append-tool-failure.md edge-case wording.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: scripts/launch-review.sh:60-62,548,958 scripts/append-tool-failure.sh:143-147
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Review failures always emit auth-retries plus transient-retries while other launchers still emit retries=N only. A single execution-issues.md mixes two suffix shapes; alerts or scripts that match only retries= miss new review failure lines. Update runbooks or matchers to accept both forms or align other launchers in a follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/test-launch-review.sh:2181-2215
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Cursor launch-review harness only adds exhausted observability test; codex adds exhausted recovery and non-transient cases. Cursor-only regression in append path or SIDECAR vs diag selection might not be caught because those scenarios are never asserted under --tool cursor. Mirror codex SL-transient-obs-fired and SL-transient-obs-nontransient as cursor stubs with existing serial-lock env pattern.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-launch-review.sh:876-996 vs 2181-2215
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Cursor harness adds only the exhausted observability case versus three Codex cases. A bug in cursor-only failure logging or transient success paths could regress without a failing test where Codex would catch it. Add lighter cursor mirrors for success-with-retry and non-transient counter semantics if maintenance cost is acceptable.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-launch-review.sh:906-907 scripts/test-launch-review.sh:969-970 scripts/test-launch-review.sh:2213-2214
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Failure entry cardinality uses grep -c on bare tool label substring. Future captured stderr/body could mention codex-review or cursor-review outside the header and inflate the count past 1. Assert on anchored header lines or a single-line regex count for Step review Step 2 headers only.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-launch-review.sh:906-907,948-949,994-995,2212-2214
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Entry counts use grep -c over the tool label substring in the full execution-issues file. Captured stderr/stdout could someday include the literal token codex-review or cursor-review outside the header line, inflating counts and flaking or mis-signaling multiple failures. Count only the failure bullet line e.g. anchored grep on Step review Step 2 and the tool label in the header.
- **Suggested revision**: Address the concern above.

