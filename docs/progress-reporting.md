# Progress reporting

Larch installs a clone-local Claude Code statusline so long `/design`, `/implement`, and review phases can show progress without adding text to the conversation.

## What appears

The statusline reads the latest breadcrumb for the current clone and renders it in yellow:

```text
larch 14:03: [implement 5] Step 5 — code review started
```

Breadcrumbs are one-line human events, not bare counters. For example, review code should write `reviewers 7/12 done`, not `reviewers 7/12`. Breadcrumbs identify GitHub entities by number, such as `PR #6626`, and do not include URLs.

## Installation and opt out

Session setup and the `SessionStart` hook idempotently merge a larch-owned `statusLine` command into `.claude/settings.local.json` for the current clone. The project-local setting uses `refreshInterval: 2` and a stable launcher at `~/.cache/larch/statusline.sh`.

Set `LARCH_STATUSLINE_DISABLE=1` before session start to skip installation. If `.claude/settings.local.json` contains invalid JSON, a symlinked target, or a non-larch local `statusLine`, larch leaves it untouched.

If you already have a user-scope statusline, larch chains it first and appends larch output. A local non-larch statusline wins and is not overwritten.

## Staleness

Progress files are per clone under `~/.cache/larch/progress/`. The reader is fail silent: missing, empty, unreadable, or corrupt files produce empty stdout and exit 0. When a breadcrumb is old and no live bgjob registry row matches the clone, the statusline appends `(stale Nm)`; well after the stale threshold it renders nothing.

## Detailed reports

The detailed end-of-run review Gantt remains available through the final-report `render-phase-detail` surface. The old typed `p` / `progress` prompt hook and `progress report` command are retired; the statusline replaces them for live progress.
