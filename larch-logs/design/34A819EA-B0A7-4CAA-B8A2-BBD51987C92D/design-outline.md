## Proposed Design Outline

### Goals
- Eliminate the two-line `--session-env-path`/`--claude-pid` boilerplate from 37+ post-Step-0a bash fences in SKILL.md.
- Write a session-keyed launcher (`design-run-$PPID.sh`) at Step 0a that bakes those args in once.
- Reduce copy-drift risk; `test-design-structure.sh` pins the new shape.

### Non-goals
- No changes to wrapper script internals (they still accept and use `--session-env-path`/`--claude-pid`).
- No changes to `/implement`'s `larch-run.sh` or its `bootstrap.py` write path.
- No new design-workflow behavior or flags.

### Approach sketch
- Add `_write_design_run_sh()` to `session_env.py`; call it from `write_design_env_main` after writing `source-env.sh`.
- The launcher bakes `PLUGIN_ROOT`, `SESSION_ENV_PATH`, `CLAUDE_PID` as literals; takes a basename, execs `$PLUGIN_ROOT/skills/design/scripts/$script --session-env-path ... --claude-pid ... "$@"`.
- SKILL.md: collapse 37+ post-Step-0a fences to `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" script.sh [extra args]`.
- Update `test-design-structure.sh` to validate the new launcher fence shape.
- Update the Bash block prelude prose and inline code in `approval-gates.md` / `discussion-rounds.md`.

### Surfaces in scope
- `python/session_env.py` — new helper + call in `write_design_env_main`
- `python/test_session_env.py` — launcher write tests
- `skills/design/SKILL.md` — 37+ fence collapses + prelude prose
- `skills/design/references/approval-gates.md` — 1 inline code update
- `skills/design/references/discussion-rounds.md` — 1 inline code update
- `scripts/test-design-structure.sh` — fence shape validator updates

### Open questions
- None.
