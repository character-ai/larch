### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/step2b5-rc-handling.md:11-17
- **Concern**: Plan introduces STEP2B5_NEXT_ACTION but never pins the action-token vocabulary. Scenario: Implementers must invent strings; structure pins and orchestrator fail-closed branches will drift from SETTLE_NEXT_ACTION-style stability
- **Proposed resolution**: Add an explicit action table (e.g. hard-size, partition, drift-advisory, no-trigger, check-size-degraded, internal-error) to step2b5-rc-handling.md and matrix-test every token plus STEP2B5_EXIT_RC parity



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/step2b5-rc-handling.md:13-16
- **Concern**: Soft-advisory breadcrumbs are omitted from the step2b5 reference shrink list. Scenario: The refactor targets rc-based item 3; SOFT_ADVISORY=true informational prints before branches 4-7 can be dropped when switching to action-only dispatch
- **Proposed resolution**: Keep a dedicated soft-advisory subsection keyed off KVs before STEP2B5_NEXT_ACTION branching; add a lifecycle test with SOFT_ADVISORY=true and SIZE_TRIGGER_FIRED true/false



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/design/test_design_cli_ports.py:8-28
- **Concern**: New design settle-next-action CLI verb is absent from the plan file list and port smoke test. Scenario: CI port registry test fails on any new machine-stdout design verb not in EXPECTED
- **Proposed resolution**: Add ### UPDATED: python/tests/design/test_design_cli_ports.py with ("settle-next-action", module, func) and assert it is in _MACHINE_STDOUT_KEYS



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/tests/design/test_design_lifecycle.py:1993-2053
- **Concern**: [SCOPE-REDUCTION] Settle tests should not add pause rc=11 to the Python helper matrix. Scenario: Wrapper already owns pause and dedup-revise before dispatch; Python pause support duplicates side effects and expands scope beyond moving rc tables
- **Proposed resolution**: Limit settle-next-action matrix to postplan rc 0/10/12/13 per site; document rc 11/pause and dedup-revise as wrapper-only in edge cases and design-step35-settle.md ### 1. code-quality / correctness — `skills/design/references/step2b5-rc-handling.md` The plan adds `STEP2B5_NEXT_ACTION` but never defines the token set. `SETTLE_NEXT_ACTION` already has pinned strings (`gate-b-continue`, `gate-a-hard-size`, etc.) in `design-step35-settle.md` and structure tests. Without the same contract for Step 2b.5, the shared helper and shrunk reference cannot stay fail-closed. **Suggested revision:** Add a normative action table to `step2b5-rc-handling.md` and table-driven tests that pin every action and its diagnostic `STEP2B5_EXIT_RC`. ### 2. correctness / risk-integration — `skills/design/references/step2b5-rc-handling.md` The shrink list covers hard, partition, drift, no-trigger, rc2, and internal-error only. Current item 3 still requires soft-advisory breadcrumbs when `SOFT_ADVISORY=true` before hard/partition branches. An action-only rewrite risks dropping that behavior. **Suggested revision:** Keep soft-advisory as KV-driven prose before `STEP2B5_NEXT_ACTION` dispatch; add matrix coverage for both `SIZE_TRIGGER_FIRED` combinations. ### 3. risk-integration — `python/tests/design/test_design_cli_ports.py` The plan registers `design settle-next-action` in `cli.py` and `_DESIGN_LIFECYCLE_STDOUT_KEYS` but omits `test_design_cli_ports.py`. That test asserts every design port is in `_REGISTRY` and `_MACHINE_STDOUT_KEYS`; a new verb breaks CI without an update. **Suggested revision:** Add the file to **Files to modify/create** and extend `EXPECTED` with the settle-next-action entry. ### 4. architecture — settle pause boundary Plan edge cases keep pause in the wrapper, but the testing strategy says matrix-test pause rc `11` “if supported by the helper.” `design-step35-settle.sh` already emits `SETTLE_NEXT_ACTION=pause` and exits `11` before any rc-to-action table runs (lines 147-166, 254-257, 296-298). Adding pause to the Python helper would duplicate wrapper-owned side effects and violate minimum-change. **Suggested revision:** Scope the Python settle helper to postplan rc `0/10/12/13` only; keep pause and `dedup-revise` wrapper-only in docs and tests.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/step2b5-rc-handling.md:11-27
- **Concern**: Plan lists STEP2B5_NEXT_ACTION emission cases but never defines the stable action-token vocabulary or rc-to-action matrix the shrunk reference and tests must pin.. Scenario: Implementers can invent divergent tokens (e.g. hard-size vs plan-size-hard vs gate-a-hard-size) across step2b5_main, postplan-emit, step2b5-rc-handling.md, and test_design_postplan.py; structure pins cannot enforce parity and merged vs retained paths can drift while still passing rc assertions.
- **Proposed resolution**: Add an explicit STEP2B5_NEXT_ACTION table (mirroring settle-rc-dispatch.md) naming each token, trigger inputs (check_size rc, SIZE_TRIGGER_FIRED, PARTITION_REQUESTED, DRIFT_TRIGGER_FIRED), and expected process rc; require step2b5-rc-handling.md branch bodies to key only on those tokens and matrix tests to cover every row.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:348-351
- **Concern**: Retained Step 2b.5 callers still bind _plan_size_rc from the fence exit code; the plan does not add the settle-parity fail-closed contract to parse STEP2B5_NEXT_ACTION from design step2b5 stdout and refuse wrapper-rc fallback.. Scenario: After step2b5_main emits an action row, the orchestrator can keep branching on $? (including rc=0 with SIZE_TRIGGER_FIRED=true) and silently ignore or mis-parse STEP2B5_NEXT_ACTION, recreating the prompt-side rc dispatch this issue removes.
- **Proposed resolution**: Update Step 2b.5 item 3 and step2b5-rc-handling.md to require one whole-line STEP2B5_NEXT_ACTION= row from design-step2b5.sh stdout (or from .design-postplan-emit-result.env on direct-entry), stop for repair when absent/duplicate, and stop when action and wrapper rc disagree; drop _plan_size_rc as routing authority (rc remains diagnostic only).



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step35-settle.sh:147-216
- **Concern**: Plan scopes design settle-next-action to POSTPLAN_RC dispatch but test prose says pause rc 11 is in the Python matrix if supported; pause and dedup-revise are emitted and exited in Bash before any POSTPLAN_RC Python call.. Scenario: Moving pause or dedup-revise into the Python helper would change marker ordering and exit semantics; a table-driven test expecting Python to emit SETTLE_NEXT_ACTION=pause would encode the wrong contract.
- **Proposed resolution**: State explicitly that pause and dedup-revise stay wrapper-only (never call design settle-next-action); limit Python matrix tests to site x POSTPLAN_RC rows {0,10,12,13} only; document that POSTPLAN_RC=11 and dedup exit 1 bypass the helper.



### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_session.py:24-67
- **Concern**: [SCOPE-REDUCTION] `STEP2B5_EXIT_RC` expands the Step 2b.5 wire contract beyond the action-envelope change. Scenario: The plan preserves `step2b5_main`'s existing process rc and only needs `STEP2B5_NEXT_ACTION` to stop prompt-side rc recomputation; adding an allowlisted exit-rc/status key creates a second rc authority that callers can route from, contrary to the no-routing-semantics-change scope
- **Proposed resolution**: Remove `STEP2B5_EXIT_RC` and any new Step 2b.5 status key from the plan unless a caller consumes it; emit `STEP2B5_NEXT_ACTION` with the existing check-size KVs and keep the process rc as the sole Step 2b.5 rc contract



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_session.py:24-77
- **Concern**: The plan adds `STEP2B5_NEXT_ACTION` but never pins the canonical action token set (unlike `SETTLE_NEXT_ACTION` in `skills/design/scripts/design-step35-settle.md`).. Scenario: Implementers can emit different strings (`hard-size` vs `hard-trigger`, etc.) across `step2b5_main`, `postplan-emit`, docs, and tests while still passing loose tests; orchestrator branches misfire and parity with today's rc matrix breaks silently.
- **Proposed resolution**: Add an explicit action table to the plan (mirror settle): e.g. `hard-trigger`, `partition-split`, `drift-advisory`, `under-threshold`, `rc2-warning`, `internal-error`; pin exact strings in matrix tests and `scripts/test-design-structure.sh`.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:348
- **Concern**: Step 2b.5 item 3 still binds `_plan_size_rc` from `$?` and branches per rc; the plan only says "require `STEP2B5_NEXT_ACTION`" without a fail-closed stdout contract.. Scenario: After Python emits the action, the orchestrator can keep routing on exit code (or re-derive triggers from KVs), defeating the issue goal and reintroducing dual authority like the retired rc tables.
- **Proposed resolution**: Replace item 3 with: parse exactly one whole-line `STEP2B5_NEXT_ACTION=` from `design step2b5` stdout; stop for repair if missing/duplicate; branch only on that action; do not use `$?` or KV triggers as a fallback router (rc remains diagnostic only, same as settle).



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/step2b5-rc-handling.md:13-16
- **Concern**: The planned shrink to action-keyed bodies omits the existing soft-advisory breadcrumbs tied to `SOFT_ADVISORY` before hard/partition/drift/no-trigger routing.. Scenario: Plans with `mechanical_churn: true` lose the informational `⏩ 2b.5: plan-size — mechanical-churn advisory...` lines; operators lose the downgrade signal even when routing still reaches hard or under-threshold paths.
- **Proposed resolution**: When refactoring to `STEP2B5_NEXT_ACTION`, keep the soft-advisory prose as pre-branch UI steps keyed off `SOFT_ADVISORY` + `SIZE_TRIGGER_FIRED` KVs (not a separate action), and pin those lines in `scripts/test-design-structure.sh`.



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_postplan.py:305-324
- **Concern**: The shared Step 2b.5 helper must encode the same trigger priority as `postplan_emit_main` (`SIZE_TRIGGER_FIRED` before `partition_requested` before drift before under-threshold), but the plan does not state that ordering.. Scenario: A standalone `design step2b5` run could emit `partition-split` while `postplan-emit --with-plan-size` returns `POSTPLAN_RC=12` for the same KVs, violating the issue's "no routing semantics change" and failure-mode #3.
- **Proposed resolution**: Document in the helper contract: evaluate hard → partition (only when `SIZE_TRIGGER_FIRED=false`) → drift → under-threshold; add one paired fixture asserting both entrypoints emit matching `STEP2B5_NEXT_ACTION` / `POSTPLAN_RC` for the same KV inputs.



### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_postplan.py:151-180
- **Concern**: `postplan-emit --with-plan-size` is only planned to write `STEP2B5_NEXT_ACTION` to `.design-postplan-emit-result.env`, not emit it on stdout. Scenario: The feature is explicitly a stdout-envelope migration. With the current flush pattern, adding the key to `kvs` without adding it to the printed flush allowlist leaves `python/cli.py design postplan-emit --with-plan-size` output without the selected action row, so merged callers still lack the direct action envelope.
- **Proposed resolution**: Update the design_postplan step to add `STEP2B5_NEXT_ACTION` and any paired exit/status keys the helper emits to the `flush()` stdout key list as well as the result env, and make the postplan fixtures assert the row appears in stdout and the env.



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/step2b5-rc-handling.md:11-21
- **Concern**: Plan omits frozen STEP2B5_NEXT_ACTION token names and parity table. Scenario: Implementers must invent action strings for hard/partition/drift/no-trigger/rc2/internal-error; matrix tests and scripts/test-design-structure.sh cannot pin exact tokens; merged postplan and standalone step2b5 can diverge silently
- **Proposed resolution**: Add a canonical action table (like design-step35-settle.md for SETTLE_NEXT_ACTION) naming every STEP2B5_NEXT_ACTION value, map inputs to it, and table-drive tests in test_design_lifecycle.py and test_design_postplan.py over all combinations



### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/step2b5-rc-handling.md:15-16
- **Concern**: Mechanical-churn soft-advisory breadcrumbs have no owner after the shrink. Scenario: The plan drops rc=0 KV-driven item 3 prose but does not assign soft-advisory ⏩ breadcrumbs to Python stdout or a retained branch; orchestrator may branch only on STEP2B5_NEXT_ACTION and lose informational churn advisories on rc=0 paths
- **Proposed resolution**: Have the shared Step 2b.5 helper print the existing soft-advisory breadcrumbs on stdout when SOFT_ADVISORY=true (before STEP2B5_NEXT_ACTION), or explicitly keep one pre-branch soft-advisory step in step2b5-rc-handling.md keyed off SOFT_ADVISORY KVs



### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_session.py:24-75
- **Concern**: [SCOPE-REDUCTION] STEP2B5_NEXT_ACTION/STEP2B5_EXIT_RC allowlist additions lack a writer. Scenario: PHASE_RESULT_ENV_ALLOW_KEYS gates phase_driver_write_result_env; step2b5 and postplan surfaces use stdout and .design-postplan-emit-result.env, not that writer; adding keys expands allowlist without acceptance-criteria benefit
- **Proposed resolution**: Omit STEP2B5_NEXT_ACTION and STEP2B5_EXIT_RC from PHASE_RESULT_ENV_ALLOW_KEYS; write STEP2B5_NEXT_ACTION only to step2b5 stdout and the postplan result env flush key list in design_postplan.py



### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:28-31
- **Concern**: design postplan only requires STEP2B5_NEXT_ACTION in the result env, not the stdout envelope. Scenario: The issue asks for Python stdout envelopes. design postplan-emit --with-plan-size could write STEP2B5_NEXT_ACTION to .design-postplan-emit-result.env while the captured stdout relayed by design step2b-postplan lacks the action row, so merged/direct-entry routing fails the stated envelope contract and the planned tests would not catch it.
- **Proposed resolution**: Update the design_postplan.py step to emit STEP2B5_NEXT_ACTION through the existing flush stdout path as well as the env file, and update postplan tests to assert exactly one STEP2B5_NEXT_ACTION in stdout and in .design-postplan-emit-result.env.



### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:119-128
- **Concern**: Testing strategy does not validate the conditional-tier token-drop acceptance criterion. Scenario: The plan can pass the listed pytest and structure checks while conditional closure tokens stay flat or grow, leaving one explicit acceptance criterion unverifiable.
- **Proposed resolution**: Add a focused validation step using python3 python/cli.py skill-closure report and confirm the design conditional token or content-token count drops versus the pre-change value.



### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-Routing Parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/step2b5-rc-handling.md:13-17
- **Concern**: skills/design/SKILL.md:348-351. Scenario: Plan never freezes the STEP2B5_NEXT_ACTION token set
- **Proposed resolution**: Implementers must invent action names for hard/partition/drift/no-trigger/rc2/internal-error; markdown branches and matrix tests can diverge from orchestrator expectations Add an explicit action table (token → branch) in the plan and pin the same strings in test_design_lifecycle.py and test-design-structure.sh



### FINDING_20:
- **Reviewer(s)**: Cursor-dyn-Routing Parity
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_postplan.py:281-291
- **Concern**: python/larch/design/design_step2b.py:218-233. Scenario: python/larch/design/design_step5c.py:51-83
- **Proposed resolution**: Merged --with-plan-size coerces every plan check-size non-zero to exit 1 while retained step2b5 preserves rc 2 and continues with a warning A check-size rc 2 on the merged initial Step 2b path aborts /design via _postplan_decide fatal handling, but the retained step2b5 path prints the rc 2 warning and returns; shared-helper work will not achieve the stated rc-matrix parity unless this split is resolved State whether merged paths intentionally stay fatal on check-size failure or extend postplan_emit_main to preserve check-size rc (especially 2), emit STEP2B5_NEXT_ACTION, and add a matching test_design_postplan.py fixture



### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-Routing Parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step35-settle.sh:286-302
- **Concern**: skills/design/references/settle-rc-dispatch.md:17-27. Scenario: Wrapper contract omits mandatory SETTLE_EXIT_RC validation
- **Proposed resolution**: Plan requires printing SETTLE_NEXT_ACTION and exiting SETTLE_EXIT_RC, but only names a single-row action guard; orchestrator action/rc disagreement checks need both keys and the wrapper should fail closed when SETTLE_EXIT_RC is missing or duplicates Require design-step35-settle.sh to parse exactly one SETTLE_EXIT_RC, abort on absence/duplicates, and update settle-rc-dispatch.md plus design-step35-settle.md with action↔SETTLE_EXIT_RC pairs for disagreement checks



### FINDING_22:
- **Reviewer(s)**: Cursor-dyn-Routing Parity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_postplan.py:151-180
- **Concern**: python/larch/design/design_session.py:24-77. Scenario: Postplan emit path not wired to flush STEP2B5_NEXT_ACTION
- **Proposed resolution**: Plan adds STEP2B5_NEXT_ACTION to PHASE_RESULT_ENV_ALLOW_KEYS and says write it into .design-postplan-emit-result.env, but flush() only prints an enumerated key list that omits STEP2B5_NEXT_ACTION/STEP2B5_EXIT_RC; direct-entry gate-a-hard-size reads would miss the action row Add STEP2B5_NEXT_ACTION (and STEP2B5_EXIT_RC if used) to kvs, the flush() key loop, and a test_design_postplan.py assertion on the env file contents



### FINDING_23:
- **Reviewer(s)**: Codex-dyn-Routing Parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:16-19; skills/design/scripts/design-step35-settle.sh:272-306
- **Concern**: Settle migration does not require the exit-code row it consumes. Scenario: The plan requires exactly one SETTLE_NEXT_ACTION but then tells Bash to exit with SETTLE_EXIT_RC; helper output with missing, duplicate, or corrupt SETTLE_EXIT_RC can change legacy exits 0/10/11/12/13 or the current contract-error exit 3 even when the action row is present.
- **Proposed resolution**: Revise the settle wrapper step to require exactly one numeric SETTLE_EXIT_RC, reject duplicates or missing rows as the existing wrapper contract error, and preserve the current exit matrix.



### FINDING_24:
- **Reviewer(s)**: Codex-dyn-Routing Parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:21-31; python/larch/review/plan_review.py:115-135; python/larch/review/plan_review_common.py:37-58
- **Concern**: Python in-loop post-apply still routes by postplan rc. Scenario: The plan updates step2b5 and postplan emitters, but the Step 3 Python loop still branches on proc.returncode for 0/11/12/10/13 and POSTPLAN_EMIT_KEYS would drop STEP2B5_NEXT_ACTION from the persisted envelope. That leaves a Python rc dispatch table after Bash and markdown move to action keys.
- **Proposed resolution**: Add plan updates for plan_review.py and plan_review_common.py: read STEP2B5_NEXT_ACTION from .design-postplan-emit-result.env, route the existing hard/partition/drift/no-trigger behavior from that action while preserving process rc compatibility, and allow the action key in POSTPLAN_EMIT_KEYS.



