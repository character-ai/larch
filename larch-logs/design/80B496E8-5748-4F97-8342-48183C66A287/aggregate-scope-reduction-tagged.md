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

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/git/pr_body.py
- **Concern**: [SCOPE-REDUCTION] Prior scope-reduction fix is incomplete: drop per-model Cursor PR-summary display plumbing. Scenario: The issue asks for MODERATE Cursor/grok routing and correct grok pricing. Accurate aggregate CURSOR_COST can ship without adding _cursor_cost_segment, PR-summary component fields, and render_run_summary parsing. Keeping those firm changes adds downstream UI churn beyond the required pricing contract.
- **Proposed resolution**: Keep model-aware token conversion and aggregate CURSOR_COST propagation where needed for correct pricing, but remove the firm pr_body.py per-model Cursor segment and component-cost display work from this plan.

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:104-110
- **Concern**: [SCOPE-REDUCTION] The plan still makes PR-summary model-component rendering a firm part of the feature.. Scenario: The binding issue only requires MODERATE Cursor routing and a `("cursor", "grok-4.5")` rate. Pricing can preserve the aggregate `CURSOR_COST` contract after model-aware token splitting, so adding component KVs through `final_report.py` and `pr_body.py` expands the wire and display surface without being required for the requested feature.
- **Proposed resolution**: Remove the firm `final_report.py` and `python/larch/git/pr_body.py` component-cost work. Keep model-aware splitting and aggregate `CURSOR_COST` in `report_tokens_cost.py`, with focused pricing coverage.

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

### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/final_report.py:365-379; python/larch/git/pr_body.py:569-749
- **Concern**: [SCOPE-REDUCTION] The prior accepted removal of per-model PR display plumbing remains unapplied. Scenario: Model-aware token arguments can produce an accurate aggregate `CURSOR_COST` without adding component KVs and a new PR-summary presentation contract
- **Proposed resolution**: Keep model-aware final-report pricing and aggregate `CURSOR_COST`, but drop the component-cost propagation and `_cursor_cost_segment` changes
