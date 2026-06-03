### FINDING_1: correctness: skills/design/scripts/design-plan-quality-assessor.sh:237-257
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Driver ignores assess-plan-round.sh exit code and defaults to skipped on empty stdout. assess-plan-round.sh exits 2 after tmpdir validation failure; driver exits 0 with ASSESSOR_STATUS=skipped; /design continues past Step 3.6 without orchestrator catch-all abort (inline set -e would have aborted). Branch on _assess_rc after assess capture; fail closed or emit explicit degraded status; add harness with ASSESS_STUB_RC=2 and no KVs.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/scripts/test-design-plan-quality-assessor.sh:164-180
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] apply_step3_6_handoff does not use qualified CLAUDE_PLUGIN_ROOT path from plan/SKILL.md pins. Regression in PATH/CWD when invoking bare script path would not be caught by handoff mirror tests. Invoke "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-plan-quality-assessor.sh" in handoff; assert pattern in harness.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/test-design-plan-quality-assessor.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness omits catch-all handoff abort test for driver exit not in {0,2}. Third SKILL.md abort guard can drift without CI failure. Add stub driver exit 3; assert failed banner and handoff return 1.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: skills/design/SKILL.md:1082-1084
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] _assessor_parse_ok set on any routing key not ASSESSOR_STATUS. Partial env file could suppress stdout WARN replay while ASSESSOR_STATUS stays empty until later guard. Set parse ok only when ASSESSOR_STATUS read from file succeeds.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/design/scripts/design-plan-quality-assessor.sh:38-61
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated json_scalar_or_sed/parse_kv helpers vs design-postplan-emit.sh. Future KV/workflow_path parsing fixes must be duplicated. Extract shared helpers to lib-phase-driver if touching drivers anyway.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/design/SKILL.md:1047-1058
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] No timing-ledger mark for Step 3.6. HARD assessor duration missing from timing reports. Add timing-ledger mark consistent with Steps 3.5/3b.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] **Pre-existing rollback cursor write** — On `write-after` failure the driver still sets `review-round-count.txt` to `ROUND_NUM-1` but calls `write-cursor --value "$ROUND_NUM"` (not `ROUND_NUM-1`). That matches the removed inline `SKILL.md` block; this branch does not introduce it. If cursor and count are meant to stay aligned, that belongs to a separate change with `run-step3-review.sh` / cap semantics tests.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Pre-existing rollback cursor write** — On `write-after` failure the driver still sets `review-round-count.txt` to `ROUND_NUM-1` but calls `write-cursor --value "$ROUND_NUM"` (not `ROUND_NUM-1`). That matches the removed inline `SKILL.md` block; this branch does not introduce it. If cursor and count are meant to stay aligned, that belongs to a separate change with `run-step3-review.sh` / cap semantics tests.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] **`_assess_rc` is never consulted** — `design-plan-quality-assessor.sh` captures `assess-plan-round.sh` exit code but always settles at driver exit `0` after KV defaults. Safe today because `assess-plan-round.sh` only exits `0` or `2`, but a future non-zero “failure” exit without KVs would be treated as `ASSESSOR_STATUS=skipped` instead of triggering the orchestrator’s catch-all abort.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **`_assess_rc` is never consulted** — `design-plan-quality-assessor.sh` captures `assess-plan-round.sh` exit code but always settles at driver exit `0` after KV defaults. Safe today because `assess-plan-round.sh` only exits `0` or `2`, but a future non-zero “failure” exit without KVs would be treated as `ASSESSOR_STATUS=skipped` instead of triggering the orchestrator’s catch-all abort. --- ### Plan / requirements check | Requirement | Status | |-------------|--------| | Phase driver with `LARCH_*_SH` seams, pause checkpoint, `set +e` child calls | Met | | `.step3.6-assessor.env` via `phase_driver_write_result_env` + stdout KVs | Met | | `SKILL.md` qualified invoke, HARD `🔶` before invoke, postplan handoff + abort block | Met | | WORSE gate / Stop branch unchanged (prompt-side) | Met | | Harness + Makefile + `test-design-structure.sh` pins | Met | | Exit `0` settled / `2` config / never `1` | Met | --- ### Notes (non-findings)
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Quiet contract (`larch_quiet_init` + `emit_kv` on FD 3) matches `design-postplan-emit.sh`; command substitution in `SKILL.md` should still receive KVs the same way as the old inline `assess-plan-round.sh` capture.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Quiet contract (`larch_quiet_init` + `emit_kv` on FD 3) matches `design-postplan-emit.sh`; command substitution in `SKILL.md` should still receive KVs the same way as the old inline `assess-plan-round.sh` capture.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Non-HARD runs now always invoke the driver and write `.step3.6-assessor.env` with `ASSESSOR_STATUS=skipped`; previously SIMPLE skipped without writing that file. That is an intentional contract extension and should not affect the WORSE gate (which requires `worse-majority` on HARD paths).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Non-HARD runs now always invoke the driver and write `.step3.6-assessor.env` with `ASSESSOR_STATUS=skipped`; previously SIMPLE skipped without writing that file. That is an intentional contract extension and should not affect the WORSE gate (which requires `worse-majority` on HARD paths).
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] The harness mirrors handoff well but does not cover the plan’s “catch-all” abort when the driver exits `1` (only exit `2` and empty-key cases). Worth adding later; not a production-path bug given the driver never exits `1`.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - The harness mirrors handoff well but does not cover the plan’s “catch-all” abort when the driver exits `1` (only exit `2` and empty-key cases). Worth adding later; not a production-path bug given the driver never exits `1`.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/design/scripts/test-design-plan-quality-assessor.sh:1120-1123
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required catch-all handoff abort (driver rc not in {0,2}) is not tested. Orchestrator SKILL.md adds a third abort guard for e.g. exit 1, but a future driver regression returning 1 could ship with only config-error and empty-key tests passing. Add apply_step3_6_handoff case with stub driver exit 1; assert handoff rc 1 and stderr contains design-plan-quality-assessor.sh failed (exit.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/design/scripts/test-design-plan-quality-assessor.sh:126-129
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No pause-checkpoint harness case despite _assessor_pause_checkpoint in driver and postplan sibling coverage. Breaking pause-before-assess ordering or ISSUE_NUMBER awk resolution would not fail CI until a manual /design pause. Mirror test-design-postplan-emit.sh pause case: .pause-requested, assert skipped result env and pause-save before snapshot/assess stubs.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/design/scripts/test-design-plan-quality-assessor.sh:218-222
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No test that stdout WARN replay is suppressed when file parse succeeds (_assessor_parse_ok=true). Regression could duplicate write-after or 0/3 warnings in chat while tests still pass file-parse visibility checks. Assert exactly one WARN line in chat.out on successful handoff; optional duplicate stdout WARN fixture.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/design/scripts/test-design-plan-quality-assessor.sh:1050-1068
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] apply_step3_6_handoff uses bare bash $SUBJECT, not qualified CLAUDE_PLUGIN_ROOT path from plan. Handoff mirror would not catch SKILL.md-style PATH/CWD invocation mistakes that structural tests target only in SKILL.md. Invoke via ${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-plan-quality-assessor.sh in handoff helper.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/design/scripts/test-design-plan-quality-assessor.sh:1042-1048
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] --timeout argv forwarding is undocumented by tests. Driver could stop passing --timeout to assess-plan-round.sh without failing make test-design-plan-quality-assessor. Assert CALL_LOG contains --timeout with default or overridden value.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: skills/design/scripts/design-plan-quality-assessor.sh:243-257
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] _assess_rc from assess-plan-round.sh is ignored; failures settle as skipped at driver exit 0. If assess-plan-round.sh ever exits non-zero without emitting KVs, /design continues past Step 3.6 instead of hitting the new catch-all abort. Document as intentional or propagate assess rc into driver/orchestrator failure handling plus harness case.
- **Suggested revision**: Address the concern above.

### FINDING_18: security: skills/design/scripts/design-plan-quality-assessor.sh:847-856
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Driver merges assess child stderr into KV parse via 2>&1; inline Step 3.6 captured stdout only. parse_kv_from_output overwrites keys so later stderr lines can spoof ASSESSOR_STATUS/ASSESSOR_VERDICT. Assess prints worse-majority on stdout then stderr emits ASSESSOR_VERDICT=skipped; orchestrator skips WORSE Continue/Stop and proceeds as if the quality gate passed. Capture assess (and snapshot) stdout only; log stderr separately. Do not feed stderr into routing KV parse unless it is a validated contract stream.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/design/scripts/design-plan-quality-assessor.sh:103-104
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] LARCH_SNAPSHOT_PLAN_ROUND_SH and LARCH_ASSESS_PLAN_ROUND_SH substitute child scripts without plugin-root validation. Inherited env in a /design session redirects the driver to an attacker-controlled script while still receiving --design-tmpdir and session paths. Restrict overrides to harness runs or validate resolved paths stay under CLAUDE_PLUGIN_ROOT before exec.
- **Suggested revision**: Address the concern above.

### FINDING_20: security: skills/design/scripts/design-plan-quality-assessor.sh:728-743
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] phase_driver_write_result_env persists parsed child values without newline rejection unlike emit_kv. Newline-bearing ASSESSOR_* values can split into extra lines in .step3.6-assessor.env and confuse the orchestrator line parser. Sanitize or reject newline/carriage-return in values before writing the result env; prefer writing only driver-controlled paths under DESIGN_TMPDIR.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] security: skills/design/scripts/assess-plan-round.sh:179
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Pre-existing LARCH_DISPATCH_PLAN_ASSESSORS_SH seam allows arbitrary dispatch script substitution. Same class as new driver seams; broader policy needed. Document and enforce a shared plugin-root allowlist for all LARCH_*_SH overrides repo-wide.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] risk-integration: skills/design/SKILL.md:1086-1088
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] WARN= replay from result env goes to chat without untrusted-data framing. Concurrent tmpdir tampering could inject operator-visible text; low likelihood in same-fence read. Optional untrusted wrapper for WARN replay or rely on atomic write + immediate read (current model).
- **Suggested revision**: Address the concern above.

### FINDING_23: architecture: skills/design/scripts/design-plan-quality-assessor.sh:118-144
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] On result-env write failure a previous .step3.6-assessor.env can remain while stdout carries fresh KVs. Stale ASSESSOR_VERDICT=worse-majority in the old file can win over stdout not-worse because _assessor_parse_ok blocks fill-only-unset merge and WORSE Continue/Stop may fire incorrectly. On write failure rm -f stale env (non-symlink) or skip file-read and force stdout fallback when phase_driver_write_result_env fails.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: skills/design/scripts/design-plan-quality-assessor.sh:167-177
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] read-cursor non-zero exit leaves ROUND_NUM=1 with no warning. HARD run with real cursor 2+ can run write-after for round 1 and corrupt round/snapshot state. Emit WARN and skip or abort write-after when read-cursor fails; do not default silently to 1.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: skills/design/scripts/design-plan-quality-assessor.sh:237-257
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Driver ignores assess-plan-round.sh exit code. Future non-zero assess exit with empty stdout would surface as ASSESSOR_STATUS=skipped and exit 0. Branch on _assess_rc; WARN plus distinct status or orchestrator-visible failure.
- **Suggested revision**: Address the concern above.

### FINDING_26: code-quality: skills/design/SKILL.md:1059-1063
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Step 3.6 fence does not pass documented --timeout to the driver. Long assessor runs cannot be tuned from the skill argv surface. Forward --timeout from env or argv if tunability is required.
- **Suggested revision**: Address the concern above.

### FINDING_27: code-quality: skills/design/scripts/test-design-plan-quality-assessor.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Missing tests for result-env write failure with stale file and pause checkpoint. Regression can reintroduce stale-env WORSE mis-routing or broken pause without CI signal. Add harness cases for failed env write plus pre-existing env and .pause-requested.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] architecture: skills/design/scripts/design-plan-quality-assessor.sh:216-220
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] write-after rollback decrements review-round-count but write-cursor uses ROUND_NUM. Pre-existing inline semantics; count/cursor mismatch may confuse rollback debugging. Document pairing in assessor.md if not intentional.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: skills/design/SKILL.md:1047-1058
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 3.6 fence omits timing-ledger mark required by plan and used by adjacent steps. /design runs lose per-step duration for Step 3.6 in timing reports while 3.5/3b still record marks; plan acceptance explicitly required timing mark in the fence. Add LARCH_TIMING_SKILL=design timing-ledger.sh mark "design Step 3.6 — assessor" after pause-check, before workflow_path pre-read.
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: skills/design/scripts/test-design-plan-quality-assessor.sh:164-182
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] apply_step3_6_handoff uses bash "$SUBJECT" instead of qualified ${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-plan-quality-assessor.sh path. Harness can pass while production SKILL.md fails if CLAUDE_PLUGIN_ROOT or cwd is wrong; structural pin on SKILL.md is not exercised by the mirror. Change handoff capture to use the qualified plugin path and assert the pattern in harness source.
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: skills/design/scripts/test-design-plan-quality-assessor.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] No test for handoff catch-all abort when driver exit is not 0 or 2. Regression could remove the third abort guard in SKILL.md without failing CI; orchestrator might continue with partial KVs after unexpected driver failure. Add stub driver exit 1 test asserting stderr banner and handoff exit 1.
- **Suggested revision**: Address the concern above.

### FINDING_32: **correctness** `skills/design/scripts/design-plan-quality-assessor.sh:118-143` — On `phase_driver_write_result_env` failure, `_write_result_and_emit` appends a “result env write failed; using stdout fallback” `WARN` and still `emit_kv`s the fresh contract to stdout, but it leaves any previous `.step3.6-assessor.env` in place. The Step 3.6 fence in `skills/design/SKILL.md:1074-1107` then file-first-parses that stale file, sets `_assessor_parse_ok=true` from old routing keys, and suppresses stdout `WARN=` replay when `_assessor_parse_ok` is true—so the write-failure warning never reaches chat and routing keys can be from an earlier round. Post-fence WORSE handling reads `.step3.6-assessor.env` from disk (`skills/design/SKILL.md:1123`), not the subshell variables populated from `_assessor_out`, so a stale `ASSESSOR_VERDICT=worse-majority` can mis-fire Continue/Stop. This is a regression vs the old inline `>` redirect, which always replaced the state file in the same invocation. **Suggested fix:** On failed `phase_driver_write_result_env`, `rm -f "$RESULT_ENV"` (or write an explicit tombstone) before emitting stdout KVs; and/or in the SKILL.md handoff, if stderr/stdout contains the write-failure `WARN`, force `_assessor_parse_ok=false` and ignore the existing env file so stdout merge and `WARN=` replay run.
- **Reviewer**: dyn-driver-protocol-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-plan-quality-assessor.sh:118-143` — On `phase_driver_write_result_env` failure, `_write_result_and_emit` appends a “result env write failed; using stdout fallback” `WARN` and still `emit_kv`s the fresh contract to stdout, but it leaves any previous `.step3.6-assessor.env` in place. The Step 3.6 fence in `skills/design/SKILL.md:1074-1107` then file-first-parses that stale file, sets `_assessor_parse_ok=true` from old routing keys, and suppresses stdout `WARN=` replay when `_assessor_parse_ok` is true—so the write-failure warning never reaches chat and routing keys can be from an earlier round. Post-fence WORSE handling reads `.step3.6-assessor.env` from disk (`skills/design/SKILL.md:1123`), not the subshell variables populated from `_assessor_out`, so a stale `ASSESSOR_VERDICT=worse-majority` can mis-fire Continue/Stop. This is a regression vs the old inline `>` redirect, which always replaced the state file in the same invocation. **Suggested fix:** On failed `phase_driver_write_result_env`, `rm -f "$RESULT_ENV"` (or write an explicit tombstone) before emitting stdout KVs; and/or in the SKILL.md handoff, if stderr/stdout contains the write-failure `WARN`, force `_assessor_parse_ok=false` and ignore the existing env file so stdout merge and `WARN=` replay run.
- **Suggested revision**: Address the concern above.

### FINDING_33: **correctness** `skills/design/SKILL.md:1059-1120` — The documented “stdout fallback” only merges `_assessor_out` inside the Bash subshell; contract KVs are never echoed to the tool-visible stdout stream (only skip/`🔶` banners and selected `WARN=` lines are). The prompt-side WORSE gate is defined to read `.step3.6-assessor.env` after the fence (`skills/design/SKILL.md:1123`), so orchestrator correctness depends on a successful result-env write, not on `$()` capture. The in-fence `rc=0 && -z ASSESSOR_STATUS` guard can pass when `_assessor_out` populated shell variables but the file is missing, giving a false “parsed OK” impression while the LLM has no durable contract. **Suggested fix:** Treat result-env presence after `rc=0` as mandatory for continuation (fail closed if the file is missing/unreadable after merge), or emit the seven routing KVs to stdout after a failed env write so the orchestrator can still recover without relying on a stale file.
- **Reviewer**: dyn-driver-protocol-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:1059-1120` — The documented “stdout fallback” only merges `_assessor_out` inside the Bash subshell; contract KVs are never echoed to the tool-visible stdout stream (only skip/`🔶` banners and selected `WARN=` lines are). The prompt-side WORSE gate is defined to read `.step3.6-assessor.env` after the fence (`skills/design/SKILL.md:1123`), so orchestrator correctness depends on a successful result-env write, not on `$()` capture. The in-fence `rc=0 && -z ASSESSOR_STATUS` guard can pass when `_assessor_out` populated shell variables but the file is missing, giving a false “parsed OK” impression while the LLM has no durable contract. **Suggested fix:** Treat result-env presence after `rc=0` as mandatory for continuation (fail closed if the file is missing/unreadable after merge), or emit the seven routing KVs to stdout after a failed env write so the orchestrator can still recover without relying on a stale file.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-driver-protocol-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-plan-quality-assessor.sh:216-219` — Write-after rollback sets `review-round-count.txt` to `ROUND_NUM-1` but calls `write-cursor --value "$ROUND_NUM"`; this matches the pre-extraction inline lane (behavior-preserving), but it may leave cursor vs count inconsistent if that prior behavior was already wrong.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-driver-protocol-output.txt
- **Concern**: - **architecture** `skills/design/scripts/design-plan-quality-assessor.sh:237-250` — `_assess_rc` is captured but never used; assess failures still settle via KV parse and `ASSESSOR_STATUS` defaults (same as the old inline path). Low risk while `assess-plan-round.sh` always exits `0` on settled paths.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-driver-protocol-output.txt
- **Concern**: - **correctness** (verification) — `_assessor_parse_ok` is set on any allowlisted routing key in the file-read loop; stdout merge uses fill-only-unset (`-z "${!_assessor_key:-}"`); abort order (rc=2 → rc=0 empty status → catch-all) matches Step 2b postplan shape; non-HARD shows one orchestrator skip breadcrumb then invokes the driver (no duplicate skip line); `emit_kv` under default quiet mode goes to FD3, which is wired into `$()` capture in a child driver process—harness uses `LARCH_QUIET_DISABLE=1`, but production capture path is sound when quiet init runs in the driver subprocess. **Branch commits:** `dbb253d81` (extract driver), `0eff34913` (larch-logs), `11a04f421` (relevant-checks fixes).
- **Suggested revision**: Address the concern above.

