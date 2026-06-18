# lib-implement-clone-tag.sh

Shared sourced-only helper for /implement Step 8 clone-tag derivation.

## Caller

`skills/implement/scripts/step-8-ship.sh` and `skills/implement/scripts/step-8-seed-initial.sh` source this helper before passing `--expected-tmpdir-basename-prefix` to Python.

## Contract

When `CLONE_TAG` is set, the helper exports it unchanged as `CLONE_TAG_FULL`. Otherwise it derives `CLONE_TAG_FULL` from `basename "$PWD"`, sanitizes to `A-Za-z0-9_-`, truncates to 32 bytes, and falls back to `_` when empty.

It also exports `EXPECTED_TMPDIR_BASENAME_PREFIX="claude-implement-${CLONE_TAG_FULL}-"`.

## Edit-in-sync

Keep this helper aligned with `python3 python/cli.py implement-finalize` `clone_basename_prefix()`. Seeded `EXPECTED_TMPDIR_BASENAME_PREFIX` must match the Step 8 ship driver so Step 18 cleanup verification does not depend on fallback masking.
