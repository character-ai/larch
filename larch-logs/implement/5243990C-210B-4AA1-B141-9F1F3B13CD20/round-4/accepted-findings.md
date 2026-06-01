### FINDING_1: correctness: skills/implement/scripts/step-18b-final-report.sh:92-95
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Body-diff logic requires snapshot_ok=true before cmp, unlike the retired inline Step 18 block where a missing .step18-prebody made ! cmp succeed. .step17-emitted exists, summary-final.md is missing before Step 18b or pre-write cp fails, write-final-report.sh writes a new non-empty body: EMIT_BODY stays false and orchestrator skips verbatim re-emit. Restore legacy cmp semantics (treat missing prebody as changed): drop snapshot_ok from the cmp branch or use [ ! -f prebody ] || ! cmp -s ...; add harness case for sentinel present + no pre-write summary.
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


### FINDING_16: correctness: skills/implement/scripts/step-18b-final-report.sh:92-95
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] EMIT_BODY body-diff gate requires snapshot_ok=true, diverging from retired inline cmp when .step18-prebody is absent. .step17-emitted exists, pre-write summary missing or cp to .step18-prebody fails, write-final-report succeeds with new non-empty summary-final.md: legacy fence sets emit via ! cmp -s; wrapper leaves EMIT_BODY=false so orchestrator skips verbatim re-emit despite refreshed body. Match legacy cmp semantics: treat missing prebody as diff, or drop snapshot_ok requirement when prebody is absent; add harness for sentinel-present + no successful snapshot + successful write.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: skills/implement/scripts/step-18b-final-report.sh:70-72
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] token-report failure path passes $? inside if ! cmd then branch, often logging exit 0. append-tool-failure.sh records wrong exit code for token-report failures, weakening Step 18 failure diagnostics. Capture token_rc before the if ! test (same pattern as wfr_rc) and pass token_rc to append_failure_best_effort.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/implement/scripts/step-18b-final-report.md:43-44
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Contract step 4 describes cmp-only body-diff flip but code requires snapshot_ok. Doc readers implement cmp without snapshot_ok and reintroduce the missing-prebody regression or diverge from step-18b-final-report.sh. Update the emit-decision steps to match implementation after fixing finding 1 (missing prebody = changed, or cmp only when snapshot exists).
- **Suggested revision**: Address the concern above.


### FINDING_20: **correctness** `skills/implement/scripts/stall-recovery-report.sh:263-266` — In the `seed-terminal-state` rewrite branch, `step` and `phase` are loaded via unguarded command substitutions (`step=$(safe_step_value "$(kv_get "$state" STALL_STEP "8")")` and the same for `PHASE`). Under `set -euo pipefail`, a non-zero exit from `kv_get` / `read-session-env-key.sh` (e.g. file becomes unreadable after `check_ship_pr_state_syntax`, `awk` failure, or a race) aborts the script before `emit_seeded_false_exit` runs, so stdout can lack `SEEDED=false` even though `stall-recovery-report.md` promises that operational failures always emit that KV first. The post-`mktemp` chain is guarded; this gap is immediately before it. **Suggested fix:** Split reads out of nested substitutions and guard each call, e.g. `step_raw=$(kv_get "$state" STALL_STEP "8") || emit_seeded_false_exit 1` then `step=$(safe_step_value "$step_raw")` (same for `phase`), or wrap both in a small helper that calls `emit_seeded_false_exit` on any `kv_get` failure; add a harness case that makes `kv_get` fail after format checks.
- **Reviewer**: dyn-set-e-kv-guarantee-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/stall-recovery-report.sh:263-266` — In the `seed-terminal-state` rewrite branch, `step` and `phase` are loaded via unguarded command substitutions (`step=$(safe_step_value "$(kv_get "$state" STALL_STEP "8")")` and the same for `PHASE`). Under `set -euo pipefail`, a non-zero exit from `kv_get` / `read-session-env-key.sh` (e.g. file becomes unreadable after `check_ship_pr_state_syntax`, `awk` failure, or a race) aborts the script before `emit_seeded_false_exit` runs, so stdout can lack `SEEDED=false` even though `stall-recovery-report.md` promises that operational failures always emit that KV first. The post-`mktemp` chain is guarded; this gap is immediately before it. **Suggested fix:** Split reads out of nested substitutions and guard each call, e.g. `step_raw=$(kv_get "$state" STALL_STEP "8") || emit_seeded_false_exit 1` then `step=$(safe_step_value "$step_raw")` (same for `phase`), or wrap both in a small helper that calls `emit_seeded_false_exit` on any `kv_get` failure; add a harness case that makes `kv_get` fail after format checks.
- **Suggested revision**: Address the concern above.


### FINDING_21: **correctness** `skills/implement/scripts/stall-recovery-report.sh:288` — On the `SEED_MODE=seed` path, `mkdir -p "$dir"` has no `|| emit_seeded_false_exit` handler. A permissions or filesystem failure trips `set -e` and exits without `SEEDED=false`, which breaks the orchestrator contract (“`SEEDED=false`, the KV is missing, or non-zero → terminal-route failure”). **Suggested fix:** Use `mkdir -p "$dir" || emit_seeded_false_exit 1` (and optionally assert the directory is writable before `mktemp`); extend `test-stall-recovery-report.sh` with a forced `mkdir` failure if you want regression coverage.
- **Reviewer**: dyn-set-e-kv-guarantee-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/stall-recovery-report.sh:288` — On the `SEED_MODE=seed` path, `mkdir -p "$dir"` has no `|| emit_seeded_false_exit` handler. A permissions or filesystem failure trips `set -e` and exits without `SEEDED=false`, which breaks the orchestrator contract (“`SEEDED=false`, the KV is missing, or non-zero → terminal-route failure”). **Suggested fix:** Use `mkdir -p "$dir" || emit_seeded_false_exit 1` (and optionally assert the directory is writable before `mktemp`); extend `test-stall-recovery-report.sh` with a forced `mkdir` failure if you want regression coverage.
- **Suggested revision**: Address the concern above.


### FINDING_25: **correctness** `skills/implement/scripts/step-18b-final-report.sh:92-95` — The post-write emit path requires `snapshot_ok=true` before `cmp` can promote `emit_body` when `.step17-emitted` is already present. If `summary-final.md` is missing before `write-final-report.sh` (so no snapshot is taken and `snapshot_ok` stays false) but the write produces a new non-empty `summary-final.md`, `EMIT_BODY` remains false and Step 18 will skip the orchestrator verbatim emit. The pre-extraction inline block did not have that guard: with `_wfr_printed=false`, `! cmp -s "$IMPLEMENT_TMPDIR/.step18-prebody" "$IMPLEMENT_TMPDIR/summary-final.md"` is true when `.step18-prebody` is absent, so `_wfr_emit_body` became true in the same scenario (see removed logic in the branch diff around the old `_wfr_printed` / `cmp` block). That is a behavioral regression relative to main, not just plan step 5’s “candidate stays false when snapshot_ok=false” wording—the plan’s edge case still promises emit when “body changed post-write via cmp,” and absent prebody behaved like a change under the old `cmp`. **Suggested fix:** In the `emit_body=false` branch after a successful write, treat “no pre-write snapshot” as eligible for cmp (e.g. drop the `snapshot_ok` guard and use `cmp` only when `.step18-prebody` exists, or set `emit_body=true` when `snapshot_ok=false`, `wfr_rc=0`, and the new body is non-empty). Add a harness case in `skills/implement/scripts/test-step-18b-final-report.sh` (sentinel present, no pre-write `summary-final.md`, write succeeds) and align `skills/implement/scripts/step-18b-final-report.md` step 4 if the contract changes.
- **Reviewer**: dyn-emit-body-snapshot-semantics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-18b-final-report.sh:92-95` — The post-write emit path requires `snapshot_ok=true` before `cmp` can promote `emit_body` when `.step17-emitted` is already present. If `summary-final.md` is missing before `write-final-report.sh` (so no snapshot is taken and `snapshot_ok` stays false) but the write produces a new non-empty `summary-final.md`, `EMIT_BODY` remains false and Step 18 will skip the orchestrator verbatim emit. The pre-extraction inline block did not have that guard: with `_wfr_printed=false`, `! cmp -s "$IMPLEMENT_TMPDIR/.step18-prebody" "$IMPLEMENT_TMPDIR/summary-final.md"` is true when `.step18-prebody` is absent, so `_wfr_emit_body` became true in the same scenario (see removed logic in the branch diff around the old `_wfr_printed` / `cmp` block). That is a behavioral regression relative to main, not just plan step 5’s “candidate stays false when snapshot_ok=false” wording—the plan’s edge case still promises emit when “body changed post-write via cmp,” and absent prebody behaved like a change under the old `cmp`. **Suggested fix:** In the `emit_body=false` branch after a successful write, treat “no pre-write snapshot” as eligible for cmp (e.g. drop the `snapshot_ok` guard and use `cmp` only when `.step18-prebody` exists, or set `emit_body=true` when `snapshot_ok=false`, `wfr_rc=0`, and the new body is non-empty). Add a harness case in `skills/implement/scripts/test-step-18b-final-report.sh` (sentinel present, no pre-write `summary-final.md`, write succeeds) and align `skills/implement/scripts/step-18b-final-report.md` step 4 if the contract changes.
- **Suggested revision**: Address the concern above.


### FINDING_26: **correctness** `skills/implement/scripts/test-step-18b-final-report.sh:125-138` — The matrix covers sentinel-present + unchanged body and sentinel-present + changed body with a pre-write snapshot, but not sentinel-present + absent pre-write `summary-final.md` + successful write. That gap would have allowed the `snapshot_ok` regression above to land despite green harnesses. **Suggested fix:** Add `case-emit-sentinel-no-prior-body`: `touch .step17-emitted`, ensure `summary-final.md` is absent, run wrapper with `WFR_MODE=ok`, and assert `EMIT_BODY` matches the intended contract (true if parity with main is required).
- **Reviewer**: dyn-emit-body-snapshot-semantics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-step-18b-final-report.sh:125-138` — The matrix covers sentinel-present + unchanged body and sentinel-present + changed body with a pre-write snapshot, but not sentinel-present + absent pre-write `summary-final.md` + successful write. That gap would have allowed the `snapshot_ok` regression above to land despite green harnesses. **Suggested fix:** Add `case-emit-sentinel-no-prior-body`: `touch .step17-emitted`, ensure `summary-final.md` is absent, run wrapper with `WFR_MODE=ok`, and assert `EMIT_BODY` matches the intended contract (true if parity with main is required).
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/implement/scripts/test-step-18b-final-report.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness omits sentinel-present + missing pre-write summary-final.md. Regression in finding 1 would not be caught by make test-step-18b-final-report. Add case: touch .step17-emitted, rm summary-final.md, WFR_MODE=ok → expect EMIT_BODY=true when body is written.
- **Suggested revision**: Address the concern above.


### FINDING_6: risk-integration: skills/implement/scripts/step-18b-final-report.sh:92-95
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] EMIT_BODY body-diff gate requires snapshot_ok=true before cmp; retired inline Step 18 block and plan spec did not. When .step17-emitted exists and pre-write cp to .step18-prebody fails (or summary-final.md was absent pre-write), a successful write-final-report that refreshes the cost line sets EMIT_BODY=false in the wrapper but would have set _wfr_emit_body=true under the old cmp-only guard—users miss the Step 18 verbatim re-emit. Confirm intent; either remove snapshot_ok guard to match plan/prior behavior, or document the guard and add harness cases for cp-fail/body-changed and cp-fail/body-unchanged.
- **Suggested revision**: Address the concern above.


