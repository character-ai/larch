### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: plan:Approach / plan:Failure modes
- **Concern**: The plan omits the #6825 land-first prerequisite. Scenario: The binding issue marks this work blocked by #6825 because both changes edit `python/larch/core/config.py` (`CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY`, panel slot construction, `ROLE_DEFAULTS` doc_fallback) and `python/larch/report/report_tokens_cost.py` (rate table, `display_rates()`, `price_run()`). Implementing on a pre-#6825 base risks merge conflicts, accidental Grok 4.5 regressions, or wrong rate-row ordering despite the plan’s preservation assertions.
- **Proposed resolution**: Add an explicit Approach or Failure modes step: land #6825 first, rebase this branch, then implement. Re-run the plan’s Grok preservation checks and focused pricing tests on the rebased tree before merge.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/config.py:417-442
- **Concern**: Plan-review panel doc_fallback update is not explicitly scoped. Scenario: The `config.py` bullet names only reviewer and fixer `doc_fallback` strings. `design.plan_review_panel` at line 442 still says per-slot auto when Cursor is available. An implementer can update `review.panel` and fixer fallbacks but leave this string, violating the issue requirement to remove Cursor auto prose everywhere. The final acceptance grep also misses isolated per-slot auto without an adjacent cursor token.
- **Proposed resolution**: Name both panel `doc_fallback` strings explicitly in the `config.py` section (include `design.plan_review_panel` at line 442). Replace per-slot auto with Composer 2.5 default-resolution wording. Add `python/larch/core/config.py` to the manual inspection list in the testing strategy.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/core/config.py;python/larch/report/report_tokens_cost.py
- **Concern**: Plan omits the native #6825 land-first prerequisite. Scenario: The binding issue states Blocked by #6825 and requires landing that Grok work first because both issues edit `config.py` cursor constants and `report_tokens_cost.py` rate tables. The plan only warns about accidental Grok regressions; it does not require rebase on merged #6825 before implementation. Implementing on current main risks conflicts, wrong merge resolution, or byte-level Grok rate drift.
- **Proposed resolution**: Add an Approach or Failure modes step: do not start until #6825 is merged to main; rebase this branch on updated main; run the listed Grok preservation assertions on the rebased tree before other edits.
