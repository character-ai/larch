## Proposed Design Outline

### Goals
- Raise the default per-attempt probe timeout `LARCH_PROBE_TIMEOUT_SECONDS` from 30s to 60s.
- Raise the launch-time health-gate default `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` from 30s to 60s (operator chose both).
- Keep docs and tests consistent with the new 60s defaults.

### Non-goals
- No retry-budget logic; `LARCH_PROBE_TIMEOUT_RETRIES` belongs to #4756, not this issue.
- No new env vars; no change to TTL / auth-retry / transient-retry knobs or the per-attempt-vs-total model.
- No CHANGELOG edit during `/design` (release tooling and `/implement` own that).

### Approach sketch
- Change one default literal in `python/agents.py` `check_reviewers` (30 → 60).
- Change the two `"30"` fallbacks in `python/session_env.py` `_external_timeout` (→ `"60"`); preserve the `0` opt-out and digit-only fallback semantics.
- Update both env-var entries plus the "session writers persist 30" prose in `docs/configuration-and-permissions.md`.
- Update `python/test_agents.py` `test_check_reviewers_invalid_env_normalization` (`[30, 30, 30]` → `[60, 60, 60]`).
- Add a focused `_external_timeout` default test in `python/test_session_env.py` (the resolver default is currently untested).

### Surfaces in scope
- `python/agents.py`, `python/session_env.py`
- `docs/configuration-and-permissions.md`
- `python/test_agents.py`, `python/test_session_env.py`

### Open questions
- None.
