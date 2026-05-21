# Review Round 1

- Mode: `diff`
- Accepted findings: 14
- Rejected findings: 0
- Exonerated findings: 4
- Neutral findings: 0

## Accepted Findings

### FINDING_10: code-quality: skills/review/scripts/aggregate-findings.md:55-56
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Contract says disabled mode does not read findings.md; implementation counts blocks before the disabled exit. Operators/tests relying on the doc may assume zero file IO under LARCH_AGGREGATOR_DISABLED=1. Reorder checks or update aggregate-findings.md to reflect the actual read.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/review/scripts/aggregate-findings.md:13-15
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Disabled-mode contract says findings.md is not read, but INPUT_COUNT runs grep on the file before the disabled exit. Operators or docs readers may assume zero filesystem access in disabled mode and be surprised by reads or rely on that for side-effect reasoning. Rewrite the escape-hatch sentence to match actual behavior (no rewrite / no LLM path; optional note that a block count probe may read the file).
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: skills/review/scripts/aggregate-findings.sh:190-208
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Input reviewer strings are not comma-split when building input_set; output slots are comma-split. A single input block with comma-separated Reviewer(s) makes validation fail spuriously. Tokenize comma-separated input reviewer fields the same as output before set comparisons.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: skills/review/scripts/collect-findings.sh:409-418 skills/review/scripts/aggregate-findings.sh:72-75 skills/review/scripts/aggregate-findings.sh:190-260 skills/review/scripts/tally-code-votes.sh:1611-1613 agents/orchestrator-aggregator.md:19-23
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] OOS and in-scope share findings.md; aggregator+validator do not preserve [OUT_OF_SCOPE] semantics on merged headings. LLM merges an OOS-tagged FINDING with in-scope text and drops [OUT_OF_SCOPE] from the merged first line; tally treats it as in-scope, mis-routing votes and scoreboard rows. Exclude or validate OOS blocks through aggregation; or validate merged headings carry OOS when any source block was OOS.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: skills/review/scripts/review-core.sh:484-496
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Aggregator stderr is discarded when review-core invokes aggregate-findings.sh. Shell or tool errors during aggregation leave no transcript signal in review-core stdout/stderr; operators only see missing KV lines or must inspect tmpdir manually. Tee or log stderr to REVIEW_TMPDIR (e.g. review-core-aggregate.stderr) or gate suppression behind a debug env var.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: skills/review/scripts/review-core.sh:493-496
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Aggregator stderr discarded; early failures may omit warnings. Operators lose diagnostics for aggregator hard failures; harder incident review. Tee stderr to tmp log; on non-zero rc emit append_warning with log path.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: skills/review/scripts/review-core.sh:495-497
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Aggregator stderr is discarded to /dev/null while failures are intended to be non-fatal. Jq/dispatch/python errors or larch_err diagnostics during aggregation vanish from the parent log; review-core still dispatches voters on the pre-merge ballot with no stderr breadcrumb, so operators cannot distinguish a clean no-op from a crashed mid-script without digging in tmp. Stop silencing stderr (tee to review-core-aggregate.stderr) or emit_kv on non-zero aggregate exit with a pointer to captured logs.
- **Suggested revision**: Address the concern above.


### FINDING_22: risk-integration: skills/review/scripts/test-aggregate-findings.sh:1820-1865
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Failure-mode tests do not assert execution-issues.md warnings. append_warning could fail silently (helper missing/non-executable) with no test signal. Run one failing scenario with --session-env-path and grep execution-issues.md for the aggregator warning.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: skills/review/scripts/test-review-core.sh:1891-1931
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] All review-core harness runs force LARCH_AGGREGATOR_DISABLED=1. Wiring mistakes between review-core.sh and aggregate-findings.sh are never exercised under the stubbed review-core harness. Add one stubbed path with aggregation enabled and a sentinel aggregate script.
- **Suggested revision**: Address the concern above.


### FINDING_24: risk-integration: skills/review/scripts/test-review-core.sh:1893-1931
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] All review-core harness runs force LARCH_AGGREGATOR_DISABLED=1. No integration coverage that review-core wires aggregate between collect and voter dispatch; regressions in wiring args/env only surface in manual runs. Add one stubbed review-core case with REVIEW_CORE_AGGREGATE_FINDINGS_SH asserting ordering between stubs.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: skills/review/scripts/test-tally-code-votes.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No harness asserts scoreboard fan-out for comma-separated Reviewer(s) lines on merged ballots. A silent bug in the new awk-based split could under-credit reviewer slots in production voting-tally.md until caught manually. Add a tally harness case with one FINDING and multiple comma-separated *-output.txt reviewers; assert per-slot scoreboard rows/outcome counts.
- **Suggested revision**: Address the concern above.


### FINDING_26: risk-integration: skills/review/scripts/test-tally-code-votes.sh (no diff)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] tally-code-votes scoreboard splitting changed without visible harness delta. A typo or behavioral regression in the new awk comma splitter may not be caught until flaky manual review. Add a fixture asserting multiple scoreboard rows for a comma-separated Reviewer(s) line.
- **Suggested revision**: Address the concern above.


### FINDING_8: code-quality: skills/review/scripts/aggregate-findings.md:1
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Disabled contract says findings.md is not read; implementation still greps for INPUT_COUNT before the disabled exit. Operators/tests relying on literal “no read” semantics are misled. Align documentation with behavior or reorder the disabled branch before count_finding_blocks.
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: skills/review/scripts/aggregate-findings.md:53-55
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Doc claims disabled mode does not read findings.md. aggregate-findings.sh still runs count_finding_blocks (grep) before the disabled exit. Misleading operator expectations about IO side effects; move disabled check before counting or fix wording to no rewrite only.
- **Suggested revision**: Address the concern above.


