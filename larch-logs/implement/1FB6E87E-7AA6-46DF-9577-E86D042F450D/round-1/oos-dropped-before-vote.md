### OOS_1: [OUT_OF_SCOPE] Empty-cwd clone-gating case is still missing for implement
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The #6080 empty-cwd foreign-clone allow case is not exercised for implement task-output reads. That leaves the clone-gating fix unverified in the exact scenario it is meant to protect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a #6080 empty-cwd Bash cat tasks/foo.output case with a foreign-clone live marker and assert allow.

### OOS_2: [OUT_OF_SCOPE] Clamp predicate mismatch between design and implement
- **Reviewer(s)**: dyn-dyn-hook-guard
- **Severity**: latent
- **Concern**: The design and implement clamp predicates use different file tests, so the two checks are not behaviorally aligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-guard: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Missing full #6080 integration sequence
- **Reviewer(s)**: dyn-dyn-hook-guard
- **Severity**: latent
- **Concern**: There is no end-to-end test for the full #6080 sequence. The current coverage does not prove denied output read, allowed sentinel probe, then allowed output read after sentinel creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-guard: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Token-count baseline drift is generated metadata
- **Reviewer(s)**: dyn-dyn-hook-guard
- **Severity**: nit
- **Concern**: The token-count drift in the diff is generated metadata rather than a functional behavior change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-guard: Address the concern above.

