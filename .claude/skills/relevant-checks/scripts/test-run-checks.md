# test-run-checks.sh

Purpose: regression-test `.claude/skills/relevant-checks/scripts/run-checks.sh` exit-code and banner behavior with disposable git repositories and controlled PATH stubs.

Primary callers: `make test-run-checks` and the `test-harnesses-5` Makefile shard.

Invariants: create one isolated git repo per assertion family; set fake `HOME`, `GIT_CONFIG_GLOBAL=/dev/null`, and `GIT_CONFIG_SYSTEM=/dev/null`; invoke `run-checks.sh` as a black box; provide executable `pre-commit` and `agent-lint` stubs only for scenarios that require them; keep `/usr/local/bin` out of PATH so host-installed `agent-lint` cannot satisfy absent-tool cases; assert both stdout banners and exit codes. Branch coverage: zero-phase exit 2 (empty `MODIFIED_FILES` and deletions-only), `agent-lint` exit-code propagation (rc=0 and rc=7), changed-file dual-phase happy path (pre-commit + agent-lint both succeed), changed-file pre-commit-fails path (run-checks.sh:116-118 propagates rc and SKIPS `agent-lint`), changed-file pre-commit-success + agent-lint-absent path (`WARNING: agent-lint not found on PATH — skipping` banner), pre-commit-missing preflight (run-checks.sh:13-16), and not-inside-a-git-repo (run-checks.sh:18). Assumes `pre-commit` and `agent-lint` are NOT present in `/usr/bin` or `/bin` on the host — both tools are conventionally pip-installed under user / virtualenv / `/usr/local/bin` paths in this repo's developer environments.

Makefile wiring: `test-run-checks` runs this script directly; `test-harnesses-5` includes `test-run-checks` so CI and `make test-harnesses` cover it.

Test harness: this file is itself the harness. Run `bash .claude/skills/relevant-checks/scripts/test-run-checks.sh` after edits, then `make test-run-checks` to verify Makefile wiring.

Edit in sync: update this contract, `.claude/skills/relevant-checks/scripts/run-checks.md`, and the Makefile target wiring whenever `run-checks.sh` phase counting, changed-file detection, preflight checks, agent-lint fallback behavior, observable banners, or exit-code contracts change.
