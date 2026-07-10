### FINDING_1: TRIVIAL waterfall must not forward a blank default model
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The TRIVIAL review-panel waterfall can still emit Codex rows on the Cursor-down path, but forwarding an empty tier default into role-based model resolution will either trip blank-value rejection or prevent the fallback model from being selected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When building waterfall argv, pass --default-model only for non-empty CODEX_REVIEW_PANEL_MODEL_BY_DIFFICULTY[tier]. On TRIVIAL Cursor-down, either omit the flag and rely on model_role=review plus CODEX_REVIEW_MODEL_DEFAULT=gpt-5.6-luna, or pass gpt-5.6-luna explicitly for that branch; never forward a blank value


### FINDING_5: Claude [1m] strings must be normalized before token logging
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The suffixed Claude model string is still written verbatim into token records, which would break the intended sub-model matching and pricing buckets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Strip [1m] inside _record_claude_ci_usage before writing MODEL and record-vendor model


### FINDING_6: Core config tests still pin the old fixer order
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The plan changes the CI recovery order, but the current core config test still asserts the old tuple, so the suite will fail unless that expectation moves with the new ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add `python/tests/core/test_config.py` to the plan and update `test_fixer_tier_order` for the new CI recovery order, plus any split CI/lint model constant used to preserve lint-fix.


### FINDING_7: Final-report harness still checks the old Codex-5.5 label
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The shipped bash final-report harness still asserts the old cost-line label, so changing the emitted label without updating the harness will leave CI red.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add `skills/implement/scripts/test-write-final-report.sh` to the plan and update its `Codex-5.5` assertions and negative checks to the new `Codex-5.6` label


### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/agents/_ci_launcher.py:1044-1049
- **Concern**: [SCOPE-REDUCTION] The plan changes the shared Claude CI fix model without preserving the lint-fix launcher default. Scenario: `launch-claude-lint-fix` also defaults `--model` from `config.CLAUDE_CI_FIX_MODEL`, so the plan would move out-of-scope lint-fix runs from Claude Opus 4.8 to `claude-sonnet-4-6[1m]`.
- **Proposed resolution**: Split the CI-recovery Claude model from lint-fix, or override `launch_claude_lint_fix_main` to keep `claude-opus-4-8` while only CI recovery uses `claude-sonnet-4-6[1m]`.


