### FINDING_13: Symlink refusal must cover ancestors, not just the leaf
- **Reviewer(s)**: Cursor-dyn-Statusline Security, Codex-dyn-Statusline Security
- **Severity**: major
- **Concern**: Leaf-only nofollow protection is insufficient for `~/.cache/larch/statusline.sh` and `~/.claude/settings.json`; a symlinked ancestor can redirect the SessionStart write to the wrong file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Statusline Security: session_env already uses _assert_no_symlink_path_or_ancestors before home-cache writes (python/larch/state/session_env.py:951-959, 905-906). Require the same for settings.json and launcher parents: reject symlinked path or ancestor, require regular non-symlink file for reads, write via atomic_write(nofollow=True), fail-open exit 0 with no stdout/stderr.
  - From Codex-dyn-Statusline Security: Add the existing ancestor-symlink guard before creating or writing either path, fail open on any symlinked parent, and keep SECURITY.md aligned by saying the installer only touches regular non-symlink files.


### FINDING_14: progress statusline must be registered for machine stdout
- **Reviewer(s)**: Codex-dyn-Statusline Security
- **Severity**: minor
- **Concern**: The new `progress statusline` command can be squelched by quiet-init unless it is registered as machine stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Statusline Security: Add ("progress", "statusline") to `_MACHINE_STDOUT_KEYS`; forbid quiet_init inside statusline_main


