### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/session_env.py:180-187
- **Concern**: Plan requires `implement_session_roots` to call `cleanup_cache_sessions_root()` with an injected `env`, but never explicitly tasks extending `cleanup_cache_sessions_root` to accept `env: Mapping[str, str] | None = None`. Scenario: Implementers may re-encode the cache-root formula inside `implement_session_roots` (violating the plan's own rule) or wire tests only through `os.environ` monkeypatch, leaving the promised `resolve_implement_tmpdir(..., env=...)` / XDG-only harness path untestable without global env mutation
- **Proposed resolution**: Add an explicit `session_env.py` sub-bullet: extend `cleanup_cache_sessions_root(env=None)` to read from the passed mapping when provided; keep existing callers on the default `os.environ` path; have `implement_session_roots` delegate to it
