# Review Round 2

- Mode: `diff`
- 5 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_3: Oversized accepted OOS still splits into parts
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: A single oversized accepted OOS body can still split into multiple public issues because only rollup-marker bodies use the summarizer, so cap=1 batches still take the split path instead of yielding one summarized issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Summarize every oversized OOS body when the effective per-run cap is one, or pass capped-batch state into _body_files_for_item and return one summarized body file.
  - From cursor-specialist-edge-cases: Use _summarize_to_github_limit for cap=1 single-item batches; retire split path for that case.
  - From codex-specialist-edge-cases: summarize any over-limit item when the effective OOS issue cap is one


### FINDING_4: Panel-failed rounds can publish raw oos.md
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Panel-failed rounds can publish raw collector oos.md, and a security-tagged OOS can remain in it when threshold_ok is false and get committed in round logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: clear or security-route oos.md before panel-failed emit/flush


### FINDING_5: Missing run-log projection coverage for oos.md
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: Plan-required run-log projection coverage for oos.md inclusion and retired pre-vote artifacts is missing, so rejected-OOS audit regressions can ship without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add _round_artifact_included and write-round tests for oos.md projection and retired artifact omission.


### FINDING_6: All-OOS branch coverage misses alternate paths
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: All-OOS voter dispatch is tested only on the normal review-core branch, so validation-exhausted and empty-merge paths can skip voting without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add branch-specific all-OOS harness tests for validation-exhausted and empty-merge paths.
  - From codex-specialist-testing: Add all-OOS tests for validation-exhausted and empty-merge that assert voters run and accepted OOS reaches the tally sink.


### FINDING_7: OOS prompt wording drift lacks regression tests
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: OOS prompt wording can drift back toward materiality wording because the legitimacy wording is not asserted in the proposal or voter renderer outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Assert legitimacy substrings in oos_proposal_instruction and voter oos_rule output.
  - From codex-specialist-testing: Add rendering tests for oos_proposal_instruction and render_voter_main OOS voter text.


