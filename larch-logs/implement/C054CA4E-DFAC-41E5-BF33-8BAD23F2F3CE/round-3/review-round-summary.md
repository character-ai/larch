# Review Round 3

- Mode: `diff`
- 18 accepted, 11 rejected (5 exonerated)

## Accepted Findings

### FINDING_10: risk-integration: Makefile:96 Makefile:399-400 scripts/relevant-checks.sh:93-94
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] test-design-route is wired into CI shards and relevant-checks but scripts/test-design-route.sh and .md are untracked. make test-harnesses-13 / make test-design-route fails on clean checkout with missing script. Commit scripts/test-design-route.sh and scripts/test-design-route.md or remove Makefile/relevant-checks registrations until they ship.
- **Suggested revision**: Address the concern above.


### FINDING_19: architecture: skills/design/SKILL.md:271-337
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] No post-handoff validation that ROUTE is non-empty and in the allowed enum after _route_rc=0. Result env missing/symlink-refused plus empty _route_out leaves ROUTE=""; clarify/already-planned/init guards do not run; run may continue without run-params.json. Abort before ROUTE case when ROUTE is empty or unknown; mirror Step 3 LOOP_STATUS guard; add structure-test pin.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/design/SKILL.md:265-266
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] No-op loops over _route_warn_lines/_route_error_lines after merge. Maintainers may think pre-ROUTE re-emit is missing or re-add duplicate prints; dead code obscures the real breadcrumb path (merge loops). Remove the loops or implement intentional re-emit once and dedupe merge-time prints.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: skills/design/SKILL.md:373-407
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] _init_rc=0 treated as success without requiring merged INIT_STATUS=ok and run-params.json. Symlink-refused result env and empty _init_out after exit 0 continue Step 0b without persisted tier/router flags. After merge on rc=0 require INIT_STATUS=ok and run-params.json exists; abort with explicit banner otherwise.
- **Suggested revision**: Address the concern above.


### FINDING_21: architecture: skills/design/scripts/design-init-runparams.sh:187-223
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Rename failure is WARN-only; write-run-params still runs and driver exits 0. Proceed path reaches later steps with run-params.json but issue title still not [DESIGNING]. Fail init on rename failure or add orchestrator title-state gate before Step 0c.
- **Suggested revision**: Address the concern above.


### FINDING_23: code-quality: skills/design/SKILL.md:265-266
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] _route_warn_lines/_route_error_lines loops are no-ops. Dead code suggests incomplete re-emit contract; confuses maintainers. Remove loops or implement explicit post-merge WARN/ERROR re-emit if still required.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: Makefile:87; scripts/relevant-checks.sh:93; skills/design/scripts/design-route.md:56; agent-lint.toml:973
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] test-design-route wired into Makefile relevant-checks agent-lint and design-route.md but scripts/test-design-route.sh is not committed make test-harnesses-13 fails on clean checkout with missing scripts/test-design-route.sh Commit scripts/test-design-route.sh and scripts/test-design-route.md with the wiring or revert all test-design-route references
- **Suggested revision**: Address the concern above.


### FINDING_25: architecture: scripts/test-design-route.sh; Makefile:87; skills/design/scripts/design-route.md:56
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] New dedicated test-design-route harness violates Round 1 Decision 2 and acceptance no new test-*.sh files Scope expands beyond agreed structure-test-only testing for #3245 Remove test-design-route harness and restore design-route.md harness text to test-design-structure.sh only
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: scripts/test-step0b-router-flag-recovery.sh:1015-1174
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Cases 8-10 added beyond plan limit of 7 unchanged cases Plan said re-point comments only; branch adds driver integration cases without plan update Revert Cases 8-10 or amend plan acceptance to document expanded coverage
- **Suggested revision**: Address the concern above.


### FINDING_27: correctness: skills/design/scripts/design-route.sh:234-239; skills/design/SKILL.md:272-274; skills/design/scripts/design-route.md:29
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] cancel-pause-load ROUTE not in plan acceptance enum Supplied acceptance lists six ROUTE values; runtime emits seventh Update plan acceptance and enum documentation or map to existing cancel route
- **Suggested revision**: Address the concern above.


### FINDING_30: **correctness** `skills/design/SKILL.md:231-334` — After `_route_rc=0`, the route handoff merges KVs but never validates that `ROUTE` is non-empty and one of the driver’s verdicts (`proceed`, `clarify`, `already-planned`, `cancel-title-filter`, `cancel-reentry-guard`, `cancel-pause-load`, or `resume@<STEP>`). The `case "${ROUTE:-}"` block only handles the three cancel routes and `resume@*`; `clarify`, `already-planned`, and `proceed` rely on later prose guards. If both handoff sources fail to supply `ROUTE` (for example symlink-refused `.design-route-result.env` plus empty `_route_out`, or a corrupt result file with no `ROUTE=` line), execution falls through with `ROUTE=""` and silently skips clarify, already-planned, and proceed gates while also skipping the sub-step 6 `ROUTE=proceed` init path — the failure mode the plan called out for empty `ROUTE` after exit 0. Step 3’s fence explicitly defaults invalid `LOOP_STATUS` (`skills/design/SKILL.md:936-938`); Step 0b has no parallel guard. **Suggested fix:** Immediately after the stdout merge loops and before brainstorm handling, abort with a Step-0b configuration/operational banner when `ROUTE` is empty or not in the known verdict set (mirror Step 3’s `LOOP_STATUS` validation pattern in `skills/design/scripts/test-step3-orchestrator-fence.sh:65-67`).
- **Reviewer**: dyn-handoff-protocol-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:231-334` — After `_route_rc=0`, the route handoff merges KVs but never validates that `ROUTE` is non-empty and one of the driver’s verdicts (`proceed`, `clarify`, `already-planned`, `cancel-title-filter`, `cancel-reentry-guard`, `cancel-pause-load`, or `resume@<STEP>`). The `case "${ROUTE:-}"` block only handles the three cancel routes and `resume@*`; `clarify`, `already-planned`, and `proceed` rely on later prose guards. If both handoff sources fail to supply `ROUTE` (for example symlink-refused `.design-route-result.env` plus empty `_route_out`, or a corrupt result file with no `ROUTE=` line), execution falls through with `ROUTE=""` and silently skips clarify, already-planned, and proceed gates while also skipping the sub-step 6 `ROUTE=proceed` init path — the failure mode the plan called out for empty `ROUTE` after exit 0. Step 3’s fence explicitly defaults invalid `LOOP_STATUS` (`skills/design/SKILL.md:936-938`); Step 0b has no parallel guard. **Suggested fix:** Immediately after the stdout merge loops and before brainstorm handling, abort with a Step-0b configuration/operational banner when `ROUTE` is empty or not in the known verdict set (mirror Step 3’s `LOOP_STATUS` validation pattern in `skills/design/scripts/test-step3-orchestrator-fence.sh:65-67`).
- **Suggested revision**: Address the concern above.


### FINDING_35: **architecture** `skills/design/scripts/design-init-runparams.sh:249-268` — On the success path the driver emits `emit_kv` lines to stdout (lines 249–255) before `phase_driver_write_result_env` (lines 266–268). That inverts the `design-route.sh` contract pinned by FINDING_19 in `scripts/test-design-structure.sh:845-850`, where the result file must be written before stdout emission. The Step 0b orchestrator reads `.design-init-runparams-result.env` first and only fills **missing** keys from `_init_out` (`skills/design/SKILL.md:378-393`). If a prior run left `INIT_STATUS=contract-drift` in the result file and a later run succeeds through jq-merge but fails the atomic result-env write, stdout can carry `INIT_STATUS=ok` while the stale file still says `contract-drift`; the orchestrator then hits the contract-drift branch at `skills/design/SKILL.md:394-396` despite a successful init body. **Suggested fix:** Mirror `design-route.sh`’s `emit_route_result`: build `_init_kvs`, call `phase_driver_write_result_env` first, then loop `emit_kv`; extend `test-design-structure.sh` with the same write-before-`emit_kv` line-order assert used for the route driver.
- **Reviewer**: dyn-driver-contract-drift-output.txt
- **Concern**: - **architecture** `skills/design/scripts/design-init-runparams.sh:249-268` — On the success path the driver emits `emit_kv` lines to stdout (lines 249–255) before `phase_driver_write_result_env` (lines 266–268). That inverts the `design-route.sh` contract pinned by FINDING_19 in `scripts/test-design-structure.sh:845-850`, where the result file must be written before stdout emission. The Step 0b orchestrator reads `.design-init-runparams-result.env` first and only fills **missing** keys from `_init_out` (`skills/design/SKILL.md:378-393`). If a prior run left `INIT_STATUS=contract-drift` in the result file and a later run succeeds through jq-merge but fails the atomic result-env write, stdout can carry `INIT_STATUS=ok` while the stale file still says `contract-drift`; the orchestrator then hits the contract-drift branch at `skills/design/SKILL.md:394-396` despite a successful init body. **Suggested fix:** Mirror `design-route.sh`’s `emit_route_result`: build `_init_kvs`, call `phase_driver_write_result_env` first, then loop `emit_kv`; extend `test-design-structure.sh` with the same write-before-`emit_kv` line-order assert used for the route driver.
- **Suggested revision**: Address the concern above.


### FINDING_36: **architecture** `scripts/test-design-structure.sh:845-850` — Structure tests pin write-before-stdout ordering only for `design-route.sh`, not for `design-init-runparams.sh`, even though both drivers share the same file-first + stdout-merge handoff in `skills/design/SKILL.md`. A future edit that reorders init emission would stay green in CI while reintroducing the stale-result-env misclassification above. **Suggested fix:** Add parallel greps/line-order checks on `design-init-runparams.sh` for `phase_driver_write_result_env "$RESULT_ENV"` preceding the success-path `emit_kv INIT_STATUS` block (and optionally a negative grep that success-path `emit_kv` does not appear above the final `phase_driver_write_result_env`).
- **Reviewer**: dyn-driver-contract-drift-output.txt
- **Concern**: - **architecture** `scripts/test-design-structure.sh:845-850` — Structure tests pin write-before-stdout ordering only for `design-route.sh`, not for `design-init-runparams.sh`, even though both drivers share the same file-first + stdout-merge handoff in `skills/design/SKILL.md`. A future edit that reorders init emission would stay green in CI while reintroducing the stale-result-env misclassification above. **Suggested fix:** Add parallel greps/line-order checks on `design-init-runparams.sh` for `phase_driver_write_result_env "$RESULT_ENV"` preceding the success-path `emit_kv INIT_STATUS` block (and optionally a negative grep that success-path `emit_kv` does not appear above the final `phase_driver_write_result_env`).
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: scripts/test-design-structure.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] cancel-pause-load ROUTE lacks structure-test grep pin. Orchestrator branch or driver emit for invalid pause resume could regress without structure-test failure (only test-design-route.sh covers it). Add grep anchors in test-design-structure.sh for cancel-pause-load in SKILL.md and design-route.sh.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: Makefile:399-400,scripts/relevant-checks.sh:93-94
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] test-design-route is registered in Makefile and relevant-checks but scripts/test-design-route.sh and .md are not in HEAD make test-design-route or relevant-checks after a clean checkout fails with missing script Commit scripts/test-design-route.sh and scripts/test-design-route.md or remove Makefile/relevant-checks/agent-lint references until the harness ships
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/design/SKILL.md:241-270
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Symlink refusal on .design-route-result.env skips file read; quiet mode leaves _route_out empty; no abort on empty ROUTE _route_rc=0 with symlinked result env leaves ROUTE unset; orchestrator may proceed without a valid verdict Abort when ROUTE is empty after _route_rc=0 or treat symlink refusal as a hard failure before ROUTE branches
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/design/scripts/design-route.sh:188-192,225-228
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Missing step-name-registry.tsv makes step_is_registered fail and routes valid pause resumes to cancel-pause-load Partial plugin tree: pause-load succeeds but resume always aborts Distinguish missing registry (operational error) from unknown step; or fail driver init if registry is absent
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: skills/design/SKILL.md:265-266
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] No-op loops where plan calls for pre-ROUTE WARN/ERROR re-emit Dead code; future editors may think re-emit is missing Remove no-op loops or implement explicit re-emit from _route_warn_lines/_route_error_lines
- **Suggested revision**: Address the concern above.


