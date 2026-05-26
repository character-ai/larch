# test-step-7a.sh

Offline regression harness for `skills/implement/scripts/step-7a.sh`.

## Cases

1. `green path`: diagram generation succeeds, `code-flow-section.md` is written, the shared diagrams helper is invoked, rebase runs, pre-bump flush succeeds, transcript status is relayed, and final KVs report `ok`.
2. `architecture-env-ignored`: `ARCHITECTURE_DIAGRAM_FILE` is ignored and only Code Flow content is written.
3. `diagram-skip`: a one-file `docs/` diff triggers the small/non-runtime skip, diagram generation is not invoked, `code-flow-section.md` is omitted, and the upsert is skipped.
4. `diagram-skip-forked`: a one-file fork-style `docs/` diff compares against `upstream/main`, skips generation, and skips the upsert.
5. `diagram-generate-forked`: a larger fork-style docs diff invokes the generator with `--base-remote upstream --base-ref main`.
6. `preserve-architecture`: a prior stable `larch:diagrams` body keeps its Architecture section while Step 7a replaces Code Flow.
7. `no-prior-diagrams-comment`: with no prior stable comment, Step 7a produces a Code Flow-only body.
8. `legacy-diagrams-orphan`: a legacy `<!-- larch:diagrams v1 runid=... -->` body is ignored so Step 7a does not collide with the stable marker.
9. `diagram-rejected`: sanitizer rejection reports `DIAGRAM_STATUS=skipped`, clears stale local diagram files, skips summary upsert, logs no warning, and continues.
10. `diagram-rejected-br-in-participant-alias`: sanitizer rejection with the `br-in-participant-alias` token still skips summary upsert.
11. `diagram-rejected-dollar-in-participant-alias`: sanitizer rejection with the `dollar-in-participant-alias` token still skips summary upsert.
12. `diagram-rejected-unclosed-frontmatter`: sanitizer rejection with the `unclosed-frontmatter` token still skips summary upsert.
13. `diagram-generation-failure`: non-sanitizer generation failure clears stale local diagram files, omits `code-flow-section.md`, skips the upsert, and logs a warning.
14. `diagram-failure-sanitizer`: a failed generator that still emits a sanitizer rejection token suppresses the summary upsert.
15. `summary-upsert-failure`: failed `upsert-diagrams-comment.sh` appends a Tool Failures entry and later phases still run.
16. `flush-failure`: failed first `flush-execution-issues.sh` degrades `LOG_FLUSH_STATUS`, appends a Tool Failures entry, and still runs post-transcript flush plus commit.
17. `flush-failure-no-logs-commit`: a degraded first flush still reports `degraded` and skips the final log commit when `--no-logs-commit true`.
18. `no-logs-commit honored`: `--no-logs-commit true` skips the final log commit and emits `skipped-no-logs-commit`.
19. `forked-target rebase argv`: `--forked-target true` passes `--base-remote upstream --base-ref main` to the rebase probe.
20. `ISSUE_NUMBER empty gate`: empty issue number suppresses the summary upsert while the rest of the pipeline runs.
21. `generator-crash`: a crashing diagram helper is treated like generation failure, skips the upsert, and logs a warning.
22. `rebase-conflict`: `REBASE_OUTCOME=conflict` exits `1`, relays the probe KVs, and reports `LOG_FLUSH_STATUS=skipped-rebase-checkpoint` because pre-bump flush never ran.
23. `rebase-failed`: `REBASE_OUTCOME=failed` exits `3`, relays the probe KVs, and reports `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`.
24. `quiet-rebase-contract`: with quiet mode enabled, the helper still relays `REBASE_OUTCOME` on the caller-visible contract stream.
25. `argv error`: missing `--implement-tmpdir` exits `2` and emits `STEP_7A_BAIL_REASON=argv`.
