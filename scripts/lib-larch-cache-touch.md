# scripts/lib-larch-cache-touch.sh — contract

Sourced-only helper library for refreshing the executing larch cache root's
directory mtime. The primary behavior is consumed by `/upgrade-larch` prune
ordering, which keeps the most-recently-touched cache directories.

`larch_touch_executing_cache_root` accepts `--path <path>` and otherwise
defaults to `$CLAUDE_PLUGIN_ROOT`. It no-ops unless the path exists as a
directory and its basename matches the numeric version grammar
`^[0-9]+(\.[0-9]+)*$`. When accepted, it runs `touch -c` best-effort and
silently ignores filesystem errors.

Primary callers:

- `scripts/session-setup.sh`
- `scripts/write-session-env.sh`
- `scripts/write-design-current-env.sh`

Edit in sync with `skills/upgrade-larch/scripts/upgrade-larch.sh` and
`skills/upgrade-larch/scripts/upgrade-larch.md` when changing cache-retention
semantics.
