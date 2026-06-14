## Proposed Design Outline

### Goals
- Port all Step 2 dispatch logic (6 bash scripts) to Python with CLI verbs callable by `python3 python/cli.py`.
- Replace 5 bash harnesses with pytest; delete absorbed scripts and `.md` siblings.
- Cut all consumer call sites to direct `python/cli.py` verbs (SKILL.md, docs).

### Non-goals
- Changing codex/cursor implementer agent prompt contracts (unchanged per issue).
- Changing the manifest schema or SKILL.md Step 2 orchestrator logic beyond call-site cutover.
- Modifying the B4 `agents.py` public API surface (launchers are additive).

### Approach sketch
- New module `python/implement_dispatch.py`: step2 dispatch, recovery paths, commit-on-behalf, and flag-derive helper.
- Extend `python/agents.py` with `launch_codex_implement_main()` and `launch_cursor_implement_main()` (following the B4 CI launcher pattern).
- Register verbs: `implement step2-dispatch`, `implement run-dispatch`, `implement recovery-paths`, `implement commit`; `agent launch-codex-implement`, `agent launch-cursor-implement` in `cli.py`.
- Cut SKILL.md `larch-run.sh run-step2-dispatch.sh` call to `python3 python/cli.py implement run-dispatch`.
- Write `python/test_implement_dispatch.py` covering all stdout contracts, bail reasons, and envelope invariants.

### Surfaces in scope
- `python/implement_dispatch.py` (new)
- `python/test_implement_dispatch.py` (new)
- `python/agents.py` (additive: 2 launcher mains)
- `python/cli.py` (register 6 new verbs)
- `skills/implement/SKILL.md` (call-site cutover)
- `skills/implement/scripts/step2-implement.md` (update contract)
- `skills/implement/scripts/run-step2-dispatch.md` (update contract)
- `scripts/launch-codex-implement.md`, `scripts/launch-cursor-implement.md` (update)
- `python/migrated-scripts.tsv` (append deleted paths)
- Deleted: `step2-implement.sh`, `run-step2-dispatch.sh`, `compute-step2-recovery-paths.sh`, `commit-implementation.sh`, `launch-codex-implement.sh`, `launch-cursor-implement.sh` and all sibling `.md` + harness `.sh` files.

### Open questions
- None.
