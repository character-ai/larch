# scripts/write-design-current-env.sh — contract

Writes a sourceable bash file that re-establishes the `/design` session
context (`$DESIGN_TMPDIR`, `$SESSION_TMPDIR`, `$SESSION_ID`,
`$MANUAL_REQUESTED`, `$CLAUDE_PLUGIN_ROOT`, reviewer presence/availability booleans,
`$ISSUE_NUMBER`) after each `Bash` tool call returns to a fresh subshell.
The Claude Code Bash tool does NOT preserve shell state between calls;
this writer plus the canonical conditional prelude in
`skills/design/SKILL.md`
(`[ -f ~/.cache/larch/sessions/current-design-env-$PPID.sh ] && source ~/.cache/larch/sessions/current-design-env-$PPID.sh`)
restores it on every block from Step 1c onward.

## Outputs

- `--output <path>` — sourceable file, written atomically via `temp+mv`.
  Lines are `export KEY=<printf-%q-quoted-value>` so values containing
  spaces or shell metacharacters survive sourcing.
- `${HOME}/.cache/larch/sessions/current-design-env-<pid>.sh` — stable
  symlink (when `--claude-pid <pid>` is passed) pointing at `--output`.
  The symlink is replaced with `ln -sfn` (same target path as the file
  body write, but symlink replacement is not the same atomicity story as
  `temp+mv` on a regular file — treat races on the stable path as
  documented operational risk, not a single atomic rename). This is the
  path the SKILL.md prelude line sources.

## Keys

Always writes `DESIGN_TMPDIR`, `SESSION_TMPDIR`, and `SESSION_ID`.
Optionally writes `MANUAL_REQUESTED`, `ISSUE_NUMBER`, `CODEX_PRESENT`, `CURSOR_PRESENT`,
`CODEX_AVAILABLE`, `CURSOR_AVAILABLE`. Always writes
`LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` (default `30`, inheriting a numeric
process-env override such as `0` for opt-out) so later `/design` Bash blocks
and external launchers inherit the launch-time health gate without parsing
session files. Writes `CLAUDE_PLUGIN_ROOT`
whenever it is set in the writer's environment, mirroring
`scripts/write-session-env.sh`'s `LARCH_CLAUDE_PLUGIN_ROOT` shape but as
the directly-usable variable name (sourceable, not parsed).

**Refresh preservation (issue #3181)**: on a no-flag refresh (Step 0b / Step 5.5-bis
shape — only `--output`, `--design-tmpdir`, `--session-id`, and friends), the four
reviewer keys (`CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_AVAILABLE`, `CURSOR_AVAILABLE`)
are recovered from the existing `--output` file when the matching flag is omitted.
An explicit flag overrides the recovered value. When exactly one side of a
`*_PRESENT` / `*_AVAILABLE` alias pair is passed, the writer mirrors that value to
the omitted peer so a partial override cannot leave a stale peer (see harness Case 14).
`MANUAL_REQUESTED`, `REPO`, and `ISSUE_NUMBER` keep clear-on-omit behavior (harness
Case 12 for `MANUAL_REQUESTED`).
## `--claude-pid`

Required for normal `/design` operation: pass the Bash-tool subshell parent
PID (e.g. `--claude-pid "$PPID"`). In Claude Code, `$PPID` in each **top-level**
Bash-tool invocation has been observed to match the Claude Code process for
that session and to stay stable across Bash tool calls in the same session, so
different concurrent Claude sessions (including `/design` from different
working-tree clones) receive different symlink names and no longer clobber each
other's session env. **Do not** wrap the writer (or the prelude contract) in an
extra nested `bash` / `bash -c` invocation unless you deliberately re-thread
`--claude-pid` for the PID namespace that owns the symlink slot — otherwise
`$PPID` may refer to an intermediate shell, not Claude.

Validates the `--design-tmpdir` argument is under the allowlist via `larch_design_tmpdir_validate` after the existing absolute-path check; failure maps to argv exit 1 (preserving the script's exit-code contract).

Validation: `--claude-pid` must match `^[1-9][0-9]{0,6}$` (at most seven
decimal digits, no leading zero).

**Transition shim**: if `--claude-pid` is omitted, the writer falls back
to the legacy unkeyed path `current-design-env.sh` and prints a stderr
warning. Callers should migrate; the shim may be removed in a follow-up
release.

**Cross-skill audit**: only `/design` uses this machine-cache symlink
pattern. `/implement`, `/research`, and `/review` thread session state
via `SESSION_ENV_PATH`, explicit per-session paths, or other handoffs —
they are unaffected by this writer's symlink naming.

## Per-Claude-process symlink keying

Concurrent `/design` runs in **different** Claude Code processes each
pass a distinct `--claude-pid`, so each session owns its own symlink
slot under `~/.cache/larch/sessions/`. Multiple `/design` runs in the
**same** Claude session share one `$PPID` and therefore one slot;
sequential runs overwrite as intended. `/implement` does not rely on
this symlink (it uses `SESSION_ENV_PATH` and related contracts), so
concurrent `/implement` runs do not race on `current-design-env-*.sh`.

**Stale symlinks**: after Claude exits, PID-keyed symlinks may dangle;
the prelude's `[ -f ... ] &&` guard skips missing targets. `/cleanup`
reaps broken `current-design-env-*.sh` symlinks automatically; operators
may also prune manually, for example:

```bash
find ~/.cache/larch/sessions -name 'current-design-env-*.sh' -type l \
  ! -exec test -e {} \; -delete
```

## Validation

- `--session-id` matches `^[A-Za-z0-9_.-]{1,128}$`.
- `--design-tmpdir` and `--output` must be absolute paths.
- `--issue-number` matches `^[0-9]+$` when present.
- `CLAUDE_PLUGIN_ROOT`, when set, must be an absolute path of 512 characters or fewer using `[A-Za-z0-9_./~+-]`.
- `--manual-requested`, when present, must be `true` or `false`.
- When `--claude-pid` is passed, its value must be non-empty and match `^[1-9][0-9]{0,6}$`. Omitting the flag entirely selects the legacy shim (stderr warning).
- Presence/availability booleans must be `true` or `false`.

## Edit-in-sync

Update `skills/design/SKILL.md` (the prelude line and Step 0 writer
call), `skills/design/scripts/test-write-design-current-env.sh` (regression
harness), and the Makefile registration when changing the writer's
public shape. Update `skills/cleanup/scripts/cleanup.sh` when changing
dangling symlink reaping behavior.
