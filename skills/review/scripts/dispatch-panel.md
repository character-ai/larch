# dispatch-panel.sh Contract

`skills/review/scripts/dispatch-panel.sh` plans and launches `/review` reviewer slots.

It launches Cursor and Codex specialists through `scripts/launch-review.sh` when those tools are available. Missing specialist slots and the Claude generic slot run through `scripts/launch-claude-subprocess.sh`, so they produce `.done`, `.meta`, and `.dirty-tree` sidecars. When both external tools are down, only one Claude generic slot is launched and `PANEL_MODE=both-down` is emitted.

Stdout is `KEY=value` only: `EXTERNAL_OUTPUT_FILES`, `CLAUDE_OUTPUT_FILES`, `PANEL_MODE`, `SLOT_COUNT`, `PANEL_MANIFEST`, and `DISPATCH_OK`.

Harness: `skills/review/scripts/test-dispatch-panel.sh`, wired through `make test-dispatch-panel`.
