### FINDING_1: Stale `test-revise-plan-with-waterfall` relevant-checks mapping
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan deletes `plan revise-waterfall`, its tests, and the Step 3 external revise path, but does not update `python/larch/implement/checks_run_relevant.py` (line 443) or the paired `Makefile` target `test-revise-plan-with-waterfall` (`pytest -k revise_waterfall`). After retirement, any PR touching `python/larch/review/plan_review.py` or `python/larch/design/plan_quality.py` will still invoke that harness and fail when zero revise tests match or the helper is gone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/larch/implement/checks_run_relevant.py` to drop the `test-revise-plan-with-waterfall` rule (and any paired patterns that only existed for revise-waterfall). Retire or repoint the `Makefile` target; do not leave a dead harness in `make lint` / `checks run-relevant`.
  - From Cursor-Innovation: Add ### UPDATED: python/larch/implement/checks_run_relevant.py; drop the test-revise-plan-with-waterfall tuple (and retire or no-op the Makefile target if nothing else needs it).


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_4: Claude review-fix launcher argv contract conflicts with caller
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan specifies `_run_coder_claude()` calling `agent launch-claude-review-fix` with `--timing-task-kind claude-review-fix`, while the new launcher is specified to mirror `launch-claude-lint-fix` argv (e.g. only `--prompt-body-file`, `--output`, `--timeout`, `--model`). If implemented literally, argparse rejects `--timing-task-kind` and the Claude review-fix tier fails before applying fixes, breaking the required Codex→Cursor→Claude waterfall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Either add --timing-task-kind with default claude-review-fix to launch-claude-review-fix, or remove the flag from _run_coder_claude and hardcode the timing task in the launcher.
  - From Codex-Innovation: Add `--timing-task-kind` to `launch_claude_review_fix_main` with default `claude-review-fix` and use it for timing, or remove the caller flag and hardcode the task kind in the launcher.
  - From Codex-Pragmatic: Add --timing-task-kind to launch-claude-review-fix with default claude-review-fix and use it for timing, or remove the caller flag and hard-code the task kind in the launcher.
  - From Codex-Requirements: Add `--timing-task-kind` to the planned `launch_claude_review_fix_main` argv contract with default `claude-review-fix`, or remove the caller flag and hardcode that timing kind inside the launcher.


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: `agent-lint.toml` still allowlists `python/cli.py plan revise-waterfall`
- **Description**: `agent-lint.toml` still allowlists `python/cli.py plan revise-waterfall`. Scenario: After the CLI verb and `revise_plan_with_waterfall_main` are removed, `make agent-lint` can fail on a stale subprocess allowlist row even when runtime code is correct.
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:530-533
- **Phase**: design




Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral

### OOS_2: Baseline rows still pin deleted `revise_plan_with_waterfall_*` subprocess sites
- **Description**: Baseline rows still pin deleted `revise_plan_with_waterfall_*` subprocess sites. Scenario: Removing the waterfall without regenerating subprocess baselines can make `py-lint` / duplicate-code checks fail on symbols that no longer exist.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/subprocess-via-runner-baseline.json:767-781
- **Phase**: design




Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral

### OOS_3: Shard map still assigns removed `test_revise_plan_with_waterfall_*` cases
- **Description**: Shard map still assigns removed `test_revise_plan_with_waterfall_*` cases. Scenario: Deleting revise-waterfall-only tests without updating shard assignments can trip strict partition guards in CI.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/shard-assignments.json:716
- **Phase**: design




Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral

### OOS_4: Complexity and subprocess baselines still reference deleted revise_plan_with_waterfall symbols
- **Description**: Complexity and subprocess baselines still reference deleted revise_plan_with_waterfall symbols. Scenario: Plan removes revise_plan_with_waterfall_main but does not list baseline regeneration for python/complexity-baseline.json or python/subprocess-via-runner-baseline.json.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/complexity-baseline.json:1817-1883
- **Phase**: design




Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral

### OOS_5: Review-fix skill prose still describes Cursor→Codex-only waterfall
- **Description**: Review-fix skill prose still describes Cursor→Codex-only waterfall. Scenario: Acceptance changes review.fix_coder to Codex→Cursor→Claude, but the plan updates docs/external-reviewers.md only; skills/review-and-fix/SKILL.md still says review-and-fix dispatches Cursor then Codex.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/review-and-fix/SKILL.md:12
- **Phase**: design




Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral

### OOS_6: [OUT_OF_SCOPE] `checks run-relevant` still maps plan changes to deleted `test-revise-plan-with-waterfall`
- **Description**: [OUT_OF_SCOPE] `checks run-relevant` still maps plan changes to deleted `test-revise-plan-with-waterfall`. Scenario: Step 6 deletes `plan revise-waterfall` and its dedicated `test_plan_quality.py` tests, but `checks_run_relevant.py` still runs `make test-revise-plan-with-waterfall` (pytest `-k revise_waterfall`) whenever `plan_quality.py`, `test_plan_quality.py`, or `plan_review.py` changes. After removal, that target can collect zero tests or fail while the explicit pytest list in the plan still passes.
- **Reviewer**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/checks_run_relevant.py:443
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] Lint baselines still pin deleted revise-waterfall symbols
- **Description**: [OUT_OF_SCOPE] Lint baselines still pin deleted revise-waterfall symbols. Scenario: Deleting `revise_plan_with_waterfall_main` and the `plan revise-waterfall` CLI without updating `agent-lint.toml`, `python/complexity-baseline.json`, and `python/subprocess-via-runner-baseline.json` leaves stale allowlist and baseline rows. Targeted pytest can pass while `make agent-lint` or complexity/subprocess checks fail on the same PR.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:530-533
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

