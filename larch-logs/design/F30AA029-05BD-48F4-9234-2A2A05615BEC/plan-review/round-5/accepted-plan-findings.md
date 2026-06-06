### FINDING_1: Step 0 rehydration block is missing the outer `fi`
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-shell-state, Codex-dyn-harness-wiring, Codex-Arch, Cursor-Edge, Cursor-Innovation, Codex-Edge, Codex-Innovation, Codex-Requirements, Codex-dyn-shell-state, Cursor-Pragmatic, Cursor-dyn-harness-wiring
- **Severity**: important
- **Concern**: The planned Step 0 parent-shell rehydration block leaves the outer `if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]` unterminated, so the initial and dirty-tree resume Bash fences would fail to parse before bootstrap routing runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-shell-state, Codex-dyn-harness-wiring: Add `fi` immediately before `export CLAUDE_PLUGIN_ROOT` so the outer conditional closes and export sits after both nested `if` blocks
  - From Codex-Arch: Insert fi before export CLAUDE_PLUGIN_ROOT in the planned block and apply the same fixed block to both fences
  - From Cursor-Edge, Cursor-Innovation: Add fi before unconditional export CLAUDE_PLUGIN_ROOT in both Step 0 fences
  - From Codex-Edge, Codex-Innovation, Codex-Requirements, Codex-dyn-shell-state: Add the missing fi after the inner plugin-root.env source block and before export CLAUDE_PLUGIN_ROOT in both insertions, or collapse the rehydration to a single guarded source line
  - From Cursor-Pragmatic: Add fi before export CLAUDE_PLUGIN_ROOT (or move export inside the inner branch and close both if blocks)
  - From Cursor-dyn-harness-wiring: Close the outer if with fi before an unconditional export CLAUDE_PLUGIN_ROOT (inner if/fi around plugin-root.env source only)


### FINDING_3: Bootstrap self-derive test may not actually cover an unset root
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The planned sandbox test for self-deriving `CLAUDE_PLUGIN_ROOT` may still call through a wrapper that exports the variable, so the test can pass without proving the unset-environment path works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Invoke wrapper with CLAUDE_PLUGIN_ROOT unset outside run_wrapper (e.g. env -u) and assert stub reached with derived root


