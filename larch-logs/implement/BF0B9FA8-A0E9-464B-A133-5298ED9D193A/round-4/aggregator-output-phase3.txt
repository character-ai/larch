### FINDING_1: Passthrough branch infers BINARY_FOUND from PRESENT when BINARY_FOUND is absent
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: In `scripts/session-setup.sh` passthrough branch (`CHECK_REVIEWERS=false`), when `CALLER_CODEX_BINARY_FOUND` / `CALLER_CURSOR_BINARY_FOUND` is absent from caller-env but `*_PRESENT=false` is present, the code infers `_passthrough_codex_bin="$CALLER_CODEX_PRESENT"` (emitting `BINARY_FOUND=false`). A legacy or new-code caller-env where `*_PRESENT=false` was written because the runtime probe failed (binary is on PATH but timed out or auth-exhausted) will propagate `BINARY_FOUND=false`, causing SKILL.md Option A to print "binary not found" instead of "runtime probe failed / auth error" — sending the user toward the wrong remediation path. The action (bail) is correct; only the diagnostic is wrong.
- **Suggested revision**: When `CALLER_CODEX_BINARY_FOUND` / `CALLER_CURSOR_BINARY_FOUND` is absent from caller-env, leave `_passthrough_codex_bin=""` / `_passthrough_cursor_bin=""` rather than falling back to the `*_PRESENT` value. Let SKILL.md's absent-key rule (treat absent as `false`) fire conservatively with the same "binary not found" default; this is no worse than the current behavior while eliminating the false-inference path. Alternatively, document the inference rule explicitly in `check-reviewers.md`'s edit-in-sync table with a comment acknowledging the false-negative case.

---

### FINDING_2: Probe helpers read outer-scope globals AUTH_ATTEMPT / MAX_AUTH_RETRIES without documentation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `larch_run_one_cursor_probe` and `larch_run_one_codex_probe` (`scripts/check-reviewers.sh:167-171,199-203`) declare only `local` vars yet silently consume the outer-scope `AUTH_ATTEMPT` and `MAX_AUTH_RETRIES` globals to decide whether to return 2 (auth-retry) or 1 (permanent failure). Functions appear self-contained but the dependency is enforced only by `set -u` catching an unset variable; a stale-but-set value produces silent wrong retry semantics. A refactor that calls these functions without first setting `AUTH_ATTEMPT`, or that resets it between the Cursor and Codex loops without understanding the convention, will silently alter retry behavior.
- **Suggested revision**: Add a short comment to each function documenting the required caller-set globals (`# Reads outer-scope: AUTH_ATTEMPT MAX_AUTH_RETRIES`), or pass `AUTH_ATTEMPT` / `MAX_AUTH_RETRIES` as positional parameters so the dependency is visible at each call site.

---

### FINDING_3: `larch_poll_probe_pid` resets the process-global `SECONDS` shell builtin
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: `larch_poll_probe_pid` (`scripts/check-reviewers.sh:131`) resets the global `SECONDS` builtin via `SECONDS=0` to implement per-probe timeout tracking. Because `SECONDS` is process-global, each probe invocation silently corrupts the script-wide elapsed-time baseline. If `lib-cursor-launcher-common.sh` or `lib-cursor-auth.sh` (sourced at lines 39–41) or any future caller uses `$SECONDS` for elapsed-time computation after the first probe call, the reset produces wrong values.
- **Suggested revision**: Replace `SECONDS=0` with `local _start=$SECONDS` and compute elapsed as `(( SECONDS - _start ))` inside the poll loop, preserving the accumulated global. Alternatively use `_t0=$(date +%s)` / `$(( $(date +%s) - _t0 ))` for full independence from the builtin.

---

### FINDING_4: `run_cr` permanently changes outer script's CWD without a subshell
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `run_cr` in `scripts/test-check-reviewers.sh:28-33` executes `cd "$REPO_ROOT"` in the function body without a subshell wrapper. Every call permanently changes the outer script's CWD. This works today because all calls target the same directory, but a future test that sets a different CWD before a `run_cr` call would have it silently overridden.
- **Suggested revision**: Wrap the function body in a subshell: `run_cr() { local tmp="$1"; shift; mkdir -p "$tmp"; ( cd "$REPO_ROOT" && TMPDIR="$tmp" LARCH_QUIET_DISABLE=1 "$@" ); }`.

---

### FINDING_5: [OUT_OF_SCOPE] EXIT trap kills PROBE_PIDS but does not `wait` after kill
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `larch_probe_exit_cleanup` (`scripts/check-reviewers.sh:62-70`) calls `kill` on each PID in `PROBE_PIDS` but does not `wait` afterward, leaving short-lived zombie entries for any in-flight probe when the trap fires. In practice the parent shell exits immediately so init reaps them; functionally harmless. Pre-existing limitation not introduced by this diff.
- **Suggested revision**: Add `wait "$pid" 2>/dev/null || true` after each `kill` in the cleanup loop if zombie avoidance is desired in future hardening.

---

### FINDING_6: Codex matrix tests t6–t12 missing Cursor auth test-mode env vars
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Codex matrix tests `t6`–`t12` in `scripts/test-check-reviewers.sh` (~lines 193, 210, 233, 250, and surrounding blocks) do not set `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux`. Each test places a `cursor` stub on PATH that exits 127; because `cursor_auth_preflight` runs before the probe loop and before the stub can short-circuit it, the Darwin keychain path can execute on macOS CI runners, potentially hanging or producing non-deterministic results. The plan explicitly required these flags for every test involving a Cursor stub on PATH. Tests `t13` and `t14` correctly set both flags, confirming the pattern was known.
- **Suggested revision**: Add `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux` to the `env …` (or `run_cr`) invocation in each of `t6`, `t7`, `t8`, `t9`, `t10`, `t11`, and `t12`.

---

### FINDING_7: `cursor_launcher_cleanup_private_config_dir` called unconditionally after partial setup
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Concern**: In `scripts/check-reviewers.sh:226-250`, `cursor_launcher_cleanup_private_config_dir` is called unconditionally after the compound `if ! { cursor_preread_service_token && cursor_auth_argv && cursor_launcher_setup_private_config_dir }` block. When `cursor_preread_service_token` or `cursor_auth_argv` fails first, `cursor_launcher_setup_private_config_dir` is never called, yet cleanup is still invoked. If the cleanup function is not a robust no-op for never-set-up state (e.g., it unconditionally removes a directory computed from an unset global), it could silently operate on the user's real Cursor config directory rather than the private probe copy.
- **Suggested revision**: Guard cleanup with a boolean tracking whether setup completed: introduce `_cursor_setup_ok=false` before the setup block, set it to `true` only on full success, and skip `cursor_launcher_cleanup_private_config_dir` when `_cursor_setup_ok=false`. Alternatively, verify `cursor_launcher_cleanup_private_config_dir` is idempotent for never-set-up state and add a comment asserting that invariant.

---

### FINDING_8: t0c / t0d skip-flag tests omit BINARY_FOUND=true assertions for the non-skipped tool
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: In `scripts/test-check-reviewers.sh`, `t0c` (`--skip-codex-probe`) asserts `CODEX_BINARY_FOUND=true` but omits `CURSOR_BINARY_FOUND=true`; `t0d` (`--skip-cursor-probe`) asserts nothing about `BINARY_FOUND` for either tool. The invariant "skipping a probe does not suppress the other tool's `BINARY_FOUND`" is unverified, leaving a silent regression vector for future skip-flag changes.
- **Suggested revision**: Add `assert_line "skip codex cursor binary" "CURSOR_BINARY_FOUND=true" "$out"` to `t0c`; add `assert_line "skip cursor codex binary" "CODEX_BINARY_FOUND=true" "$out"` and `assert_line "skip cursor cursor binary" "CURSOR_BINARY_FOUND=true" "$out"` to `t0d`.

---

### FINDING_9: TMPDIR stamp poisoning via unvalidated TMPDIR environment variable
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `larch_stamp_path` (`scripts/check-reviewers.sh:75`) builds stamp paths as `${TMPDIR:-/tmp}/larch-${1}-present-${_u:-larch}.stamp`, trusting the `TMPDIR` env var without sanitization. A local attacker who controls `TMPDIR` before `check-reviewers.sh` runs can pre-seed the expected stamp file with content `true` and a current mtime, causing the probe to report `CURSOR_PRESENT=true` or `CODEX_PRESENT=true` without executing the runtime health check. Any subsequent invocation within `LARCH_PROBE_TTL_SECONDS` will cache-hit and skip auth entirely.
- **Suggested revision**: Derive stamp paths from a fixed prefix not controlled by `TMPDIR` — e.g., `${HOME}/.cache/larch/stamps/` (already used for session tmpdirs in `session-setup.sh`) validated against a known absolute prefix. Alternatively, explicitly document in the script header that `TMPDIR` is trusted and that the stamp TTL provides no security boundary when `TMPDIR` is attacker-controlled.

---

### FINDING_10: [OUT_OF_SCOPE] Cursor auth tokens visible in process argv during probe subprocess
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Cursor authentication tokens injected into `CURSOR_AUTH_ARGS` appear in the process argv (`cursor agent … --api-key $TOKEN`) for the probe subprocess duration, making them visible in `/proc/$pid/cmdline` and `ps aux` output to co-users on shared hosts. Pre-existing pattern shared with all Cursor launchers; not introduced by this diff.
- **Suggested revision**: Consider passing tokens via environment variable rather than CLI args in a follow-up hardening pass.

---

### FINDING_11: SKILL.md absent BINARY_FOUND conflated with confirmed binary-missing bail message
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: In `skills/implement/SKILL.md:1084,1087`, the "absent from session-env" sub-bullet for both `CURSOR_BINARY_FOUND` and `CODEX_BINARY_FOUND` maps to the same "binary not found" bail message as the confirmed-`false` case. `check-reviewers.sh` emits all six keys in a single end-of-script batch (lines 286–291); if the script exits abnormally before that block (e.g., a sourced-lib function calls `exit` on an unexpected error), the session-env has `*_PRESENT` from an earlier run but no `*_BINARY_FOUND`. An explicit-coder bail in that state says "binary not found" when the binary may be installed. The action (bail) is correct; the message is misleading.
- **Suggested revision**: Distinguish the absent case with a separate message: e.g., `--coder=cursor requested but CURSOR_BINARY_FOUND could not be determined (Step 0 may have failed). Re-run to re-probe.` rather than conflating it with the confirmed-missing case.

---

### FINDING_12: Session-setup integration test leaks stamp files to system TMPDIR
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: The `session-setup.sh` integration test in `scripts/test-check-reviewers.sh:321-331` does not set `TMPDIR` to an isolated scratch subdirectory. With `LARCH_PROBE_TTL_SECONDS=0` the stamp files are never read during this test, but `larch_write_bool_stamp` writes `larch-cursor-present-${USER}.stamp` and `larch-codex-present-${USER}.stamp` to the real system `TMPDIR`. A subsequent real invocation of `check-reviewers.sh` with the default TTL of 60 seconds would read the stub-created `true` stamp and skip the actual runtime probe.
- **Suggested revision**: Add `TMPDIR="$SCRATCH/sess-env-test"` to the env prefix on the `session-setup.sh` invocation at line 323.
