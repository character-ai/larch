### [rejected] FINDING_12

### FINDING_12: risk-integration: scripts/test-ship-pr.sh:1338-1380
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] OID-mismatch test duplicates rebump stub wiring next to _make_rebase_stubs instead of extending the shared helper (plan named _make_rebase_stubs). Future run_rebase_rebump dependency changes may be wired in one helper but not the OID case (or vice versa), weakening regression signal until a failure surfaces in CI. Extend _make_rebase_stubs (or a shared _ensure_rebump_deps) and call it from oid_mismatch_recoverable; optionally assert STALL_TRACKING=false / STALL_STEP cleared.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_2

### FINDING_2: architecture: scripts/test-ship-pr.sh:1338-1380
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Test setup diverges from plan text explicit ci-wait override and _make_rebase_stubs Plan listed dedicated ci-wait always-merge and _make_rebase_stubs; test uses default write_stubs ci-wait merge plus inline helper loop including refresh-run-logs.sh Document in test comment or align with _make_rebase_stubs pattern if maintainers want strict plan traceability
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_4

### FINDING_4: code-quality: scripts/test-ship-pr.sh:1361-1368
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New OID-mismatch test reimplements the stub loop from _make_rebase_stubs instead of composing that helper per implementation plan Helper list and chmod list can diverge from _make_rebase_stubs on future edits causing false test failures or missing coverage Call _make_rebase_stubs then overwrite ci-wait.sh and merge-pr.sh optionally extend _make_rebase_stubs to stub refresh-run-logs.sh for all rebump scenarios
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_5

### FINDING_5: code-quality: scripts/test-ship-pr.sh:1361-1379
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Regression test uses ad hoc stubs instead of _make_rebase_stubs per plan Stub surface may drift from other rebase tests if helpers change Align test with _make_rebase_stubs or shared stub builder
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_6

### FINDING_6: correctness: scripts/ship-pr.sh:1173-1208
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Helper placed before run_rebase_rebump not after Plan first option was after run_rebase_rebump; behavior unchanged Accept as-is alternate placement or move after function if style guide prefers plan order
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 NEUTRAL=1

