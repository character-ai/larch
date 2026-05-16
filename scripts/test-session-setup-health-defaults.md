# test-session-setup-health-defaults.sh

**Primary**: `scripts/session-setup.sh` (the `.health` sidecar write block, section 6).

5. `--check-reviewers` with caller-env `true`: CODEX/CURSOR values propagate correctly.

**Wired into**: `Makefile` `test-harnesses-6` shard (`make test-session-setup-health-defaults`).

**Edit-in-sync rules**:

- If the `.health` write block in `session-setup.sh` (section 6) changes its key set or guard semantics, update the test cases here.
- If a future refactor adds an actual `--check-reviewers` probe stub, replace the passthrough fixtures here with a stub-driven harness (do NOT remove the empty-caller-env scenarios; they pin the load-bearing default).
- The sibling source file `scripts/session-setup.sh` carries an inline comment block above the affected `echo` lines explaining the fail-closed rationale; keep that comment in sync with the test header.
