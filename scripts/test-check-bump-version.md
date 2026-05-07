# scripts/test-check-bump-version.sh — contract

Regression harness for `scripts/check-bump-version.sh` covering all three `STATUS` paths × both `--mode pre` / `--mode post` modes plus the `origin/main`-only fallback and the #172 fail-closed regression guard. Wired into `make lint` via the `test-check-bump-version` target. The full contract is owned by `scripts/check-bump-version.md`; this stub satisfies `.claude/rules/script-md-siblings.md`. Listed in `agent-lint.toml`'s exclude set because agent-lint does not follow Makefile-only references.
