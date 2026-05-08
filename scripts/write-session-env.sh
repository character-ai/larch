#!/usr/bin/env bash
# write-session-env.sh — Write session environment values to a file for child skills.
#
# Usage:
#   write-session-env.sh --output <path> --slack-ok <true|false> \
#                        [--slack-missing <csv>] --repo <owner/repo> \
#                        --repo-unavailable <true|false> \
#                        [--codex-healthy <true|false>] [--cursor-healthy <true|false>] [--gemini-healthy <true|false>] \
#                        [--timing-ledger <path>] [--token-session-id <id>] \
#                        [--claude-source-file <path>]
#
# Options:
#   --repo may be empty when --repo-unavailable is true (repo discovery failed).
#   --slack-missing is optional (only meaningful when --slack-ok is false).
#   --codex-healthy/--cursor-healthy/--gemini-healthy are optional (reviewer health state from probe).
#   --timing-ledger is optional (shared timing ledger path for nested skills).
#   --token-session-id is optional (token ledger session id for nested skills).
#   --claude-source-file is optional (Claude transcript snapshot for token reports).
#
# Output: Writes a KEY=VALUE file to --output path (atomic via temp+mv).
#         This file is not safe to source; parse with read-session-env-key.sh.
#         Values are not shell-quoted; callers MUST validate inputs before writing.
#         When --output is /dev/null, the output is silently discarded.
# Exit codes: 0 success, 1 invalid args

set -euo pipefail

OUTPUT=""
SLACK_OK=""
SLACK_MISSING=""
REPO=""
REPO_UNAVAILABLE=""
CODEX_HEALTHY=""
CURSOR_HEALTHY=""
GEMINI_HEALTHY=""
TIMING_LEDGER=""
TOKEN_SESSION_ID=""
CLAUDE_SOURCE_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)           OUTPUT="$2"; shift 2 ;;
    --slack-ok)         SLACK_OK="$2"; shift 2 ;;
    --slack-missing)    SLACK_MISSING="$2"; shift 2 ;;
    --repo)             REPO="$2"; shift 2 ;;
    --repo-unavailable) REPO_UNAVAILABLE="$2"; shift 2 ;;
    --codex-healthy)    CODEX_HEALTHY="$2"; shift 2 ;;
    --cursor-healthy)   CURSOR_HEALTHY="$2"; shift 2 ;;
    --gemini-healthy)   GEMINI_HEALTHY="$2"; shift 2 ;;
    --timing-ledger)    TIMING_LEDGER="$2"; shift 2 ;;
    --token-session-id) TOKEN_SESSION_ID="$2"; shift 2 ;;
    --claude-source-file) CLAUDE_SOURCE_FILE="$2"; shift 2 ;;
    *) echo "ERROR=Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$OUTPUT" || -z "$SLACK_OK" || -z "$REPO_UNAVAILABLE" ]]; then
  echo "ERROR=Missing required arguments: --output, --slack-ok, --repo-unavailable" >&2
  exit 1
fi

if [[ -n "$TOKEN_SESSION_ID" && ( ${#TOKEN_SESSION_ID} -gt 128 || ! "$TOKEN_SESSION_ID" =~ ^[A-Za-z0-9_.-]+$ ) ]]; then
  echo "ERROR=Invalid --token-session-id: must match ^[A-Za-z0-9_.-]{1,128}$" >&2
  exit 1
fi

if [[ -n "$CLAUDE_SOURCE_FILE" && ( ${#CLAUDE_SOURCE_FILE} -gt 512 || ! "$CLAUDE_SOURCE_FILE" =~ ^[A-Za-z0-9_./~+-]+$ ) ]]; then
  echo "ERROR=Invalid --claude-source-file: must match ^[A-Za-z0-9_./~+-]{1,512}$" >&2
  exit 1
fi

if [[ -n "$TIMING_LEDGER" && ( ${#TIMING_LEDGER} -gt 512 || ! "$TIMING_LEDGER" =~ ^[A-Za-z0-9_./~+-]+$ ) ]]; then
  echo "ERROR=Invalid --timing-ledger: must match ^[A-Za-z0-9_./~+-]{1,512}$" >&2
  exit 1
fi

# Build the content
CONTENT="SLACK_OK=$SLACK_OK
SLACK_MISSING=$SLACK_MISSING
REPO=$REPO
REPO_UNAVAILABLE=$REPO_UNAVAILABLE"
[[ -n "$CODEX_HEALTHY" ]] && CONTENT="$CONTENT
CODEX_HEALTHY=$CODEX_HEALTHY"
[[ -n "$CURSOR_HEALTHY" ]] && CONTENT="$CONTENT
CURSOR_HEALTHY=$CURSOR_HEALTHY"
[[ -n "$GEMINI_HEALTHY" ]] && CONTENT="$CONTENT
GEMINI_HEALTHY=$GEMINI_HEALTHY"
[[ -n "$TIMING_LEDGER" ]] && CONTENT="$CONTENT
LARCH_TIMING_LEDGER=$TIMING_LEDGER"
[[ -n "$TOKEN_SESSION_ID" ]] && CONTENT="$CONTENT
LARCH_TOKEN_SESSION_ID=$TOKEN_SESSION_ID"
[[ -n "$CLAUDE_SOURCE_FILE" ]] && CONTENT="$CONTENT
LARCH_CLAUDE_SOURCE_FILE=$CLAUDE_SOURCE_FILE"

# Write atomically via temp+mv for regular paths.
# Skip /dev/null — mktemp and mv both fail on device nodes.
if [[ "$OUTPUT" == "/dev/null" ]]; then
  : # Discard — caller explicitly requested no output
else
  TMPFILE=$(mktemp "${OUTPUT}.tmp.XXXXXX")
  echo "$CONTENT" > "$TMPFILE"
  mv "$TMPFILE" "$OUTPUT"
fi
