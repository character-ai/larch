### OOS_1: [OUT_OF_SCOPE] Assessment tests do not pin `launch-claude-subprocess` argv
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Assessment tests mock `subprocess.run` but do not pin `launch-claude-subprocess` argv. A revert to bare `claude --print` would not be caught by current tests. Assert `launch-claude-subprocess` and `--timing-task-kind exec-issue-assessment` appear in the mocked argv.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


