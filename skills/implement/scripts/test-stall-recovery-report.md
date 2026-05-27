# test-stall-recovery-report.sh

Hermetic offline harness for `stall-recovery-report.sh`.

The harness builds a temporary plugin-like sandbox, copies the helper and required shared scripts, stubs GitHub-facing commands, and exercises the 21 planned cases without network access. Fixtures use synthetic `ship-pr-state.sh`, `session-env.sh`, failure-detail logs, and attempts files only.

Invariants:

- Public output surfaces must not contain injected raw classifier-input sentinels.
- `lint` must prove allowlist parity across TSV, code, and `stall-recovery-report.md`.
- Dry-run mode must not call `gh` or invoke `/larch:issue`.
- Missing `ship-pr-state.sh` must classify as `unrecoverable`, not exit 3.
- Malformed present `ship-pr-state.sh` is the only exit-3 path.
