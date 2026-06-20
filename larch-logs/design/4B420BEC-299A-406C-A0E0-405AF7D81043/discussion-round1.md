## Decision 1: Sibling launch-time gate scope
- **Question**: Besides the Step 0 probe timeout `LARCH_PROBE_TIMEOUT_SECONDS` (30s→60s), should the sibling launch-time health gate `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` (also default 30s) be raised to 60s?
- **Resolution**: Both timeouts. Raise `LARCH_PROBE_TIMEOUT_SECONDS` 30→60 (`python/agents.py`) AND `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` 30→60 (`python/session_env.py` `_external_timeout`). This is option (b) from the issue's open question.
- **Source**: user

## Decision 2: Override semantics must be preserved (per-knob, NOT identical)
- **Question**: Do the two knobs share fallback semantics for `0` / empty / non-numeric?
- **Resolution**: No — they differ and both must be preserved as-is.
  - `LARCH_PROBE_TIMEOUT_SECONDS` (`_env_int(..., zero_allowed=False)`): non-numeric / empty / `0` all fall back to the default (now 60).
  - `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` (`_external_timeout`): only non-digit falls back to the default (now 60); `0` is a valid opt-out and MUST stay `0`, a positive value overrides. Only the default literal changes.
- **Source**: codebase (`python/agents.py` `check_reviewers`, `python/session_env.py` `_external_timeout`)

## Decision 3: Change surface (in-scope files)
- **Question**: Which files form the complete change surface?
- **Resolution**: `python/agents.py` (probe default), `python/session_env.py` (external-gate default), `docs/configuration-and-permissions.md` (both doc entries + the "session writers persist 30" prose), `python/test_agents.py` (`test_check_reviewers_invalid_env_normalization` asserts `[30,30,30]`), and a new focused test for `_external_timeout` in `python/test_session_env.py` (currently untested). Repo-wide sweep found no other live references (README/SECURITY/skills/docs/external-reviewers are clean; remaining hits are historical `larch-logs/` artifacts that MUST NOT be edited).
- **Source**: codebase (Step 0c + Step 1d greps)

## Constraint: relationship to #4756 (do not implement #4756 here)
- **Question**: Does this design need to land/wait for #4756?
- **Resolution**: This issue is blocked by #4756 for merge ordering, but the design is independent. Do NOT add the `LARCH_PROBE_TIMEOUT_RETRIES` retry budget (#4756 owns it). This issue is solely the 30→60 default bump for the two timeouts. Plan targets current `main`; `/implement` re-materializes after #4756 lands.
- **Source**: issue body

## Non-goals
- No retry-budget logic, no new env vars, no change to TTL / auth-retry / transient-retry knobs.
- No change to the per-attempt-vs-total timeout model.
- No CHANGELOG edit during `/design` (release tooling owns version bumps; `/implement` adds the changelog bullet).
