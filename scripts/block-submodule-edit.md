# `block-submodule-edit.sh` contract

`scripts/block-submodule-edit.sh` is the fail-closed PreToolUse shim for the Rust-owned `hook block-submodule-edit` command. It forwards stdin through `scripts/larch.sh` with `LARCH_BOOTSTRAP_NO_INSTALL=1`. A missing launcher, unavailable verified binary, or nonzero Rust command emits the shim's static deny envelope and exits zero; hooks never download or install an executable.

The Rust owner anchors repository discovery to `CLAUDE_PROJECT_DIR`, then falls back to the current directory. It resolves the target through a bounded symlink walk and its nearest existing ancestor. A target is denied only when its discovered repository matches both the worktree and Git directory of an initialized, direct submodule checkout reported by the superproject. An unrelated nested repository remains allowed.

Malformed JSON and a relative target deny before repository discovery. Once a repository root is established, a symlink cycle denies. Clearly non-Git targets and unavailable repository metadata fail open. The migrated regression cases live in `crates/larch-cli/src/hook_commands.rs` and use the shared Git fixture surface.
