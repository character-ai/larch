# Review Round 1

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Heartbeats on stderr may not fix empty stdout/task-output hang
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-dyn-heartbeat-concurrency-output.txt
- **Severity**: important
- **Concern**: Repair-loop liveness breadcrumbs are emitted only to stderr (`file=sys.stderr`), while issue #5286 and the repair-loop contract describe an empty background task-output file that orchestrators read once after completion, parsing stdout keys (`NEXT_ACTION`, `LOOP_STATUS`). If background Bash capture is stdout-only or does not surface stderr to the operator-visible `.output` sidecar, stdout stays blank for the full lint-fix duration (10–40+ minutes) and the hang appearance persists despite stderr heartbeats and passing capsys unit tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add background-capture integration test; or emit flushed PROGRESS= lines on stdout documented as non-terminal; verify end-to-end in implement harness.
  - From codex-specialist-correctness-output.txt: Emit safe STATUS progress lines to stdout and teach parsers/tests to ignore them, or explicitly merge stderr into the watched output and document that contract.
  - From cursor-specialist-edge-cases-output.txt: Verify stderr is visible on the production path; if task-output is stdout-only emit a stdout liveness line outside the parsed KV set or document stderr as the observation surface
  - From codex-specialist-testing-output.txt: Emit STATUS progress lines to stdout with flush and update parsing/tests to ignore STATUS, or change the orchestrator contract so stderr is captured into the same progress stream.
  - From dyn-dyn-heartbeat-concurrency-output.txt: Emit flushed, orchestrator-ignorable **stdout** liveness lines (for example `PROGRESS=lint-fix-running site=… elapsed=…s`) that are outside the `NEXT_ACTION`/`LOOP_STATUS` key set section 3 extracts, or confirm and document that the Bash capture layer merges stderr into the task-output file and add an integration test that asserts non-empty `.output` growth during a slow mocked `run_lint_fix`.


