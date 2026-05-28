### FINDING_1: Cap-overflow warning over-attributes remaining cache overflow to pinned entries
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: latent
- **Concern**: The proposed post-loop warning can misleadingly blame pinned entries when the prune loop may also have stopped because removable candidate deletion failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Change the warning text to name both causes, e.g. pinned entries or prune failures blocked full trim, or only use the pinning-specific text when PRUNE_FAILED_VERSIONS is empty.


### FINDING_2: Behavior change omits required sibling script documentation update
- **Reviewer(s)**: Cursor-dyn-sibling-contract, Codex-dyn-sibling-contract
- **Severity**: important
- **Concern**: The plan changes `skills/upgrade-larch/scripts/upgrade-larch.sh` behavior but does not update the required sibling `.md` documentation for the prune-loop behavior and new warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-sibling-contract, Codex-dyn-sibling-contract: Add skills/upgrade-larch/scripts/upgrade-larch.md to the plan and update the prune behavior text to include the post-loop cache-cap warning when pinned entries leave the cache above KEEP_LIMIT


