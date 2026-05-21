## Goal
Replace binary-only probe in check-reviewers.sh with runtime health probe (mutex+retry+TTL), add Option A explicit-coder bail at Step 1

## Implementation Plan
## Implementation Plan: Harden cursor/codex probe in check-reviewers.sh

### Objective
Replace the binary-only `command -v` probe in `scripts/check-reviewers.sh` with a real runtime health probe (mutex + retry + TTL stamp caching) for both Cursor and Codex. Add Option A Step 1/Step 2 implementer consistency: when `coder_explicit=true` and the explicit coder is unavailable, bail at Step 1 with a clear error instead of silently falling back at Step 2.

### Files to modify

1. **`scripts/check-reviewers.sh`** — Replace `command -v` probes with full runtime health probes. Emit `CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND` (command -v result) plus `CODEX_PRESENT`/`CURSOR_PRESENT` (runtime probe result). Source `lib-cursor-launcher-common.sh` and `lib-cursor-auth.sh`. Add TTL stamp logic (USER-scoped, atomic mktemp+mv). Add bounded retry loop with `external_is_auth_failure` classification. Add `cursor_auth_preflight` gate. Add per-tool mutex via `external_serial_lock_acquire`/`external_serial_lock_release_after`. Add cursor private config dir setup/cleanup. Add `LARCH_PROBE_TTL_SECONDS`, `LARCH_PROBE_TIMEOUT_SECONDS`, `LARCH_EXTERNAL_AUTH_RETRIES` env var validation.

2. **`scripts/check-reviewers.md`** — Reverse "no runtime health probe" statement. Document mutex/retry/TTL behavior, new output keys (`CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND`), env knobs, probe argv divergences, rejected `--probe` exit code (1).

3. **`scripts/test-check-reviewers.sh`** — Full rewrite: PATH-stubbed probe scenarios for Cursor (success, non-auth failure, auth retry then success, auth exhaustion, stamp hit, stamp expired, skip flag) and Codex (same matrix), env var normalization, `--probe` exit 1 check. Use `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux` to skip Darwin keychain on non-Darwin hosts.

4. **`scripts/test-check-reviewers.md`** — Update fixture coverage to match new test matrix.

5. **`scripts/cursor-wrap-prompt.md`** — Update non-callers note: single `cursor agent` invocation per auth-retry, no wrap-prompt prefix.

6. **`scripts/session-setup.md`** — Update "static binary detection" to "runtime health probe" prose; document `*_BINARY_FOUND` keys.

7. **`skills/shared/external-reviewers.md`** — Update availability semantics: two-tier `BINARY_FOUND=false` vs `PRESENT=false` with separate warning messages.

8. **`skills/implement/SKILL.md`** — Option A: when `coder_explicit=true` and cursor/codex unavailable, bail to Step 18 with `STALL_TRACKING=true` instead of silently proceeding. Remove blanket "explicit value wins" sentence.

9. **`skills/implement/scripts/test-step2-dispatch.sh`** — Add Test 3e: explicit `--coder cursor --cursor-present true` reaches external Cursor launcher (stub-bailed manifest).

10. **`skills/implement/scripts/test-step2-dispatch.md`** — Add Test 3e to inventory; update Test 3b description for Option A backstop semantics.

11. **`scripts/test-implement-step2-routing.sh`** — Remove assertion pinning old "explicit value wins" sentence; add assertions for new Option A bail text.

12. **`docs/configuration-and-permissions.md`** — Add `LARCH_PROBE_TTL_SECONDS`, `LARCH_PROBE_TIMEOUT_SECONDS` env vars; update existing `LARCH_CODEX_EFFORT` prose.

13. **`scripts/write-session-env.sh`** — Add `--codex-binary-found`/`--cursor-binary-found` flags with validation.

14. **`scripts/session-setup.sh`** — Parse `CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND` from probe output; pass to `write-session-env.sh`.

### Approach

**check-reviewers.sh probe mechanics:**
- Binary check first; if absent → `*_PRESENT=false`, `*_BINARY_FOUND=false`, emit, done.
- If `--skip-*-probe` → `*_PRESENT=false`, `*_BINARY_FOUND` still reflects `command -v`, emit, done.
- Validate env vars via `case "$var" in ''|*[!0-9]*) var=default ;; esac`; special case for TIMEOUT (0 → default 30).
- TTL stamp: `${TMPDIR:-/tmp}/larch-cursor-present-${USER:-larch}.stamp`; `mktemp+mv` for atomic write; GNU/BSD `stat` fallback for mtime.
- Cursor: `cursor_auth_preflight` (returns 2 → skip loop); acquire mutex; `cursor_preread_service_token`+`cursor_auth_argv`; `cursor_launcher_setup_private_config_dir`; bounded retry loop; release mutex immediately after spawn; timeout poll loop using `SECONDS` builtin; `cursor_launcher_cleanup_private_config_dir`.
- Codex: same mutex pattern; `codex exec --sandbox read-only -C "$PWD" --output-last-message "$probe_out" -- "Respond with OK"`; no Cursor-specific auth helpers.
- Both: write stamp atomically after probe or skip.

**Bash 3.2 compliance:** use `printf -v` (already in lib), no `[[`-specific constructs, `$((..))` for arithmetic.

**Test isolation:** each test gets its own `$SCRATCH/tN` TMPDIR subdir for stamps; `LARCH_PROBE_TTL_SECONDS=0` to disable cache except in stamp tests; `LARCH_EXTERNAL_AUTH_RETRIES=3` (small, fast).

**Option A in SKILL.md:** narrow replacement of the single "explicit value wins" paragraph with a three-bullet list covering explicit-cursor-unavailable, explicit-codex-unavailable, and otherwise-proceed.

### Edge cases
- Darwin vs Linux: `external_serial_lock_acquire` is no-op on non-Darwin; `cursor_auth_preflight` is Darwin-only.
- Probe timeout: timeout poll kills PID, sets `probe_rc=124`, treats as non-auth failure.
- Stamp corrupt: treat non-`true`/`false` first line as cache miss.
- Concurrent probes on Linux: last writer wins (acceptable for coarse boolean TTL).
- `cursor_auth_preflight` returns 2: skip loop, write `false` stamp immediately.
- `cursor_launcher_setup_private_config_dir` fails: set `CURSOR_PRESENT=false`, skip loop.


## Test plan
- `make test-harnesses` runs `test-check-reviewers.sh` (new comprehensive suite).
- `make lint` covers bash32 compliance and markdown lint.
- `test-implement-step2-routing.sh` and `test-step2-dispatch.sh` updated assertions.

diff_lines: 420
