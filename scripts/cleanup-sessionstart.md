# scripts/cleanup-sessionstart.sh contract

`${CLAUDE_PLUGIN_ROOT}/scripts/cleanup-sessionstart.sh` is the SessionStart hook that launches `python3 python/cli.py cleanup run` as a detached background process at session start. The cleanup command performs the age-based `larch-*` sweep, including `larch-report-tokens.*` roots preserved for advertised `/report-tokens` artifacts.

**Primary caller:** `hooks/hooks.json` `SessionStart` hook (matcher `startup|resume|clear|compact`, timeout 10).

**Invariants:**

- The hook MUST always exit 0. SessionStart maintenance is non-blocking.
- The hook file MUST be executable (`100755`). Claude Code invokes it directly.
- Cleanup runs as a detached background process (`&` + `disown`); the hook exits before cleanup finishes.
- Output from cleanup is redirected to `${TMPDIR:-/tmp}/larch-cleanup-sessionstart-$$.log` for post-hoc debugging.
- The hook emits no advisory JSON. Cleanup is silent background maintenance and requires no operator action.
- When `python3` or `cli.py` is unavailable, the hook exits 0 silently.

**Harness:** `make test-cleanup-sessionstart` runs `scripts/test-cleanup-sessionstart.sh`.

**Edit-in-sync:** When changing the CLI verb path (`cleanup run`), update this doc and `scripts/test-cleanup-sessionstart.sh`. When changing the `hooks.json` `SessionStart` entry for this hook, update this doc and the harness registration assertion.
