### FINDING_1: Codex `_prepare_codex_home` failures must not use transient retry budget
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: The plan only "considers" a no-retry path for deterministic Codex setup failures, but `_prepare_codex_home` failures already collapse to `rc == 1`. A naive `rc == 1` transient-retry loop (default `LARCH_PROBE_RETRIES=2` => three total attempts) would re-probe a known-bad Codex home, waste work on deterministic auth-setup failures, violate the stated fast-fail constraint, and break `test_check_reviewers_codex_auth_setup_failure` (expects `probe_calls == 1`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mandate a non-retry return from `_run_one_codex_probe` for `_prepare_codex_home` failure (dedicated rc or early exit in `_run_codex_probes`), keep `test_check_reviewers_codex_auth_setup_failure`, and drop the optional wording
  - From Cursor-Pragmatic: Mandate fast-fail for _prepare_codex_home failure (distinct internal rc or pre-probe guard) in the plan Step 2b loop rules; do not treat prep/setup rc==1 as transient-retryable
  - From Cursor-Requirements: Mandate a distinct no-retry outcome for deterministic setup failures (for example return a dedicated rc from `_run_one_codex_probe` when `_prepare_codex_home` fails, and fail immediately in `_run_codex_probes` / `_run_cursor_probes` without consuming `LARCH_PROBE_RETRIES`). Drop the "consider" wording and state that `test_check_reviewers_codex_auth_setup_failure` must stay one-shot
  - From Codex-Requirements: Make the no-retry path mandatory for _prepare_codex_home failures, for example with an internal sentinel rc handled by the loop as fail-without-retry, and keep the existing setup-failure test asserting one probe call


### FINDING_2: Health-gate callers inherit default `LARCH_PROBE_RETRIES` and lose fast-fail contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Launch-time health gates rely on `LARCH_EXTERNAL_AUTH_RETRIES=1` for a single probe attempt, but the plan defaults `LARCH_PROBE_RETRIES=2` and forbids caller edits. A transient `rc == 1` inside `agent check-reviewers` can become three internal attempts (~90s worst case) instead of one, regressing the documented fast-fail health-gate contract without any plan step addressing those call sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `check_reviewers`, when `LARCH_PROBE_RETRIES` is unset and `LARCH_EXTERNAL_AUTH_RETRIES=1`, force `max_transient_retries=0`; document that explicit `LARCH_PROBE_RETRIES` overrides this
  - From Cursor-Pragmatic: In docs/configuration-and-permissions.md update the LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT bullet to state LARCH_PROBE_RETRIES applies there too, or add an explicit plan step to export LARCH_PROBE_RETRIES=0 on those six call sites


### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:795-811, python/test_agents.py:1095-1119
- **Concern**: [SCOPE-REDUCTION] The plan makes no-retry handling for Codex setup failures optional even though `_run_one_codex_probe` currently maps `_prepare_codex_home` failure to `rc == 1`, which the new loop will retry by default.. Scenario: A deterministic local setup/auth-copy failure would be retried 3 times with default `LARCH_PROBE_RETRIES=2`, conflicting with the existing one-shot setup-failure contract and broadening the feature beyond transient probe retry.
- **Proposed resolution**: Make the no-retry path mandatory for `_prepare_codex_home` failures. Use a private sentinel return code or equivalent immediate-fail branch, and preserve `test_check_reviewers_codex_auth_setup_failure` at 1 probe call.


### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:805-811
- **Concern**: [SCOPE-REDUCTION] Plan only "considers" a no-retry path for `_prepare_codex_home` failures, but those failures already surface as `rc == 1`. Scenario: Deterministic Codex auth-setup failures would be retried up to `LARCH_PROBE_RETRIES` times, breaking `test_check_reviewers_codex_auth_setup_failure` (expects one probe call) and adding pointless Step 0 latency on hard failures
- **Proposed resolution**: Make setup/preflight hard-fail explicit: return a dedicated non-retry rc from `_run_one_codex_probe` when `_prepare_codex_home` fails (and similarly for other deterministic rc==1 paths the plan names), and have `_run_*_probes` fail immediately on that rc without consuming the transient budget




### FINDING_2: Probe loop must separate auth attempt-cap from transient retry-count semantics
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: Adding transient `rc==1` retries in `_run_codex_probes` / `_run_cursor_probes` must not reuse the existing auth `for attempt in range(1, max(max_auth_retries, 1) + 1)` bound or symmetric retry counters. Auth and transient budgets use **different counting semantics**: `LARCH_EXTERNAL_AUTH_RETRIES` caps **total probe invocations** (e.g. 5 → five probes on all-auth failure via `range(1, max+1)`), while `LARCH_PROBE_RETRIES=2` means **two extra attempts after the first failure** (three total on all-`rc==1`). A naive port that caps iterations at `max_auth_retries`, extends the same `for` bound, or applies symmetric retry counters can under-retry transient failures, break the health-gate override case (`LARCH_EXTERNAL_AUTH_RETRIES=1`, explicit `LARCH_PROBE_RETRIES=2`, three transient `rc==1` calls), mishandle mixed auth-then-transient sequences, or inflate auth probes (e.g. `LARCH_EXTERNAL_AUTH_RETRIES=5` → six probes), breaking `test_check_reviewers_expired_stamp_misses_and_auth_retry` and changing launcher auth semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In _run_codex_probes/_run_cursor_probes use a while-loop with separate counters: on rc==2 continue while auth_failures < max_auth_retries; on rc==1 continue while transient_failures <= max_transient_retries (or equivalent retries_remaining starting at max_transient_retries). Do not extend range(1, max_transient_retries+1)
  - From Cursor-Pragmatic: Replace the shared `for` bound with a `while` loop and separate `auth_attempts` / `transient_attempts` counters. Continue on `rc==2` only while auth budget remains; on `rc==1` only while transient budget remains; exit immediately on timeout or `_PROBE_NO_RETRY_RC`
  - From Codex-Generic: In `_run_codex_probes` / `_run_cursor_probes`, preserve today's auth path as an attempt cap identical to the existing loop (or equivalent), and apply `max_transient_retries` only for `rc==1`. Document in the plan loop section that auth keeps attempt-cap semantics while transient uses retry-after-first-failure semantics



### FINDING_3: Missing regression test for Cursor preflight one-shot on transient rc==1
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `test_check_reviewers_cursor_preflight_rc2_one_shot` covers probe `rc==2` only. Without a test where preflight `rc==2` and the fake probe returns `rc==1`, an implementer can wire only the global health-gate rule and omit call-site `max_transient_retries=0`, allowing a misclassified or transient probe `rc==1` to run three attempts (default `LARCH_PROBE_RETRIES=2`) and break the definite-auth one-shot contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a test mirroring preflight rc `2` with fake probe returning `1` and assert exactly one probe call with default env (no explicit `LARCH_PROBE_RETRIES`).



