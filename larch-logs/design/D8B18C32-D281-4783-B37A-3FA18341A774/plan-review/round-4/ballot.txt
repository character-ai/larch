Verifying the cited locations so merged findings reflect the same behavioral risks accurately.
### FINDING_1: Step 4 rewrite omits `is-larch-dev-clone` / `LARCH_DEV_CLONE` gate
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: A Step 4 rewrite that follows only the proposed bullet list can drop the `stall-recovery-report.sh is-larch-dev-clone --implement-tmpdir "$IMPLEMENT_TMPDIR"` call and the subsequent `LARCH_DEV_CLONE` parse before `bug-body`. Without that mechanical discriminator (fork suppression plus working-tree marker check), dev-clone vs consumer/`--forked` routing breaks: consumer runs may auto-invoke `/larch:issue` when they should print `## Action required — file larch bug`, or dev-clone runs may skip filing. `test-implement-structure.sh` does not grep for this call, so CI could still pass after the omission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Edge: Keep the current order explicitly: is-larch-dev-clone --implement-tmpdir before bug-body; parse LARCH_DEV_CLONE; branch filing vs chat-print on that KV; add this gate to the Leave unchanged list alongside attempt_count and the consumer path
  - From Cursor-Pragmatic: Add is-larch-dev-clclone to Leave unchanged or as the first procedural bullet: call stall-recovery-report.sh is-larch-dev-clone --implement-tmpdir "$IMPLEMENT_TMPDIR", parse LARCH_DEV_CLONE, then bug-body; gate /larch:issue and env normalization on LARCH_DEV_CLONE=true
  - From Cursor-Requirements: Add is-larch-dev-clone --implement-tmpdir "$IMPLEMENT_TMPDIR" and parse LARCH_DEV_CLONE to the Step 4 rewrite bullets, or list that call explicitly under Leave unchanged alongside the attempt_count gate and consumer/--forked print path

### FINDING_2: Unsafe-step regression fixture does not exercise sanitizer rewrite
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The proposed unsafe-step regression uses `STALL_STEP=8a<script>`, but the prefix glob (`8[[:alnum:]-]*`) already rejects that full string because `<` terminates the suffix. The fixture would pass under current `safe_step_value` even if the sanitizer rewrite is skipped or reverted to the old glob, so CI would not catch that regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Use an alnum-only invalid suffix the old matcher accepts and the allowlist rejects (e.g. STALL_STEP=8aevil); assert heading uses at unknown and the suffix is absent from the title line
