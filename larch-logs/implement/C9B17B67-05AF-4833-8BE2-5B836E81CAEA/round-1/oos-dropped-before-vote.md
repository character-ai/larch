### OOS_1: [OUT_OF_SCOPE] Wrong reference target for the OOS triage policy
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `agents/_implementer-base.md` points to `skills/implement/SKILL.md` for the OOS triage policy, but the referenced section is in `skills/implement/references/execution-issues-tracking.md`; this looks pre-existing and outside the diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Uncertainty guidance is inconsistent across policy surfaces
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-public-routing
- **Severity**: latent
- **Concern**: The restored uncertainty rule is present in the implementer prompts, but the canonical OOS triage policy and other main-agent paths still do not carry the same explicit guidance, and the wording still leaves uncertainty around maybe-security inline-folding. That keeps the no-public-filing / private-disclosure behavior uneven across call sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-public-routing: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Prompt compression drift and missing regression guard
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: latent
- **Concern**: To stay within the +40-token cap, the branch recompressed the existing security bullet, which makes the diff harder to audit and can hide a future re-compression; there is also no targeted lint/test that anchors the restored caution substring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Revert prefix to pre-branch wording and append only the caution, or record the extra compression as an explicit plan waiver.
  - From cursor-specialist-testing: Add a small rendering or lint assertion for the caution in generated implementer prompts if mechanical regression guard is desired.

