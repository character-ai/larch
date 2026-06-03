# Review Round 1

- Mode: `diff`
- 13 accepted, 12 rejected (11 exonerated)

## Accepted Findings

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


### FINDING_2: code-quality: skills/design/scripts/test-design-plan-quality-assessor.sh:164-180
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] apply_step3_6_handoff does not use qualified CLAUDE_PLUGIN_ROOT path from plan/SKILL.md pins. Regression in PATH/CWD when invoking bare script path would not be caught by handoff mirror tests. Invoke "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-plan-quality-assessor.sh" in handoff; assert pattern in harness.
- **Suggested revision**: Address the concern above.


### FINDING_23: architecture: skills/design/scripts/design-plan-quality-assessor.sh:118-144
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] On result-env write failure a previous .step3.6-assessor.env can remain while stdout carries fresh KVs. Stale ASSESSOR_VERDICT=worse-majority in the old file can win over stdout not-worse because _assessor_parse_ok blocks fill-only-unset merge and WORSE Continue/Stop may fire incorrectly. On write failure rm -f stale env (non-symlink) or skip file-read and force stdout fallback when phase_driver_write_result_env fails.
- **Suggested revision**: Address the concern above.


### FINDING_27: code-quality: skills/design/scripts/test-design-plan-quality-assessor.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Missing tests for result-env write failure with stale file and pause checkpoint. Regression can reintroduce stale-env WORSE mis-routing or broken pause without CI signal. Add harness cases for failed env write plus pre-existing env and .pause-requested.
- **Suggested revision**: Address the concern above.


### FINDING_29: correctness: skills/design/SKILL.md:1047-1058
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 3.6 fence omits timing-ledger mark required by plan and used by adjacent steps. /design runs lose per-step duration for Step 3.6 in timing reports while 3.5/3b still record marks; plan acceptance explicitly required timing mark in the fence. Add LARCH_TIMING_SKILL=design timing-ledger.sh mark "design Step 3.6 — assessor" after pause-check, before workflow_path pre-read.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/design/scripts/test-design-plan-quality-assessor.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness omits catch-all handoff abort test for driver exit not in {0,2}. Third SKILL.md abort guard can drift without CI failure. Add stub driver exit 3; assert failed banner and handoff return 1.
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


### FINDING_6: code-quality: skills/design/SKILL.md:1047-1058
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] No timing-ledger mark for Step 3.6. HARD assessor duration missing from timing reports. Add timing-ledger mark consistent with Steps 3.5/3b.
- **Suggested revision**: Address the concern above.


