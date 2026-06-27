### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/implement_dispatch.py
- **Concern**: [SCOPE-REDUCTION] Reimplementing `run_gate` in Python duplicates `step-18.sh` stall-layer logic. Scenario: The plan adds `_stall_layer_active`, `_resolve_stall_memory_layer`, and file readers in `implement_dispatch.py` to mirror `step-18.sh:108-167`. That is the largest new complexity block and the accepted parity-risk surface (memory `case` binding, OR-of-four-layers). Any drift spuriously routes `NEXT_ACTION=stall-recovery` or runs green-path finalize while a stall layer is active.
- **Proposed resolution**: Inside `step_18_gate_finalize_main()`, subprocess `bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-18.sh --phase gate --stall-tracking-memory …`, parse `STALL_RECOVERY_REQUIRED` and `STALL_TRACKING_*` from that capture, then branch. Keep only `normalize-outcome`, escalation-evidence checks, and finalize chaining in Python; document any new subprocess sites for the ratchet.
