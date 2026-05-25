# test-step-7a.sh

Offline regression harness for `skills/implement/scripts/step-7a.sh`.

## Cases

1. `green path`: diagram generation succeeds, summary comment is upserted, rebase runs, pre-bump flush succeeds, and final KVs report `ok`.
2. `diagram-skip`: a one-file `docs/` diff triggers the small/non-runtime skip, diagram generation is not invoked, and the placeholder is still posted.
3. `diagram-rejected`: sanitizer rejection reports `DIAGRAM_STATUS=skipped`, skips summary upsert, logs no warning, and continues.
4. `diagram-skipped-non-sanitizer`: a non-sanitizer `STATUS=skipped` still posts the placeholder summary comment.
5. `diagram-generation-failure`: non-sanitizer generation failure posts the placeholder summary comment and logs a warning.
6. `summary-upsert-failure`: failed `tracking-issue-summary.sh` appends a Tool Failures entry and later phases still run.
7. `flush-failure`: failed first `flush-execution-issues.sh` degrades `LOG_FLUSH_STATUS`, appends a Tool Failures entry, and still runs post-transcript flush plus commit.
8. `flush-failure-no-logs-commit`: a degraded first flush still reports `degraded` and skips the final log commit when `--no-logs-commit true`.
9. `no-logs-commit honored`: `--no-logs-commit true` skips the final log commit and emits `skipped-no-logs-commit`.
10. `forked-target rebase argv`: `--forked-target true` passes `--base-remote upstream --base-ref main` to the rebase probe.
11. `ISSUE_NUMBER empty gate`: empty issue number suppresses the summary upsert while the rest of the pipeline runs.
12. `generator-crash`: a crashing diagram helper is treated like generation failure, posts the placeholder summary comment, and logs a warning.
13. `rebase-conflict`: `REBASE_OUTCOME=conflict` exits `1`, relays the probe KVs, and reports `LOG_FLUSH_STATUS=skipped-rebase-checkpoint` because pre-bump flush never ran.
14. `rebase-failed`: `REBASE_OUTCOME=failed` exits `3`, relays the probe KVs, and reports `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`.
15. `quiet-rebase-contract`: with quiet mode enabled, the helper still relays `REBASE_OUTCOME` on the caller-visible contract stream.
16. `argv error`: missing `--implement-tmpdir` exits `2` and emits `STEP_7A_BAIL_REASON=argv`.
