# Review Round 2

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Missing pytest parity coverage after shell harness deletion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The retired shell harness coverage is not fully replaced. Regressions in `read --issue --prompt` append failure mapping, quiet stream contracts, summary upsert paths, CLI registry coverage, sentinel cases, cap overrides, retry/idempotency, and exit-code tables may pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Usage diagnostics can be hidden by quiet stderr redirection
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-stream-contracts-output.txt
- **Severity**: important
- **Concern**: `tracking_issue.py` calls `quiet_init()` before parser failures. Usage diagnostics can write to the quiet log instead of caller stderr, breaking the stderr-only usage contract for write verbs and parser-level read failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-stream-contracts-output.txt: Address the concern above.


### FINDING_3: Write CLIs validate inputs after repo or GitHub work
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Some write commands validate issue numbers, states, markers, comment IDs, or required files too late. Invalid local input can trigger repo resolution or `gh` reads and return the wrong exit class.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


