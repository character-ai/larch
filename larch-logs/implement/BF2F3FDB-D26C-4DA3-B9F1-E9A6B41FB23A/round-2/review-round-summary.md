# Review Round 2

- Mode: `diff`
- 5 accepted, 7 rejected (7 exonerated)

## Accepted Findings

### FINDING_1: Step 18 marks final summary emitted before orchestrator emit
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 18 Bash touches `.step17-emitted` before the orchestrator performs the verbatim top-chat emit. This can make the orchestrator treat the summary as already emitted and skip the visible full-body summary, recreating invisible final summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: Step 18 body-diff test checks only Cost substring
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/test-write-final-report.sh` could pass even if the refreshed summary loses required structure, because the changed-body path asserts only a `Cost` substring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Test pins premature Bash mutation of `.step17-emitted`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-render-cost-line-callsites.sh` currently allows or pins the Bash-side `.step17-emitted` touch instead of enforcing that only orchestrator prose writes the sentinel after a successful verbatim emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_5: Design summary prose misstates the visibility contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` still says `render-final-summary.sh` prints the summary to chat, which can lead an agent to treat collapsed Bash output as sufficient and skip the required orchestrator verbatim emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_6: #2970 changelog entry is under Changed instead of Fixed
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The #2970 entry is described as a fix but is categorized under `### Changed`, weakening the semver signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


