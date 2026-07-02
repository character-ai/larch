### OOS_1: [OUT_OF_SCOPE] `dynamic_archetypes_main` accepts `--max-archetypes` up to 8
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: In `python/larch/design/plan_scout.py:671`, `dynamic_archetypes_main` still accepts `--max-archetypes` up to 8. Direct scout CLI calls outside skill wrappers can emit more than one archetype.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Clamp dynamic_archetypes_main to 0..1 or document it as non-review-only.

### OOS_2: [OUT_OF_SCOPE] Direct CLI can pass `--round-cap` above 2
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: In `python/larch/review/review_and_fix.py`, explicit `--round-cap` above 2 still works for direct CLI invocation. Test harnesses can exceed the shipped cap-2 contract outside skill entrypoints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Reject or warn on --round-cap greater than 2 outside test-only paths if desired.

### OOS_3: [OUT_OF_SCOPE] Unit tests use `max_archetypes=3` inconsistent with production 0..1 ceiling
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: In `python/tests/design/test_plan_scout.py`, many unit tests still pass `max_archetypes=3` to internal helpers. Internal API tests no longer mirror the 0..1 production ceiling though CLI rejection is tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Retarget helper tests to max_archetypes=1 for consistency.

