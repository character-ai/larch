### OOS_1: [OUT_OF_SCOPE] Add HTML redaction wrapper
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: The plan body is still inlined without the HTML redaction wrapper, leaving a pre-existing prompt-injection surface unaddressed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: No change required in this PR; track as separate hardening if desired

### OOS_2: [OUT_OF_SCOPE] Normalize TSV-only tier language
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-prompt-contract
- **Severity**: important
- **Concern**: The tier block still uses YES/NO vote language even though plan-review prompts are TSV-oriented, which can confuse models about the required output grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Fix in a separate prompt-consistency pass if desired
  - From dyn-dyn-prompt-contract: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Pin the updated test coverage wording
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The branch says `test_rendering.py` is UPDATED even though no test files changed; that is polish-level noise because existing substring tests still cover the invariant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Optionally add assert Cursor cannot read in cursor inline test when tightening coverage

### OOS_4: [OUT_OF_SCOPE] Show harness and acceptance evidence
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The required plan-test harness runs and live panel-prompt-sizes.tsv acceptance evidence are missing from the branch artifacts, so completion is unproven at merge time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Run plan testing strategy and live design acceptance before treating issue complete

### OOS_5: [OUT_OF_SCOPE] Remove numbered-findings/TSV dual-format ambiguity
- **Reviewer(s)**: dyn-dyn-prompt-contract
- **Severity**: important
- **Concern**: The scaffold still instructs reviewers to return numbered findings and separately mandates a TSV block, which can produce dual-format responses that the structured parser has to salvage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-prompt-contract: Address the concern above.

