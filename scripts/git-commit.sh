#!/usr/bin/env bash
# git-commit.sh — Stage files and commit with Co-Authored-By trailer.
#
# Usage: git-commit.sh -m "message" [--no-trailer] [--only]
#                      [--pathspec-from-file PATH [--pathspec-file-nul]]
#                      [file1 file2 ...]
#
# Stages the specified files (if any) via `git add`, then commits using
# `git commit --file <tmpfile>` to avoid shell quoting issues with
# multi-line messages. Appends the Co-Authored-By trailer by default.
#
# Options:
#   -m <message>     Commit message (required). Written verbatim to a temp
#                    file, so newlines and special characters are safe.
#   --no-trailer     Omit the Co-Authored-By trailer.
#   --only           Pass --only to git commit, scoping the commit to the
#                    provided file args or pathspec file.
#   --pathspec-from-file PATH
#                    Read pathspecs from PATH for git add and git commit.
#   --pathspec-file-nul
#                    Treat the pathspec file as NUL-delimited.
#
# Positional args:   Files to stage via `git add`. If none are provided,
#                    commits whatever is already staged.
#
# Exit codes:
#   0  Success
#   1  Usage error (missing -m, empty message)
#   >0 git add or git commit failure (passthrough)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

TRAILER="Co-Authored-By: Claude Code <noreply@anthropic.com>"
MESSAGE=""
NO_TRAILER=false
ONLY=false
PATHSPEC_FROM_FILE=""
PATHSPEC_FILE_NUL=false
FILES=()

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    -m)
      if [[ $# -lt 2 ]]; then
        larch_err "git-commit.sh: -m requires a message argument"
        exit 1
      fi
      MESSAGE="$2"
      shift 2
      ;;
    --no-trailer)
      NO_TRAILER=true
      shift
      ;;
    --only)
      ONLY=true
      shift
      ;;
    --pathspec-from-file)
      if [[ $# -lt 2 ]]; then
        larch_err "git-commit.sh: --pathspec-from-file requires a path"
        exit 1
      fi
      PATHSPEC_FROM_FILE="$2"
      shift 2
      ;;
    --pathspec-file-nul)
      PATHSPEC_FILE_NUL=true
      shift
      ;;
    --)
      shift
      FILES+=("$@")
      break
      ;;
    *)
      FILES+=("$1")
      shift
      ;;
  esac
done

# --- Validate message ---
TRIMMED="${MESSAGE#"${MESSAGE%%[![:space:]]*}"}"
TRIMMED="${TRIMMED%"${TRIMMED##*[![:space:]]}"}"
if [[ -z "$TRIMMED" ]]; then
  larch_err "git-commit.sh: commit message must be non-empty"
  exit 1
fi

# --- Stage files ---
if [[ -n "$PATHSPEC_FROM_FILE" ]]; then
  add_args=(--pathspec-from-file="$PATHSPEC_FROM_FILE")
  if [[ "$PATHSPEC_FILE_NUL" == true ]]; then
    add_args+=(--pathspec-file-nul)
  fi
  git add "${add_args[@]}"
elif [[ ${#FILES[@]} -gt 0 ]]; then
  git add -- "${FILES[@]}"
fi

# --- Write message and append trailer ---
TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT

printf '%s\n' "$MESSAGE" > "$TMPFILE"

if [[ "$NO_TRAILER" == false ]]; then
  # Use git's native trailer machinery to append Co-Authored-By.
  # --if-exists addIfDifferent avoids duplicates when the message
  # already contains a Co-Authored-By with a different value, and
  # skips appending when the exact same trailer is already present.
  git interpret-trailers --in-place \
    --if-exists addIfDifferent --if-missing add \
    --trailer "$TRAILER" "$TMPFILE"
fi

commit_args=(--file "$TMPFILE")
if [[ "$ONLY" == true ]]; then
  commit_args+=(--only)
fi
if [[ -n "$PATHSPEC_FROM_FILE" ]]; then
  commit_args+=(--pathspec-from-file="$PATHSPEC_FROM_FILE")
  if [[ "$PATHSPEC_FILE_NUL" == true ]]; then
    commit_args+=(--pathspec-file-nul)
  fi
elif [[ ${#FILES[@]} -gt 0 ]]; then
  commit_args+=(--)
  commit_args+=("${FILES[@]}")
fi

git commit "${commit_args[@]}"
