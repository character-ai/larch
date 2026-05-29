#!/usr/bin/env bash
# write-design-current-env.sh — Write a sourceable /design session-env file
# and refresh the stable symlink consumers source from every Bash block.
#
# Usage:
#   write-design-current-env.sh --output <path> \
#                               --design-tmpdir <path> \
#                               --session-id <id> \
#                               [--manual-requested <true|false>] \
#                               [--codex-present <true|false>] \
#                               [--cursor-present <true|false>] \
#                               [--codex-available <true|false>] \
#                               [--cursor-available <true|false>] \
#                               [--repo <owner/repo>] \
#                               [--issue-number <n>] \
#                               [--claude-pid <pid>]
#
# Output: writes a sourceable bash file at --output (atomic temp+mv), then
# updates a stable symlink under ~/.cache/larch/sessions/ pointing at
# --output (atomic ln -sfn). With --claude-pid, the symlink is
# current-design-env-<pid>.sh (one slot per Claude Code process). Omitting
# --claude-pid uses the legacy current-design-env.sh name and prints a stderr
# warning (transition shim). Values are shell-quoted via printf '%q' so paths
# containing spaces or shell metacharacters survive round-tripping through
# `source`.
#
# Callers should pass the Bash-tool subshell parent PID (e.g. --claude-pid
# "$PPID") from the root Bash-tool invocation so concurrent /design runs in
# different Claude sessions do not clobber each other's symlink. Wrapping the
# writer in an extra nested `bash`/`bash -c` layer can change which PID "$PPID"
# refers to; avoid that unless the caller re-handles --claude-pid explicitly.
#
# Exit codes: 0 success, 1 invalid args.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$SCRIPT_DIR/lib-design-tmpdir.sh"

OUTPUT=""
DESIGN_TMPDIR_ARG=""
SESSION_ID=""
MANUAL_REQUESTED=""
CODEX_PRESENT=""
CURSOR_PRESENT=""
CODEX_AVAILABLE=""
CURSOR_AVAILABLE=""
CODEX_PRESENT_SET=false
CURSOR_PRESENT_SET=false
CODEX_AVAILABLE_SET=false
CURSOR_AVAILABLE_SET=false
REPO=""
ISSUE_NUMBER=""
CLAUDE_PID=""
CLAUDE_PID_SPECIFIED=0
CLAUDE_PLUGIN_ROOT_VALUE="${CLAUDE_PLUGIN_ROOT:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)           OUTPUT="$2"; shift 2 ;;
    --design-tmpdir)    DESIGN_TMPDIR_ARG="$2"; shift 2 ;;
    --session-id)       SESSION_ID="$2"; shift 2 ;;
    --manual-requested) MANUAL_REQUESTED="$2"; shift 2 ;;
    --codex-present)    CODEX_PRESENT="$2"; CODEX_PRESENT_SET=true; shift 2 ;;
    --cursor-present)   CURSOR_PRESENT="$2"; CURSOR_PRESENT_SET=true; shift 2 ;;
    --codex-available)  CODEX_AVAILABLE="$2"; CODEX_AVAILABLE_SET=true; shift 2 ;;
    --cursor-available) CURSOR_AVAILABLE="$2"; CURSOR_AVAILABLE_SET=true; shift 2 ;;
    --repo)             REPO="$2"; shift 2 ;;
    --issue-number)     ISSUE_NUMBER="$2"; shift 2 ;;
    --claude-pid)       CLAUDE_PID="$2"; CLAUDE_PID_SPECIFIED=1; shift 2 ;;
    *) larch_err "ERROR=Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ -z "$OUTPUT" || -z "$DESIGN_TMPDIR_ARG" || -z "$SESSION_ID" ]]; then
  larch_err "ERROR=Missing required arguments: --output, --design-tmpdir, --session-id"
  exit 1
fi

validate_bool() {
  local flag_name="$1" val="$2"
  if [[ -n "$val" && "$val" != "true" && "$val" != "false" ]]; then
    larch_err "ERROR=Invalid --${flag_name}: must be true or false"
    exit 1
  fi
}
validate_bool codex-present "$CODEX_PRESENT"
validate_bool cursor-present "$CURSOR_PRESENT"
validate_bool codex-available "$CODEX_AVAILABLE"
validate_bool cursor-available "$CURSOR_AVAILABLE"
validate_bool manual-requested "$MANUAL_REQUESTED"

if [[ -n "$ISSUE_NUMBER" && ! "$ISSUE_NUMBER" =~ ^[0-9]+$ ]]; then
  larch_err "ERROR=Invalid --issue-number: must be a non-negative integer"
  exit 1
fi

if [[ -n "$REPO" && ! "$REPO" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
  larch_err "ERROR=Invalid --repo: must match OWNER/REPO"
  exit 1
fi

if [[ ! "$SESSION_ID" =~ ^[A-Za-z0-9_.-]{1,128}$ ]]; then
  larch_err "ERROR=Invalid --session-id: must match ^[A-Za-z0-9_.-]{1,128}$"
  exit 1
fi

if [[ "$CLAUDE_PID_SPECIFIED" -eq 1 ]]; then
  if [[ -z "$CLAUDE_PID" || ! "$CLAUDE_PID" =~ ^[1-9][0-9]{0,6}$ ]]; then
    larch_err "ERROR=Invalid --claude-pid: must be a positive integer of at most 7 decimal digits"
    exit 1
  fi
fi

if [[ "$DESIGN_TMPDIR_ARG" != /* ]]; then
  larch_err "ERROR=Invalid --design-tmpdir: must be an absolute path"
  exit 1
fi

larch_design_tmpdir_validate "$DESIGN_TMPDIR_ARG" || exit 1

if [[ "$OUTPUT" != /* ]]; then
  larch_err "ERROR=Invalid --output: must be an absolute path"
  exit 1
fi

if [[ -n "$CLAUDE_PLUGIN_ROOT_VALUE" ]]; then
  if [[ ${#CLAUDE_PLUGIN_ROOT_VALUE} -gt 512 || ! "$CLAUDE_PLUGIN_ROOT_VALUE" =~ ^[A-Za-z0-9_./~+-]+$ ]]; then
    larch_err "ERROR=Invalid CLAUDE_PLUGIN_ROOT: must match ^[A-Za-z0-9_./~+-]{1,512}$"
    exit 1
  fi
  if [[ "$CLAUDE_PLUGIN_ROOT_VALUE" != /* ]]; then
    larch_err "ERROR=Invalid CLAUDE_PLUGIN_ROOT: must be an absolute path"
    exit 1
  fi
fi

# Refresh executing larch cache-directory mtime after validation. Best-effort;
# helper silently no-ops on non-numeric paths or missing directories.
# shellcheck source=scripts/lib-larch-cache-touch.sh
source "$SCRIPT_DIR/lib-larch-cache-touch.sh"
larch_touch_executing_cache_root --path "$CLAUDE_PLUGIN_ROOT_VALUE"

build_export() {
  local key="$1" val="$2"
  printf 'export %s=%q\n' "$key" "$val"
}

recover_prior_bool_value() {
  local key="$1"
  local prior_file="$2"
  if [[ ! -f "$prior_file" ]]; then
    return 0
  fi
  local line=""
  line=$(grep -E "^export ${key}=(true|false)$" "$prior_file" 2>/dev/null | tail -1) || true
  if [[ -z "$line" ]]; then
    return 0
  fi
  printf '%s' "${line#*=}"
}

# Mirror a partial explicit *_PRESENT / *_AVAILABLE override to its alias peer.
if [[ "$CODEX_PRESENT_SET" == true && "$CODEX_AVAILABLE_SET" != true ]]; then
  CODEX_AVAILABLE="$CODEX_PRESENT"
elif [[ "$CODEX_AVAILABLE_SET" == true && "$CODEX_PRESENT_SET" != true ]]; then
  CODEX_PRESENT="$CODEX_AVAILABLE"
fi
if [[ "$CURSOR_PRESENT_SET" == true && "$CURSOR_AVAILABLE_SET" != true ]]; then
  CURSOR_AVAILABLE="$CURSOR_PRESENT"
elif [[ "$CURSOR_AVAILABLE_SET" == true && "$CURSOR_PRESENT_SET" != true ]]; then
  CURSOR_PRESENT="$CURSOR_AVAILABLE"
fi

for _recover_key in CODEX_PRESENT CURSOR_PRESENT CODEX_AVAILABLE CURSOR_AVAILABLE; do
  if [[ -z "${!_recover_key}" ]]; then
    _recovered=$(recover_prior_bool_value "$_recover_key" "$OUTPUT") || true
    if [[ -n "$_recovered" ]]; then
      printf -v "$_recover_key" '%s' "$_recovered"
    fi
  fi
done

validate_bool codex-present "$CODEX_PRESENT"
validate_bool cursor-present "$CURSOR_PRESENT"
validate_bool codex-available "$CODEX_AVAILABLE"
validate_bool cursor-available "$CURSOR_AVAILABLE"

{
  printf '#!/usr/bin/env bash\n'
  printf '# /design session env — generated by write-design-current-env.sh. Do not edit.\n'
  build_export DESIGN_TMPDIR "$DESIGN_TMPDIR_ARG"
  build_export SESSION_TMPDIR "$DESIGN_TMPDIR_ARG"
  build_export SESSION_ID "$SESSION_ID"
  [[ -n "$MANUAL_REQUESTED" ]] && build_export MANUAL_REQUESTED "$MANUAL_REQUESTED"
  [[ -n "$REPO" ]] && build_export REPO "$REPO"
  [[ -n "$ISSUE_NUMBER" ]] && build_export ISSUE_NUMBER "$ISSUE_NUMBER"
  [[ -n "$CODEX_PRESENT" ]] && build_export CODEX_PRESENT "$CODEX_PRESENT"
  [[ -n "$CURSOR_PRESENT" ]] && build_export CURSOR_PRESENT "$CURSOR_PRESENT"
  [[ -n "$CODEX_AVAILABLE" ]] && build_export CODEX_AVAILABLE "$CODEX_AVAILABLE"
  [[ -n "$CURSOR_AVAILABLE" ]] && build_export CURSOR_AVAILABLE "$CURSOR_AVAILABLE"
  [[ -n "$CLAUDE_PLUGIN_ROOT_VALUE" ]] && build_export CLAUDE_PLUGIN_ROOT "$CLAUDE_PLUGIN_ROOT_VALUE"
} > "${OUTPUT}.tmp.$$"

mv "${OUTPUT}.tmp.$$" "$OUTPUT"

SYMLINK_DIR="${HOME}/.cache/larch/sessions"
if [[ -n "$CLAUDE_PID" ]]; then
  SYMLINK_PATH="${SYMLINK_DIR}/current-design-env-${CLAUDE_PID}.sh"
else
  SYMLINK_PATH="${SYMLINK_DIR}/current-design-env.sh"
  larch_err "WARNING=write-design-current-env.sh: --claude-pid omitted; using legacy current-design-env.sh symlink (transition shim; pass --claude-pid)"
fi
mkdir -p "$SYMLINK_DIR"
ln -sfn "$OUTPUT" "$SYMLINK_PATH"
