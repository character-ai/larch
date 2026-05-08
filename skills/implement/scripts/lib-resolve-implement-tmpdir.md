# skills/implement/scripts/lib-resolve-implement-tmpdir.sh — contract

`lib-resolve-implement-tmpdir.sh` is a sourced-only helper for the
post-/design hook scripts. It exposes `resolve_implement_tmpdir <hook-cwd>`,
enumerates `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions`, `/tmp`, and
`/private/tmp` for `claude-implement-*` directories with
`design-export/manifest.env`, requires every candidate to provide
`.larch-keepalive` whose `CLONE_PATH` exactly matches the supplied hook cwd,
and returns the freshest eligible manifest mtime with lexicographic tie-break.
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
2. **Wall-clock TTL backstop.** Applied only when session-id binding did not
   produce an exact match (i.e. env unset OR session check skipped).
   Candidates whose `manifest.env` mtime is older than
   `LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS` (default 21600 = 6 hours; set to 0 to
   disable) are skipped. If `date +%s` cannot be obtained (`now=0`), TTL
   evaluation is fail-closed: the candidate is rejected.

The exact-session-match path bypasses TTL on the rationale that a paused or
long-running `/design` session is provably the active session and should still
arm halt protection. The TTL-only path applies when no authoritative session
signal is available.

Edit in sync with `hook-post-design.sh`, `hook-stop-fail-close.sh`, and
`skills/implement/scripts/test-post-design-boundary.sh`.
