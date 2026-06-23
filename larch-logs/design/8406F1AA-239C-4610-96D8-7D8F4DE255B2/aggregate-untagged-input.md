### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/checks-repair-loop.md:64
- **Concern**: Outer main-agent-edit re-entry omits pinned --site/--checks-site contract. Scenario: Section 4 tells orchestrators to re-invoke `checks repair-loop` with only the new `--checks-log` after main-agent edits. Step 5 MAV/coder requires `--site step5-mav --checks-site step5-review-fixes`; defaulting `--checks-site` to `--site` reruns internal rechecks under `step5-mav` instead of `step5-review-fixes`, so post-edit verification can diverge from the capture fence and mis-route `NEXT_ACTION`.
- **Proposed resolution**: In section 4 `main-agent-edit`, require every re-invocation to repeat the same pinned `--site` / optional `--checks-site` pair from section 2 for that call site (not only the updated `--checks-log`).

### FINDING_2:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:243-260
- **Concern**: Testing strategy bash fence is unterminated. Scenario: The plan command parser will treat prose and diff_* trailers after line 245 as shell invocations, including Then, `make, No, and diff_added:, which can break plan command validation and make verification noisy or blocked
- **Proposed resolution**: Close the bash fence after the two pytest commands, then put the make commands in a separate closed bash fence or one closed fence containing commands only
