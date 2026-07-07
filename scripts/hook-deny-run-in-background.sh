#!/usr/bin/env bash
# PreToolUse hook: deny Bash run_in_background launches while a larch bgjob is active in this clone.
# Hooks are a trust boundary: malformed JSON is denied when background intent cannot be ruled out.

set -u

[ "${LARCH_HOOK_DENY_RUN_IN_BACKGROUND_DISABLE:-}" = "1" ] && exit 0
[ "${LARCH_CLAUDE_SUBPROCESS_HOOK_EXEMPT:-}" = "1" ] && exit 0

INPUT=$(cat 2>/dev/null) || INPUT=""

emit_deny() {
  local reason="$1"
  jq -cn --arg reason "$reason" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$reason}}'
}

emit_deny_no_jq() {
  local reason="$1"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
}

canonical_dir() {
  [ -n "$1" ] || return 1
  [ -d "$1" ] || return 1
  (cd "$1" 2>/dev/null && pwd -P)
}

clone_paths_same() {
  local marker_canon="$1" current_canon="$2"
  [ "$marker_canon" = "$current_canon" ] && return 0
  case "$current_canon" in "$marker_canon"/*) return 0 ;; esac
  case "$marker_canon" in "$current_canon"/*) return 0 ;; esac
  return 1
}

if ! command -v jq >/dev/null 2>&1; then
  case "$INPUT" in
    *run_in_background*) emit_deny_no_jq 'run_in_background denied: jq unavailable to validate Bash payload'; exit 0 ;;
    *) exit 0 ;;
  esac
fi

if ! printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1; then
  emit_deny 'run_in_background denied: malformed hook JSON cannot rule out Bash background launch'
  exit 0
fi

tool_name=$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null) || tool_name=""
[ "$tool_name" = "Bash" ] || exit 0
run_bg=$(printf '%s' "$INPUT" | jq -r '.tool_input.run_in_background // false' 2>/dev/null) || run_bg="parse-error"
command_text=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null) || command_text=""
case "$run_bg:$command_text" in
  true:*) ;;
  parse-error:*) emit_deny 'run_in_background denied: cannot parse Bash tool_input'; exit 0 ;;
  *:*run_in_background*true*) ;;
  *) exit 0 ;;
esac

cwd=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null) || cwd=""
cwd_canon=$(canonical_dir "$cwd" 2>/dev/null || true)
if [ -z "$cwd_canon" ]; then
  # No clone identity to compare, but the payload is definitely a background Bash launch.
  # In normal Claude hook envelopes cwd is present; deny to keep active-run sessions closed.
  emit_deny 'run_in_background denied: missing canonical cwd for Bash background launch'
  exit 0
fi

registry_root="${LARCH_BGJOB_REGISTRY_ROOT:-${HOME:-}/.cache/larch/daemons}"
[ -d "$registry_root" ] || exit 0

found_same_clone=0
for entry in "$registry_root"/*.env; do
  [ -f "$entry" ] && [ ! -L "$entry" ] || continue
  clone_path=$(awk -F= '$1 == "CLONE_PATH" { sub(/^[^=]*=/, ""); print; exit }' "$entry" 2>/dev/null || true)
  [ -n "$clone_path" ] || continue
  clone_canon=$(canonical_dir "$clone_path" 2>/dev/null || true)
  [ -n "$clone_canon" ] || continue
  if clone_paths_same "$clone_canon" "$cwd_canon"; then
    found_same_clone=1
    break
  fi
done

if [ "$found_same_clone" = "1" ]; then
  emit_deny "run_in_background denied: active larch bgjob registry exists for this clone ($entry)"
fi

exit 0
