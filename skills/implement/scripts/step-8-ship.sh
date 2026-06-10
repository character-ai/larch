#!/usr/bin/env bash
# step-8-ship.sh — /implement Step 8+ active ship driver selector.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
  # shellcheck source=/dev/null
  . "$IMPLEMENT_TMPDIR/plugin-root.env"
fi
[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || CLAUDE_PLUGIN_ROOT=$PLUGIN_ROOT
export CLAUDE_PLUGIN_ROOT
if [ -n "${CLONE_TAG:-}" ]; then
  CLONE_TAG_FULL=$CLONE_TAG
else
  _clone_bt=$(basename "$PWD")
  CLONE_TAG_FULL=$(printf '%s' "$_clone_bt" | tr -c 'A-Za-z0-9_-' '_')
  CLONE_TAG_FULL=${CLONE_TAG_FULL%????????????????????????????????*}
  CLONE_TAG_FULL=$(printf '%.32s' "$CLONE_TAG_FULL")
  [ -n "$CLONE_TAG_FULL" ] || CLONE_TAG_FULL="_"
fi
if [ "${LARCH_SHIP_PR_IMPL:-python}" != "bash" ]; then
  if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    echo "ERROR: Python ship driver requires Python 3.11 or newer" >&2
    printf '%s\n' '{"detail":"Python ship driver requires Python 3.11 or newer","failed_run_id":"","merge_result":"","needs_user_reason":"","outcome":"STALLED","pr_number":null,"pr_url":""}'
    exit 4
  fi
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr \
    --branch "$BRANCH_NAME" \
    --issue "$ISSUE_NUMBER" \
    --repo "$REPO" \
    --run-id "$RUN_ID" \
    --tmpdir "$IMPLEMENT_TMPDIR" \
    --manifest-path "${MANIFEST_PATH:-}" \
    --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" \
    --tool-label "${coder:-claude}" \
    --merge "${merge:-false}" \
    --draft "${draft:-false}" \
    --forked "${forked_target:-false}" \
    --repo-unavailable "${REPO_UNAVAILABLE:-false}" \
    --no-admin-fallback "${no_admin_fallback:-false}" \
    --no-logs-commit "${no_logs_commit:-false}" \
    --expected-session-id "$(cat "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)" \
    --expected-tmpdir-basename-prefix "claude-implement-${CLONE_TAG_FULL}-"
else
"${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh" \
  --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" \
  --implement-tmpdir "$IMPLEMENT_TMPDIR" \
  --merge "${merge:-false}" \
  --draft "${draft:-false}" \
  --forked "${forked_target:-false}" \
  --branch-name "$BRANCH_NAME" \
  --expected-session-id "$(cat "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)" \
  --expected-tmpdir-basename-prefix "claude-implement-${CLONE_TAG_FULL}-" \
  --issue-number "$ISSUE_NUMBER" \
  --manifest-path "${MANIFEST_PATH:-}" \
  --run-id "$RUN_ID" \
  --tool-label "${coder:-claude}" \
  --no-admin-fallback "${no_admin_fallback:-false}" \
  --no-logs-commit "${no_logs_commit:-false}" \
  --repo "$REPO"
fi
