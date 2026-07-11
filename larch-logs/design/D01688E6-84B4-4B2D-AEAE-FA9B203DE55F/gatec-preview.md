## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Approach

1. Remove Cursor `auto` producers from reviewer slots, dynamic rows, forced plan-fidelity dispatch, and both fixer launchers.
2. Let Cursor rows resolve through the existing model chain. Preserve explicit per-slot `cursor_model` plumbing for callers that need a non-default override, while ensuring every static and dynamic Cursor manifest records its effective `resolved_model`.
3. Remove the auto rate, token flags, display fields, cost fields, and rendered breakdowns as one two-lane Composer/Grok schema change.
4. Treat legacy `model="auto"` token buckets and any other unrecognized Cursor model names as unknown Cursor models. Fold them into the Composer bucket and price them through `DEFAULT_VENDOR_MODEL["cursor"]`.
5. Keep readers tolerant of stale `CURSOR_AUTO_COST` lines in committed artifacts by ignoring unknown keys. Do not rewrite run logs.
6. Update every current Cursor-auto prose occurrence, including installation and configuration guidance. Regenerate the topology projection from its TSV source.
7. Add focused routing, manifest, schema-compatibility, and launcher tests. Preserve the current Grok 4.5 constants, rate row, MODERATE coder routing, and token bucket.

## Files to modify/create

### UPDATED: python/larch/core/config.py

- Delete `CURSOR_AUTO_MODEL`.
- Remove Cursor model overrides from `review.panel` and `design.plan_review_panel` slot construction.
- Keep `CURSOR_DEFAULT_MODEL = "composer-2.5"`, `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY`, and all generic `SlotDefault.cursor_model` plumbing.
- Update reviewer and fixer `doc_fallback` text to describe Composer 2.5 default resolution rather than per-slot auto selection.
- Do not change voter roles or Grok 4.5 routing.

### UPDATED: python/larch/review/review_dispatch_panel.py

- Remove explicit auto assignments from dynamic Cursor reviewer rows.
- Record `resolved_model` through the same Cursor resolution helper used by ordinary rows, with Composer 2.5 as the default.
- In `_append_static_specialist_rows`, add the Cursor equivalent of the existing resolution handling: when `slot.tool == "cursor"`, populate `resolved_model` with `_resolved_model_for_row("cursor")` if `slot.cursor_model` is absent; retain `cursor_model` only when a caller supplied an explicit override.
- Remove auto assignments from any forced plan-fidelity Cursor row that remains reachable, and resolve its manifest model through the standard Cursor chain.
- Preserve `"plan-fidelity-forced": "architecture"` tally behavior and all slot accounting.

### UPDATED: python/larch/review/plan_review_panel.py

- Stop assigning auto to dynamic plan-review Cursor rows.
- Resolve their manifest model through the standard Cursor chain.
- Let static rows without an explicit override record Composer 2.5 as their resolved model.
- Preserve Codex difficulty routing and generic per-slot override support.

### UPDATED: python/larch/agents/_ci_launcher.py

- Delete the `args.role == "fix"` auto special case in `launch_cursor_ci_main`.
- Honor `args.model` when present. Otherwise call `resolve_model_args("cursor", with_effort=True)` so CI-recovery Cursor launches default to Composer 2.5 and still respect supported environment overrides.
- Keep conflict-resolution behavior and launcher error handling unchanged.

### UPDATED: python/larch/review/coder_runner.py

- Replace `_run_coder_cursor`’s hardcoded auto arguments with `resolve_model_args("cursor", with_effort=True)`.
- Fail through the existing unavailable-tier path if model resolution fails.
- Keep authentication, prompt wrapping, startup locking, and edit validation unchanged.

### UPDATED: python/larch/report/report_tokens_models.py

- Remove `RunRecord.cursor_auto_cost`.
- Remove the auto input, cache-read, and output fields from `DisplayRates`.
- Retain Composer and Grok lane fields and aggregate Cursor totals.

### UPDATED: python/larch/report/report_tokens_cost.py

- Delete the `("cursor", "auto")` rate row and auto display-rate environment overrides.
- Remove the auto-specific branch from `cursor_argv_from_buckets`.
- Fold legacy `model="auto"` and any other unrecognized Cursor models into the Composer token bucket. This routes them through the existing vendor-default fallback.
- Remove `--cursor-auto-*-tokens`, their parsed counters, and auto cost computation.
- Change detailed Cursor results from Composer/Grok/Auto to Composer/Grok.
- Change `has_cursor_components`, `_emit_cost_line()`, and `render_cost_line_from_args()` to require and emit the two-lane Composer/Grok contract only; a fresh detailed record with both retained lanes must not fall back to aggregate-only output because the removed auto lane is absent.
- Remove `cursor_auto_cost` assignment from `price_run()`.
- Stop emitting, parsing, or requiring `CURSOR_AUTO_COST`.
- Preserve the current surcharged Composer rates and the Grok 4.5 rate row byte-for-byte.
- Keep aggregate-only legacy pricing behavior unchanged.

### UPDATED: python/larch/report/report_tokens_render.py

- Change Cursor lane completeness checks and summaries to use Composer and Grok only.
- Remove the `Cursor Auto` vendor row, trend, rate line, and cached JSON field.
- Preserve aggregate-only rendering when old records lack the current lane split.

### UPDATED: python/larch/report/final_report.py

- Stop reading and forwarding `CURSOR_AUTO_COST`.
- Keep Composer and Grok cost fields optional when model-level token data is unavailable.
- Continue ignoring stale, unknown keys from historical cost text.
- Keep legacy `model="auto"` token-report buckets accepted through the revised cost bucketing path.

### UPDATED: python/larch/git/pr_body.py

- Remove auto token CLI arguments and `cursor_auto_cost` state.
- Render the detailed Cursor segment as Composer and Grok only.
- Fall back to the aggregate Cursor amount when either current component is unavailable.
- Ignore stale `CURSOR_AUTO_COST` input rather than failing old run summaries.

### UPDATED: skills/implement/SKILL.md

- Replace the Step 5 tier banner’s Cursor auto wording with Cursor Composer 2.5 wording.
- Audit associated script and Python emitters of that banner so no stale variant remains.
- Do not change Bash fences, launcher commands, tier counts, Codex models, or review-loop behavior.

### UPDATED: skills/shared/topology.tsv

- Replace the Cursor/auto topology label with the current Cursor/Composer 2.5 description.
- Preserve row keys, authority paths, and panel counts.

### REWRITTEN: docs/topology.md

- Regenerate with `python3 python/cli.py generate topology-docs` after updating `skills/shared/topology.tsv`.
- Verify the generated file contains no Cursor/auto label and no unrelated projection changes.

### UPDATED: docs/review-agents.md

- Replace per-slot auto and difficulty-matrix wording with Composer 2.5 default resolution.
- Preserve panel shapes, Codex tier models, no-fallback behavior, voting rules, and round caps.

### UPDATED: docs/external-reviewers.md

- Update plan-review, code-review, review-fix, and related Cursor role descriptions to Composer 2.5.
- Keep Grok 4.5 implementation routing and all non-Cursor role descriptions unchanged.

### UPDATED: docs/installation-and-setup.md

- Replace reviewer-panel references and examples that pin Cursor slots to `auto` with Composer 2.5 default-resolution wording.
- Explain that a caller may still provide an explicit per-slot `cursor_model` override through the retained generic plumbing.
- Keep installation flow, panel shape, and non-Cursor setup guidance unchanged.

### UPDATED: docs/configuration-and-permissions.md

- Update CI-recovery and other fixer-routing prose from Cursor auto to Composer 2.5.
- Replace the `LARCH_CURSOR_MODEL` auto example with Composer 2.5 default-resolution guidance.
- Update reviewer-panel pinning prose so it no longer describes per-slot Cursor auto; retain documentation of supported explicit model overrides.
- Preserve the documented Codex and Claude fallback order.

### UPDATED: python/tests/core/test_external_role_defaults.py

- Assert reviewer Cursor slots have no forced model override.
- Assert their effective default remains `CURSOR_DEFAULT_MODEL`.
- Update role documentation expectations without changing voter or Grok assertions.

### UPDATED: python/tests/agents/test_external_dispatch.py

- Update static and dynamic reviewer manifest expectations to Composer 2.5.
- Use a neutral sentinel model instead of `"auto"` in tests that specifically validate generic per-slot override plumbing.
- Verify both static and dynamic Cursor rows record `resolved_model="composer-2.5"` when no override is supplied, while omitted `cursor_model` remains absent unless explicitly supplied.
- Preserve forced plan-fidelity tally assertions.

### UPDATED: python/tests/agents/test_collect_results.py

- Replace `"auto"` cursor-model fixtures with a neutral explicit-model sentinel.
- Continue proving that generic outer-launcher cursor model metadata is parsed and forwarded unchanged.

### UPDATED: python/tests/agents/test_launch_review.py

- Replace `--cursor-model auto` fixtures and `MODEL=auto` expectations with a neutral explicit-model sentinel.
- Preserve generic launch-review override-plumbing coverage without retaining a forbidden Cursor-auto example.

### UPDATED: python/tests/review/test_plan_review_panel.py

- Assert dynamic Cursor plan-review rows resolve to Composer 2.5 without an explicit override.
- Keep coverage for Codex model roles, render failures, and slot manifests.

### UPDATED: python/tests/review/test_review_pipeline.py

- Update static, dynamic, TRIVIAL, and plan-review Cursor manifest assertions that currently expect auto.
- Assert no default `cursor_model` pin is emitted when unset and that `resolved_model` records Composer 2.5 through standard resolution.
- Use neutral explicit-model sentinels where this suite tests generic override propagation.
- Preserve panel-shape, role, tally, and non-Cursor routing assertions.

### UPDATED: python/tests/agents/test_agents.py

- Extend the existing Cursor CI launcher test to capture model resolution for `role="fix"`.
- Assert the launcher requests the standard Cursor model arguments and launches with `--model composer-2.5`.
- Retain explicit `--model` override coverage and conflict-role behavior.

### UPDATED: python/tests/review/test_review_and_fix.py

- Add focused `_run_coder_cursor` coverage for standard model resolution.
- Assert the review-fix Cursor command uses Composer 2.5 by default and still follows the existing failure path when model resolution fails.

### UPDATED: python/tests/report/test_report_tokens_cost.py

- Replace the auto rate-row test with assertions that no `("cursor", "auto")` row exists and `rate_row("cursor", model="auto")` returns the Composer default row.
- Update detailed token-cost tests to cover Composer and Grok only.
- Add a legacy `BUCKETS_cursor_by_model["auto"]` case that is folded into Composer pricing without warnings.
- Remove auto flags, environment-rate fields, KVs, and cost-record expectations.
- Assert fresh detailed Composer/Grok records satisfy the two-lane completeness contract without requiring an auto cost.
- Assert Composer surcharge values and Grok 4.5 rates remain unchanged.

### UPDATED: python/tests/report/test_report_tokens_render.py

- Update golden and focused output expectations to show only Composer and Grok Cursor lanes.
- Remove auto trend, vendor row, rate text, and cache-field assertions.
- Keep legacy aggregate-only and mixed-record fallback coverage.
- Add coverage that a fresh two-lane Composer/Grok record renders detailed output rather than falling back due to a missing removed lane.

### UPDATED: python/tests/report/test_final_report.py

- Remove `cursor_auto_cost` expectations.
- Assert detailed reports expose Composer and Grok costs only.
- Add or retain coverage that old auto model buckets price as Composer while malformed model detail still falls back safely.

### UPDATED: python/tests/git/test_pr_body.py

- Update detailed Cursor summary fixtures and assertions to the two-lane Composer/Grok format.
- Remove auto token-argument and cost-field expectations.
- Preserve aggregate fallback and total-cost invariance tests.
- Add a stale `CURSOR_AUTO_COST` input case if existing lenient parsing coverage does not already prove that unknown historical KVs are ignored.

## Edge cases

- An explicit `LARCH_CURSOR_MODEL` or plugin option must still override Composer 2.5 where standard model resolution applies.
- A caller-provided per-slot `cursor_model` must still pass through unchanged. Tests should use a non-auto sentinel.
- Every Cursor lane manifest, including static specialist rows, must record its effective `resolved_model`; defaulted rows must record `composer-2.5`.
- Historical token reports may contain `model="auto"`. Count those tokens in the Composer bucket and price them with the existing Composer row.
- Historical cost text may contain `CURSOR_AUTO_COST`. Ignore the stale key without requiring a migration.
- Fresh detailed Cursor cost records require Composer and Grok components only; they must not require the removed auto component.
- Aggregate-only Cursor records must continue rendering without a lane breakdown.
- Mixed Composer and Grok reports must keep their separate costs and correct aggregate total.
- Do not interpret unrelated terms such as auto-merge, auto-approve, dialectic categories, or other non-Cursor uses of `auto` as Cursor model references.

## Failure modes

- Removing the constant before all producers are updated can cause import failures. Remove consumers and the constant in the same change.
- Leaving one static, dynamic, or forced manifest producer unchanged can omit or misreport `resolved_model` relative to the model actually launched.
- Removing only the rate row while retaining auto token flags or a three-lane completeness requirement can silently misattribute totals or force fresh detailed reports into aggregate fallback.
- Requiring the new two-field schema from historical committed records can suppress aggregate reports. Keep old readers tolerant and use aggregate fallback.
- Leaving installation or configuration examples unchanged can direct operators to an unsupported Cursor model mode.
- Editing adjacent model tables can accidentally change Grok 4.5 rates or MODERATE coder routing. Add focused preservation assertions and inspect the final diff.
- Hand-editing `docs/topology.md` can drift from its TSV source. Regenerate it through the canonical command.

## Testing strategy

1. Run focused Python tests for the changed runtime and report surfaces:
   - `python3 -m pytest python/tests/core/test_external_role_defaults.py`
   - `python3 -m pytest python/tests/agents/test_external_dispatch.py python/tests/agents/test_collect_results.py python/tests/agents/test_launch_review.py python/tests/agents/test_agents.py`
   - `python3 -m pytest python/tests/review/test_review_pipeline.py python/tests/review/test_plan_review_panel.py python/tests/review/test_review_and_fix.py`
   - `python3 -m pytest python/tests/report/test_report_tokens_cost.py python/tests/report/test_report_tokens_render.py python/tests/report/test_final_report.py`
   - `python3 -m pytest python/tests/git/test_pr_body.py`
2. Regenerate topology docs, then run the topology generator and rule-path tests.
3. Run linters only for changed files using the repository’s documented focused commands. Then run `make py-lint` and `make py-test` as the acceptance sweep.
4. Run targeted repository-root acceptance checks:
   - `rg -n "CURSOR_AUTO_MODEL|LARCH_CURSOR_AUTO_" docs/ skills/ scripts/ python/ agents/ README.md` returns no matches.
   - `rg -in "cursor[[:space:][:punct:]]*auto|auto[[:space:][:punct:]]*cursor|cursor-auto|cursor/auto" docs/ skills/ scripts/ python/ agents/ README.md` returns no matches.
   - Inspect `docs/installation-and-setup.md` and `docs/configuration-and-permissions.md` specifically to confirm no reviewer-panel auto pinning or `LARCH_CURSOR_MODEL` auto example remains.
   - Search Cursor model producers and manifest assertions narrowly, rather than requiring all `auto` literals in `python/larch/` to disappear: verify no production `cursor_model` assignment, Cursor launcher argument, pricing row, display field, or Cursor-specific environment variable selects auto. Allow only the intentional legacy compatibility test fixtures and unknown-model fallback coverage.
5. Verify the retained Grok surfaces with focused assertions and a final diff inspection:
   - `("cursor", "grok-4.5")` rate row is unchanged.
   - `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY` is unchanged.
   - MODERATE coder routing remains Grok 4.5.
   - Grok token flags and Composer surcharge values are unchanged.
6. Confirm no committed run logs were modified and `retro_fix_cursor` was not run.

difficulty: HARD
mechanical_churn: false
oversize_override: operator
diff_lines: 480
