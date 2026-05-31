### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:Testing strategy §1 (errexit leak assertion)
- **Concern**: Leak regression test is specified with errexit already on before the call. Scenario: The production bug is unconditional `set -e` after `set +e` while `ship-pr.sh` baseline is `set +e` (scripts/ship-pr.sh:4-7). With errexit already on, a post-call `$-` check cannot tell a bad force-enable from a correct restore; the buggy helper path still shows `e` in `$-`
- **Proposed resolution**: Primary assertion: `set +e` before each toggle path, invoke the path, then assert `$-` does not contain `e`. Optional second case: `set -e` before call, assert `e` remains after restore

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-ship-pr.sh:47-50
- **Concern**: Leak test only specifies errexit-on shell. Scenario: The bug force-enables errexit after script baseline `set +e`; with errexit already on, before/after `$-` both contain `e` and a missed unconditional `set -e` at scripts/ship-pr.sh:1557 or :1567 still passes
- **Proposed resolution**: Add an explicit `set +e` subtest (or snapshot `$-` before/after with pre-call `set +e`) so failure leaves `e` in `$-`; keep the errexit-on harness subtest separate

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:1554-1567
- **Concern**: Regression test only drives `run_oos_disposition_gate_if_required_before_oos_pending_false`; it does not exercise the `run_pr_prep_phase` outer `set +e` … `set -e` wrappers that the plan also fixes. Scenario: Implementer fixes the helper (lines 1045-1053) but leaves unconditional `set -e` at 1557/1567; the new test passes, but errexit still leaks on the production pr-prep path before CI evaluation
- **Proposed resolution**: Extend the leak assertion to cover pr-prep: minimal `write_state` + `IMPLEMENT_TMPDIR`/`STATE_FILE`, stub `oos-disposition-gate.sh`, invoke the same outer snapshot/`set +e`/gate/`gate_rc=$?`/conditional-restore sequence (or a thin wrapper mirroring 1554-1557), and assert `$-` is unchanged; keep the helper-only case as a second assertion
