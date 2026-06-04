### FINDING_10: Step 2 fail-closed `manifest-oos-materialization-failed` path untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Fail-closed `emit_bailed` `manifest-oos-materialization-failed` when manifest has non-empty `oos_observations[]` is untested. External implementer completes with OOS in manifest; materialize helper breaks; Step 2 could still emit `STATUS=complete` and skip OOS filing until ship time or never.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend `test-step2-dispatch.sh` (or sibling) with stubbed helper failure and assert `STATUS=bailed` / `REASON=manifest-oos-materialization-failed`.



### FINDING_23: Python pre-PR OOS enforcement duplicated instead of invoking gate/checkpoint scripts
- **Reviewer(s)**: dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: Pre-PR OOS enforcement is duplicated in `oos.disposition_ok` instead of calling `oos-disposition-gate.sh` / `oos-disposition-checkpoint.sh`. Checkpoint-only rules (e.g. requiring `--oos-issues-ndjson` when `non_sec_oos > 0`) are not applied on the Python path, so bash and Python can disagree on pass/fail at the same tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-parity-output.txt: Subprocess the same gate/checkpoint scripts with the same argv shape as `ship-pr.sh` / `oos-disposition-checkpoint.sh`, or add explicit parity tests that run both paths on identical fixtures.



### FINDING_7: Materialize failure leaves no accepted markdown; Step 9a.1 can pass and create PR without filing manifest OOS (bash)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Materialize failure sets `OOS_PENDING` but leaves no markdown; Step 9a.1 step-2 no-input exit + disposition pass + `--resume-phase pr-create` skips pr-prep rematerialize. Non-empty manifest `oos_observations[]` + `materialize-manifest-oos.sh` failure → orchestrator runs empty Step 9a.1 → gate passes with 0 blocks → PR created without filing manifest OOS (Python path blocks; bash does not).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Re-run materialize at start of Step 9a.1 or fail gate when manifest has OOS but no accepted blocks; or resume full ship/pr-prep not pr-create only until materialize succeeds.



