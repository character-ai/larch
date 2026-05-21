# Review Round 1

- Mode: `diff`
- Accepted findings: 10
- Rejected findings: 0
- Exonerated findings: 4
- Neutral findings: 0

## Accepted Findings

### FINDING_1: SKILL.md `session_env_args` missing `--codex-binary-found`/`--cursor-binary-found`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The `session_env_args` array constructed in the Step 0 Bash block (`SKILL.md:280-293`) passes `--codex-present` and `--cursor-present` to `write-session-env.sh` but omits `--codex-binary-found` and `--cursor-binary-found`. Because `session-setup.sh` does not write the session-env file directly, these keys are never persisted. Line 301 instructs the orchestrator to read `CODEX_BINARY_FOUND` from `session-env.sh` to drive the two-tier "binary not found" vs "probe failed" warning, but the read always returns empty, silently collapsing the two-tier diagnostic to the single-tier `CODEX_PRESENT=false` path.
- **Suggested revision**: Add `--codex-binary-found <value>` and `--cursor-binary-found <value>` to the `session_env_args` construction block in `SKILL.md`, extracting the values from the `session-setup.sh` stdout the same way `--codex-present` is extracted.

---


### FINDING_11: `${USER:-larch}` in stamp paths interpolated without sanitization — path traversal risk
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `larch_stamp_path_cursor` and `larch_stamp_path_codex` (`check-reviewers.sh:225-231`) interpolate `${USER:-larch}` directly into the stamp file path under `${TMPDIR:-/tmp}`. An attacker controlling the process environment (e.g. a malicious CI wrapper) can set `USER='../../etc/cron.d/evil'` to redirect `larch_write_bool_stamp`'s atomic `mktemp+mv` to an arbitrary filesystem path. The atomicity of the write does not protect the destination path.
- **Suggested revision**: Sanitize `USER` before embedding it in the path, e.g. `local _u="${USER//[^A-Za-z0-9._-]/}"; printf '%s' "${TMPDIR:-/tmp}/larch-cursor-present-${_u:-larch}.stamp"`.

---


### FINDING_13: `larch_write_bool_stamp` called without `|| true` — stamp write failure aborts script under `set -euo pipefail`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `larch_write_bool_stamp` is called without a `|| true` guard at three call sites (`check-reviewers.sh:210,236,267`). The function does `mktemp -p … || return 1`; under `set -euo pipefail`, a non-zero return propagates upward and aborts `check-reviewers.sh` entirely. A full `/tmp` or permission failure turns a TTL-cache write — an optimization — into a hard session-setup error that kills the entire run.
- **Suggested revision**: Add `|| true` at every call site: `larch_write_bool_stamp "$(larch_stamp_path_cursor)" "$CURSOR_PRESENT" || true` (and symmetrically for the Codex call).

---


### FINDING_14: Temp files leak if `external_serial_lock_acquire` exits non-zero
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: In both `larch_run_one_cursor_probe` and `larch_run_one_codex_probe` (`check-reviewers.sh:115-123,156-165`), `probe_out` (and `probe_side`) are allocated via `mktemp` before `external_serial_lock_acquire`. If the lock function exits non-zero, `set -euo pipefail` propagates the error before the `rm -f "$probe_out"` cleanup at the bottom of each function, leaking those temp files. In long-lived CI environments or constrained `/tmp`, repeated probe failures accumulate uncleaned files.
- **Suggested revision**: Guard `external_serial_lock_acquire` with `|| { rm -f "$probe_out" "${probe_side:-}"; return 1; }`, or add a `trap 'rm -f "$probe_out" "${probe_side:-}"' RETURN` immediately after the `mktemp` calls (scoped to the function).

### FINDING_4: `test-check-reviewers.sh` t0c/t0d dropped cross-tool presence assertions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Tests t0c and t0d only assert that the skipped tool reports `*_PRESENT=false`; they no longer assert that the non-skipped tool successfully probed and reports `*_PRESENT=true`. A regression where a skip flag accidentally suppresses the other tool's probe would go undetected. The plan explicitly requires verifying "the other tool still probes when its binary is stubbed."
- **Suggested revision**: Restore `assert_line "skip codex cursor still present" "CURSOR_PRESENT=true" "$out"` in t0c, and `assert_line "skip cursor codex still present" "CODEX_PRESENT=true" "$out"` in t0d.

---


### FINDING_5: `session-setup.sh` output-comment drops backward-compat `CODEX_AVAILABLE`/`CURSOR_AVAILABLE` alias documentation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The updated output-comment section removes documentation for `CODEX_AVAILABLE=true|false` and `CURSOR_AVAILABLE=true|false`, but the script body still emits them via `emit_kv CODEX_AVAILABLE`/`emit_kv CURSOR_AVAILABLE`. Callers relying on those backward-compat keys and reading only the header comment will not know the outputs exist.
- **Suggested revision**: Restore a one-line backward-compat note in the output comment, e.g. `#   CODEX_AVAILABLE/CURSOR_AVAILABLE  Backward-compat aliases for CODEX_PRESENT/CURSOR_PRESENT`.

---


### FINDING_6: `session-setup.sh` caller-env parsing loop and passthrough branch silently discard `BINARY_FOUND` keys
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The diff adds `CODEX_BINARY_FOUND, CURSOR_BINARY_FOUND` to the `--caller-env` "Recognized keys" comment (`session-setup.sh:23`), but the actual `case "$key"` parsing loop (`lines 135-147`, unchanged) has no arms for those keys — they fall to `*) ;;` and are silently dropped. In the passthrough branch (`CHECK_REVIEWERS=false`), `FINAL_CODEX_BINARY_FOUND=""` and `FINAL_CURSOR_BINARY_FOUND=""` are unconditionally empty and never forwarded to `write-session-env.sh`. A continuation run feeding a prior session-env via `--caller-env` loses the binary-vs-probe distinction; `read-session-env-key.sh --key CODEX_BINARY_FOUND` returns empty rather than `false`, so the "binary not found" warning path in `SKILL.md` silently never fires.
- **Suggested revision**: Add `CODEX_BINARY_FOUND) CALLER_CODEX_BINARY_FOUND="$value" ;;` and `CURSOR_BINARY_FOUND) CALLER_CURSOR_BINARY_FOUND="$value" ;;` to the caller-env parsing `case`, initialize the variables, and propagate them as `FINAL_CODEX_BINARY_FOUND` / `FINAL_CURSOR_BINARY_FOUND` in the passthrough branch — mirroring the `CODEX_PRESENT` pattern. Alternatively, remove these keys from the "Recognized keys" comment until passthrough support is intentionally implemented.

---


### FINDING_7: `test-step2-dispatch.sh` Test 3e `[[ -z "$ERR" ]]` assertion is fragile and can abort the entire test suite
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Test 3e at `skills/implement/scripts/test-step2-dispatch.sh:1499-1505` asserts `[[ -z "$ERR" ]]` (completely empty stderr) while `LARCH_QUIET_DISABLE=1` is active. With quiet disabled, `larch_quiet_init` returns early so `larch_err`/`larch_errf` writes go directly to `>&2`, captured in `$STDERR_3E`. Any informational diagnostic from the cursor launcher infrastructure causes a false failure. Because `fail()` calls `exit 1`, this causes the entire subsequent test suite (Tests 3b2 through Test 14) to be skipped with a CI failure.
- **Suggested revision**: Replace `[[ -z "$ERR" ]]` with a targeted negative check (e.g. `! grep -iq "error\|fatal\|failed" "$STDERR_3E"`) or capture combined output with `2>&1` and drop the separate `$STDERR_3E` capture. The meaningful correctness assertions (STATUS/REASON/TOOL/AUTH keys) already cover the pass condition.

---


### FINDING_8: Stamp-expiry tests t5/t11 cannot distinguish cache-hit from re-probe path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `test-check-reviewers.sh` stamp-expiry tests t5 (Cursor) and t11 (Codex) initialize the stamp to `true` and use a success stub (exit 0). Both the stale-stamp-cache-hit path and the correct expired-stamp-re-probe path return `*_PRESENT=true`, so a bug where an expired stamp is treated as fresh produces the same passing output. Contrast with t4/t10 (stamp hit) which use a failing stub, making a cache miss immediately visible.
- **Suggested revision**: For t5/t11, initialize the stamp to `false` and use a success stub; then a cache hit on the stale `false` stamp causes the test to fail, while a correct re-probe returns `true` and passes.

---


### FINDING_9: `docs/configuration-and-permissions.md` incorrectly states `LARCH_CURSOR_MODEL`/`LARCH_CODEX_MODEL` apply to `check-reviewers.sh` probes
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The updated "When set" bullets for both `LARCH_CURSOR_MODEL` and `LARCH_CODEX_MODEL` now list "Step 0 `check-reviewers.sh` probes" as a consumer, but the probe code passes no `--model` flag to `cursor agent` and no model flag to `codex exec`. `check-reviewers.md` (also updated in this PR) correctly documents "no model args." Operators setting these variables expecting probe-level model control will be surprised.
- **Suggested revision**: Remove "Step 0 `check-reviewers.sh` probes" from the "When set" bullets for both variables; list only the sites where model argv is actually injected (reviews, sketches, voting, negotiations, `--coder=cursor|codex` implement).

---


