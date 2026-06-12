### OOS_1: [OUT_OF_SCOPE] Missing consumer documentation for public upstream filing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Consumer-facing permissions docs omit the new public upstream failure-report behavior, including gh identity, Tier B safety boundaries, comment boundaries, and fallback printing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Implementer waterfall docs disagree with bootstrap behavior
- **Reviewer(s)**: dyn-risk-integration-output.txt
- **Severity**: latent
- **Concern**: Bootstrap now prefers Cursor, then Codex, then Claude, while `SKILL.md` still describes an older Codex, then Cursor, then Claude fallback order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-risk-integration-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] Tier B dedup comment validation can fail open
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-architecture-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: Tier B dedup comments can skip full sensitive-token validation when the sensitive corpus or validator is missing, letting public comments post with only weaker grep checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-architecture-output.txt, dyn-risk-integration-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] SECURITY.md bail enum is stale
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` omits the `protected-path-edit-required-out-of-scope` bail token added in stall recovery reporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


