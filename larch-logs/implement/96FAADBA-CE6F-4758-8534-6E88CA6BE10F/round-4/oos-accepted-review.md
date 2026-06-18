### OOS_5: [OUT_OF_SCOPE] deleted Bash case-22 clear/seed failure-path harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Bash case-22 clear/seed failure-path harness was deleted; pytest only covers success paths. Atomic rewrite failures (symlink/malformed/mv-fail) in `clear_stall`/`seed_terminal_state` could regress without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port a small subset of case-22 failure fixtures or soften docs/linting.md claims


