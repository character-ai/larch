### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_panel.py:1149-1210
- **Concern**: Prior-round dispatch refactor is incomplete: voter-1 parse-rate retry and voter-status-block still hardcode tool claude. Scenario: After the three-slot waterfall lands, VOTER_1_PATH will point at codex-validity-vote-output.txt while VOTER_1_TOOL and parse-rate attribution still emit claude, so findings-classification.tsv and /voter-calibration see legacy vendor labels on the primary slot
- **Proposed resolution**: Extend the plan_review_panel.dispatch_voters section to derive voter_1_tool (and prompt file) from bind_manifest_slot_outputs like agent_voters._state_from_bindings, and pass that semantic label through _parse_rate_retry and voter-status-block for all three slots

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_tally.py:360-363
- **Concern**: Plan updates _DESIGN_VOTER_FALLBACKS in _voting_calibration.py but leaves a second legacy fallback dict in plan_review_tally. Scenario: When slot_tool[pos] is empty, voting-tally.md agreement rows still fall back to Claude/Codex/Cursor even after semantic dispatch, splitting calibration labels across modules
- **Proposed resolution**: Add an explicit plan_review_tally.py step to reuse the same design semantic fallbacks (codex-validity/codex-plan-fidelity/codex-pragmatism) for the _voter_agreement_row_for_item path

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/review/test_plan_review_round.py
- **Concern**: The test inventory omits plan-review round integration harnesses that still assert VOTER_1_TOOL=claude and claude-vote-output.txt paths. Scenario: CI can pass panel/dispatch unit tests while round-loop mocks still encode the Claude-first contract and miss regressions in tally handoff
- **Proposed resolution**: Add ### UPDATED: python/tests/review/test_plan_review_round.py with expectations for three-row manifests, codex-*-vote-output basenames, and semantic VOTER_N_TOOL values

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-prompt-template-invariants.sh:132-155
- **Concern**: Plan omits the prompt invariant harness that still asserts legacy plan-voter prompt files. Scenario: The proposed single-Claude both-externals-down floor and semantic voter prompt/output basenames can stop producing codex-plan-voter-prompt-codex.txt and cursor-plan-voter-prompt-cursor.txt, so test-prompt-template-invariants fails in CI
- **Proposed resolution**: Add scripts/test-prompt-template-invariants.sh, and its md if needed, to the plan. Update the plan-voter smoke to assert the new semantic prompt files or a happy-path manifest while preserving the Verify silently and Output ONLY vote lines checks.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_panel.py:1149-1220
- **Concern**: Plan refactor omits explicit cleanup of hardcoded voter-1 `claude` tool literals in parse-rate retry and `voter-status-block` emission on the externals-present path. Scenario: Mirroring the three-slot manifest without also switching voter-1 tool attribution leaves `VOTER_1_TOOL=claude` and `voter_tool="claude"` while voter-1 output moves to `codex-validity-vote-output.txt`; voters 2/3 can likewise stay bare `codex`/`cursor` from bindings instead of `codex-plan-fidelity`/`codex-pragmatism`, so tally and `findings-classification.tsv` keep legacy labels and break acceptance criterion 6
- **Proposed resolution**: In `dispatch_voters`, resolve all three slots through the same `_semantic_label` + `_state_from_bindings` pattern as `agent_voters`, remove happy-path `Popen` voter-1, and pass resolved semantic tools into `_parse_rate_retry` and final `VOTER_N_TOOL` emission (or reuse `_emit_final_kvs`); keep `claude` only on the both-externals-down floor branch

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/review/test_plan_review_panel.py:490-1430
- **Concern**: Planned `test_plan_review_panel.py` updates do not call out the many `subprocess.Popen` voter-1 mocks that encode the removed parallel-Claude architecture. Scenario: After happy-path dispatch drops `Popen`, tests such as `test_dispatch_voters_calibration_wiring_harness` and `test_voter_dispatch_claude_failure_codex_cursor_succeed` will fail or keep testing deleted behavior unless rewritten around a three-row waterfall mock
- **Proposed resolution**: Add an explicit test-plan bullet to rewrite or delete every Popen-based happy-path voter-dispatch test and assert `VOTER_1_TOOL=codex-validity` (or cursor/claude fallback labels) on the externals-present path

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/test-prompt-template-invariants.sh:132-155
- **Concern**: Prompt invariant harness still targets legacy design voter prompt basenames. Scenario: The plan moves design voter prompt/output stems to the codex-validity, codex-plan-fidelity, and codex-pragmatism policy shape, but this make lint harness still opens codex-plan-voter-prompt-codex.txt and cursor-plan-voter-prompt-cursor.txt after voter-dispatch. Full lint or CI can fail even when the feature works.
- **Proposed resolution**: Add ### UPDATED: scripts/test-prompt-template-invariants.sh and retarget the smoke assertions to the new policy-derived prompt files, or discover the generated prompt files from the voter manifest instead of hard-coded legacy names.
