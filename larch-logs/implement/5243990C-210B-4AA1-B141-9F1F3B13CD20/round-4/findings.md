### FINDING_1: correctness: skills/implement/scripts/step-18b-final-report.sh:92-95
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Body-diff logic requires snapshot_ok=true before cmp, unlike the retired inline Step 18 block where a missing .step18-prebody made ! cmp succeed. .step17-emitted exists, summary-final.md is missing before Step 18b or pre-write cp fails, write-final-report.sh writes a new non-empty body: EMIT_BODY stays false and orchestrator skips verbatim re-emit. Restore legacy cmp semantics (treat missing prebody as changed): drop snapshot_ok from the cmp branch or use [ ! -f prebody ] || ! cmp -s ...; add harness case for sentinel present + no pre-write summary.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/implement/scripts/step-18b-final-report.md:43-44
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Contract step 4 describes cmp-only body-diff flip but code requires snapshot_ok. Doc readers implement cmp without snapshot_ok and reintroduce the missing-prebody regression or diverge from step-18b-final-report.sh. Update the emit-decision steps to match implementation after fixing finding 1 (missing prebody = changed, or cmp only when snapshot exists).
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/implement/scripts/test-step-18b-final-report.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness omits sentinel-present + missing pre-write summary-final.md. Regression in finding 1 would not be caught by make test-step-18b-final-report. Add case: touch .step17-emitted, rm summary-final.md, WFR_MODE=ok → expect EMIT_BODY=true when body is written.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/implement/scripts/stall-recovery-report.sh:79-106
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated ship-pr-state.sh line-validation loops in check_ship_pr_state_syntax and ship_pr_state_has_keys. Higher maintenance cost when malformed-line rules change; risk of subtle drift between helpers. Compose ship_pr_state_has_keys from check_ship_pr_state_syntax plus a single key-presence scan, or route both subcommands through check_ship_pr_state_format.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/stall-recovery-report.sh:115-117
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] check_ship_pr_state_format is only used from classify; clear-stall/seed use split three-tier guards. Readers may expect one format helper at all call sites; behavior is correct per contract. Optional refactor for clarity only; not introduced as a functional bug by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: skills/implement/scripts/step-18b-final-report.sh:92-95
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] EMIT_BODY body-diff gate requires snapshot_ok=true before cmp; retired inline Step 18 block and plan spec did not. When .step17-emitted exists and pre-write cp to .step18-prebody fails (or summary-final.md was absent pre-write), a successful write-final-report that refreshes the cost line sets EMIT_BODY=false in the wrapper but would have set _wfr_emit_body=true under the old cmp-only guard—users miss the Step 18 verbatim re-emit. Confirm intent; either remove snapshot_ok guard to match plan/prior behavior, or document the guard and add harness cases for cp-fail/body-changed and cp-fail/body-unchanged.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: skills/implement/scripts/test-stall-recovery-report.sh:826-880
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] clear-stall/seed-terminal-state tests omit temp-read-assert failure on the atomic chain. A bug that writes a bad temp but passes mktemp/awk could leave orchestrators without a tested signal that temp-read-assert emits CLEARED=false/SEEDED=false before exit. Add a harness case stubbing read-session-env-key.sh (or corrupting temp content) so temp-read-assert fails and stdout includes the promised KV before non-zero exit.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: skills/implement/scripts/test-step-18b-final-report.sh:119-122
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] .step17-emitted never-written assertion runs only in the first test case. A future regression that writes the sentinel in another branch would only be caught if that branch reuses case-emit-absent. Assert wrapper never creates .step17-emitted in run_wrapper or after every matrix case.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/implement/scripts/step-18b-final-report.sh:47-50` — When `CLAUDE_PLUGIN_ROOT` is unset, the wrapper sources `$tmpdir/plugin-root.env`, which can redirect execution to an arbitrary plugin tree if the session tmpdir is tampered with by another same-user process. This matches the existing Step 18 pattern in `skills/implement/SKILL.md` (teardown blocks already source `plugin-root.env`); the new script continues that trust model rather than inventing it. **Suggested fix:** If hardening is desired repo-wide, validate `plugin-root.env` against a known canonical plugin root before sourcing (out of this PR’s scope).
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/implement/scripts/stall-recovery-report.sh` (all `--implement-tmpdir` subcommands) — `--implement-tmpdir` is only checked with `[ -d ]`, not canonicalized or prefix-bound to `~/.cache/larch/sessions/`, so a mis-invocation with a relative or foreign directory would write `ship-pr-state.sh` there. Pre-existing across implement helpers including `write-final-report.sh`; not introduced by this diff. **Suggested fix:** Shared `validate_implement_tmpdir_root` helper used at entry to new and existing writers (future hardening).
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/implement/scripts/step-18b-final-report.sh:74-95
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] snapshot_ok gate suppresses cmp-driven re-emit when pre-write cp fails .step17-emitted present; cp to .step18-prebody fails; write-final-report changes summary-final.md; EMIT_BODY stays false and Step 18 skips verbatim emit despite a material body change Treat failed snapshot like missing prebody or cmp when post-write body is non-empty; add harness with forced cp failure
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/implement/scripts/stall-recovery-report.sh:229-232
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Post-mv destination re-read failure emits CLEARED=false after disk may already be cleared mv succeeds and sets STALL_TRACKING=false; read-session-env-key fails on destination; orchestrator routes terminal and seed-terminal-state may set STALL_TRACKING=true again Verify temp vs dest before CLEARED=false; mirror guard in seed-terminal-state
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/implement/scripts/step-18b-final-report.sh:65-101
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Sentinel without summary file blocks recovery emit .step17-emitted exists but summary-final.md missing; WFR writes new non-empty body; EMIT_BODY false Document invariant or widen gate when sentinel present but pre-body absent and WFR_RC=0
- **Suggested revision**: Address the concern above.

### FINDING_14: architecture: skills/implement/scripts/step-18b-final-report.md:38-44
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Contract omits snapshot_ok prerequisite for cmp step Doc readers expect cmp always runs on body change; implementation skips cmp when snapshot cp failed Document snapshot_ok in emit-decision section
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/implement/references/stall-recovery.md:30
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] clear-stall exit 0 with CLEARED=false for keyless files Orchestrator branches on exit code only and treats keyless file as success without reading CLEARED Pin SKILL/stall-recovery prose to branch on CLEARED KV not exit code alone
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: skills/implement/scripts/step-18b-final-report.sh:92-95
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] EMIT_BODY body-diff gate requires snapshot_ok=true, diverging from retired inline cmp when .step18-prebody is absent. .step17-emitted exists, pre-write summary missing or cp to .step18-prebody fails, write-final-report succeeds with new non-empty summary-final.md: legacy fence sets emit via ! cmp -s; wrapper leaves EMIT_BODY=false so orchestrator skips verbatim re-emit despite refreshed body. Match legacy cmp semantics: treat missing prebody as diff, or drop snapshot_ok requirement when prebody is absent; add harness for sentinel-present + no successful snapshot + successful write.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: skills/implement/scripts/step-18b-final-report.sh:70-72
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] token-report failure path passes $? inside if ! cmd then branch, often logging exit 0. append-tool-failure.sh records wrong exit code for token-report failures, weakening Step 18 failure diagnostics. Capture token_rc before the if ! test (same pattern as wfr_rc) and pass token_rc to append_failure_best_effort.
- **Suggested revision**: Address the concern above.

### FINDING_18: architecture: skills/implement/scripts/stall-recovery-report.sh:184-215
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] clear-stall/seed-terminal-state use syntax+has_keys split instead of calling check_ship_pr_state_format as plan prose described. Reviewers tracing plan literally may expect one format helper at subcommand entry; behavior is documented but split across helpers. Call check_ship_pr_state_format where appropriate with explicit keyless branches, or document that subcommands intentionally use the finer split.
- **Suggested revision**: Address the concern above.

### FINDING_19: architecture: skills/implement/SKILL.md:1428
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] STEP17_EMITTED_PRESENT parsed but unused in Step 18b orchestrator text. Dead parse surface; plan asked for parsing without stating orchestrator use. Remove parse or document intended use in Step 18b prose.
- **Suggested revision**: Address the concern above.

### FINDING_20: **correctness** `skills/implement/scripts/stall-recovery-report.sh:263-266` — In the `seed-terminal-state` rewrite branch, `step` and `phase` are loaded via unguarded command substitutions (`step=$(safe_step_value "$(kv_get "$state" STALL_STEP "8")")` and the same for `PHASE`). Under `set -euo pipefail`, a non-zero exit from `kv_get` / `read-session-env-key.sh` (e.g. file becomes unreadable after `check_ship_pr_state_syntax`, `awk` failure, or a race) aborts the script before `emit_seeded_false_exit` runs, so stdout can lack `SEEDED=false` even though `stall-recovery-report.md` promises that operational failures always emit that KV first. The post-`mktemp` chain is guarded; this gap is immediately before it. **Suggested fix:** Split reads out of nested substitutions and guard each call, e.g. `step_raw=$(kv_get "$state" STALL_STEP "8") || emit_seeded_false_exit 1` then `step=$(safe_step_value "$step_raw")` (same for `phase`), or wrap both in a small helper that calls `emit_seeded_false_exit` on any `kv_get` failure; add a harness case that makes `kv_get` fail after format checks.
- **Reviewer**: dyn-set-e-kv-guarantee-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/stall-recovery-report.sh:263-266` — In the `seed-terminal-state` rewrite branch, `step` and `phase` are loaded via unguarded command substitutions (`step=$(safe_step_value "$(kv_get "$state" STALL_STEP "8")")` and the same for `PHASE`). Under `set -euo pipefail`, a non-zero exit from `kv_get` / `read-session-env-key.sh` (e.g. file becomes unreadable after `check_ship_pr_state_syntax`, `awk` failure, or a race) aborts the script before `emit_seeded_false_exit` runs, so stdout can lack `SEEDED=false` even though `stall-recovery-report.md` promises that operational failures always emit that KV first. The post-`mktemp` chain is guarded; this gap is immediately before it. **Suggested fix:** Split reads out of nested substitutions and guard each call, e.g. `step_raw=$(kv_get "$state" STALL_STEP "8") || emit_seeded_false_exit 1` then `step=$(safe_step_value "$step_raw")` (same for `phase`), or wrap both in a small helper that calls `emit_seeded_false_exit` on any `kv_get` failure; add a harness case that makes `kv_get` fail after format checks.
- **Suggested revision**: Address the concern above.

### FINDING_21: **correctness** `skills/implement/scripts/stall-recovery-report.sh:288` — On the `SEED_MODE=seed` path, `mkdir -p "$dir"` has no `|| emit_seeded_false_exit` handler. A permissions or filesystem failure trips `set -e` and exits without `SEEDED=false`, which breaks the orchestrator contract (“`SEEDED=false`, the KV is missing, or non-zero → terminal-route failure”). **Suggested fix:** Use `mkdir -p "$dir" || emit_seeded_false_exit 1` (and optionally assert the directory is writable before `mktemp`); extend `test-stall-recovery-report.sh` with a forced `mkdir` failure if you want regression coverage.
- **Reviewer**: dyn-set-e-kv-guarantee-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/stall-recovery-report.sh:288` — On the `SEED_MODE=seed` path, `mkdir -p "$dir"` has no `|| emit_seeded_false_exit` handler. A permissions or filesystem failure trips `set -e` and exits without `SEEDED=false`, which breaks the orchestrator contract (“`SEEDED=false`, the KV is missing, or non-zero → terminal-route failure”). **Suggested fix:** Use `mkdir -p "$dir" || emit_seeded_false_exit 1` (and optionally assert the directory is writable before `mktemp`); extend `test-stall-recovery-report.sh` with a forced `mkdir` failure if you want regression coverage.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-set-e-kv-guarantee-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/stall-recovery-report.sh:216-234` — For `clear-stall`, the temp-write → temp re-read → `mv -f` → destination re-read chain after `mktemp` uses explicit `|| emit_cleared_false_exit` / `if ! rewrite_ship_pr_state_keys` guards; this matches the plan and existing mv/temp-assert harness cases. No comparable pre-`mktemp` unguarded `kv_get` on that path.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-set-e-kv-guarantee-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/stall-recovery-report.sh:225-227,304-306` — `rm -f "$tmp"` inside plain `if` bodies (not tied to `||`) could theoretically abort under `set -e` before the emit helper if `rm` failed; risk is negligible with `rm -f` and was not introduced as a new pattern by this branch’s core design.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-set-e-kv-guarantee-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-stall-recovery-report.sh` — Harness covers mv/temp/dest assert failures for both subcommands but not `kv_get`/`mkdir` failures before `SEEDED=false` emission on the rewrite/seed paths above.
- **Suggested revision**: Address the concern above.

### FINDING_25: **correctness** `skills/implement/scripts/step-18b-final-report.sh:92-95` — The post-write emit path requires `snapshot_ok=true` before `cmp` can promote `emit_body` when `.step17-emitted` is already present. If `summary-final.md` is missing before `write-final-report.sh` (so no snapshot is taken and `snapshot_ok` stays false) but the write produces a new non-empty `summary-final.md`, `EMIT_BODY` remains false and Step 18 will skip the orchestrator verbatim emit. The pre-extraction inline block did not have that guard: with `_wfr_printed=false`, `! cmp -s "$IMPLEMENT_TMPDIR/.step18-prebody" "$IMPLEMENT_TMPDIR/summary-final.md"` is true when `.step18-prebody` is absent, so `_wfr_emit_body` became true in the same scenario (see removed logic in the branch diff around the old `_wfr_printed` / `cmp` block). That is a behavioral regression relative to main, not just plan step 5’s “candidate stays false when snapshot_ok=false” wording—the plan’s edge case still promises emit when “body changed post-write via cmp,” and absent prebody behaved like a change under the old `cmp`. **Suggested fix:** In the `emit_body=false` branch after a successful write, treat “no pre-write snapshot” as eligible for cmp (e.g. drop the `snapshot_ok` guard and use `cmp` only when `.step18-prebody` exists, or set `emit_body=true` when `snapshot_ok=false`, `wfr_rc=0`, and the new body is non-empty). Add a harness case in `skills/implement/scripts/test-step-18b-final-report.sh` (sentinel present, no pre-write `summary-final.md`, write succeeds) and align `skills/implement/scripts/step-18b-final-report.md` step 4 if the contract changes.
- **Reviewer**: dyn-emit-body-snapshot-semantics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-18b-final-report.sh:92-95` — The post-write emit path requires `snapshot_ok=true` before `cmp` can promote `emit_body` when `.step17-emitted` is already present. If `summary-final.md` is missing before `write-final-report.sh` (so no snapshot is taken and `snapshot_ok` stays false) but the write produces a new non-empty `summary-final.md`, `EMIT_BODY` remains false and Step 18 will skip the orchestrator verbatim emit. The pre-extraction inline block did not have that guard: with `_wfr_printed=false`, `! cmp -s "$IMPLEMENT_TMPDIR/.step18-prebody" "$IMPLEMENT_TMPDIR/summary-final.md"` is true when `.step18-prebody` is absent, so `_wfr_emit_body` became true in the same scenario (see removed logic in the branch diff around the old `_wfr_printed` / `cmp` block). That is a behavioral regression relative to main, not just plan step 5’s “candidate stays false when snapshot_ok=false” wording—the plan’s edge case still promises emit when “body changed post-write via cmp,” and absent prebody behaved like a change under the old `cmp`. **Suggested fix:** In the `emit_body=false` branch after a successful write, treat “no pre-write snapshot” as eligible for cmp (e.g. drop the `snapshot_ok` guard and use `cmp` only when `.step18-prebody` exists, or set `emit_body=true` when `snapshot_ok=false`, `wfr_rc=0`, and the new body is non-empty). Add a harness case in `skills/implement/scripts/test-step-18b-final-report.sh` (sentinel present, no pre-write `summary-final.md`, write succeeds) and align `skills/implement/scripts/step-18b-final-report.md` step 4 if the contract changes.
- **Suggested revision**: Address the concern above.

### FINDING_26: **correctness** `skills/implement/scripts/test-step-18b-final-report.sh:125-138` — The matrix covers sentinel-present + unchanged body and sentinel-present + changed body with a pre-write snapshot, but not sentinel-present + absent pre-write `summary-final.md` + successful write. That gap would have allowed the `snapshot_ok` regression above to land despite green harnesses. **Suggested fix:** Add `case-emit-sentinel-no-prior-body`: `touch .step17-emitted`, ensure `summary-final.md` is absent, run wrapper with `WFR_MODE=ok`, and assert `EMIT_BODY` matches the intended contract (true if parity with main is required).
- **Reviewer**: dyn-emit-body-snapshot-semantics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-step-18b-final-report.sh:125-138` — The matrix covers sentinel-present + unchanged body and sentinel-present + changed body with a pre-write snapshot, but not sentinel-present + absent pre-write `summary-final.md` + successful write. That gap would have allowed the `snapshot_ok` regression above to land despite green harnesses. **Suggested fix:** Add `case-emit-sentinel-no-prior-body`: `touch .step17-emitted`, ensure `summary-final.md` is absent, run wrapper with `WFR_MODE=ok`, and assert `EMIT_BODY` matches the intended contract (true if parity with main is required).
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] **`wfr_rc` capture** in `skills/implement/scripts/step-18b-final-report.sh:85-90` is correct under `set -euo pipefail`: the `if`/`else` contains the failing command, and `wfr_rc=$?` in the `else` branch records the exit code without aborting.
- **Reviewer**: dyn-emit-body-snapshot-semantics-output.txt
- **Concern**: - **`wfr_rc` capture** in `skills/implement/scripts/step-18b-final-report.sh:85-90` is correct under `set -euo pipefail`: the `if`/`else` contains the failing command, and `wfr_rc=$?` in the `else` branch records the exit code without aborting.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] **NEVER #20 boundary** is preserved: the wrapper does not print `summary-final.md` to chat and does not write `.step17-emitted` (`skills/implement/scripts/step-18b-final-report.sh:103-105`, `skills/implement/SKILL.md:1431`); verbatim emit and sentinel writes remain orchestrator-only.
- **Reviewer**: dyn-emit-body-snapshot-semantics-output.txt
- **Concern**: - **NEVER #20 boundary** is preserved: the wrapper does not print `summary-final.md` to chat and does not write `.step17-emitted` (`skills/implement/scripts/step-18b-final-report.sh:103-105`, `skills/implement/SKILL.md:1431`); verbatim emit and sentinel writes remain orchestrator-only.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Dropping Step 18 `--print-stdout` is an intentional, documented delta (`skills/implement/scripts/step-18b-final-report.md:46`); it is separate from the snapshot/`cmp` regression above.
- **Reviewer**: dyn-emit-body-snapshot-semantics-output.txt
- **Concern**: - Dropping Step 18 `--print-stdout` is an intentional, documented delta (`skills/implement/scripts/step-18b-final-report.md:46`); it is separate from the snapshot/`cmp` regression above.
- **Suggested revision**: Address the concern above.

