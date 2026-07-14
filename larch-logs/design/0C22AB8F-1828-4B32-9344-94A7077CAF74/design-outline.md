## Proposed Design Outline

### Goals
- Migrate all assertions from four Bash harnesses to `python/tests/implement/test_implement_shell_scripts.py`.
- Delete the four Bash harnesses after parity and remove every reference in Makefile, residual-bash-paths.txt, and contract docs.
- Tests invoke the real repository scripts via subprocess; no fixture copies.

### Non-goals
- Do not modify any runtime helper scripts (step-5-review.sh, step-8-ship.sh, step-18.sh, review-and-fix, etc.).
- Do not add new abstractions or shared Bash libraries.
- Do not port coverage for deleted machinery (test-step-8-assessment.sh removed by #7193).

### Approach sketch
- Create `python/tests/implement/test_implement_shell_scripts.py` with one class/section per source harness.
- For each harness: translate static-text assertions to `Path.read_text` substring checks and dynamic execution assertions to `subprocess.run` calls with stubbed env/binary trees.
- After all assertions map 1-to-1 to pytest nodes and pass, delete the four `.sh` harnesses.
- Update contract docs (`step-5-review.md`, `step-8-ship.md`, `step-18.md`, `test-implement-review-token-propagation.md`) to reference the pytest module.
- Remove Makefile focused targets and shard entries, remove residual-bash-paths.txt rows.

### Surfaces in scope
- `python/tests/implement/test_implement_shell_scripts.py` (new)
- `skills/implement/scripts/test-step-5-review.sh` (deleted)
- `skills/implement/scripts/test-step-8-ship.sh` (deleted)
- `skills/implement/scripts/test-step-18.sh` (deleted)
- `skills/implement/scripts/test-implement-review-token-propagation.sh` (deleted)
- `skills/implement/scripts/step-5-review.md`, `step-8-ship.md`, `step-18.md`, `test-implement-review-token-propagation.md` (updated)
- `Makefile` (remove 4 targets, update 3 shard lines)
- `scripts/residual-bash-paths.txt` (remove 3 rows)

### Open questions
- None.
