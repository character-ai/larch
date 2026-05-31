Verifying referenced locations so merged findings accurately reflect the code paths reviewers cited.
# Aggregated findings

### FINDING_1: Errexit-on-only leak test cannot detect unconditional `set -e`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The planned and harness-specified errexit-leak regression runs with errexit already enabled (`e` already in `$-`). Production `ship-pr.sh` deliberately avoids global `set -e` (baseline `set +e` at lines 4–7), while the defect is an unconditional `set -e` after a local `set +e` (e.g. at lines 1557/1567 and in the helper at 1045–1053). If errexit is on before the exercised path, both before- and after-call `$-` still contain `e`, so a missed unconditional `set -e` after restore still passes and the assertion cannot tell a bad force-enable from a correct restore.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Primary assertion: `set +e` before each toggle path, invoke the path, then assert `$-` does not contain `e`. Optional second case: `set -e` before call, assert `e` remains after restore
  - From Cursor-Innovation: Add an explicit `set +e` subtest (or snapshot `$-` before/after with pre-call `set +e`) so failure leaves `e` in `$-`; keep the errexit-on harness subtest separate

### FINDING_2: Leak regression does not exercise pr-prep outer `set +e` / `set -e` wrappers
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The regression test only drives `run_oos_disposition_gate_if_required_before_oos_pending_false` and does not exercise the `run_pr_prep_phase` outer `set +e` … `set -e` wrappers at `scripts/ship-pr.sh:1554–1567` that the plan also fixes. An implementer could fix the helper (lines 1045–1053) but leave unconditional `set -e` at 1557/1567; the new test would pass while errexit still leaks on the production pr-prep path before CI evaluation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Extend the leak assertion to cover pr-prep: minimal `write_state` + `IMPLEMENT_TMPDIR`/`STATE_FILE`, stub `oos-disposition-gate.sh`, invoke the same outer snapshot/`set +e`/gate/`gate_rc=$?`/conditional-restore sequence (or a thin wrapper mirroring 1554-1557), and assert `$-` is unchanged; keep the helper-only case as a second assertion
