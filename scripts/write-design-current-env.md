# scripts/write-design-current-env.sh — contract

Writes a sourceable bash file that re-establishes the `/design` session
context (`$DESIGN_TMPDIR`, `$SESSION_TMPDIR`, `$SESSION_ID`,
`$CLAUDE_PLUGIN_ROOT`, reviewer presence/availability booleans,
`$ISSUE_NUMBER`) after each `Bash` tool call returns to a fresh subshell.
The Claude Code Bash tool does NOT preserve shell state between calls;
this writer plus the canonical conditional prelude in
`skills/design/SKILL.md` (`[ -f ~/.cache/larch/sessions/current-design-env.sh ] && source ~/.cache/larch/sessions/current-design-env.sh`)
restores it on every block from Step 1c onward.

## Outputs

- `--output <path>` — sourceable file, written atomically via `temp+mv`.
  Lines are `export KEY=<printf-%q-quoted-value>` so values containing
  spaces or shell metacharacters survive sourcing.
- `${HOME}/.cache/larch/sessions/current-design-env.sh` — stable symlink
  pointing at `--output`. Refreshed atomically via `ln -sfn`. This is the
  path the SKILL.md prelude line sources.

## Keys

Always writes `DESIGN_TMPDIR`, `SESSION_TMPDIR`, and `SESSION_ID`.
Optionally writes `ISSUE_NUMBER`, `CODEX_PRESENT`, `CURSOR_PRESENT`,
`CODEX_AVAILABLE`, `CURSOR_AVAILABLE`. Writes `CLAUDE_PLUGIN_ROOT`
whenever it is set in the writer's environment, mirroring
`scripts/write-session-env.sh`'s `LARCH_CLAUDE_PLUGIN_ROOT` shape but as
the directly-usable variable name (sourceable, not parsed).

## Validation

- `--session-id` matches `^[A-Za-z0-9_.-]{1,128}$`.
- `--design-tmpdir` and `--output` must be absolute paths.
- `--issue-number` matches `^[0-9]+$` when present.
- Presence/availability booleans must be `true` or `false`.

## Single-runner invariant

Only one `/design` may run per repository at a time (mirrors the
`/implement` single-runner invariant in `AGENTS.md`). The stable symlink
is a process-wide resource; concurrent `/design` invocations would
clobber it and corrupt later Bash blocks of the older run. Detection is
out of scope for this writer — the invariant is documented; locking is a
follow-up if needed.

## Edit-in-sync

Update `skills/design/SKILL.md` (the prelude line and Step 0 writer
call), `skills/design/scripts/test-write-design-current-env.sh` (regression
harness), and the Makefile registration when changing the writer's
public shape.
