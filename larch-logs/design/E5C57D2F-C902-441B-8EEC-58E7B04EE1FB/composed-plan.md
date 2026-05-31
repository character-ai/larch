## Plan

Fix the undocumented `ship-pr.sh` exit 2 that fires when a local CI harness confirms a failure. SIMPLE tier: smallest change that fixes the root cause; no exit-routing changes.

### Root cause

- `scripts/ship-pr.sh` runs `set -uo pipefail` by design (lines 4-7: "Intentionally no `set -e`"); every helper call captures `rc` explicitly.
- `run_pr_prep_phase` and its helper `run_oos_disposition_gate_if_required_before_oos_pending_false` wrap their OOS-gate calls in `set +e` … `set -e`, but the trailing `set -e` is **unconditional** at lines **1052**, **1557**, and **1567** (unlike the correct save/restore idiom at lines **139-147**). Because `set` options are global and the baseline is `set +e`, errexit leaks out of `run_pr_prep_phase` into the later CI phases.
- With errexit leaked on, `run_evaluate_failure` → `run_per_job_local_fix_loop` → `run_captured_cmd_then_fix_loop` → `_run_per_job_command_capture` (lines **2262-2267**) runs the local harness via the set-e-fragile pattern `"${_PJA_ARGV[@]}" > "$_RCC_RAW_LOG_PATH" 2>&1` immediately followed by `_RCC_CMD_RC=$?`. A failing harness aborts the whole script with the raw harness code (2) **before** `_RCC_CMD_RC=$?` runs, with `BAIL_REASON` empty and `STALL_TRACKING=false`. Exit 2 is not in the documented orchestrator exit table (0, 3, 4, 5, 6).
- Translating the code inside `run_evaluate_failure` (the issue's suggested fix) cannot work alone: the script dies at the harness invocation before reaching any translation logic.

### Files to modify

#### `scripts/ship-pr.sh`
1. **Stop the errexit leak at the three toggle sites (lines 1045-1052, 1554-1557, 1564-1567).** Replace each unconditional trailing `set -e` with the conditional save/restore idiom already used at lines 139-147:
   - `run_oos_disposition_gate_if_required_before_oos_pending_false` (1045-1053): snapshot prior errexit before `set +e` (`local _had_errexit=0; case $- in *e*) _had_errexit=1 ;; esac`); after `gate_rc=$?`, replace `set -e` with `(( _had_errexit )) && set -e`.
   - `run_pr_prep_phase` first OOS-gate call (1554-1557): same snapshot/restore.
   - `run_pr_prep_phase` recovery-waterfall OOS-gate call (1564-1567, nested in `if run_recovery_waterfall …; then`): same snapshot/restore.
   - Declare `_had_errexit` with `local`. (The helper self-managing errexit makes the outer wrappers redundant; keeping them with save/restore is defense-in-depth; deleting the now-redundant outer `set +e`/`set -e` pairs is an acceptable equivalent.)
2. **Harden the harness rc-capture in `_run_per_job_command_capture` (lines 2262-2267)** so a future leak cannot abort the script at the harness line. Replace `"${_PJA_ARGV[@]}" > "$_RCC_RAW_LOG_PATH" 2>&1` / `_RCC_CMD_RC=$?` with `_RCC_CMD_RC=0` then `"${_PJA_ARGV[@]}" > "$_RCC_RAW_LOG_PATH" 2>&1 || _RCC_CMD_RC=$?`. Preserves the contract (callers read `${_RCC_CMD_RC:-1}` at 280/304; global default at 173 unchanged); the `||` makes the harness a tested command so errexit never fires on it.
   - Leave `_run_per_job_command_once` (2269-2273) unchanged (always invoked under `if …; then`). Leave `run_evaluate_failure`'s helper captures (`gh-run-logs.sh` ~2527, `ci-failed-jobs.sh` ~2567, `ci-rerun-failed.sh` ~2496) unchanged — protected by the leak fix; hardening them is out of scope.

#### `scripts/test-ship-pr.sh`
Add a regression section (gated by `section_runs`) that sources `scripts/ship-pr.sh` under the side-effect-free source guard (line 3805; same pattern as the source-witness test at 889-905) and asserts:
1. **No errexit leak (baseline-off primary).** With `set +e` in the test shell, invoke each fixed toggle path and assert `$-` still lacks `e` afterward (an unconditional trailing `set -e` would leave `e` and fail; an errexit-on-only check cannot distinguish a force-enable from a correct restore). Stub the gate as an **on-disk** no-op (`exit 0`) script at `$PLUGIN_ROOT/skills/implement/scripts/oos-disposition-gate.sh` (the helper runs `bash "$gate_script"` as a subprocess at line 1046 — function override would not intercept; same pattern as `write_subject` at `scripts/test-ship-pr.sh:41-43`). Exercise all three surfaces:
   - **Helper** (1045-1053): sourcing resets `STATE_FILE`/`IMPLEMENT_TMPDIR` to empty (lines 27-28), so set `STATE_FILE` (minimal state, `FORKED_TARGET=false`, `REPO_UNAVAILABLE=false`), `IMPLEMENT_TMPDIR`, and `CLAUDE_PLUGIN_ROOT`/`PLUGIN_ROOT` **after** source — else the helper early-returns at 1008 (forked/unavailable) or 1012 (missing gate) before the toggle at 1045 and the assertion false-passes.
   - **Pr-prep first outer wrapper** (1554-1557): minimal pr-prep fixture; run the same outer sequence production uses (snapshot, `set +e`, gate helper, `gate_rc=$?`, conditional restore), not the helper alone.
   - **Pr-prep recovery outer wrapper** (1564-1567): same fixture; stub/short-circuit `run_recovery_waterfall` so the nested block runs (or mirror it verbatim).
2. **No errexit leak (restore-when-on secondary).** Per path: `set -e` before the call, assert `$-` still contains `e` after restore.
3. **Harness capture is errexit-safe.** With `set -e` active, pre-init `_PJL_LOG_PATH` to a writable temp file (the capture sets `_RCC_RAW_LOG_PATH="$_PJL_LOG_PATH"` and redirects to it at 2264-2265; default empty at 2172), set `_PJA_ARGV` to a command exiting non-zero, call `_run_per_job_command_capture`, and assert it returns without aborting the shell and `_RCC_CMD_RC` equals the real code (2), not 0.

Keep stubs Bash 3.2-compatible.

#### `scripts/ship-pr.md`
Add a short maintainer note: the `set +e` … `set -e` OOS-gate blocks must restore the prior errexit state (save/restore idiom) because the script baseline is `set +e`; documented exit-code table unchanged.

### Approach
Errexit-invariant restoration, not exit-code translation. Documented exits already cover confirmed-failure outcomes once the crash is gone (`ci-local-unfixable` exit 3 at 2384/2484; `…-max-retries` stall exit 4). No `run_evaluate_failure` routing change. Reuse the in-repo save/restore idiom (139-147) verbatim in shape. Confine `ship-pr.sh` edits to the three toggle sites and the one harness-capture site.

### Out of scope
- Re-routing confirmed failures to the autonomous main-agent CI-fix path (`first-fixer-non-health`) — a separate behavioral change.
- The `review-and-fix.sh` `classifier-failed` bug from the incident's reproduction context.

## Acceptance

- After the fix, `run_pr_prep_phase` and the OOS-gate helper no longer leave `set -e` enabled: the three toggle sites (1052/1557/1567) restore the prior errexit state.
- `_run_per_job_command_capture` records the local harness's real exit code in `_RCC_CMD_RC` without aborting the script, even when errexit is active.
- A failing local CI harness no longer causes `ship-pr.sh` to exit with the raw harness code; the run continues through the documented orchestrator exits (0/3/4/5/6) — confirmed-unfixable jobs still reach `ci-local-unfixable` exit 3 / `…-max-retries` stall exit 4.
- New `scripts/test-ship-pr.sh` regression assertions pass: baseline-off no-leak for all three toggle surfaces (helper + both `run_pr_prep_phase` outer wrappers), restore-when-on for each, and errexit-safe harness capture (real rc captured, no crash).
- `bash scripts/test-ship-pr.sh` and `make test-harnesses` pass; `bash scripts/relevant-checks.sh` (lint, shellcheck, bash32) passes.
- `scripts/ship-pr.md` documents the errexit save/restore invariant; the documented exit-code table is unchanged.

diff_lines: 95
