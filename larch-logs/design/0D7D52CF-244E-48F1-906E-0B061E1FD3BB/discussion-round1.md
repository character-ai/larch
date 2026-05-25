## Decision 1: OOS dedup paragraph scope
- **Question**: Should the dedup-semantics fix also update step 3 (OOS dedup) in plan-review.md, or limit changes to step 2 only?
- **Resolution**: Update both step 2 and step 3 for symmetry — the same semantic-vs-syntactic anti-pattern applies to OOS observations.
- **Source**: user

## Decision 2: NEVER rule threshold language
- **Question**: Should the new NEVER rule include the specific "~30 raw findings" threshold from the issue's proposed text?
- **Resolution**: Omit the specific number; rely on the qualitative "temptation to write a Python/shell helper" signal so the rule stays timeless.
- **Source**: user

## Decision 3: Optional helper (aggregate-plan-findings.sh)
- **Question**: Should the optional helper script (suggested fix #3) be included in this change?
- **Resolution**: Out-of-scope — the issue explicitly marks it as future work. Doc clarification + NEVER rule alone are sufficient.
- **Source**: issue body (explicit "Out of scope" section)

## Decision 4: Parallel /review path updates
- **Question**: Should parallel changes apply to skills/review/references/* for symmetry?
- **Resolution**: Not needed — /review already has the LLM-based aggregator helper (skills/review/scripts/aggregate-findings.sh) and does NOT do main-agent string-key clustering. Asymmetric prompt is correct.
- **Source**: codebase
