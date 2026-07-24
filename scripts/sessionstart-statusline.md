# sessionstart-statusline.sh

SessionStart hook registered in `hooks/hooks.json` to idempotently install the larch progress statusline for the current clone.

## Contract

- Caller: Claude Code `SessionStart` for `startup|resume|clear|compact`.
- Clears stale active-run pointers only on `startup` and `clear`; `resume` and `compact` preserve the pointer.
- Skips reset when a live larch bgjob exists for the clone.
- Deletes only `~/.cache/larch/progress/<clone-hash>/current`; run directories and `breadcrumbs.log` files remain intact.
- Mutates only `~/.cache/larch/statusline.sh`, `<repo>/.claude/settings.local.json`, and the clone-local `current` pointer described above.
- Honors `LARCH_STATUSLINE_DISABLE=1`.
- The installed launcher caches each clone's larch render for 5 seconds by default. `LARCH_STATUSLINE_REFRESH_SECONDS` sets a positive override. The cache also stores empty renders.
- Refuses symlinked target paths or ancestors through the Python runtime.
- Performs no network calls and exits 0 with no stdout/stderr on every missing-tool or failure path.

## Harness

`make test-sessionstart-statusline` runs `scripts/test-sessionstart-statusline.sh`.
