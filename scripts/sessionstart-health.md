# scripts/sessionstart-health.sh — contract

`${CLAUDE_PLUGIN_ROOT}/scripts/sessionstart-health.sh` is the SessionStart preflight hook that probes `jq`, `git`, the larch marketplace sparse cone, leftover git state, and pending /implement boundary state at session start, then injects an advisory into session context when anything needs attention. `${CLAUDE_PLUGIN_ROOT}/scripts/test-sessionstart-health.sh` is its regression test, wired into `make lint` via the `test-sessionstart` target (run manually via `bash ${CLAUDE_PLUGIN_ROOT}/scripts/test-sessionstart-health.sh`).

The hook MUST always exit 0 (SessionStart is non-blocking by spec). Dynamic advisory content, including stash refs, sentinel fields, and resolved tmpdir basenames, must be emitted via `jq -n --arg`.

**Invariants:** When `jq` is missing, the hook emits a fixed-literal advisory envelope and does NOT interpolate `MSG` content. Two fixed literals exist: jq-only-missing and jq+git-both-missing, branched on `GIT_AVAILABLE`. This permanently closes the JSON-injection surface that was OOS issue #1420 — even if a future probe adds operator-controlled content to `MSG` outside the `JQ_AVAILABLE && GIT_AVAILABLE` gate, the jq-missing emission path cannot reflect that content into JSON.

When both `jq` and `git` are available and `git rev-parse --is-inside-work-tree` succeeds, the hook also warns about:

- uncommitted working-tree changes,
- leftover larch-managed stashes (`larch-` in `git stash list`),
- interrupted rebase, merge, or cherry-pick state,
- local branches not merged into `main`,
- `.git/larch-stalled-run.txt` sentinel content from a prior stalled `/implement` run.

Probe-internal failures are skipped silently; missing `jq` or `git` still produce the existing tool advisory and suppress the git-state probes.

When both `jq` and `git` are available, the hook also performs a warn-only sparse-cone drift probe for `$HOME/.claude/plugins/marketplaces/larch-local`. The probe compares the checkout with the fixed `.claude-plugin` cone also emitted by the Rust `upgrade-larch sparse-dirs` command. It skips silently when `HOME` is empty, the marketplace clone is missing, the directory is not a git repo, `larch-logs/` is present, or either compare side is empty. The compare is read-only, best-effort under restored parent-shell `errexit`, and non-mutating: it never removes, adds, updates, or installs a marketplace. On mismatch, `append_msg` runs in the parent shell and emits a fixed-string advisory pointing at `/upgrade-larch`. The hook still exits 0.

When `jq` is available, the hook reads the SessionStart JSON payload on stdin and extracts `cwd` and `session_id`. It exports the payload `session_id` as `LARCH_TOKEN_SESSION_ID` when present so the resolver can apply its session binding, then resolves the active `/implement` tmpdir through `python/cli.py session resolve-implement-tmpdir --cwd "$HOOK_CWD"`.

Before spawning Python, the hook performs a cheap bash glob pre-check for `claude-implement-*` directories under these roots:

1. `${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions`
2. `/tmp`
3. `/private/tmp`

The resolver call is fail-open and must keep this `set -e`-safe capture shape:

```bash
IMPLEMENT_TMPDIR=$(python3 "$PLUGIN_ROOT/python/cli.py" session resolve-implement-tmpdir --cwd "$HOOK_CWD" 2>/dev/null) || IMPLEMENT_TMPDIR=""
```

A bare command substitution without `|| IMPLEMENT_TMPDIR=""` can abort the always-exit-0 hook under `set -e`. Missing stdin, missing `jq`, malformed JSON, no session dirs, missing `python3`, a failed resolver, no matching tmpdir, stale candidates, or `.run-cleaned-up` all fail open with no boundary advisory.

Boundary advisories are emitted for:

- post-/review: `review-round-summary.md` exists without `.review-boundary-passed`; recovery points to the Step 5 post-/review actions and Step 6 sentinel.

The post-/release SessionStart advisory was retired in Phase 1 (#3364); `/implement` no longer arms `.release-armed` on the ship path.
