# test-step-7a.sh

Offline regression harness for `skills/implement/scripts/step-7a.sh`.

## Cases

1. `green path`: diagram generation succeeds, summary comment is upserted, rebase runs, pre-bump flush succeeds, transcript status is relayed, and final KVs report `ok`.
2. `diagram-skip`: a one-file `docs/` diff triggers the small/non-runtime skip, diagram generation is not invoked, and the placeholder is still posted.
3. `diagram-rejected`: sanitizer rejection reports `DIAGRAM_STATUS=skipped`, skips summary upsert, logs no warning, and continues.
4. `diagram-rejected-br-in-participant-alias`: sanitizer rejection with the `br-in-participant-alias` token still skips summary upsert.
5. `diagram-rejected-dollar-in-participant-alias`: sanitizer rejection with the `dollar-in-participant-alias` token still skips summary upsert.
6. `diagram-rejected-unclosed-frontmatter`: sanitizer rejection with the `unclosed-frontmatter` token still skips summary upsert.
7. `diagram-generation-failure`: non-sanitizer generation failure posts the placeholder summary comment and logs a warning.
8. `diagram-failure-sanitizer`: a failed generator that still emits a sanitizer rejection token suppresses the summary upsert.
9. `summary-upsert-failure`: failed `tracking-issue-summary.sh` appends a Tool Failures entry and later phases still run.
10. `flush-failure`: failed first `flush-execution-issues.sh` degrades `LOG_FLUSH_STATUS`, appends a Tool Failures entry, and still runs post-transcript flush plus commit.
11. `flush-failure-no-logs-commit`: a degraded first flush still reports `degraded` and skips the final log commit when `--no-logs-commit true`.
12. `no-logs-commit honored`: `--no-logs-commit true` skips the final log commit and emits `skipped-no-logs-commit`.
13. `forked-target rebase argv`: `--forked-target true` passes `--base-remote upstream --base-ref main` to the rebase probe.
14. `ISSUE_NUMBER empty gate`: empty issue number suppresses the summary upsert while the rest of the pipeline runs.
15. `generator-crash`: a crashing diagram helper is treated like generation failure, posts the placeholder summary comment, and logs a warning.
16. `rebase-conflict`: `REBASE_OUTCOME=conflict` exits `1`, relays the probe KVs, and reports `LOG_FLUSH_STATUS=skipped-rebase-checkpoint` because pre-bump flush never ran.
17. `rebase-failed`: `REBASE_OUTCOME=failed` exits `3`, relays the probe KVs, and reports `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`.
18. `quiet-rebase-contract`: with quiet mode enabled, the helper still relays `REBASE_OUTCOME` on the caller-visible contract stream.
19. `argv error`: missing `--implement-tmpdir` exits `2` and emits `STEP_7A_BAIL_REASON=argv`.
