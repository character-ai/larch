# scripts/test-session-entry-gate.sh — contract

`scripts/test-session-entry-gate.sh` is the offline regression harness for `scripts/session-entry-gate.sh`. It uses a fixed table of helper invocations and never calls git, `preflight.sh`, or `session-setup.sh`.

The fixture matrix covers the successful gate policy for `/implement` and `/design`: main, user branch, non-user branch, detached HEAD, and `/design` nested `--branch-info-supplied=true`. Each success case asserts exact stdout, empty stderr, exit 0, and the current invariant that `ENTRY_GATE=continue` iff `SKIP_BRANCH_CHECK=true`.

The invalid-input matrix covers bad mode, missing required flags, missing flag values, malformed booleans, empty user prefix, implement-mode rejection of `--branch-info-supplied` for both true and false values, and unknown flags. Each failure case asserts exit 4, empty stdout, and a `GATE_ERROR=` stderr line containing the expected reason.

The harness first asserts `scripts/session-entry-gate.sh` is executable and invokes it directly via path, not through `bash scripts/session-entry-gate.sh`. This keeps the executable bit load-bearing.

Edit this harness in sync with:

- `scripts/session-entry-gate.sh`
- `scripts/session-entry-gate.md`
- `skills/implement/SKILL.md` Step 0
- `skills/design/SKILL.md` Step 0
- `Makefile` target and shard assignment
- `agent-lint.toml` Makefile-only harness exclusion
