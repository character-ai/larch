# Review Round 4

- Mode: `diff`
- Accepted findings: 6
- Rejected findings: 0
- Exonerated findings: 3
- Neutral findings: 1

## Accepted Findings

### FINDING_11: SKILL.md absent BINARY_FOUND conflated with confirmed binary-missing bail message
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: In `skills/implement/SKILL.md:1084,1087`, the "absent from session-env" sub-bullet for both `CURSOR_BINARY_FOUND` and `CODEX_BINARY_FOUND` maps to the same "binary not found" bail message as the confirmed-`false` case. `check-reviewers.sh` emits all six keys in a single end-of-script batch (lines 286–291); if the script exits abnormally before that block (e.g., a sourced-lib function calls `exit` on an unexpected error), the session-env has `*_PRESENT` from an earlier run but no `*_BINARY_FOUND`. An explicit-coder bail in that state says "binary not found" when the binary may be installed. The action (bail) is correct; the message is misleading.
- **Suggested revision**: Distinguish the absent case with a separate message: e.g., `--coder=cursor requested but CURSOR_BINARY_FOUND could not be determined (Step 0 may have failed). Re-run to re-probe.` rather than conflating it with the confirmed-missing case.

---


### FINDING_12: Session-setup integration test leaks stamp files to system TMPDIR
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: The `session-setup.sh` integration test in `scripts/test-check-reviewers.sh:321-331` does not set `TMPDIR` to an isolated scratch subdirectory. With `LARCH_PROBE_TTL_SECONDS=0` the stamp files are never read during this test, but `larch_write_bool_stamp` writes `larch-cursor-present-${USER}.stamp` and `larch-codex-present-${USER}.stamp` to the real system `TMPDIR`. A subsequent real invocation of `check-reviewers.sh` with the default TTL of 60 seconds would read the stub-created `true` stamp and skip the actual runtime probe.
- **Suggested revision**: Add `TMPDIR="$SCRATCH/sess-env-test"` to the env prefix on the `session-setup.sh` invocation at line 323.

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


### FINDING_6: Codex matrix tests t6–t12 missing Cursor auth test-mode env vars
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Codex matrix tests `t6`–`t12` in `scripts/test-check-reviewers.sh` (~lines 193, 210, 233, 250, and surrounding blocks) do not set `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux`. Each test places a `cursor` stub on PATH that exits 127; because `cursor_auth_preflight` runs before the probe loop and before the stub can short-circuit it, the Darwin keychain path can execute on macOS CI runners, potentially hanging or producing non-deterministic results. The plan explicitly required these flags for every test involving a Cursor stub on PATH. Tests `t13` and `t14` correctly set both flags, confirming the pattern was known.
- **Suggested revision**: Add `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux` to the `env …` (or `run_cr`) invocation in each of `t6`, `t7`, `t8`, `t9`, `t10`, `t11`, and `t12`.

---


### FINDING_8: t0c / t0d skip-flag tests omit BINARY_FOUND=true assertions for the non-skipped tool
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: In `scripts/test-check-reviewers.sh`, `t0c` (`--skip-codex-probe`) asserts `CODEX_BINARY_FOUND=true` but omits `CURSOR_BINARY_FOUND=true`; `t0d` (`--skip-cursor-probe`) asserts nothing about `BINARY_FOUND` for either tool. The invariant "skipping a probe does not suppress the other tool's `BINARY_FOUND`" is unverified, leaving a silent regression vector for future skip-flag changes.
- **Suggested revision**: Add `assert_line "skip codex cursor binary" "CURSOR_BINARY_FOUND=true" "$out"` to `t0c`; add `assert_line "skip cursor codex binary" "CODEX_BINARY_FOUND=true" "$out"` and `assert_line "skip cursor cursor binary" "CURSOR_BINARY_FOUND=true" "$out"` to `t0d`.

---


