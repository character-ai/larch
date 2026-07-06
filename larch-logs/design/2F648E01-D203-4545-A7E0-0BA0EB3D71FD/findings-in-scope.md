### FINDING_1: Voter-1 semantic labels still hardcoded
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The plan-review voter dispatch refactor still leaves voter-1 parse-rate retry, voter-status-block emission, and final tool attribution tied to legacy `claude` labels even when the slot output moves to semantic Codex paths, which will keep legacy vendor labels in tallying and calibration data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the plan_review_panel.dispatch_voters section to derive voter_1_tool (and prompt file) from bind_manifest_slot_outputs like agent_voters._state_from_bindings, and pass that semantic label through _parse_rate_retry and voter-status-block for all three slots
  - From Cursor-Innovation: In `dispatch_voters`, resolve all three slots through the same `_semantic_label` + `_state_from_bindings` pattern as `agent_voters`, remove happy-path `Popen` voter-1, and pass resolved semantic tools into `_parse_rate_retry` and final `VOTER_N_TOOL` emission (or reuse `_emit_final_kvs`); keep `claude` only on the both-externals-down floor branch

### FINDING_2: Legacy fallback labels remain in tally agreement rows
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: `plan_review_tally` still uses a separate legacy fallback dict for agreement rows, so empty `slot_tool[pos]` positions can continue to emit Claude/Codex/Cursor labels after the design moves to semantic dispatch, splitting calibration labels across modules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit plan_review_tally.py step to reuse the same design semantic fallbacks (codex-validity/codex-plan-fidelity/codex-pragmatism) for the _voter_agreement_row_for_item path

### FINDING_3: Integration tests still encode the old voter-1 contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: minor
- **Concern**: The planned test inventory misses review-round integration harnesses that still assert `VOTER_1_TOOL=claude`, `claude-vote-output.txt`, and `subprocess.Popen`-based happy-path dispatch, so CI can pass narrow panel tests while round-loop mocks keep testing deleted behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/tests/review/test_plan_review_round.py with expectations for three-row manifests, codex-*-vote-output basenames, and semantic VOTER_N_TOOL values
  - From Cursor-Innovation: Add an explicit test-plan bullet to rewrite or delete every Popen-based happy-path voter-dispatch test and assert `VOTER_1_TOOL=codex-validity` (or cursor/claude fallback labels) on the externals-present path

### FINDING_4: Prompt invariant smoke still hardcodes legacy prompt filenames
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: major
- **Concern**: The prompt-invariant harness still asserts legacy plan/design voter prompt basenames, so the new semantic prompt/output names can cause lint or CI failures even when the feature works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add scripts/test-prompt-template-invariants.sh, and its md if needed, to the plan. Update the plan-voter smoke to assert the new semantic prompt files or a happy-path manifest while preserving the Verify silently and Output ONLY vote lines checks.
  - From Codex-Requirements: Add ### UPDATED: scripts/test-prompt-template-invariants.sh and retarget the smoke assertions to the new policy-derived prompt files, or discover the generated prompt files from the voter manifest instead of hard-coded legacy names.
