# test-session-setup-health-defaults.sh

**Primary**: `scripts/session-setup.sh` (the `.health` sidecar write block, section 6).

**Purpose**: regression harness pinning the fail-closed `:-false` defaults for `CODEX_HEALTHY` / `CURSOR_HEALTHY` / `GEMINI_HEALTHY` in the `.health` sidecar that `session-setup.sh` writes when invoked with `--write-health`. Closes #1336.

**Background**: `session-setup.sh` originally wrote `CODEX_HEALTHY=${FINAL_CODEX_HEALTHY:-true}` (and the same for Cursor / Gemini). Empty `FINAL_*_HEALTHY` (a future refactor dropping the key from `check-reviewers.sh` probe output, or a passthrough caller-env that omits the key) silently re-masked unhealthy state as `true`, undoing the fail-closed contract from #1317. The fix flips the defaults to `:-false`. This harness pins the new behavior so a future revert to `:-true` is caught immediately.

**Coverage**: four scenarios run via the passthrough caller-env path (`--skip-preflight`, no `--check-reviewers`). Note: `GEMINI_HEALTHY` is always hard-coded `false` by `session-setup.sh` (#1720 Part 1); tests verify this unconditional behavior.

1. Empty caller-env: `CODEX_HEALTHY=false`, `CURSOR_HEALTHY=false`, `GEMINI_HEALTHY=false`.
3. Explicit caller-env `true` for CODEX/CURSOR: passes through unchanged; GEMINI always `false`.
4. Explicit caller-env `false` for CODEX/CURSOR: passes through unchanged; GEMINI always `false`.
5. `--check-reviewers` with caller-env `true`: CODEX/CURSOR values propagate correctly.

**Wired into**: `Makefile` `test-harnesses-6` shard (`make test-session-setup-health-defaults`).

**Edit-in-sync rules**:

- If the `.health` write block in `session-setup.sh` (section 6) changes its key set or guard semantics, update the test cases here.
- If a future refactor adds an actual `--check-reviewers` probe stub, replace the passthrough fixtures here with a stub-driven harness (do NOT remove the empty-caller-env scenarios; they pin the load-bearing default).
- The sibling source file `scripts/session-setup.sh` carries an inline comment block above the affected `echo` lines explaining the fail-closed rationale; keep that comment in sync with the test header.
