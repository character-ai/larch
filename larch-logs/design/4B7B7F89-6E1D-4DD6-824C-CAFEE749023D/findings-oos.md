### OOS_1: `_fallback_cost()` still calls `display_rates()` with no `claude_model` / `RunRecord.main_model`
- **Description**: `_fallback_cost()` still calls `display_rates()` with no `claude_model` / `RunRecord.main_model`. Scenario: When `token_cost_from_args()` fails (malformed argv, drift, subprocess exception), `price_run()` and `/report-tokens` fall back to blended Opus pricing even for Sonnet-majority runs
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/report_tokens_cost.py:508-523
- **Phase**: design



### OOS_2: Plan adds another local `claude_sub` argv splitter beside `report_tokens_cost._claude_sub_argv()`
- **Description**: Plan adds another local `claude_sub` argv splitter beside `report_tokens_cost._claude_sub_argv()`. Scenario: `final_report._token_argv_from_report()` already duplicates Codex routing; a second hand-rolled `claude_sub` mirror increases drift risk when flag families or fold rules change
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/final_report.py:275-312
- **Phase**: design



### OOS_3: `CLAUDE_SUB_DEFAULT_MODEL_BY_RAW` may omit `exec-issue-assessment` rows that map to `claude_review`
- **Description**: `CLAUDE_SUB_DEFAULT_MODEL_BY_RAW` may omit `exec-issue-assessment` rows that map to `claude_review`. Scenario: Legacy ledger rows without `model=` from exec-issue assessment (Haiku) inherit `claude_review` → Sonnet default, mispricing Haiku subprocess until model recording ships everywhere
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/core/config.py:358-421 and python/exec_issue_detail.py:396
- **Phase**: design



### OOS_4: `_fallback_cost` still ignores `RunRecord.main_model`
- **Description**: `_fallback_cost` still ignores `RunRecord.main_model`. Scenario: When `token_cost_from_args` raises (malformed argv, missing cache keys, etc.), `price_run` falls back to `display_rates()` with no model and Opus-blended main-lane math. Sonnet-main `/report-tokens` rows can still show Opus-scale totals on the error path.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/report_tokens_cost.py:508-523
- **Phase**: design



### OOS_5: `render_cost_line_from_args` bypasses `_parse_pricing_argv`
- **Description**: `render_cost_line_from_args` bypasses `_parse_pricing_argv`. Scenario: Callers that add `--claude-model` to argv passed to `render_cost_line_from_args` still hit `_parse_count_args` first and get `unknown or incomplete flag`, same failure mode as pre-fix `token_cost_from_args`.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/report_tokens_cost.py:471-483
- **Phase**: design



### OOS_6: python/design_summary.py:89-122
- **Description**: python/design_summary.py:89-122. Scenario: Duplicate argv builders can drift from `report_tokens_cost`
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/final_report.py:275-312
- **Phase**: design



### OOS_7: _fallback_cost always uses display_rates() with no main model
- **Description**: _fallback_cost always uses display_rates() with no main model. Scenario: When price_run/token_cost_from_args fails, /report-tokens blended fallback reprices Sonnet main runs at Opus rates despite RunRecord.main_model
- **Reviewer**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/report_tokens_cost.py:508-523
- **Phase**: design



### OOS_8: [OUT_OF_SCOPE] claude-fable-5 rate row and flag family have no spawn consumer
- **Description**: [OUT_OF_SCOPE] claude-fable-5 rate row and flag family have no spawn consumer. Scenario: No subprocess path records claude-fable-5 today; adding a third model family expands _FLAG_NAMES and tests without fixing a current mispricing
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/report_tokens_cost.py:26-48
- **Phase**: design



### OOS_9: _fallback_cost still calls display_rates() with no RunRecord.main_model when token_cost_from_args fails.
- **Description**: _fallback_cost still calls display_rates() with no RunRecord.main_model when token_cost_from_args fails.. Scenario: /report-tokens price_run fallback on malformed argv or pricing errors reprices Sonnet-main historical runs at Opus blended defaults.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/report_tokens_cost.py:508-523
- **Phase**: design



### OOS_10: [SCOPE-REDUCTION] claude-fable-5 rate rows and matching subprocess flag family are added even though no spawn path in agents.py references that model today.
- **Description**: [SCOPE-REDUCTION] claude-fable-5 rate rows and matching subprocess flag family are added even though no spawn path in agents.py references that model today.. Scenario: ~100+ LOC of rates, argv families, and tests for a model family with zero current ledger traffic.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/report_tokens_cost.py:26-49
- **Phase**: design



