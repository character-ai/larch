# skills/implement/scripts/hook-post-design.sh — contract

`hook-post-design.sh` is the plugin-shipped `PostToolUse` hook registered for the `Skill` tool. It reads Claude Code hook JSON on stdin, fires only when `tool_name` is `Skill` and `tool_input.skill` or `tool_input.skill_name` is `design` or `larch:design`, resolves the active `/implement` tmpdir through `lib-resolve-implement-tmpdir.sh` using the stdin `cwd` field, and runs `post-design-boundary.sh` with `--design-only` read from `$IMPLEMENT_TMPDIR/.design-only`.

Stdout is either empty or a JSON object with `hookSpecificOutput.hookEventName="PostToolUse"` and `hookSpecificOutput.additionalContext` containing byte-preserved boundary wrapper stdout. The hook captures wrapper stdout in a temp file and emits JSON with `jq --rawfile` so trailing newlines survive. Exit code is always 0; non-design Skill calls, missing `jq`, malformed stdin, and no qualifying tmpdir are fail-open no-ops. If `jq` is absent, the orchestrator-driven Step 1 Bash invocation remains the load-bearing boundary gate.

The `additionalContext` shape was verified against the Claude Code hooks reference at `https://code.claude.com/docs/en/hooks` on May 8, 2026. Edit in sync with `lib-resolve-implement-tmpdir.sh`, `post-design-boundary.sh`, `hooks/hooks.json`, and `skills/implement/scripts/test-post-design-boundary.sh`.
