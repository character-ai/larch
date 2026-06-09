# Review Round 4

- Mode: `diff`
- 8 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_10: Warn on keepalive write failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: _write_session_identity() swallows .larch-keepalive write failures with suppress(OSError) and emits no warning, unlike retired session-setup.sh. Full disk, permission error, or read-only session tmpdir can leave session-id written but .larch-keepalive missing with no stderr signal, degrading hook routing while setup appears healthy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Port entry-gate failure matrix tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The deleted test-session-entry-gate.sh failure matrix has no pytest replacement; only success paths are tested. implement-bootstrap.sh entry-gate validation regressions such as wrong exit code or missing GATE_ERROR= would not be caught after harness deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Fix migrated CLI harness fixtures
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retargeted harness fixtures create filenames containing the session subcommand instead of providing an executable python/cli.py dispatcher. CI harnesses fail during fixture setup or exercise no valid migrated CLI stub, leaving migrated call paths unverifiable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Add missing writer-guard negative tests
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Writer-guard negative tests promised in the plan are absent; only out-of-root rejection is tested. Future edits could weaken NEVER #14 enforcement without CI catching CR/LF rejection, disallowed keys, or carve-out path regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_6: Reject carriage returns in KV readers
- **Reviewer(s)**: codex-specialist-security-output.txt
- **Severity**: important
- **Concern**: KV readers use splitlines(), so bare carriage returns become new logical records instead of rejected data. A tampered session/state file such as SAFE=value\rLARCH_TOKEN_SESSION_ID=attacker can make read-key/setup/restore-finalize-state consume a forged allowlisted key despite the CR/LF writer guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Address the concern above.


### FINDING_7: Preserve design tmpdir validation stderr parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: validate_design_tmpdir embeds ERROR= and write_design_env_main re-prefixes with ERROR=, producing a double ERROR= prefix on relative --design-tmpdir and breaking exact stderr parity with retired bash behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: cleanup-tmpdir should succeed for already-absent targets
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: cleanup-tmpdir returns failure when an allowed tempdir target was already removed, unlike the retired rm -rf contract. Retry or duplicate cleanup paths can report teardown/cleanup failure even though the tempdir is already gone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Restore write-id uuidgen fallback parity
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: write-id does not implement the planned uuidgen-else-basename behavior; it always uses Python uuid4. On a host without uuidgen, old write-session-id.sh wrote the parent tmpdir basename, while the new CLI writes a random UUID.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


