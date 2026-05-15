#!/usr/bin/env bash
# parse-args.sh — argument parser for /umbrella
#
# Stdout grammar (one KV per line; consumers MUST split each line on the FIRST
# '=' only — values may contain literal '=' characters):
#   LABELS_COUNT=<integer >= 0>
#   LABEL_1=<value>
#   LABEL_2=<value>
#   ...
#   LABEL_<LABELS_COUNT>=<value>
#   TITLE_PREFIX=<prefix string — empty if none>
#   REPO=<owner/repo — empty if not specified>
#   CLOSED_WINDOW_DAYS=<integer — empty if not specified>
#   DRY_RUN=<true|false>
#   GO=<true|false>
#   INPUT_FILE=<path — empty if --input-file not specified>
#   UMBRELLA_SUMMARY_FILE=<path — empty if --umbrella-summary-file not specified>
#   PIECES_JSON=<path — empty if --pieces-json not specified>
#   BLOCKED_BY_ISSUE=<positive integer — empty if --blocked-by-issue not specified>
#   TASK=<verbatim remainder of $ARGS_STR after the flag prefix — may be
#         empty; preserves embedded whitespace AND any quote/escape characters>
#   UMBRELLA_TMPDIR=<absolute path — newly-created mktemp dir owned by this run>
#
# Frozen ERROR= templates (printed to stderr, exit 1):
#   ERROR=--label requires a value
#   ERROR=--title-prefix requires a value
#   ERROR=--repo requires a value
#   ERROR=--closed-window-days requires a value
#   ERROR=--closed-window-days must be a non-negative integer; got '<value>'
#   ERROR=--input-file requires a value
#   ERROR=--umbrella-summary-file requires a value
#   ERROR=Unknown flag: <flag>
#   ERROR=unclosed double quote at offset <N>
#   ERROR=unclosed single quote at offset <N>
#   ERROR=stray backslash at end of input
#   ERROR=embedded newline in quoted value at offset <N>
#   ERROR=embedded newline in unquoted value at offset <N>
#   ERROR=embedded newline in TASK at offset <N>
#   ERROR=--pieces-json requires a value
#   ERROR=--pieces-json requires --input-file
#   ERROR=--blocked-by-issue requires a value
#   ERROR=--blocked-by-issue must be a positive integer; got '<value>'
#   ERROR=--input-file and --umbrella-summary-file must be passed together
#   ERROR=--input-file is mutually exclusive with positional TASK
#
# See parse-args.md for the full contract, supported quoting subset, and
# consumer-side parsing rules.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

# Pin C locale so ${var:offset:1} and ${#var} use byte semantics regardless
# of caller LC_ALL / LANG. Without this, multi-byte UTF-8 in flag values
# would be character-indexed, drifting offsets vs byte positions.
LC_ALL=C
export LC_ALL

LABEL_VALUES=()
TITLE_PREFIX=""
REPO=""
CLOSED_WINDOW_DAYS=""
DRY_RUN="false"
GO="false"
INPUT_FILE=""
UMBRELLA_SUMMARY_FILE=""
PIECES_JSON=""
BLOCKED_BY_ISSUE=""

# Single positional argument: the entire $ARGUMENTS string from the SKILL.
ARGS_STR="${1:-}"
ARGS_LEN=${#ARGS_STR}

# Phase 1 cursor. Advances through $ARGS_STR.
i=0

# TASK byte offset. -1 means "no TASK present" (input ended after final flag).
TASK_START_OFFSET=-1

# Globals set by the lexer helpers below.
TOKEN_VALUE=""
TOKEN_END=0

# --- Helpers ---

# Skip ASCII whitespace (space, tab, newline) starting at $1; print new offset.
skip_ws() {
  local pos="$1"
  while [ "$pos" -lt "$ARGS_LEN" ]; do
    local c="${ARGS_STR:$pos:1}"
    case "$c" in
      ' '|$'\t'|$'\n') pos=$((pos + 1)) ;;
      *) break ;;
    esac
  done
  printf '%s' "$pos"
}

# Read an unquoted token starting at offset $1. Stops at the first unquoted
# whitespace byte (space/tab/newline) or end-of-string. Backslash escapes the
# next non-newline byte (`\<c>` → literal `<c>`); errors on stray trailing
# backslash and on backslash-escaped newline (`\<LF>`).
# Sets globals: TOKEN_VALUE, TOKEN_END.
read_unquoted_token() {
  local pos="$1"
  TOKEN_VALUE=""
  while [ "$pos" -lt "$ARGS_LEN" ]; do
    local c="${ARGS_STR:$pos:1}"
    case "$c" in
      ' '|$'\t'|$'\n')
        break
        ;;
      \\)
        pos=$((pos + 1))
        if [ "$pos" -ge "$ARGS_LEN" ]; then
          larch_err "ERROR=stray backslash at end of input"
          exit 1
        fi
        local nc="${ARGS_STR:$pos:1}"
        if [ "$nc" = $'\n' ]; then
          larch_err "ERROR=embedded newline in unquoted value at offset $pos"
          exit 1
        fi
        TOKEN_VALUE="${TOKEN_VALUE}${nc}"
        pos=$((pos + 1))
        ;;
      *)
        TOKEN_VALUE="${TOKEN_VALUE}${c}"
        pos=$((pos + 1))
        ;;
    esac
  done
  TOKEN_END="$pos"
}

# Read a quoted token starting at offset $1 (which MUST point at " or ').
# Errors on unclosed quote or embedded literal newline (single-line KV grammar
# cannot carry a newline inside a value).
# Sets globals: TOKEN_VALUE, TOKEN_END.
read_quoted_token() {
  local pos="$1"
  local quote="${ARGS_STR:$pos:1}"
  local start="$pos"
  pos=$((pos + 1))
  TOKEN_VALUE=""
  if [ "$quote" = "'" ]; then
    # Single-quoted: no escape processing, no newline allowed.
    while [ "$pos" -lt "$ARGS_LEN" ]; do
      local c="${ARGS_STR:$pos:1}"
      case "$c" in
        $'\n')
          larch_err "ERROR=embedded newline in quoted value at offset $pos"
          exit 1
          ;;
        \')
          TOKEN_END=$((pos + 1))
          return
          ;;
        *)
          TOKEN_VALUE="${TOKEN_VALUE}${c}"
          pos=$((pos + 1))
          ;;
      esac
    done
    larch_err "ERROR=unclosed single quote at offset $start"
    exit 1
  else
    # Double-quoted: \" \\ \$ are escapes; other \X stays literal as \X.
    while [ "$pos" -lt "$ARGS_LEN" ]; do
      local c="${ARGS_STR:$pos:1}"
      case "$c" in
        $'\n')
          larch_err "ERROR=embedded newline in quoted value at offset $pos"
          exit 1
          ;;
        \")
          TOKEN_END=$((pos + 1))
          return
          ;;
        \\)
          pos=$((pos + 1))
          if [ "$pos" -ge "$ARGS_LEN" ]; then
            larch_err "ERROR=stray backslash at end of input"
            exit 1
          fi
          local next="${ARGS_STR:$pos:1}"
          if [ "$next" = $'\n' ]; then
            larch_err "ERROR=embedded newline in quoted value at offset $pos"
            exit 1
          fi
          case "$next" in
            \"|\\|\$)
              TOKEN_VALUE="${TOKEN_VALUE}${next}"
              ;;
            *)
              TOKEN_VALUE="${TOKEN_VALUE}\\${next}"
              ;;
          esac
          pos=$((pos + 1))
          ;;
        *)
          TOKEN_VALUE="${TOKEN_VALUE}${c}"
          pos=$((pos + 1))
          ;;
      esac
    done
    larch_err "ERROR=unclosed double quote at offset $start"
    exit 1
  fi
}

# Read the next token (quoted or unquoted) starting at offset $1.
# Sets globals: TOKEN_VALUE, TOKEN_END.
read_next_token() {
  local pos="$1"
  if [ "$pos" -ge "$ARGS_LEN" ]; then
    TOKEN_VALUE=""
    TOKEN_END="$pos"
    return
  fi
  local c="${ARGS_STR:$pos:1}"
  case "$c" in
    \"|\')
      read_quoted_token "$pos"
      ;;
    *)
      read_unquoted_token "$pos"
      ;;
  esac
}

# Read the value-token for a value-taking flag whose name was just consumed.
# Skips leading whitespace, then reads the value (quoted or unquoted).
# On end-of-input, errors with the flag-name-specific "requires a value" message.
# Sets globals: TOKEN_VALUE, TOKEN_END.
read_flag_value() {
  local flag_name="$1"
  local pos="$2"
  pos=$(skip_ws "$pos")
  if [ "$pos" -ge "$ARGS_LEN" ]; then
    larch_err "ERROR=$flag_name requires a value"
    exit 1
  fi
  read_next_token "$pos"
}

# --- Phase 1: walk the flag prefix ---

while :; do
  i=$(skip_ws "$i")
  if [ "$i" -ge "$ARGS_LEN" ]; then
    break
  fi
  TOKEN_START="$i"

  # Peek: a quoted token in this position is a positional task — phase 1 stops.
  c="${ARGS_STR:$i:1}"
  if [ "$c" = '"' ] || [ "$c" = "'" ]; then
    TASK_START_OFFSET="$TOKEN_START"
    break
  fi

  read_unquoted_token "$i"
  i="$TOKEN_END"
  tok="$TOKEN_VALUE"

  if [ "$tok" = "--" ]; then
    # End-of-flags marker. TASK begins at the next token (after whitespace).
    i=$(skip_ws "$i")
    if [ "$i" -lt "$ARGS_LEN" ]; then
      TASK_START_OFFSET="$i"
    fi
    break
  fi

  case "$tok" in
    --*)
      case "$tok" in
        --label)
          read_flag_value "--label" "$i"
          i="$TOKEN_END"
          LABEL_VALUES+=("$TOKEN_VALUE")
          ;;
        --title-prefix)
          read_flag_value "--title-prefix" "$i"
          i="$TOKEN_END"
          TITLE_PREFIX="$TOKEN_VALUE"
          ;;
        --repo)
          read_flag_value "--repo" "$i"
          i="$TOKEN_END"
          REPO="$TOKEN_VALUE"
          ;;
        --closed-window-days)
          read_flag_value "--closed-window-days" "$i"
          i="$TOKEN_END"
          CLOSED_WINDOW_DAYS="$TOKEN_VALUE"
          case "$CLOSED_WINDOW_DAYS" in
            ''|*[!0-9]*)
              larch_err "ERROR=--closed-window-days must be a non-negative integer; got '$CLOSED_WINDOW_DAYS'"
              exit 1
              ;;
          esac
          ;;
        --dry-run) DRY_RUN="true" ;;
        --go) GO="true" ;;
        --input-file)
          read_flag_value "--input-file" "$i"
          i="$TOKEN_END"
          INPUT_FILE="$TOKEN_VALUE"
          ;;
        --umbrella-summary-file)
          read_flag_value "--umbrella-summary-file" "$i"
          i="$TOKEN_END"
          UMBRELLA_SUMMARY_FILE="$TOKEN_VALUE"
          ;;
        --blocked-by-issue)
          read_flag_value "--blocked-by-issue" "$i"
          i="$TOKEN_END"
          BLOCKED_BY_ISSUE="$TOKEN_VALUE"
          case "$BLOCKED_BY_ISSUE" in
            ''|*[!0-9]*|0|0[0-9]*)
              larch_err "ERROR=--blocked-by-issue must be a positive integer; got '$BLOCKED_BY_ISSUE'"
              exit 1
              ;;
          esac
          ;;
        --pieces-json)
          read_flag_value "--pieces-json" "$i"
          i="$TOKEN_END"
          PIECES_JSON="$TOKEN_VALUE"
          ;;
        *)
          larch_err "ERROR=Unknown flag: $tok"
          exit 1
          ;;
      esac
      ;;
    *)
      # Non-flag-looking token (single-dash, plain word, etc.) — TASK starts here.
      TASK_START_OFFSET="$TOKEN_START"
      break
      ;;
  esac
done

# --- Phase 2: TASK is the verbatim remainder of $ARGS_STR ---

if [ "$TASK_START_OFFSET" -ge 0 ]; then
  TASK="${ARGS_STR:$TASK_START_OFFSET}"
else
  TASK=""
fi

# A literal newline in TASK would, via printf 'TASK=%s\n' "$TASK", emit
# multiple physical lines and break the documented one-KV-per-line stdout
# grammar — the very contract this script enforces. Reject fail-fast.
case "$TASK" in
  *$'\n'*)
    nl_pos=$TASK_START_OFFSET
    while [ "$nl_pos" -lt "$ARGS_LEN" ]; do
      if [ "${ARGS_STR:$nl_pos:1}" = $'\n' ]; then
        break
      fi
      nl_pos=$((nl_pos + 1))
    done
    larch_err "ERROR=embedded newline in TASK at offset $nl_pos"
    exit 1
    ;;
esac

# --- Paired-flag and mutual-exclusion validation ---

# --input-file and --umbrella-summary-file must be passed together (both or neither).
if [ -n "$INPUT_FILE" ] && [ -z "$UMBRELLA_SUMMARY_FILE" ]; then
  larch_err "ERROR=--input-file and --umbrella-summary-file must be passed together"
  exit 1
fi
if [ -z "$INPUT_FILE" ] && [ -n "$UMBRELLA_SUMMARY_FILE" ]; then
  larch_err "ERROR=--input-file and --umbrella-summary-file must be passed together"
  exit 1
fi

# --input-file is mutually exclusive with positional TASK.
if [ -n "$INPUT_FILE" ] && [ -n "$TASK" ]; then
  larch_err "ERROR=--input-file is mutually exclusive with positional TASK"
  exit 1
fi

# --pieces-json requires --input-file.
if [ -n "$PIECES_JSON" ] && [ -z "$INPUT_FILE" ]; then
  larch_err "ERROR=--pieces-json requires --input-file"
  exit 1
fi

# --- mktemp (only after parse success) ---

UMBRELLA_TMPDIR=$(mktemp -d -t claude-umbrella-XXXXXX)

# --- Emit stdout ---

LABELS_COUNT="${#LABEL_VALUES[@]}"
emit_kv LABELS_COUNT "$LABELS_COUNT"
idx=0
while [ "$idx" -lt "$LABELS_COUNT" ]; do
  emit_kv "LABEL_$((idx + 1))" "${LABEL_VALUES[$idx]}"
  idx=$((idx + 1))
done
emit_kv TITLE_PREFIX "$TITLE_PREFIX"
emit_kv REPO "$REPO"
emit_kv CLOSED_WINDOW_DAYS "$CLOSED_WINDOW_DAYS"
emit_kv DRY_RUN "$DRY_RUN"
emit_kv GO "$GO"
emit_kv INPUT_FILE "$INPUT_FILE"
emit_kv UMBRELLA_SUMMARY_FILE "$UMBRELLA_SUMMARY_FILE"
emit_kv PIECES_JSON "$PIECES_JSON"
emit_kv BLOCKED_BY_ISSUE "$BLOCKED_BY_ISSUE"
emit_kv TASK "$TASK"
emit_kv UMBRELLA_TMPDIR "$UMBRELLA_TMPDIR"
