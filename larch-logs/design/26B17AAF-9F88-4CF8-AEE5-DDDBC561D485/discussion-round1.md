## Decision 1: Tier
- **Question**: Should this run SIMPLE or HARD (3 external architecture sketches)?
- **Resolution**: Keep SIMPLE — skip sketches, go straight to plan authoring.
- **Source**: user

## Decision 2: Module structure
- **Question**: Should all 10 scripts go into one module or split by concern?
- **Resolution**: Split by concern — three new/updated modules:
  - Group A (bootstrap machinery): `python/bootstrap.py`
  - Group B (admission/entry): `python/admission.py`
  - Group C (in-run checks): `python/dirty_tree.py` (new; not checks.py which is the ship-pr lint/fix loop)
- **Source**: user

## Decision 3: lib-dirty-tree-sidecar.sh consumer scope
- **Question**: lib-dirty-tree-sidecar.sh is only sourced by launch-review.sh (B4 scope). Can C4a delete it?
- **Resolution**: C4a ports check-mid-run-dirty-tree.sh to dirty_tree.py and registers its CLI verbs. lib-dirty-tree-sidecar.sh is updated to call the Python CLI (replacing the bash invocation) but NOT deleted in C4a; B4 deletes it when launch-review.sh is migrated. This avoids breaking launch-review.sh before B4 lands.
- **Source**: codebase (launch-review.sh is the only caller; B4 is the responsible issue)

## Decision 4: step-0-bootstrap.sh cutover
- **Question**: Does step-0-bootstrap.sh get ported to Python itself?
- **Resolution**: No — step-0-bootstrap.sh is NOT in the "Absorbs" list. It stays as bash but is updated to call Python CLI verbs (python3 cli.py bootstrap ...) instead of the old bash scripts it currently invokes.
- **Source**: codebase (not listed in issue absorbs list; stays as orchestrator wrapper)

## Decision 5: Hard constraints to preserve exactly
- **Question**: What must be preserved exactly?
- **Resolution**: Preflight plan-presence/adequacy gates and refuse exit 3 (docs/issue-anchored-plan.md); --emergency bypass semantics in implement-admission.sh; all exit codes from implement-admission.sh (0, 2, 4, 5, 6, 7); check-mid-run-dirty-tree.sh's baseline/checkpoint mode contract; check-scope-reduction-marker.sh's Python-inline implementation (already Python, just needs a CLI wrapper).
- **Source**: issue body ("preserved exactly"), codebase inspection
