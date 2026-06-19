## Proposed Design Outline

### Goals
- Repoint every consumer of the ~19 git/phantom bash helpers to direct `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git …` / `push …` / phantom-probe calls, in one hard-cutover PR.
- Delete the retired `.sh` + `.md` siblings + bash test harnesses; append every deleted path to `python/migrated-scripts.tsv`.
- Land with `make lint-retired-scripts` and `make lint` clean and no test-coverage regression.

### Non-goals
- Re-porting logic. Native `python/git.py` / `phantom.py` exist and are parity-verified.
- Migrating non-listed scripts (`create-pr.sh`, `merge-pr.sh`, `lib-phantom-probe.sh`) beyond repointing their references.
- Shim or forwarding `.sh` stubs, or any new abstraction layer.

### Approach sketch
- Parity-audit each retired script against its `cli.py` verb (flags, exit codes, output); close any gap inside `python/git.py` / `phantom.py` (Decision 1).
- Repoint consumers across skills, scripts, python modules, docs, Makefile, and hook bodies to direct `cli.py` calls.
- Before deleting each bash harness, confirm `python/test_git.py` / `python/test_phantom.py` cover it; add pytest cases for gaps (Decision 2).
- Delete `.sh` / `.md` / harness files, update `python/migrated-scripts.tsv`, run `make lint-retired-scripts`.

### Surfaces in scope
- `scripts/`: the ~19 retired `.sh` + `.md` siblings + their `test-*.sh` / `.md` harnesses.
- Consumers: `skills/implement/**`, `skills/research/SKILL.md`, `.claude/skills/audit-runs/SKILL.md`, `scripts/create-pr.sh`, `scripts/merge-pr.sh`, `scripts/rebase-checkpoint-probe.sh`, `scripts/lib-phantom-probe.sh`.
- `python/`: `git.py`, `phantom.py`, `push.py`, `rebase.py`, `admission.py`, `bootstrap.py`, `implement_dispatch.py`, `review_and_fix.py` + colocated `test_*.py`.
- `docs/linting.md`, `docs/workflow-lifecycle.md`, `Makefile`, `python/migrated-scripts.tsv`, `hooks/` bodies.

### Open questions
- None. The two prior open questions (lib-phantom-probe.sh survival; push/rebase domain ownership) were resolved by codebase audit on 2026-06-19. The exhaustive consumer list is a Step 2b grep-audit discovery task, not a user decision.
