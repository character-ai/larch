### FINDING_1: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Hoisted past-cap anchor uses bare -f while artifact guard uses step5_probe_prior_round_env Transient invisible round-(N-1)/review-and-fix.env skips hoisted mav-resume-past-cap even though sync retry would see the file; in-loop cap check still prevents extra review work but adds unnecessary loop entry Call step5_probe_prior_round_env for the hoisted anchor when STARTING_ROUND > entry_effective_cap
- **Suggested revision**: Address the concern above.

### FINDING_2: risk-integration: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] STALL_TRACKING retain/assign is prompt-only with no mechanical regression guard A future SKILL edit could reintroduce unconditional Set STALL_TRACKING=true and negate starting-round-invalid envelope reclassification exactly as in RUN_ID FA25692E Add test-implement-structure.sh assertion on stall bullet prose per plan optional harness
- **Suggested revision**: Address the concern above.

### FINDING_3: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:2270-2276
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] retry-sees-prewritten-prior uses background sleep/cp race against sync stub On overloaded CI the copy may occur after both probe attempts causing intermittent harness failure Use create-prior sync stub or synchronize copy with stub invocation instead of timing-based background job
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/review-and-fix/scripts/test-review-and-fix.md:7
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract doc updated outside plan six-file list Minor scope drift versus stated acceptance boundary 10 Accept as doc sync or fold section note into review-implement-step5-loop.md only
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Hoisted mav-resume-past-cap anchor uses bare -f instead of step5_probe_prior_round_env. STARTING_ROUND=6 with round-5 artifact briefly invisible: hoisted misses, probe+sync succeeds, in-loop past-cap still fires on first iteration—correct status, extra round-entry work. Route hoisted anchor through step5_probe_prior_round_env or document in-loop check as intentional retry.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:2265-2278
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] retry-sees-prewritten-prior uses wall-clock race between background copy and sleep-only sync. Slow CI: probe succeeds before background write (false positive). Fast CI: usually passes but timing-dependent. Replace with deterministic sync stub (e.g. create-prior latch) like retry-sees-prior.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] STALL_TRACKING=false for starting-round-invalid relies on orchestrator prose; ship-pr-state rewrite only when file exists (usually Step 8+). Model ignores retain-from-envelope prose: tracking issue could still be renamed [STALLED] despite envelope false (pre-fix class of failure). Add mechanical STALL_TRACKING persistence on Step 5 stall skip if hard guarantee needed.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:2195-2203
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] entry-nonnumeric stub references step5_original_count_prior_degraded_rounds only defined in parsers section. Future test hitting stub else branch under --section step5-starting-round alone: command not found. Move count_prior_degraded_rounds alias into step5-starting-round section setup.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] correctness: scripts/run-step5-review.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] IMPLEMENT_TMPDIR pwd -P vs writer path mismatch (Hypothesis B) deferred per plan. sync+retry cannot fix true path split; diagnostic keys are the mitigation. Future issue if diagnostics show path mismatch.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:2265-2278
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] retry-sees-prewritten-prior uses wall-clock race between background writer and stubbed sync On slow CI the background job may not create round-4 before the second probe causing intermittent starting-round-invalid failures Make sync stub create the file deterministically or use a barrier instead of sleep-based background cp
- **Suggested revision**: Address the concern above.

### FINDING_11: **`STARTING_ROUND` / `prior_round_num`** are validated as positive integers before use in `round-${n}/` paths, which blocks shell metacharacter injection in constructed paths (`review-implement-step5-loop.sh:91-107`, `run-step5-review.sh:134-137`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`STARTING_ROUND` / `prior_round_num`** are validated as positive integers before use in `round-${n}/` paths, which blocks shell metacharacter injection in constructed paths (`review-implement-step5-loop.sh:91-107`, `run-step5-review.sh:134-137`).
- **Suggested revision**: Address the concern above.

### FINDING_12: **Hoisted `mav-resume-past-cap`** requires both `STARTING_ROUND > entry_effective_cap` and existence of the immediate prior `review-and-fix.env`, closing the “high `--starting-round` with no artifacts → silent success” gap (test case `starting-round-999`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Hoisted `mav-resume-past-cap`** requires both `STARTING_ROUND > entry_effective_cap` and existence of the immediate prior `review-and-fix.env`, closing the “high `--starting-round` with no artifacts → silent success” gap (test case `starting-round-999`).
- **Suggested revision**: Address the concern above.

### FINDING_13: **`starting-round-invalid`** still exits `2` with `STEP5_REVIEW_STATUS=stall`; only tracking rename is softened via `STALL_TRACKING=false`, not review completion.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`starting-round-invalid`** still exits `2` with `STEP5_REVIEW_STATUS=stall`; only tracking rename is softened via `STALL_TRACKING=false`, not review completion.
- **Suggested revision**: Address the concern above.

### FINDING_14: **`sync`** is bounded (one call, two `-f` probes max) and guarded with `|| true` under `set -euo pipefail`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`sync`** is bounded (one call, two `-f` probes max) and guarded with `|| true` under `set -euo pipefail`.
- **Suggested revision**: Address the concern above.

### FINDING_15: No new secrets, credential handling, network calls, or dependency changes in the functional diff.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - No new secrets, credential handling, network calls, or dependency changes in the functional diff.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:108-111` — The hoisted past-cap anchor checks only `round-(STARTING_ROUND-1)/review-and-fix.env`, not continuity of rounds `1..N-2`. A party that can write under `IMPLEMENT_TMPDIR` and influence `--starting-round` could still reach `mav-resume-past-cap` with a sparse tmpdir (e.g. only `round-5` present while starting at `6`). That trust model predates this PR (the in-loop cap path had the same semantics); the hoisted check does not widen it materially. **Suggested fix:** If the threat model ever includes untrusted tmpdir writers, require monotonic round artifacts or a signed resume token in `session-env.sh` before emitting `mav-resume-past-cap`.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:114` — New `larch_err` diagnostics emit full `IMPLEMENT_TMPDIR` and `expected_env_path` values (often under `~/.cache/larch/sessions/…`). That is useful for operators but can surface usernames or internal paths in shared CI logs. **Suggested fix:** If logs leave the operator machine, route through existing redaction helpers or log basenames plus a stable session id.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **architecture** `skills/implement/SKILL.md:1214` — Round-2 prose adds persisting envelope `STALL_TRACKING` into `ship-pr-state.sh` via key-based rewrite (not sourcing). That is sound from a code-execution perspective; enforcement depends on the orchestrator following prose and not sourcing untrusted state files—consistent with existing implement patterns.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:2195-2204
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] entry-prior-deg-nonnumeric delegates to step5_original_count_prior_degraded_rounds but that alias is only defined in the parsers section make test-review-and-fix-step5-starting-round skips parsers; subshell errors with command not found instead of asserting env-write-failed Duplicate the eval alias in the step5-starting-round section after sourcing lib-implement-round-cap.sh
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/implement/SKILL.md:1214
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] ship-pr-state.sh STALL_TRACKING persistence prose rarely applies at Step 5 because ship-pr-state is usually created at Step 8 envelope STALL_TRACKING=false may not reach finalize-state on pre-ship stalls; [STALLED] rename still depends on orchestrator discipline Document the gap or add a mechanical early-run STALL_TRACKING writer before Step 18
- **Suggested revision**: Address the concern above.

### FINDING_21: architecture: skills/review-and-fix/scripts/review-implement-step5-loop.sh:108
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Hoisted past-cap anchor uses bare -f without sync retry while probe path has sync+retry transient visibility miss skips hoisted mav-resume-past-cap; in-loop cap check still saves correctness but paths differ Reuse step5_probe_prior_round_env for the hoisted anchor
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:2270-2276
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] retry-sees-prewritten-prior uses sleep 0.1 background race slow CI can flake: first probe misses, case fails intermittently Use deterministic sync shadow like retry-sees-prior
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] architecture: skills/review-and-fix/scripts/review-implement-step5-loop.sh:142-145
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] flush_review_batches ordering differs between hoisted and in-loop mav-resume paths theoretical partial-stdout consumer could observe different ordering unify order if a consumer is identified
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] architecture: scripts/run-step5-review.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] IMPLEMENT_TMPDIR pwd -P resolution not changed per plan Hypothesis B path mismatch would still defeat sync retry dedicated follow-up if diagnostics show path skew
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:2195-2204
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] step5_original_count_prior_degraded_rounds is only aliased in the parsers section but referenced from the step5-starting-round entry-nonnumeric stub. Running make test-review-and-fix-step5-starting-round alone would break if the stub ever calls the fallback path (e.g. future in-loop count_prior_degraded_rounds calls with a different second argument). Add the same declare -f count_prior_degraded_rounds rename eval at the start of the step5-starting-round section after sourcing lib-implement-round-cap.sh.
- **Suggested revision**: Address the concern above.

### FINDING_26: **architecture** `skills/implement/SKILL.md:1214` — Round-1 added the correct stall-bullet fixes (retain envelope `STALL_TRACKING`, removed `Set STALL_TRACKING=true`, moved `starting-round-invalid` to Tool Failures, added conditional `ship-pr-state.sh` key rewrite), but the primary `starting-round-invalid` path still cannot reach mechanical teardown rename semantics. Step 5 `stall` skips to Step 16; `ship-pr-state.sh` is not created until Step 8+ (`skills/implement/SKILL.md:1444-1455`). On that path the new “if `ship-pr-state.sh` already exists, persist…” branch is a no-op. Step 18 `implement-finalize.sh teardown` reads `STALL_TRACKING` only from `finalize-state.sh` after optional `restore-finalize-state.sh` (`scripts/implement-finalize.sh:1320`, `skills/implement/SKILL.md:1805-1817`), not from the orchestrator variable assigned at Step 5. So envelope `STALL_TRACKING=false` is not durably wired into the rename gate the prose claims; prevention of `[STALLED]` rename relies on teardown failing/absent state (pre-existing) or prompt-side behavior, not on the new persistence contract. **Suggested fix:** On Step 5 `stall`, before “Skip to Step 16”, require writing or updating minimal on-disk state when `ship-pr-state.sh` is absent: either seed the Step 8 initial `ship-pr-state.sh` template with `STALL_TRACKING` taken from the parsed envelope (plus `ISSUE_NUMBER`/`RUN_ID`/`REPO` from `parent-issue.md`/`session-env.sh`), or extend Step 18 with an orchestrator-allowed pre-teardown path that builds `finalize-state.sh` via `restore-finalize-state.sh` from that minimal state. Align `review-implement-step5-loop.md:17` with whichever mechanism is chosen.
- **Reviewer**: dyn-stall-tracking-propagation-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:1214` — Round-1 added the correct stall-bullet fixes (retain envelope `STALL_TRACKING`, removed `Set STALL_TRACKING=true`, moved `starting-round-invalid` to Tool Failures, added conditional `ship-pr-state.sh` key rewrite), but the primary `starting-round-invalid` path still cannot reach mechanical teardown rename semantics. Step 5 `stall` skips to Step 16; `ship-pr-state.sh` is not created until Step 8+ (`skills/implement/SKILL.md:1444-1455`). On that path the new “if `ship-pr-state.sh` already exists, persist…” branch is a no-op. Step 18 `implement-finalize.sh teardown` reads `STALL_TRACKING` only from `finalize-state.sh` after optional `restore-finalize-state.sh` (`scripts/implement-finalize.sh:1320`, `skills/implement/SKILL.md:1805-1817`), not from the orchestrator variable assigned at Step 5. So envelope `STALL_TRACKING=false` is not durably wired into the rename gate the prose claims; prevention of `[STALLED]` rename relies on teardown failing/absent state (pre-existing) or prompt-side behavior, not on the new persistence contract. **Suggested fix:** On Step 5 `stall`, before “Skip to Step 16”, require writing or updating minimal on-disk state when `ship-pr-state.sh` is absent: either seed the Step 8 initial `ship-pr-state.sh` template with `STALL_TRACKING` taken from the parsed envelope (plus `ISSUE_NUMBER`/`RUN_ID`/`REPO` from `parent-issue.md`/`session-env.sh`), or extend Step 18 with an orchestrator-allowed pre-teardown path that builds `finalize-state.sh` via `restore-finalize-state.sh` from that minimal state. Align `review-implement-step5-loop.md:17` with whichever mechanism is chosen.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] **Verified positives (scout checklist):** `skills/implement/SKILL.md:1214` contains “Retain STALL_TRACKING from the parsed envelope above”, assigns it back to the orchestrator variable, and documents conditional `ship-pr-state.sh` key-based rewrite; the literal `Set STALL_TRACKING=true` sentence is gone repo-wide in `SKILL.md`. `mav-resume-past-cap` at `skills/implement/SKILL.md:1265` is unchanged. Bash layer correctly emits `STALL_TRACKING=false` for `starting-round-invalid` (`skills/review-and-fix/scripts/review-implement-step5-loop.sh:115`).
- **Reviewer**: dyn-stall-tracking-propagation-output.txt
- **Concern**: - **Verified positives (scout checklist):** `skills/implement/SKILL.md:1214` contains “Retain STALL_TRACKING from the parsed envelope above”, assigns it back to the orchestrator variable, and documents conditional `ship-pr-state.sh` key-based rewrite; the literal `Set STALL_TRACKING=true` sentence is gone repo-wide in `SKILL.md`. `mav-resume-past-cap` at `skills/implement/SKILL.md:1265` is unchanged. Bash layer correctly emits `STALL_TRACKING=false` for `starting-round-invalid` (`skills/review-and-fix/scripts/review-implement-step5-loop.sh:115`).
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] **Pre-existing:** Step 18 always invokes `implement-finalize.sh teardown` with `finalize-state.sh` even when neither `ship-pr-state.sh` nor `finalize-state.sh` exists (`skills/implement/SKILL.md:1815-1817`; `scripts/implement-finalize.sh:121` requires a readable state file). Early bail / Step-5-stall paths share this fragility; not introduced by the loop changes alone.
- **Reviewer**: dyn-stall-tracking-propagation-output.txt
- **Concern**: - **Pre-existing:** Step 18 always invokes `implement-finalize.sh teardown` with `finalize-state.sh` even when neither `ship-pr-state.sh` nor `finalize-state.sh` exists (`skills/implement/SKILL.md:1815-1817`; `scripts/implement-finalize.sh:121` requires a readable state file). Early bail / Step-5-stall paths share this fragility; not introduced by the loop changes alone.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] **`write-final-report.sh`:** With no `ship-pr-state.sh`, `STALL_TRACKING` defaults to `false` and outcome is usually `bailed`, not `stalled` (`skills/implement/scripts/write-final-report.sh:88-99,127-144`) — aligned with desired reporting for `starting-round-invalid`, independent of teardown rename.
- **Reviewer**: dyn-stall-tracking-propagation-output.txt
- **Concern**: - **`write-final-report.sh`:** With no `ship-pr-state.sh`, `STALL_TRACKING` defaults to `false` and outcome is usually `bailed`, not `stalled` (`skills/implement/scripts/write-final-report.sh:88-99,127-144`) — aligned with desired reporting for `starting-round-invalid`, independent of teardown rename.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] **No regression harness** exercises orchestrator Step 5 stall → Step 16 → Step 18 propagation of `STALL_TRACKING`; coverage is limited to loop envelope tests in `skills/review-and-fix/scripts/test-review-and-fix.sh`.
- **Reviewer**: dyn-stall-tracking-propagation-output.txt
- **Concern**: - **No regression harness** exercises orchestrator Step 5 stall → Step 16 → Step 18 propagation of `STALL_TRACKING`; coverage is limited to loop envelope tests in `skills/review-and-fix/scripts/test-review-and-fix.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_31: **risk-integration** `skills/review-and-fix/scripts/test-review-and-fix.sh:2006,2197-2203,2361-2368` — `step5_original_count_prior_degraded_rounds` is only created in the `parsers` block via `eval "$(declare -f count_prior_degraded_rounds | …)"`, but that block sources only `review-implement-step5-loop.sh` and never `scripts/lib-implement-round-cap.sh`, so `count_prior_degraded_rounds` is not defined when `parsers` runs (including `--section parsers` alone). The `step5-starting-round` block references `step5_original_count_prior_degraded_rounds` in the `entry-nonnumeric` override’s `else` branch but never defines it itself. Case 8 (`STARTING_ROUND=1`) masks this because production code exits on the first bogus entry call and never reaches the fallback; the Makefile/CI shard runs `--section step5-starting-round` without `parsers`, so the fallback path is both untested and broken if ever exercised. **Suggested fix:** After sourcing `lib-implement-round-cap.sh` in the `step5-starting-round` block (around 2098–2101), add the same `eval "$(declare -f count_prior_degraded_rounds | sed '1s/count_prior_degraded_rounds/step5_original_count_prior_degraded_rounds/')"` there (or call `count_prior_degraded_rounds` from lib directly in the `else` branch). Optionally remove or relocate the parsers-line alias so shard order is not load-bearing.
- **Reviewer**: dyn-test-isolation-output.txt
- **Concern**: - **risk-integration** `skills/review-and-fix/scripts/test-review-and-fix.sh:2006,2197-2203,2361-2368` — `step5_original_count_prior_degraded_rounds` is only created in the `parsers` block via `eval "$(declare -f count_prior_degraded_rounds | …)"`, but that block sources only `review-implement-step5-loop.sh` and never `scripts/lib-implement-round-cap.sh`, so `count_prior_degraded_rounds` is not defined when `parsers` runs (including `--section parsers` alone). The `step5-starting-round` block references `step5_original_count_prior_degraded_rounds` in the `entry-nonnumeric` override’s `else` branch but never defines it itself. Case 8 (`STARTING_ROUND=1`) masks this because production code exits on the first bogus entry call and never reaches the fallback; the Makefile/CI shard runs `--section step5-starting-round` without `parsers`, so the fallback path is both untested and broken if ever exercised. **Suggested fix:** After sourcing `lib-implement-round-cap.sh` in the `step5-starting-round` block (around 2098–2101), add the same `eval "$(declare -f count_prior_degraded_rounds | sed '1s/count_prior_degraded_rounds/step5_original_count_prior_degraded_rounds/')"` there (or call `count_prior_degraded_rounds` from lib directly in the `else` branch). Optionally remove or relocate the parsers-line alias so shard order is not load-bearing.
- **Suggested revision**: Address the concern above.

### FINDING_32: **risk-integration** `skills/review-and-fix/scripts/test-review-and-fix.sh:2265-2279` — Case 1b (`retry-sees-prewritten-prior`) starts a background subshell (`sleep 0.1` then `cp` into `round-4`) with `&` but never `wait`s on it. The test relies on that job finishing during the subshell’s `sleep-only` sync (`sleep 0.2` at 2217–2218) before the second artifact probe. Under scheduler delay this can flake false-fail; the orphan job can also outlive the assertion window (usually harmless because case dirs are unique, but it weakens isolation guarantees). **Suggested fix:** `wait` on the background PID immediately after `step5_run_loop_case` returns (or pre-create `round-4/review-and-fix.env` before invoking the loop and use sync only to exercise ordering, matching Case 1’s deterministic `create-prior` pattern).
- **Reviewer**: dyn-test-isolation-output.txt
- **Concern**: - **risk-integration** `skills/review-and-fix/scripts/test-review-and-fix.sh:2265-2279` — Case 1b (`retry-sees-prewritten-prior`) starts a background subshell (`sleep 0.1` then `cp` into `round-4`) with `&` but never `wait`s on it. The test relies on that job finishing during the subshell’s `sleep-only` sync (`sleep 0.2` at 2217–2218) before the second artifact probe. Under scheduler delay this can flake false-fail; the orphan job can also outlive the assertion window (usually harmless because case dirs are unique, but it weakens isolation guarantees). **Suggested fix:** `wait` on the background PID immediately after `step5_run_loop_case` returns (or pre-create `round-4/review-and-fix.env` before invoking the loop and use sync only to exercise ordering, matching Case 1’s deterministic `create-prior` pattern).
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-test-isolation-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/test-review-and-fix.sh:2197-2204` — The `entry-nonnumeric` stub returns `bogus` whenever `$2 == $STARTING_ROUND`, so any future case with `STARTING_ROUND>1` would poison the first in-loop `count_prior_degraded_rounds` call as well as the entry call. Case 8 correctly uses `STARTING_ROUND=1`; not a regression from this branch’s scope, but it limits extending that mode.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-test-isolation-output.txt
- **Concern**: - **architecture** Plan called for lifting `write_prior_round` to file scope (FINDING_33); the branch instead adds a separate `step5_write_prior_round` inside `step5-starting-round` only (`2103-2107`), which avoids leakage with convergence’s different `write_prior_round` signature (`1285+`) but does not match the plan’s shared-helper intent.
- **Suggested revision**: Address the concern above.

