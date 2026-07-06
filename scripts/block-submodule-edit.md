# scripts/block-submodule-edit.sh — contract

`scripts/block-submodule-edit.sh` is the PreToolUse hook that denies edits to files inside submodules. It is registered in `hooks/hooks.json`, anchors on `CLAUDE_PROJECT_DIR`, and emits a `permissionDecision: deny` envelope when a tool targets submodule content. `scripts/test-block-submodule-edit.sh` is its regression harness, wired into `make lint` via the `test-block-submodule` target; edits to the hook must stay in sync with the harness.

Do not edit files inside a checked-out submodule directly from this superproject. Make the content change in the submodule's own repository, land that PR, then bump the superproject pin by checking out the desired submodule SHA and committing the submodule path in the superproject. `git submodule update` only checks out the recorded SHA; it does not advance the pin.

Detection walks from the target file to the first containing git repository, then verifies with `rev-parse --show-superproject-working-tree` that the repository is a true submodule of the superproject. Symlinks resolve before classification with bounded depth, and `cd` into a submodule does not bypass the guard because the hook classifies the target path relative to `CLAUDE_PROJECT_DIR`.
