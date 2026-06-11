## Proposed Design Outline

### Goals
- Port 10 bash scripts (~2800 lines) to three Python modules: `bootstrap.py`, `admission.py`, `dirty_tree.py`.
- Register CLI verbs under `bootstrap`, `admission`, and `dirty-tree` domains in `python/cli.py`.
- Replace bash test harnesses with colocated pytest covering the same behavioral contracts.

### Non-goals
- Porting `skills/implement/scripts/step-0-bootstrap.sh` to Python (it stays bash, updated to call Python CLI verbs).
- Deleting `scripts/lib-dirty-tree-sidecar.sh` (updated to call Python CLI; deletion is B4's job when `launch-review.sh` is migrated).
- Changing any exit-code contract, KV output format, or --emergency bypass semantics of the ported scripts.

### Approach sketch
- Port each script group to a Python module; expose importable functions and register CLI verbs per the migration playbook.
- Group A → `python/bootstrap.py`: 4-phase bootstrap (infra/tracking/plan/coder), invoke wrapper, routing-envelope parser.
- Group B → `python/admission.py`: admission gate (all 5 exit codes preserved), preflight check, fork-env setup.
- Group C → `python/dirty_tree.py`: mid-run dirty-tree detection (baseline + checkpoint modes), dirty-tree sidecar helper, recovery-paths scope check, scope-reduction marker check.
- Cut over `step-0-bootstrap.sh` and `/implement` SKILL.md to call `python3 cli.py bootstrap ...` / `python3 cli.py admission ...` verbs.
- Write `python/test_bootstrap.py`, `python/test_admission.py`, `python/test_dirty_tree.py`; delete absorbed bash + `.md` siblings; append to `python/migrated-scripts.tsv`.

### Surfaces in scope
- `python/bootstrap.py` (new)
- `python/admission.py` (new)
- `python/dirty_tree.py` (new)
- `python/test_bootstrap.py` (new)
- `python/test_admission.py` (new)
- `python/test_dirty_tree.py` (new)
- `python/cli.py` (registry additions)
- `skills/implement/scripts/step-0-bootstrap.sh` (cutover)
- `skills/implement/SKILL.md` (cutover references)
- `scripts/lib-dirty-tree-sidecar.sh` (updated to call Python CLI)
- 10 bash scripts + `.md` siblings + test harnesses deleted
- `python/migrated-scripts.tsv` (appended)

### Open questions
- None.
