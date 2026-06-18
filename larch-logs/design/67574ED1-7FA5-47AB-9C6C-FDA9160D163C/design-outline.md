## Proposed Design Outline

### Goals
- Port the Step 5b prepare and annotate orchestration bodies from bash into `python/design_lifecycle.py`
- Replace the fat bash wrappers with thin `python3 cli.py design step5b-*` delegation scripts
- Wire up tests and migrated-scripts manifest entries

### Non-goals
- Porting `design-step5c.sh`, `design-step6*`, final-summary, or clarify bodies (other G6.x pieces)
- Changing the behavior of `design_oos.py` `file_oos_prepare_main` / `file_oos_annotate_main`
- Adding a separate Python entrypoint for the `design-step5.sh` compatibility wrapper

### Approach sketch
- Add `step5b_prepare_main` and `step5b_annotate_main` to `python/design_lifecycle.py`, porting the pause check, sentinel writes, timing mark, subprocess call, KV output parsing, and error-logging logic from the bash scripts
- Register `("design", "step5b-prepare")` and `("design", "step5b-annotate")` in `python/cli.py` _REGISTRY and _MACHINE_STDOUT_KEYS
- Replace `design-step5b-prepare.sh` and `design-step5b-annotate.sh` with thin wrappers that call `python3 cli.py design step5b-prepare` / `step5b-annotate`
- Update `design-step5.sh` to delegate to `python3 cli.py design step5b-prepare` directly instead of the bash script
- Add tests in `python/test_design_oos.py` covering the prepare and annotate wrapper orchestration; extend `test_design_cli_ports.py`
- Record retired paths in `python/migrated-scripts.tsv`

### Surfaces in scope
- `python/design_lifecycle.py` — new entrypoints
- `python/cli.py` — routing rows and machine-stdout keys
- `skills/design/scripts/design-step5b-prepare.sh` — replace with thin wrapper
- `skills/design/scripts/design-step5b-annotate.sh` — replace with thin wrapper
- `skills/design/scripts/design-step5.sh` — update delegation target
- `python/test_design_oos.py` — new tests for orchestration wrapper behavior
- `python/test_design_cli_ports.py` — add new verbs to EXPECTED
- `python/migrated-scripts.tsv` — retired path entries
- `skills/design/scripts/design-step5b-prepare.md` / `design-step5b-annotate.md` — update docs

### Open questions
- None.
