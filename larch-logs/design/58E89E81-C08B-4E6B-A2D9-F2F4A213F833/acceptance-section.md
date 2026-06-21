## Acceptance

- `python/cli.py plan-review normalize-status` owns the post-loop status normalization, result-env synthesis, canonical KV envelope, escalation-evidence recording, and the `--read-result-env` read mode.
- `skills/design/scripts/design-step3-review.sh` retains only argv parse, resume-state validation, pause-save, `set -m` monitor setup, the background `plan-review run --mode loop` launch, process-group teardown, EXIT-trap sentinel guarantees, and the two normalizer calls. The wrapper shrinks materially while keeping job control.
- The `.completed/step-3` and `.completed/step-3-terminal` sentinel contracts are unchanged.
- The post-loop stdout KV envelope grammar and ordering stay byte-identical to the pre-refactor wrapper.
- The `--read-result-env` recovery grammar (`READ_RESULT_ENV_STATUS` plus the seven follow-up KVs) is unchanged; a symlinked result env yields `READ_RESULT_ENV_STATUS=missing` with no machine `WARN=` line.
- Terminal exit codes are preserved: `postplan-failed` emits `SUMMARY_OUTCOME=failed-postplan` and exits 1; `panel-init-failed` emits `SUMMARY_OUTCOME=failed-judge-panel` and exits 1.
- `make test-design-step3-review`, `make test-step3-orchestrator-fence`, `python3 -m pytest python/test_plan_review.py`, `make py-lint`, `make py-test`, and `make lint` all pass.
