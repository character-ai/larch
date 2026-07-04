## Decision 1: nosession fallback symmetry
- **Question**: Should the fix reuse the existing `HOOK_ANTI_READ_POLL_DISCRIMINATOR` / `nosession` fallback logic for the generic-read counter?
- **Resolution**: Yes — `session_hash` at line 50 already incorporates that fallback. Changing `state-${cwd_hash}.tsv` to `state-${session_hash}-${cwd_hash}.tsv` automatically reuses it with no additional code.
- **Source**: codebase

## Decision 2: intentionality of cwd-only key
- **Question**: Was the generic-read counter left cwd-only deliberately?
- **Resolution**: No evidence of intentional design. The task-output counter was properly scoped when session-awareness was added; the generic-read counter was simply not updated in the same pass. The sibling doc (`hook-anti-read-poll.md`) already notes the asymmetry in its State section, providing further evidence it was an oversight.
- **Source**: codebase

## Decision 3: impact on existing state files
- **Resolution**: Renaming the generic-read key is a non-disruptive reset. Old `state-${cwd_hash}.tsv` files become orphaned in TMPDIR; the hook is fail-open and state expires in 30s, so orphaned files are harmless.
- **Source**: codebase

## Decision 4: test path updates required
- **Resolution**: Three tests in `test-hook-anti-read-poll.sh` directly construct the state file path using `state-$(... cksum).tsv`. After the fix the path becomes `state-${nosession_hash}-${cwd_hash}.tsv`. All three must be updated. A shared `nosession_hash` variable should be computed once near the top.
- **Source**: codebase
