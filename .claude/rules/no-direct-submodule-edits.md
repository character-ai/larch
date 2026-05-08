---
paths: ["**/*"]
---

# No Direct Edits Inside Submodules

Files inside a checked-out submodule of this superproject are
off-limits to `Edit` and `Write`. The PreToolUse hook
`scripts/block-submodule-edit.sh` (registered in `hooks/hooks.json`)
emits `permissionDecision: deny` and aborts tool calls.

To change submodule content, file a PR in the submodule repo. After it
lands, bump the superproject pin by checking out the desired SHA in the
submodule checkout, then run `git add <submodule-path>` and commit in the
superproject. `git submodule update` only checks out the recorded SHA; it
does not advance the pin.

Detection: the guard walks from target file to first containing git repo,
then verifies via `rev-parse --show-superproject-working-tree` that it is
a true submodule of the superproject. Symlinks resolve before
classification, bounded depth 40 (#166); `cd` into a submodule does not
bypass the guard because the hook anchors on `CLAUDE_PROJECT_DIR` (#150).
