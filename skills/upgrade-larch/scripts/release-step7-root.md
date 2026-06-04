# release-step7-root.sh - contract

Sourced helper for `/release` Step 7 root resolution and shared plugin-version parsing.

## Purpose

`release-step7-root.sh` contains side-effect-light helpers used by the release prompt and `upgrade-larch.sh`:

- `get_installed_larch_version`
- `is_cache_shaped_larch_root`
- `single_larch_cache_version_dir`
- `resolve_release_step7_root`

The file may be sourced from Bash fences and scripts. It must not install traps, initialize quiet logging, change file descriptors, run upgrades, or mutate plugin state at source time.

## Resolution Order

`resolve_release_step7_root CURRENT_VERSION` returns the first defensible cache root:

1. Active `CLAUDE_PLUGIN_ROOT` when it is an existing cache-shaped larch version dir.
2. Installed metadata version when the matching cache dir exists.
3. `CURRENT_VERSION` when that dir exists and is the sole cache version dir.
4. No root when the cache is empty, ambiguous, or only contains a different stale version.

When metadata names a version whose cache dir is missing, resolution falls through to the `CURRENT_VERSION`/sole-cache checks instead of failing closed.

## Edit In Sync

- `skills/upgrade-larch/scripts/upgrade-larch.sh` sources this file for shared helpers.
- `.claude/skills/release/SKILL.md` documents the prompt-side Step 7 use.
- `skills/upgrade-larch/scripts/test-upgrade-larch-retention.sh` covers the root-resolution matrix.
