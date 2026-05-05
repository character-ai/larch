# test-run-external-agent-args.sh

**Purpose**: Offline argument-validation harness for `scripts/run-external-agent.sh`. It verifies wrapper-side validation before any child command is launched.

**Coverage**:
- `--timeout 0` exits 1 when all required flags and a command are present.
- The zero-timeout failure reports the exact unprefixed error from `run-external-agent.sh` on the combined stdout/stderr stream (the harness captures with `2>&1`).
- No output / `.done` / `.meta` / `.diag` file is created on the rejection path — a reject-before-side-effects guard parallel to `scripts/test-run-external-agent.sh`.

**Invariants**:
- The harness must stay offline and must not depend on an external agent binary.
- The command after `--` must remain present so required-command validation does not mask timeout validation.
- The expected error string intentionally starts with `ERROR:` rather than a script-name prefix.

**Makefile wiring**:
- `make test-run-external-agent-args`.
- `make test-harnesses-5`.

**Edit-in-sync**:
- `scripts/run-external-agent.sh` — argument-validation behavior under test.
- `scripts/run-external-agent.md` — primary script contract and test-harness registry.
- `Makefile` — target and shard wiring.
