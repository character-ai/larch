#!/usr/bin/env bash
# Combined /design wrapper. Keep in sync with skills/design/SKILL.md.
# shellcheck disable=SC1090,SC1091,SC2154
set -euo pipefail
SESSION_ENV_PATH=""
CLAUDE_PID=""
REENTRY=false
while [ "$#" -gt 0 ]; do
  case "$1" in
    --session-env-path) SESSION_ENV_PATH="$2"; shift 2 ;;
    --claude-pid) CLAUDE_PID="$2"; shift 2 ;;
    --reentry) REENTRY=true; shift ;;
    *) printf '%s\n' "$0: unknown argument: $1" >&2; exit 2 ;;
  esac
done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

_step3_entry_panel_init_failed_exit() {
  local _reason="${1:-panel-init-failed}"
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review prelaunch-failure \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --reason "$_reason"
  printf '%s\n' 'SUMMARY_OUTCOME=failed-judge-panel'
  exit 1
}
DESIGN_TMPDIR="${DESIGN_TMPDIR:-}"
if [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  # shellcheck source=/dev/null
  . "$SESSION_ENV_PATH"
fi
if [ -z "${DESIGN_TMPDIR:-}" ]; then
  printf '%s\n' "/design Step 3 entry: DESIGN_TMPDIR required" >&2
  exit 1
fi
python3 "$SCRIPT_DIR/../../../python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR" || exit 2
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
if [ "$REENTRY" = true ]; then
  : > "$DESIGN_TMPDIR/.step3-reentry"
  rm -f "$DESIGN_TMPDIR/oos-aggregate-pool.md"
fi
rm -f "$DESIGN_TMPDIR/.pause-save-complete"
"$SCRIPT_DIR/design-step3-entry-state.sh" --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID"
[ -f "$DESIGN_TMPDIR/.pause-save-complete" ] && exit 0
if ! python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan-review snapshot-pre-review \
  --design-tmpdir "$DESIGN_TMPDIR"; then
  printf '%s\n' "**⚠ Step 3: failed to snapshot plan.txt before reviewer launch**" >&2
  _step3_entry_panel_init_failed_exit snapshot-pre-review-failure
fi
_scope_anchor="$DESIGN_TMPDIR/plan-review-scope-anchor.txt"
_had_issue_body=false
_scope_body="$(mktemp "${TMPDIR:-/tmp}/larch-plan-review-scope.XXXXXX")" || {
  printf '%s\n' "**⚠ Step 3: could not allocate plan-review scope anchor staging file; aborting before reviewer launch**" >&2
  _step3_entry_panel_init_failed_exit scope-staging-file-failure
}
_scope_stripped="$(mktemp "${TMPDIR:-/tmp}/larch-plan-review-scope-stripped.XXXXXX")" || {
  rm -f "$_scope_body"
  printf '%s\n' "**⚠ Step 3: could not allocate stripped issue body staging file; aborting before reviewer launch**" >&2
  _step3_entry_panel_init_failed_exit scope-staging-file-failure
}
if [ -s "$DESIGN_TMPDIR/issue-body.txt" ]; then
  _had_issue_body=true
  if ! python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan-block strip-body \
    --file "$DESIGN_TMPDIR/issue-body.txt" \
    --output "$_scope_stripped" >/dev/null; then
    rm -f "$_scope_body" "$_scope_stripped"
    printf '%s\n' "**⚠ Step 3: failed to strip prior larch:plan block from issue body; aborting before reviewer launch**" >&2
    _step3_entry_panel_init_failed_exit strip-body-failure
  fi
else
  : >"$_scope_stripped"
fi
{
  if [ -n "${ISSUE_TITLE:-}" ]; then
    printf '# %s\n\n' "$ISSUE_TITLE"
  fi
  if [ -s "$_scope_stripped" ]; then
    cat "$_scope_stripped"
  elif [ "$_had_issue_body" != true ] && [ -s "$DESIGN_TMPDIR/feature-description.txt" ]; then
    _scope_fd_stripped="$(mktemp "${TMPDIR:-/tmp}/larch-plan-review-scope-fd.XXXXXX")" || true
    if [ -n "${_scope_fd_stripped:-}" ] && python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan-block strip-body \
      --file "$DESIGN_TMPDIR/feature-description.txt" \
      --output "$_scope_fd_stripped" >/dev/null 2>&1 && [ -s "$_scope_fd_stripped" ]; then
      cat "$_scope_fd_stripped"
    fi
    rm -f "${_scope_fd_stripped:-}"
  elif [ "${POSITIONAL_KIND:-}" = verbal ] && [ -n "${POSITIONAL_VALUE:-}" ]; then
    printf '%s\n' "$POSITIONAL_VALUE"
  fi
  if [ -s "$DESIGN_TMPDIR/design-outline.md" ] && [ -f "$DESIGN_TMPDIR/.outline-approved" ]; then
    printf '\n## Approved direction (outline)\n\n'
    cat "$DESIGN_TMPDIR/design-outline.md"
  fi
} >"$_scope_body"
rm -f "$_scope_stripped"
if [ ! -s "$_scope_body" ]; then
  rm -f "$_scope_body" "$_scope_anchor"
  printf '%s\n' "**⚠ Step 3: plan-review-scope-anchor.txt would be empty; aborting before reviewer launch**" >&2
  _step3_entry_panel_init_failed_exit scope-anchor-empty
fi
mv "$_scope_body" "$_scope_anchor"
if ! python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" scope-anchor validate \
  --mode design \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --path "$_scope_anchor" >/dev/null; then
  printf '%s\n' "**⚠ Step 3: plan-review-scope-anchor.txt failed validation; aborting before reviewer launch**" >&2
  _step3_entry_panel_init_failed_exit scope-anchor-validation-failure
fi
"$SCRIPT_DIR/design-step3-entry-preview.sh" --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID"
