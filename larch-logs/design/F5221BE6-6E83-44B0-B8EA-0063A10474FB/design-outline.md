## Proposed Design Outline

### Goals
- Make every post-Step-0 `/implement` Bash fence reliably resolve and invoke its launcher from a brand-new Bash tool call, eliminating the exit-127 failure in #6090.
- Mirror `/design`'s own already-working PID-keyed launcher pattern (`$PPID`/`$HOME`-only resolution, no export or shell-state carryover needed).

### Non-goals
- Do not touch `$IMPLEMENT_TMPDIR` occurrences used as argument values (e.g. `--implement-tmpdir "$IMPLEMENT_TMPDIR"`); those stay the orchestrating agent's literal-substitution job, unchanged by this fix.
- Do not rewrite `larch-run.sh`'s internal dispatch/cleanup logic; the new launcher is a thin delegator in front of the unchanged script.
- Do not add Step 18 cleanup for the new launcher file — parity with `/design`'s own never-cleaned `design-run-$PID.sh`.
- Do not touch `python/bootstrap.py`'s CLI argv or `BootstrapOptions`: `step-0-bootstrap.sh` already exports `LARCH_CLAUDE_PID="${LARCH_CLAUDE_PID:-$PPID}"` before invoking bootstrap, so the pid reaching `session write-implement-env` is already correct.

### Approach sketch
- Add `_implement_run_path` / `_implement_run_launcher_text` / `_write_implement_run_sh` to `python/larch/state/session_env.py`, mirroring the existing `_design_run_*` family; wire the write into the existing `write_implement_env_main` (already invoked with a real `$PPID`-derived pid).
- New fixed launcher `~/.cache/larch/sessions/implement-run-$PPID.sh` reads `IMPLEMENT_TMPDIR` from the existing PID-keyed pointer file (`current-implement-env-$PID.sh`) and `exec`s the unchanged `$IMPLEMENT_TMPDIR/larch-run.sh "$@"`.
- Mechanically replace the `bash "$IMPLEMENT_TMPDIR/larch-run.sh" ` fence prefix with `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" ` everywhere it appears as an orchestrator-issued fence (SKILL.md + its step references), excluding the one internal same-process script-to-script call.
- Update every structural test harness that pins the old literal fence text, plus add unit tests for the new launcher-writing helpers.
- Verify completeness with a repo-wide grep gate rather than a hand-maintained file list.

### Surfaces in scope
- `python/larch/state/session_env.py`
- `skills/implement/SKILL.md` and its step references/script docs that show the launcher fence
- `skills/review/SKILL.md` (one cross-reference to keep in sync)
- `scripts/test-implement-fence-shape.sh` (+ sibling `.md`), `scripts/test-implement-structure.sh`, `scripts/test-implement-timing-rehydration.sh`, `scripts/test-render-cost-line-callsites.sh`, `skills/implement/scripts/test-architectural-guidelines-step.sh`
- `python/tests/state/test_session_env.py`

### Open questions
- None.
