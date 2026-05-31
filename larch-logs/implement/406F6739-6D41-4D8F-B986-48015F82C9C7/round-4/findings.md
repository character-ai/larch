### FINDING_1: code-quality: skills/design/SKILL.md:856-877
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Orchestrator gates .step3-review-result.env on rc==0 but driver exit 1 still writes the file On HARD write-cursor failure the driver writes a full result env and exits 1; SKILL skips the file and parses only partial stdout KVs, diverging from the documented file-first handoff and breaking if a future change stops emitting stdout on exit 1 Read result env whenever present and non-symlink regardless of rc; use rc only for exit-2 abort and missing-status fallbacks
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/scripts/run-step3-review.sh:169-185,268-296
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated result-env write and emit_kv breadcrumb blocks Cursor-failure and success paths maintain parallel copies of the same key list; a key added to one path can be omitted from the other Extract a finalize_step3_result helper that writes env emits full breadcrumbs and exits
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/test-plan-review-loop.sh:1509-1543
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unrelated collector-stderr regression added in Step 3 PR Reviewers must validate plan-review-loop behavior unrelated to run-step3-review extraction increasing PR scope and review noise Split the collector-stderr test into its own commit or PR
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/scripts/run-step3-review.sh:104-115,268-280
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] .step3-review-cap.env is written but no longer consumed by SKILL.md Cap state is duplicated across two files while only .step3-review-result.env is read; cap file purpose is unclear to future driver authors Document cap env as forensic-only or stop writing it if result env is canonical
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/run-step2-dispatch.sh:15-23
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] session_get duplicates new phase_driver_session_get Pre-existing duplication not introduced by this branch; lib foundation not yet adopted by implement stack Refactor run-step2-dispatch to source lib-phase-driver.sh when next implement driver lands
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: skills/design/references/approval-gates.md:90-100
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Gate B still normatively reads .step3-plan-review-result.env while Step 3 handoff uses .step3-review-result.env On cap-reached re-entry stale inner env can say converged while driver wrote cap-reached only to normalized env; agent following approval-gates may enter passive-summary/Gate B incorrectly Update approval-gates.md and test-design-structure.sh pin 931 to prefer .step3-review-result.env for LOOP_STATUS; keep inner env loop-internal
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/design/SKILL.md:856-867
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] SKILL loads result env only when driver rc==0 but driver exits 1 after writing cursor-failure handoff Quiet/substitution failure drops on-disk KVs; orchestrator only gets generic panel-failed fallback Read result env on rc==1 when file exists or use exit 0 for documented handoff statuses
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/design/scripts/run-step3-review.sh:202-203
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] CODEX_PRESENT/CURSOR_PRESENT default false when empty string unlike prior bare pass Empty session env previously argv-exit 2 panel-failed; now false may change external panel composition Pass bare vars or reject empty string before loop invoke
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] correctness: skills/design/SKILL.md:826
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Cap prose omits degraded-empty-collector rollback mention Misleading doc only; driver and branch matrix handle degraded path Add degraded-empty-collector to cap-guard prose for parity with driver
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] risk-integration: scripts/test-design-structure.sh:931
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Harness pins approval-gates to old inner-env-only MainAgent wording Blocks fixing approval-gates drift without harness change Update pin when approval-gates.md is aligned
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

### FINDING_14: risk-integration: skills/design/scripts/test-run-step3-review.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No spy test verifies CODEX_PRESENT/CURSOR_PRESENT forwarding to plan-review-loop argv. Dropping --codex-present/--cursor-present from the driver would not fail CI despite breaking external panel dispatch. Add a stub loop that logs argv and assert the four presence flags are forwarded.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/design/scripts/test-lib-phase-driver.sh:103-111
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] read_result_env negative allowlist filtering is not asserted. A regression could leak non-allowlisted keys from a tampered inner result env into normalization. Write a fixture with extra keys and assert only allowlisted keys are emitted.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/design/scripts/test-run-step3-review.sh:374-380
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Invalid --convergence-threshold argv path is untested though invalid --round-cap is covered. Negative or non-numeric convergence threshold could stop normalizing to panel-failed without CI detection. Add symmetric invalid --convergence-threshold case expecting panel-failed in stdout and result env.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] risk-integration: skills/design/references/plan-review.md:48
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Caller prose still names SKILL.md Step 3 directly instead of run-step3-review.sh. Doc drift only; not introduced by this diff’s stated doc-sync scope. Update when doing a broader design doc pass.
- **Suggested revision**: Address the concern above.

### FINDING_18: Removed orchestrator `source` of `.step3-review-cap.env` (previously executable if tampered).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Removed orchestrator `source` of `.step3-review-cap.env` (previously executable if tampered).
- **Suggested revision**: Address the concern above.

### FINDING_19: Orchestrator now uses **allowlisted** `printf -v` reads from `.step3-review-result.env`, with symlink refusal.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Orchestrator now uses **allowlisted** `printf -v` reads from `.step3-review-result.env`, with symlink refusal.
- **Suggested revision**: Address the concern above.

### FINDING_20: Driver preserves symlink-safe `plan-review/round-*` cleanup and extends the same pattern to `.step3-review-result.env` writes via `phase_driver_write_result_env`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Driver preserves symlink-safe `plan-review/round-*` cleanup and extends the same pattern to `.step3-review-result.env` writes via `phase_driver_write_result_env`.
- **Suggested revision**: Address the concern above.

### FINDING_21: `SECURITY.md` documents the new normalized result env alongside the inner loop env.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `SECURITY.md` documents the new normalized result env alongside the inner loop env.
- **Suggested revision**: Address the concern above.

### FINDING_22: `LOOP_STATUS` normalization stays in deterministic Bash with a closed allow-list before handoff.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `LOOP_STATUS` normalization stays in deterministic Bash with a closed allow-list before handoff. Argv handling uses a case dispatch (no `eval`). Inner loop and snapshot scripts are invoked as quoted argv arrays. Test-only `RUN_STEP3_*` overrides mirror the established `RUN_STEP2_IMPLEMENT_SH` pattern from `run-step2-dispatch.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/design/scripts/run-step3-review.sh:154-191` — `RUN_STEP3_PLAN_REVIEW_LOOP_SH` and `RUN_STEP3_SNAPSHOT_PLAN_ROUND_SH` allow overriding which executables run, without constraining paths to `PLUGIN_ROOT`. This matches the existing Step 2 dispatcher test-injection pattern and sits inside larch’s same-UID trust model; a same-UID writer who could poison these env vars could already tamper with session artifacts or skill prompts. **Why out of scope:** convention is pre-established elsewhere; residual risk is unchanged in kind, only the Step 3 surface is new.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/design/scripts/run-step3-review.sh:104-115,146-147` — Writes to `.step3-review-cap.env` and `review-round-count.txt` do not refuse symlink targets (unlike `.step3-review-result.env`). **Why out of scope:** behavior is ported from pre-refactor inline Step 3; impact is reduced because the orchestrator no longer `source`s the cap env file. --- **Verdict:** From a security/trust-boundary lens, this branch is sound. Symlink guards, allowlisted KV parsing, and removal of `source` on session artifacts are the right direction; no new exploitable cross-boundary paths were identified under larch’s documented same-UID model.
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

### FINDING_29: [OUT_OF_SCOPE] correctness: skills/design/scripts/run-step3-review.sh:121-137
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Cap-reached path still deletes plan-review/round-* artifacts before skipping loop. Pre-existing; cap hit on 3rd/5th review run wipes round forensics operators might expect to keep. Consider skipping cleanup when STEP3_REVIEW_CAP_REACHED=true (future change).
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: skills/design/SKILL.md:856-867
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 3 gates sourcing .step3-review-result.env on _plan_review_rc==0 even though run-step3-review.sh exit 1 writes that file per run-step3-review.md and test-run-step3-review.sh. On write-cursor failure the driver exits 1 after writing panel-failed into .step3-review-result.env; SKILL skips the file and uses stdout fallback only, conflicting with file-first branch-matrix prose and risking lost KVs if quiet capture fails. Source .step3-review-result.env whenever the file exists and is not a symlink; reserve rc==2 for config abort, or document and test stdout-only handoff explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: skills/design/SKILL.md:849-884
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan edge case requires preserving inline exit 1 on HARD cursor advance failure; driver exits 1 but orchestrator continues into panel-failed short-circuit. Operators expecting a hard Step 3 fence abort on cursor failure get soft continuation instead of the pre-refactor exit 1 stop. Reconcile plan, run-step3-review.md, and SKILL.md on abort vs panel-failed handoff; add a structure pin for the chosen behavior.
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: skills/design/scripts/test-lib-phase-driver.sh:92-95
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan requires write_result_env atomicity tests; harness only checks final contents and symlink refusal. Atomic write regressions in lib-phase-driver.sh would not be caught by CI. Add a targeted atomicity assertion for the mktemp+mv path or drop atomicity from the contract if untestable.
- **Suggested revision**: Address the concern above.

### FINDING_33: **correctness** `skills/design/SKILL.md:849-877` — The refactor drops the two `WARN) printf '%s\n' "WARN=$_value"` branches that used to run after reading `.step3-plan-review-result.env` and after parsing `_plan_review_out`. The new fence only assigns orchestrator variables for the normalized KV allow-list and never re-emits `WARN` lines. Because `run-step3-review.sh` is invoked inside `_plan_review_out=$(...)`, driver `emit` / `emit_kv` output (including re-emitted loop WARNs at `skills/design/scripts/run-step3-review.sh:127-136,219-233,243` and cap breadcrumbs at `100-101`) is captured into `_plan_review_out` instead of reaching the user terminal under `larch_quiet_init`. Pre-refactor, env-file WARN were printed directly in the fence (outside substitution) and stdout WARN were explicitly re-printed from `_plan_review_out`; post-refactor those warnings are silently dropped whenever `LOOP_STATUS` is populated from `.step3-review-result.env` (the common rc=0 path). **Suggested fix:** Restore WARN pass-through in the SKILL fence (e.g. `WARN) printf '%s\n' "WARN=$_value" ;;` when sourcing `.step3-review-result.env` if WARN keys are ever persisted there, and always when scanning `_plan_review_out`), or stop wrapping the driver in command substitution and parse its contract stdout after a foreground invocation (mirroring `run-step2-dispatch.sh` in `skills/implement/SKILL.md:722-725`).
- **Reviewer**: dyn-behavioral-equivalence-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:849-877` — The refactor drops the two `WARN) printf '%s\n' "WARN=$_value"` branches that used to run after reading `.step3-plan-review-result.env` and after parsing `_plan_review_out`. The new fence only assigns orchestrator variables for the normalized KV allow-list and never re-emits `WARN` lines. Because `run-step3-review.sh` is invoked inside `_plan_review_out=$(...)`, driver `emit` / `emit_kv` output (including re-emitted loop WARNs at `skills/design/scripts/run-step3-review.sh:127-136,219-233,243` and cap breadcrumbs at `100-101`) is captured into `_plan_review_out` instead of reaching the user terminal under `larch_quiet_init`. Pre-refactor, env-file WARN were printed directly in the fence (outside substitution) and stdout WARN were explicitly re-printed from `_plan_review_out`; post-refactor those warnings are silently dropped whenever `LOOP_STATUS` is populated from `.step3-review-result.env` (the common rc=0 path). **Suggested fix:** Restore WARN pass-through in the SKILL fence (e.g. `WARN) printf '%s\n' "WARN=$_value" ;;` when sourcing `.step3-review-result.env` if WARN keys are ever persisted there, and always when scanning `_plan_review_out`), or stop wrapping the driver in command substitution and parse its contract stdout after a foreground invocation (mirroring `run-step2-dispatch.sh` in `skills/implement/SKILL.md:722-725`).
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] **Persist/rollback** — `run-step3-review.sh:254-264` matches the removed SKILL logic (`tally-error` via `TALLY_PLAN_REVIEW_STATUS` or `LOOP_STATUS`, plus `degraded-empty-collector`; rollback to `_step3_prior_round_count`; otherwise keep `STEP3_REVIEW_ROUND_NUM`). The driver also updates `REVIEW_ROUND_COUNT` on rollback (new breadcrumb only).
- **Reviewer**: dyn-behavioral-equivalence-output.txt
- **Concern**: - **Persist/rollback** — `run-step3-review.sh:254-264` matches the removed SKILL logic (`tally-error` via `TALLY_PLAN_REVIEW_STATUS` or `LOOP_STATUS`, plus `degraded-empty-collector`; rollback to `_step3_prior_round_count`; otherwise keep `STEP3_REVIEW_ROUND_NUM`). The driver also updates `REVIEW_ROUND_COUNT` on rollback (new breadcrumb only).
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] **LOOP_STATUS normalization** — The allow-list regex at `run-step3-review.sh:247-250` is the same as the removed fence; `skills/design/SKILL.md:881-884` still supplies a second `panel-failed` fallback only when `LOOP_STATUS` is empty after sourcing / stdout parse. Symlink-inner-env and stdout-only paths are handled inside the driver before writing `.step3-review-result.env`.
- **Reviewer**: dyn-behavioral-equivalence-output.txt
- **Concern**: - **LOOP_STATUS normalization** — The allow-list regex at `run-step3-review.sh:247-250` is the same as the removed fence; `skills/design/SKILL.md:881-884` still supplies a second `panel-failed` fallback only when `LOOP_STATUS` is empty after sourcing / stdout parse. Symlink-inner-env and stdout-only paths are handled inside the driver before writing `.step3-review-result.env`.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] **HARD write-cursor failure** — Behavior intentionally diverges from the old bare `exit 1` (`diff.txt` ~655): the driver now writes `LOOP_STATUS=panel-failed`, leaves the pending round persisted, and exits `1` (`run-step3-review.sh:164-185`), with harness coverage in `test-run-step3-review.sh`. SKILL recovers via stdout when rc≠0 blocks sourcing (`856-877`).
- **Reviewer**: dyn-behavioral-equivalence-output.txt
- **Concern**: - **HARD write-cursor failure** — Behavior intentionally diverges from the old bare `exit 1` (`diff.txt` ~655): the driver now writes `LOOP_STATUS=panel-failed`, leaves the pending round persisted, and exits `1` (`run-step3-review.sh:164-185`), with harness coverage in `test-run-step3-review.sh`. SKILL recovers via stdout when rc≠0 blocks sourcing (`856-877`).
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] **CODEX_PRESENT default** — Driver passes `"${CODEX_PRESENT:-false}"` (`202-203`) vs the old `"$CODEX_PRESENT"`; if session env ever leaves these unset, the old path failed closed in `plan-review-loop.sh` argv validation (exit `2`), while the new path defaults to `false`. Likely benign if Step 0 always sets the flags.
- **Reviewer**: dyn-behavioral-equivalence-output.txt
- **Concern**: - **CODEX_PRESENT default** — Driver passes `"${CODEX_PRESENT:-false}"` (`202-203`) vs the old `"$CODEX_PRESENT"`; if session env ever leaves these unset, the old path failed closed in `plan-review-loop.sh` argv validation (exit `2`), while the new path defaults to `false`. Likely benign if Step 0 always sets the flags.
- **Suggested revision**: Address the concern above.

### FINDING_38: **security** `skills/design/scripts/run-step3-review.sh:221-224` — Round 3 replaced the pre-refactor `case "$_key" in …)` guard (present in the initial extract at `b9806b39d` and in main-branch `SKILL.md` for the same inner-env read) with a bare `printf -v "$_key"` over lines parsed from `phase_driver_read_result_env` stdout. Allowlist filtering happens only inside `phase_driver_read_result_env` when reading the file; the consumer loop does not re-check keys. Because `phase_driver_read_result_env` re-emits values with `printf '%s=%s\n'` and does not reject embedded newlines, a multiline allowlisted value (e.g. `REASON=line1\nPATH=/evil`, writable via `plan-review-loop.sh`'s unguarded `printf 'REASON=%s\n'` in `write_step3_result_env` or by a same-UID writer of `$DESIGN_TMPDIR/.step3-plan-review-result.env`) splits into extra physical lines that bypass the allowlist and reach `printf -v` with attacker-chosen names, including bash-sensitive variables (`PATH`, `BASH_ENV`, `arr[0]`, etc.). The adjacent stdout-fallback path at `239-241` and the orchestrator fence in `skills/design/SKILL.md:862-865` still use a `case` allowlist; only this inner-env path regressed. **Suggested fix:** Restore the explicit `case "$_key" in …)` allowlist (matching the stdout-fallback block) before every `printf -v` at `221-224`, and harden `phase_driver_read_result_env` to refuse or strip values containing `\n`/`\r` (mirroring `emit_kv` in `scripts/lib-quiet.sh:166-172`) so the line-oriented KV protocol cannot be broken by multiline spill.
- **Reviewer**: dyn-allowlist-variable-injection-output.txt
- **Concern**: - **security** `skills/design/scripts/run-step3-review.sh:221-224` — Round 3 replaced the pre-refactor `case "$_key" in …)` guard (present in the initial extract at `b9806b39d` and in main-branch `SKILL.md` for the same inner-env read) with a bare `printf -v "$_key"` over lines parsed from `phase_driver_read_result_env` stdout. Allowlist filtering happens only inside `phase_driver_read_result_env` when reading the file; the consumer loop does not re-check keys. Because `phase_driver_read_result_env` re-emits values with `printf '%s=%s\n'` and does not reject embedded newlines, a multiline allowlisted value (e.g. `REASON=line1\nPATH=/evil`, writable via `plan-review-loop.sh`'s unguarded `printf 'REASON=%s\n'` in `write_step3_result_env` or by a same-UID writer of `$DESIGN_TMPDIR/.step3-plan-review-result.env`) splits into extra physical lines that bypass the allowlist and reach `printf -v` with attacker-chosen names, including bash-sensitive variables (`PATH`, `BASH_ENV`, `arr[0]`, etc.). The adjacent stdout-fallback path at `239-241` and the orchestrator fence in `skills/design/SKILL.md:862-865` still use a `case` allowlist; only this inner-env path regressed. **Suggested fix:** Restore the explicit `case "$_key" in …)` allowlist (matching the stdout-fallback block) before every `printf -v` at `221-224`, and harden `phase_driver_read_result_env` to refuse or strip values containing `\n`/`\r` (mirroring `emit_kv` in `scripts/lib-quiet.sh:166-172`) so the line-oriented KV protocol cannot be broken by multiline spill.
- **Suggested revision**: Address the concern above.

### FINDING_39: **security** `skills/design/scripts/lib-phase-driver.sh:67-76` — `phase_driver_read_result_env` splits on the first `=`, matches keys against the caller allowlist, then re-emits `key=value` lines without validating that `value` is single-line. Any embedded newline in an allowlisted value produces additional stdout lines that downstream consumers treat as independent KVs; combined with the missing re-allowlist at `run-step3-review.sh:221-224`, this is the enabling primitive for indirect variable assignment injection. **Suggested fix:** Before emitting, reject lines whose value contains newline/carriage return (return failure or skip the line with `larch_err`), or emit via an encoding that cannot spill (e.g. base64) and decode only after allowlist confirmation; add a harness case in `test-lib-phase-driver.sh` for multiline rejection.
- **Reviewer**: dyn-allowlist-variable-injection-output.txt
- **Concern**: - **security** `skills/design/scripts/lib-phase-driver.sh:67-76` — `phase_driver_read_result_env` splits on the first `=`, matches keys against the caller allowlist, then re-emits `key=value` lines without validating that `value` is single-line. Any embedded newline in an allowlisted value produces additional stdout lines that downstream consumers treat as independent KVs; combined with the missing re-allowlist at `run-step3-review.sh:221-224`, this is the enabling primitive for indirect variable assignment injection. **Suggested fix:** Before emitting, reject lines whose value contains newline/carriage return (return failure or skip the line with `larch_err`), or emit via an encoding that cannot spill (e.g. base64) and decode only after allowlist confirmation; add a harness case in `test-lib-phase-driver.sh` for multiline rejection.
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-allowlist-variable-injection-output.txt
- **Concern**: - **security** `skills/design/scripts/plan-review-loop.sh:154-173` — `write_step3_result_env` writes inner result keys with raw `printf '%s\n'` and no newline guard, while stdout uses `emit_kv` which rejects multiline values (`scripts/lib-quiet.sh:166-172`). This pre-existing gap is the practical write path for multiline inner-env content; the branch amplifies its impact only because `run-step3-review.sh:221-224` lost the per-line `case` guard that main/`SKILL.md` previously applied.
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-allowlist-variable-injection-output.txt
- **Concern**: - **security** `skills/design/SKILL.md:860-876` — The new orchestrator fence correctly uses a `case` allowlist before each `printf -v` when sourcing `.step3-review-result.env` and stdout fallback; allowlisted keys are intentional orchestrator state (`LOOP_STATUS`, `REVIEW_ROUND_COUNT`, etc.) and exclude bash specials. Residual multiline spill could still set a second allowlisted key (e.g. forged `REVIEW_ROUND_COUNT`) if a tampered result env contained embedded newlines, but driver-written values are regex/numeric constrained, so this is lower risk than the inner-env path above.
- **Suggested revision**: Address the concern above.

### FINDING_42: **correctness** `skills/design/scripts/run-step3-review.sh:139-283` + `skills/design/SKILL.md:856-884` — On the cap-reached path the driver sets `LOOP_STATUS=cap-reached` and writes `.step3-review-cap.env`, then calls `phase_driver_write_result_env` for `.step3-review-result.env` and **exits 1** if that path is a symlink (lines 268–282) **without** emitting `emit_kv LOOP_STATUS=…` first (contrast the HARD cursor-failure handoff at lines 169–185, which writes the result env, emits KVs, then exits 1). The orchestrator only sources `.step3-review-result.env` when `_plan_review_rc==0` (SKILL.md:856), and the cap branch never prints `LOOP_STATUS=cap-reached` to stdout—only `emit` prose (run-step3-review.sh:100–101). So a symlinked `.step3-review-result.env` turns a successful cap guard into `LOOP_STATUS=panel-failed` (SKILL.md:881–883), skipping the cap-reached → Step 3b short-circuit and risking Gate B with stale findings. **Suggested fix:** Emit the normalized `emit_kv` breadcrumbs (at least `LOOP_STATUS` and `TALLY_PLAN_REVIEW_STATUS`) **before** `phase_driver_write_result_env`, on every exit path including cap-reached; or treat a refused symlink write as a non-fatal WARN, emit KVs, and exit 0 when `LOOP_STATUS` is already `cap-reached`. Add a harness case mirroring `test-lib-phase-driver.sh`’s symlink refusal but with `review-round-count.txt` at cap and assert stdout/orchestrator-visible `LOOP_STATUS=cap-reached`, not `panel-failed`.
- **Reviewer**: dyn-cap-path-roundcleanup-ordering-output.txt
- **Concern**: - **correctness** `skills/design/scripts/run-step3-review.sh:139-283` + `skills/design/SKILL.md:856-884` — On the cap-reached path the driver sets `LOOP_STATUS=cap-reached` and writes `.step3-review-cap.env`, then calls `phase_driver_write_result_env` for `.step3-review-result.env` and **exits 1** if that path is a symlink (lines 268–282) **without** emitting `emit_kv LOOP_STATUS=…` first (contrast the HARD cursor-failure handoff at lines 169–185, which writes the result env, emits KVs, then exits 1). The orchestrator only sources `.step3-review-result.env` when `_plan_review_rc==0` (SKILL.md:856), and the cap branch never prints `LOOP_STATUS=cap-reached` to stdout—only `emit` prose (run-step3-review.sh:100–101). So a symlinked `.step3-review-result.env` turns a successful cap guard into `LOOP_STATUS=panel-failed` (SKILL.md:881–883), skipping the cap-reached → Step 3b short-circuit and risking Gate B with stale findings. **Suggested fix:** Emit the normalized `emit_kv` breadcrumbs (at least `LOOP_STATUS` and `TALLY_PLAN_REVIEW_STATUS`) **before** `phase_driver_write_result_env`, on every exit path including cap-reached; or treat a refused symlink write as a non-fatal WARN, emit KVs, and exit 0 when `LOOP_STATUS` is already `cap-reached`. Add a harness case mirroring `test-lib-phase-driver.sh`’s symlink refusal but with `review-round-count.txt` at cap and assert stdout/orchestrator-visible `LOOP_STATUS=cap-reached`, not `panel-failed`.
- **Suggested revision**: Address the concern above.

