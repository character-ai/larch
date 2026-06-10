## Proposed Design Outline

### Goals
- Zero-turn, zero-API-call on-demand progress report: typing `p` or `progress` shows a live status without consuming model context.
- Skill/step-aware report engine in `python/progress_report.py` dispatched via `cli.py progress report`.
- Hook shim `scripts/hook-progress-report.sh` registered under `UserPromptSubmit` in `hooks/hooks.json`.

### Non-goals
- No statusline liveness snippet.
- No component-written `progress.txt` for fine-grained sub-step tracking (v1 uses derive-only step determination).
- No native Python rendering of the Step 5 table (deferred to sh-to-py B3/C2 port; v1 shells out to `render-review-phase-detail.sh`).
- No richer `/design` renderers beyond generic fallback.

### Approach sketch
- Add `UserPromptSubmit` hook in `hooks/hooks.json`; shim reads stdin JSON, exact-matches `p`/`progress`, fails open on any error.
- New `python/progress_report.py` (stdlib-only): discovers live run via session pointer files under `~/.cache/larch/sessions/`, dispatches per-(skill, step) renderer.
- New `session write-implement-env` verb in `session_env.py` writes `~/.cache/larch/sessions/current-implement-env-$PPID.sh`; called from `implement-bootstrap.sh`; companion `session clear-implement-pointer` called at Step 18 teardown.
- `progress/done` marker written inside `scripts/run-step5-review.sh` (on all exit paths via trap/return), scoped to Step 5 loop for issue #3878 Monitor watcher.
- Banner line added to SKILL.md Step 0 post-bootstrap print and Step 5 launch banner.

### Surfaces in scope
- `scripts/hook-progress-report.sh` (new)
- `python/progress_report.py` (new)
- `python/cli.py` (new `progress report` subcommand)
- `python/session_env.py` (new `write-implement-env` + `clear-implement-pointer` verbs)
- `scripts/implement-bootstrap.sh` (call new pointer writer after `IMPLEMENT_TMPDIR` established)
- `scripts/implement-bootstrap-invoke.sh` (pass `--claude-pid "$PPID"` through)
- `skills/implement/SKILL.md` (banner lines + Step 18 pointer clear)
- `scripts/run-step5-review.sh` (`progress/done` marker write)
- `hooks/hooks.json` (new `UserPromptSubmit` entry)
- `SECURITY.md` (new always-on prompt-path hook surface)
- Tests: `scripts/test-hook-progress-report.sh`, `python/test_progress_report.py`, Makefile targets

### Open questions
- None.
