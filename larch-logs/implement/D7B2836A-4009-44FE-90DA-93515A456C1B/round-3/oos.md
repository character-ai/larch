### FINDING_18: [OUT_OF_SCOPE] risk-integration: scripts/test-design-structure.md:3831-3833
[nit] Harness doc omits assert_postplan_thin_fence coverage. Contributors may not know postplan thin-fence pins exist or lack self-tests. Document assert_postplan_thin_fence and planned negative fixtures in test-design-structure.md.

### FINDING_30: [OUT_OF_SCOPE] `scripts/test-design-structure.sh` adds `assert_postplan_thin_fence` for Step 2b and pins rc0 `step-2b.5`, but the plan’s broader sentinel pins (initial rc12 Split entry `step-2b`, Refine/no-split Continue pairs, Gate B Override, decompose-panel §6 Continue, Step 1e rc12/13) are not structurally enforced—only dispatch anchors in decompose-panel are checked (~lines 1262-1267). Regression risk for the gaps above remains prompt-side only.
- `scripts/test-design-structure.sh` adds `assert_postplan_thin_fence` for Step 2b and pins rc0 `step-2b.5`, but the plan’s broader sentinel pins (initial rc12 Split entry `step-2b`, Refine/no-split Continue pairs, Gate B Override, decompose-panel §6 Continue, Step 1e rc12/13) are not structurally enforced—only dispatch anchors in decompose-panel are checked (~lines 1262-1267). Regression risk for the gaps above remains prompt-side only.

### FINDING_31: [OUT_OF_SCOPE] Initial Step 2b’s inline bash fence correctly writes both sentinels on rc0 and `step-2b` on rc12/rc13 before Split; rc10 Fix-and-retry and rc11 pause-save paths look consistent with the thin-fence contract.
- Initial Step 2b’s inline bash fence correctly writes both sentinels on rc0 and `step-2b` on rc12/rc13 before Split; rc10 Fix-and-retry and rc11 pause-save paths look consistent with the thin-fence contract.

### FINDING_36: [OUT_OF_SCOPE] **Correct core split:** Legacy `_postplan_write_result_and_emit` still mirrors contract KVs to FD 3 via `emit_kv`; merged `_postplan_write_result_merged` does not call `emit_kv`, fails closed on result-env write failure without stdout-KV fallback (D26), captures nested `check-plan-size.sh` stdout only for internal `parse_kv_from_output`, routes stderr to a sidecar on nonzero plan-size exits, and suppresses `append-tool-failure.sh` helper KVs (D22, D27).
- **Correct core split:** Legacy `_postplan_write_result_and_emit` still mirrors contract KVs to FD 3 via `emit_kv`; merged `_postplan_write_result_merged` does not call `emit_kv`, fails closed on result-env write failure without stdout-KV fallback (D26), captures nested `check-plan-size.sh` stdout only for internal `parse_kv_from_output`, routes stderr to a sidecar on nonzero plan-size exits, and suppresses `append-tool-failure.sh` helper KVs (D22, D27).

### FINDING_37: [OUT_OF_SCOPE] **Thin-fence hygiene:** `SKILL.md` Step 2b drops the old stdout-KV merge / symlink “stdout fallback” block; `assert_postplan_thin_fence` forbids `<<<"${_postplan_out:-}"` heredoc parsing; orchestrator uses allowlisted line reads, not `source`.
- **Thin-fence hygiene:** `SKILL.md` Step 2b drops the old stdout-KV merge / symlink “stdout fallback” block; `assert_postplan_thin_fence` forbids `<<<"${_postplan_out:-}"` heredoc parsing; orchestrator uses allowlisted line reads, not `source`.

### FINDING_38: [OUT_OF_SCOPE] **Harness gap vs plan:** Structure pins do not yet enforce the full “no contract keys on merged stdout” set promised in the plan (only `POSTPLAN_EMIT_STATUS=` / `WARN=`).
- **Harness gap vs plan:** Structure pins do not yet enforce the full “no contract keys on merged stdout” set promised in the plan (only `POSTPLAN_EMIT_STATUS=` / `WARN=`).

