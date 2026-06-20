## Acceptance

- All 19 retired git/phantom plumbing helpers under `scripts/`, their `.md` siblings, and their 6 Bash `test-*.sh` harnesses are deleted. Every deleted path is appended to `python/migrated-scripts.tsv` with `#3692`.
- Every live consumer (Python modules, survivor `scripts/lib-phantom-probe.sh`, `skills/implement` + `skills/research` docs and scripts, `Makefile`, `agent-lint.toml`, `docs/`, `.claude/skills/audit-runs`, and the implement static harnesses) calls the `git` / `push` / `git phantom-probe` verbs through `cli.py` directly, or the `$SCRIPT_DIR/../python/cli.py` form inside survivors. No live retired-helper path reference remains outside `python/migrated-scripts.tsv`, `CHANGELOG.md`, or excluded logs.
- `scripts/lib-phantom-probe.sh` survives, delegates to `cli.py git phantom-probe` without requiring `CLAUDE_PLUGIN_ROOT`, and does not double-append phantom warnings.
- Parity is preserved: fail-open parse exits for `snapshot-untracked` and `check-remote-branch`; intentional legacy stderr prefixes (for example `git-commit.sh:`) kept; phantom warning appended exactly once.
- `make lint-retired-scripts`, `make py-lint`, `make py-test`, and `make lint` are clean. The implement static harnesses (`make test-implement-structure`, `make test-implement-step8-exit3-first-fixer`, `make test-implement-fence-shape`) pass. No test-coverage regression.

diff_lines: 3215
