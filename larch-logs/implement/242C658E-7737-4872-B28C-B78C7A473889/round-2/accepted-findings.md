### FINDING_10: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:2265-2278
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] retry-sees-prewritten-prior uses wall-clock race between background writer and stubbed sync On slow CI the background job may not create round-4 before the second probe causing intermittent starting-round-invalid failures Make sync stub create the file deterministically or use a barrier instead of sleep-based background cp
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:2195-2204
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] entry-prior-deg-nonnumeric delegates to step5_original_count_prior_degraded_rounds but that alias is only defined in the parsers section make test-review-and-fix-step5-starting-round skips parsers; subshell errors with command not found instead of asserting env-write-failed Duplicate the eval alias in the step5-starting-round section after sourcing lib-implement-round-cap.sh
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] ship-pr-state.sh STALL_TRACKING persistence prose rarely applies at Step 5 because ship-pr-state is usually created at Step 8 envelope STALL_TRACKING=false may not reach finalize-state on pre-ship stalls; [STALLED] rename still depends on orchestrator discipline Document the gap or add a mechanical early-run STALL_TRACKING writer before Step 18
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:2270-2276
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] retry-sees-prewritten-prior uses sleep 0.1 background race slow CI can flake: first probe misses, case fails intermittently Use deterministic sync shadow like retry-sees-prior
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:2195-2204
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] step5_original_count_prior_degraded_rounds is only aliased in the parsers section but referenced from the step5-starting-round entry-nonnumeric stub. Running make test-review-and-fix-step5-starting-round alone would break if the stub ever calls the fallback path (e.g. future in-loop count_prior_degraded_rounds calls with a different second argument). Add the same declare -f count_prior_degraded_rounds rename eval at the start of the step5-starting-round section after sourcing lib-implement-round-cap.sh.
- **Suggested revision**: Address the concern above.


### FINDING_26: **architecture** `skills/implement/SKILL.md:1214` — Round-1 added the correct stall-bullet fixes (retain envelope `STALL_TRACKING`, removed `Set STALL_TRACKING=true`, moved `starting-round-invalid` to Tool Failures, added conditional `ship-pr-state.sh` key rewrite), but the primary `starting-round-invalid` path still cannot reach mechanical teardown rename semantics. Step 5 `stall` skips to Step 16; `ship-pr-state.sh` is not created until Step 8+ (`skills/implement/SKILL.md:1444-1455`). On that path the new “if `ship-pr-state.sh` already exists, persist…” branch is a no-op. Step 18 `implement-finalize.sh teardown` reads `STALL_TRACKING` only from `finalize-state.sh` after optional `restore-finalize-state.sh` (`scripts/implement-finalize.sh:1320`, `skills/implement/SKILL.md:1805-1817`), not from the orchestrator variable assigned at Step 5. So envelope `STALL_TRACKING=false` is not durably wired into the rename gate the prose claims; prevention of `[STALLED]` rename relies on teardown failing/absent state (pre-existing) or prompt-side behavior, not on the new persistence contract. **Suggested fix:** On Step 5 `stall`, before “Skip to Step 16”, require writing or updating minimal on-disk state when `ship-pr-state.sh` is absent: either seed the Step 8 initial `ship-pr-state.sh` template with `STALL_TRACKING` taken from the parsed envelope (plus `ISSUE_NUMBER`/`RUN_ID`/`REPO` from `parent-issue.md`/`session-env.sh`), or extend Step 18 with an orchestrator-allowed pre-teardown path that builds `finalize-state.sh` via `restore-finalize-state.sh` from that minimal state. Align `review-implement-step5-loop.md:17` with whichever mechanism is chosen.
- **Reviewer**: dyn-stall-tracking-propagation-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:1214` — Round-1 added the correct stall-bullet fixes (retain envelope `STALL_TRACKING`, removed `Set STALL_TRACKING=true`, moved `starting-round-invalid` to Tool Failures, added conditional `ship-pr-state.sh` key rewrite), but the primary `starting-round-invalid` path still cannot reach mechanical teardown rename semantics. Step 5 `stall` skips to Step 16; `ship-pr-state.sh` is not created until Step 8+ (`skills/implement/SKILL.md:1444-1455`). On that path the new “if `ship-pr-state.sh` already exists, persist…” branch is a no-op. Step 18 `implement-finalize.sh teardown` reads `STALL_TRACKING` only from `finalize-state.sh` after optional `restore-finalize-state.sh` (`scripts/implement-finalize.sh:1320`, `skills/implement/SKILL.md:1805-1817`), not from the orchestrator variable assigned at Step 5. So envelope `STALL_TRACKING=false` is not durably wired into the rename gate the prose claims; prevention of `[STALLED]` rename relies on teardown failing/absent state (pre-existing) or prompt-side behavior, not on the new persistence contract. **Suggested fix:** On Step 5 `stall`, before “Skip to Step 16”, require writing or updating minimal on-disk state when `ship-pr-state.sh` is absent: either seed the Step 8 initial `ship-pr-state.sh` template with `STALL_TRACKING` taken from the parsed envelope (plus `ISSUE_NUMBER`/`RUN_ID`/`REPO` from `parent-issue.md`/`session-env.sh`), or extend Step 18 with an orchestrator-allowed pre-teardown path that builds `finalize-state.sh` via `restore-finalize-state.sh` from that minimal state. Align `review-implement-step5-loop.md:17` with whichever mechanism is chosen.
- **Suggested revision**: Address the concern above.


### FINDING_3: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:2270-2276
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] retry-sees-prewritten-prior uses background sleep/cp race against sync stub On overloaded CI the copy may occur after both probe attempts causing intermittent harness failure Use create-prior sync stub or synchronize copy with stub invocation instead of timing-based background job
- **Suggested revision**: Address the concern above.


### FINDING_31: **risk-integration** `skills/review-and-fix/scripts/test-review-and-fix.sh:2006,2197-2203,2361-2368` — `step5_original_count_prior_degraded_rounds` is only created in the `parsers` block via `eval "$(declare -f count_prior_degraded_rounds | …)"`, but that block sources only `review-implement-step5-loop.sh` and never `scripts/lib-implement-round-cap.sh`, so `count_prior_degraded_rounds` is not defined when `parsers` runs (including `--section parsers` alone). The `step5-starting-round` block references `step5_original_count_prior_degraded_rounds` in the `entry-nonnumeric` override’s `else` branch but never defines it itself. Case 8 (`STARTING_ROUND=1`) masks this because production code exits on the first bogus entry call and never reaches the fallback; the Makefile/CI shard runs `--section step5-starting-round` without `parsers`, so the fallback path is both untested and broken if ever exercised. **Suggested fix:** After sourcing `lib-implement-round-cap.sh` in the `step5-starting-round` block (around 2098–2101), add the same `eval "$(declare -f count_prior_degraded_rounds | sed '1s/count_prior_degraded_rounds/step5_original_count_prior_degraded_rounds/')"` there (or call `count_prior_degraded_rounds` from lib directly in the `else` branch). Optionally remove or relocate the parsers-line alias so shard order is not load-bearing.
- **Reviewer**: dyn-test-isolation-output.txt
- **Concern**: - **risk-integration** `skills/review-and-fix/scripts/test-review-and-fix.sh:2006,2197-2203,2361-2368` — `step5_original_count_prior_degraded_rounds` is only created in the `parsers` block via `eval "$(declare -f count_prior_degraded_rounds | …)"`, but that block sources only `review-implement-step5-loop.sh` and never `scripts/lib-implement-round-cap.sh`, so `count_prior_degraded_rounds` is not defined when `parsers` runs (including `--section parsers` alone). The `step5-starting-round` block references `step5_original_count_prior_degraded_rounds` in the `entry-nonnumeric` override’s `else` branch but never defines it itself. Case 8 (`STARTING_ROUND=1`) masks this because production code exits on the first bogus entry call and never reaches the fallback; the Makefile/CI shard runs `--section step5-starting-round` without `parsers`, so the fallback path is both untested and broken if ever exercised. **Suggested fix:** After sourcing `lib-implement-round-cap.sh` in the `step5-starting-round` block (around 2098–2101), add the same `eval "$(declare -f count_prior_degraded_rounds | sed '1s/count_prior_degraded_rounds/step5_original_count_prior_degraded_rounds/')"` there (or call `count_prior_degraded_rounds` from lib directly in the `else` branch). Optionally remove or relocate the parsers-line alias so shard order is not load-bearing.
- **Suggested revision**: Address the concern above.


### FINDING_32: **risk-integration** `skills/review-and-fix/scripts/test-review-and-fix.sh:2265-2279` — Case 1b (`retry-sees-prewritten-prior`) starts a background subshell (`sleep 0.1` then `cp` into `round-4`) with `&` but never `wait`s on it. The test relies on that job finishing during the subshell’s `sleep-only` sync (`sleep 0.2` at 2217–2218) before the second artifact probe. Under scheduler delay this can flake false-fail; the orphan job can also outlive the assertion window (usually harmless because case dirs are unique, but it weakens isolation guarantees). **Suggested fix:** `wait` on the background PID immediately after `step5_run_loop_case` returns (or pre-create `round-4/review-and-fix.env` before invoking the loop and use sync only to exercise ordering, matching Case 1’s deterministic `create-prior` pattern).
- **Reviewer**: dyn-test-isolation-output.txt
- **Concern**: - **risk-integration** `skills/review-and-fix/scripts/test-review-and-fix.sh:2265-2279` — Case 1b (`retry-sees-prewritten-prior`) starts a background subshell (`sleep 0.1` then `cp` into `round-4`) with `&` but never `wait`s on it. The test relies on that job finishing during the subshell’s `sleep-only` sync (`sleep 0.2` at 2217–2218) before the second artifact probe. Under scheduler delay this can flake false-fail; the orphan job can also outlive the assertion window (usually harmless because case dirs are unique, but it weakens isolation guarantees). **Suggested fix:** `wait` on the background PID immediately after `step5_run_loop_case` returns (or pre-create `round-4/review-and-fix.env` before invoking the loop and use sync only to exercise ordering, matching Case 1’s deterministic `create-prior` pattern).
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:2265-2278
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] retry-sees-prewritten-prior uses wall-clock race between background copy and sleep-only sync. Slow CI: probe succeeds before background write (false positive). Fast CI: usually passes but timing-dependent. Replace with deterministic sync stub (e.g. create-prior latch) like retry-sees-prior.
- **Suggested revision**: Address the concern above.


### FINDING_8: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:2195-2203
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] entry-nonnumeric stub references step5_original_count_prior_degraded_rounds only defined in parsers section. Future test hitting stub else branch under --section step5-starting-round alone: command not found. Move count_prior_degraded_rounds alias into step5-starting-round section setup.
- **Suggested revision**: Address the concern above.


