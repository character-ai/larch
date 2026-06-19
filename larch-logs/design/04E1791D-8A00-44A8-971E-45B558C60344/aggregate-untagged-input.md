### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agents.py:1940-1951
- **Concern**: Item 3 pins immediate keychain release via external_startup_lock_release_after(state delay=0) but that helper always schedules threading.Timer release even when delay is 0. Scenario: check_reviewers runs cursor_auth_preflight then _cursor_probe_setup_chain to cursor_preread_service_token back-to-back; the first call's async release can leave the lock held while the second acquire spins (up to LARCH_EXTERNAL_STARTUP_LOCK_TRIES) adding health-gate latency or timeout under load
- **Proposed resolution**: Pin synchronous release for delay=0 (rmdir in finally before return) or hoist one lock around the combined Darwin keychain phase in check_reviewers and probe setup; add a test that back-to-back preflight+preread does not block on self-contention

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/agents.py:4268-4280
- **Concern**: _review_emit_launcher_result would call _compose_failure_diag on every exit including success. Scenario: The plan wires compose-before-classify into _review_emit_launcher_result, but that helper is invoked after successful Codex/Cursor review runs too (for example launch_codex_review_main ~4431 and launch_cursor_review_main ~4633). compose gathers non-empty sidecar/diag sections into .failure-diag even when launcher_exit is 0, so a green review can leave a spurious failure-diag carrier and skew later resolver/diagnostic consumers.
- **Proposed resolution**: Gate compose to launcher_exit != 0 inside _review_emit_launcher_result, matching _review_append_launch_failure. On success, only emit KVs from existing artifacts; do not compose.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:4043-4055 and 4404-4431
- **Concern**: Double compose on agent-failure paths when emit also composes. Scenario: On non-zero Codex/Cursor agent exits, _review_append_launch_failure already calls _compose_failure_diag before logging; the plan then composes again inside _review_emit_launcher_result. _compose_failure_diag appends an "additional failure diagnostics" block when the carrier already exists, so one failure produces duplicated sections and an inflated .failure-diag.
- **Proposed resolution**: [SCOPE-REDUCTION] For Item 7, delegate _review_failure_source to resolve_failure_diagnostic_source and fix _append_implement_launch_failure; in emit, forward stderr_sink into the resolver only. Do not re-compose on paths where append already ran. Reserve compose-in-emit for preflight-only emit call sites that never call append.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:4866-4879
- **Concern**: Implement stderr-tail regeneration rule is underspecified. Scenario: The plan says to regenerate output.stderr-tail when an existing tail came from a less-specific generic carrier, but gives no mechanical rule for detecting that case. Implementers can overwrite a correct tail, skip regeneration when sidecar stderr is still masked, or regenerate from the wrong source.
- **Proposed resolution**: Define an explicit rule: after compose+resolve, regenerate stderr-tail only when the tail file is missing OR when resolve_failure_diagnostic_source returns a different non-empty path than the one used for the existing tail; never overwrite when the resolved path matches the tail source. Pin this in test_agents.py.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agents.py:947-959 and 755-758
- **Concern**: Probe path can hit the startup lock three times per check_reviewers cursor pass. Scenario: After wrapping keychain reads, check_reviewers still does cursor_auth_preflight, then _cursor_probe_setup_chain calls cursor_preread_service_token again, then _run_one_cursor_probe acquires the lock a third time. That is correct for safety but adds avoidable latency on the health-gate path the issue asked to keep unchanged.
- **Proposed resolution**: [SCOPE-REDUCTION] Skip cursor_preread_service_token inside _cursor_probe_setup_chain when CURSOR_API_KEY is already set from the preflight/preread that ran immediately above in check_reviewers (and the analogous launch-review sequence), so keychain work and lock churn happen once per boundary.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_agent_voters.py:117-121
- **Concern**: Planned `_append_voter1_failure` regression monkeypatches `Path.read_bytes`, but the plan switches reads to `path.open("rb").read(limit)`. Scenario: A whole-file read regression in `_append_voter1_failure` would not raise on `read_bytes`; the new test would still pass while large `.diag` / `.launcher-stderr` files load fully into memory again
- **Proposed resolution**: Guard the bounded-read contract by monkeypatching `Path.open` (or a shared prefix helper) and asserting `read()` is called with limit 200/500, or assert `read_bytes` is never invoked on those paths

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/collect_results.py:788-810
- **Concern**: Item 6 phase `.launch-stderr` gap may remain: per-candidate loop checks only `{candidate}.launch-stderr`, not `{candidate_stem}-retry.txt.launch-stderr` or `{candidate_stem}-ns-retry.txt.launch-stderr`. Scenario: NS-retry launches write `{stem}-ns-retry.txt.launch-stderr`; a `*-phase3.txt` reviewer can still miss phase2 NS-retry launcher stderr when derived stderr-tail files are absent but NS-retry launch-stderr is populated
- **Proposed resolution**: Add retry/NS-retry `.launch-stderr` render steps after derived stderr-tail checks and before `{candidate}.launch-stderr`; extend `python/test_collect_results.py` with a phase3 fixture where only `*-phase2-ns-retry.txt.launch-stderr` is non-empty
