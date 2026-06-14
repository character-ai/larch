# Review Round 2

- Mode: `diff`
- 1 accepted, 8 rejected (2 neutral)

## Accepted Findings

### FINDING_4: TERM-trap regression test does not assert stub launcher PID death
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The TERM-trap regression in `scripts/test-dispatch-with-waterfall.sh` checks phase-wrapper death but not the cursor stub launcher PID. The stub `sleep 30` can survive while the wrapper subshell dies, so CI passes while `ps` still shows the orphan class from the issue. A fix that kills the subshell wrapper but leaves the sleeping cursor stub (or deeper children) alive would pass CI while operators still see active shells after Step 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Assert kill -0 on term_stub_pid fails after dispatcher TERM/wait.
  - From cursor-specialist-testing-output.txt: After dispatcher TERM/wait, assert ! kill -0 on term_stub_pid; add success-path cleanup for the stub so the 30s sleep cannot leak across harness cases.


