### OOS_1: [OUT_OF_SCOPE] Both-externals-down still launches a single Claude voter
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: blocking
- **Concern**: The both-externals-down branch still launches a single Claude voter on slot 1. That matches the Gate C plan, but it conflicts with the issue text that asked for zero automated voters and main-agent adjudication.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Missing explicit `VOTER_1_TOOL=codex-validity` assertion
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: latent
- **Concern**: The default happy-path test still lacks an explicit `VOTER_1_TOOL=codex-validity` assert, so a slot-1 label regression could slip past CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

