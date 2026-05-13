# dispatch-panel.sh Contract

`skills/review/scripts/dispatch-panel.sh` plans and launches `/review` reviewer slots.

It launches Cursor and Codex specialists through `scripts/launch-review.sh` when those tools are available. When a tool is unavailable, its specialist slots are skipped entirely (no Claude substitution for partial outages). The Claude generic slot always runs through `scripts/launch-claude-subprocess.sh`. When both external tools are down, only one Claude generic slot is launched and `PANEL_MODE=both-down` is emitted.

Pass `--description-text` to thread the user's description through to both external and Claude reviewer prompts in description mode.

Stdout is `KEY=value` only: `EXTERNAL_OUTPUT_FILES`, `CLAUDE_OUTPUT_FILES`, `PANEL_MODE`, `SLOT_COUNT`, `PANEL_MANIFEST`, and `DISPATCH_OK`.

Harness: `skills/review/scripts/test-dispatch-panel.sh`, wired through `make test-dispatch-panel`.
