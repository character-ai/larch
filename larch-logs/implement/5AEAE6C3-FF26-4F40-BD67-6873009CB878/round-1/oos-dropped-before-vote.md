### OOS_1: [OUT_OF_SCOPE] Submodule path normalization is behavior-preserving
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The `submodule_paths` cleanup deduplicates with a sorted set and still filters empty paths; the surrounding matching logic is unchanged, so the remaining risk is mostly around incidental ordering expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Harness prompt-surface additions are documented
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The harness now exposes four Python prompt surfaces, and the doc fix matches the Makefile; the instruction reordering is an explicit, documented trade-off rather than an active defect, so the main risk is future drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

