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

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/difficulty.py
- **Concern**: Plan targets a nonexistent difficulty module. Scenario: The repo defines difficulty helpers in python/larch/calibration/difficulty.py, while python/larch/core/difficulty.py does not exist. Implementing the shared Step 2 resolver at the planned UPDATED path can either fail immediately or create a second difficulty authority that bootstrap and dispatch do not already import.
- **Proposed resolution**: Change the firm plan item to update python/larch/calibration/difficulty.py and python/tests/calibration/test_difficulty.py, then import the shared resolver from larch.calibration.difficulty in bootstrap and dispatch.

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:26-33
- **Concern**: The shared resolver is assigned to `python/larch/core/difficulty.py`, but the existing difficulty implementation lives in `python/larch/calibration/difficulty.py`, which both bootstrap and dispatch currently import.. Scenario: An implementation that follows the listed path can create a second difficulty module or leave the existing callers unchanged. Bootstrap and dispatch may then use different normalization and file-error behavior, defeating the required single-precedence resolver.
- **Proposed resolution**: Place the shared resolver in the existing `python/larch/calibration/difficulty.py`, or explicitly update both import sites and define the new module's complete ownership and compatibility contract.

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

### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/difficulty.py:1
- **Concern**: The plan marks a nonexistent module as UPDATED. Scenario: The shared resolver cannot be implemented at the named path without creating an unlisted file, and existing callers already import `larch.calibration.difficulty`
- **Proposed resolution**: Move the resolver change to `python/larch/calibration/difficulty.py` and keep both callers on that existing module
