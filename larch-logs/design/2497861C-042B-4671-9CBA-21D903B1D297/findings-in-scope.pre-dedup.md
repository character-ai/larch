### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_step2.py:348-370
- **Concern**: Blank Cursor overrides are silently replaced by the tier default in the dispatcher metadata path. Scenario: The plan requires blank overrides to fail validation, but `_first_model_value` skips blank environment or session values. The launcher resolver may reject the same override while the dispatcher records `grok-4.5` or `composer-2.5`, producing inconsistent model metadata and masking invalid configuration
- **Proposed resolution**: Make the dispatcher model lookup reject a present-but-blank or control-character override using the same validation semantics as `resolve_model_args`, rather than skipping it



### FINDING_2:
- **Reviewer(s)**: Cursor-dyn-Model Routing Auditor
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/implement/test_implement_dispatch.py:206-217
- **Concern**: Override tests omit MODERATE tier context. Scenario: `test_resolve_implement_rater_model_uses_cursor_plugin_option_from_session` calls `_resolve_implement_rater_model` without `difficulty_tier`, so it only proves the plugin option beats the empty-tier fallback (`CURSOR_DEFAULT_MODEL`), not that overrides beat the MODERATE `grok-4.5` default; a broken `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY` MODERATE entry could still pass
- **Proposed resolution**: Add to the plan’s `test_implement_dispatch.py` section: parametrize override tests (env, plugin, env+plugin precedence) with `difficulty_tier` in `{TRIVIAL, MODERATE, HARD}`; for MODERATE, assert overrides beat `grok-4.5`, not only `composer-2.5`



### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-Model Routing Auditor
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/agents/test_agents.py:469-473
- **Concern**: Launcher-path env-vs-plugin precedence untested in plan. Scenario: `resolve_model_args` is what `launch_cursor_implement_main` uses (`python/larch/agents/_ci_launcher.py:978`), but the plan’s `test_agents.py` bullets only require overrides beat a supplied `default_model`; acceptance also requires `LARCH_CURSOR_MODEL` to win when both override sources are set
- **Proposed resolution**: Add a `test_agents.py` case: with `default_model="grok-4.5"`, set both `LARCH_CURSOR_MODEL` and `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL` and assert argv uses the larch env value



### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-Model Routing Auditor
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/implement/test_implement_dispatch.py:238-298
- **Concern**: Plan omits cursor MODERATE difficulty-metadata test. Scenario: The plan requires dispatcher metadata to match the resolved model (`dispatch_step2.py` `_write_step2_difficulty_record` → `--rater-model`), but testing strategy only extends config/dispatch/agents tests; existing coverage is codex-only (`test_write_step2_difficulty_record_*`)
- **Proposed resolution**: Add a cursor+MODERATE `_write_step2_difficulty_record` test asserting `--rater-model` is `grok-4.5` (and override cases when env/plugin set) ### 1. [correctness] `python/tests/implement/test_implement_dispatch.py:206-217` — Override tests omit MODERATE tier context The plan requires overrides to beat the tier default at each tier, but the existing plugin-option test calls `_resolve_implement_rater_model` without `difficulty_tier`. That only checks the plugin path against the empty-tier fallback (`CURSOR_DEFAULT_MODEL` / `composer-2.5`), not against MODERATE’s `grok-4.5` default. **Suggested revision:** Parametrize override cases with `difficulty_tier` in `{TRIVIAL, MODERATE, HARD}`. For MODERATE, assert env and plugin overrides resolve to the override value, not `grok-4.5`. ### 2. [correctness] `python/tests/agents/test_agents.py:469-473` — Launcher-path env-vs-plugin precedence untested in plan Acceptance requires `LARCH_CURSOR_MODEL` to win when both override variables are set. The plan’s `test_implement_dispatch.py` section covers that for `_resolve_implement_rater_model`, but the `test_agents.py` section only requires both sources to beat a supplied `default_model`. The launch path uses `resolve_model_args` at `python/larch/agents/_ci_launcher.py:978`, which is a separate code path. **Suggested revision:** Add a `resolve_model_args("cursor", default_model="grok-4.5")` test with both env vars set; assert the larch env model wins. ### 3. [correctness] `python/tests/implement/test_implement_dispatch.py:238-298` — Plan omits cursor MODERATE difficulty-metadata test The plan’s `dispatch_step2.py` section requires difficulty metadata to match the resolved model, but the testing strategy does not extend the existing `_write_step2_difficulty_record` tests (codex-only today). Usage sidecar coverage in `test_agents.py` does not validate `--rater-model` written by the dispatcher. **Suggested revision:** Add `test_write_step2_difficulty_record_passes_cursor_moderate_rater_model` (or extend the parametrized matrix) asserting `--rater-model` is `grok-4.5` for `tool_tag="cursor"` and `difficulty=MODERATE`. --- **Verified contract paths (no plan gap):** `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY` at `python/larch/core/config.py:294-298`; tier lookup in `_resolve_implement_rater_model` at `python/larch/implement/dispatch_step2.py:362-368`; `--difficulty` forwarding at `python/larch/implement/dispatch_step2.py:263-264`; launcher map + `normalize_tier` at `python/larch/agents/_ci_launcher.py:974-978`; usage attribution via `_model_arg_value` → `_record_cursor_implement_usage(..., model=...)` at `python/larch/agents/_ci_launcher.py:1005-1010`; `resolve_model_args` caller-default precedence at `python/larch/agents/_launch_failure.py:233-235`; MODERATE Codex fallback `gpt-5.6-sol` at `python/larch/core/config.py:705-708`; non-Step-2 CI fixer still uses bare `resolve_model_args("cursor", ...)` at `python/larch/agents/_ci_launcher.py:371`.



### FINDING_5:
- **Reviewer(s)**: Codex-dyn-Model Routing Auditor
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/agents/_launch_failure.py:233-235
- **Concern**: [SCOPE-REDUCTION] The plan proposes changing the Cursor resolver to honor `default_model`, but the current resolver already uses the caller default before `CURSOR_DEFAULT_MODEL` while preserving both override precedences.. Scenario: Implementing this plan item adds needless churn without changing the Step 2 execution path.
- **Proposed resolution**: Remove the `_launch_failure.py` work item, or limit it to a regression test if the final diff needs coverage.



