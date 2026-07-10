### FINDING_5: Dispatcher test coverage is missing the binary-present external-coder path
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The current tests only pin the dispatcher’s token-mark behavior for the binary-missing path, so they do not guard against accidental double-marking once launchers own Step 2 token marks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: `Add a run_dispatch_main test with coder=codex or cursor, binary-found=true, and assert zero dispatcher token mark calls while launcher tests assert exactly one token mark after budget preflight`


