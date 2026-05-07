# test-session-setup-health-defaults.sh

**Primary**: `scripts/session-setup.sh` (the `.health` sidecar write block, section 6).

**Purpose**: regression harness pinning the fail-closed `:-false` defaults for `CODEX_HEALTHY` / `CURSOR_HEALTHY` / `GEMINI_HEALTHY` in the `.health` sidecar that `session-setup.sh` writes when invoked with `--write-health`. Closes #1336.

**Background**: `session-setup.sh` originally wrote `CODEX_HEALTHY=${FINAL_CODEX_HEALTHY:-true}` (and the same for Cursor / Gemini). Empty `FINAL_*_HEALTHY` (a future refactor dropping the key from `check-reviewers.sh` probe output, or a passthrough caller-env that omits the key) silently re-masked unhealthy state as `true`, undoing the fail-closed contract from #1317. The fix flips the defaults to `:-false`. This harness pins the new behavior so a future revert to `:-true` is caught immediately.

**Coverage**: four scenarios run via the passthrough caller-env path (`--skip-preflight`, no `--check-reviewers`):

1. Empty caller-env, no `--check-gemini-reviewer`: `CODEX_HEALTHY=false`, `CURSOR_HEALTHY=false`, `GEMINI_HEALTHY` key absent (Gemini guard suppresses emission when neither flag nor explicit value is present).
2. Empty caller-env with `--check-gemini-reviewer`: all three keys emitted as `false`. This case intentionally exercises the section-6 `.health` write guard (`if [[ "$CHECK_GEMINI_REVIEWER" == "true" || ... ]]`) in isolation — `--check-gemini-reviewer` is documented as "only meaningful with `--check-reviewers`" for the full reviewer probe workflow, but the write guard fires on the flag alone, so passing it without `--check-reviewers` is the correct way to test the guard's empty-`FINAL_GEMINI_HEALTHY` branch via the passthrough path. Do not "fix" by adding `--check-reviewers` — that would invoke the real probe and narrow coverage to whatever the live `check-reviewers.sh` happens to emit.
3. Explicit caller-env `true` values for all three keys: passes through unchanged (the fail-closed default does not clobber explicit values).
4. Explicit caller-env `false` values: passes through unchanged.

**Wired into**: `Makefile` `test-harnesses-6` shard (`make test-session-setup-health-defaults`).

**Edit-in-sync rules**:

- If the `.health` write block in `session-setup.sh` (section 6) changes its key set or guard semantics, update the test cases here.
- If a future refactor adds an actual `--check-reviewers` probe stub, replace the passthrough fixtures here with a stub-driven harness (do NOT remove the empty-caller-env scenarios; they pin the load-bearing default).
- The sibling source file `scripts/session-setup.sh` carries an inline comment block above the affected `echo` lines explaining the fail-closed rationale; keep that comment in sync with the test header.
