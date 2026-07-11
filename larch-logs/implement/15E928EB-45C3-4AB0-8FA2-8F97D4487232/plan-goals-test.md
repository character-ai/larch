## Goal
Implement issue #6855: [IMPLEMENTING] We set up claude to run with GLM 5.2, and need to update pricing.

## Implementation Plan
## Plan

## Goal

Price a GLM-5.2 **main-agent** lane with the configured Z.ai token rates. In final reports, show both the reference token cost and the estimated plan cost. Use the estimated plan cost in `TOTAL`.

Confidence: high

## Approach

1. Define the canonical GLM-5.2 model identifier and fixed plan divisor `15` as shared constants.
2. Add a shared, GLM-specific model canonicalization helper:
   - Map `glm-5.2[1m]` to canonical `glm-5.2`.
   - Leave every other model string unchanged, including non-GLM `[1m]` variants.
   - Use it only for main-agent GLM rate lookup and final-summary GLM identity detection.
3. Add the GLM-5.2 row to the Claude rate table with the complete Claude bucket shape:
   - input: `$1.40` per million tokens
   - cache read: `$0.26` per million tokens
   - cache create 5m: `$0.00`
   - cache create 1h: `$0.00`
   - output: `$4.40` per million tokens
4. Keep shared pricing outputs token-based. `CLAUDE_COST`, `TOTAL_COST`, and `/report-tokens` remain API-equivalent token estimates.
5. Preserve subprocess pricing from its recorded model:
   - Do not canonicalize inside the shared `rate_row()` path if that path is also used by `_claude_sub_rates_for_model()`.
   - Apply GLM alias canonicalization only in the main-agent rate-selection path, such as `display_rates()` or a dedicated main-lane lookup helper.
   - Keep `claude_sub` on its recorded model lookup behavior, including when its recorded model string is `glm-5.2[1m]`.
6. Change final-summary rendering only when the canonicalized resolved main-agent model is GLM-5.2:
   - Render the main lane as `Claude/GLM-5.2 token $T (estimated $E)`.
   - Compute `E` as `T / 15`.
   - Replace the main Claude token cost with `E` in the displayed `TOTAL`.
   - Leave Codex, Cursor, and `Claude (subprocess)` costs unchanged.
   - Add a concise explanation bullet immediately after the cost bullet.
7. Preserve the current cost line and surrounding summary byte-for-byte for non-GLM models, including existing non-GLM `[1m]` model behavior.

## Files to modify/create

### UPDATED: python/larch/core/config.py

- Add a canonical constant for `glm-5.2`.
- Add a named constant for the token-to-plan divisor `15`.
- Add a shared helper that canonicalizes only the GLM `[1m]` alias to the canonical GLM model identifier.
- Keep these pricing wire literals and the GLM alias behavior in the shared configuration authority.
- Do not introduce generic `[1m]` stripping that changes pricing behavior for other Claude models.

### UPDATED: python/larch/report/report_tokens_cost.py

- Add the GLM-5.2 Claude rate row with all five keys consumed by the rate-display and bucket-pricing paths: `input`, `cache_read`, `cache_create_5m`, `cache_create_1h`, and `output`.
- Set both cache-create tier rates to zero.
- Apply the shared GLM-specific canonicalization helper only before the **main-agent** Claude rate lookup.
- Keep the shared `rate_row()` and `_claude_sub_rates_for_model()` behavior based on their supplied recorded model strings; do not globally canonicalize there if those paths serve subprocess pricing.
- Ensure main-agent `glm-5.2` and `glm-5.2[1m]` price the main Claude bucket with the GLM row.
- Ensure a recorded `claude_sub` model remains priced through its existing subprocess lookup path and is not newly canonicalized.
- Preserve lookup behavior for every non-GLM model string, including non-GLM `[1m]` variants.
- Do not apply the plan divisor here. Shared token pricing and `/report-tokens` must retain token-based totals.

### UPDATED: python/larch/git/pr_body.py

- Canonicalize the resolved main-agent model with the shared GLM-specific helper before deciding whether the run is GLM-5.2.
- Detect GLM-5.2 from the resolved run identity used by `render_run_summary`, including the `glm-5.2[1m]` alias.
- Add a small final-summary-only calculation for the estimated plan cost and adjusted headline total.
- Render `Claude/GLM-5.2 token $T (estimated $E)` for the GLM main lane.
- Insert the explanation bullet directly after `- **Cost**:`.
- Keep the existing cost segment, total, and line ordering unchanged for non-GLM runs.
- Preserve the existing `- **Cost**:` grammar and all other vendor segments.
- Do not canonicalize or reprice the recorded `claude_sub` model for this display path.

### UPDATED: python/tests/report/test_report_tokens_cost.py

- Assert the exact GLM-5.2 rate row, including both zero-valued cache-create tiers and the zero cache-write behavior.
- Extend the rate-row shape coverage so GLM-5.2 is validated against every Claude bucket key read by `display_rates()`.
- Assert that main-agent `glm-5.2[1m]` resolves to the GLM-5.2 row.
- Verify bucketed GLM main-agent token counts produce the expected `CLAUDE_COST`.
- Verify shared `TOTAL_COST` remains token-based rather than divided by `15`.
- Add a regression assertion that a non-GLM `[1m]` model retains its existing lookup behavior and is not newly canonicalized to a base-model rate row.
- Add a subprocess-path regression case showing that a recorded `claude_sub` model is not passed through main-agent GLM alias canonicalization.

### UPDATED: python/tests/git/test_pr_body.py

- Add a GLM final-summary fixture with known costs.
- Assert the `Claude/GLM-5.2 token $T (estimated $E)` segment.
- Assert the headline total substitutes the estimated main-agent cost while retaining all other lane costs.
- Assert the explanation bullet follows the cost bullet.
- Cover `glm-5.2[1m]` through the final-summary rendering path, not only shared-pricing lookup.
- Include a nonzero `claude_sub` lane and assert it remains token-priced and is not divided by `15`.
- Add or strengthen a non-GLM golden assertion so its cost line and bullet layout remain unchanged.

### UPDATED: python/tests/report/test_final_report.py

- Exercise the manifest-driven path with `model_roster.main` set to GLM-5.2.
- Exercise the equivalent manifest-driven path with `model_roster.main` set to `glm-5.2[1m]`.
- Verify final-report token extraction uses the GLM rate rather than the Opus fallback for the main-agent lane.
- Verify the rendered report applies plan pricing only to the main Claude lane.
- Include a nonzero `claude_sub` lane and assert it is not divided by `15` or newly canonicalized through the main-agent rate path.
- Verify a non-GLM manifest model continues to use the existing final-summary format.

### UPDATED: docs/configuration-and-permissions.md

- Document the GLM-5.2 default rate row, including zero cache-create tier rates.
- Document that `glm-5.2[1m]` is treated as the GLM-5.2 pricing alias for the main-agent lane.
- Explain that shared pricing and `/report-tokens` show token-equivalent cost.
- Document the final-summary-only plan estimate and fixed divisor.
- Clarify that the plan adjustment applies only to the GLM main-agent lane and does not alter subprocess pricing.
- Clarify that this alias handling does not normalize or reprice other `[1m]` model names.

### UPDATED: docs/run-logs.md

- Update the final-summary contract for GLM-5.2 main-agent runs.
- Document the alternate `Claude/GLM-5.2` segment, adjusted `TOTAL`, and explanation bullet.
- State that a main-agent `glm-5.2[1m]` receives the same GLM final-summary treatment.
- State that non-GLM summaries retain the existing format, including non-GLM `[1m]` behavior, and that `claude_sub` remains token-priced from its recorded model.

## Edge cases

- Treat main-agent `glm-5.2` and `glm-5.2[1m]` as the same pricing and final-summary model.
- Do not strip or otherwise canonicalize `[1m]` suffixes for non-GLM models.
- Do not apply main-agent GLM alias canonicalization to subprocess rate lookup; `claude_sub` continues to use its recorded model string.
- Do not trigger plan pricing for unknown models, missing manifest models, or other Claude models.
- For non-GLM (Anthropic) main-agent runs, keep the plain `Claude $C` segment with no `(estimated ...)` annotation and no explanation bullet, since token cost equals actual cost there.
- Render `$0.00` values consistently when the GLM lane has no billable tokens.
- Round the token cost through the existing pricing path, then format the plan estimate and adjusted total to two decimal places.
- Keep cost-unavailable summaries as `N/A` without an explanation bullet.
- Leave cursor component breakdowns and Codex model splits unchanged.

## Failure modes

- If GLM alias handling occurs only in final rendering, `/report-tokens` may still fall back to Opus rates. Apply the shared GLM-specific helper in the main-agent rate lookup path.
- If GLM alias handling is added to shared `rate_row()`, `_claude_sub_rates_for_model()` can silently reprice subprocesses recorded as `glm-5.2[1m]`. Keep canonicalization out of shared subprocess-capable lookup paths.
- If final rendering compares the raw main model string, `glm-5.2[1m]` may price correctly but omit the estimated segment, explanation, and adjusted `TOTAL`. Canonicalize before the GLM identity check.
- If the GLM rate row omits either cache-create tier, bucketed pricing or rate display can raise a missing-key error. Provide the complete Claude row shape.
- If generic `[1m]` stripping is used, existing non-GLM models may be silently repriced outside this scope. Canonicalize only the explicit GLM main-agent alias.
- If the divisor is applied in shared pricing, `/report-tokens` and pricing KVs will change out of scope.
- If `TOTAL` is divided wholesale, subprocess and non-Claude lane costs will be understated. Replace only the main Claude component.
- If model detection reads ambient state instead of the resolved manifest identity, historical or resumed reports may receive the wrong format.
- If the explanation is appended as free-form trailing text, it may drift away from the cost line. Render it as an adjacent summary bullet.

## Testing strategy

Run only the affected tests and linters:

- `python3 -m pytest python/tests/report/test_report_tokens_cost.py`
- `python3 -m pytest python/tests/git/test_pr_body.py`
- `python3 -m pytest python/tests/report/test_final_report.py`
- Run the repository’s changed-file Python lint and type-check targets for the modified Python files.
- Run the changed-file Markdown lint for `docs/configuration-and-permissions.md` and `docs/run-logs.md`.

Confirm these invariants in tests:

- Main-agent GLM-5.2 and `glm-5.2[1m]` no longer fall back to Opus pricing.
- The GLM rate row contains every required Claude bucket key.
- Non-GLM `[1m]` model lookup behavior is unchanged.
- Recorded subprocess model lookup is unchanged by main-agent GLM alias support.
- Shared pricing remains token-based.
- Final-summary `TOTAL` uses only the divided GLM main-agent component.
- `claude_sub` is never divided or newly canonicalized.
- Non-GLM output remains byte-identical.

## Acceptance

Run only the affected tests and linters:

- `python3 -m pytest python/tests/report/test_report_tokens_cost.py`
- `python3 -m pytest python/tests/git/test_pr_body.py`
- `python3 -m pytest python/tests/report/test_final_report.py`
- Run the repository’s changed-file Python lint and type-check targets for the modified Python files.
- Run the changed-file Markdown lint for `docs/configuration-and-permissions.md` and `docs/run-logs.md`.

Confirm these invariants in tests:

- Main-agent GLM-5.2 and `glm-5.2[1m]` no longer fall back to Opus pricing.
- The GLM rate row contains every required Claude bucket key.
- Non-GLM `[1m]` model lookup behavior is unchanged.
- Recorded subprocess model lookup is unchanged by main-agent GLM alias support.
- Shared pricing remains token-based.
- Final-summary `TOTAL` uses only the divided GLM main-agent component.
- `claude_sub` is never divided or newly canonicalized.
- Non-GLM output remains byte-identical.

mechanical_churn: false
oversize_override: operator
diff_lines: 248

## Test plan
(no test plan section in plan-file)
