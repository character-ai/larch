### FINDING_1: code-quality: skills/design/SKILL.md:856-877
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Orchestrator gates .step3-review-result.env on rc==0 but driver exit 1 still writes the file On HARD write-cursor failure the driver writes a full result env and exits 1; SKILL skips the file and parses only partial stdout KVs, diverging from the documented file-first handoff and breaking if a future change stops emitting stdout on exit 1 Read result env whenever present and non-symlink regardless of rc; use rc only for exit-2 abort and missing-status fallbacks
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: skills/design/SKILL.md:856-884
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No harness exercises the Step 3 orchestrator fence that sources .step3-review-result.env only when _plan_review_rc=0 with stdout fallback. A future driver exit-code or allowlist change could leave LOOP_STATUS unset in the orchestrator while driver unit tests still pass, misrouting Gate B / Step 3b. Add a hermetic fence-integration harness stubbing run-step3-review.sh to assert rc=0 file sourcing, symlink/missing-file fallback, and panel-failed default.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: skills/design/scripts/test-run-step3-review.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Outer symlink refusal for .step3-review-result.env (documented exit 1) is untested. A symlinked outer result env could regress to silent overwrite or wrong exit semantics without CI signal. Add a test ln -s the result path expect exit 1 WARN and no target mutation.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: skills/design/scripts/test-run-step3-review.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] test-design-multi-round-integration.sh still bypasses run-step3-review.sh so the new driver boundary lacks cross-script integration coverage. Cap guard round-count or cursor-advance regressions could slip past driver unit tests and the existing multi-round harness. Add one integration case routing through run-step3-review.sh with a stubbed inner loop.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/design/scripts/test-lib-phase-driver.sh:103-111
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] read_result_env negative allowlist filtering is not asserted. A regression could leak non-allowlisted keys from a tampered inner result env into normalization. Write a fixture with extra keys and assert only allowlisted keys are emitted.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/design/scripts/test-run-step3-review.sh:374-380
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Invalid --convergence-threshold argv path is untested though invalid --round-cap is covered. Negative or non-numeric convergence threshold could stop normalizing to panel-failed without CI detection. Add symmetric invalid --convergence-threshold case expecting panel-failed in stdout and result env.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: skills/design/SKILL.md:856-884
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Driver exit 1 on symlink refusal to write .step3-review-result.env skips terminal emit_kv; orchestrator only sources result env on rc==0 and defaults LOOP_STATUS=panel-failed. Successful plan-review-loop completes but normalized result env is a symlink; driver exits 1 without LOOP_STATUS on stdout; orchestrator treats run as panel-failed and skips Gate B despite a good panel. Emit full KV breadcrumbs before exit 1 on write refusal; and/or source non-symlink .step3-review-result.env when present regardless of rc (except rc==2).
- **Suggested revision**: Address the concern above.


### FINDING_26: architecture: skills/design/SKILL.md:856-877
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] rc==0 gate makes file-first contract depend on quiet stdout capture for exit 1 handoffs. Cursor write-cursor failure writes a correct .step3-review-result.env but orchestrator ignores it; if quiet init/routing changes, orchestrator loses round/cap KVs while file is correct. Source allowlisted keys from non-symlink result env whenever present; use stdout only to fill missing keys.
- **Suggested revision**: Address the concern above.


### FINDING_27: correctness: skills/design/scripts/run-step3-review.sh:143-157
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Pending round persisted before HARD read-cursor; read-cursor failure aborts without rollback. read-cursor subprocess fails after review-round-count.txt bumped; next Gate C re-entry sees consumed slot without review artifacts. Persist after cursor advance succeeds or rollback to _step3_prior_round_count on read-cursor failure.
- **Suggested revision**: Address the concern above.


### FINDING_28: risk-integration: skills/design/scripts/test-run-step3-review.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit]  No regression test for symlinked outer .step3-review-result.env after successful loop. Refactor can reintroduce silent mis-routing without CI signal. Add harness case for symlinked outer result env and expected driver/orchestrator status.
- **Suggested revision**: Address the concern above.


### FINDING_30: correctness: skills/design/SKILL.md:856-867
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 3 gates sourcing .step3-review-result.env on _plan_review_rc==0 even though run-step3-review.sh exit 1 writes that file per run-step3-review.md and test-run-step3-review.sh. On write-cursor failure the driver exits 1 after writing panel-failed into .step3-review-result.env; SKILL skips the file and uses stdout fallback only, conflicting with file-first branch-matrix prose and risking lost KVs if quiet capture fails. Source .step3-review-result.env whenever the file exists and is not a symlink; reserve rc==2 for config abort, or document and test stdout-only handoff explicitly.
- **Suggested revision**: Address the concern above.


### FINDING_31: correctness: skills/design/SKILL.md:849-884
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan edge case requires preserving inline exit 1 on HARD cursor advance failure; driver exits 1 but orchestrator continues into panel-failed short-circuit. Operators expecting a hard Step 3 fence abort on cursor failure get soft continuation instead of the pre-refactor exit 1 stop. Reconcile plan, run-step3-review.md, and SKILL.md on abort vs panel-failed handoff; add a structure pin for the chosen behavior.
- **Suggested revision**: Address the concern above.


### FINDING_33: **correctness** `skills/design/SKILL.md:849-877` — The refactor drops the two `WARN) printf '%s\n' "WARN=$_value"` branches that used to run after reading `.step3-plan-review-result.env` and after parsing `_plan_review_out`. The new fence only assigns orchestrator variables for the normalized KV allow-list and never re-emits `WARN` lines. Because `run-step3-review.sh` is invoked inside `_plan_review_out=$(...)`, driver `emit` / `emit_kv` output (including re-emitted loop WARNs at `skills/design/scripts/run-step3-review.sh:127-136,219-233,243` and cap breadcrumbs at `100-101`) is captured into `_plan_review_out` instead of reaching the user terminal under `larch_quiet_init`. Pre-refactor, env-file WARN were printed directly in the fence (outside substitution) and stdout WARN were explicitly re-printed from `_plan_review_out`; post-refactor those warnings are silently dropped whenever `LOOP_STATUS` is populated from `.step3-review-result.env` (the common rc=0 path). **Suggested fix:** Restore WARN pass-through in the SKILL fence (e.g. `WARN) printf '%s\n' "WARN=$_value" ;;` when sourcing `.step3-review-result.env` if WARN keys are ever persisted there, and always when scanning `_plan_review_out`), or stop wrapping the driver in command substitution and parse its contract stdout after a foreground invocation (mirroring `run-step2-dispatch.sh` in `skills/implement/SKILL.md:722-725`).
- **Reviewer**: dyn-behavioral-equivalence-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:849-877` — The refactor drops the two `WARN) printf '%s\n' "WARN=$_value"` branches that used to run after reading `.step3-plan-review-result.env` and after parsing `_plan_review_out`. The new fence only assigns orchestrator variables for the normalized KV allow-list and never re-emits `WARN` lines. Because `run-step3-review.sh` is invoked inside `_plan_review_out=$(...)`, driver `emit` / `emit_kv` output (including re-emitted loop WARNs at `skills/design/scripts/run-step3-review.sh:127-136,219-233,243` and cap breadcrumbs at `100-101`) is captured into `_plan_review_out` instead of reaching the user terminal under `larch_quiet_init`. Pre-refactor, env-file WARN were printed directly in the fence (outside substitution) and stdout WARN were explicitly re-printed from `_plan_review_out`; post-refactor those warnings are silently dropped whenever `LOOP_STATUS` is populated from `.step3-review-result.env` (the common rc=0 path). **Suggested fix:** Restore WARN pass-through in the SKILL fence (e.g. `WARN) printf '%s\n' "WARN=$_value" ;;` when sourcing `.step3-review-result.env` if WARN keys are ever persisted there, and always when scanning `_plan_review_out`), or stop wrapping the driver in command substitution and parse its contract stdout after a foreground invocation (mirroring `run-step2-dispatch.sh` in `skills/implement/SKILL.md:722-725`).
- **Suggested revision**: Address the concern above.


### FINDING_38: **security** `skills/design/scripts/run-step3-review.sh:221-224` — Round 3 replaced the pre-refactor `case "$_key" in …)` guard (present in the initial extract at `b9806b39d` and in main-branch `SKILL.md` for the same inner-env read) with a bare `printf -v "$_key"` over lines parsed from `phase_driver_read_result_env` stdout. Allowlist filtering happens only inside `phase_driver_read_result_env` when reading the file; the consumer loop does not re-check keys. Because `phase_driver_read_result_env` re-emits values with `printf '%s=%s\n'` and does not reject embedded newlines, a multiline allowlisted value (e.g. `REASON=line1\nPATH=/evil`, writable via `plan-review-loop.sh`'s unguarded `printf 'REASON=%s\n'` in `write_step3_result_env` or by a same-UID writer of `$DESIGN_TMPDIR/.step3-plan-review-result.env`) splits into extra physical lines that bypass the allowlist and reach `printf -v` with attacker-chosen names, including bash-sensitive variables (`PATH`, `BASH_ENV`, `arr[0]`, etc.). The adjacent stdout-fallback path at `239-241` and the orchestrator fence in `skills/design/SKILL.md:862-865` still use a `case` allowlist; only this inner-env path regressed. **Suggested fix:** Restore the explicit `case "$_key" in …)` allowlist (matching the stdout-fallback block) before every `printf -v` at `221-224`, and harden `phase_driver_read_result_env` to refuse or strip values containing `\n`/`\r` (mirroring `emit_kv` in `scripts/lib-quiet.sh:166-172`) so the line-oriented KV protocol cannot be broken by multiline spill.
- **Reviewer**: dyn-allowlist-variable-injection-output.txt
- **Concern**: - **security** `skills/design/scripts/run-step3-review.sh:221-224` — Round 3 replaced the pre-refactor `case "$_key" in …)` guard (present in the initial extract at `b9806b39d` and in main-branch `SKILL.md` for the same inner-env read) with a bare `printf -v "$_key"` over lines parsed from `phase_driver_read_result_env` stdout. Allowlist filtering happens only inside `phase_driver_read_result_env` when reading the file; the consumer loop does not re-check keys. Because `phase_driver_read_result_env` re-emits values with `printf '%s=%s\n'` and does not reject embedded newlines, a multiline allowlisted value (e.g. `REASON=line1\nPATH=/evil`, writable via `plan-review-loop.sh`'s unguarded `printf 'REASON=%s\n'` in `write_step3_result_env` or by a same-UID writer of `$DESIGN_TMPDIR/.step3-plan-review-result.env`) splits into extra physical lines that bypass the allowlist and reach `printf -v` with attacker-chosen names, including bash-sensitive variables (`PATH`, `BASH_ENV`, `arr[0]`, etc.). The adjacent stdout-fallback path at `239-241` and the orchestrator fence in `skills/design/SKILL.md:862-865` still use a `case` allowlist; only this inner-env path regressed. **Suggested fix:** Restore the explicit `case "$_key" in …)` allowlist (matching the stdout-fallback block) before every `printf -v` at `221-224`, and harden `phase_driver_read_result_env` to refuse or strip values containing `\n`/`\r` (mirroring `emit_kv` in `scripts/lib-quiet.sh:166-172`) so the line-oriented KV protocol cannot be broken by multiline spill.
- **Suggested revision**: Address the concern above.


### FINDING_39: **security** `skills/design/scripts/lib-phase-driver.sh:67-76` — `phase_driver_read_result_env` splits on the first `=`, matches keys against the caller allowlist, then re-emits `key=value` lines without validating that `value` is single-line. Any embedded newline in an allowlisted value produces additional stdout lines that downstream consumers treat as independent KVs; combined with the missing re-allowlist at `run-step3-review.sh:221-224`, this is the enabling primitive for indirect variable assignment injection. **Suggested fix:** Before emitting, reject lines whose value contains newline/carriage return (return failure or skip the line with `larch_err`), or emit via an encoding that cannot spill (e.g. base64) and decode only after allowlist confirmation; add a harness case in `test-lib-phase-driver.sh` for multiline rejection.
- **Reviewer**: dyn-allowlist-variable-injection-output.txt
- **Concern**: - **security** `skills/design/scripts/lib-phase-driver.sh:67-76` — `phase_driver_read_result_env` splits on the first `=`, matches keys against the caller allowlist, then re-emits `key=value` lines without validating that `value` is single-line. Any embedded newline in an allowlisted value produces additional stdout lines that downstream consumers treat as independent KVs; combined with the missing re-allowlist at `run-step3-review.sh:221-224`, this is the enabling primitive for indirect variable assignment injection. **Suggested fix:** Before emitting, reject lines whose value contains newline/carriage return (return failure or skip the line with `larch_err`), or emit via an encoding that cannot spill (e.g. base64) and decode only after allowlist confirmation; add a harness case in `test-lib-phase-driver.sh` for multiline rejection.
- **Suggested revision**: Address the concern above.


### FINDING_42: **correctness** `skills/design/scripts/run-step3-review.sh:139-283` + `skills/design/SKILL.md:856-884` — On the cap-reached path the driver sets `LOOP_STATUS=cap-reached` and writes `.step3-review-cap.env`, then calls `phase_driver_write_result_env` for `.step3-review-result.env` and **exits 1** if that path is a symlink (lines 268–282) **without** emitting `emit_kv LOOP_STATUS=…` first (contrast the HARD cursor-failure handoff at lines 169–185, which writes the result env, emits KVs, then exits 1). The orchestrator only sources `.step3-review-result.env` when `_plan_review_rc==0` (SKILL.md:856), and the cap branch never prints `LOOP_STATUS=cap-reached` to stdout—only `emit` prose (run-step3-review.sh:100–101). So a symlinked `.step3-review-result.env` turns a successful cap guard into `LOOP_STATUS=panel-failed` (SKILL.md:881–883), skipping the cap-reached → Step 3b short-circuit and risking Gate B with stale findings. **Suggested fix:** Emit the normalized `emit_kv` breadcrumbs (at least `LOOP_STATUS` and `TALLY_PLAN_REVIEW_STATUS`) **before** `phase_driver_write_result_env`, on every exit path including cap-reached; or treat a refused symlink write as a non-fatal WARN, emit KVs, and exit 0 when `LOOP_STATUS` is already `cap-reached`. Add a harness case mirroring `test-lib-phase-driver.sh`’s symlink refusal but with `review-round-count.txt` at cap and assert stdout/orchestrator-visible `LOOP_STATUS=cap-reached`, not `panel-failed`.
- **Reviewer**: dyn-cap-path-roundcleanup-ordering-output.txt
- **Concern**: - **correctness** `skills/design/scripts/run-step3-review.sh:139-283` + `skills/design/SKILL.md:856-884` — On the cap-reached path the driver sets `LOOP_STATUS=cap-reached` and writes `.step3-review-cap.env`, then calls `phase_driver_write_result_env` for `.step3-review-result.env` and **exits 1** if that path is a symlink (lines 268–282) **without** emitting `emit_kv LOOP_STATUS=…` first (contrast the HARD cursor-failure handoff at lines 169–185, which writes the result env, emits KVs, then exits 1). The orchestrator only sources `.step3-review-result.env` when `_plan_review_rc==0` (SKILL.md:856), and the cap branch never prints `LOOP_STATUS=cap-reached` to stdout—only `emit` prose (run-step3-review.sh:100–101). So a symlinked `.step3-review-result.env` turns a successful cap guard into `LOOP_STATUS=panel-failed` (SKILL.md:881–883), skipping the cap-reached → Step 3b short-circuit and risking Gate B with stale findings. **Suggested fix:** Emit the normalized `emit_kv` breadcrumbs (at least `LOOP_STATUS` and `TALLY_PLAN_REVIEW_STATUS`) **before** `phase_driver_write_result_env`, on every exit path including cap-reached; or treat a refused symlink write as a non-fatal WARN, emit KVs, and exit 0 when `LOOP_STATUS` is already `cap-reached`. Add a harness case mirroring `test-lib-phase-driver.sh`’s symlink refusal but with `review-round-count.txt` at cap and assert stdout/orchestrator-visible `LOOP_STATUS=cap-reached`, not `panel-failed`.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/design/SKILL.md:856-867
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] SKILL loads result env only when driver rc==0 but driver exits 1 after writing cursor-failure handoff Quiet/substitution failure drops on-disk KVs; orchestrator only gets generic panel-failed fallback Read result env on rc==1 when file exists or use exit 0 for documented handoff statuses
- **Suggested revision**: Address the concern above.


