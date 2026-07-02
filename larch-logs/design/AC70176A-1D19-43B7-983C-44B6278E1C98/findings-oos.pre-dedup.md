### OOS_1: `agent-lint.toml` still allowlists `python/cli.py plan revise-waterfall`
- **Description**: `agent-lint.toml` still allowlists `python/cli.py plan revise-waterfall`. Scenario: After the CLI verb and `revise_plan_with_waterfall_main` are removed, `make agent-lint` can fail on a stale subprocess allowlist row even when runtime code is correct.
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:530-533
- **Phase**: design



### OOS_2: Baseline rows still pin deleted `revise_plan_with_waterfall_*` subprocess sites
- **Description**: Baseline rows still pin deleted `revise_plan_with_waterfall_*` subprocess sites. Scenario: Removing the waterfall without regenerating subprocess baselines can make `py-lint` / duplicate-code checks fail on symbols that no longer exist.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/subprocess-via-runner-baseline.json:767-781
- **Phase**: design



### OOS_3: Shard map still assigns removed `test_revise_plan_with_waterfall_*` cases
- **Description**: Shard map still assigns removed `test_revise_plan_with_waterfall_*` cases. Scenario: Deleting revise-waterfall-only tests without updating shard assignments can trip strict partition guards in CI.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/shard-assignments.json:716
- **Phase**: design



### OOS_4: Complexity and subprocess baselines still reference deleted revise_plan_with_waterfall symbols
- **Description**: Complexity and subprocess baselines still reference deleted revise_plan_with_waterfall symbols. Scenario: Plan removes revise_plan_with_waterfall_main but does not list baseline regeneration for python/complexity-baseline.json or python/subprocess-via-runner-baseline.json.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/complexity-baseline.json:1817-1883
- **Phase**: design



### OOS_5: Review-fix skill prose still describes Cursor→Codex-only waterfall
- **Description**: Review-fix skill prose still describes Cursor→Codex-only waterfall. Scenario: Acceptance changes review.fix_coder to Codex→Cursor→Claude, but the plan updates docs/external-reviewers.md only; skills/review-and-fix/SKILL.md still says review-and-fix dispatches Cursor then Codex.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/review-and-fix/SKILL.md:12
- **Phase**: design



### OOS_6: [OUT_OF_SCOPE] `checks run-relevant` still maps plan changes to deleted `test-revise-plan-with-waterfall`
- **Description**: [OUT_OF_SCOPE] `checks run-relevant` still maps plan changes to deleted `test-revise-plan-with-waterfall`. Scenario: Step 6 deletes `plan revise-waterfall` and its dedicated `test_plan_quality.py` tests, but `checks_run_relevant.py` still runs `make test-revise-plan-with-waterfall` (pytest `-k revise_waterfall`) whenever `plan_quality.py`, `test_plan_quality.py`, or `plan_review.py` changes. After removal, that target can collect zero tests or fail while the explicit pytest list in the plan still passes.
- **Reviewer**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/checks_run_relevant.py:443
- **Phase**: design



### OOS_7: [OUT_OF_SCOPE] Lint baselines still pin deleted revise-waterfall symbols
- **Description**: [OUT_OF_SCOPE] Lint baselines still pin deleted revise-waterfall symbols. Scenario: Deleting `revise_plan_with_waterfall_main` and the `plan revise-waterfall` CLI without updating `agent-lint.toml`, `python/complexity-baseline.json`, and `python/subprocess-via-runner-baseline.json` leaves stale allowlist and baseline rows. Targeted pytest can pass while `make agent-lint` or complexity/subprocess checks fail on the same PR.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:530-533
- **Phase**: design



