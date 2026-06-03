### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: skills/design/scripts/design-plan-quality-assessor.sh:38-51
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] json_scalar_or_sed and workflow_path resolution are duplicated in design-postplan-emit.sh assess-plan-round.sh SKILL.md Step 3.6 fence and test apply_step3_6_handoff A future run-params field or merge rule change updates one copy and leaves others stale causing wrong HARD/SIMPLE gating or mismatched breadcrumbs Extract shared lib-run-params-scalar.sh (or similar) with json_scalar_or_sed and resolve_design_workflow_path; source from all phase drivers and assess-plan-round.sh
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: **Symlink refusal** on `.step3.6-assessor.env` (driver write + orchestrator read), matching Step 2b postplan parity
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Symlink refusal** on `.step3.6-assessor.env` (driver write + orchestrator read), matching Step 2b postplan parity
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: **Atomic result-env write** via `phase_driver_write_result_env`
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Atomic result-env write** via `phase_driver_write_result_env`
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: **`_assessor_force_stdout`** when env write fails, preventing stale file poisoning
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`_assessor_force_stdout`** when env write fails, preventing stale file poisoning
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: **Fail-closed abort** on driver config error / empty mandatory keys
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Fail-closed abort** on driver config error / empty mandatory keys
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: **Pause checkpoint** resolves `ISSUE_NUMBER` via awk on `source-env.sh` instead of `source` (same pattern as `design-postplan-emit.sh`)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Pause checkpoint** resolves `ISSUE_NUMBER` via awk on `source-env.sh` instead of `source` (same pattern as `design-postplan-emit.sh`)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: **Child calls quoted** (`"$SNAPSHOT_SH"`, `"$ASSESS_SH"`); no `eval`
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Child calls quoted** (`"$SNAPSHOT_SH"`, `"$ASSESS_SH"`); no `eval`
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: **Allowlisted `printf -v`** keys in the orchestrator handoff; `WARN` lines printed, not dynamically assigned
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Allowlisted `printf -v`** keys in the orchestrator handoff; `WARN` lines printed, not dynamically assigned
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: **Failure captures** go through `append-tool-failure.sh --redact`
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Failure captures** go through `append-tool-failure.sh --redact`
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: **`LARCH_*_SH` overrides** are an intentional hermetic-test seam already used in `assess-plan-round.sh`; execution remains quoted, not interpolated
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`LARCH_*_SH` overrides** are an intentional hermetic-test seam already used in `assess-plan-round.sh`; execution remains quoted, not interpolated Untrusted external assessor content (qualifications, verdict prose) still reaches the LLM only through the existing WORSE gate, which SKILL.md explicitly marks as untrusted data — unchanged by this extraction. The new WARN replay path does not widen that surface beyond what the prior inline Step 3.6 block already printed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/design/SKILL.md:1055-1077
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Orchestrator re-implements full workflow_path and design_classification merge then invokes driver that repeats the same logic Every SIMPLE run pays double jq/sed work; silent orchestrator alignment vs driver WARN on conflict can confuse operators who only read the skip line Share one resolver helper; keep SKILL pre-read minimal (banner only) or derive breadcrumb from driver WORKFLOW_PATH KV after invoke
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: risk-integration: skills/design/SKILL.md:1089-090
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Stale-env detection uses prose substring grep on captured output. Benign log line containing the same sentence forces stdout fallback and ignores a valid result env. Key off a dedicated emit_kv token instead of grep on warning text.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: architecture: skills/design/scripts/design-plan-quality-assessor.sh:75-81
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --timeout is accepted but only forwarded to assess-plan-round.sh. Snapshot hangs are not bounded by the documented driver timeout flag. Document assess-only timeout or propagate timeout to snapshot children if supported.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: **correctness** `skills/design/scripts/design-plan-quality-assessor.sh:160-162` — `_write_result_and_emit` calls `emit_kv WARN "$_warn"` under `set -e` with no local errexit suppression. `emit_kv` returns `2` when a value contains embedded newline/CR (`scripts/lib-quiet.sh:166-172`), which would terminate the driver mid-emit (partial stdout, no guaranteed result-env write) even on otherwise-successful assessor paths. **Suggested fix:** Wrap the WARN emit loop in `set +e` and treat a non-zero `emit_kv` rc as a degrade (append a single safe fallback `WARN=` or omit the offending line), then continue emitting the routing KVs and complete the function; alternatively sanitize/strip newlines from WARN text before emit.
- **Reviewer**: dyn-shell-set-e-invariants-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-plan-quality-assessor.sh:160-162` — `_write_result_and_emit` calls `emit_kv WARN "$_warn"` under `set -e` with no local errexit suppression. `emit_kv` returns `2` when a value contains embedded newline/CR (`scripts/lib-quiet.sh:166-172`), which would terminate the driver mid-emit (partial stdout, no guaranteed result-env write) even on otherwise-successful assessor paths. **Suggested fix:** Wrap the WARN emit loop in `set +e` and treat a non-zero `emit_kv` rc as a degrade (append a single safe fallback `WARN=` or omit the offending line), then continue emitting the routing KVs and complete the function; alternatively sanitize/strip newlines from WARN text before emit.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: architecture: skills/design/scripts/test-design-plan-quality-assessor.sh:180-274
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] apply_step3_6_handoff duplicates the full Step 3.6 handoff fence for regression parity Handoff contract changes require editing SKILL.md and ~95 lines of harness code in lockstep Factor handoff into a sourced script or strengthen structural pins on the full fence block
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: risk-integration: skills/design/scripts/design-plan-quality-assessor.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] --timeout forwarding is documented but not asserted in the offline harness. Timeout argv could break silently while tests stay green. Stub-log --timeout and add one driver invocation with non-default timeout.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: risk-integration: skills/design/scripts/test-design-plan-quality-assessor.sh:202-203
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] HARD step-start banner ordering is not explicitly asserted. Deferred post-driver banner could reappear without failing CI. Assert first chat.out line or banner-before-WARN ordering on HARD handoff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

