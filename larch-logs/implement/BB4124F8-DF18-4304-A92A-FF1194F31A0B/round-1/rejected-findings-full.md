### [rejected] FINDING_1

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_1: correctness: skills/design/scripts/design-plan-quality-assessor.sh:237-257
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Driver ignores assess-plan-round.sh exit code and defaults to skipped on empty stdout. assess-plan-round.sh exits 2 after tmpdir validation failure; driver exits 0 with ASSESSOR_STATUS=skipped; /design continues past Step 3.6 without orchestrator catch-all abort (inline set -e would have aborted). Branch on _assess_rc after assess capture; fail closed or emit explicit degraded status; add harness with ASSESS_STUB_RC=2 and no KVs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: risk-integration: skills/design/scripts/test-design-plan-quality-assessor.sh:1042-1048
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] --timeout argv forwarding is undocumented by tests. Driver could stop passing --timeout to assess-plan-round.sh without failing make test-design-plan-quality-assessor. Assert CALL_LOG contains --timeout with default or overridden value.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: correctness: skills/design/scripts/design-plan-quality-assessor.sh:243-257
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] _assess_rc from assess-plan-round.sh is ignored; failures settle as skipped at driver exit 0. If assess-plan-round.sh ever exits non-zero without emitting KVs, /design continues past Step 3.6 instead of hitting the new catch-all abort. Document as intentional or propagate assess rc into driver/orchestrator failure handling plus harness case.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: security: skills/design/scripts/design-plan-quality-assessor.sh:847-856
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Driver merges assess child stderr into KV parse via 2>&1; inline Step 3.6 captured stdout only. parse_kv_from_output overwrites keys so later stderr lines can spoof ASSESSOR_STATUS/ASSESSOR_VERDICT. Assess prints worse-majority on stdout then stderr emits ASSESSOR_VERDICT=skipped; orchestrator skips WORSE Continue/Stop and proceeds as if the quality gate passed. Capture assess (and snapshot) stdout only; log stderr separately. Do not feed stderr into routing KV parse unless it is a validated contract stream.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: risk-integration: skills/design/scripts/design-plan-quality-assessor.sh:103-104
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] LARCH_SNAPSHOT_PLAN_ROUND_SH and LARCH_ASSESS_PLAN_ROUND_SH substitute child scripts without plugin-root validation. Inherited env in a /design session redirects the driver to an attacker-controlled script while still receiving --design-tmpdir and session paths. Restrict overrides to harness runs or validate resolved paths stay under CLAUDE_PLUGIN_ROOT before exec.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: security: skills/design/scripts/design-plan-quality-assessor.sh:728-743
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] phase_driver_write_result_env persists parsed child values without newline rejection unlike emit_kv. Newline-bearing ASSESSOR_* values can split into extra lines in .step3.6-assessor.env and confuse the orchestrator line parser. Sanitize or reject newline/carriage-return in values before writing the result env; prefer writing only driver-controlled paths under DESIGN_TMPDIR.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: correctness: skills/design/scripts/design-plan-quality-assessor.sh:167-177
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] read-cursor non-zero exit leaves ROUND_NUM=1 with no warning. HARD run with real cursor 2+ can run write-after for round 1 and corrupt round/snapshot state. Emit WARN and skip or abort write-after when read-cursor fails; do not default silently to 1.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: risk-integration: skills/design/scripts/design-plan-quality-assessor.sh:237-257
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Driver ignores assess-plan-round.sh exit code. Future non-zero assess exit with empty stdout would surface as ASSESSOR_STATUS=skipped and exit 0. Branch on _assess_rc; WARN plus distinct status or orchestrator-visible failure.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: code-quality: skills/design/SKILL.md:1059-1063
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Step 3.6 fence does not pass documented --timeout to the driver. Long assessor runs cannot be tuned from the skill argv surface. Forward --timeout from env or argv if tunability is required.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_33

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_33: **correctness** `skills/design/SKILL.md:1059-1120` — The documented “stdout fallback” only merges `_assessor_out` inside the Bash subshell; contract KVs are never echoed to the tool-visible stdout stream (only skip/`🔶` banners and selected `WARN=` lines are). The prompt-side WORSE gate is defined to read `.step3.6-assessor.env` after the fence (`skills/design/SKILL.md:1123`), so orchestrator correctness depends on a successful result-env write, not on `$()` capture. The in-fence `rc=0 && -z ASSESSOR_STATUS` guard can pass when `_assessor_out` populated shell variables but the file is missing, giving a false “parsed OK” impression while the LLM has no durable contract. **Suggested fix:** Treat result-env presence after `rc=0` as mandatory for continuation (fail closed if the file is missing/unreadable after merge), or emit the seven routing KVs to stdout after a failed env write so the orchestrator can still recover without relying on a stale file.
- **Reviewer**: dyn-driver-protocol-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:1059-1120` — The documented “stdout fallback” only merges `_assessor_out` inside the Bash subshell; contract KVs are never echoed to the tool-visible stdout stream (only skip/`🔶` banners and selected `WARN=` lines are). The prompt-side WORSE gate is defined to read `.step3.6-assessor.env` after the fence (`skills/design/SKILL.md:1123`), so orchestrator correctness depends on a successful result-env write, not on `$()` capture. The in-fence `rc=0 && -z ASSESSOR_STATUS` guard can pass when `_assessor_out` populated shell variables but the file is missing, giving a false “parsed OK” impression while the LLM has no durable contract. **Suggested fix:** Treat result-env presence after `rc=0` as mandatory for continuation (fail closed if the file is missing/unreadable after merge), or emit the seven routing KVs to stdout after a failed env write so the orchestrator can still recover without relying on a stale file.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: correctness: skills/design/SKILL.md:1082-1084
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] _assessor_parse_ok set on any routing key not ASSESSOR_STATUS. Partial env file could suppress stdout WARN replay while ASSESSOR_STATUS stays empty until later guard. Set parse ok only when ASSESSOR_STATUS read from file succeeds.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: skills/design/scripts/design-plan-quality-assessor.sh:38-61
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated json_scalar_or_sed/parse_kv helpers vs design-postplan-emit.sh. Future KV/workflow_path parsing fixes must be duplicated. Extract shared helpers to lib-phase-driver if touching drivers anyway.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

