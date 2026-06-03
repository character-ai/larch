# skills/implement/scripts/lib-resolve-implement-tmpdir.sh — contract

`lib-resolve-implement-tmpdir.sh` is a sourced-only helper for the
post-/design and post-/review hook scripts. It exposes `resolve_implement_tmpdir <hook-cwd>`,
enumerates `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions`, `/tmp`, and
`/private/tmp` for `claude-implement-*` directories that have `design-export/manifest.env`
(normal path), `review-round-summary.md` (both-externals-down path that skips
`/design` — issue #1862), or `.release-armed` (post-/bump resume when
manifest/review artifacts are absent). Each candidate must provide `.larch-keepalive`,
a slim session-identity record whose `CLONE_PATH` exactly matches the
supplied hook cwd. The helper returns the freshest eligible manifest mtime with
lexicographic tie-break.
**Empty `<hook-cwd>` is fail-open by construction**: the helper returns
immediately without scanning any session root, so a hook stdin that omits
`cwd` (or has `cwd=""`, or whose cwd field could not be parsed because `jq`
is missing) cannot misbind to the globally-newest tmpdir. Empty stdout is
also the fail-open result when no keepalive matches a non-empty cwd.

Candidate eligibility additionally applies two layered checks on top of
`CLONE_PATH` match (issue #1425):

1. **Session-id binding (when `LARCH_TOKEN_SESSION_ID` is set in hook
   environment).** The candidate's `.larch-keepalive` MUST contain a
   `SESSION_ID=` line whose value exactly equals `LARCH_TOKEN_SESSION_ID`. A
   keepalive missing the line, or carrying a different value, **disqualifies
   that candidate** (this is fail-closed for the candidate; missing keepalive
   `SESSION_ID` is NOT treated as "missing signal — proceed"). When
   `LARCH_TOKEN_SESSION_ID` is unset, the session check is skipped entirely.
   In production, the env value is surfaced into hook subprocesses by
   `hook-stop-fail-close.sh`, which parses `.session_id` from the Claude Code
   hook stdin payload and `export LARCH_TOKEN_SESSION_ID="$SID"` before
   sourcing this lib. `/implement` Step 0's in-bash `export` does NOT
   propagate to hook subprocesses on its own, so the hook-side surfacing is the
   load-bearing path that makes the exact-match branch reachable in production.
2. **Wall-clock TTL backstop.** Applied only when session-id binding did not
   produce an exact match (i.e. env unset OR session check skipped).
   Candidates whose accepted sentinel mtime age `now - mtime` is greater than or
   equal to `LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS` (default 21600 = 6 hours;
   set to 0 to disable) are skipped. The window is `[0, ttl)` exclusive at
   the right boundary — a candidate exactly `ttl` seconds old is treated as
   stale, not fresh, matching the operator-facing "expire once age reaches
   the configured TTL" intent. If `date +%s` cannot be obtained (`now=0`),
   TTL evaluation is fail-closed: the candidate is rejected.

The exact-session-match path bypasses TTL on the rationale that a paused or
long-running `/design` session is provably the active session and should still
arm halt protection. The TTL-only path applies when no authoritative session
signal is available.

Edit in sync with `hook-stop-fail-close.sh`, `hooks/hooks.json`,
`scripts/test-implement-anti-halt.sh`, and
`skills/implement/scripts/test-resolve-implement-tmpdir.sh` (concurrent
worktree `CLONE_PATH` routing).
