# Review Round 1

- Mode: `diff`
- Accepted findings: 15
- Rejected findings: 0
- Exonerated findings: 0
- Neutral findings: 0

## Accepted Findings

### FINDING_10: correctness: scripts/token-cost.md:42-43
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Comparison table omits Claude LARCH_TOKEN_RATE_PER_M fallback used by token-cost.sh. Operators may believe Claude cost is N/A whenever LARCH_CLAUDE_RATE_PER_M is unset even if LARCH_TOKEN_RATE_PER_M is set; diverges from actual token-cost.sh behavior. Document Claude-only LARCH_TOKEN_RATE_PER_M fallback in the rate row and adjust N/A wording to match effective rates after fallback.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: scripts/token-tally.md:66-77
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Symmetric table repeats the incomplete token-cost rate model. Same misunderstanding propagates from the tally doc back to implement/fix-issue operators. Mirror the corrected token-cost.md semantics in the token-cost.sh column.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: scripts/token-tally.md:72-74
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Symmetric token-cost column repeats incomplete rate semantics. Same misunderstanding as token-cost.md for readers who only open token-tally.md. Mirror the corrected token-cost.md wording in this table.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/implement/scripts/write-final-report.sh:76-79
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Invalid RUN_ID failure path omits COMMENT_URL KV. Strict parsers expecting three keys on every failed envelope may treat output as incomplete versus other failure paths. Add emit_kv_out COMMENT_URL "" before STATUS or ERROR consistent with fail_usage and mkdir failure blocks.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/implement/scripts/write-final-report.sh:76-79
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Invalid RUN_ID failure omits COMMENT_URL KV line. Parsers expecting COMMENT_URL on every STATUS=failed per write-final-report.md see a missing key on traversal rejection only. Emit emit_kv_out COMMENT_URL "" before STATUS and ERROR like other failed paths.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/implement/scripts/write-final-report.sh:76-79
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Invalid RUN_ID failure omits COMMENT_URL in emitted KV lines. Parsers or orchestration that require COMMENT_URL on every terminal STATUS=failed may treat the stream as incomplete or mis-classify the failure compared to other exit-1 paths in the same script. Emit emit_kv_out COMMENT_URL "" before STATUS/ERROR on this path.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/implement/scripts/write-final-report.sh:76-79
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Invalid RUN_ID failure omits COMMENT_URL KV line unlike other STATUS=failed paths. Downstream parsers or wrappers that expect a complete KV set on every failure may mis-handle the response or retain a stale COMMENT_URL. Emit emit_kv_out COMMENT_URL "" before STATUS/ERROR on the invalid-RUN_ID branch to match mkdir/cp/ISSUE/upsert failure paths.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: skills/implement/scripts/write-final-report.sh:76-80
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] RUN_ID path-traversal failure omits COMMENT_URL KV line unlike other STATUS=failed exits. Downstream parsers or operators comparing KV shape across failure modes see only STATUS/ERROR for this branch while other failures include COMMENT_URL=. Emit emit_kv_out COMMENT_URL "" before STATUS/ERROR on the RUN_ID rejection branch; optionally align write-final-report.md RUN_ID bullet with the table.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: scripts/token-cost.md:39-44
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Divergence table lists only three vendor rates for token-cost.sh and omits LARCH_TOKEN_RATE_PER_M as Claude fallback. Readers may think token-cost has no single-rate path analogous to token-tally. Add a footnote or extra bullet clarifying Claude fallback via LARCH_TOKEN_RATE_PER_M per token-cost.sh.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: scripts/token-tally.md:74-75
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New table row says $ column omitted for unset/zero only; contract above also omits for malformed/non-numeric. Minor internal doc inconsistency within one file. Match wording to the Cost column paragraph (unset, malformed, or non-positive).
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: skills/implement/scripts/write-final-report.md:61-63
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Claims no filesystem touch on RUN_ID rejection. Strict reading contradicts earlier reads of IMPLEMENT_TMPDIR inputs. Reword to no writes under the run log directory tree or equivalent precision.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: scripts/token-cost.md:35-46;scripts/token-tally.md:67-78
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan asked for rounding semantics; tables omit %.2f vs $%.4f display divergence. Operators comparing dollar strings across surfaces may assume identical rounding without reading scripts. Add one row or footnote on decimal precision differences between helpers.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: scripts/token-cost.md:39-42
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Comparison table lists only three vendor rate env vars for token-cost.sh and omits LARCH_TOKEN_RATE_PER_M. Readers can wrongly infer Codex/Cursor inherit LARCH_TOKEN_RATE_PER_M or that token-cost has no shared-rate path; contradicts scripts/token-cost.sh:49-50 and the Environment table in the same doc. Amend the table cell to document LARCH_TOKEN_RATE_PER_M as Claude-only fallback when LARCH_CLAUDE_RATE_PER_M is unset empty or zero.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/token-cost.md:39-44;scripts/token-tally.md:71-76
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Divergence tables omit Claude-only LARCH_TOKEN_RATE_PER_M fallback and overstate independent per-vendor N/A. Only LARCH_TOKEN_RATE_PER_M set yields Claude USD while Codex/Cursor stay N/A, contradicting three-isolated-rates and symmetric N/A rows. Document Claude fallback to LARCH_TOKEN_RATE_PER_M in the rate and N/A rows in both markdown files.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/token-cost.md:39-46
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New divergence table omits Claude fallback to LARCH_TOKEN_RATE_PER_M and overstates per-vendor N/A rules. Operators or tooling may assume research’s LARCH_TOKEN_RATE_PER_M never affects /implement costs, or that Claude is N/A whenever LARCH_CLAUDE_RATE_PER_M is unset even when LARCH_TOKEN_RATE_PER_M is set; debugging and env parity assumptions become wrong. Document Claude-only fallback to LARCH_TOKEN_RATE_PER_M and align the N/A row with token-cost.sh (rate_or_na plus fallback).
- **Suggested revision**: Address the concern above.


