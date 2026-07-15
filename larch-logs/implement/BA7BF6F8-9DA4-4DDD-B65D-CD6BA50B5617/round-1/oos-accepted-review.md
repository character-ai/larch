### OOS_1: [OUT_OF_SCOPE] Missing required baselines are accepted on clean scans
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: A missing unreachable-branch occurrence baseline produces a successful clean scan instead of failing as the legacy rule did.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
