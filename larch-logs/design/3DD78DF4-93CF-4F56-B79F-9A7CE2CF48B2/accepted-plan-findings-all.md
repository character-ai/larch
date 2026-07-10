### FINDING_1: Normalize GLM-5.2 identity consistently for pricing and final-summary rendering
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-dyn-Pricing Contract Auditor
- **Severity**: major
- **Concern**: Trailing `[1m]` normalization must be shared across rate lookup and final-summary rendering. If `glm-5.2[1m]` is priced as GLM-5.2 but compared as a raw model string during rendering, the report can retain the legacy Claude token segment, omit the estimated plan-cost segment and explanation, and leave `TOTAL` undiscounted. The normalization should apply to the main-agent model without changing `claude_sub` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add normalize_claude_pricing_model() in config.py (generic trailing [1m] strip). Use it in rate_row() and in pr_body GLM detection before comparing to GLM_5_2_MODEL.
  - From Codex-Arch: Add a shared model-normalization helper or reuse the rate-lookup normalization before deciding whether to apply the GLM final-summary format and divisor
  - From Cursor-Innovation: In the pr_body.py approach, require the same trailing-[1m] strip before the GLM-5.2 identity check (or call a shared helper). Keep the planned [1m] test in test_pr_body.py.
  - From Codex-Innovation: Normalize the resolved main model, or compare it after removing the trailing `[1m]` suffix, before applying the GLM final-summary label and divisor. Add a final-summary assertion for the variant, not only a shared-pricing lookup assertion.
  - From Codex-Pragmatic: Use the same trailing `[1m]` normalization for final-summary model detection, or centralize a predicate that treats `glm-5.2` and `glm-5.2[1m]` as the same main-agent model.
  - From Cursor-Requirements: Add a shared config helper (next to the GLM constants) that canonicalizes pricing-model strings; call it from both `rate_row`/`display_rates` and the GLM branch in `render_run_summary` before `is_glm` checks and display math.
  - From Codex-dyn-Pricing Contract Auditor: Normalize the resolved main model before the GLM final-summary check, or compare both `glm-5.2` and `glm-5.2[1m]`; keep the normalization limited to main-agent summary detection so `claude_sub` remains unchanged


### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/report_tokens_cost.py:78-106
- **Concern**: [SCOPE-REDUCTION] GLM rate row must name all five Claude bucket keys. Scenario: GLM row text only says cache writes are $0.00. display_rates() always reads cache_create_5m and cache_create_1h from the row. A row with only input/cache_read/output will KeyError on the first bucketed GLM run.
- **Proposed resolution**: In the rate-row step, require cache_create_5m: 0.0 and cache_create_1h: 0.0 (same shape as other Claude rows). Extend test_claude_rate_rows_include_cache_tiers to include glm-5.2.


### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/report/report_tokens_cost.py:127-138
- **Concern**: [SCOPE-REDUCTION] Generic trailing `[1m]` stripping before every Claude rate lookup exceeds GLM-only scope. Scenario: Approach step 3 normalizes any trailing `[1m]` suffix before lookup. That also reprices existing non-GLM models such as `claude-sonnet-4-6[1m]` (see `config.CLAUDE_CI_RECOVERY_MODEL`) from Opus fallback to Sonnet rates in shared `TOTAL_COST` and `/report-tokens`, outside the issue anchor. Only GLM pricing was requested.
- **Proposed resolution**: Normalize only GLM aliases (map `glm-5.2[1m]` to the canonical `glm-5.2` row) or add an explicit plan/test/doc note that repricing all `[1m]` suffixed Claude models is intentional collateral.

### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/report_tokens_cost.py:127-138
- **Concern**: Keep GLM alias canonicalization on the main-agent pricing path, not in the shared `rate_row()` used by subprocess pricing. Scenario: The plan requires `claude_sub` to remain priced from its recorded Claude model. If `rate_row()` canonicalizes `glm-5.2[1m]` globally, `_claude_sub_rates_for_model()` will also receive GLM handling, changing subprocess pricing when a recorded subprocess model uses that alias
- **Proposed resolution**: Apply the helper in `display_rates()` or another main-lane-only lookup path, or add an explicit non-GLM/subprocess path that preserves the recorded subprocess model unchanged

