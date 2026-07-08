### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/core/config.py
- **Concern**: [SCOPE-REDUCTION] Plan adds MAIN_HEALTH_MAX_TRANSIENT_RETRIES=1 while CI_MONITOR_TRANSIENT_RERUN_MAX is already 1 in the same module. Scenario: Two independent constants with the same bound can drift if one is tuned later; the diff adds config surface without new behavior
- **Proposed resolution**: Reuse config.CI_MONITOR_TRANSIENT_RERUN_MAX in _postmerge_main_health_gate (or assign MAIN_HEALTH_MAX_TRANSIENT_RETRIES = CI_MONITOR_TRANSIENT_RERUN_MAX) and drop the new constant from the plan unless a deliberate split is documented



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:30-32
- **Concern**: Transient-recovery resume can still be reclassified by the flap-sensitive postmerge path. Scenario: The resume branch verifies `MAIN_REPAIR_HEAD` with `skip_flap_check=True`, then hands control to `run_postmerge_phase()`, which the plan does not change. That phase re-reads main health with the default flap check, so the same green rerun can still come back as fail and drop back to `NEEDS_USER_INPUT`.
- **Proposed resolution**: Thread the recovery bypass into `run_postmerge_phase()` and `_postmerge_main_health_gate()` for this resume path, or finalize directly after the green pre-check succeeds



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/implement/dispatch_ship.py:799-812
- **Concern**: python/larch/implement/ship.py postmerge TRANSIENT shares global ship-pr-net-retries-python.count. Scenario: A merge run that already consumed three CI-phase exit-6 transients can hit NEXT_ACTION=stall on the first postmerge auto-rerun instead of the planned emergency-repair handoff
- **Proposed resolution**: In dispatch_ship.py exempt PHASE=postmerge-push-watch from ship-pr-net-retries-python.count or add a postmerge-specific reship path; add a test_implement_dispatch.py case with count=3 and postmerge TRANSIENT ## Findings ### 1. Postmerge `TRANSIENT` shares the global route-exit net-retry counter (risk-integration) The plan routes the first postmerge push-CI failure through `Outcome.TRANSIENT` / exit 6 so Step 8 can `reship`. That reuses the phase-agnostic `ship-pr-net-retries-python.count` logic in `dispatch_ship.py` (cap `SHIP_ROUTE_TRANSIENT_STALL_RETRY=4`), which today only governs CI-monitor network transients. That coupling is separate from the new `MAIN_HEALTH_MAX_TRANSIENT_RETRIES` / `TRANSIENT_RETRIES` budget the plan adds in ship state. A run that already absorbed three earlier exit-6 transients during the merge loop can stall at `transient-retry-cap` on the first postmerge auto-rerun instead of falling through to `emergency-repair` / `postmerge-repair`. Before this change, the same postmerge failure went straight to exit 3 (`NEEDS_USER_INPUT`), so this is a narrow regression on an edge path. **Suggested revision:** Either exempt `PHASE=postmerge-push-watch` from the global net-retry counter in `dispatch_ship.py`, or document the shared budget in `postmerge-emergency-repair.md` and add a `test_implement_dispatch.py` regression with count=3 plus postmerge `TRANSIENT`.



### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:716-740
- **Concern**: Using `counters.transient_retries > 0` to set `skip_flap_check` is too broad.. Scenario: Any unrelated transient earlier in the run flips the global counter, so the first post-merge health check stops honoring same-SHA flap detection and can misclassify a real failure as green.
- **Proposed resolution**: Use a postmerge-specific retry marker, or gate the bypass only on the explicit postmerge retry path that just submitted `rerun_failed()`.



### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/tests/implement/test_ship.py:4464-4517
- **Concern**: The existing first-failure postmerge test still expects immediate `NEEDS_USER_INPUT`.. Scenario: Once the new transient retry lands, that test will fail and block verification unless it is rewritten to expect `Outcome.TRANSIENT` first.
- **Proposed resolution**: Rewrite this case into a first-failure transient assertion plus a separate second-failure emergency-repair assertion.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:665-783;python/larch/implement/ship_resume.py:577-591
- **Concern**: Postmerge retry and skip_flap_check reuse ship-wide TRANSIENT_RETRIES that CI monitor already increments. Scenario: TRANSIENT_RETRIES is persisted across the merge loop when ci_monitor sets transient_rerun_attempted (ship.py:1584-1594, test_ship.py:2892-2902). The plan keys both skip_flap_check=counters.transient_retries > 0 and the postmerge rerun budget off that same counter. A run that already has TRANSIENT_RETRIES>=1 before the first postmerge push-watch can skip the flap guard on the initial merged-SHA poll and treat the first postmerge failure as budget-exhausted (no ci_monitor.rerun_failed, straight to emergency-repair), leaving the reported operator path broken.
- **Proposed resolution**: Add a postmerge-only counter (for example MAIN_HEALTH_TRANSIENT_RETRIES in ship_state.py/ship_seed.py, optional ShipReconciliationCounters field) incremented only when _postmerge_main_health_gate submits a main-health rerun; gate skip_flap_check and MAIN_HEALTH_MAX_TRANSIENT_RETRIES on that counter only. Add a test_ship.py case that seeds TRANSIENT_RETRIES=1 from a prior CI transient and asserts the first postmerge failure still calls rerun_failed once and returns Outcome.TRANSIENT.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:1154-1164
- **Concern**: Plan does not require EMERGENCY_REPAIR_BRANCH guard before auto-finalize in the cited resume block. Scenario: The emergency-repair resume fix is specified only in the Approach bullet list; the ship.py update section lists reading EMERGENCY_REPAIR_BRANCH but does not restate the empty-branch guard in the resume-branch steps. An implementation that re-polls main health on every emergency-repair relaunch without checking EMERGENCY_REPAIR_BRANCH can call run_postmerge_phase while a real repair branch/PR is active, finalizing as merged and skipping the repair state machine.
- **Proposed resolution**: In the run_ship resume.start == "emergency-repair" steps, make the empty EMERGENCY_REPAIR_BRANCH (and no repair PR) check an explicit ordered guard before read_main_health/run_postmerge_phase; add a test_ship.py case with EMERGENCY_REPAIR_BRANCH set that asserts no run_postmerge_phase call and NEEDS_USER_INPUT is preserved.



### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ship.py:747-780; skills/implement/references/ship-pr-exit-matrix.md:23,43
- **Concern**: [SCOPE-REDUCTION] Postmerge rerun is routed through the generic rc 6 reship path. Scenario: After the PR is already merged, the planned failed-run rerun returns Outcome.TRANSIENT. route-exit maps rc 6 to reship, and reship runs ship pre-fix-rebase for every non-phase14 reship. That can rebase or conflict on the original merged feature branch before the driver can re-check the now-green main run, so the recovery path can still dead-end.
- **Proposed resolution**: Keep the narrow emergency-repair relaunch re-verification fix and drop the automatic postmerge rerun, or add an explicit postmerge-push-watch closed-PR reship carve-out that skips pre-fix rebase and relaunches the driver only.



### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:572-577,1584-1595
- **Concern**: Plan keys postmerge skip_flap_check to the global TRANSIENT_RETRIES counter. Scenario: An earlier PR-CI transient rerun can increment TRANSIENT_RETRIES before merge. The first merged-SHA health check would then skip same-SHA failure-flap detection before any postmerge rerun, allowing a failure-plus-latest-success flap to finalize as merged and also consuming the promised postmerge retry budget.
- **Proposed resolution**: Use a postmerge-specific persisted retry marker or counter for both skip_flap_check and the postmerge rerun budget, or reset/translate the counter at postmerge entry so only a submitted postmerge rerun enables skip_flap_check.



### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-Ship Ci State Machine
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/main_health.py:210-226; python/larch/implement/ship.py:729-783; plan Approach (post-merge push watch)
- **Concern**: TRANSIENT reship can re-enter emergency-repair while the submitted rerun is still in flight. Scenario: Plan returns Outcome.TRANSIENT as soon as ci_monitor.rerun_failed() submits, then Step 8 reships into _postmerge_main_health_gate → wait_main_health. wait_main_health returns on the first pass or fail with no settle loop (main_health.py:225-226). If GitHub still lists the merged-SHA push run as completed failure before the rerun flips to in_progress, re-entry sees fail with TRANSIENT_RETRIES already 1, the retry guard is false, and the gate writes PHASE=emergency-repair (current fail path at ship.py:747-783) even though the driver-initiated rerun is still running. That recreates the operator dead-end the issue reports, bypassing the intended single auto-retry.
- **Proposed resolution**: Persist the failed run id when emitting TRANSIENT (plan already says preserve failed-run context but only names PHASE/TRANSIENT_RETRIES). On re-entry with TRANSIENT_RETRIES>0, treat fail on that same run id as pending: poll until the run reaches success, a different terminal failure, or MAIN_HEALTH_WAIT_TIMEOUT_SEC, then only spend the emergency-repair budget on a confirmed failure. Mirror the post-rerun settle loop in python/larch/design/design_log_ship.py:223-228.



### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-Ship Ci State Machine
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:1584-1594; python/larch/implement/ship_resume.py:590; plan Approach (MAIN_HEALTH_MAX_TRANSIENT_RETRIES / TRANSIENT_RETRIES)
- **Concern**: Post-merge retry budget shares TRANSIENT_RETRIES with CI-monitor transients. Scenario: Plan gates the postmerge rerun on counters.transient_retries < MAIN_HEALTH_MAX_TRANSIENT_RETRIES and increments the same TRANSIENT_RETRIES field. That field is already incremented when CI monitor submits a transient rerun during the merge loop (ship.py:1584-1594, ship_resume.py:590). A run that consumed one CI transient rerun enters postmerge with TRANSIENT_RETRIES=1, so the first postmerge push failure skips ci_monitor.rerun_failed() and goes straight to emergency-repair despite MAIN_HEALTH_MAX_TRANSIENT_RETRIES=1.
- **Proposed resolution**: Use a postmerge-only counter (for example POSTMERGE_MAIN_HEALTH_TRANSIENT_RETRIES) or gate the rerun on increments written only from _postmerge_main_health_gate, not on the CI-monitor shared TRANSIENT_RETRIES field. ## 1. [correctness] TRANSIENT reship can declare emergency-repair before the submitted rerun finishes **Locations:** `python/larch/implement/main_health.py:210-226`, `python/larch/implement/ship.py:729-783`, plan **Approach → For post-merge push watch** **Concern:** The plan correctly routes terminal success through `run_postmerge_phase()` (`python/larch/implement/ship_pr.py:312-348`), which writes `post-merge-sentinel`, runs `finalize.postmerge`, and flushes logs before `phase=done`. That preserves post-merge sentinel, final report inputs, and teardown. The gap is in the new driver-initiated retry path. The plan returns `Outcome.TRANSIENT` immediately after `ci_monitor.rerun_failed()` submits. On reship, `_postmerge_main_health_gate()` calls `wait_main_health()`, which exits on the first `fail` (`main_health.py:225-226`). If the merged-SHA run still shows a completed failure before the rerun moves to `in_progress`, re-entry hits the existing fail branch (`ship.py:747-783`) with `TRANSIENT_RETRIES=1`, the retry guard is false, and the driver enters `PHASE=emergency-repair` while the submitted rerun may still be running. The plan says to preserve failed-run context in state, but the listed writes are only `PHASE=postmerge-push-watch` and `TRANSIENT_RETRIES`; without persisting the failed run id, re-entry cannot tell an in-flight rerun from a new real failure. **Suggested revision:** When emitting `Outcome.TRANSIENT`, persist `MAIN_REPAIR_RUN_ID` / `MAIN_REPAIR_HEAD` (or a dedicated rerun marker). On re-entry with `TRANSIENT_RETRIES>0`, do not treat the first `fail` on that run as terminal; poll until success, a different failure, or `MAIN_HEALTH_WAIT_TIMEOUT_SEC`, following the settle pattern in `python/larch/design/design_log_ship.py:223-228`. ## 2. [correctness] Post-merge retry budget is coupled to CI-monitor `TRANSIENT_RETRIES` **Locations:** `python/larch/implement/ship.py:1584-1594`, `python/larch/implement/ship_resume.py:590`, plan **Approach** (`MAIN_HEALTH_MAX_TRANSIENT_RETRIES`, `TRANSIENT_RETRIES`) **Concern:** The plan reuses the shared `TRANSIENT_RETRIES` ship-state field for both CI-monitor transient reruns and postmerge main-health reruns. CI monitor already increments that field (`ship.py:1584-1594`). After one CI transient rerun, `TRANSIENT_RETRIES=1`, so the plan's guard `transient_retries < MAIN_HEALTH_MAX_TRANSIENT_RETRIES` is false on the first postmerge failure and the driver skips its one allowed `rerun_failed()` call. The reported bug path (manual rerun + emergency-repair relaunch) is still fixed by the planned green `emergency-repair` resume branch calling `run_postmerge_phase()`. This coupling only weakens the new automatic postmerge retry. **Suggested revision:** Track postmerge health retries separately (dedicated state key incremented only in `_postmerge_main_health_gate`) or base the rerun gate on that postmerge-only counter while leaving CI `TRANSIENT_RETRIES` unchanged. --- **What the plan gets right (no finding):** - Green transient recovery through `run_postmerge_phase()` does not bypass sentinel, finalize, or teardown (`ship_pr.py:320-343`). - Emergency-repair resume with empty `EMERGENCY_REPAIR_BRANCH` and green `MAIN_REPAIR_HEAD` under `skip_flap_check=True` is the right narrow fix for the filed bug (`ship.py:1154-1163` today always re-emits `NEEDS_USER_INPUT`). - Real repair work stays on the existing repair-branch path (`ship_resume.py:96-100` checkout routing; plan keeps non-empty `EMERGENCY_REPAIR_BRANCH` on `NEEDS_USER_INPUT`). - `skip_flap_check` default `false` with only two call sites matches the failure-mode guard in the plan. - Scope stays narrow: no new `NEXT_ACTION`, no change to `postmerge-repair` routing (`config.py:69`, `ship-pr-exit-matrix.md:32`).



