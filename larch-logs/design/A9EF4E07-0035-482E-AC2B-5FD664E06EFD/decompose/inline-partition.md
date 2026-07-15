## Pieces

### Piece 1: cli.py registry schema unification
- Scope: Merge _REGISTRY and _MACHINE_STDOUT_KEYS into a single dict with a machine_stdout bool per entry. Delete _DESIGN_LIFECYCLE_STDOUT_KEYS and the hand-maintained _MACHINE_STDOUT_KEYS literal (replace with computed alias). Update dispatch to unpack the bool. Keep existing facade routing intact (no module repoints in this piece).
- Firm-headings: python/larch/cli.py, python/tests/test_cli.py, python/tests/skills/_structure_design_specialized.py
- Acceptance: make py-lint passes; _MACHINE_STDOUT_KEYS is a computed alias; _DESIGN_LIFECYCLE_STDOUT_KEYS is deleted; dispatch unpacks 3 values; machine-stdout verbs set LARCH_QUIET_DISABLE=1; python3 python/cli.py design step0-session -- --help exits 0.
- Dependencies: none
- Size estimate: ~800 lines changed

### Piece 2: cli.py facade-routing repoints
- Scope: Repoint 28 design entries from design_lifecycle to sub-modules, 6 review entries from review_pipeline to sub-modules, 5 run-log entries from run_logs to run_log_commit/run_log_flush. Update test mocks.
- Firm-headings: python/larch/cli.py, python/tests/test_cli.py
- Acceptance: no registry entry has design_lifecycle as module; make py-lint passes; python3 python/cli.py design step0-session -- --help exits 0.
- Dependencies: blocked-by Piece 1
- Size estimate: ~800 lines changed
