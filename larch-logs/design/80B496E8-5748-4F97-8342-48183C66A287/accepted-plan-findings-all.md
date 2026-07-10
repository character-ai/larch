### FINDING_1: DisplayRates fields are assigned to the wrong module
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Pragmatic, Cursor-dyn-Routing Attribution Auditor
- **Severity**: major
- **Concern**: The plan assigns new `DisplayRates` grok-4.5 fields to `report_tokens_cost.py`, but the dataclass is defined in `report_tokens_models.py`. Implementing only the listed changes can leave the pricing stack unable to construct or access the new fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Move the DisplayRates field additions to `### UPDATED: python/larch/report/report_tokens_models.py` (optional defaulted grok rate fields), keep `display_rates()`/`_pricing_from_counts` changes in `report_tokens_cost.py`, and add a field-presence test if needed.
  - From Codex-Arch: Add python/larch/report/report_tokens_models.py to the firm update list and add the three grok-4.5 fields there, preserving defaults or updating every constructor consistently
  - From Codex-Pragmatic: Add python/larch/report/report_tokens_models.py to the UPDATED files and specify the DisplayRates field changes there
  - From Cursor-dyn-Routing Attribution Auditor: Add ### UPDATED: python/larch/report/report_tokens_models.py for grok rate fields (defaults like cursor_auto_*). Extend test_report_tokens_models.py field assertions.


### FINDING_2: Bootstrap coder routing ignores difficulty overrides
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Routing Attribution Auditor
- **Severity**: major
- **Concern**: `_phase_coder` keys coder order only from `difficulty-prior.env`, while dispatch resolves the effective tier using the difficulty override first. An explicit `/implement --difficulty` can therefore make bootstrap select a coder order inconsistent with the model launched by Step 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Resolve effective tier the same way as dispatch_step2._resolve_step2_difficulty (st.opts.difficulty_override or run-flags, then difficulty-prior.env) before map lookup. Add test_bootstrap coverage for override vs prior.
  - From Cursor-Pragmatic: In _phase_coder resolve tier with the same precedence as dispatch _resolve_step2_difficulty (DIFFICULTY_OVERRIDE from run-flags.sh then difficulty-prior.env) before CODER_TOOL_ORDER_BY_DIFFICULTY lookup; add a bootstrap test for override beats prior
  - From Cursor-dyn-Routing Attribution Auditor: Reuse the same effective-tier resolver as dispatch (st.opts.difficulty_override or run-flags.sh, then difficulty-prior.env) before CODER_TOOL_ORDER_BY_DIFFICULTY lookup. Add test_bootstrap coverage for override vs prior.


### FINDING_4: The plan references a nonexistent cost-computation symbol
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The plan names `compute_run_cost_from_argv`, which does not exist in the referenced pricing module. This can misdirect implementation; the relevant logic is in the existing token-cost and pricing helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Point plan steps at token_cost_from_args / _FLAG_NAMES / _pricing_from_counts and mirror the codex-mini flag pattern for grok counters.


### FINDING_5: Final-report pricing does not route Cursor buckets by model
- **Reviewer(s)**: Codex-Innovation, Cursor-Requirements, Codex-Requirements, Codex-dyn-Routing Attribution Auditor
- **Severity**: major
- **Concern**: The final-report token-argv path aggregates `BUCKETS_cursor` and ignores `BUCKETS_cursor_by_model`. A grok-4.5 run can therefore be priced using composer-2.5 rates, and the final report cannot propagate separate model costs to PR summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update `final_report.py` to use the model-aware Cursor argv conversion, extract the grok-4.5 cost field, and pass it through to `render_run_summary`. Add coverage for final-report pricing and rendering with both Cursor models.
  - From Cursor-Requirements: Mirror _codex_token_argv: add _cursor_token_argv that routes grok-4.5 to new grok flags and other non-auto models to composer flags; call it from _token_argv_from_report. Parse any new per-model Cursor cost KVs in _final_report_token_fields for render_run_summary.
  - From Codex-Requirements: Include `python/larch/report/final_report.py` in the plan and route its Cursor bucket conversion through the same model-aware helper or emit separate grok and composer token flags; add coverage for final-report pricing and PR-summary propagation
  - From Codex-dyn-Routing Attribution Auditor: This feature's report path must call the model-aware Cursor argv split, or reproduce its grok-4.5 versus composer-2.5 and Auto partition before invoking token_cost_from_args.


### FINDING_6: Step 2 routing harness is not updated for difficulty-keyed ordering
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The Step 2 routing harness is absent from the plan even though the planned bootstrap change removes the existing `external_defaults.tool_order("implement.step2_coder")` call that the harness asserts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add ### UPDATED: scripts/test-implement-step2-routing.sh to assert CODER_TOOL_ORDER_BY_DIFFICULTY lookup with registry fallback instead of the old tool_order substring pin


### FINDING_8:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/report/report_tokens_cost.py:436-463; python/larch/git/pr_body.py:656-709
- **Concern**: [SCOPE-REDUCTION] Drop topology.tsv/docs/topology.md regeneration steps; grok pricing argv contract is incomplete in the plan. Scenario: `skills/shared/topology.tsv` is a hand-maintained panel projection (no `implement.step2_coder` row); `generate topology-docs` only renders `docs/topology.md` from that TSV, not from `ROLE_DEFAULTS`. Those steps add churn without updating Step 2 docs. Separately, splitting grok tokens in `_cursor_argv` requires matching `--cursor-grok-4-5-*` entries in `_FLAG_NAMES`, `_pricing_from_counts`, and (for run summaries) `pr_body._TOKEN_COST_ARGS` plus `render_run_summary_main` KV parsing; the plan names `_cursor_cost_segment` and `compute_run_cost_from_argv` but omits this Codex-mini-style plumbing, so grok-priced runs can hit unknown-flag failures or stay aggregate-only in PR/summary cost lines.
- **Proposed resolution**: Remove `### UPDATED: docs/topology.md` and `### UPDATED: skills/shared/topology.tsv` unless a real topology row changes. Extend the plan to mirror the Codex mini split end-to-end: new grok flags in `_FLAG_NAMES` and `_cursor_argv`, grok rate fields in `_pricing_from_counts`/`token_cost_from_args` output (e.g. `CURSOR_GROK_4_5_COST`), `pr_body._TOKEN_COST_ARGS` + `render_run_summary_main` parsing, then `_cursor_cost_segment`/`render_run_summary`.


### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/references/step2-dispatch.md:92
- **Concern**: [SCOPE-REDUCTION] Drop firm pr_body.py cursor cost segment. Scenario: Issue scope is MODERATE coder routing plus grok-4.5 rate row. Correct _cursor_argv and _pricing_from_counts make CURSOR_COST accurate without PR/final-report per-model display work.
- **Proposed resolution**: Remove python/larch/git/pr_body.py from firm UPDATED list; keep aggregate CURSOR_COST line unchanged.


### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/shared/topology.tsv; docs/topology.md
- **Concern**: [SCOPE-REDUCTION] topology.tsv regeneration step is mis-aimed. Scenario: There is no ROLE_DEFAULTS to topology.tsv generator; topology.md is generated from topology.tsv via python3 python/cli.py generate topology-docs and implement.step2_coder is not a tsv row today
- **Proposed resolution**: Drop the mandatory skills/shared/topology.tsv edit unless a row actually changes; keep doc_fallback in config.py and skip topology artifacts unless a harness requires them ## Findings ### 1. Bootstrap tier source must match dispatch (correctness) `_phase_coder` in `bootstrap.py` currently always uses `external_defaults.tool_order("implement.step2_coder")`. The plan switches to `CODER_TOOL_ORDER_BY_DIFFICULTY` keyed on `difficulty-prior.env` only. Dispatch already resolves Step 2 difficulty with override-first logic in `_resolve_step2_difficulty`: def _resolve_step2_difficulty(tmpdir: Path) -> str: override = larch_io.read_kv(path=tmpdir / "run-flags.sh", key="DIFFICULTY_OVERRIDE", default="", first_match=True, on_error_default=True) normalized_override = difficulty.normalize_tier(override) if normalized_override: return normalized_override prior = _read_design_difficulty_prior(tmpdir) return difficulty.normalize_tier(prior) If bootstrap ignores `DIFFICULTY_OVERRIDE`, operator `/implement --difficulty` can pick the wrong implementer or pair Cursor with the wrong default model. Bootstrap should reuse the same tier resolution before looking up `CODER_TOOL_ORDER_BY_DIFFICULTY`. ### 2. CI harness gap (risk-integration) `scripts/test-implement-step2-routing.sh` is in `test-harnesses-4` and pins the old bootstrap contract: role_out="$(python3 "$REPO_ROOT/python/cli.py" external-defaults role --role implement.step2_coder)" printf '%s\n' "$role_out" | grep -Fq 'KIND=waterfall' || fail "step2 coder role kind missing" printf '%s\n' "$role_out" | grep -Fq 'ORDER=codex,cursor,claude' || fail "step2 coder registry order changed" assert_contains "$BOOTSTRAP_SH" 'external_defaults.tool_order("implement.step2_coder")' "implicit registry-backed coder preference" The plan does not list this script. Registry `ORDER=codex,cursor,claude` should stay, but the bootstrap substring assertion will fail after the refactor. ### 3. PR cost breakdown plumbing incomplete (correctness) The plan adds `_cursor_cost_segment` in `pr_body.py` mirroring Codex split, but `final_report.py` only forwards aggregate `CURSOR_COST`: return { "cost_unavailable": False, "total_cost": total_cost, "claude_cost": larch_io.kv_value(text=cost_kv, key="CLAUDE_COST", default="N/A"), "codex_cost": larch_io.kv_value(text=cost_kv, key="CODEX_COST", default="N/A"), "codex_gpt_5_5_cost": larch_io.kv_value(text=cost_kv, key="CODEX_GPT_5_5_COST", default="N/A"), "codex_gpt_5_4_mini_cost": larch_io.kv_value(text=cost_kv, key="CODEX_GPT_5_4_MINI_COST", default="N/A"), "cursor_cost": larch_io.kv_value(text=cost_kv, key="CURSOR_COST", default="N/A"), Without new cost KVs from `token_cost_from_args` and matching reads in `final_report.py` / `render_run_summary_main`, the PR cost line cannot show grok-4.5 vs composer-2.5 even after `_cursor_argv` splits token buckets. ### 4. Topology regeneration is unnecessary scope (architecture) The plan calls for regenerating `skills/shared/topology.tsv` from `ROLE_DEFAULTS`, but the repo only generates `docs/topology.md` from the tsv (`python3 python/cli.py generate topology-docs`). `implement.step2_coder` is not present in `topology.tsv` today; the Step 2 order lives in `config.py` `doc_fallback` and `docs/external-reviewers.md`. Updating the tsv is likely no-op churn unless a row is intentionally added.


### FINDING_1: Shared difficulty resolver targets nonexistent module
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The plan assigns the shared Step 2 effective-difficulty resolver to `python/larch/core/difficulty.py`, but the existing difficulty implementation lives in `python/larch/calibration/difficulty.py`, which bootstrap and dispatch already import. Implementing the listed path could create a second authority, leave callers unchanged, or cause bootstrap and dispatch to diverge on precedence and normalization behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add resolve_step2_effective_difficulty(tmpdir) to python/larch/calibration/difficulty.py (move _resolve_step2_difficulty from dispatch_step2.py). Update the plan path and imports in bootstrap.py and dispatch_step2.py.
  - From Cursor-Innovation: Change the firm plan item to update python/larch/calibration/difficulty.py and python/tests/calibration/test_difficulty.py, then import the shared resolver from larch.calibration.difficulty in bootstrap and dispatch.
  - From Codex-Innovation: Place the shared resolver in the existing `python/larch/calibration/difficulty.py`, or explicitly update both import sites and define the new module's complete ownership and compatibility contract.
  - From Cursor-Pragmatic: Retarget the plan to `python/larch/calibration/difficulty.py`: add a shared Step 2 effective-difficulty resolver there and have bootstrap plus `dispatch_step2.py` import it.
  - From Cursor-Requirements: Retarget the firm change to `python/larch/calibration/difficulty.py`: add an import-safe `resolve_step2_effective_difficulty(tmpdir)` there and switch bootstrap plus dispatch to import it from `larch.calibration.difficulty`.
  - From Codex-Requirements: Move the resolver change to `python/larch/calibration/difficulty.py` and keep both callers on that existing module


### FINDING_3: Final report may retain duplicated or incorrect Cursor argv assembly
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: minor
- **Concern**: The final-report plan does not concretely replace the existing Cursor argv branch, which aggregates `BUCKETS_cursor` and ignores `BUCKETS_cursor_by_model`. A separate or unchanged implementation can continue pricing grok-4.5 usage at Composer rates and drift from the shared Cursor pricing helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require final_report to build Cursor argv via report_tokens_cost._cursor_argv (or token_cost_argv) from the enriched report record, not a second inline cursor branch.
  - From Cursor-Pragmatic: Specify adding a `_cursor_token_argv` helper parallel to `_codex_token_argv` (grok-4.5, Composer, Auto split) and call it from `_token_argv_from_report`; cover it in `python/tests/report/test_final_report.py`.
  - From Cursor-Requirements: Replace the cursor block in `_token_argv_from_report` with the shared `report_tokens_cost._cursor_argv` path (via `RunRecord.raw_report` that includes `BUCKETS_cursor_by_model`, or via `token_cost_argv`), and add a final-report test with mixed grok/composer buckets asserting grok flags are emitted.


### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/git/pr_body.py
- **Concern**: [SCOPE-REDUCTION] Firm pr_body and report_tokens_render per-model Cursor display exceeds issue scope. Scenario: Issue scope is MODERATE Step 2 Cursor/grok routing plus a grok-4.5 rate row. Correct _cursor_argv and aggregate CURSOR_COST satisfy pricing; PR per-model segments and DisplayRates render splits are optional display work (~100+ lines).
- **Proposed resolution**: Drop firm updates to pr_body.py and report_tokens_render.py and their focused tests. Keep report_tokens_cost argv/pricing split and final_report argv routing only for accurate aggregate CURSOR_COST.


### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/git/pr_body.py
- **Concern**: [SCOPE-REDUCTION] Prior scope-reduction fix is incomplete: drop per-model Cursor PR-summary display plumbing. Scenario: The issue asks for MODERATE Cursor/grok routing and correct grok pricing. Accurate aggregate CURSOR_COST can ship without adding _cursor_cost_segment, PR-summary component fields, and render_run_summary parsing. Keeping those firm changes adds downstream UI churn beyond the required pricing contract.
- **Proposed resolution**: Keep model-aware token conversion and aggregate CURSOR_COST propagation where needed for correct pricing, but remove the firm pr_body.py per-model Cursor segment and component-cost display work from this plan.


### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:104-110
- **Concern**: [SCOPE-REDUCTION] The plan still makes PR-summary model-component rendering a firm part of the feature.. Scenario: The binding issue only requires MODERATE Cursor routing and a `("cursor", "grok-4.5")` rate. Pricing can preserve the aggregate `CURSOR_COST` contract after model-aware token splitting, so adding component KVs through `final_report.py` and `pr_body.py` expands the wire and display surface without being required for the requested feature.
- **Proposed resolution**: Remove the firm `final_report.py` and `python/larch/git/pr_body.py` component-cost work. Keep model-aware splitting and aggregate `CURSOR_COST` in `report_tokens_cost.py`, with focused pricing coverage.


### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/git/pr_body.py
- **Concern**: [SCOPE-REDUCTION] Round 1 accepted dropping firm `pr_body.py` per-model Cursor work; this plan still firm-updates `pr_body.py` and `test_pr_body.py` for grok/composer segments.. Scenario: Issue scope is MODERATE Step 2 routing plus a grok-4.5 rate row; accurate aggregate `CURSOR_COST` via `final_report.py` and `report_tokens_cost.py` satisfies PR cost lines without new `_cursor_cost_segment` plumbing.
- **Proposed resolution**: Drop the firm `python/larch/git/pr_body.py` and `python/tests/git/test_pr_body.py` Cursor component segments; keep aggregate `cursor_cost` fallback only. ## Findings 1. **correctness** — `python/larch/core/difficulty.py`: The plan lists a module that does not exist. Step 2 difficulty code belongs in `python/larch/calibration/difficulty.py`, which bootstrap and dispatch already use. Point the shared resolver there. 2. **architecture** — `python/larch/report/final_report.py:275-310`: The plan says to reuse model-aware Cursor argv conversion but does not name the concrete helper. Today Cursor pricing in final reports ignores `BUCKETS_cursor_by_model`. Add a `_cursor_token_argv` helper mirroring `_codex_token_argv`. 3. **risk-integration** — `python/larch/git/pr_body.py`: Prior review accepted dropping firm PR per-model Cursor splits. This plan reintroduces that work. Aggregate `CURSOR_COST` is enough for the issue scope once grok pricing lands in `report_tokens_cost.py` and final-report argv conversion is fixed.


### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/report/final_report.py:365-379; python/larch/git/pr_body.py:550-579,656-749
- **Concern**: [SCOPE-REDUCTION] The plan retains the previously accepted unnecessary final-report and PR-body component-cost expansion. Scenario: The feature only needs model-aware Cursor token pricing so grok-4.5 usage contributes to the existing aggregate CURSOR_COST at the correct rate. New component KVs, parser arguments, summary fields, and per-model PR prose add unrelated wire and presentation surface without affecting routing or aggregate cost correctness.
- **Proposed resolution**: Remove the CURSOR_GROK_4_5_COST and CURSOR_COMPOSER_2_5_COST propagation and PR rendering work. Keep the model-aware token split and existing aggregate CURSOR_COST contract.


### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/git/pr_body.py
- **Concern**: [SCOPE-REDUCTION] The plan reintroduces a firm `pr_body.py` Cursor component-cost segment after round 1 accepted dropping that surface; the binding issue only requires the grok-4.5 rate row in `report_tokens_cost.py`.. Scenario: `_cursor_argv` plus accurate aggregate `CURSOR_COST` already satisfy the stated pricing goal; PR-summary per-model plumbing adds flags, parsers, render branches, and tests with no correctness benefit.
- **Proposed resolution**: Drop the firm `pr_body.py` update and related component-cost KV propagation; keep aggregate `CURSOR_COST` rendering unchanged.


### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/report_tokens_render.py
- **Concern**: [SCOPE-REDUCTION] The plan adds a firm grok-4.5 rate display split in `report_tokens_render.py`, which the issue did not request.. Scenario: /report-tokens already shows aggregate Cursor cost; separate grok rate text is display-only churn beyond the required pricing fix.
- **Proposed resolution**: Remove the firm `report_tokens_render.py` change; rely on corrected aggregate Cursor pricing from `report_tokens_cost.py`.


### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/final_report.py:365-379; python/larch/git/pr_body.py:569-749
- **Concern**: [SCOPE-REDUCTION] The prior accepted removal of per-model PR display plumbing remains unapplied. Scenario: Model-aware token arguments can produce an accurate aggregate `CURSOR_COST` without adding component KVs and a new PR-summary presentation contract
- **Proposed resolution**: Keep model-aware final-report pricing and aggregate `CURSOR_COST`, but drop the component-cost propagation and `_cursor_cost_segment` changes


