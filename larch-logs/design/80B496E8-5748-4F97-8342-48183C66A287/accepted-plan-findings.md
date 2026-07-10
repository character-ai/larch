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


