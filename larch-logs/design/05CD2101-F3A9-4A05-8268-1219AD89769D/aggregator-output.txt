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

### FINDING_3: All-pinned overflow test fixture may miss implicit preservation paths
- **Reviewer(s)**: Cursor-dyn-test-pin-completeness, Codex-dyn-test-pin-completeness
- **Severity**: important
- **Concern**: The planned test does not specify fixture values tightly enough to prove both implicit preservation paths are covered while also exercising the cap-overflow warning path with zero evictable candidates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-pin-completeness, Codex-dyn-test-pin-completeness: Revise the plan's test fixture to specify post-install >8 entries and zero evictable candidates, for example GH_OUTPUT and INSTALL_RESULT_VERSION = 50.0.10, PLUGIN_ROOT_VERSION = 50.0.1, CACHED_VERSIONS = 50.0.1 through 50.0.9, SESSION_PINNED_VERSIONS = 50.0.2 through 50.0.9, with no rm/stat failure knobs; then assert all original cache dirs plus 50.0.10 remain and the cap-overflow warning appears.
