### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/agents.py:886-922
- **Concern**: Health-gate transient suppression needs os.environ membership, not _env_int alone. Scenario: Implementing only max_transient_retries = _env_int("LARCH_PROBE_RETRIES", 2) ignores the max_auth_retries == 1 unset override; launch-time health gates (LARCH_EXTERNAL_AUTH_RETRIES=1) would run up to three transient retries and regress fast-fail latency
- **Proposed resolution**: Add explicit check_reviewers binding, e.g. if "LARCH_PROBE_RETRIES" in os.environ: max_transient_retries = _env_int("LARCH_PROBE_RETRIES", 2) elif max_auth_retries == 1: max_transient_retries = 0 else: max_transient_retries = 2; document that _env_int cannot implement unset-vs-set by itself

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:905-922
- **Concern**: Cursor preflight auth failure must pass per-call max_transient_retries=0 without zeroing Codex transient budget. Scenario: Plan sets max_transient_retries globally in check_reviewers but only Cursor preflight auth failure needs 0; if the global value is reused for _run_cursor_probes without a preflight branch, a probe rc==1 after preflight rc==2 still gets transient retries (up to 3 calls) even though auth is already known bad
- **Proposed resolution**: At the Cursor call site compute cursor_transient = 0 when preflight.rc == _CURSOR_PREFLIGHT_AUTH_RC else max_transient_retries; pass cursor_transient only to _run_cursor_probes; keep the global max_transient_retries for Codex

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:896-897
- **Concern**: max_transient_retries resolution must distinguish unset LARCH_PROBE_RETRIES from explicit values before calling _env_int. Scenario: _env_int uses os.environ.get(name, str(default)) so unset reads as 2; health-gate suppression (unset + max_auth_retries==1 → 0) requires a name-in-os.environ branch; a single _env_int call never applies that suppression
- **Proposed resolution**: Document and implement a three-branch resolver: if LARCH_PROBE_RETRIES in os.environ then _env_int(..., 2); elif max_auth_retries==1 then 0; else 2

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:886-922
- **Concern**: Invalid or empty `LARCH_PROBE_RETRIES` in the parent environment bypasses health-gate transient suppression. Scenario: Plan treats any `LARCH_PROBE_RETRIES` key as an explicit override while also saying invalid/empty values fall back to `2`. Launch-time health gate calls `check-reviewers` with `LARCH_EXTERNAL_AUTH_RETRIES=1` only. An inherited `LARCH_PROBE_RETRIES=""` or `LARCH_PROBE_RETRIES=bad` would force `max_transient_retries=2` and up to three probe calls per gate attempt instead of today's one-shot fast-fail, regressing health-gate latency and rate-limit exposure.
- **Proposed resolution**: Only honor explicit override when the value parses as a non-negative integer. On invalid/empty present values, apply the same fallback as unset: `0` when `max_auth_retries == 1`, else `2`. Document that behavior in `docs/configuration-and-permissions.md`.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:910-912
- **Concern**: Cursor preflight auth short-circuit lacks a regression test for transient `rc==1` with zero transient budget. Scenario: When `cursor_auth_preflight` returns rc `2`, the plan forces `max_auth_retries=1` and `max_transient_retries=0` at the call site while global `max_auth_retries` stays `5`. Existing test `test_check_reviewers_cursor_preflight_rc2_one_shot` only covers probe rc `2`. If implementer wires only the global health-gate rule and omits the call-site `max_transient_retries=0`, a misclassified or transient probe rc `1` would run three attempts (default `LARCH_PROBE_RETRIES=2`) and break the definite-auth one-shot contract.
- **Proposed resolution**: Add a test mirroring preflight rc `2` with fake probe returning `1` and assert exactly one probe call with default env (no explicit `LARCH_PROBE_RETRIES`).

