### OOS_1: [OUT_OF_SCOPE] Cursor strip-regex guard number mismatch is pre-existing
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-prompt-contract
- **Severity**: nit
- **Concern**: The Cursor strip regex still targets guard #9 for spawn text while the interactive-subprocess guard is #8. The mismatch predates this branch and was marked out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Fix regex anchor in a follow-up if Cursor-specific guard omission is still desired.

### OOS_2: [OUT_OF_SCOPE] Security uncertainty clause removal is pre-existing and ancillary
- **Reviewer(s)**: dyn-dyn-prompt-contract
- **Severity**: latent
- **Concern**: Compression removed the OOS triage line “If uncertain whether a finding is security, do not file publicly.” That weakens conservative security routing guidance, but the issue is pre-existing and ancillary to the manifest, `needs_qa`, and commit contracts this pass targeted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-prompt-contract: If uncertain whether a finding is security, do not file publicly.

