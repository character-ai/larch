### [Plan Review] FINDING_2

### FINDING_2: Unsafe-step regression fixture does not exercise sanitizer rewrite
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The proposed unsafe-step regression uses `STALL_STEP=8a<script>`, but the prefix glob (`8[[:alnum:]-]*`) already rejects that full string because `<` terminates the suffix. The fixture would pass under current `safe_step_value` even if the sanitizer rewrite is skipped or reverted to the old glob, so CI would not catch that regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Use an alnum-only invalid suffix the old matcher accepts and the allowlist rejects (e.g. STALL_STEP=8aevil); assert heading uses at unknown and the suffix is absent from the title line

