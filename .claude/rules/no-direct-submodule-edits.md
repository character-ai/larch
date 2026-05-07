---
paths: ["**/*"]
---

# No Direct Edits Inside Submodules

Files inside a checked-out git submodule of this superproject are off-limits to `Edit` and `Write`. The PreToolUse hook `scripts/block-submodule-edit.sh` (registered in `hooks/hooks.json`) emits a `permissionDecision: deny` and aborts the tool call.

If you need to change submodule content, file a PR in the submodule's own repo, then bump the pinned commit in this superproject via a normal `git submodule update` workflow.

Detection: the guard walks from the target file up to the first containing git repo and verifies via `rev-parse --show-superproject-working-tree` that the containing repo is a true submodule of the current superproject. Symlinks are resolved (bounded depth 40) before classification (#166); `cd` into a submodule does not bypass the guard because the hook anchors on `CLAUDE_PROJECT_DIR` (#150).
