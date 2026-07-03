### FINDING_2: Shared activation directory can cross-session-couple hooks
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: A shared user-level activation directory can let a sentinel from one Claude session arm a leaked hook in another session, so unrelated sessions can block each other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document as an explicit residual risk in SECURITY.md and deny-edit-write.md, or narrow the directory (for example only sentinels under the active session tmpdir tree) if a hook-readable session anchor exists without PPID matching.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### OOS_1: Deny envelope reason stays /research-branded while /bug wires the same hook
- **Description**: Deny envelope reason stays /research-branded while /bug wires the same hook. Scenario: When /bug is active and denies a Write outside /tmp, operators still see "/research is a read-only-repo skill…". Plan mandates byte-identical output. Confusing but not a functional regression on the leak fix.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/deny-edit-write.sh:54-65
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: test-deny-edit-write lint table still describes only always-active deny cases
- **Description**: test-deny-edit-write lint table still describes only always-active deny cases. Scenario: The make test-deny-edit-write row will be wrong after the activation gate lands; operators reading linting.md will miss inactive-gate, stale-sentinel, and token-scoping coverage.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: docs/linting.md:312
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: Deny reason string stays /research-specific while /bug also wires the hook
- **Description**: Deny reason string stays /research-specific while /bug also wires the hook. Scenario: When /bug is active and denies a Write outside /tmp, operators still see "/research is a read-only-repo skill...". The plan preserves byte-identical JSON for harness stability.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/deny-edit-write.sh:54-65
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: The `make test-deny-edit-write` lint table row still describes the hook as always enforcing deny-outside-`/tmp` with no activation-gate axis
- **Description**: The `make test-deny-edit-write` lint table row still describes the hook as always enforcing deny-outside-`/tmp` with no activation-gate axis. Scenario: The plan updates `scripts/test-deny-edit-write.md` and several skill docs but not this lint catalog row, so operators reading `docs/linting.md` may miss that inactive-gate allow behavior is now the primary leak fix
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: docs/linting.md:312
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

