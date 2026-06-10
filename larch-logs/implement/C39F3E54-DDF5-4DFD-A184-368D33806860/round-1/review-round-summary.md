# Review Round 1

- Mode: `diff`
- 4 accepted, 12 rejected (3 neutral)

## Accepted Findings

### FINDING_10: Delimiter parser accepts nested plan and summary envelopes
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `launch-claude-drafter.sh` accepts responses where the plan envelope is nested inside the summary envelope, allowing corrupted summaries containing plan sentinels to be promoted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Drafter dirty-tree path hard-aborts instead of using recovery flow
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-drafter-integration-output.txt
- **Severity**: important
- **Concern**: Confirmed drafter mutations write `dirty-tree-detected.env` and exit without the standard dirty-tree `AskUserQuestion` recovery loop used by other `/design` external boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-drafter-integration-output.txt: Address the concern above.


### FINDING_4: Once-only postplan inline fallback is not mechanically implemented
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-drafter-integration-output.txt
- **Severity**: important
- **Concern**: Drafter-sourced plans that fail postplan validation with `rc=10` go to the normal validator path instead of writing the retry sentinel, clearing stale summary state, rerunning inline Step 2b once, and re-entering postplan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-drafter-integration-output.txt: Address the concern above.


### FINDING_5: Drafter prompt under-carries Step 2b synthesis and disposition semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The subprocess prompt omits binding inline Step 2b rules for disposition branches, sentinel synthesis cases, optional/required artifact handling, and degraded/no-sketch flows, allowing semantically wrong plans to pass structural checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


