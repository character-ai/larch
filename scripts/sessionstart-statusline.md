# sessionstart-statusline.sh

SessionStart hook registered in `hooks/hooks.json` to idempotently install the larch progress statusline for the current clone.

## Contract

- Caller: Claude Code `SessionStart` for `startup|resume|clear|compact`.
- Writes only `~/.cache/larch/statusline.sh`, `<repo>/.claude/settings.local.json`, and `~/.cache/larch/progress/` breadcrumbs written by the Python runtime.
- Honors `LARCH_STATUSLINE_DISABLE=1`.
- Refuses symlinked target paths or ancestors through the Python installer.
- Performs no network calls and exits 0 with no stdout/stderr on every missing-tool or failure path.

## Harness

`make test-sessionstart-statusline` runs `scripts/test-sessionstart-statusline.sh`.
