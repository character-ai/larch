## Proposed Design Outline

### Goals
- Add bounded retry for transient non-auth probe failures in `_run_cursor_probes` and `_run_codex_probes`.
- Expose the retry count via `LARCH_PROBE_RETRIES` (default 2), separate from `LARCH_EXTERNAL_AUTH_RETRIES`.
- Cover the new retry path with regression tests in `python/test_agents.py`.

### Non-goals
- Negative caching (`LARCH_PROBE_NEGATIVE_TTL_SECONDS`) is out of scope.
- No changes to the probe timeout (`LARCH_PROBE_TIMEOUT_SECONDS`) or Codex probe model/effort.
- No changes to caller sites outside `python/agents.py` (launchers, session-setup wrappers).

### Approach sketch
- Add `LARCH_PROBE_RETRIES` read in `check_reviewers` alongside `LARCH_EXTERNAL_AUTH_RETRIES`.
- Pass a new `max_transient_retries` parameter (or pair of parameters) to `_run_cursor_probes` / `_run_codex_probes`.
- In each probe loop, retry on `rc == 1` (non-auth, non-timeout) up to `max_transient_retries` attempts in addition to existing auth retry logic.
- Update `docs/configuration-and-permissions.md` to document `LARCH_PROBE_RETRIES`.
- Update `python/test_agents.py`: rename the existing `test_check_reviewers_non_auth_failure_no_retry` test to reflect new behavior; add cases for transient retry success and retry exhaustion.

### Surfaces in scope
- `python/agents.py` — probe loop retry logic and `LARCH_PROBE_RETRIES` reading.
- `python/test_agents.py` — regression coverage.
- `docs/configuration-and-permissions.md` — env var documentation.

### Open questions
- None.
