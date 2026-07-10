### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty.py
- **Concern**: Plan targets nonexistent python/larch/core/difficulty.py for the shared Step 2 resolver. Scenario: Bootstrap already imports larch.calibration.difficulty; there is no python/larch/core/difficulty.py. Implementing the listed path can add a dead module or leave bootstrap/dispatch on divergent helpers.
- **Proposed resolution**: Add resolve_step2_effective_difficulty(tmpdir) to python/larch/calibration/difficulty.py (move _resolve_step2_difficulty from dispatch_step2.py). Update the plan path and imports in bootstrap.py and dispatch_step2.py.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/report_tokens_cost.py:652-657
- **Concern**: token_cost_from_args order tuple omits new Cursor component-cost KVs. Scenario: Plan adds CURSOR_GROK_4_5_COST and CURSOR_COMPOSER_2_5_COST to _pricing_from_counts but stdout emission is limited to the hardcoded order tuple. Component costs never reach final_report or pr_body even if computed.
- **Proposed resolution**: Extend the order sequence in token_cost_from_args to include CURSOR_GROK_4_5_COST and CURSOR_COMPOSER_2_5_COST immediately before CURSOR_COST, or the plan must drop those KVs entirely.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/final_report.py:275-310
- **Concern**: final_report duplicates Cursor argv assembly instead of reusing pricing helper. Scenario: _token_argv_from_report inlines aggregate BUCKETS_cursor flags and ignores BUCKETS_cursor_by_model. A parallel rewrite can drift from report_tokens_cost._cursor_argv and reintroduce composer-priced grok usage.
- **Proposed resolution**: Require final_report to build Cursor argv via report_tokens_cost._cursor_argv (or token_cost_argv) from the enriched report record, not a second inline cursor branch.



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/git/pr_body.py
- **Concern**: [SCOPE-REDUCTION] Firm pr_body and report_tokens_render per-model Cursor display exceeds issue scope. Scenario: Issue scope is MODERATE Step 2 Cursor/grok routing plus a grok-4.5 rate row. Correct _cursor_argv and aggregate CURSOR_COST satisfy pricing; PR per-model segments and DisplayRates render splits are optional display work (~100+ lines).
- **Proposed resolution**: Drop firm updates to pr_body.py and report_tokens_render.py and their focused tests. Keep report_tokens_cost argv/pricing split and final_report argv routing only for accurate aggregate CURSOR_COST.



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:98-109
- **Concern**: [SCOPE-REDUCTION] Remove the firm final-report and PR-summary per-model Cursor plumbing from this feature. Scenario: The issue requires MODERATE Cursor routing and the grok-4.5 rate in report_tokens_cost.py. Extending final_report.py and pr_body.py adds new component-KV contracts, compatibility branches, render logic, and tests without being required for the requested pricing calculation. It enlarges the failure surface and can create needless report-format churn.
- **Proposed resolution**: Limit the firm scope to report_tokens_cost.py, report_tokens_models.py, and the directly required rate-display path and tests. Keep aggregate CURSOR_COST accurate there. Move final_report.py, pr_body.py, and their tests to a tracked follow-up unless the originating issue explicitly requires per-model display in those surfaces.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/difficulty.py
- **Concern**: Plan targets a nonexistent difficulty module. Scenario: The repo defines difficulty helpers in python/larch/calibration/difficulty.py, while python/larch/core/difficulty.py does not exist. Implementing the shared Step 2 resolver at the planned UPDATED path can either fail immediately or create a second difficulty authority that bootstrap and dispatch do not already import.
- **Proposed resolution**: Change the firm plan item to update python/larch/calibration/difficulty.py and python/tests/calibration/test_difficulty.py, then import the shared resolver from larch.calibration.difficulty in bootstrap and dispatch.



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
- **Location**: plan.txt:26-33
- **Concern**: The shared resolver is assigned to `python/larch/core/difficulty.py`, but the existing difficulty implementation lives in `python/larch/calibration/difficulty.py`, which both bootstrap and dispatch currently import.. Scenario: An implementation that follows the listed path can create a second difficulty module or leave the existing callers unchanged. Bootstrap and dispatch may then use different normalization and file-error behavior, defeating the required single-precedence resolver.
- **Proposed resolution**: Place the shared resolver in the existing `python/larch/calibration/difficulty.py`, or explicitly update both import sites and define the new module's complete ownership and compatibility contract.



### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:104-110
- **Concern**: [SCOPE-REDUCTION] The plan still makes PR-summary model-component rendering a firm part of the feature.. Scenario: The binding issue only requires MODERATE Cursor routing and a `("cursor", "grok-4.5")` rate. Pricing can preserve the aggregate `CURSOR_COST` contract after model-aware token splitting, so adding component KVs through `final_report.py` and `pr_body.py` expands the wire and display surface without being required for the requested feature.
- **Proposed resolution**: Remove the firm `final_report.py` and `python/larch/git/pr_body.py` component-cost work. Keep model-aware splitting and aggregate `CURSOR_COST` in `report_tokens_cost.py`, with focused pricing coverage.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/difficulty.py
- **Concern**: The plan targets a nonexistent `python/larch/core/difficulty.py`; difficulty helpers live in `python/larch/calibration/difficulty.py`, which bootstrap and dispatch already import.. Scenario: Implementing the listed path adds a stray module or leaves `_resolve_step2_difficulty` duplicated; bootstrap and dispatch can still diverge on effective tier.
- **Proposed resolution**: Retarget the plan to `python/larch/calibration/difficulty.py`: add a shared Step 2 effective-difficulty resolver there and have bootstrap plus `dispatch_step2.py` import it.



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/final_report.py:275-310
- **Concern**: The final-report plan is vague about mechanics; `final_report.py` already uses a local `_codex_token_argv` helper, while Cursor still aggregates `BUCKETS_cursor` and ignores `BUCKETS_cursor_by_model`.. Scenario: A grok-4.5 MODERATE run can keep Composer-priced argv in `_final_report_token_fields` even after `report_tokens_cost._cursor_argv` is fixed, so `CURSOR_COST` stays wrong in final reports and PR summaries.
- **Proposed resolution**: Specify adding a `_cursor_token_argv` helper parallel to `_codex_token_argv` (grok-4.5, Composer, Auto split) and call it from `_token_argv_from_report`; cover it in `python/tests/report/test_final_report.py`.



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/git/pr_body.py
- **Concern**: [SCOPE-REDUCTION] Round 1 accepted dropping firm `pr_body.py` per-model Cursor work; this plan still firm-updates `pr_body.py` and `test_pr_body.py` for grok/composer segments.. Scenario: Issue scope is MODERATE Step 2 routing plus a grok-4.5 rate row; accurate aggregate `CURSOR_COST` via `final_report.py` and `report_tokens_cost.py` satisfies PR cost lines without new `_cursor_cost_segment` plumbing.
- **Proposed resolution**: Drop the firm `python/larch/git/pr_body.py` and `python/tests/git/test_pr_body.py` Cursor component segments; keep aggregate `cursor_cost` fallback only. ## Findings 1. **correctness** — `python/larch/core/difficulty.py`: The plan lists a module that does not exist. Step 2 difficulty code belongs in `python/larch/calibration/difficulty.py`, which bootstrap and dispatch already use. Point the shared resolver there. 2. **architecture** — `python/larch/report/final_report.py:275-310`: The plan says to reuse model-aware Cursor argv conversion but does not name the concrete helper. Today Cursor pricing in final reports ignores `BUCKETS_cursor_by_model`. Add a `_cursor_token_argv` helper mirroring `_codex_token_argv`. 3. **risk-integration** — `python/larch/git/pr_body.py`: Prior review accepted dropping firm PR per-model Cursor splits. This plan reintroduces that work. Aggregate `CURSOR_COST` is enough for the issue scope once grok pricing lands in `report_tokens_cost.py` and final-report argv conversion is fixed.



### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/report/final_report.py:365-379; python/larch/git/pr_body.py:550-579,656-749
- **Concern**: [SCOPE-REDUCTION] The plan retains the previously accepted unnecessary final-report and PR-body component-cost expansion. Scenario: The feature only needs model-aware Cursor token pricing so grok-4.5 usage contributes to the existing aggregate CURSOR_COST at the correct rate. New component KVs, parser arguments, summary fields, and per-model PR prose add unrelated wire and presentation surface without affecting routing or aggregate cost correctness.
- **Proposed resolution**: Remove the CURSOR_GROK_4_5_COST and CURSOR_COMPOSER_2_5_COST propagation and PR rendering work. Keep the model-aware token split and existing aggregate CURSOR_COST contract.



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty.py
- **Concern**: The plan targets a nonexistent `python/larch/core/difficulty.py` for the shared Step 2 effective-difficulty resolver. The live module is `larch.calibration.difficulty`, which already owns `normalize_tier` and is imported by bootstrap and dispatch.. Scenario: Implementing the listed path adds a dead module or leaves bootstrap/dispatch on divergent helpers, so override-before-prior precedence and MODERATE routing can still drift.
- **Proposed resolution**: Retarget the firm change to `python/larch/calibration/difficulty.py`: add an import-safe `resolve_step2_effective_difficulty(tmpdir)` there and switch bootstrap plus dispatch to import it from `larch.calibration.difficulty`.



### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/final_report.py:275-310
- **Concern**: The final-report fix is underspecified for the existing `_token_argv_from_report` cursor branch, which reads only `BUCKETS_cursor` and emits Composer-priced `--cursor-*` flags. The plan does not name the shared helper or require `BUCKETS_cursor_by_model` on the record passed into it.. Scenario: An implementer can update prose only or tweak aggregate flags while leaving `BUCKETS_cursor_by_model` unused, so grok-4.5 Step 2 usage still prices at Composer rates and prior FINDING_5 persists.
- **Proposed resolution**: Replace the cursor block in `_token_argv_from_report` with the shared `report_tokens_cost._cursor_argv` path (via `RunRecord.raw_report` that includes `BUCKETS_cursor_by_model`, or via `token_cost_argv`), and add a final-report test with mixed grok/composer buckets asserting grok flags are emitted.



### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/implement/dispatch_step2.py:468-557
- **Concern**: The plan replaces `_resolve_step2_difficulty` but does not require `step2_dispatch_main` to call the shared resolver when `--difficulty` is empty. Resolution currently happens only in `run_dispatch_main` before spawning the child.. Scenario: Direct `step2-dispatch` callers and tests that omit `--difficulty` but populate `run-flags.sh` / `difficulty-prior.env` will launch Cursor with an empty tier, so MODERATE runs keep the composer-2.5 default and `--model grok-4.5` never applies.
- **Proposed resolution**: After parsing args in `step2_dispatch_main`, set `args.difficulty = shared_resolver(tmpdir)` when empty before `_dispatch_state`, matching the run-dispatch wrapper contract.



### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/git/pr_body.py
- **Concern**: [SCOPE-REDUCTION] The plan reintroduces a firm `pr_body.py` Cursor component-cost segment after round 1 accepted dropping that surface; the binding issue only requires the grok-4.5 rate row in `report_tokens_cost.py`.. Scenario: `_cursor_argv` plus accurate aggregate `CURSOR_COST` already satisfy the stated pricing goal; PR-summary per-model plumbing adds flags, parsers, render branches, and tests with no correctness benefit.
- **Proposed resolution**: Drop the firm `pr_body.py` update and related component-cost KV propagation; keep aggregate `CURSOR_COST` rendering unchanged.



### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/report_tokens_render.py
- **Concern**: [SCOPE-REDUCTION] The plan adds a firm grok-4.5 rate display split in `report_tokens_render.py`, which the issue did not request.. Scenario: /report-tokens already shows aggregate Cursor cost; separate grok rate text is display-only churn beyond the required pricing fix.
- **Proposed resolution**: Remove the firm `report_tokens_render.py` change; rely on corrected aggregate Cursor pricing from `report_tokens_cost.py`.



### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/difficulty.py:1
- **Concern**: The plan marks a nonexistent module as UPDATED. Scenario: The shared resolver cannot be implemented at the named path without creating an unlisted file, and existing callers already import `larch.calibration.difficulty`
- **Proposed resolution**: Move the resolver change to `python/larch/calibration/difficulty.py` and keep both callers on that existing module



### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/final_report.py:365-379; python/larch/git/pr_body.py:569-749
- **Concern**: [SCOPE-REDUCTION] The prior accepted removal of per-model PR display plumbing remains unapplied. Scenario: Model-aware token arguments can produce an accurate aggregate `CURSOR_COST` without adding component KVs and a new PR-summary presentation contract
- **Proposed resolution**: Keep model-aware final-report pricing and aggregate `CURSOR_COST`, but drop the component-cost propagation and `_cursor_cost_segment` changes



