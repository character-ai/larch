# Review Round 1

- Mode: `diff`
- 3 accepted, 5 rejected (4 neutral)

## Accepted Findings

### FINDING_14: **risk-integration** `python/rendering.py:1136` — The plan-review prompt now allows TSV `severity blocking`, but the Step 3 continuation path still treats only `important`, `latent`, and `nit` as structured severities in `skills/design/scripts/plan-review-continuation.sh:89-97` and the Gate B contract in `skills/design/references/approval-gates.md:64-70`. A blocking accepted finding can therefore fall back to concern-text classification, so `HIGH_ACCEPTED_COUNT` can be wrong when the concern text lacks the fallback keywords. **Suggested fix:** Add `blocking` to the design accepted-finding severity contracts, map it above `important`, and add a continuation/Gate B regression test for an accepted `- **Severity**: blocking` finding.
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: - **risk-integration** `python/rendering.py:1136` — The plan-review prompt now allows TSV `severity blocking`, but the Step 3 continuation path still treats only `important`, `latent`, and `nit` as structured severities in `skills/design/scripts/plan-review-continuation.sh:89-97` and the Gate B contract in `skills/design/references/approval-gates.md:64-70`. A blocking accepted finding can therefore fall back to concern-text classification, so `HIGH_ACCEPTED_COUNT` can be wrong when the concern text lacks the fallback keywords. **Suggested fix:** Add `blocking` to the design accepted-finding severity contracts, map it above `important`, and add a continuation/Gate B regression test for an accepted `- **Severity**: blocking` finding.
- **Suggested revision**: Address the concern above.


### FINDING_15: **risk-integration** `skills/shared/reviewer-templates.md:204-213` — The reviewer templates now tell code reviewers to emit `blocking`, but the code-review aggregator still hard-codes `important|latent|nit` in `agents/orchestrator-aggregator.md:30-37` and validates the same three values in `python/legacy_review_shell/aggregate-findings.sh:317-318,664-668`. If a reviewer follows the new prompt, the aggregator must either down-convert the severity or fail validation if it preserves `blocking`. **Suggested fix:** Update the aggregator prompt, merge ordering, validator regex, and aggregate-findings tests to accept `blocking` above `important`.
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: - **risk-integration** `skills/shared/reviewer-templates.md:204-213` — The reviewer templates now tell code reviewers to emit `blocking`, but the code-review aggregator still hard-codes `important|latent|nit` in `agents/orchestrator-aggregator.md:30-37` and validates the same three values in `python/legacy_review_shell/aggregate-findings.sh:317-318,664-668`. If a reviewer follows the new prompt, the aggregator must either down-convert the severity or fail validation if it preserves `blocking`. **Suggested fix:** Update the aggregator prompt, merge ordering, validator regex, and aggregate-findings tests to accept `blocking` above `important`.
- **Suggested revision**: Address the concern above.


### FINDING_5: **correctness** `skills/design/scripts/plan-review-continuation.sh:89-97` — `python/rendering.py:1136` now tells plan reviewers to emit `severity blocking`, but Gate B still treats only `important`, `latent`, and `nit` as structured severities. A blocking plan finding makes the whole set fall back to concern-text classification, so a blocking item without fallback keywords may not be counted as high/blocking. **Suggested fix:** Add `blocking` to the valid structured severity set, map it explicitly in `skills/design/references/approval-gates.md`, and add/update Gate B tests for blocking severity.
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: - **correctness** `skills/design/scripts/plan-review-continuation.sh:89-97` — `python/rendering.py:1136` now tells plan reviewers to emit `severity blocking`, but Gate B still treats only `important`, `latent`, and `nit` as structured severities. A blocking plan finding makes the whole set fall back to concern-text classification, so a blocking item without fallback keywords may not be counted as high/blocking. **Suggested fix:** Add `blocking` to the valid structured severity set, map it explicitly in `skills/design/references/approval-gates.md`, and add/update Gate B tests for blocking severity.
- **Suggested revision**: Address the concern above.


