### OOS_1: [OUT_OF_SCOPE] agreement scoreboard rows use the pre-reclassification result
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Agreement scoreboard rows are computed before the OOS-specific classification branch, so accepted OOS items show neutral in diagnostics even though tally accepts them; there is no filing impact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Compute agreement_row after the is_oos/classify_oos_result branch, or pass OOS-specific result into voter_agreement_row_from_panel.

### OOS_2: [OUT_OF_SCOPE] security tally tests only verify public-artifact absence
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Security tally coverage only checks that the public artifact is absent, so sidecar routing failures might leave security OOS nowhere durable without failing the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Extend test to assert security-oos-observations.md content when security OOS is tallied.

### OOS_3: [OUT_OF_SCOPE] stale comments still describe the removed pre-vote gate
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Stale comments still reference the removed pre-vote gate, which can mislead maintainers about the expected post-validation flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Update comments to describe post-prune voter dispatch only.

### OOS_4: [OUT_OF_SCOPE] oversized filing tests still describe unrelated multi-part split behavior
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The oversized filing test still exercises multi-part split behavior that is unrelated to the cap=1 rollup invariant, which can confuse readers about the scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: No change required unless cap>1 split policy is also being retired.

### OOS_5: [OUT_OF_SCOPE] OOS blocks without Vote tally are still treated as eligible for serialization
- **Reviewer(s)**: dyn-dyn-oos-routing
- **Severity**: latent
- **Concern**: _is_vote_tally_eligible still treats OOS blocks with no Vote tally line as eligible for serialization into the accepted sink, which matters more now that oos.md is projected in run logs and emit can rebuild the accepted sink from it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-routing: Address the concern above.

