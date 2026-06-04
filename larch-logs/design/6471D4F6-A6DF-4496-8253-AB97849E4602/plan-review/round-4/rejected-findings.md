### [Plan Review] FINDING_6

### FINDING_6: SessionStart lib sourcing can use stale CLAUDE_PLUGIN_ROOT
- **Reviewer(s)**: Codex-dyn-shell-root-binding
- **Severity**: latent
- **Concern**: The SessionStart probe plan still allows sourcing `lib-sparse-dirs.sh` through `CLAUDE_PLUGIN_ROOT` instead of the executing script tree. A stale or mismatched plugin root could cause the hook to read an old allowlist and miss sparse-cone drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-shell-root-binding: Remove the CLAUDE_PLUGIN_ROOT alternative for this probe. Require source "$SCRIPT_DIR/lib-sparse-dirs.sh" or derive any root only from SCRIPT_DIR, and keep later PLUGIN_ROOT out of the allowlist path.


