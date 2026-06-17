## Goal
Implement issue #4613: [IMPLEMENTING] [BUG] External-tool health probe emits false-negative probe-failed verdicts.

## Implementation Plan
## Plan

## Basis

- `approach-synthesis.txt` is `NO_SKETCHES`; draft from direct code and doc inspection.
- `discussion-round1.md` sets `LARCH_PROBE_RETRIES`, default `2`, as the retry API.
- Approved outline limits scope to `python/agents.py`, `python/test_agents.py`, and `docs/configuration-and-permissions.md`.
- Do not change negative caching, probe timeout, model effort, or caller scripts.

## Approach

- Add a separate transient retry budget for non-auth probe failures.
- Keep auth retry behavior separate from transient retry behavior.
- **Preserve distinct counting semantics**: auth and transient budgets must not share a `for attempt in range(...)` bound or symmetric counter.
- Treat `LARCH_PROBE_RETRIES=0` as "no transient retry".
- Keep invalid or empty `LARCH_PROBE_RETRIES` values falling back to `2`.
- Preserve fast failure for definite auth preflight failures, deterministic setup failures, and health-gate one-shot probes.
- Do not change the public `agent check-reviewers` key-value output.

## Files to modify/create

### UPDATED: python/agents.py

- Add module-level constants near existing probe retry handling:

  - `_AUTH_RETRY_RC = 2` (existing)
  - `_PROBE_NO_RETRY_RC = 3` — private sentinel for deterministic failures that must never consume auth or transient retry budgets

- In `check_reviewers`, read:

  - `max_auth_retries = _env_int("LARCH_EXTERNAL_AUTH_RETRIES", 5, zero_allowed=False)`
  - `max_transient_retries` from `LARCH_PROBE_RETRIES` via `_env_int("LARCH_PROBE_RETRIES", 2)` when the variable is present in the environment
  - When `LARCH_PROBE_RETRIES` is **unset**, default transient retries to `2` for normal Step 0 probes, **except** force `max_transient_retries = 0` when `max_auth_retries == 1` (health-gate fast-fail contract). An explicit `LARCH_PROBE_RETRIES` in the environment overrides this health-gate suppression, including `0`.

- Change `_run_codex_probes` signature to accept both retry budgets:

  - `max_auth_retries`
  - `max_transient_retries`
  - `timeout`

- Change `_run_cursor_probes` the same way.
- Update call sites in `check_reviewers` to pass both budgets. For Cursor preflight auth failure (`preflight.rc == _CURSOR_PREFLIGHT_AUTH_RC`), keep `max_auth_retries = 1` and pass `max_transient_retries = 0` at the call site.

- **Replace the shared `for attempt in range(...)` loop** in `_run_codex_probes` and `_run_cursor_probes` with a **`while True` loop and independent counters**.

  **Semantic contract:**

  - **Auth (`rc == _AUTH_RETRY_RC`) — attempt-cap semantics (unchanged):** `LARCH_EXTERNAL_AUTH_RETRIES=N` caps total probe invocations on an all-auth-failure path to N. Example: `N=5` → five probe calls; `N=2` with auth then success → two calls.
  - **Transient (`rc == 1`) — retry-after-first-failure semantics (new):** `LARCH_PROBE_RETRIES=N` allows N additional attempts after the first transient failure, for N+1 total calls on an all-`rc==1` path. Example: `N=2` → three calls; `N=0` → one call.
  - Auth and transient budgets are **independent**: mixed sequences consume only the budget for each probe's failure class.

  **Suggested loop shape:**

  ```python
  auth_failures = 0
  transient_retries_used = 0
  while True:
      rc = _run_one_*_probe(timeout)
      if rc == 0:
          return True, False
      if rc == config.EXIT_TIMEOUT:
          return False, True
      if rc == _PROBE_NO_RETRY_RC:
          return False, False
      if rc == _AUTH_RETRY_RC:
          auth_failures += 1
          if auth_failures >= max(max_auth_retries, 1):
              return False, False
          continue
      if rc == 1:
          if transient_retries_used >= max_transient_retries:
              return False, False
          transient_retries_used += 1
          continue
      return False, False
  ```

- **Mandatory** deterministic no-retry path in `_run_one_codex_probe`:

  - When `_prepare_codex_home` returns non-zero, return `_PROBE_NO_RETRY_RC` instead of `1`.

- Cursor setup fast-fail remains unchanged: `_cursor_probe_setup_chain()` returning `None` exits before the retry loop.

- Keep stamp read/write behavior unchanged.
- Keep negative stamp TTL behavior unchanged.

### UPDATED: python/test_agents.py

- Rename `test_check_reviewers_non_auth_failure_no_retry` to `test_check_reviewers_transient_failure_retries_until_exhausted`.
- Update it: fake probe always returns `1`; default `LARCH_PROBE_RETRIES=2` yields 3 total calls; result absent, not timed out.
- Add transient success case: probe returns `1` then `0`; result present; calls count 2.
- Add zero-budget case: `LARCH_PROBE_RETRIES=0`, probe returns `1`; calls count 1.
- Keep `test_check_reviewers_codex_auth_setup_failure` asserting one probe call when `_prepare_codex_home` fails (`_PROBE_NO_RETRY_RC` must not trigger transient retry).
- Add `_PROBE_NO_RETRY_RC` sentinel coverage: monkeypatch `_run_one_codex_probe` to return `_PROBE_NO_RETRY_RC`; assert exactly one loop iteration.
- Keep `test_check_reviewers_expired_stamp_misses_and_auth_retry` unchanged: `LARCH_EXTERNAL_AUTH_RETRIES=2` with auth-then-success must remain two calls.
- Add health-gate fast-fail compatibility: `LARCH_EXTERNAL_AUTH_RETRIES=1`, `LARCH_PROBE_RETRIES` unset, probe returns `1` → exactly one call. Companion case: `LARCH_PROBE_RETRIES=2` explicit → three calls.
- Add Cursor retry loop coverage: binary on PATH, preflight ok, setup chain and cleanup patched, probe returns `1` then `0` or always `1`; assert retry success or exhaustion.
- Keep `test_check_reviewers_cursor_preflight_rc2_one_shot_and_cleanup` unchanged.
- Add `test_check_reviewers_cursor_preflight_rc2_transient_rc1_one_shot`: preflight returns `rc=2`, probe returns `1`; `max_transient_retries=0` at call site → exactly one probe call.
- Keep existing auth retry test.
- Extend `test_check_reviewers_invalid_env_normalization` to cover invalid `LARCH_PROBE_RETRIES` falling back to `2`.

### UPDATED: docs/configuration-and-permissions.md

- Add `LARCH_PROBE_RETRIES` to "External reviewer probe tuning (`agent check-reviewers`)":
  - Default `2` when unset.
  - Non-negative integer; `0` disables non-auth transient retry.
  - Invalid or empty values fall back to `2`.
  - Semantics: N additional retries after the first transient non-auth failure (N+1 total calls on all-`rc==1` path).
  - When unset and `LARCH_EXTERNAL_AUTH_RETRIES=1`, transient retries forced to `0`; explicit `LARCH_PROBE_RETRIES` overrides this.
- Update `LARCH_EXTERNAL_AUTH_RETRIES` bullet: controls auth-classified failures only, attempt-cap semantics (max total invocations on repeated auth failures). Does not govern transient `rc==1` retries.
- Do not change `LARCH_PROBE_NEGATIVE_TTL_SECONDS` guidance.

## Edge cases

- Cached positive stamps skip probing; no retry logic runs.
- Cached negative stamps ignored by default (negative TTL remains `0`).
- Timeout returns `*_PROBE_TIMED_OUT=true` immediately; no retry.
- Cursor preflight auth failure: at most one probe call, zero transient retries, even when probe returns `rc==1`.
- `_prepare_codex_home` failure: one-shot even with default `LARCH_PROBE_RETRIES=2`.
- `LARCH_PROBE_RETRIES=0`: preserves old one-shot behavior.
- Health-gate callers (`LARCH_EXTERNAL_AUTH_RETRIES=1`, `LARCH_PROBE_RETRIES` unset): one-shot for transient failures.
- Explicit `LARCH_PROBE_RETRIES` overrides health-gate transient suppression.
- Mixed auth/transient sequences: each failure class consumes only its own budget.
- Invalid retry env values must not crash `check-reviewers`.

## Failure modes

- More attempts may slightly increase Step 0 latency when a tool is truly unavailable.
- Setup failures not on `_PROBE_NO_RETRY_RC` would waste attempts on deterministic failures.
- Rapid repeated probes can still aggravate provider rate limits; retry budget must remain small.
- Health-gate latency could regress if transient suppression is omitted when `LARCH_EXTERNAL_AUTH_RETRIES=1`.
- A shared `for`-loop bound can under-retry transient, over-retry auth, or break existing auth tests.
- Omitting Cursor preflight call-site `max_transient_retries=0` can allow transient retry after definite preflight auth failure.

## Testing strategy

- `python3 -m pytest python/test_agents.py -k check_reviewers`
- `make py-lint && make py-test && make lint`

diff_lines: 225

## Acceptance

- `_run_codex_probes` and `_run_cursor_probes` retry up to `LARCH_PROBE_RETRIES` times (default 2) on transient `rc==1` failures before declaring `probe-failed`.
- Auth retries (`_AUTH_RETRY_RC=2`) remain controlled by `LARCH_EXTERNAL_AUTH_RETRIES`; budgets are independent.
- `_prepare_codex_home` failure returns `_PROBE_NO_RETRY_RC` and is never retried.
- `LARCH_PROBE_RETRIES=0` preserves one-shot behavior.
- Health-gate path (`LARCH_EXTERNAL_AUTH_RETRIES=1`, `LARCH_PROBE_RETRIES` unset) suppresses transient retry.
- All new behaviors are covered by regression tests in `python/test_agents.py`.
- `docs/configuration-and-permissions.md` documents `LARCH_PROBE_RETRIES`.
- `make py-lint`, `make py-test`, and `make lint` pass.

## Test plan
(no test plan section in plan-file)
