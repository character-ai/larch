#!/usr/bin/env bash
# write-session-env.sh — Write session environment values to a file for child skills.
#
# Usage:
#   write-session-env.sh --output <path> --repo <owner/repo> \
#                        --repo-unavailable <true|false> \
#                        [--codex-present <true|false>] [--cursor-present <true|false>] \
#                        [--timing-ledger <path>] [--token-session-id <id>] \
#                        [--claude-source-file <path>] [--prev-implement-tmpdir <path>]
#
# Options:
#   --repo may be empty when --repo-unavailable is true (repo discovery failed).
#   --codex-present/--cursor-present are optional (reviewer binary presence from setup).
#   --timing-ledger is optional (shared timing ledger path for nested skills).
#   --token-session-id is optional (token ledger session id for nested skills).
#   --claude-source-file is optional (Claude transcript snapshot for token reports).
#   --prev-implement-tmpdir is optional (previous /implement tmpdir for larch-log handoff).
#   LARCH_CLAUDE_PLUGIN_ROOT is written automatically when CLAUDE_PLUGIN_ROOT is set.
#
# Output: Writes a KEY=VALUE file to --output path (atomic via temp+mv).
#         This file is not safe to source; parse with read-session-env-key.sh.
#         Values are not shell-quoted; callers MUST validate inputs before writing.
#         When --output is /dev/null, the output is silently discarded.
# Exit codes: 0 success, 1 invalid args

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

OUTPUT=""
REPO=""
REPO_UNAVAILABLE=""
CODEX_PRESENT=""
CURSOR_PRESENT=""
TIMING_LEDGER=""
TOKEN_SESSION_ID=""
CLAUDE_SOURCE_FILE=""
PREV_IMPLEMENT_TMPDIR_ARG=""
CLAUDE_PLUGIN_ROOT_VALUE="${CLAUDE_PLUGIN_ROOT:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)           OUTPUT="$2"; shift 2 ;;
    --repo)             REPO="$2"; shift 2 ;;
    --repo-unavailable) REPO_UNAVAILABLE="$2"; shift 2 ;;
    --codex-present)    CODEX_PRESENT="$2"; shift 2 ;;
    --cursor-present)   CURSOR_PRESENT="$2"; shift 2 ;;
    --timing-ledger)    TIMING_LEDGER="$2"; shift 2 ;;
    --token-session-id) TOKEN_SESSION_ID="$2"; shift 2 ;;
    --claude-source-file) CLAUDE_SOURCE_FILE="$2"; shift 2 ;;
    --prev-implement-tmpdir) PREV_IMPLEMENT_TMPDIR_ARG="$2"; shift 2 ;;
    *) larch_err "ERROR=Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ -z "$OUTPUT" || -z "$REPO_UNAVAILABLE" ]]; then
  larch_err "ERROR=Missing required arguments: --output, --repo-unavailable"
  exit 1
fi

if [[ -n "$TOKEN_SESSION_ID" && ( ${#TOKEN_SESSION_ID} -gt 128 || ! "$TOKEN_SESSION_ID" =~ ^[A-Za-z0-9_.-]+$ ) ]]; then
  larch_err "ERROR=Invalid --token-session-id: must match ^[A-Za-z0-9_.-]{1,128}$"
  exit 1
fi

if [[ -n "$CLAUDE_SOURCE_FILE" && ( ${#CLAUDE_SOURCE_FILE} -gt 512 || ! "$CLAUDE_SOURCE_FILE" =~ ^[A-Za-z0-9_./~+-]+$ ) ]]; then
  larch_err "ERROR=Invalid --claude-source-file: must match ^[A-Za-z0-9_./~+-]{1,512}$"
  exit 1
fi

if [[ -n "$TIMING_LEDGER" && ( ${#TIMING_LEDGER} -gt 512 || ! "$TIMING_LEDGER" =~ ^[A-Za-z0-9_./~+-]+$ ) ]]; then
  larch_err "ERROR=Invalid --timing-ledger: must match ^[A-Za-z0-9_./~+-]{1,512}$"
  exit 1
fi

if [[ -n "$PREV_IMPLEMENT_TMPDIR_ARG" ]]; then
  if [[ ${#PREV_IMPLEMENT_TMPDIR_ARG} -gt 512 || ! "$PREV_IMPLEMENT_TMPDIR_ARG" =~ ^[A-Za-z0-9_./~+-]+$ ]]; then
    larch_err "ERROR=Invalid --prev-implement-tmpdir: must match ^[A-Za-z0-9_./~+-]{1,512}$"
    exit 1
  fi
  if [[ "$PREV_IMPLEMENT_TMPDIR_ARG" != /* ]]; then
    larch_err "ERROR=Invalid --prev-implement-tmpdir: must be an absolute path"
    exit 1
  fi
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

# Build the content
CONTENT="REPO=$REPO
REPO_UNAVAILABLE=$REPO_UNAVAILABLE"
[[ -n "$CODEX_PRESENT" ]] && CONTENT="$CONTENT
CODEX_PRESENT=$CODEX_PRESENT
CODEX_AVAILABLE=$CODEX_PRESENT"
[[ -n "$CURSOR_PRESENT" ]] && CONTENT="$CONTENT
CURSOR_PRESENT=$CURSOR_PRESENT
CURSOR_AVAILABLE=$CURSOR_PRESENT"
[[ -n "$TIMING_LEDGER" ]] && CONTENT="$CONTENT
LARCH_TIMING_LEDGER=$TIMING_LEDGER"
[[ -n "$TOKEN_SESSION_ID" ]] && CONTENT="$CONTENT
LARCH_TOKEN_SESSION_ID=$TOKEN_SESSION_ID"
[[ -n "$CLAUDE_SOURCE_FILE" ]] && CONTENT="$CONTENT
LARCH_CLAUDE_SOURCE_FILE=$CLAUDE_SOURCE_FILE"
[[ -n "$PREV_IMPLEMENT_TMPDIR_ARG" ]] && CONTENT="$CONTENT
PREV_IMPLEMENT_TMPDIR=$PREV_IMPLEMENT_TMPDIR_ARG"
[[ -n "$CLAUDE_PLUGIN_ROOT_VALUE" ]] && CONTENT="$CONTENT
LARCH_CLAUDE_PLUGIN_ROOT=$CLAUDE_PLUGIN_ROOT_VALUE"

# Write atomically via temp+mv for regular paths.
# Skip /dev/null — mktemp and mv both fail on device nodes.
if [[ "$OUTPUT" == "/dev/null" ]]; then
  : # Discard — caller explicitly requested no output
else
  TMPFILE=$(mktemp "${OUTPUT}.tmp.XXXXXX")
  echo "$CONTENT" > "$TMPFILE"
  mv "$TMPFILE" "$OUTPUT"
fi
