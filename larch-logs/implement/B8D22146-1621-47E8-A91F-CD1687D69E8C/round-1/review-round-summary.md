# Review Round 1

- Mode: `diff`
- Accepted findings: 18
- Rejected findings: 4
- Exonerated findings: 0
- Neutral findings: 2

## Accepted Findings

### FINDING_1: **Important** `correctness` — `scripts/dispatch-code-voters.sh:230`, `skills/review/scripts/tally-code-votes.sh:212` — Parse-rate diagnostics are keyed only by tool, but voter slots can share a tool after fallback, especially Claude. Concrete failing scenario: voter 1 fails parse retry and leaves `claude-parse-rate-diag.txt`; voter 2 falls back to Claude, initially fails parse-rate, then succeeds on retry, and line 230 removes `claude-parse-rate-diag.txt`, so the tally at `skills/review/scripts/tally-code-votes.sh:212-216` reports no failed voter parse slot even though `VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE`. Make diagnostics slot-specific, or pass/count the emitted `VOTER_N_PARSE_RATE_STATUS` values through `review-core.sh` into the tally instead of inferring slot failures from `${tool}-parse-rate-diag.txt`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` — `scripts/dispatch-code-voters.sh:230`, `skills/review/scripts/tally-code-votes.sh:212` — Parse-rate diagnostics are keyed only by tool, but voter slots can share a tool after fallback, especially Claude. Concrete failing scenario: voter 1 fails parse retry and leaves `claude-parse-rate-diag.txt`; voter 2 falls back to Claude, initially fails parse-rate, then succeeds on retry, and line 230 removes `claude-parse-rate-diag.txt`, so the tally at `skills/review/scripts/tally-code-votes.sh:212-216` reports no failed voter parse slot even though `VOTER_1_PARSE_RATE_STATUS=NOT_SUBSTANTIVE`. Make diagnostics slot-specific, or pass/count the emitted `VOTER_N_PARSE_RATE_STATUS` values through `review-core.sh` into the tally instead of inferring slot failures from `${tool}-parse-rate-diag.txt`.
- **Suggested revision**: Address the concern above.


### FINDING_10: code-quality: scripts/dispatch-code-voters.sh:check_voter_parse_rate (pre-retry branch)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Execution-issues warning is logged on first NOT_SUBSTANTIVE before retry succeeds, leaving a stale warning after a clean retry. Operators see a warning despite recovered structured votes. Defer append-tool-failure until retry fails or annotate/supersede on successful retry.
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: scripts/test-dispatch-code-voters.sh; implementation_plan:Testing strategy
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Only voter-1 (Claude) parse-rate retry is covered by new tests; no coverage for voter slots 2–3 retry paths or their PARSE_RATE_STATUS KVs. A regression in codex/cursor retry wiring can ship while CI still passes. Add stubbed codex/cursor NOT_SUBSTANTIVE→retry scenarios asserting launch logs, final output paths, and VOTER_2/3_PARSE_RATE_STATUS.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: scripts/dispatch-code-voters.sh:126 skills/review/scripts/tally-code-votes.sh:211-218
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Parse-rate diag paths are per-tool; tally counts one file per tool. Two slots with the same voter_tool can share one diag file; VOTER_PARSE_FAILED_COUNT can undercount and EFFECTIVE_VOTERS can be too high. Key diag files by slot or output path; tally failures per voter file path instead of tool set.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: scripts/dispatch-code-voters.sh:221-223
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] check_voter_parse_rate on retry output re-runs full warning side effects before restoring saved diag. Retry attempt 2 is non-empty and still NOT_SUBSTANTIVE: second append-tool-failure and second larch_err for same slot; duplicate execution warnings. Refactor to compute parse-rate status without logging on probe calls or only emit after final disposition.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: scripts/dispatch-code-voters.sh:check_voter_parse_rate diag; skills/review/scripts/tally-code-votes.sh:VOTER_PARSE_FAILED_COUNT loop
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Diag filenames are per voter_tool only; tally counts at most one diag per tool name. When two slots both report tool claude (dual fallback), two narrative-only slots can still yield only one claude-parse-rate-diag.txt so EFFECTIVE_VOTERS and voter-parse banners undercount failures. Key diag by slot/output stem or emit explicit per-slot parse KV for tally instead of inferring from three fixed filenames.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: skills/review/scripts/tally-code-votes.sh:252-254,279
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Banner and panel_tier use EFFECTIVE_VOTERS but classify_result still uses ELIGIBLE_VOTERS. Three voter files with diag files for claude codex and cursor yields EFFECTIVE_VOTERS=0 and main-agent banner text while accept_finding still applies eligible=3 thresholds so 2 YES plus NEUT can still accept. Align classify_result eligible argument with EFFECTIVE_VOTERS or change banner so it does not imply acceptance policy from effective count.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: skills/review/scripts/tally-code-votes.sh:252-254,279
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Banner and panel_tier use EFFECTIVE_VOTERS but classify_result still uses ELIGIBLE_VOTERS. Three voter files on disk with one parse-degraded file inflates NEUT while the banner claims a reduced tier such as unanimous-2; outcomes still follow three-judge classify_result branches. Align classify_result (and docs) with EFFECTIVE_VOTERS or stop advertising a reduced tier when ELIGIBLE_VOTERS drives math.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: scripts/dispatch-code-voters.sh:125-153,198-232
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] First NOT_SUBSTANTIVE check logs execution-issues before retry; successful retry clears diag but leaves prior warning. Operators see a parse-rate warning after a successful retry and clean KVs, causing false escalations. Defer logging until retry fails or append a follow-up resolution line on success.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: scripts/dispatch-code-voters.sh:221-238
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Retry probe runs full check_voter_parse_rate on retry_output, which can append-tool-failure again. Narrative on both attempts yields duplicate Warnings rows for one slot. Use a non-logging classification path for the retry probe or suppress duplicate warnings.
- **Suggested revision**: Address the concern above.


### FINDING_22: risk-integration: scripts/dispatch-code-voters.sh:99-240
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Successful parse-rate retry does not retract the execution-issues warning logged on the first NOT_SUBSTANTIVE pass. Operators see a persistent voter parse-rate warning in execution-issues.md even when VOTER_N_PARSE_RATE_STATUS=OK and voter output was replaced after a successful retry. Defer append-tool-failure until retry fails, or append a follow-up resolution line when retry succeeds.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: scripts/dispatch-code-voters.sh:check_and_retry_voter_parse_rate
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Post-retry check_voter_parse_rate on retry output can duplicate append-tool-failure / larch_err when both attempts are NOT_SUBSTANTIVE. execution-issues.md accumulates two warnings for one slot; operators may treat it as two independent failures. Add a silent re-check mode or skip logging on the diagnostic pass over the retry artifact.
- **Suggested revision**: Address the concern above.


### FINDING_24: risk-integration: scripts/test-dispatch-code-voters.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No tests cover voter 2/3 parse-retry or launch_voter_retry for codex/cursor. Regression in waterfall-external retry path ships without CI signal. Add stubbed NOT_SUBSTANTIVE cases for codex and cursor slots.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: scripts/test-dispatch-code-voters.sh (new retry cases)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No harness coverage for voter-2/voter-3 parse-rate retry or launch_voter_retry codex/cursor paths. Regression in waterfall retry wiring could ship undetected despite plan scope for voters 2 and 3. Add stubbed codex/cursor (or waterfall) tests asserting retry KVs and side effects for slots 2 and 3.
- **Suggested revision**: Address the concern above.


### FINDING_26: risk-integration: skills/review/scripts/tally-code-votes.sh:211-218
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Parse-rate diag files are counted only by fixed tool names under REVIEW_TMPDIR, not tied to the current voter file set or run identity. A reused tmpdir can retain claude/codex/cursor parse-rate diags from a prior run, falsely lowering EFFECTIVE_VOTERS and showing degraded banners while all current voter outputs are substantive. Bind diag detection to active voter outputs or a per-run diag naming scheme and clear or ignore stale diags.
- **Suggested revision**: Address the concern above.


### FINDING_27: risk-integration: skills/review/scripts/tally-code-votes.sh:252-279
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Panel tier banner uses EFFECTIVE_VOTERS but classify_result still uses ELIGIBLE_VOTERS. Tally shows unanimous-2 (or similar) while vote thresholds still follow 3-judge rules, misaligning displayed policy with outcomes. Align classify_result denominator with EFFECTIVE_VOTERS or document that the banner is informational and does not change quorum math.
- **Suggested revision**: Address the concern above.


### FINDING_28: risk-integration: skills/review/scripts/tally-code-votes.sh:638-645,564
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] VOTER_PARSE_FAILED_COUNT scans fixed tool names; VOTER_COUNT still emits ELIGIBLE_VOTERS. Stale claude-parse-rate-diag.txt in tmpdir lowers EFFECTIVE_VOTERS while VOTER_COUNT stays 3; banner contradicts KV consumers. Scope diag detection to active voter paths or clear diags per run.
- **Suggested revision**: Address the concern above.


### FINDING_7: architecture: scripts/dispatch-code-voters.sh:126,198-239; skills/review/scripts/tally-code-votes.sh:638-645
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Parse-rate diag file is per voter_tool not per slot; tally counts at most one failure per tool name. Both waterfall slots resolve to claude; two narrative outputs contend for claude-parse-rate-diag.txt; voter banner undercounts failed slots. Key diag and tally signals by slot id or output basename, not tool name alone.
- **Suggested revision**: Address the concern above.


