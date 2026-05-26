# test-step-7a.sh

Offline regression harness for `skills/implement/scripts/step-7a.sh`.

## Cases

<<<<<<< HEAD
1. `green`: diagram generation succeeds, summary comment is upserted, rebase runs, pre-bump flush succeeds, transcript status is relayed, and final KVs report `ok`.
2. `diagram-skip`: a one-file `docs/` diff triggers the small/non-runtime skip, diagram generation is not invoked, and the placeholder is still posted.
3. `diagram-skip-forked`: a one-file fork-style `docs/` diff compares against `upstream/main`, skips generation, and still posts the placeholder.
4. `diagram-generate-forked`: a larger fork-style docs diff invokes the generator with `--base-remote upstream --base-ref main`.
5. `diagram-rejected`: sanitizer rejection reports `DIAGRAM_STATUS=skipped`, posts the placeholder summary comment carrying the generator-emitted `SKIP_REASON` value (default `pipe-in-node-label fence=mermaid line=7`), logs no warning, and continues.
6. `diagram-rejected-br-in-participant-alias`: sanitizer rejection posts the placeholder summary comment carrying `br-in-participant-alias fence=mermaid line=7`.
7. `diagram-rejected-dollar-in-participant-alias`: sanitizer rejection posts the placeholder summary comment carrying `dollar-in-participant-alias fence=mermaid line=7`.
8. `diagram-rejected-unclosed-frontmatter`: sanitizer rejection posts the placeholder summary comment carrying `unclosed-frontmatter fence=mermaid line=7`.
9. `diagram-failure`: posts the placeholder summary comment carrying `SKIP_REASON` `helper-error` (or whatever `STEP7A_GEN_FORCE_SKIP_REASON` overrides to), appends a Warnings entry, and exits 0.
10. `diagram-failure-sanitizer`: a failed generator that emits a sanitizer rejection token (via `STEP7A_GEN_FORCE_SKIP_REASON='pipe-in-node-label fence=mermaid line=7'`) still posts the placeholder summary comment with that `SKIP_REASON` and emits `DIAGRAM_STATUS=failed` with `COMMENT_URL` set.
11. `upsert-failure`: failed `tracking-issue-summary.sh` appends a Tool Failures entry and later phases still run.
12. `flush-failure`: failed first `flush-execution-issues.sh` degrades `LOG_FLUSH_STATUS`, appends a Tool Failures entry, and still runs post-transcript flush plus commit.
13. `flush-failure-no-logs-commit`: a degraded first flush still reports `degraded` and skips the final log commit when `--no-logs-commit true`.
14. `no-logs-commit`: `--no-logs-commit true` skips the final log commit and emits `skipped-no-logs-commit`.
15. `forked-target`: `--forked-target true` passes `--base-remote upstream --base-ref main` to the rebase probe.
16. `issue-empty`: empty issue number suppresses the summary upsert while the rest of the pipeline runs.
17. `generator-crash`: a crashing diagram helper is treated like generation failure, posts the placeholder summary comment, and logs a warning.
18. `rebase-conflict`: `REBASE_OUTCOME=conflict` exits `1`, relays the probe KVs, and reports `LOG_FLUSH_STATUS=skipped-rebase-checkpoint` because pre-bump flush never ran.
19. `rebase-failed`: `REBASE_OUTCOME=failed` exits `3`, relays the probe KVs, and reports `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`.
20. `rebase-unexpected-rc`: `STEP7A_REBASE_MODE=unexpected` causes the probe to return rc 5 with `REBASE_OUTCOME=failed`, `REBASE_ERROR=unexpected-rc-5`; the helper exits 5 and emits `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`.
21. `quiet-rebase-contract`: with quiet mode enabled, the helper still relays `REBASE_OUTCOME` on the caller-visible contract stream.
22. `quiet-diagram-skip-contract`: with quiet mode enabled, the helper still relays the `⏩ 7a: diagrams status=skip reason=small-non-runtime-change elapsed=0s` line on the caller-visible contract stream.
23. `argv-error`: missing `--implement-tmpdir` exits `2` and emits `STEP_7A_BAIL_REASON=argv`.
=======
1. `green path`: diagram generation succeeds, `code-flow-section.md` is written, the shared diagrams helper is invoked, rebase runs, pre-bump flush succeeds, transcript status is relayed, and final KVs report `ok`.
2. `architecture-env-ignored`: `ARCHITECTURE_DIAGRAM_FILE` is ignored and only Code Flow content is written.
3. `diagram-skip`: a one-file `docs/` diff triggers the small/non-runtime skip, diagram generation is not invoked, `code-flow-section.md` is omitted, and the upsert is skipped.
4. `diagram-skip-forked`: a one-file fork-style `docs/` diff compares against `upstream/main`, skips generation, and skips the upsert.
5. `diagram-generate-forked`: a larger fork-style docs diff invokes the generator with `--base-remote upstream --base-ref main`.
6. `diagram-rejected`: sanitizer rejection reports `DIAGRAM_STATUS=skipped`, skips summary upsert, logs no warning, and continues.
7. `diagram-rejected-br-in-participant-alias`: sanitizer rejection with the `br-in-participant-alias` token still skips summary upsert.
8. `diagram-rejected-dollar-in-participant-alias`: sanitizer rejection with the `dollar-in-participant-alias` token still skips summary upsert.
9. `diagram-rejected-unclosed-frontmatter`: sanitizer rejection with the `unclosed-frontmatter` token still skips summary upsert.
10. `diagram-generation-failure`: non-sanitizer generation failure omits `code-flow-section.md`, skips the upsert, and logs a warning.
11. `diagram-failure-sanitizer`: a failed generator that still emits a sanitizer rejection token suppresses the summary upsert.
12. `summary-upsert-failure`: failed `upsert-diagrams-comment.sh` appends a Tool Failures entry and later phases still run.
13. `flush-failure`: failed first `flush-execution-issues.sh` degrades `LOG_FLUSH_STATUS`, appends a Tool Failures entry, and still runs post-transcript flush plus commit.
14. `flush-failure-no-logs-commit`: a degraded first flush still reports `degraded` and skips the final log commit when `--no-logs-commit true`.
15. `no-logs-commit honored`: `--no-logs-commit true` skips the final log commit and emits `skipped-no-logs-commit`.
16. `forked-target rebase argv`: `--forked-target true` passes `--base-remote upstream --base-ref main` to the rebase probe.
17. `ISSUE_NUMBER empty gate`: empty issue number suppresses the summary upsert while the rest of the pipeline runs.
18. `generator-crash`: a crashing diagram helper is treated like generation failure, skips the upsert, and logs a warning.
19. `rebase-conflict`: `REBASE_OUTCOME=conflict` exits `1`, relays the probe KVs, and reports `LOG_FLUSH_STATUS=skipped-rebase-checkpoint` because pre-bump flush never ran.
20. `rebase-failed`: `REBASE_OUTCOME=failed` exits `3`, relays the probe KVs, and reports `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`.
21. `quiet-rebase-contract`: with quiet mode enabled, the helper still relays `REBASE_OUTCOME` on the caller-visible contract stream.
22. `argv error`: missing `--implement-tmpdir` exits `2` and emits `STEP_7A_BAIL_REASON=argv`.
>>>>>>> 03920fdd (Implement shared diagrams upsert helper: /design posts Architecture, /implement posts Code Flow (#2840))
