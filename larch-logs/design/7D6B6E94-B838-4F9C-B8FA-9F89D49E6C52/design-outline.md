## Proposed Design Outline

### Goals
- Repoint every consumer of the ~19 listed git/phantom bash helpers to direct `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git …` / `git phantom-probe` calls, in one atomic hard-cutover PR.
- Delete the retired `.sh` + `.md` siblings + their bash `test-*` harnesses; append every deleted path to `python/migrated-scripts.tsv`.
- Land with `make lint-retired-scripts` and `make lint` clean, no test-coverage regression.

### Non-goals
- Re-porting logic (native `python/git.py` / `phantom.py` exist, parity-verified).
- Migrating non-listed scripts (`create-pr.sh`, `merge-pr.sh`, `lib-phantom-probe.sh`) beyond repointing references.
- Shim/forwarding `.sh` stubs or new abstractions.

### Approach sketch
- Parity-audit each retired script vs its `cli.py` verb (flags, exit codes, output); close any gap inside `python/git.py` / `phantom.py` in this slice.
- Repoint consumers across skills, scripts, python modules, docs, Makefile, and hook bodies to direct `cli.py` calls.
- Before deleting each bash harness, confirm `python/test_git.py` / `python/test_phantom.py` cover it; add pytest for gaps.
- Delete `.sh`/`.md`/harness files, append to the manifest, run `lint-retired-scripts`.

### Surfaces in scope
- `scripts/`: the ~19 retired `.sh` + `.md` siblings + their `test-*.sh`/`.md` harnesses.
- Consumers: `skills/implement/**`, `skills/research/SKILL.md`, `.claude/skills/audit-runs/SKILL.md`, `scripts/create-pr.sh`, `scripts/merge-pr.sh`, `scripts/rebase-checkpoint-probe.sh`, `scripts/lib-phantom-probe.sh`.
- `python/`: `git.py`, `phantom.py`, `push.py`, `rebase.py`, `admission.py`, `bootstrap.py`, `implement_dispatch.py`, `review_and_fix.py` + colocated `test_*.py`.
- `docs/linting.md`, `docs/workflow-lifecycle.md`, `Makefile`, `python/migrated-scripts.tsv`, `hooks/` bodies.

### Open questions
- `lib-phantom-probe.sh` (not in retire list): repointed-consumer survivor vs dead once `phantom-probe-with-warn.sh` goes — resolve in Step 2b audit.
- Whether `python/push.py` / `python/rebase.py` own the push/rebase verbs vs `git.py` — resolve in Step 2b audit.
