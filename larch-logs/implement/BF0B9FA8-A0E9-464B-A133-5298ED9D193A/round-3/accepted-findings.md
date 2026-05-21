### FINDING_1: Test stamp path skips USER sanitization
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `scripts/test-check-reviewers.sh:997-998,1013-1014,1079,1093` stamp paths use `${USER:-larch}` verbatim, but `larch_stamp_path()` in `check-reviewers.sh` first strips non-`[A-Za-z0-9._-]` chars. A CI username like `bot@example.com` causes test and script to produce different paths; stamp-hit tests (t4, t5, t10, t11) become accidental cache-miss runs, masking the real cached value.
- **Suggested revision**: Replicate the sanitisation: `stamp="$SCRATCH/tN/larch-cursor-present-${USER//[^A-Za-z0-9._-]/}.stamp"` (fallback to `larch` when the sanitised string is empty).

---


### FINDING_10: No test for BINARY_FOUND propagation through session-setup → write-session-env chain
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `scripts/session-setup.sh:349-490` — The `CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND` propagation path (`check-reviewers.sh` → `session-setup.sh` → `write-session-env.sh` → `session-env.sh`) is untested end-to-end. A silent regression in any link (e.g. the `[[ -n "$PROBED_CODEX_BINARY_FOUND" ]]` guard returning false) leaves both keys absent from session-env, causing SKILL.md's two-tier Option A bail to skip both branches silently.
- **Suggested revision**: Add a test (in `test-check-reviewers.sh` or a minimal `test-session-setup.sh`) that invokes `session-setup.sh --check-reviewers --write-session-env <path>` with a PATH-stubbed binary and asserts the resulting session-env file contains both `CODEX_BINARY_FOUND=...` and `CURSOR_BINARY_FOUND=...`.

---


### FINDING_11: Timeout branch in larch_poll_probe_pid not tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `scripts/check-reviewers.sh:127-145` — The `probe_rc=124` timeout path (kill + wait interplay under `set -euo pipefail`) is never exercised. A race where the process exits between `kill -0` and `kill` could leave `_poll_rc` empty and fall through to `wait`, producing an incorrect `probe_rc` silently.
- **Suggested revision**: Add a test with a stub that runs `sleep 300` and set `LARCH_PROBE_TIMEOUT_SECONDS=2`; assert the probe completes within a few seconds and `*_PRESENT=false` is emitted.

---


### FINDING_12: Codex matrix tests t6–t11 don't assert CODEX_BINARY_FOUND
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `scripts/test-check-reviewers.sh:188-230` — Per-tool codex matrix tests (t6 success, t9 auth-exhausted, t10 stamp-hit, t11 stamp-expired) never assert `CODEX_BINARY_FOUND`. Only t12 (skip-probe path) and the combined t0 happy path check the key. An accidental removal of the `emit_kv CODEX_BINARY_FOUND` line would pass all these tests silently.
- **Suggested revision**: Add `assert_line "codex ok binary" "CODEX_BINARY_FOUND=true" "$out"` assertions to t6, t9, t10, t11 and the corresponding `false` assertion to t7.

---


### FINDING_15: CALLER_*_BINARY_FOUND emitted without boolean validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `scripts/session-setup.sh:424-429` — `CALLER_CODEX_BINARY_FOUND` and `CALLER_CURSOR_BINARY_FOUND` from the caller-env file are passed to `emit_kv` without a `true`/`false` guard (unlike `write-session-env.sh`, which validates before writing). A tampered caller-env value propagates further than needed before being caught.
- **Suggested revision**: Add `[[ "$CALLER_CODEX_BINARY_FOUND" == "true" || "$CALLER_CODEX_BINARY_FOUND" == "false" ]]` guards before `emit_kv`, matching the `write-session-env.sh` validation style. Symmetric for `CURSOR_BINARY_FOUND`.

---


### FINDING_17: mktemp -p DIR form not portable to macOS — stamp caching silently broken
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `scripts/check-reviewers.sh:121` — `larch_write_bool_stamp` uses `mktemp -p "${TMPDIR:-/tmp}" "larch-probe-stamp.XXXXXX"`. The `-p DIR` flag is GNU coreutils-specific; macOS/BSD `mktemp` does not support it and returns non-zero. The call site uses `|| return 1`, so the failure is silent — on macOS the stamp is never written and TTL caching is permanently disabled. Every session re-probes from scratch. All other `mktemp` calls in the repo use the portable template-path form.
- **Suggested revision**: Change to `stamp_tmp=$(mktemp "${TMPDIR:-/tmp}/larch-probe-stamp.XXXXXX") || return 1`, matching the portable form used by `larch_run_one_cursor_probe` (line 149) and `larch_run_one_codex_probe` (line 179).

---


### FINDING_20: Wrong shellcheck disable code (SC2086 vs SC2068)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `scripts/check-reviewers.sh:154` — `# shellcheck disable=SC2086` is placed above the `${CURSOR_AUTH_ARGS[@]+"${CURSOR_AUTH_ARGS[@]}"}` expansion. SC2086 is the scalar unquoted-variable warning; the correct suppression for an array conditional expansion is SC2068 (or no disable at all). The mismatch silently suppresses the wrong warning and misleads future `shellcheck` runs.
- **Suggested revision**: Remove `# shellcheck disable=SC2086`, or replace it with `# shellcheck disable=SC2068` if shellcheck still flags the outer conditional form.

---


### FINDING_21: t13 env-normalization test omits CODEX_PRESENT assertion
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `scripts/test-check-reviewers.sh:1110-1113` — The env-normalization test (t13) asserts only `CURSOR_PRESENT=true`. `STUB_BIN` (`bin0`) has both stubs exiting 0, so the Codex probe also runs successfully but its result is never asserted. Plan item 3 requires both tools to succeed under invalid env vars; a regression in Codex probe behavior under bad env vars would pass undetected.
- **Suggested revision**: Add `assert_line "env norm codex" "CODEX_PRESENT=true" "$out"` alongside the existing Cursor assertion.

---


### FINDING_22: design-only both-externals-down bail message text not pinned by any test
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `skills/implement/SKILL.md:1452` — The `design_only=true` + both-externals-down bail message wording diverges from the plan's specified string (plan: "both Codex and Cursor unavailable but --design-only requires external-backed plan-review"; implementation: "--design-only requires external-backed plan-review but no external reviewer is available"). No test pins this text; an accidental rewrite would go undetected.
- **Suggested revision**: Add an `assert_contains` assertion in `scripts/test-implement-step2-routing.sh` pinning the new message fragment (e.g., `'--design-only requires external-backed plan-review but no external reviewer is available'`).

---


### FINDING_23: Passthrough branch doesn't synthesize BINARY_FOUND from PRESENT for pre-feature sessions
- **Reviewer(s)**: dyn-key-propagation-output.txt
- **Concern**: `scripts/session-setup.sh:414-439` — When `CHECK_REVIEWERS=false` (passthrough), `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` are emitted only when `CALLER_CODEX_BINARY_FOUND` / `CALLER_CURSOR_BINARY_FOUND` are non-empty. A pre-feature session-env (or manually constructed caller-env) that supplies `CODEX_PRESENT=true` but not `CODEX_BINARY_FOUND` results in `FINAL_CODEX_BINARY_FOUND=""`, the `--codex-binary-found` flag is omitted, and the key is absent from session-env. Downstream skills using the two-tier `codex_available=true` only when **both** `CODEX_BINARY_FOUND=true` and `CODEX_PRESENT=true` will derive `codex_available=false` and fall back to Claude unnecessarily.
- **Suggested revision**: In the passthrough branch, when `CALLER_CODEX_BINARY_FOUND` is empty but `CALLER_CODEX_PRESENT` is non-empty, synthesize: `FINAL_CODEX_BINARY_FOUND="${CALLER_CODEX_BINARY_FOUND:-${CALLER_CODEX_PRESENT:-}}"`. Symmetric for `CURSOR_BINARY_FOUND`.

---


### FINDING_24: SKILL.md Option A bail has no arm for absent/empty BINARY_FOUND key
- **Reviewer(s)**: dyn-key-propagation-output.txt
- **Concern**: `skills/implement/SKILL.md:1077-1081` — The four Option A bail bullets each test for `BINARY_FOUND=false` or `BINARY_FOUND=true` explicitly. If `CURSOR_BINARY_FOUND` is absent from session-env (passthrough gap in FINDING_23, or any pre-feature env), `read-session-env-key.sh --default ""` returns `""`. An absent key matches neither bullet; the orchestrator has no instruction for this case and may proceed with an unchecked explicit coder.
- **Suggested revision**: Add a fifth bullet (or generalise the `BINARY_FOUND=false` bullet) to treat an absent/empty `BINARY_FOUND` as `false`: "If the explicit coder is `cursor` AND `cursor_available=false` AND `CURSOR_BINARY_FOUND` is absent or empty, treat as `CURSOR_BINARY_FOUND=false` and print the binary-not-found message." Symmetric for Codex.

---


### FINDING_5: probe_out not registered in PROBE_TMPFILES immediately after mktemp
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `scripts/check-reviewers.sh:179-183` — `probe_out` is created by `mktemp` on line 179, but `PROBE_TMPFILES` registration occurs on line 182, after `probe_side` is created on line 181. With `set -euo pipefail`, if the sidecar creation fails (e.g. TMPDIR full), the EXIT trap fires before `probe_out` is registered, leaking it for the process lifetime.
- **Suggested revision**: Move `PROBE_TMPFILES[...] = "$probe_out"` to immediately after the `mktemp` call (before `probe_side` is assigned or created).

---


### FINDING_6: --probe rejection test missing LARCH_QUIET_DISABLE=1
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `scripts/test-check-reviewers.sh:1122` — The `--probe` test invokes `"$CR" --probe` without `LARCH_QUIET_DISABLE=1`, unlike every other invocation (which go through `run_cr`). If `larch_err` is updated to route through quiet-mode suppression (FD3 vs stderr), the test silently produces a false pass because the expected string never appears on stderr.
- **Suggested revision**: Add `LARCH_QUIET_DISABLE=1` to the `--probe` invocation, or route it through `run_cr`.

---


### FINDING_7: Tool-specific tests don't stub the absent tool — real binary may be invoked
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `scripts/test-check-reviewers.sh` (t1/SB1, t3/SB3, t4/SB4, t5/SB5, t7/SB7, t9/SB9, t10/SB10, t11/SB11) — Cursor-only tests set `PATH="$SBn:/usr/bin:/bin"` without a no-op Codex stub, and Codex-only tests omit a no-op Cursor stub. On a machine with the real binary at `/usr/bin`, these tests invoke live auth/network probes, causing flakiness.
- **Suggested revision**: Add a no-op (`exit 127`) stub for the absent tool in each tool-specific scratch directory so `PATH` is fully isolated.

---


### FINDING_8: Routing test missing "binary not found" Option A bail assertions
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `scripts/test-implement-step2-routing.sh:1180-1182` — The new assertions cover only the `BINARY_FOUND=true` (probe-failed / auth error) bail messages. The symmetric `BINARY_FOUND=false` (binary not found) messages for both Cursor and Codex are not pinned; an accidental deletion would go undetected.
- **Suggested revision**: Add `assert_contains` calls for the "binary not found" message fragments (e.g., `'--coder=cursor requested but Cursor binary not found'` and the Codex equivalent).

---


### FINDING_9: Test 3e uses bare subshell inside set -euo pipefail — opaque failure
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `skills/implement/scripts/test-step2-dispatch.sh:225-238` — Test 3e wraps the dispatcher invocation in a bare `(...)` subshell. Every other test uses command substitution, which captures the exit code without triggering the outer `-e`. If the dispatcher exits non-zero for an unexpected reason, `set -e` fires before reaching the `fail 3e` message, producing a bare script exit with no context.
- **Suggested revision**: Wrap the subshell with `set +e` / `_3e_rc=$?` / `set -e` guards, or capture both streams via `OUT=$(... 2>&1)` to match the file's established pattern.

---


