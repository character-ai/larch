### OOS_7: [OUT_OF_SCOPE] risk-integration: `lib-cursor-auth.md` documents wrong test command
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Doc says `bash python/test_launch_review.py`. Operators following doc get wrong command.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Use `make test-launch-review` or `python3 -m pytest python/test_launch_review.py`.


