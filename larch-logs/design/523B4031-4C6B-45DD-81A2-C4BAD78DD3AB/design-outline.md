## Proposed Design Outline

### Goals
- Cut every live consumer of the 19 git/phantom Bash helpers over to `cli.py git` / `push` / `git phantom-probe` verbs.
- Delete the 19 `.sh` helpers, their `.md` siblings, and their Bash `test-*.sh` harnesses atomically in one PR.
- Proactively audit each verb for parity (flags, exit codes, stdout/stderr) and fix gaps in `python/git.py` / `push.py` / `phantom.py`.

### Non-goals
- Re-doing #4642 work (verb registration, create-pr/merge-pr/rebase-checkpoint-probe already deleted).
- Touching CHANGELOG, committed run-logs, or intentional legacy stderr prefixes inside the ports.
- Retiring `scripts/lib-phantom-probe.sh` or the unrelated `scripts/check-stale-plugin.sh`.

### Approach sketch
- Parity pass first: diff each helper against its verb; fix gaps in the Python ports + add pytest cases for any coverage gap before deletion.
- Repoint consumers: Python modules (admission, implement_dispatch, review_and_fix, rebase, bootstrap), survivor `lib-phantom-probe.sh`, implement/research skill docs, Makefile, agent-lint.toml, docs.
- Survivor `lib-phantom-probe.sh`: repoint internals to `cli.py git phantom-probe`; do not double-append warnings.
- Delete + record: append all deleted paths to `python/migrated-scripts.tsv` with `#3692`.
- Gate on `make lint-retired-scripts`, `make py-lint`, `make py-test`, `make lint` clean.

### Surfaces in scope
- `scripts/` (19 helpers + `.md` + `test-*.sh`; survivor `lib-phantom-probe.sh`).
- `python/` (git.py, push.py, phantom.py, admission.py, implement_dispatch.py, review_and_fix.py, rebase.py, bootstrap.py, test_git.py, test_push.py, test_phantom.py, migrated-scripts.tsv).
- `skills/implement/` + `skills/research/`, `Makefile`, `agent-lint.toml`, `docs/linting.md`, `docs/workflow-lifecycle.md`.

### Open questions
- None. Codebase audit confirmed no adjacent git/phantom helpers beyond the 19 + survivor.
