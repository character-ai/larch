### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/tests/design/test_design_lifecycle.py:1993-2053
- **Concern**: [SCOPE-REDUCTION] Settle tests should not add pause rc=11 to the Python helper matrix. Scenario: Wrapper already owns pause and dedup-revise before dispatch; Python pause support duplicates side effects and expands scope beyond moving rc tables
- **Proposed resolution**: Limit settle-next-action matrix to postplan rc 0/10/12/13 per site; document rc 11/pause and dedup-revise as wrapper-only in edge cases and design-step35-settle.md ### 1. code-quality / correctness — `skills/design/references/step2b5-rc-handling.md` The plan adds `STEP2B5_NEXT_ACTION` but never defines the token set. `SETTLE_NEXT_ACTION` already has pinned strings (`gate-b-continue`, `gate-a-hard-size`, etc.) in `design-step35-settle.md` and structure tests. Without the same contract for Step 2b.5, the shared helper and shrunk reference cannot stay fail-closed. **Suggested revision:** Add a normative action table to `step2b5-rc-handling.md` and table-driven tests that pin every action and its diagnostic `STEP2B5_EXIT_RC`. ### 2. correctness / risk-integration — `skills/design/references/step2b5-rc-handling.md` The shrink list covers hard, partition, drift, no-trigger, rc2, and internal-error only. Current item 3 still requires soft-advisory breadcrumbs when `SOFT_ADVISORY=true` before hard/partition branches. An action-only rewrite risks dropping that behavior. **Suggested revision:** Keep soft-advisory as KV-driven prose before `STEP2B5_NEXT_ACTION` dispatch; add matrix coverage for both `SIZE_TRIGGER_FIRED` combinations. ### 3. risk-integration — `python/tests/design/test_design_cli_ports.py` The plan registers `design settle-next-action` in `cli.py` and `_DESIGN_LIFECYCLE_STDOUT_KEYS` but omits `test_design_cli_ports.py`. That test asserts every design port is in `_REGISTRY` and `_MACHINE_STDOUT_KEYS`; a new verb breaks CI without an update. **Suggested revision:** Add the file to **Files to modify/create** and extend `EXPECTED` with the settle-next-action entry. ### 4. architecture — settle pause boundary Plan edge cases keep pause in the wrapper, but the testing strategy says matrix-test pause rc `11` “if supported by the helper.” `design-step35-settle.sh` already emits `SETTLE_NEXT_ACTION=pause` and exits `11` before any rc-to-action table runs (lines 147-166, 254-257, 296-298). Adding pause to the Python helper would duplicate wrapper-owned side effects and violate minimum-change. **Suggested revision:** Scope the Python settle helper to postplan rc `0/10/12/13` only; keep pause and `dedup-revise` wrapper-only in docs and tests.

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_session.py:24-67
- **Concern**: [SCOPE-REDUCTION] `STEP2B5_EXIT_RC` expands the Step 2b.5 wire contract beyond the action-envelope change. Scenario: The plan preserves `step2b5_main`'s existing process rc and only needs `STEP2B5_NEXT_ACTION` to stop prompt-side rc recomputation; adding an allowlisted exit-rc/status key creates a second rc authority that callers can route from, contrary to the no-routing-semantics-change scope
- **Proposed resolution**: Remove `STEP2B5_EXIT_RC` and any new Step 2b.5 status key from the plan unless a caller consumes it; emit `STEP2B5_NEXT_ACTION` with the existing check-size KVs and keep the process rc as the sole Step 2b.5 rc contract

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_session.py:24-75
- **Concern**: [SCOPE-REDUCTION] STEP2B5_NEXT_ACTION/STEP2B5_EXIT_RC allowlist additions lack a writer. Scenario: PHASE_RESULT_ENV_ALLOW_KEYS gates phase_driver_write_result_env; step2b5 and postplan surfaces use stdout and .design-postplan-emit-result.env, not that writer; adding keys expands allowlist without acceptance-criteria benefit
- **Proposed resolution**: Omit STEP2B5_NEXT_ACTION and STEP2B5_EXIT_RC from PHASE_RESULT_ENV_ALLOW_KEYS; write STEP2B5_NEXT_ACTION only to step2b5 stdout and the postplan result env flush key list in design_postplan.py
