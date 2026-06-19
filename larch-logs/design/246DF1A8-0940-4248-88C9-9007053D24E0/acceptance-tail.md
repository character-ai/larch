
## Acceptance

- All consumers (skills, scripts, python modules, docs, Makefile, hooks) call the `git` / `push` / `git phantom-probe` verbs via `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py"` directly, or the `$SCRIPT_DIR/../python/cli.py` form inside survivor scripts. No live retired-bash-helper path reference remains outside `python/migrated-scripts.tsv`, `CHANGELOG.md`, or excluded logs.
- The ~19 retired `.sh` helpers, their `.md` siblings, and their obsolete bash `test-*.sh` harnesses are deleted. Survivors (`create-pr.sh`, `merge-pr.sh`, `rebase-checkpoint-probe.sh`, `lib-phantom-probe.sh`) remain and call `cli.py` directly.
- Every deleted path is appended to `python/migrated-scripts.tsv` with `#3692`.
- Each retired git/push verb is registered in `_MACHINE_STDOUT_KEYS`, so quiet parents capture `PUSHED` / `STATUS` / `COMMITTED` on stdout, not fd 3.
- `python/git.py`, `python/push.py`, and `python/phantom.py` preserve flag, exit-code, and stdout/stderr parity with the retired scripts; any gap is fixed in this PR. Legacy stderr prefixes stay as intentional parity output.
- `python/test_git.py`, `python/test_push.py`, and `python/test_phantom.py` cover every deleted bash harness; no test-coverage regression.
- `make lint-retired-scripts`, `make py-lint`, `make py-test`, and `make lint` are clean.

diff_lines: 2850
