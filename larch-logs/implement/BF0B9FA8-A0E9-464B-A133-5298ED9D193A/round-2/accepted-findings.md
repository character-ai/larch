### FINDING_1: Duplicate `larch_stamp_path_cursor`/`larch_stamp_path_codex` functions
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `larch_stamp_path_cursor` and `larch_stamp_path_codex` (`check-reviewers.sh:60-68`) are byte-identical except for the literal `cursor`/`codex` in the stamp filename. Called a total of four times, the duplication multiplies if the naming scheme ever changes.
- **Suggested revision**: Replace both with `larch_stamp_path <tool>` accepting the tool name as a parameter: `printf '%s' "${TMPDIR:-/tmp}/larch-${1}-present-${_u:-larch}.stamp"`.


### FINDING_10: No EXIT trap to clean up probe temp files and orphaned background PIDs
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `larch_run_one_cursor_probe` and `larch_run_one_codex_probe` create `mktemp` temp files before spawning background CLIs. All three explicit return paths clean up the files, but SIGKILL arriving inside the 1-second `sleep 1` poll loop orphans both the background PID and the temp files. Auth-diagnostic output (including token hints in error strings) persisting in `/tmp` between sessions is a latent risk. Additionally, `cursor_preread_service_token` and `cursor_auth_argv` are called bare inside `set -euo pipefail` (`check-reviewers.sh:214-216`) with no `|| true` guard; a failure causes the script to exit before `emit_kv`, leaving `session-setup.sh` with empty output and silently treating both tools as unprobed.
- **Suggested revision**: Register `trap 'rm -f "${PROBE_TMPFILES[@]:-}"; kill "${PROBE_PIDS[@]:-}" 2>/dev/null || true' EXIT` (populating arrays after each `mktemp` / after each `… &`). Separately, wrap auth-setup calls with a `|| { CURSOR_PRESENT=false; … cleanup; larch_write_bool_stamp … || true; }` fallback so a helper failure degrades gracefully instead of exiting.


### FINDING_11: `larch_try_read_fresh_stamp` has no guard against negative `age` (future-dated stamp)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `age=$((now - mtime))` at ~line 258 of `check-reviewers.sh` has no check for a negative result. A stamp file with a future mtime (NTP correction, cross-host filesystem, or manual `touch -t <future>`) makes `age` negative, so `(( age > LARCH_PROBE_TTL_SECONDS ))` is false for any positive TTL, causing the stamp to appear perpetually fresh until the clock catches up.
- **Suggested revision**: Add `if (( age < 0 )); then return 1; fi` immediately after `age=$((now - mtime))` to treat future-dated stamps as cache misses.


### FINDING_12: `codex_available` / `cursor_available` semantics do not short-circuit on `BINARY_FOUND=false`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `skills/shared/external-reviewers.md:12-17` and `skills/implement/SKILL.md:~1388` derive `codex_available` solely from `CODEX_PRESENT`. A session-env with `CODEX_PRESENT=true` (stale from a skip-probe passthrough) and `CODEX_BINARY_FOUND=false` (fresh binary check after the binary was removed) is a reachable state: `session-setup.sh`'s skip-probe override restores `PROBED_CODEX_PRESENT` from the caller value without touching `PROBED_CODEX_BINARY_FOUND`. In that state `codex_available` is `true` and Codex slots are dispatched against a missing binary, wasting a slot and producing a confusing trace.
- **Suggested revision**: In `external-reviewers.md` and `SKILL.md` Step 0, state explicitly that `codex_available` (and its Cursor mirror) is `false` whenever **either** `CODEX_BINARY_FOUND=false` **or** `CODEX_PRESENT=false`.


### FINDING_13: `external-reviewers.md` failure-case bullets omit explicit `codex_available=false` assignment
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `skills/shared/external-reviewers.md:14` — the revised bullet list for Codex availability uses an if/else-if/else chain, but neither failure branch (`BINARY_FOUND=false` or `PRESENT=false`) includes an explicit `codex_available=false` statement. Readers must infer the assignment from the chain structure. The old text was explicit; combined with FINDING_12, the omission is load-bearing.
- **Suggested revision**: Add `codex_available=false` (and the Cursor mirror) explicitly to both failure-case bullets, matching the explicitness of the old text.


### FINDING_14: `external-reviewers.md:1671` stale "static session-start presence only" phrasing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The trailing sentence "Do not write runtime failure status back to session env. `CODEX_PRESENT` and `CURSOR_PRESENT` describe static session-start presence only." was not updated by the diff. "Static" previously contrasted binary-detection (once, cheap) with per-slot runtime failures, but now reads as though `*_PRESENT` is still binary-only, contradicting the two-tier runtime-probe semantics introduced earlier in the same file.
- **Suggested revision**: Change "static session-start presence only" to "set once at session start via the runtime health probe; not updated mid-session by per-slot launch failures."

---


### FINDING_2: Duplicate poll/timeout/wait/`probe_rc` block
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The ~13-line poll loop inside `larch_run_one_cursor_probe` (`check-reviewers.sh:127-139`) and `larch_run_one_codex_probe` (`check-reviewers.sh:170-182`) is verbatim identical. The real tool-specific asymmetry is limited to the spawn line and auth-check call sites, not the poll loop itself.
- **Suggested revision**: Extract the poll loop into a `larch_poll_probe_pid <pid> <timeout>` helper; call it from both probe functions.


### FINDING_5: Test 3e stderr assertion `! grep -Eiq 'error|fatal|failed'` is too broad and fragile
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `test-step2-dispatch.sh:1596` (Test 3e) checks `! grep -Eiq 'error|fatal|failed' <<<"$ERR"` against full verbose stderr (`LARCH_QUIET_DISABLE=1`). The word "failed" is common in diagnostic log prose from the Cursor launcher stack (e.g., "auth-retry failed", "cursor config setup error", "token refresh failed"). Any such line produces a false-positive test failure that is indistinguishable from a real error. All other tests in this file do not apply this filter, making Test 3e uniquely fragile.
- **Suggested revision**: Drop the catch-all negative filter entirely (the existing `STATUS=bailed REASON=stub-bailed`, `TOOL=cursor`, `ORCHESTRATOR_EDIT_AUTHORITY=forbidden`, and `step2-spawn-coder.txt` assertions already fully cover postconditions), or restrict to a specific unambiguous fatal-boot pattern such as `grep -Fq 'FATAL'`.


### FINDING_6: Test t12 missing `CODEX_BINARY_FOUND=true` assertion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Test t12 (`--skip-codex-probe` with a `codex` stub on PATH, `test-check-reviewers.sh:228-236`) asserts `CODEX_PRESENT=false` but does not assert `CODEX_BINARY_FOUND=true`. The symmetrically structured cursor-skip test (t0c) correctly pins both. A regression that stops emitting `CODEX_BINARY_FOUND` in the skip-probe path would pass t12 silently.
- **Suggested revision**: Add `assert_line "skip codex bin found" "CODEX_BINARY_FOUND=true" "$out"` to test t12.


### FINDING_7: Option A bail messages in `SKILL.md` collapse binary-not-found and runtime-probe-failed into one string
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: `skills/implement/SKILL.md:1433-1434` Option A bail bullets say "runtime probe failed" unconditionally, but `cursor_available=false` also fires when `CURSOR_BINARY_FOUND=false` (binary absent from PATH). This produces conflicting or misleading diagnostics for users who never installed the tool. The Step 0 warning block already uses the two-tier pattern (`BINARY_FOUND=false` → "binary not found" vs `PRESENT=false` → "probe failed"), but Option A collapses it.
- **Suggested revision**: Split each Option A bail sub-bullet: if `CURSOR_BINARY_FOUND=false`, say "Cursor binary not found"; if `CURSOR_BINARY_FOUND=true` but `cursor_available=false`, say "Cursor runtime probe failed / auth error". Mirror for Codex.


### FINDING_8: Test harness drops all `*_AVAILABLE` backward-compat alias assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The rewritten `test-check-reviewers.sh` drops all four `*_AVAILABLE` alias assertions (`CODEX_AVAILABLE=true`, `CURSOR_AVAILABLE=true`, `CODEX_AVAILABLE=false`, `CURSOR_AVAILABLE=false`) that existed in the prior harness. `check-reviewers.sh` still emits `emit_kv CODEX_AVAILABLE` / `emit_kv CURSOR_AVAILABLE`, and `session-setup.sh` still parses these aliases. A future edit that silently removes the `emit_kv` calls would go undetected.
- **Suggested revision**: Restore at minimum `assert_line "codex available alias" "CODEX_AVAILABLE=true"` and `assert_line "cursor available alias" "CURSOR_AVAILABLE=true"` in the t0 happy-path block; restore the corresponding `=false` counterparts in the absent-binary (t0b) block.


### FINDING_9: `LARCH_EXTERNAL_AUTH_RETRIES=0` normalization path has no test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The `case` validator in `check-reviewers.sh:221` includes `''|*[!0-9]*|0) MAX_AUTH_RETRIES=5` — the `0` branch is the only path not exercised by `test-check-reviewers.sh`. A regression that removes or miscodes the `0` case would silently change auth-exhaustion behavior. Tests t13 covers invalid strings and zero-timeout, but not zero-retries.
- **Suggested revision**: Add a test variant (in t13 or a new t15) that sets `LARCH_EXTERNAL_AUTH_RETRIES=0` against an always-auth-failing stub and asserts `CURSOR_PRESENT=false` (confirming 0 normalizes to 5, not to "no retries").


