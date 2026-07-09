# Progress reporting

Larch installs a clone-local Claude Code statusline so long `/design`, `/implement`, and review phases can show progress without adding text to the conversation.

## What appears

The statusline reads the latest breadcrumb for the current clone and active run ID, then renders it in yellow:

```text
larch 14:03: [implement 5] Step 5 — code review started
```

Breadcrumbs are one-line human events, not bare counters. For example, review code should write `reviewers 7/12 done`, not `reviewers 7/12`. Breadcrumbs identify GitHub entities by number, such as `PR #6626`, and do not include URLs.

## Run-scoped storage

Breadcrumbs are scoped by clone and active run ID. The active pointer is `~/.cache/larch/progress/<clone-hash>/current`, and the active breadcrumb log is `~/.cache/larch/progress/<clone-hash>/<run-id>/breadcrumbs.log`.

Default writers require a valid `current` pointer. When the clone progress directory, pointer, run ID, run directory, or log path is missing, invalid, unreadable, corrupt, or symlinked, default writes no-op fail silent. The explicit `progress note --run-id` override writes the named run log without changing `current`.

The reader follows `current` through a no-create fd-relative clone-directory traversal and tails only the active run log. Legacy flat `<clone-hash>.log` files are ignored. A fresh run starts empty because `activate_run` points `current` at a new run directory.

Fresh Claude session starts clear the clone's active `current` pointer before statusline installation. This prevents stale prior-run breadcrumbs from appearing before a new run starts. The first visible larch statusline entry after a fresh session should come from the new run's first breadcrumb. Resume and compact events preserve `current` to avoid hiding active work, and live bgjobs protect their breadcrumbs from SessionStart reset. The reset deletes only `current`; run directories and `breadcrumbs.log` files remain available for cleanup and audit.

Larch assumes one active larch run per clone. It does not add concurrency semantics for simultaneous `/design` and `/implement` runs in the same checkout.

## Installation and opt out

Session setup and the `SessionStart` hook idempotently merge a larch-owned `statusLine` command into `.claude/settings.local.json` for the current clone. The project-local setting uses `refreshInterval: 2` and a stable launcher at `~/.cache/larch/statusline.sh`.

Set `LARCH_STATUSLINE_DISABLE=1` before session start to skip installation. If `.claude/settings.local.json` contains invalid JSON, a symlinked target, or a non-larch local `statusLine`, larch leaves it untouched.

If you already have a user-scope statusline, larch chains it first and appends larch output. A local non-larch statusline wins and is not overwritten.

## Staleness

Progress files live under `~/.cache/larch/progress/`. The reader is fail silent: missing, empty, unreadable, or corrupt active-run state produces empty stdout and exit 0. When the active run log is old and no live bgjob registry row matches the clone, the statusline appends `(stale Nm)`; well after the stale threshold it renders nothing. Prior run logs do not affect staleness unless `current` points at that run.

## Detailed reports

The detailed end-of-run review Gantt remains available through the final-report `render-phase-detail` surface. The old typed `p` / `progress` prompt hook and `progress report` command are retired; the statusline replaces them for live progress.
