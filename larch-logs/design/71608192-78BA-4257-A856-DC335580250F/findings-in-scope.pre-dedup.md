### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_dispatch_panel.py:881-902
- **Concern**: TRIVIAL tier must omit blank --default-model on waterfall; cursor-down Codex cannot rely on CODEX_REVIEW_PANEL_MODEL_BY_DIFFICULTY[TRIVIAL]="" alone. Scenario: Plan sets TRIVIAL map entry to "" and says pass --default-model <tier-panel-model> globally, but TRIVIAL Cursor-down still emits Codex rows. Forwarding an empty default_model into role-path resolve_model_args hits reject_blank, or skips the tier model entirely unless dispatch special-cases the floor
- **Proposed resolution**: When building waterfall argv, pass --default-model only for non-empty CODEX_REVIEW_PANEL_MODEL_BY_DIFFICULTY[tier]. On TRIVIAL Cursor-down, either omit the flag and rely on model_role=review plus CODEX_REVIEW_MODEL_DEFAULT=gpt-5.6-luna, or pass gpt-5.6-luna explicitly for that branch; never forward a blank value



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/review/test_review_pipeline.py:4905-4936
- **Concern**: Plan-fidelity helper unit tests still expect a forced row after review.panel no-op. Scenario: Plan disables _append_forced_plan_fidelity_row for review.panel, but tests that call the helper directly with PLAN_FIDELITY_FORCED=true still assert slot plan-fidelity-forced is appended; targeted pytest will fail even if matrix tests pass
- **Proposed resolution**: Rewrite the _append_forced_plan_fidelity_row direct tests to assert zero rows for review.panel (or delete them if prune fixtures are covered elsewhere); keep prune tests that use synthetic plan-fidelity-forced fixtures only when they do not assert panel policy



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/agents/agent_waterfall.py:57-444
- **Concern**: [SCOPE-REDUCTION] Per-row default_model on dynamic manifest rows is unwired; review-role default is enough. Scenario: Plan tells _synthesize_dynamic_slots to write default_model=gpt-5.6-luna on rows, but Slot parsing and launch only forward global opts.default_model; row-level default_model is ignored today and the plan does not add per-slot forwarding
- **Proposed resolution**: Do not add per-row default_model fields unless agent_waterfall gains slot-level parsing and forwarding; for TRIVIAL Cursor-down emit model_role=review only and depend on CODEX_REVIEW_MODEL_DEFAULT=gpt-5.6-luna with omitted global --default-model



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_dispatch_panel.py:229-248
- **Concern**: Tier-specific default_model never reaches resolved_model attribution. Scenario: HARD and TRIVIAL-fallback Codex rows will launch with different models than the manifest records, so the new tier routing stays unverifiable and the HARD tests that inspect resolved_model will still read the role default.
- **Proposed resolution**: Thread the tier default_model into _resolved_model_for_row or store it on each manifest row before writing JSON



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/agents/agent_voters.py:307-319
- **Concern**: Voter manifest rows have no field for the routed Codex model. Scenario: The plan asks for vote-model metadata, but the manifest writer only emits slot, tool, output, prompt_files, and payload_files, so /review cannot record whether a tier used Luna or Terra.
- **Proposed resolution**: Add a resolved_model or default_model field to voter rows and populate it from the tier-aware routing



### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_claude_runner.py:242-273
- **Concern**: Claude [1m] model strings are still written verbatim to token records. Scenario: launch-claude-ci and launch-claude-review-fix call _record_claude_ci_usage with args.model, so the suffixed model will still reach token ledgers and break the new Claude sub-model matching and pricing buckets.
- **Proposed resolution**: Strip [1m] inside _record_claude_ci_usage before writing MODEL and record-vendor model



### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/agents/_ci_launcher.py:228-341,920-1010,1043-1155
- **Concern**: [SCOPE-REDUCTION] Scope the new fix-model pins to the CI-recovery path instead of changing the shared CI launchers.. Scenario: launch-codex-ci, launch-cursor-ci, launch-claude-ci, and launch-claude-lint-fix are also used by rebase-conflict and lint-fix flows, so the new defaults would silently leak into unrelated fixers.
- **Proposed resolution**: Keep the existing shared launcher defaults for resolve-conflict and lint-fix callers, and pass the new models only from the CI-recovery call site or behind an args.role == "fix" guard.



### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_dispatch_panel.py:229-247,282-316,360-453
- **Concern**: HARD panel rows will still serialize the review-role default because `_resolved_model_for_row` never sees the tier-specific `default_model`.. Scenario: `review.panel` rows can launch `gpt-5.6-terra` while the manifest still records `gpt-5.6-luna`, so the panel manifest and the new tests no longer describe the real launch.
- **Proposed resolution**: Thread the tier default into the row-attribution helper, or set `resolved_model` from the same tier map before writing each Codex row.



### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/agents/_ci_launcher.py:1044-1049
- **Concern**: [SCOPE-REDUCTION] The plan changes the shared Claude CI fix model without preserving the lint-fix launcher default. Scenario: `launch-claude-lint-fix` also defaults `--model` from `config.CLAUDE_CI_FIX_MODEL`, so the plan would move out-of-scope lint-fix runs from Claude Opus 4.8 to `claude-sonnet-4-6[1m]`.
- **Proposed resolution**: Split the CI-recovery Claude model from lint-fix, or override `launch_claude_lint_fix_main` to keep `claude-opus-4-8` while only CI recovery uses `claude-sonnet-4-6[1m]`.



### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/core/test_config.py:7-10
- **Concern**: The plan omits the core config test that pins the old CI fixer order. Scenario: After `FIXER_TIER_ORDER` changes to `("codex", "cursor", "claude")`, the existing test still expects `("claude", "codex", "cursor")`, so the Python suite fails.
- **Proposed resolution**: Add `python/tests/core/test_config.py` to the plan and update `test_fixer_tier_order` for the new CI recovery order, plus any split CI/lint model constant used to preserve lint-fix.



### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-write-final-report.sh:432-806
- **Concern**: The plan changes the cost-line label but omits the shipped bash final-report harness. Scenario: The implementation will emit `Codex-5.6`, while `make test-write-final-report` still checks `Codex-5.5` in this harness, leaving CI red.
- **Proposed resolution**: Add `skills/implement/scripts/test-write-final-report.sh` to the plan and update its `Codex-5.5` assertions and negative checks to the new `Codex-5.6` label.



