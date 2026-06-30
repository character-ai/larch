# test-step-7a.sh

Offline regression harness for `skills/implement/scripts/step-7a.sh`.

## Cases

1. `green path`: diagram generation succeeds, `code-flow-section.md` is written, the shared diagrams helper is invoked, rebase runs, pre-ship log flush succeeds, transcript status is relayed, and final KVs report `ok`.
2. `architecture-env-ignored`: `ARCHITECTURE_DIAGRAM_FILE` is ignored and only Code Flow content is written.
3. `diagram-skip`: a one-file `docs/` diff triggers the small/non-runtime skip, diagram generation is not invoked, `code-flow-section.md` is omitted, and the upsert is skipped.
4. `diagram-skip-forked`: a one-file fork-style `docs/` diff compares against `upstream/main`, skips generation, and skips the upsert.
5. `diagram-generate-forked`: a larger fork-style docs diff invokes the generator with `--base-remote upstream --base-ref main`.
6. `preserve-architecture`: a prior stable `larch:diagrams` body keeps its Architecture section while Step 7a replaces Code Flow.
7. `preserve-architecture-production-helper`: the production `python/cli.py diagrams upsert` path preserves a prior stable Architecture section while patching the stable comment in place.
8. `no-prior-diagrams-comment`: with no prior stable comment, Step 7a produces a Code Flow-only body.
9. `legacy-diagrams-orphan`: a legacy `<!-- larch:diagrams v1 runid=... -->` body is ignored so Step 7a does not collide with the stable marker.
10. `diagram-rejected`: sanitizer rejection reports `DIAGRAM_STATUS=skipped`, clears stale local diagram files, skips summary upsert, logs no warning, and continues.
11. `diagram-rejected-br-in-participant-alias`: sanitizer rejection with the `br-in-participant-alias` token still skips summary upsert.
12. `diagram-rejected-dollar-in-participant-alias`: sanitizer rejection with the `dollar-in-participant-alias` token still skips summary upsert.
13. `diagram-rejected-unclosed-frontmatter`: sanitizer rejection with the `unclosed-frontmatter` token still skips summary upsert.
14. `diagram-generation-failure`: non-sanitizer generation failure clears stale local diagram files, omits `code-flow-section.md`, skips the upsert, logs a warning, and does not copy `code-flow-diagram.failure.log` into committed run logs.
15. `diagram-failure-sanitizer`: a failed generator that still emits a sanitizer rejection token suppresses the summary upsert.
16. `summary-upsert-failure`: failed `python/cli.py diagrams upsert` appends a Tool Failures entry and later phases still run.
17. `flush-failure`: failed first `flush-execution-issues.sh` degrades `LOG_FLUSH_STATUS`, appends a Tool Failures entry, and still runs post-transcript flush plus commit.
18. `flush-failure-no-logs-commit`: a degraded first flush still reports `degraded` and skips the final log commit when `--no-logs-commit true`.
19. `no-logs-commit honored`: `--no-logs-commit true` skips the final log commit and emits `skipped-no-logs-commit`.
20. `forked-target rebase argv`: `--forked-target true` passes `--base-remote upstream --base-ref main` to the rebase probe.
21. `ISSUE_NUMBER empty gate`: empty issue number suppresses the summary upsert while the rest of the pipeline runs.
22. `generator-crash`: a crashing diagram helper is treated like generation failure, skips the upsert, and logs a warning.
23. `rebase-conflict`: `REBASE_OUTCOME=conflict` and `CHECKPOINT_NEXT=load-routing` exit `1`, relay the probe KVs, run the pre-ship log flush, and defer the git-backed log commit.
24. `rebase-failed`: `REBASE_OUTCOME=failed` and `CHECKPOINT_NEXT=load-routing` exit `3`, relay the probe KVs, run the pre-ship log flush, and defer the git-backed log commit.
25. `rebase-unexpected-rc`: preserves probe rc `5`, relays `REBASE_OUTCOME=failed` / `ROUTE=bail` / `CHECKPOINT_NEXT=load-routing`, runs the flush, and defers the git-backed log commit.
26. `quiet-rebase-contract`: with quiet mode enabled, the helper still relays `REBASE_OUTCOME` and `CHECKPOINT_NEXT` on the caller-visible contract stream.
27. `argv error`: missing `--implement-tmpdir` exits `2` and emits `STEP_7A_BAIL_REASON=argv`.

## Invariants

The harness treats empty copied script globs as valid so fixture setup stays portable when no root `scripts/*.sh` stubs are installed.
The fixture plugin copies the canonical `python/larch` package next to the shimmed `python/cli.py`, so migrated Step 7a imports exercise the production package layout.
String assertions use here-strings rather than producer pipes so `grep -q` early exits do not trip `pipefail` on large SKILL.md bodies.
