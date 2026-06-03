### FINDING_1: code-quality: skills/design/scripts/design-plan-quality-assessor.sh:38-51
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] json_scalar_or_sed and workflow_path resolution are duplicated in design-postplan-emit.sh assess-plan-round.sh SKILL.md Step 3.6 fence and test apply_step3_6_handoff A future run-params field or merge rule change updates one copy and leaves others stale causing wrong HARD/SIMPLE gating or mismatched breadcrumbs Extract shared lib-run-params-scalar.sh (or similar) with json_scalar_or_sed and resolve_design_workflow_path; source from all phase drivers and assess-plan-round.sh
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/SKILL.md:1055-1077
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Orchestrator re-implements full workflow_path and design_classification merge then invokes driver that repeats the same logic Every SIMPLE run pays double jq/sed work; silent orchestrator alignment vs driver WARN on conflict can confuse operators who only read the skip line Share one resolver helper; keep SKILL pre-read minimal (banner only) or derive breadcrumb from driver WORKFLOW_PATH KV after invoke
- **Suggested revision**: Address the concern above.

### FINDING_3: architecture: skills/design/scripts/test-design-plan-quality-assessor.sh:180-274
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] apply_step3_6_handoff duplicates the full Step 3.6 handoff fence for regression parity Handoff contract changes require editing SKILL.md and ~95 lines of harness code in lockstep Factor handoff into a sourced script or strengthen structural pins on the full fence block
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: skills/design/scripts/design-plan-quality-assessor.md:36
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Responsibility bullet 7 documents rollback order opposite to implementation. Future edits may reorder rollback and break harness expectations (count 1, cursor 2 after round-2 write-after failure). Update item 7 to: decrement review-round-count.txt then best-effort write-cursor --value ROUND_NUM.
- **Suggested revision**: Address the concern above.

### FINDING_5: risk-integration: skills/design/scripts/test-assess-plan-round.sh:16-19
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] assess-plan-round.sh gained resolve_workflow_path() but its harness still only sets workflow_path. Empty or mismatched run-params can change skip vs HARD assess behavior without any failing test in make test-assess-plan-round. Add harness cases for design_classification-only HARD and workflow_path vs design_classification conflict; assert ASSESSOR_STATUS/VERDICT.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: skills/design/scripts/test-design-plan-quality-assessor.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No test for workflow_path vs design_classification mismatch WARN and chat replay. Operator-visible disagreement breadcrumb could regress while driver still runs HARD lane. Add run-params conflict fixture; assert WARN in result env and apply_step3_6_handoff chat.out.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: skills/design/scripts/design-plan-quality-assessor.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] --timeout forwarding is documented but not asserted in the offline harness. Timeout argv could break silently while tests stay green. Stub-log --timeout and add one driver invocation with non-default timeout.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: skills/design/scripts/test-design-plan-quality-assessor.sh:557-593
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Immutable env tests hard-fail when chflags/chattr unavailable. Linux CI may report harness failure unrelated to product logic. Skip with explicit pass or use a portable write-failure injection.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: skills/design/scripts/test-design-plan-quality-assessor.sh:202-203
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] HARD step-start banner ordering is not explicitly asserted. Deferred post-driver banner could reappear without failing CI. Assert first chat.out line or banner-before-WARN ordering on HARD handoff.
- **Suggested revision**: Address the concern above.

### FINDING_10: **Symlink refusal** on `.step3.6-assessor.env` (driver write + orchestrator read), matching Step 2b postplan parity
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Symlink refusal** on `.step3.6-assessor.env` (driver write + orchestrator read), matching Step 2b postplan parity
- **Suggested revision**: Address the concern above.

### FINDING_11: **Atomic result-env write** via `phase_driver_write_result_env`
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Atomic result-env write** via `phase_driver_write_result_env`
- **Suggested revision**: Address the concern above.

### FINDING_12: **`_assessor_force_stdout`** when env write fails, preventing stale file poisoning
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`_assessor_force_stdout`** when env write fails, preventing stale file poisoning
- **Suggested revision**: Address the concern above.

### FINDING_13: **Fail-closed abort** on driver config error / empty mandatory keys
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Fail-closed abort** on driver config error / empty mandatory keys
- **Suggested revision**: Address the concern above.

### FINDING_14: **Pause checkpoint** resolves `ISSUE_NUMBER` via awk on `source-env.sh` instead of `source` (same pattern as `design-postplan-emit.sh`)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Pause checkpoint** resolves `ISSUE_NUMBER` via awk on `source-env.sh` instead of `source` (same pattern as `design-postplan-emit.sh`)
- **Suggested revision**: Address the concern above.

### FINDING_15: **Child calls quoted** (`"$SNAPSHOT_SH"`, `"$ASSESS_SH"`); no `eval`
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Child calls quoted** (`"$SNAPSHOT_SH"`, `"$ASSESS_SH"`); no `eval`
- **Suggested revision**: Address the concern above.

### FINDING_16: **Allowlisted `printf -v`** keys in the orchestrator handoff; `WARN` lines printed, not dynamically assigned
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Allowlisted `printf -v`** keys in the orchestrator handoff; `WARN` lines printed, not dynamically assigned
- **Suggested revision**: Address the concern above.

### FINDING_17: **Failure captures** go through `append-tool-failure.sh --redact`
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Failure captures** go through `append-tool-failure.sh --redact`
- **Suggested revision**: Address the concern above.

### FINDING_18: **`LARCH_*_SH` overrides** are an intentional hermetic-test seam already used in `assess-plan-round.sh`; execution remains quoted, not interpolated
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`LARCH_*_SH` overrides** are an intentional hermetic-test seam already used in `assess-plan-round.sh`; execution remains quoted, not interpolated Untrusted external assessor content (qualifications, verdict prose) still reaches the LLM only through the existing WORSE gate, which SKILL.md explicitly marks as untrusted data — unchanged by this extraction. The new WARN replay path does not widen that surface beyond what the prior inline Step 3.6 block already printed.
- **Suggested revision**: Address the concern above.

### FINDING_19: architecture: skills/design/scripts/design-plan-quality-assessor.md:36
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Responsibility text documents rollback order and no-decrement-on-write-cursor-failure that contradict implementation and test 21. Operators or future edits may "fix" rollback to match the doc and break harness/test-run-step3-review round-count semantics. Update item 7 to decrement-then-write-cursor; document WARN-on-write-cursor-fail without count restore.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/design/scripts/design-plan-quality-assessor.sh:310-314
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Exit-0 assess path defaults empty KVs to skipped rather than assess-failed. Truncated or buggy assess stdout after successful write-after proceeds with no quality gate and no execution-issues capture. Fail closed when ASSESSOR_STATUS is empty after assess rc=0; log capture and set assess-failed.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/design/SKILL.md:1100-1102
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] _assessor_parse_ok flips true on any routing key not ASSESSOR_STATUS. Partial corrupt .step3.6-assessor.env can suppress stdout WARN replay while mandatory-key guard still aborts late. Set parse_ok only when ASSESSOR_STATUS is populated from file or treat partial parse as stdout fallback.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: skills/design/SKILL.md:1089-090
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Stale-env detection uses prose substring grep on captured output. Benign log line containing the same sentence forces stdout fallback and ignores a valid result env. Key off a dedicated emit_kv token instead of grep on warning text.
- **Suggested revision**: Address the concern above.

### FINDING_23: architecture: skills/design/scripts/design-plan-quality-assessor.sh:75-81
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --timeout is accepted but only forwarded to assess-plan-round.sh. Snapshot hangs are not bounded by the documented driver timeout flag. Document assess-only timeout or propagate timeout to snapshot children if supported.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: skills/design/scripts/test-design-plan-quality-assessor.sh:615-625
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness lacks handoff chat assertion for read-cursor failure WARN. File-parse WARN replay for read-cursor could regress without failing CI. Add apply_step3_6_handoff case asserting read-cursor WARN in chat.out.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: skills/design/SKILL.md:1055-1067
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Orchestrator pre-read aligns workflow_path to design_classification when they disagree; plan required same-as-inline workflow_path pre-read and behavior preservation. Stale run-params with workflow_path=SIMPLE and design_classification=HARD previously skipped Step 3.6; now prints HARD banner and runs snapshot/assessor work. Remove _dc override from orchestrator pre-read or amend plan and add harness coverage for disagreeing fields.
- **Suggested revision**: Address the concern above.

### FINDING_26: **correctness** `skills/design/scripts/design-plan-quality-assessor.sh:197-210,237-250,286-300` — On the degraded paths that must always settle at exit `0` (`read-cursor` logging, `write-after-failed`, and `assess-failed`), housekeeping steps (`mktemp`, `printf` into the temp capture file, `rm -f "$_cap"`, and `printf` into `review-round-count.txt`) run under the script-wide `set -euo pipefail` without a local `set +e` guard. Any of those failing aborts the driver before `_write_result_and_emit`, producing exit `1` instead of the contracted settled `0`, leaving no `.step3.6-assessor.env`, and forcing the Step 3.6 orchestrator down the mandatory-keys / catch-all abort paths. The removed inline `SKILL.md` lane did not run under `set -e`, so this is a regression on failure of ancillary I/O. **Suggested fix:** Wrap each degrade block’s non-contract housekeeping (`mktemp`, cap write, `rm`, count-file write) in `set +e` … `set -e` the same way child script calls are wrapped, or funnel it through a small helper that never aborts; guarantee `_write_result_and_emit` runs on every branch that sets `ASSESSOR_STATUS` to `write-after-failed`, `assess-failed`, or skip variants before `exit 0`.
- **Reviewer**: dyn-shell-set-e-invariants-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-plan-quality-assessor.sh:197-210,237-250,286-300` — On the degraded paths that must always settle at exit `0` (`read-cursor` logging, `write-after-failed`, and `assess-failed`), housekeeping steps (`mktemp`, `printf` into the temp capture file, `rm -f "$_cap"`, and `printf` into `review-round-count.txt`) run under the script-wide `set -euo pipefail` without a local `set +e` guard. Any of those failing aborts the driver before `_write_result_and_emit`, producing exit `1` instead of the contracted settled `0`, leaving no `.step3.6-assessor.env`, and forcing the Step 3.6 orchestrator down the mandatory-keys / catch-all abort paths. The removed inline `SKILL.md` lane did not run under `set -e`, so this is a regression on failure of ancillary I/O. **Suggested fix:** Wrap each degrade block’s non-contract housekeeping (`mktemp`, cap write, `rm`, count-file write) in `set +e` … `set -e` the same way child script calls are wrapped, or funnel it through a small helper that never aborts; guarantee `_write_result_and_emit` runs on every branch that sets `ASSESSOR_STATUS` to `write-after-failed`, `assess-failed`, or skip variants before `exit 0`.
- **Suggested revision**: Address the concern above.

### FINDING_27: **correctness** `skills/design/scripts/design-plan-quality-assessor.sh:160-162` — `_write_result_and_emit` calls `emit_kv WARN "$_warn"` under `set -e` with no local errexit suppression. `emit_kv` returns `2` when a value contains embedded newline/CR (`scripts/lib-quiet.sh:166-172`), which would terminate the driver mid-emit (partial stdout, no guaranteed result-env write) even on otherwise-successful assessor paths. **Suggested fix:** Wrap the WARN emit loop in `set +e` and treat a non-zero `emit_kv` rc as a degrade (append a single safe fallback `WARN=` or omit the offending line), then continue emitting the routing KVs and complete the function; alternatively sanitize/strip newlines from WARN text before emit.
- **Reviewer**: dyn-shell-set-e-invariants-output.txt
- **Concern**: - **correctness** `skills/design/scripts/design-plan-quality-assessor.sh:160-162` — `_write_result_and_emit` calls `emit_kv WARN "$_warn"` under `set -e` with no local errexit suppression. `emit_kv` returns `2` when a value contains embedded newline/CR (`scripts/lib-quiet.sh:166-172`), which would terminate the driver mid-emit (partial stdout, no guaranteed result-env write) even on otherwise-successful assessor paths. **Suggested fix:** Wrap the WARN emit loop in `set +e` and treat a non-zero `emit_kv` rc as a degrade (append a single safe fallback `WARN=` or omit the offending line), then continue emitting the routing KVs and complete the function; alternatively sanitize/strip newlines from WARN text before emit.
- **Suggested revision**: Address the concern above.

### FINDING_28: **correctness** `skills/design/scripts/test-design-plan-quality-assessor.sh:207-273` — `apply_step3_6_handoff` turns errexit off with `set +e` for driver capture but never restores `set -e` before `return`. Because `set +/-e` is shell-global, callers that invoke the mirror without their own trailing `set -e` (or that add assertions after the call inside the same subshell) run subsequent checks with errexit disabled, weakening fail-closed coverage of the handoff abort guards the harness is meant to pin. **Suggested fix:** Add `set -e` immediately before each `return` in `apply_step3_6_handoff` (after the abort checks, which intentionally need `set +e` or explicit rc tests), matching the `SKILL.md` fence pattern at `skills/design/SKILL.md:1073-1079`.
- **Reviewer**: dyn-shell-set-e-invariants-output.txt
- **Concern**: - **correctness** `skills/design/scripts/test-design-plan-quality-assessor.sh:207-273` — `apply_step3_6_handoff` turns errexit off with `set +e` for driver capture but never restores `set -e` before `return`. Because `set +/-e` is shell-global, callers that invoke the mirror without their own trailing `set -e` (or that add assertions after the call inside the same subshell) run subsequent checks with errexit disabled, weakening fail-closed coverage of the handoff abort guards the harness is meant to pin. **Suggested fix:** Add `set -e` immediately before each `return` in `apply_step3_6_handoff` (after the abort checks, which intentionally need `set +e` or explicit rc tests), matching the `SKILL.md` fence pattern at `skills/design/SKILL.md:1073-1079`.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-shell-set-e-invariants-output.txt
- **Concern**: - **correctness** — The Step 3.6 `SKILL.md` fence correctly pairs `set +e` driver capture with `set -e` restoration before parse/abort (`skills/design/SKILL.md:1073-1140`); no defect found there relative to the scout checklist.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-shell-set-e-invariants-output.txt
- **Concern**: - **correctness** — Every wrapped `"$SNAPSHOT_SH"` / `"$ASSESS_SH"` / `append-tool-failure.sh` block in the driver captures rc before restoring `set -e` and reaches `_write_result_and_emit` on the intended settle paths when housekeeping above does not fail; child-call invariants match the `design-postplan-emit.sh` pattern.
- **Suggested revision**: Address the concern above.

### FINDING_31: **correctness** `skills/design/scripts/test-assess-plan-round.sh:16-56` — The branch replaces `read_workflow_path` with `resolve_workflow_path` in `assess-plan-round.sh` (empty/missing `workflow_path` falls back to `design_classification`, mismatch aligns to `design_classification`), but this harness still only writes `workflow_path` via `write_params` and never references `design_classification`. `make test-assess-plan-round` therefore cannot catch drift between `assess-plan-round.sh` and `design-plan-quality-assessor.sh` on those branches when `assess-plan-round.sh` is exercised directly. **Suggested fix:** Add cases analogous to `test-design-plan-quality-assessor.sh` #19 (only `{"design_classification":"HARD"}`) and a mismatch fixture (`workflow_path` vs `design_classification`), asserting resolved HARD vs skipped behavior and emitted KVs.
- **Reviewer**: dyn-assess-round-regression-output.txt
- **Concern**: - **correctness** `skills/design/scripts/test-assess-plan-round.sh:16-56` — The branch replaces `read_workflow_path` with `resolve_workflow_path` in `assess-plan-round.sh` (empty/missing `workflow_path` falls back to `design_classification`, mismatch aligns to `design_classification`), but this harness still only writes `workflow_path` via `write_params` and never references `design_classification`. `make test-assess-plan-round` therefore cannot catch drift between `assess-plan-round.sh` and `design-plan-quality-assessor.sh` on those branches when `assess-plan-round.sh` is exercised directly. **Suggested fix:** Add cases analogous to `test-design-plan-quality-assessor.sh` #19 (only `{"design_classification":"HARD"}`) and a mismatch fixture (`workflow_path` vs `design_classification`), asserting resolved HARD vs skipped behavior and emitted KVs.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] No remaining `read_workflow_path` references in executable code (grep only hits historical `larch-logs/` review artifacts).
- **Reviewer**: dyn-assess-round-regression-output.txt
- **Concern**: - No remaining `read_workflow_path` references in executable code (grep only hits historical `larch-logs/` review artifacts).
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] `resolve_workflow_path` in `skills/design/scripts/assess-plan-round.sh:38-56`, the pre-invoke block in `skills/design/SKILL.md:1051-1067`, and `skills/design/scripts/design-plan-quality-assessor.sh:108-125` use the same resolution rules (empty `workflow_path` → `HARD` only when `design_classification` is exactly `HARD`, else `SIMPLE`; when both are non-empty and differ, follow `design_classification`). The driver additionally emits a `WARN=` on mismatch; the orchestrator pre-read aligns silently, which is consistent because the driver warning is replayed via the handoff parse.
- **Reviewer**: dyn-assess-round-regression-output.txt
- **Concern**: - `resolve_workflow_path` in `skills/design/scripts/assess-plan-round.sh:38-56`, the pre-invoke block in `skills/design/SKILL.md:1051-1067`, and `skills/design/scripts/design-plan-quality-assessor.sh:108-125` use the same resolution rules (empty `workflow_path` → `HARD` only when `design_classification` is exactly `HARD`, else `SIMPLE`; when both are non-empty and differ, follow `design_classification`). The driver additionally emits a `WARN=` on mismatch; the orchestrator pre-read aligns silently, which is consistent because the driver warning is replayed via the handoff parse.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] `json_scalar_or_sed` is duplicated in `assess-plan-round.sh`, `design-plan-quality-assessor.sh`, and `design-postplan-emit.sh` with the same jq → sed → default behavior; command substitution strips trailing newlines, so `[[ … == HARD ]]` / `!= HARD` gates are not broken by `printf '%s\n'`.
- **Reviewer**: dyn-assess-round-regression-output.txt
- **Concern**: - `json_scalar_or_sed` is duplicated in `assess-plan-round.sh`, `design-plan-quality-assessor.sh`, and `design-postplan-emit.sh` with the same jq → sed → default behavior; command substitution strips trailing newlines, so `[[ … == HARD ]]` / `!= HARD` gates are not broken by `printf '%s\n'`.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] Intentional behavior change (not a regression on normal runs): `design-init-runparams.sh` always writes both fields, but `run-params.json` with only `design_classification":"HARD"` now enters the HARD assessor lane; covered at the driver layer in `test-design-plan-quality-assessor.sh` #19, not in `test-assess-plan-round.sh`.
- **Reviewer**: dyn-assess-round-regression-output.txt
- **Concern**: - Intentional behavior change (not a regression on normal runs): `design-init-runparams.sh` always writes both fields, but `run-params.json` with only `design_classification":"HARD"` now enters the HARD assessor lane; covered at the driver layer in `test-design-plan-quality-assessor.sh` #19, not in `test-assess-plan-round.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] `skills/design/scripts/assess-plan-round.md:7` still describes only `workflow_path` gating and does not document the `design_classification` fallback added in this branch (doc drift only).
- **Reviewer**: dyn-assess-round-regression-output.txt
- **Concern**: - `skills/design/scripts/assess-plan-round.md:7` still describes only `workflow_path` gating and does not document the `design_classification` fallback added in this branch (doc drift only).
- **Suggested revision**: Address the concern above.

