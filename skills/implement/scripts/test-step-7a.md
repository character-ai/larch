# test-step-7a.sh

Offline regression harness for `skills/implement/scripts/step-7a.sh`.

## Cases

1. `green path`: diagram generation succeeds, summary comment is upserted, rebase runs, pre-bump flush succeeds, and final KVs report `ok`.
2. `diagram-skip`: a one-file `docs/` diff triggers the small/non-runtime skip, diagram generation is not invoked, and the placeholder is still posted.
3. `diagram-rejected`: sanitizer rejection reports `DIAGRAM_STATUS=failed`, skips summary upsert, logs a warning, and continues.
4. `diagram-generation-failure`: non-sanitizer generation failure posts the placeholder summary comment and logs a warning.
5. `summary-upsert-failure`: failed `tracking-issue-summary.sh` appends a Tool Failures entry and later phases still run.
6. `flush-failure`: failed first `flush-execution-issues.sh` degrades `LOG_FLUSH_STATUS`, appends a Tool Failures entry, and still runs post-transcript flush plus commit.
7. `no-logs-commit honored`: `--no-logs-commit true` skips the final log commit and emits `skipped-no-logs-commit`.
8. `forked-target rebase argv`: `--forked-target true` passes `--base-remote upstream --base-ref main` to the rebase probe.
9. `ISSUE_NUMBER empty gate`: empty issue number suppresses the summary upsert while the rest of the pipeline runs.
10. `argv error`: missing `--implement-tmpdir` exits `2` and emits `STEP_7A_BAIL_REASON=argv`.
