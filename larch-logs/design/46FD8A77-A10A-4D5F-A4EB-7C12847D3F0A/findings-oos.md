### OOS_1: Deny envelope reason stays /research-branded while /bug wires the same hook
- **Description**: Deny envelope reason stays /research-branded while /bug wires the same hook. Scenario: When /bug is active and denies a Write outside /tmp, operators still see "/research is a read-only-repo skill…". Plan mandates byte-identical output. Confusing but not a functional regression on the leak fix.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/deny-edit-write.sh:54-65
- **Phase**: design



### OOS_2: test-deny-edit-write lint table still describes only always-active deny cases
- **Description**: test-deny-edit-write lint table still describes only always-active deny cases. Scenario: The make test-deny-edit-write row will be wrong after the activation gate lands; operators reading linting.md will miss inactive-gate, stale-sentinel, and token-scoping coverage.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: docs/linting.md:312
- **Phase**: design



### OOS_3: Deny reason string stays /research-specific while /bug also wires the hook
- **Description**: Deny reason string stays /research-specific while /bug also wires the hook. Scenario: When /bug is active and denies a Write outside /tmp, operators still see "/research is a read-only-repo skill...". The plan preserves byte-identical JSON for harness stability.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/deny-edit-write.sh:54-65
- **Phase**: design



### OOS_4: The `make test-deny-edit-write` lint table row still describes the hook as always enforcing deny-outside-`/tmp` with no activation-gate axis
- **Description**: The `make test-deny-edit-write` lint table row still describes the hook as always enforcing deny-outside-`/tmp` with no activation-gate axis. Scenario: The plan updates `scripts/test-deny-edit-write.md` and several skill docs but not this lint catalog row, so operators reading `docs/linting.md` may miss that inactive-gate allow behavior is now the primary leak fix
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: docs/linting.md:312
- **Phase**: design



