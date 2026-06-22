### OOS_4: [OUT_OF_SCOPE] GitHub body-size limit for OOS rollups (operational mitigation)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Removing excerpt caps is correct for #5097, but a `cap=1` rollup of many large OOS items can exceed GitHub's issue-body limit and fail at `/issue` create time with no preflight size check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Operational mitigation only if this shows up in practice (split rollups, cap tuning, or a fail-closed size probe before filing); not required for the core bug fix.


