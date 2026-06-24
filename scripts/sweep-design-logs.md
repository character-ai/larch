# scripts/sweep-design-logs.sh — contract

`${CLAUDE_PLUGIN_ROOT}/scripts/sweep-design-logs.sh` is the SessionStart hook that launches `python3 python/cli.py ship design-log-sweep` as a detached background process at session start. The sweep admin-merges accumulated `chore(larch-logs)` design-run PRs whose required CI checks are already green, providing a durable automatic trigger for the backstop that `_spawn_detached_admin_merge` in `python/design_log_publish_flow.py` can miss when the originating session exits.

**Primary caller:** `hooks/hooks.json` `SessionStart` hook (matcher `startup|resume|clear|compact`, timeout 10).

**Invariants:**
- The hook MUST always exit 0 (SessionStart is non-blocking by spec). All error paths exit 0.
- The sweep runs as a detached background process (`&` + `disown`); the hook exits before the sweep finishes.
- Output from the sweep is redirected to `${TMPDIR:-/tmp}/larch-sweep-design-logs-$$.log` for post-hoc debugging.
- The hook emits no advisory JSON — the sweep is silent background maintenance and requires no operator action.
- When `python3` or `cli.py` is unavailable, the hook exits 0 silently.

**No Makefile target.** This hook is exercised by running the CI shellcheck via `make lint`.

**Edit-in-sync:** When changing the CLI verb path (`ship design-log-sweep`), update this doc. When changing the `hooks.json` `SessionStart` entry for this hook, update this doc. Changes to `python/design_log_ship.py::sweep_main` are independent and do not require edits here.
