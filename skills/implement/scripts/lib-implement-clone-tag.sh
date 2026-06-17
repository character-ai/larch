# shellcheck shell=bash
# Shared clone-tag derivation for /implement Step 8 ship state and driver wrappers.

if [ -n "${CLONE_TAG:-}" ]; then
  CLONE_TAG_FULL=$CLONE_TAG
else
  _clone_bt=$(basename "$PWD")
  CLONE_TAG_FULL=$(printf '%s' "$_clone_bt" | tr -c 'A-Za-z0-9_-' '_')
  CLONE_TAG_FULL=${CLONE_TAG_FULL%????????????????????????????????*}
  CLONE_TAG_FULL=$(printf '%.32s' "$CLONE_TAG_FULL")
  [ -n "$CLONE_TAG_FULL" ] || CLONE_TAG_FULL="_"
fi
export CLONE_TAG_FULL
EXPECTED_TMPDIR_BASENAME_PREFIX="claude-implement-${CLONE_TAG_FULL}-"
export EXPECTED_TMPDIR_BASENAME_PREFIX
