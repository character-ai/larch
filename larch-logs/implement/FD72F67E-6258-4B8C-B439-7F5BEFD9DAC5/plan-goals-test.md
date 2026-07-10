## Goal
Implement issue #6838: [IMPLEMENTING] Grok-aware Cursor pricing and cost wire.

## Implementation Plan
## Plan

## Approach

Extend the existing Cursor split into three lanes:

- Composer: every model other than Auto and exact `grok-4.5`, including empty, unknown, and future model names.
- Grok: exact `grok-4.5`.
- Auto: `config.CURSOR_AUTO_MODEL`.

Add the `("cursor", "grok-4.5")` rate row at input `2.00`, cache read `0.50`, and output `6.00` per million tokens. Apply the Teams surcharge only to the Composer lane; it must not affect Grok or Auto.

Evolve the cost wire additively. Preserve `CURSOR_COST` as the aggregate across all priced Cursor lanes. On detailed per-lane pricing, emit Composer, Grok, and Auto component keys immediately before `CURSOR_COST`; on the legacy aggregate fallback, emit only `CURSOR_COST` and do not infer a lane split.

Export one shared Cursor bucket-to-argv helper for `/report-tokens` and final-report pricing. It must accept a per-model Cursor mapping plus its aggregate bucket, validate the entire mapping before classification, classify all three lanes, and fall back to aggregate Composer-priced flags whenever the per-model mapping is missing, empty, malformed, or contains even one malformed per-model bucket. This prevents incomplete token accounting and prevents `/report-tokens`, final reports, and PR summaries from assigning a model to different pricing lanes.

## Files to modify/create

### UPDATED: python/larch/report/report_tokens_models.py

- Append optional per-lane Cursor costs to `RunRecord`: Composer, Grok, and Auto.
- Use an explicit unavailable default state for the new fields so historical constructors and legacy aggregate-only artifacts remain compatible and cannot be rendered as an inferred Composer split.
- Keep existing positional constructor compatibility by appending only defaulted fields.
- Add Grok display-rate fields to `DisplayRates`, with defaulted placement compatible with existing direct construction.

### UPDATED: python/larch/report/report_tokens_cost.py

- Add the `("cursor", "grok-4.5")` rate row with `2.00` input, `0.50` cache read, and `6.00` output per million tokens, without the Teams surcharge.
- Extend `display_rates()` and `DisplayRates` construction with Grok input, cache-read, and output rates, using focused Grok environment overrides consistent with the existing Cursor Auto override contract.
- Extend the token-cost CLI with:
  - `--cursor-grok-input-tokens`
  - `--cursor-grok-cache-read-tokens`
  - `--cursor-grok-output-tokens`
- Keep existing `--cursor-*` flags as the Composer detailed lane and aggregate legacy fallback; retain `--cursor-auto-*` as the Auto lane.
- Extract and export a public helper, parallel to the existing model-aware argv helpers, that accepts `BUCKETS_cursor_by_model` plus `BUCKETS_cursor` and returns the three-lane Cursor token flags:
  - validate that the top-level value is a non-empty mapping and that **every** model entry has a valid token-bucket mapping before accumulating any detailed lane;
  - exact `config.CURSOR_AUTO_MODEL` to `--cursor-auto-*`;
  - exact `"grok-4.5"` to `--cursor-grok-*`;
  - all other valid model keys, including empty, unknown, and future names, to `--cursor-*`;
  - missing, empty, malformed, or partially malformed model maps fall back exclusively to aggregate `BUCKETS_cursor` flags, without mixing valid detailed entries with aggregate fallback.
- Make `_cursor_argv()` delegate to that exported helper so report-run pricing and final-report argv construction share identical classification, validation, and fallback behavior.
- Extend parsed pricing counts with Grok input, cache-read, output, and a Grok-bucket indicator.
- Enter detailed Cursor pricing when **any** Composer, Grok, or Auto detailed bucket is present, including Grok-only usage; do not let a Grok-only invocation fall through to blended legacy Cursor pricing.
- In the detailed path:
  - calculate Composer, Grok, and Auto costs independently from their respective display-rate rows;
  - include all three lanes in `CURSOR_TOKENS`;
  - set `CURSOR_COST` to the rounded sum of the three lane costs;
  - preserve zero-valued component costs when detailed lane flags established model-aware source shape.
- In the aggregate fallback path, continue using blended `--cursor-tokens` pricing and emit no component Cursor keys.
- Emit `CURSOR_COMPOSER_COST`, `CURSOR_GROK_COST`, and `CURSOR_AUTO_COST` immediately before `CURSOR_COST` in `token_cost_from_args()`’s fixed wire order.
- Update the compact cost-line renderer to show a Cursor lane split when any component key is present, including known detail that rounds to `$0.00`; otherwise retain the existing aggregate Cursor segment.
- In `price_run()`, after parsing the cost wire, keep `RunRecord.cursor_cost` bound to aggregate `CURSOR_COST` and copy the three component values to the new `RunRecord` lane fields only when:
  - the source report has a valid non-empty `BUCKETS_cursor_by_model` mapping under the shared helper’s full-mapping validation rules; and
  - all three detailed component keys are present in the parsed cost wire.
- Leave all `RunRecord` Cursor lane fields unavailable for aggregate fallback, absent/empty/malformed/partially malformed model mappings, and `_fallback_cost()` results. Rendering and report-cache construction must consume these stored fields only; they must not re-price or reclassify `raw_report`.

### UPDATED: python/larch/report/report_tokens_render.py

- Render Composer, Grok, and Auto Cursor costs in the vendor breakdown when lane fields are available, while retaining aggregate Cursor cost and token totals.
- Add per-run Cursor lane detail to the top-runs table without removing the aggregate Cursor total.
- Add per-day trends for each available Cursor lane while retaining the aggregate Cursor trend.
- Include Grok and Auto rate rows in the rates section, alongside Composer’s existing Cursor rate row.
- Add per-lane values to report-cache rows only as additive fields.
- Gate split rendering on lane availability/source shape, not nonzero monetary values, so valid tiny lane costs that round to zero remain visible.
- For legacy records with unavailable lane fields, render only the existing aggregate Cursor value and preserve current golden output.
- Keep renderers display-only: use the per-lane values populated by `price_run()` and do not inspect model buckets or duplicate Cursor lane classification.

### UPDATED: python/larch/report/final_report.py

- Replace the inline aggregate Cursor argv branch in `_token_argv_from_report()` with the exported shared Cursor bucket-to-argv helper.
- Pass `BUCKETS_cursor_by_model` and aggregate `BUCKETS_cursor` through that helper so final reports classify Composer, exact Grok 4.5, and Auto identically to `/report-tokens`.
- Preserve aggregate-bucket fallback for missing, empty, malformed, and partially malformed per-model mappings.
- Read the additive Cursor component cost keys from the cost wire, along with unchanged `CURSOR_COST`.
- Return aggregate and additive Cursor costs from `_final_report_token_fields()`.
- Pass lane costs to the final-summary renderer only when component keys are present; preserve aggregate-only presentation for legacy token artifacts.

### UPDATED: python/larch/git/pr_body.py

- Extend `_TOKEN_COST_ARGS` and the run-summary CLI parser with all detailed Cursor lane flags:
  - existing `cursor-auto-*` flags;
  - new `cursor-grok-*` flags;
  - existing `cursor-*` Composer flags.
- Ensure `_summary_token_argv()` forwards every Cursor lane flag to `report_tokens_cost.token_cost_from_args()` unchanged.
- Read `CURSOR_COMPOSER_COST`, `CURSOR_GROK_COST`, and `CURSOR_AUTO_COST` from the returned cost wire in addition to unchanged `CURSOR_COST`.
- Add a Cursor summary formatter parallel to the Codex formatter.
- Render Composer, Grok, and Auto amounts only when component cost keys are available; otherwise preserve the existing single aggregate Cursor summary.
- Preserve total-cost and total-token summary grammar and values.

### UPDATED: python/tests/report/test_report_tokens_cost.py

- Assert the Grok 4.5 rate row uses `2.00`, `0.50`, and `6.00`, and that changing the Teams surcharge does not change Grok or Auto rates.
- Cover Grok display-rate overrides, including malformed or nonpositive override fallback behavior if that is part of the existing `env_rate()` contract.
- Test direct Grok-only flags and verify they enter detailed pricing rather than blended fallback.
- Assert Grok-only detailed pricing emits all three Cursor component keys, with zero-valued Composer and Auto components where applicable, and that their sum equals `CURSOR_COST`.
- Test a mixed Composer, Grok, and Auto invocation. Assert each lane’s independent cost, aggregate `CURSOR_COST`, `CURSOR_TOKENS`, and `TOTAL_TOKENS`.
- Assert the exact output wire order places `CURSOR_COMPOSER_COST`, `CURSOR_GROK_COST`, and `CURSOR_AUTO_COST` immediately before `CURSOR_COST`.
- Assert the aggregate-only `--cursor-tokens` fallback emits only `CURSOR_COST`, with no Cursor component keys.
- Test the exported Cursor argv helper and `_cursor_argv()` delegation with:
  - Composer;
  - exact `grok-4.5`;
  - Auto;
  - unknown and model-less entries routed to Composer;
  - missing and empty model maps falling back to aggregate Cursor flags;
  - malformed top-level model maps falling back to aggregate Cursor flags;
  - a partially malformed map containing valid model buckets plus one invalid/non-mapping bucket falling back entirely to aggregate Cursor flags, with no detailed lane flags emitted.
- Cover split and aggregate forms of the compact cost line, including model-aware lane costs that round to zero.
- Verify `price_run()` copies all three component costs into `RunRecord` only for valid detailed model-aware reports, keeps aggregate `cursor_cost`, and leaves lane fields unavailable for legacy aggregate, malformed, partially malformed, and fallback-priced reports.

### UPDATED: python/tests/report/test_report_tokens_render.py

- Add a model-aware `RunRecord` fixture with Composer, Grok, and Auto costs, including an availability-preserving zero-valued lane case.
- Assert token analysis renders all three lane amounts while retaining aggregate Cursor cost.
- Assert top-run and trend output includes available Cursor lane splits.
- Assert cache JSON gains additive per-lane fields.
- Assert a legacy record with unavailable lane fields still renders only aggregate Cursor output.
- Keep existing legacy golden fixtures unchanged unless a verified aggregate-only rendering change is required.

### UPDATED: python/tests/report/test_final_report.py

- Add a token-report fixture containing Composer, exact `grok-4.5`, Auto, unknown, and model-less Cursor model buckets.
- Assert `_token_argv_from_report()` delegates to shared classification behavior and emits the correct Composer, Grok, and Auto flags.
- Assert final-report pricing handles Grok-only model buckets through detailed Grok pricing rather than aggregate Composer pricing.
- Add malformed top-level and partially malformed per-model Cursor-map fixtures; assert `_token_argv_from_report()` uses aggregate Cursor fallback rather than partially classifying valid entries.
- Assert `_final_report_token_fields()` returns aggregate Cursor cost plus additive component fields for model-aware artifacts.
- Assert the rendered final summary shows the Cursor lane split when component fields exist.
- Add legacy token artifacts with absent, empty, and malformed `BUCKETS_cursor_by_model`; assert aggregate Cursor fallback and aggregate-only presentation.

### UPDATED: python/tests/git/test_pr_body.py

- Test PR summary rendering with Composer, Grok, and Auto cost fields.
- Assert the aggregate Cursor label is replaced by the lane split only when component cost fields are available, including components that render as `$0.00`.
- Keep coverage for legacy callers that provide only `cursor_cost`.
- Test CLI forwarding of Composer, Grok, and Auto token flags into the shared pricing wire.
- Add a Grok-only forwarding case to prevent fallback to blended Composer pricing.
- Assert total cost and token totals remain unchanged by presentation splitting.

## Edge cases

- Treat `grok-4.5` as an exact model identifier. Do not classify other `grok-*` names at the Grok 4.5 rate.
- Route empty, unknown, and future unrecognized model names to Composer.
- Treat missing, empty, malformed, or partially malformed `BUCKETS_cursor_by_model` as legacy aggregate data.
- Validate every model entry before detailed classification; never silently discard malformed buckets from an otherwise mapping-shaped model map.
- Do not infer a lane split from aggregate `CURSOR_COST` or aggregate Cursor token counts.
- Preserve zero-valued lane fields when a valid detailed source shape exists.
- Use source-shape availability and component-key presence, not monetary truthiness, when selecting split rendering.
- Keep the Teams surcharge limited to Composer pricing. It must not affect Grok or Auto.
- Do not add `tokens.py` enrichment; newly generated reports already contain `BUCKETS_cursor_by_model`.

## Failure modes

- Omitting the Grok bucket from the detailed-pricing guard would make Grok-only data fall through to blended Composer pricing. Include Grok counts and the Grok bucket indicator in the detailed-path decision.
- Accepting a partially malformed model map and skipping its invalid entry would silently undercount Cursor usage. Treat any invalid per-model bucket as a whole-map validation failure and use aggregate Cursor pricing only.
- Duplicated Cursor classification could price final reports differently from `/report-tokens`. Export one helper and make both callers use it.
- Failing to map detailed cost-wire components in `price_run()` would leave `/report-tokens` scan-and-render output aggregate-only despite valid model-aware source data. Copy all component keys into `RunRecord` only after valid source-shape and complete-wire checks.
- Omitting Auto or Grok from `_TOKEN_COST_ARGS` would produce correct stored cost fields but incorrect recomputed PR summaries. Forward all detailed Cursor flags.
- Emitting component keys during aggregate fallback would falsely label historical aggregate costs. Restrict component-key emission to detailed lane pricing.
- Changing `CURSOR_COST` or placing new keys unpredictably would break existing wire consumers. Preserve the aggregate key and fixed additive ordering.
- Applying the Teams surcharge to Grok would overstate the new lane.
- Positional `RunRecord` construction can break if new defaulted fields are inserted before existing fields. Append them.

## Testing strategy

- Run the four focused test modules:
  - `python/tests/report/test_report_tokens_cost.py`
  - `python/tests/report/test_report_tokens_render.py`
  - `python/tests/report/test_final_report.py`
  - `python/tests/git/test_pr_body.py`
- Run configured Python lint and type checks against the changed Python files.
- Verify exact cost-wire names and ordering with direct assertions.
- Verify these scenarios:
  - Composer only;
  - Grok only;
  - Auto only;
  - mixed Composer, Grok, and Auto;
  - unknown and model-less rows;
  - missing, empty, malformed, and partially malformed per-model maps;
  - legacy aggregate artifact;
  - model-aware artifact whose lane costs round to zero.
- Confirm `CURSOR_COST` always equals the component sum on detailed pricing, valid detailed scan records carry all lane values into rendering and cache output, and existing aggregate totals and legacy golden reports remain byte-compatible.

## Acceptance

- Run the four focused test modules:
  - `python/tests/report/test_report_tokens_cost.py`
  - `python/tests/report/test_report_tokens_render.py`
  - `python/tests/report/test_final_report.py`
  - `python/tests/git/test_pr_body.py`
- Run configured Python lint and type checks against the changed Python files.
- Verify exact cost-wire names and ordering with direct assertions.
- Verify these scenarios:
  - Composer only;
  - Grok only;
  - Auto only;
  - mixed Composer, Grok, and Auto;
  - unknown and model-less rows;
  - missing, empty, malformed, and partially malformed per-model maps;
  - legacy aggregate artifact;
  - model-aware artifact whose lane costs round to zero.
- Confirm `CURSOR_COST` always equals the component sum on detailed pricing, valid detailed scan records carry all lane values into rendering and cache output, and existing aggregate totals and legacy golden reports remain byte-compatible.

diff_lines: 612

## Test plan
(no test plan section in plan-file)
