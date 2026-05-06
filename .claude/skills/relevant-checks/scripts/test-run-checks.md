# test-run-checks.sh

Purpose: regression-test `.claude/skills/relevant-checks/scripts/run-checks.sh` exit-code and banner behavior with disposable git repositories and controlled PATH stubs.

Primary callers: `make test-run-checks` and the `test-harnesses-5` Makefile shard.

Invariants: create one isolated git repo per assertion family; set fake `HOME`, `GIT_CONFIG_GLOBAL=/dev/null`, and `GIT_CONFIG_SYSTEM=/dev/null`; invoke `run-checks.sh` as a black box; provide executable `pre-commit` and `agent-lint` stubs only for scenarios that require them; keep `/usr/local/bin` out of PATH so host-installed `agent-lint` cannot satisfy absent-tool cases; assert both stdout banners and exit codes.

Makefile wiring: `test-run-checks` runs this script directly; `test-harnesses-5` includes `test-run-checks` so CI and `make test-harnesses` cover it.

Test harness: this file is itself the harness. Run `bash .claude/skills/relevant-checks/scripts/test-run-checks.sh` after edits, then `make test-run-checks` to verify Makefile wiring.

Edit in sync: update this contract, `.claude/skills/relevant-checks/scripts/run-checks.md`, and the Makefile target wiring whenever `run-checks.sh` phase counting, changed-file detection, preflight checks, agent-lint fallback behavior, observable banners, or exit-code contracts change.
