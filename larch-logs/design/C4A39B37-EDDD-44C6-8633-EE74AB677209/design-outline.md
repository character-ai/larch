## Proposed Design Outline

### Goals
- Port all 11 `/design` Step-0/1 bash bodies into `python/design_lifecycle.py`, running in-process behind `python3 python/cli.py design <verb>`.
- Repoint every SKILL.md Step-0/1 fence to the new CLI verbs and complete the full hard cutover (delete bash, manifest, lint).
- Preserve PID-keyed session isolation, rehydration, pause/resume, and every orchestrator-parsed contract grammar.

### Non-goals
- No port of G5/G6 bodies (Step 2+ orchestration); only Step-0/1.
- No change to pause/resume wire bytes or `docs/issue-anchored-plan.md` payload fields.
- No refactor of shared `design_lifecycle.py` helpers beyond what the port needs (limit G5/G6 conflict surface).

### Approach sketch
- Add one Python verb per body to `design_lifecycle.py`; register each in `cli.py` `_REGISTRY` (lazy import).
- Fold each wrapper's glue (source-env read, `.pause-requested` -> `pause-save`, folded sentinel writes, issue fetch, result-env reads) into the verb so behavior is preserved.
- Keep the per-PID launcher transport from `python/session_env.py` so fences stay session-isolated; the launcher dispatches the new verbs.
- Cover the verbs with colocated pytest in `python/test_design_lifecycle.py` (fd-3/stdout contracts, route verdicts, pause/resume, degraded-tools gate).

### Surfaces in scope
- `python/design_lifecycle.py`, `python/cli.py`, `python/test_design_lifecycle.py`.
- `python/session_env.py` (launcher dispatch) and `python/design_argv.py` (parse-argv) as needed.
- `skills/design/SKILL.md` Step-0/1 fences.
- The 11 `design-step0-*.sh` / `design-step1d*.sh` / `design-step1e-reentry.sh` bodies + their `.md` and `test-*.sh` siblings (delete).
- `python/migrated-scripts.tsv`.

### Open questions
- Launcher-dispatch shape: launcher invokes `python3 cli.py design <verb>` vs. fence calls Python directly with a baked `--session-env-path`. Resolve in plan drafting; reviewers verify.
- Whether `session_env.py`'s launcher template needs changes to dispatch verbs vs. wrapper basenames.
