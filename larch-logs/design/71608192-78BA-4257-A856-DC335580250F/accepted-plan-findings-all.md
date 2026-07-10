### FINDING_1: Review-fix Cursor auto pin hits the wrong launcher
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-Routing Matrix Auditor
- **Severity**: major
- **Concern**: The review-fix Cursor path still resolves the generic Cursor model on the live launcher path, so the fixer waterfall can keep using `composer-2.5` instead of `auto`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `The fixer matrix requires Cursor \`auto\`, but shipped review-fix would keep \`composer-2.5\`. Add \`### UPDATED: python/larch/review/coder_runner.py\`: pin \`--model auto\` in \`_run_coder_cursor\` (or call a launcher that does). Drop the \`_review_launcher.py\` review-fix carve-out unless a real call site exists.`
  - From Codex-Pragmatic: `Add python/larch/review/coder_runner.py to firm changes and pin _run_coder_cursor to ["--model", config.CURSOR_AUTO_MODEL], with the review-fix test updated to assert auto`
  - From Codex-Requirements: `Add python/larch/review/coder_runner.py to the firm changes, set the review-fix Cursor argv to --model auto at _run_coder_cursor, and cover that argv in the review-fix coder tests.`
  - From Cursor-dyn-Routing Matrix Auditor: `Pin --model auto in coder_runner._run_coder_cursor (or pass --cursor-model auto through launch-review if that path is adopted); add/extend python/tests/review/test_review_and_fix.py coverage for the cursor argv`


### FINDING_2: Review-fix Claude 1m pin is not on the live path
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-dyn-Routing Matrix Auditor
- **Severity**: major
- **Concern**: The review-fix Claude launcher still defaults to unsuffixed Sonnet on the live path, so changing config alone does not make the waterfall launch `claude-sonnet-4-6[1m]`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `Review-fix Claude stays on unsuffixed Sonnet 4.6, not \`claude-sonnet-4-6[1m]\`. Update \`launch_claude_review_fix\` default to the \`[1m]\` constant (or dict lookup) and/or pass \`--model claude-sonnet-4-6[1m]\` from \`_run_coder_claude\`. List \`_ci_launcher.py\` and \`coder_runner.py\` under Files to modify.`
  - From Codex-Innovation: `Add review/coder_runner.py to the plan and pin the Cursor fixer to --model auto and the Claude fixer to claude-sonnet-4-6[1m].`
  - From Cursor-dyn-Routing Matrix Auditor: `Change launch_claude_review_fix_main default to the new [1m] constant (or claude_sub_default_model), or pass --model claude-sonnet-4-6[1m] from coder_runner._run_coder_claude; cover in python/tests/review/test_review_and_fix.py and python/tests/report/test_tokens.py`


### FINDING_3: Under-quorum voter retries drop the tier
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Requirements, Codex-dyn-Routing Matrix Auditor
- **Severity**: major
- **Concern**: Targeted voter retries do not carry the resolved tier through dispatch, so TRIVIAL revotes can fall back to the flat vote-role default instead of the tier-specific model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `Under-quorum revotes fall back to the flat vote-role default (\`gpt-5.6-terra\`) even on TRIVIAL/MODERATE rounds that require \`gpt-5.6-luna\`. Add \`### UPDATED: python/larch/review/round_runner.py\` and forward resolved \`panel_tier\` as \`--tier\` in \`_build_targeted_dispatch_args\` (and any helper it shares).`
  - From Codex-Arch: `Add --tier args.panel_tier to the targeted dispatch args before calling agent dispatch-voters.`
  - From Cursor-Requirements: `Add panel_tier to ReviewCoreBranchContext (python/larch/review/review_pipeline_shared.py) when constructing branch_ctx, pass --tier from ctx in _dispatch_voters_for_ballot, or read PANEL_TIER from review-core-dispatch.env before dispatch-voters.`
  - From Codex-dyn-Routing Matrix Auditor: `Add the resolved tier to the targeted revote args, pass it through agent dispatch-voters, and record the launched Codex vote model in the voter manifest metadata.`


### FINDING_5: TRIVIAL dynamic Codex floor is missing when Cursor is down
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Routing Matrix Auditor, Codex-dyn-Routing Matrix Auditor
- **Severity**: major
- **Concern**: The dynamic-slot synthesizer skips Codex rows on TRIVIAL when Cursor is unavailable, so the required review floor disappears on that fallback path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: `In _synthesize_dynamic_slots add an elif branch for TRIVIAL with not cursor_available and codex_available: emit one Codex row per archetype with model_role review and tier default_model luna; keep the existing block that skips Codex on TRIVIAL when Cursor is up`
  - From Cursor-dyn-Routing Matrix Auditor: `Allow Codex dynamic rows on TRIVIAL only when cursor_available is false, with model_role=review and default_model gpt-5.6-luna; extend python/tests/review/test_review_pipeline.py with a TRIVIAL cursor-down dynamic case`
  - From Codex-dyn-Routing Matrix Auditor: `Mirror the static TRIVIAL fallback inside _synthesize_dynamic_slots and emit Codex gpt-5.6-luna rows for dynamic archetypes when Cursor is unavailable.`


### FINDING_6: Panel-composition tests target the wrong files
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Routing Matrix Auditor
- **Severity**: major
- **Concern**: The plan points panel-composition assertions at the wrong test module set, leaving the actual review-panel manifest tests and the external-dispatch expectations stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: `Add python/tests/review/test_review_pipeline.py to Files to modify/create with tier matrix updates mirroring test_review_dispatch.py (TRIVIAL Cursor-only when both vendors up, TRIVIAL Cursor-down Codex luna, MODERATE/HARD pair models, no default-role rows)`
  - From Cursor-Pragmatic: `Target composition-by-tier and no-default-role assertions at python/tests/agents/test_external_dispatch.py (and test_review_pipeline.py); make the test_external_dispatch.py generalist/model-role updates mandatory not conditional`
  - From Cursor-Requirements: `Add ### UPDATED: python/tests/review/test_review_pipeline.py with explicit matrix assertions (TRIVIAL Cursor singles, TRIVIAL Cursor-down Codex luna singles, MODERATE/HARD pair models) and include the file in the targeted pytest command.`
  - From Cursor-dyn-Routing Matrix Auditor: `Add ### UPDATED: python/tests/review/test_review_pipeline.py and include it in the testing-strategy pytest invocation; retire or narrow test_review_dispatch.py panel claims to match its classify/wait scope`


### FINDING_7: Registry and calibration tests still expect deleted overrides
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Tests outside the panel-dispatch file set still assert the deleted generalist slot and review.panel override behavior, so the broader pytest sweep will fail unless they are updated too.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: `Removing review.panel from DIFFICULTY_CODEX_MODEL_ROLE_OVERRIDES and deleting the generalist SlotDefault breaks test_external_role_defaults (generalist lookup and review.panel override dict) and test_difficulty review.panel HARD archetype role expectations. make py-test fails outside the plan's enumerated test modules. Add ### UPDATED entries for both files: drop generalist expectations, remove review.panel override assertions, and keep design.plan_review_panel coverage only.`


### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_dispatch_panel.py:338-358
- **Concern**: [SCOPE-REDUCTION] Forced plan-fidelity reviewer remains outside the complete panel matrix. Scenario: When PLAN_FIDELITY_FORCED=true, Step 5 emits an extra Cursor or Codex reviewer beyond the static and dynamic archetype sets the issue declares complete; the Codex branch also still consults codex_review_model_role_for_archetype for review.panel
- **Proposed resolution**: Revise the plan to remove or disable the forced plan-fidelity row for review.panel and update affected tests/docs so panel manifests contain only the specified matrix rows


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


