## Plan

Port completion plan for G7: keep the existing native `python/stall_recovery.py` report composer, close path and parity gaps identified by review (generic-profile classify branch, record_attempt append parity), cut remaining bash consumers to `python/cli.py stall-recovery`, move the report contract files into `python/`, retire the shell harnesses into pytest, and delete the old bash report body.

See `$DESIGN_TMPDIR/plan.txt` for the full implementation plan.

## Acceptance

- `stall-recovery-report.sh` deleted with no shims.
- `plan_review.py` shell-out replaced by direct `stall_recovery.record_escalation()` import call.
- `stall-recovery-report.md` and `stall-recovery-report-allowlists.tsv` moved to `python/`; `stall_recovery.py` path references updated.
- `test-stall-recovery-report-{1,2,3}.{sh,md}` deleted; key scenarios ported to `test_stall_recovery.py`.
- Design test scripts updated (3-4 call sites) to use `python3 cli.py stall-recovery`.
- `python/stall_recovery.py` classify() gains a generic-profile branch matching bash:1091-1112.
- `record_attempt()` rewrites to append `attempt.N.*` rows preserving prior history.
- `migrated-scripts.tsv` updated with 9 retired paths.
- `make lint-retired-scripts`, `make py-lint`, `make py-test`, `make lint` all pass.

review_status: complete
rounds_completed: 5
diff_lines: 7280
