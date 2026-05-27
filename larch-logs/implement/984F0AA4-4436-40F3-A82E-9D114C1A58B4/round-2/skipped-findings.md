### FINDING_3: Missing design-env CLAUDE_PLUGIN_ROOT rejection tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `write-design-current-env.sh` now validates `CLAUDE_PLUGIN_ROOT`, but the design harness lacks rejection coverage and the stricter contract may break callers that previously relied on permissive exports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.



