#!/usr/bin/env bash
# step-8-oos-checkpoint.sh — run OOS disposition checkpoint and log missing Tool Failures rows.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
  # shellcheck source=/dev/null
  . "$IMPLEMENT_TMPDIR/plugin-root.env"
fi
[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || CLAUDE_PLUGIN_ROOT=$PLUGIN_ROOT
export CLAUDE_PLUGIN_ROOT
_oos_chk_err="$IMPLEMENT_TMPDIR/oos-disposition-checkpoint.stderr.log"
: >"$_oos_chk_err" 2>/dev/null || true
_oos_chk_args=(--implement-tmpdir "$IMPLEMENT_TMPDIR")
[ -n "${DESIGN_TMPDIR:-}" ] && _oos_chk_args+=(--design-tmpdir "$DESIGN_TMPDIR")
set +e
bash "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/oos-disposition-checkpoint.sh" \
  "${_oos_chk_args[@]}" \
  2>"$_oos_chk_err"
_oos_chk_rc=$?
set -e
_oos_already_logged=false
if [ "$_oos_chk_rc" -eq 1 ]; then
  if command grep -Fq 'Step step-8-oos-checkpoint —' "$IMPLEMENT_TMPDIR/execution-issues.md" 2>/dev/null \
    || { command grep -Fq 'step-8-oos-checkpoint' "$IMPLEMENT_TMPDIR/execution-issues.md" 2>/dev/null \
      && ! command grep -Fq 'step-8-oos-checkpoint-validation' "$IMPLEMENT_TMPDIR/execution-issues.md" 2>/dev/null; }; then
    _oos_already_logged=true
  fi
elif [ "$_oos_chk_rc" -eq 2 ]; then
  command grep -Fq 'step-8-oos-checkpoint-validation' "$IMPLEMENT_TMPDIR/execution-issues.md" 2>/dev/null && _oos_already_logged=true
else
  command grep -Fq 'step-8-oos-checkpoint-validation' "$IMPLEMENT_TMPDIR/execution-issues.md" 2>/dev/null && _oos_already_logged=true
fi
if [ "$_oos_chk_rc" -ne 0 ] && [ "$_oos_already_logged" = false ]; then
  _oos_fail_site=step-8-oos-checkpoint-validation
  [ "$_oos_chk_rc" -eq 1 ] && _oos_fail_site=step-8-oos-checkpoint
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" run-log append-failure \
    --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
    --site "$_oos_fail_site" \
    --tool oos-disposition-checkpoint.sh \
    --exit-code "$_oos_chk_rc" \
    --category "Tool Failures" \
    --output-file "$_oos_chk_err" \
    --redact || true
fi
printf 'OOS_CHECKPOINT_RC=%s\n' "$_oos_chk_rc"
[ "$_oos_chk_rc" -ne 0 ] && exit "$_oos_chk_rc"
exit 0
