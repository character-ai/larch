# scripts/sessionstart-health.sh — contract

`${CLAUDE_PLUGIN_ROOT}/scripts/sessionstart-health.sh` is the SessionStart preflight hook that probes `jq`, `git`, and leftover git state at session start, then injects an advisory into session context when anything needs attention. `${CLAUDE_PLUGIN_ROOT}/scripts/test-sessionstart-health.sh` is its regression test, wired into `make lint` via the `test-sessionstart` target (run manually via `bash ${CLAUDE_PLUGIN_ROOT}/scripts/test-sessionstart-health.sh`).

The hook MUST always exit 0 (SessionStart is non-blocking by spec). Dynamic advisory content, including stash refs and sentinel fields, must be emitted via `jq -n --arg`; the jq-missing fallback may hand-craft JSON only from fixed ASCII literals.

When both `jq` and `git` are available and `git rev-parse --is-inside-work-tree` succeeds, the hook also warns about:

- uncommitted working-tree changes,
- leftover larch-managed stashes (`larch-` in `git stash list`),
- interrupted rebase, merge, or cherry-pick state,
- local branches not merged into `main`,
- `.git/larch-stalled-run.txt` sentinel content from a prior stalled `/implement` run.

Probe-internal failures are skipped silently; missing `jq` or `git` still produce the existing tool advisory and suppress the git-state probes.
