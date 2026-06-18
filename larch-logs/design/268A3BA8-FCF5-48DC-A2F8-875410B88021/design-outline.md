## Proposed Design Outline

### Goals
- Port bodies of 6 design Step-2 Bash scripts to Python (`design_drafter.py` + `plan_quality.py`).
- Register new CLI verbs in `cli.py`; add colocated pytest in `test_design_drafter.py`.
- Reduce the 6 `.sh` files to thin delegation wrappers calling `python3 cli.py design <verb>`.

### Non-goals
- Porting `launch-codex-drafter.sh` / `launch-claude-drafter.sh` (vendor launchers stay Bash).
- Deleting the 6 `.sh` wrapper files (launcher enforces `*.sh`; they become thin stubs).
- Changing the `design-run-$PPID.sh` launcher mechanism.

### Approach sketch
- Create `python/design_drafter.py` for step2a sentinel-prep, step2b-prelude, step2b-drafter orchestration, step2b-postplan delegation, and step2b5 plan-check wrapper.
- Add `validator_autofix_main` to `python/plan_quality.py` (validator-autofix body).
- Register new `design` verbs: `sentinel-prep`, `step2b-prelude`, `step2b-drafter`, `step2b-postplan`, `step2b5`, `validator-autofix`.
- Rewrite each `.sh` file as a ~20-line thin delegation stub.
- Delete the 6 `.md` siblings; append paths to `python/migrated-scripts.tsv`.
- Update `_dbg-validator.sh` to call `python3 cli.py design validator-autofix`.
- Update SKILL.md wrapper inventory (remove stale test harness entries; add new Python module names).

### Surfaces in scope
- `python/design_drafter.py` (new)
- `python/plan_quality.py` (`validator_autofix_main` addition)
- `python/cli.py` (6 new verb registrations)
- `python/test_design_drafter.py` (new)
- `skills/design/scripts/design-step2{a,b-prelude,b-drafter,b-postplan,b5}.sh` + `design-step-validator-autofix.sh` (thin wrapper rewrites)
- `skills/design/scripts/_dbg-validator.sh` (update to call Python)
- 6 `.md` siblings (delete)
- `python/migrated-scripts.tsv` (append 6 entries)
- `skills/design/SKILL.md` (wrapper inventory cleanup)

### Open questions
- `design-step2b5.sh` already calls `python3 cli.py plan check-size` directly. Does it need a new `design step2b5` verb, or is a thinner `.sh` stub calling `plan check-size` sufficient?
