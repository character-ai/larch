### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/session_env.py:180-187
- **Concern**: Plan requires implement_session_roots to call cleanup_cache_sessions_root with injected env but never specifies extending that helper. Scenario: Implementer may re-encode the cache-root formula inside implement_session_roots to satisfy tests, violating the plan's no-re-encode rule and drifting from the bash three-root literal pinned in both hooks
- **Proposed resolution**: Add an explicit plan step: extend cleanup_cache_sessions_root(*, env: Mapping[str, str] | None = None) to read XDG_CACHE_HOME/HOME from env or os.environ; have implement_session_roots call it with the same env passed to resolve_implement_tmpdir

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/session_env.py:resolve_implement_tmpdir_main
- **Concern**: CLI stdout must be newline-free like bash `printf '%s'`. Scenario: Bash returns the path with no trailing newline; hooks capture via `IMPLEMENT_TMPDIR=$(python3 ...)` and then test `[[ -f "$IMPLEMENT_TMPDIR/review-round-summary.md" ]]`. A `print()` or `_emit()` path adds `\n`, so file probes miss and Stop/SessionStart fail open silently
- **Proposed resolution**: Document and implement: write with `sys.stdout.write(path)` (flush, no `\n`); add a pytest asserting captured stdout is byte-identical to the path

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/session_env.py:180-187
- **Concern**: Plan requires implement_session_roots/resolve_implement_tmpdir to honor an injected env mapping via cleanup_cache_sessions_root, but never says to extend cleanup_cache_sessions_root itself. Scenario: Resolver unit tests passing env={XDG_CACHE_HOME: ...} (and env-carried LARCH_TOKEN_SESSION_ID / LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS) will still read os.environ unless every lookup is threaded; implementers may re-encode the cache formula to dodge the gap
- **Proposed resolution**: Add an explicit plan step: extend cleanup_cache_sessions_root(*, env=None) (and resolve_implement_tmpdir env reads) so all resolver env access uses the passed mapping with os.environ fallback only when env is None

### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:136-139
- **Concern**: [SCOPE-REDUCTION] Marker-based no-session-dir SessionStart test depends on global /tmp and /private/tmp being empty. Scenario: The planned hook pre-check scans fixed roots including /tmp and /private/tmp, so an unrelated stale claude-implement-* directory can invoke the python3 stub and fail make lint even when the test-created cache root has no sessions
- **Proposed resolution**: Replace the marker-based runtime case with a structural no-spawn assertion that does not depend on ambient global tmp state, and keep the resolver-fail runtime case for fail-open coverage

