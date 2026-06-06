### FINDING_1: Step 0 parent rehydration snippet is missing the outer `fi`
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements, Cursor-Edge, Cursor-dyn-shell-fence-flow, Cursor-dyn-contract-sync, Cursor-Innovation, Cursor-dyn-harness-wiring, Cursor-dyn-scope-control, Codex-dyn-shell-fence-flow, Codex-dyn-harness-wiring, Codex-dyn-contract-sync
- **Severity**: important
- **Concern**: The planned Step 0 parent rehydration block opens an outer `if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then` but only closes the nested `plugin-root.env` check, leaving both initial and dirty-tree resume Step 0 Bash fences syntactically invalid before routing parse can run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements: Close the outer if before export: after the inner fi add fi, then export CLAUDE_PLUGIN_ROOT (initial and dirty-tree resume insertion points)
  - From Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements: Close the outer if before export CLAUDE_PLUGIN_ROOT in the proposed block.
  - From Cursor-Edge, Cursor-dyn-shell-fence-flow, Cursor-dyn-contract-sync: Close the outer `if` before `export CLAUDE_PLUGIN_ROOT` (export should run unconditionally after the conditional source)
  - From Cursor-Innovation, Cursor-dyn-harness-wiring: Add fi before export CLAUDE_PLUGIN_ROOT so the block reads: outer if → parse _inv_tmpdir → inner if source plugin-root.env → fi → fi → export CLAUDE_PLUGIN_ROOT
  - From Cursor-dyn-scope-control: Add the missing closing fi for the outer if before export CLAUDE_PLUGIN_ROOT and verify both initial and resume fences shellcheck clean
  - From Codex-dyn-shell-fence-flow: Add the missing outer `fi` before `export CLAUDE_PLUGIN_ROOT` in both proposed insertions; keep `export CLAUDE_PLUGIN_ROOT` outside the guard.
  - From Codex-dyn-harness-wiring: Add the missing outer fi before export CLAUDE_PLUGIN_ROOT, leaving export outside the if so already-set values are exported too
  - From Codex-dyn-contract-sync: Add the closing fi before export CLAUDE_PLUGIN_ROOT in both inserted blocks, or use a one-line guarded source form


