### FINDING_1: code-quality: scripts/test-design-route.sh:1
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] New offline route harness added despite plan Round 1 Decision 2 forbidding new driver test harnesses. CI and contributor surface grow (Makefile shard, agent-lint, relevant-checks) while the written plan promised only two updated harnesses; future work may assume no third harness exists. Fold cases into test-design-structure.sh per plan, or update plan/acceptance to bless test-design-route.sh and document why.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/SKILL.md:265-266
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] No-op loops over _route_warn_lines/_route_error_lines after merge. Maintainers may think pre-ROUTE re-emit is missing or re-add duplicate prints; dead code obscures the real breadcrumb path (merge loops). Remove the loops or implement intentional re-emit once and dedupe merge-time prints.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/design-route.sh:38-58
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] plan_block_present duplicates plan-block-read.sh pairing rules. Next marker-rule fix updated only in plan-block-read.sh could leave design-route.sh routing already-planned incorrectly. Extract shared presence helper or single source of truth for marker pairing.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/scripts/design-route.sh:23-36
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Duplicated validate_plain_scalar/validate_repo in both drivers. Argv validation fixes must be applied twice; risk of skew between route and init drivers. Centralize in lib-phase-driver.sh or lib-design-driver-argv.sh.
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

### FINDING_10: risk-integration: Makefile:96 Makefile:399-400 scripts/relevant-checks.sh:93-94
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] test-design-route is wired into CI shards and relevant-checks but scripts/test-design-route.sh and .md are untracked. make test-harnesses-13 / make test-design-route fails on clean checkout with missing script. Commit scripts/test-design-route.sh and scripts/test-design-route.md or remove Makefile/relevant-checks registrations until they ship.
- **Suggested revision**: Address the concern above.

### FINDING_11: **Argv hardening**: `--issue`, `--claude-pid`, `--repo`, `--issue-title`, and `--issue-body-file` are validated (`validate_repo`, `validate_plain_scalar`, numeric checks, regular-file + no-symlink on the body file) in `design-route.sh` / `design-init-runparams.sh`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Argv hardening**: `--issue`, `--claude-pid`, `--repo`, `--issue-title`, and `--issue-body-file` are validated (`validate_repo`, `validate_plain_scalar`, numeric checks, regular-file + no-symlink on the body file) in `design-route.sh` / `design-init-runparams.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_12: **Symlink refusal** on `.design-route-result.env` / `.design-init-runparams-result.env` in both `phase_driver_write_result_env` and the orchestrator fences matches the Step 3 precedent.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Symlink refusal** on `.design-route-result.env` / `.design-init-runparams-result.env` in both `phase_driver_write_result_env` and the orchestrator fences matches the Step 3 precedent.
- **Suggested revision**: Address the concern above.

### FINDING_13: **Resume safety**: `step_is_registered` plus `ROUTE=cancel-pause-load` for `LOAD_OK=true` with missing/unregistered `STEP` closes a class of bad pause payloads before the orchestrator jumps steps (`design-route.sh` ~195–241, `SKILL.md` ~272–274).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Resume safety**: `step_is_registered` plus `ROUTE=cancel-pause-load` for `LOAD_OK=true` with missing/unregistered `STEP` closes a class of bad pause payloads before the orchestrator jumps steps (`design-route.sh` ~195–241, `SKILL.md` ~272–274).
- **Suggested revision**: Address the concern above.

### FINDING_14: **Orchestrator KV merge** uses an allowlisted `case` before `printf -v` — unknown keys cannot become dynamic variable names (`SKILL.md` ~247–263).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Orchestrator KV merge** uses an allowlisted `case` before `printf -v` — unknown keys cannot become dynamic variable names (`SKILL.md` ~247–263).
- **Suggested revision**: Address the concern above.

### FINDING_15: **REPO forwarding** after a single `resolve-repo.sh` / `gh repo view` resolve reduces wrong-remote `gh` operations on fork/multi-remote checkouts (planned FINDING_1 R4).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **REPO forwarding** after a single `resolve-repo.sh` / `gh repo view` resolve reduces wrong-remote `gh` operations on fork/multi-remote checkouts (planned FINDING_1 R4).
- **Suggested revision**: Address the concern above.

### FINDING_16: **Pause-load trust chain** remains intact: `design-pause-load.sh` still validates slugs, steps, repos, and emits fixed-token `ERROR=` values; drivers only relay stdout KVs.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Pause-load trust chain** remains intact: `design-pause-load.sh` still validates slugs, steps, repos, and emits fixed-token `ERROR=` values; drivers only relay stdout KVs. No new secret material, `eval` on untrusted input, or unsafe deserializers appear in the diff. Router-flag `jq` merge uses `--argjson` booleans and a fixed filter over a path under `$DESIGN_TMPDIR`. Residual risk (result-env TOCTOU / last-key-wins parsing, collaborator-driven issue content in banners) is **pre-existing or local-user** in scope and not materially worse than Step 3’s file-first handoff; not elevated to Important/Latent under your scope rules.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/lib-title-eligibility.sh:38,42` — `eval "$_saved_shopt"` for `nocasematch` restore is a long-standing pattern in a file the diff only sources, not modifies.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `skills/design/scripts/design-route.sh:268` — unquoted `for _rkv in $_reentry_out` word-splitting is inherited from prior inline Step 0b; values today are numeric or fixed-path KVs from `lib-design-reentry-guard.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_19: architecture: skills/design/SKILL.md:271-337
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] No post-handoff validation that ROUTE is non-empty and in the allowed enum after _route_rc=0. Result env missing/symlink-refused plus empty _route_out leaves ROUTE=""; clarify/already-planned/init guards do not run; run may continue without run-params.json. Abort before ROUTE case when ROUTE is empty or unknown; mirror Step 3 LOOP_STATUS guard; add structure-test pin.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/design/SKILL.md:373-407
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] _init_rc=0 treated as success without requiring merged INIT_STATUS=ok and run-params.json. Symlink-refused result env and empty _init_out after exit 0 continue Step 0b without persisted tier/router flags. After merge on rc=0 require INIT_STATUS=ok and run-params.json exists; abort with explicit banner otherwise.
- **Suggested revision**: Address the concern above.

### FINDING_21: architecture: skills/design/scripts/design-init-runparams.sh:187-223
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Rename failure is WARN-only; write-run-params still runs and driver exits 0. Proceed path reaches later steps with run-params.json but issue title still not [DESIGNING]. Fail init on rename failure or add orchestrator title-state gate before Step 0c.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/design/scripts/design-init-runparams.sh:238-241
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] jq router-flag merge failure logs only to execution-issues.md. Operator sees INIT_STATUS=ok; partition/brainstorm/manual argv flags may not persist across subshells. add_warn on jq failure with operator-visible text in addition to append-tool-failure.sh.
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

### FINDING_28: architecture: skills/design/scripts/design-init-runparams.sh:178-184; skills/design/scripts/design-init-runparams.md:31; skills/design/SKILL.md:398-400
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] INIT_STATUS env-refresh-failed outside plan allowlist ok contract-drift Consumers of documented INIT_STATUS set miss env-refresh-failed handling Extend plan and design-init-runparams.md allowlist or collapse into documented statuses
- **Suggested revision**: Address the concern above.

### FINDING_29: code-quality: skills/design/SKILL.md:265-266
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] No-op loops over _route_warn_lines and _route_error_lines after route merge Dead code suggests incomplete Round 2 pre-branch re-emit step Remove no-op loops or add explicit WARN ERROR re-emit if required
- **Suggested revision**: Address the concern above.

### FINDING_30: **correctness** `skills/design/SKILL.md:231-334` — After `_route_rc=0`, the route handoff merges KVs but never validates that `ROUTE` is non-empty and one of the driver’s verdicts (`proceed`, `clarify`, `already-planned`, `cancel-title-filter`, `cancel-reentry-guard`, `cancel-pause-load`, or `resume@<STEP>`). The `case "${ROUTE:-}"` block only handles the three cancel routes and `resume@*`; `clarify`, `already-planned`, and `proceed` rely on later prose guards. If both handoff sources fail to supply `ROUTE` (for example symlink-refused `.design-route-result.env` plus empty `_route_out`, or a corrupt result file with no `ROUTE=` line), execution falls through with `ROUTE=""` and silently skips clarify, already-planned, and proceed gates while also skipping the sub-step 6 `ROUTE=proceed` init path — the failure mode the plan called out for empty `ROUTE` after exit 0. Step 3’s fence explicitly defaults invalid `LOOP_STATUS` (`skills/design/SKILL.md:936-938`); Step 0b has no parallel guard. **Suggested fix:** Immediately after the stdout merge loops and before brainstorm handling, abort with a Step-0b configuration/operational banner when `ROUTE` is empty or not in the known verdict set (mirror Step 3’s `LOOP_STATUS` validation pattern in `skills/design/scripts/test-step3-orchestrator-fence.sh:65-67`).
- **Reviewer**: dyn-handoff-protocol-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:231-334` — After `_route_rc=0`, the route handoff merges KVs but never validates that `ROUTE` is non-empty and one of the driver’s verdicts (`proceed`, `clarify`, `already-planned`, `cancel-title-filter`, `cancel-reentry-guard`, `cancel-pause-load`, or `resume@<STEP>`). The `case "${ROUTE:-}"` block only handles the three cancel routes and `resume@*`; `clarify`, `already-planned`, and `proceed` rely on later prose guards. If both handoff sources fail to supply `ROUTE` (for example symlink-refused `.design-route-result.env` plus empty `_route_out`, or a corrupt result file with no `ROUTE=` line), execution falls through with `ROUTE=""` and silently skips clarify, already-planned, and proceed gates while also skipping the sub-step 6 `ROUTE=proceed` init path — the failure mode the plan called out for empty `ROUTE` after exit 0. Step 3’s fence explicitly defaults invalid `LOOP_STATUS` (`skills/design/SKILL.md:936-938`); Step 0b has no parallel guard. **Suggested fix:** Immediately after the stdout merge loops and before brainstorm handling, abort with a Step-0b configuration/operational banner when `ROUTE` is empty or not in the known verdict set (mirror Step 3’s `LOOP_STATUS` validation pattern in `skills/design/scripts/test-step3-orchestrator-fence.sh:65-67`).
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] The `for _w in "${_route_warn_lines[@]}"; do :; done` / `for _e in "${_route_error_lines[@]}"; do :; done` loops at `skills/design/SKILL.md:265-266` are inert no-ops, not a side-channel flush. WARN/ERROR surfacing is handled by immediate `printf` during the file-first and stdout-merge loops (`250-251`, `261-262`), which addresses Round 5 file-only coverage; the arrays exist for dedup only.
- **Reviewer**: dyn-handoff-protocol-output.txt
- **Concern**: - The `for _w in "${_route_warn_lines[@]}"; do :; done` / `for _e in "${_route_error_lines[@]}"; do :; done` loops at `skills/design/SKILL.md:265-266` are inert no-ops, not a side-channel flush. WARN/ERROR surfacing is handled by immediate `printf` during the file-first and stdout-merge loops (`250-251`, `261-262`), which addresses Round 5 file-only coverage; the arrays exist for dedup only.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] `cancel-pause-load` handling is wired correctly: `design-route.sh` emits it with exit 0 (`227-233`, `289`), and the orchestrator aborts in the `case` arm (`272-274`).
- **Reviewer**: dyn-handoff-protocol-output.txt
- **Concern**: - `cancel-pause-load` handling is wired correctly: `design-route.sh` emits it with exit 0 (`227-233`, `289`), and the orchestrator aborts in the `case` arm (`272-274`).
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Stdout merge fill-only logic (`[[ -n "${!_key:-}" ]] || printf -v`) correctly avoids overwriting file-sourced routing keys with empty stdout values; an empty pre-initialized `ROUTE=""` still allows stdout to populate `ROUTE`.
- **Reviewer**: dyn-handoff-protocol-output.txt
- **Concern**: - Stdout merge fill-only logic (`[[ -n "${!_key:-}" ]] || printf -v`) correctly avoids overwriting file-sourced routing keys with empty stdout values; an empty pre-initialized `ROUTE=""` still allows stdout to populate `ROUTE`.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] Init handoff (`373-405`) matches the intended exit-code fence (`_init_rc=2` / unexpected non-zero abort; `_init_rc=1` merge then `INIT_STATUS` handling). No in-scope correctness defect found there beyond the shared “prose-gated sub-step 6” pattern (init fence runs only when the orchestrator honors `ROUTE=proceed`).
- **Reviewer**: dyn-handoff-protocol-output.txt
- **Concern**: - Init handoff (`373-405`) matches the intended exit-code fence (`_init_rc=2` / unexpected non-zero abort; `_init_rc=1` merge then `INIT_STATUS` handling). No in-scope correctness defect found there beyond the shared “prose-gated sub-step 6” pattern (init fence runs only when the orchestrator honors `ROUTE=proceed`).
- **Suggested revision**: Address the concern above.

### FINDING_35: **architecture** `skills/design/scripts/design-init-runparams.sh:249-268` — On the success path the driver emits `emit_kv` lines to stdout (lines 249–255) before `phase_driver_write_result_env` (lines 266–268). That inverts the `design-route.sh` contract pinned by FINDING_19 in `scripts/test-design-structure.sh:845-850`, where the result file must be written before stdout emission. The Step 0b orchestrator reads `.design-init-runparams-result.env` first and only fills **missing** keys from `_init_out` (`skills/design/SKILL.md:378-393`). If a prior run left `INIT_STATUS=contract-drift` in the result file and a later run succeeds through jq-merge but fails the atomic result-env write, stdout can carry `INIT_STATUS=ok` while the stale file still says `contract-drift`; the orchestrator then hits the contract-drift branch at `skills/design/SKILL.md:394-396` despite a successful init body. **Suggested fix:** Mirror `design-route.sh`’s `emit_route_result`: build `_init_kvs`, call `phase_driver_write_result_env` first, then loop `emit_kv`; extend `test-design-structure.sh` with the same write-before-`emit_kv` line-order assert used for the route driver.
- **Reviewer**: dyn-driver-contract-drift-output.txt
- **Concern**: - **architecture** `skills/design/scripts/design-init-runparams.sh:249-268` — On the success path the driver emits `emit_kv` lines to stdout (lines 249–255) before `phase_driver_write_result_env` (lines 266–268). That inverts the `design-route.sh` contract pinned by FINDING_19 in `scripts/test-design-structure.sh:845-850`, where the result file must be written before stdout emission. The Step 0b orchestrator reads `.design-init-runparams-result.env` first and only fills **missing** keys from `_init_out` (`skills/design/SKILL.md:378-393`). If a prior run left `INIT_STATUS=contract-drift` in the result file and a later run succeeds through jq-merge but fails the atomic result-env write, stdout can carry `INIT_STATUS=ok` while the stale file still says `contract-drift`; the orchestrator then hits the contract-drift branch at `skills/design/SKILL.md:394-396` despite a successful init body. **Suggested fix:** Mirror `design-route.sh`’s `emit_route_result`: build `_init_kvs`, call `phase_driver_write_result_env` first, then loop `emit_kv`; extend `test-design-structure.sh` with the same write-before-`emit_kv` line-order assert used for the route driver.
- **Suggested revision**: Address the concern above.

### FINDING_36: **architecture** `scripts/test-design-structure.sh:845-850` — Structure tests pin write-before-stdout ordering only for `design-route.sh`, not for `design-init-runparams.sh`, even though both drivers share the same file-first + stdout-merge handoff in `skills/design/SKILL.md`. A future edit that reorders init emission would stay green in CI while reintroducing the stale-result-env misclassification above. **Suggested fix:** Add parallel greps/line-order checks on `design-init-runparams.sh` for `phase_driver_write_result_env "$RESULT_ENV"` preceding the success-path `emit_kv INIT_STATUS` block (and optionally a negative grep that success-path `emit_kv` does not appear above the final `phase_driver_write_result_env`).
- **Reviewer**: dyn-driver-contract-drift-output.txt
- **Concern**: - **architecture** `scripts/test-design-structure.sh:845-850` — Structure tests pin write-before-stdout ordering only for `design-route.sh`, not for `design-init-runparams.sh`, even though both drivers share the same file-first + stdout-merge handoff in `skills/design/SKILL.md`. A future edit that reorders init emission would stay green in CI while reintroducing the stale-result-env misclassification above. **Suggested fix:** Add parallel greps/line-order checks on `design-init-runparams.sh` for `phase_driver_write_result_env "$RESULT_ENV"` preceding the success-path `emit_kv INIT_STATUS` block (and optionally a negative grep that success-path `emit_kv` does not appear above the final `phase_driver_write_result_env`).
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] Cross-checked the scout-listed `grep -Fq` literals against `design-route.sh` and `design-init-runparams.sh` (`design-pause-load.sh" --design-tmpdir …`)`, `step_is_registered`, `phase_driver_write_result_env "$RESULT_ENV"`, `INIT_STATUS=env-refresh-failed`, `_wdce_args+=(--manual-requested true)`): all are present; no silent harness/string drift found for those pins.
- **Reviewer**: dyn-driver-contract-drift-output.txt
- **Concern**: - Cross-checked the scout-listed `grep -Fq` literals against `design-route.sh` and `design-init-runparams.sh` (`design-pause-load.sh" --design-tmpdir …`)`, `step_is_registered`, `phase_driver_write_result_env "$RESULT_ENV"`, `INIT_STATUS=env-refresh-failed`, `_wdce_args+=(--manual-requested true)`): all are present; no silent harness/string drift found for those pins.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] `test-step0b-router-flag-recovery.sh` cases 8–10 invoke the real `design-init-runparams.sh` with stubbed `CLAUDE_PLUGIN_ROOT` helpers; stubs are sufficient for jq-failure, missing-file WARN, and jq-unavailable paths.
- **Reviewer**: dyn-driver-contract-drift-output.txt
- **Concern**: - `test-step0b-router-flag-recovery.sh` cases 8–10 invoke the real `design-init-runparams.sh` with stubbed `CLAUDE_PLUGIN_ROOT` helpers; stubs are sufficient for jq-failure, missing-file WARN, and jq-unavailable paths.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] The branch adds `scripts/test-design-route.sh` (also wired in `Makefile`) despite the #3245 plan’s “no new driver test harnesses” decision; it is documented in `design-route.md` and exercises `cancel-pause-load` / plan-marker routing usefully.
- **Reviewer**: dyn-driver-contract-drift-output.txt
- **Concern**: - The branch adds `scripts/test-design-route.sh` (also wired in `Makefile`) despite the #3245 plan’s “no new driver test harnesses” decision; it is documented in `design-route.md` and exercises `cancel-pause-load` / plan-marker routing usefully.
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] `skills/design/SKILL.md:265-266` uses no-op `for _w` / `for _e` loops where the plan called for pre-branch WARN/ERROR re-emit; breadcrumbs are already printed in the file-first/stdout `case` arms, so behavior looks correct but the loops are misleading dead code.
- **Reviewer**: dyn-driver-contract-drift-output.txt
- **Concern**: - `skills/design/SKILL.md:265-266` uses no-op `for _w` / `for _e` loops where the plan called for pre-branch WARN/ERROR re-emit; breadcrumbs are already printed in the file-first/stdout `case` arms, so behavior looks correct but the loops are misleading dead code.
- **Suggested revision**: Address the concern above.

