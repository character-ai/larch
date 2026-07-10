## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

Route `/implement` Step 2 to Cursor with `grok-4.5` only when the **effective** difficulty is MODERATE. Keep TRIVIAL and HARD Codex-first, preserve explicit coder and Cursor-model overrides, and price Cursor usage by model so grok-4.5 is not charged at the Composer Teams rate.

1. Add difficulty-keyed coder-tool and Cursor-model maps as the configuration source of truth.
2. Centralize effective Step 2 difficulty resolution in the existing calibration module so bootstrap and dispatch use identical override-first precedence and normalization.
3. Make bootstrap select the implicit coder from the effective difficulty while preserving explicit `--coder` behavior and registry fallback.
4. Forward the effective difficulty to Cursor, select `grok-4.5` for MODERATE Cursor launches, and retain environment/plugin model override precedence.
5. Add the grok-4.5 rate and model-aware Cursor token splitting while preserving the aggregate `CURSOR_COST` contract.
6. Make final-report token conversion call the shared Cursor token-argv helper so final reports price by-model Cursor buckets correctly without introducing per-model PR-summary display or cost-KV plumbing.
7. Update the Step 2 routing harness and focused tests. Do not regenerate topology artifacts: `implement.step2_coder` is not a topology TSV row.

## Files to modify/create

### UPDATED: python/larch/core/config.py

- Add `CODER_TOOL_ORDER_BY_DIFFICULTY: Final[dict[str, tuple[str, ...]]]`:
  - TRIVIAL: `("codex", "cursor", "claude")`
  - MODERATE: `("cursor", "codex", "claude")`
  - HARD: `("codex", "cursor", "claude")`
- Add `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY: Final[dict[str, str]]`:
  - MODERATE: `"grok-4.5"`
  - TRIVIAL and HARD: `CURSOR_DEFAULT_MODEL`
- Do not change `CURSOR_DEFAULT_MODEL`, `CURSOR_AUTO_MODEL`, Codex difficulty mappings, the registry default order, or non-implement roles.
- Update the `implement.step2_coder` `doc_fallback` text to describe Cursor-first MODERATE routing and Codex-first TRIVIAL/HARD routing.

### UPDATED: python/larch/calibration/difficulty.py

- Add an import-safe shared `resolve_step2_effective_difficulty(tmpdir)` resolver in the existing difficulty authority.
- Move the existing Step 2 resolution behavior from `dispatch_step2.py` into this resolver rather than creating a new `larch.core.difficulty` module.
- Preserve dispatch precedence exactly:
  1. a valid `DIFFICULTY_OVERRIDE` from `run-flags.sh`;
  2. the persisted design difficulty prior;
  3. an empty/invalid result when neither source normalizes to a valid tier.
- Keep tier normalization and malformed/unreadable-file behavior fail-closed so callers can retain their existing fallback behavior.

### UPDATED: python/larch/state/bootstrap.py

- Import `resolve_step2_effective_difficulty` from `larch.calibration.difficulty`.
- In `_phase_coder`, keep explicit coder handling before implicit-order selection.
- For no explicit `--coder`, resolve the effective Step 2 difficulty and look up `CODER_TOOL_ORDER_BY_DIFFICULTY`.
- Fall back to `external_defaults.tool_order("implement.step2_coder")` when the effective tier is missing, invalid, or absent from the map.
- Preserve existing availability checks, Claude fallback marker behavior, and explicit-unavailable warning recording.
- Ensure an explicit difficulty override takes precedence over a conflicting persisted difficulty prior, matching dispatch behavior.

### UPDATED: python/larch/implement/dispatch_step2.py

- Import and use `resolve_step2_effective_difficulty` from `larch.calibration.difficulty`; remove the local Step 2 effective-difficulty implementation.
- Extend `_launcher_args` so both Codex and Cursor receive `--difficulty` whenever `DispatchState.difficulty` is set.
- Update `_resolve_implement_rater_model` so Cursor resolves its caller default from `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY` for the effective tier, then falls back to `CURSOR_DEFAULT_MODEL`.
- Preserve Cursor session and plugin-option model override precedence.

### UPDATED: python/larch/agents/_ci_launcher.py

- In `launch_cursor_implement_main`, derive the default Cursor model from `config.CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY` using normalized `args.difficulty`; use `CURSOR_DEFAULT_MODEL` for missing or invalid difficulty.
- Pass that value to `resolve_model_args` as `default_model`.
- Keep existing usage recording so the resolved `model=<...>` continues to populate `BUCKETS_cursor_by_model`.
- Leave Cursor auth, workspace/config isolation, prompt construction, retry behavior, and Auto-mode launchers unchanged.

### UPDATED: python/larch/agents/_launch_failure.py

- Make `resolve_model_args` honor caller-supplied `default_model` for Cursor, matching the existing Codex default-model contract.
- Preserve this precedence:
  1. `LARCH_CURSOR_MODEL`
  2. `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL`
  3. caller-supplied `default_model`
  4. `CURSOR_DEFAULT_MODEL`
- Retain blank-value and control-character validation.

### UPDATED: python/larch/report/report_tokens_cost.py

- Add `CURSOR_GROK_4_5_BASE: Final = {"input": 2.00, "cache_read": 0.50, "output": 6.00}`.
- Add `("cursor", "grok-4.5")` to `DEFAULT_RATE_TABLE_PER_M` with those direct rates and no Teams surcharge.
- Keep the Composer, Auto, and Codex rows unchanged.
- Extend `_FLAG_NAMES` with dedicated grok-4.5 Cursor input, cache-read, and output flags.
- Update `_cursor_argv` to split `BUCKETS_cursor_by_model` into:
  - Auto tokens, which remain in the existing zero-priced Auto bucket;
  - `grok-4.5` tokens, emitted through the dedicated grok flags;
  - all other non-Auto Cursor models, emitted through the existing surcharged Composer bucket.
- Ensure callers that only have aggregate Cursor buckets retain the existing Composer-compatible fallback behavior.
- Extend pricing input parsing and calculation so dedicated grok token counters contribute at the grok-4.5 rate while existing Composer counters continue to contribute at the Composer rate.
- Preserve the existing aggregate `CURSOR_COST` and total-cost output contract; do not add per-model Cursor component-cost KVs or new display-rate fields.

### UPDATED: python/larch/report/final_report.py

- Add a private `_cursor_token_argv` helper parallel to `_codex_token_argv`.
- Have `_cursor_token_argv` call the shared `report_tokens_cost._cursor_argv` conversion using the report record’s aggregate Cursor bucket and `BUCKETS_cursor_by_model` data, rather than duplicating Cursor model-splitting logic.
- Replace the existing inline Cursor branch in `_token_argv_from_report` with `_cursor_token_argv`.
- Preserve aggregate-only Cursor compatibility and existing final-report fields, including the single aggregate `CURSOR_COST`.
- Do not add Cursor component-cost fields or alter PR-summary rendering inputs.

### UPDATED: scripts/test-implement-step2-routing.sh

- Keep the registry assertion that `implement.step2_coder` remains `ORDER=codex,cursor,claude`.
- Replace the old bootstrap source pin for unconditional `external_defaults.tool_order("implement.step2_coder")` with assertions that bootstrap:
  - imports and uses the shared calibration difficulty resolver;
  - consults `CODER_TOOL_ORDER_BY_DIFFICULTY`;
  - retains registry-order fallback for invalid or absent effective difficulty.
- Assert `dispatch_step2.py` imports the resolver from `larch.calibration.difficulty` rather than defining a second Step 2 resolver.

### MAY_UPDATE: docs/agents.md

- Update only if it states the Step 2 implicit coder order as unconditional Codex-first.

### UPDATED: python/tests/calibration/test_difficulty.py

- Cover `resolve_step2_effective_difficulty` normalization and source precedence.
- Assert a valid `DIFFICULTY_OVERRIDE` beats a conflicting persisted design prior.
- Assert missing, malformed, unreadable, and invalid override/prior inputs fail closed without producing an effective tier.

### UPDATED: python/tests/state/test_bootstrap.py

- Cover implicit MODERATE routing with Cursor and Codex available: Cursor is selected.
- Cover MODERATE fallback when Cursor is unavailable: Codex is selected.
- Cover a valid difficulty override conflicting with the persisted prior: the override determines the implicit coder order.
- Assert TRIVIAL and HARD use their configured Codex-first order.
- Assert missing, malformed, and invalid effective difficulty retain the Codex-first registry fallback.
- Assert explicit `--coder codex`, explicit `--coder cursor`, and self-implement behavior override difficulty-keyed implicit routing.

### UPDATED: python/tests/implement/test_implement_dispatch.py

- Cover the shared effective-difficulty resolver through dispatch behavior, including override-before-prior precedence.
- Assert `_launcher_args` forwards difficulty for both Cursor and Codex.
- Assert MODERATE Cursor launch argv includes `--model grok-4.5`.
- Assert TRIVIAL, HARD, missing, and invalid difficulty use the `composer-2.5` default.
- Assert Cursor environment and plugin-option overrides beat the MODERATE `grok-4.5` caller default.
- Assert rater attribution resolves to `grok-4.5` for MODERATE Cursor.
- Retain Codex difficulty regression coverage.

### UPDATED: python/tests/agents/test_external_dispatch.py

- Update Step 2 role-routing coverage to include effective difficulty context.
- Verify missing or invalid effective difficulty retains the `implement.step2_coder` registry fallback.

### UPDATED: python/tests/agents/test_agents.py

- Add Cursor `default_model` coverage in `resolve_model_args`.
- Verify environment and plugin options override the caller default.
- Verify caller default overrides `CURSOR_DEFAULT_MODEL` when no higher-precedence override exists.
- Retain fail-closed coverage for blank and invalid model values.

### UPDATED: python/tests/report/test_report_tokens_cost.py

- Assert the `("cursor", "grok-4.5")` rate row is input `2.00`, cache-read `0.50`, and output `6.00`, with no Teams surcharge.
- Assert Composer rates remain unchanged.
- Assert `_cursor_argv` emits grok-4.5 token counters separately from Composer counters and preserves Auto handling.
- Assert all new grok flags are accepted by token-cost argument parsing.
- Assert mixed grok-4.5 and Composer model buckets produce the correct aggregate `CURSOR_COST` and total cost.
- Assert aggregate-only Cursor buckets preserve the existing Composer-compatible fallback.

### UPDATED: python/tests/report/test_final_report.py

- Cover final-report conversion of mixed `BUCKETS_cursor_by_model` usage through `_cursor_token_argv` into separate grok-4.5 and Composer-priced token arguments.
- Assert final-report pricing yields the correct aggregate `CURSOR_COST` for mixed model buckets.
- Cover compatibility behavior for aggregate-only Cursor buckets.
- Assert no new Cursor component-cost fields are required for final-report or PR-summary compatibility.

## Edge cases

- Missing, malformed, unreadable, or invalid override/prior data produces no effective tier and retains the Codex-first registry order.
- A valid difficulty override beats a conflicting persisted difficulty prior in both bootstrap and dispatch.
- MODERATE with Cursor unavailable falls through to Codex using the existing Codex model selection.
- Explicit `--coder codex` at MODERATE remains Codex; explicit `--coder cursor` remains Cursor.
- `LARCH_CURSOR_MODEL` and `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL` override the difficulty-selected Cursor default.
- TRIVIAL and HARD remain Codex-first and use the existing Cursor default if Cursor is explicitly selected or reached through availability fallback.
- Cursor Auto tokens remain unaffected and retain zero-cost treatment.
- Unknown non-Auto Cursor models remain priced through the existing Composer-compatible, surcharged fallback.
- Old reports without by-model Cursor buckets remain renderable and retain aggregate Cursor-cost behavior.

## Failure modes

- If bootstrap and dispatch use different difficulty precedence, `/implement --difficulty` can select one coder lane and launch a model for another tier.
- If the resolver is added outside `larch.calibration.difficulty`, existing imports can leave two difficulty authorities with divergent behavior.
- If Cursor does not receive `--difficulty`, a MODERATE Cursor launch can silently use `composer-2.5`.
- If grok-4.5 tokens are aggregated into Composer flags, MODERATE Cursor costs are overstated.
- If new grok flags are absent from `_FLAG_NAMES` or pricing helpers, model-aware reports can fail parsing or omit grok usage from aggregate Cursor cost.
- If final-report retains a separate inline Cursor argv branch, it can ignore `BUCKETS_cursor_by_model` and price grok-4.5 usage at Composer rates.
- If the routing harness keeps its unconditional registry-order source assertion, the intended bootstrap refactor fails CI despite preserving registry fallback.

## Testing strategy

- Run focused tests for:
  - `python/tests/calibration/test_difficulty.py`
  - `python/tests/state/test_bootstrap.py`
  - `python/tests/implement/test_implement_dispatch.py`
  - `python/tests/agents/test_external_dispatch.py`
  - `python/tests/agents/test_agents.py`
  - `python/tests/report/test_report_tokens_cost.py`
  - `python/tests/report/test_final_report.py`
  - `scripts/test-implement-step2-routing.sh`
- Run the repository’s relevant Python lint target only for changed Python modules and the relevant shell lint/harness target for the changed routing script.
- Verify the routing matrix:
  - MODERATE with Cursor available;
  - MODERATE with Cursor unavailable;
  - MODERATE override conflicting with prior;
  - TRIVIAL and HARD with both tools available;
  - explicit Codex and Cursor selections.
- Verify mixed Cursor model buckets produce grok-4.5-priced and Composer-priced token arguments, an accurate aggregate `CURSOR_COST`, and matching final-report cost output.

difficulty: MODERATE
diff_added: 340
diff_deleted: 35
mechanical_churn: false
oversize_override: operator
diff_lines: 375
