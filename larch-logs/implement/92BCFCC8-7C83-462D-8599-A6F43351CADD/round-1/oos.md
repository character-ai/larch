### OOS_1: [OUT_OF_SCOPE] Workflow documentation has stale authorization guidance
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Workflow documentation still shows `block-issue` without operator authorization, so operators following it encounter authorization failures.
- **Suggested revisions (informational for voters; coder decides):**
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_2: [OUT_OF_SCOPE] Dependency mutation APIs have inconsistent authorization
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `issue add-blocked-by` retains legacy authorization while `block-issue` is tightened, leaving dependency mutation APIs inconsistent.
- **Suggested revisions (informational for voters; coder decides):**
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_3: [OUT_OF_SCOPE] Evidence-path allowlist condition is tautological
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The evidence path condition does not enforce an actual allowlist, which may mislead maintainers about path restrictions.
- **Suggested revisions (informational for voters; coder decides):**
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_4: [OUT_OF_SCOPE] Dependency caller tests assert the obsolete argv
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The dependency edge-apply test still expects the old `block-issue` arguments and can remain green while production calls fail.
- **Suggested revisions (informational for voters; coder decides):**
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_5: [OUT_OF_SCOPE] Partition tests do not exercise real block-issue arguments
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Partition tests mock dependency mutation and therefore cannot detect regressions in the operator-authorization argv.
- **Suggested revisions (informational for voters; coder decides):**
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_6: [OUT_OF_SCOPE] External probe allowlist lacks tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The external codex-model-readonly probe allowlist has no acceptance or rejection coverage, allowing drift to go unnoticed.
- **Suggested revisions (informational for voters; coder decides):**
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_7: [OUT_OF_SCOPE] Blocking issues lack triage preconditions
- **Reviewer(s)**: dyn-dyn-cas-mutations
- **Severity**: major
- **Concern**: Triage-controlled dependency writes validate only the blocked target, not whether the blocker is secure, protected, or closed.
- **Suggested revisions (informational for voters; coder decides):**
  - From dyn-dyn-cas-mutations: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_8: [OUT_OF_SCOPE] Dependency postconditions are not verified atomically
- **Reviewer(s)**: dyn-dyn-cas-mutations
- **Severity**: minor
- **Concern**: Relation presence and timestamp advancement are checked in separate reads, allowing a concurrent change between postcondition checks.
- **Suggested revisions (informational for voters; coder decides):**
  - From dyn-dyn-cas-mutations: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_9: [OUT_OF_SCOPE] Valid-path stale snapshot coverage is missing
- **Reviewer(s)**: dyn-dyn-cas-mutations
- **Severity**: major
- **Concern**: Tests do not verify that the valid body-edit path refuses mutation when `updatedAt` changes after the initial snapshot.
- **Suggested revisions (informational for voters; coder decides):**
  - From dyn-dyn-cas-mutations: Address the concern above.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false
