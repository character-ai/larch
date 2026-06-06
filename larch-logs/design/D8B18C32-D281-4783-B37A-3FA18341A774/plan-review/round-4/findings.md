### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:19
- **Concern**: Step 4 rewrite bullets omit the is-larch-dev-clone call and LARCH_DEV_CLONE branch gate. Scenario: An implementer who follows only the listed bullets can drop stall-recovery-report.sh is-larch-dev-clone; dev-clone vs consumer/--forked routing then has no mechanical discriminator (fork suppression plus working-tree marker check) and may auto-file in consumer repos or skip filing in dev clones
- **Proposed resolution**: Keep the current order explicitly: is-larch-dev-clone --implement-tmpdir before bug-body; parse LARCH_DEV_CLONE; branch filing vs chat-print on that KV; add this gate to the Leave unchanged list alongside attempt_count and the consumer path

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-stall-recovery-report.sh:114-117
- **Concern**: Unsafe-step regression uses STALL_STEP=8a<script> but prefix glob already rejects that full string. Scenario: The proposed fixture passes on current safe_step_value (8[[:alnum:]-]* requires a full-string match; < terminates the suffix), so CI would not fail if the sanitizer rewrite is skipped or reverted to the old glob
- **Proposed resolution**: Use an alnum-only invalid suffix the old matcher accepts and the allowlist rejects (e.g. STALL_STEP=8aevil); assert heading uses at unknown and the suffix is absent from the title line

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/references/stall-recovery.md:19
- **Concern**: Step 4 rewrite bullets omit explicit preservation of is-larch-dev-clone before bug-body. Scenario: Replacing the single step-4 paragraph with the new bullet list can drop the is-larch-dev-clone call while only attempt_count and consumer print paths are listed under Leave unchanged; orchestrator then loses LARCH_DEV_CLONE gating and may auto-file in consumer repos or skip dev-clone filing
- **Proposed resolution**: Add is-larch-dev-clclone to Leave unchanged or as the first procedural bullet: call stall-recovery-report.sh is-larch-dev-clone --implement-tmpdir "$IMPLEMENT_TMPDIR", parse LARCH_DEV_CLONE, then bug-body; gate /larch:issue and env normalization on LARCH_DEV_CLONE=true

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:19
- **Concern**: Step 4 rewrite omits the is-larch-dev-clone subcommand and LARCH_DEV_CLONE parse. Scenario: A full Step 4 rewrite from the plan bullets can drop stall-recovery-report.sh is-larch-dev-clone before bug-body; test-implement-structure.sh does not grep for it, so CI would still pass while consumer or forked runs wrongly invoke /larch:issue or skip the Action-required print path
- **Proposed resolution**: Add is-larch-dev-clone --implement-tmpdir "$IMPLEMENT_TMPDIR" and parse LARCH_DEV_CLONE to the Step 4 rewrite bullets, or list that call explicitly under Leave unchanged alongside the attempt_count gate and consumer/--forked print path
