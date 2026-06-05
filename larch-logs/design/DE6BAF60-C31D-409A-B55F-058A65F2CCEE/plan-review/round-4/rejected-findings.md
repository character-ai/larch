### [Plan Review] FINDING_3

### FINDING_3: Trusted-project `-c` adjacency is planned on a less direct env-key case
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Concern**: The trusted-project `-c` adjacency assertion is planned for `t10-env-key-false`, even though `t6m` already exercises the live login-path probe with argv capture. Extending `t10-env-key-false` adds sentinel setup without covering a distinct production surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add adjacency plus trust string assertions to the existing t6m argv log; keep t10-env-key-false limited to stamp miss, env-key argv, and sentinel leak checks


### [Plan Review] FINDING_6

### FINDING_6: Review-and-fix mv stub must delegate unrelated mv calls
- **Reviewer(s)**: Codex-dyn-stub-isolation
- **Severity**: important
- **Concern**: The plan’s instruction to mirror the implementer mv stub risks copying an unconditional `mv` failure stub into review-and-fix. That could break unrelated harness or fallback `mv` calls and create false failures rather than isolating the intended Codex auth-prep rename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-stub-isolation: Replace “mirroring” with an explicit conditional stub shape: fail only the larch-codex-review-fix-home.* config.toml rewrite/rename and exec /bin/mv "$@" for every other invocation.


### [Plan Review] FINDING_8

### FINDING_8: Mutation sanity needs negative controls for strip/capture wiring
- **Reviewer(s)**: Cursor-dyn-assertion-fidelity
- **Severity**: latent
- **Concern**: The planned mutation sanity checks only flip expected values, which can catch inverted assertions but not vacuous wiring. A grep against an unstripped, missing, or wrong capture file may still fail when flipped without proving the assertion observes the production processing step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-assertion-fidelity: Add one negative control per harness: skip the strip/capture step (or point at a pre-strip snapshot) and require the new assertion to fail before the flip check.

