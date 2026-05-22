#!/usr/bin/env bash
# oos-disposition-gate.sh — Mechanical guard: non-security accepted OOS entries
# must have either filed issue URLs, Inline-triage commit breadcrumbs, or
# explicit rejection markers in the oos-issues NDJSON batch.
#
# Exit 0: pass or skipped (--fork-mode / --repo-unavailable).
# Exit 1: disposition gap (non_security > 0, filed == 0, inline < non_security,
#   rejected markers < non_security).
# Exit 2: bad arguments or unreadable inputs required for a non-skip run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OOS_COUNT_AWK="$SCRIPT_DIR/oos-non-security-block-count.awk"
# shellcheck source=skills/implement/scripts/oos-disposition-shared.inc.bash
. "$SCRIPT_DIR/oos-disposition-shared.inc.bash"

usage() {
  printf 'usage: oos-disposition-gate.sh [--fork-mode] [--repo-unavailable] \\\n' >&2
  printf '  --accepted-files CSV --filed-urls-file PATH \\\n' >&2
  printf '  [--oos-issues-ndjson PATH] --commit-range RANGE\n' >&2
}

count_non_security_oos() {
  local csv="$1" f n sum
  sum=0
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    n=$(awk -f "$OOS_COUNT_AWK" "$f" 2>/dev/null || printf '0')
    sum=$((sum + n))
  done <<EOF
$(printf '%s' "$csv" | tr ',' '\n')
EOF
  printf '%s' "$sum"
}

count_inline_triage() {
  local range="$1"
  local repo
  repo=$(git rev-parse --show-toplevel 2>/dev/null || true)
  if [ -z "$repo" ]; then
    printf '%s\n' 'oos-disposition-gate: not inside a git work tree (need commit-range scan)' >&2
    return 2
  fi
  set +e
  git -C "$repo" rev-list -1 "$range" >/dev/null 2>&1
  local rev_ok=$?
  set -e
  if [ "$rev_ok" -ne 0 ]; then
    printf '%s\n' "oos-disposition-gate: invalid commit-range: $range" >&2
    return 2
  fi
  set +e
  local c
  c=$(git -C "$repo" log --format=%B "$range" 2>/dev/null | grep -cF 'Inline-triage rule' || true)
  set -e
  printf '%s' "$c"
}

ACCEPTED_FILES=""
FILED_URLS_FILE=""
OOS_ISSUES_NDJSON=""
COMMIT_RANGE=""
FORK_MODE=false
REPO_UNAVAILABLE=false

while [ $# -gt 0 ]; do
  case "$1" in
    --accepted-files)
      [ $# -ge 2 ] || {
        usage
        exit 2
      }
      ACCEPTED_FILES="$2"
      shift 2
      ;;
    --filed-urls-file)
      [ $# -ge 2 ] || {
        usage
        exit 2
      }
      FILED_URLS_FILE="$2"
      shift 2
      ;;
    --oos-issues-ndjson)
      [ $# -ge 2 ] || {
        usage
        exit 2
      }
      OOS_ISSUES_NDJSON="$2"
      shift 2
      ;;
    --commit-range)
      [ $# -ge 2 ] || {
        usage
        exit 2
      }
      COMMIT_RANGE="$2"
      shift 2
      ;;
    --fork-mode) FORK_MODE=true; shift ;;
    --repo-unavailable) REPO_UNAVAILABLE=true; shift ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      printf 'oos-disposition-gate: unknown argument: %s\n' "$1" >&2
      usage
      exit 2
      ;;
  esac
done

if [ "$FORK_MODE" = true ] || [ "$REPO_UNAVAILABLE" = true ]; then
  exit 0
fi

if [ -z "$ACCEPTED_FILES" ] || [ -z "$FILED_URLS_FILE" ] || [ -z "$COMMIT_RANGE" ]; then
  usage
  exit 2
fi

oos_validate_accepted_inputs() {
  local f any_acc=false filed_probe
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    if [ -e "$f" ]; then
      if [ ! -f "$f" ] || [ ! -r "$f" ]; then
        printf 'oos-disposition-gate: accepted file path is not a readable regular file: %s\n' "$f" >&2
        return 2
      fi
    fi
  done <<EOF
$(printf '%s' "$ACCEPTED_FILES" | tr ',' '\n')
EOF
  if [ -n "$OOS_ISSUES_NDJSON" ] && [ -f "$OOS_ISSUES_NDJSON" ] && [ -s "$OOS_ISSUES_NDJSON" ]; then
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      [ -f "$f" ] && any_acc=true
    done <<EOF
$(printf '%s' "$ACCEPTED_FILES" | tr ',' '\n')
EOF
    if [ "$any_acc" = false ]; then
      filed_probe=$(count_filed_urls_union_files "$OOS_ISSUES_NDJSON")
      if [ "${filed_probe:-0}" -gt 0 ]; then
        printf '%s\n' 'oos-disposition-gate: oos-issues.ndjson lists filed GitHub issue URLs but no --accepted-files paths exist as regular files (check CSV path list)' >&2
        return 2
      fi
    fi
  fi
  return 0
}

oos_validate_accepted_inputs || exit 2

non_sec=$(count_non_security_oos "$ACCEPTED_FILES")
if [ -n "$OOS_ISSUES_NDJSON" ] && [ -f "$OOS_ISSUES_NDJSON" ]; then
  filed=$(count_filed_urls_union_files "$FILED_URLS_FILE" "$OOS_ISSUES_NDJSON")
else
  filed=$(count_filed_urls_union_files "$FILED_URLS_FILE")
fi
rejected=0
if [ -n "$OOS_ISSUES_NDJSON" ] && [ -f "$OOS_ISSUES_NDJSON" ]; then
  rejected=$(count_rejected_oos_markers_from_ndjson "$OOS_ISSUES_NDJSON")
fi
inline_raw=$(count_inline_triage "$COMMIT_RANGE") || exit 2
inline=$inline_raw

if [ "${non_sec:-0}" -eq 0 ]; then
  exit 0
fi

if [ "${filed:-0}" -gt 0 ]; then
  exit 0
fi

if [ "${inline:-0}" -ge "${non_sec:-0}" ]; then
  exit 0
fi

if [ "${rejected:-0}" -ge "${non_sec:-0}" ]; then
  exit 0
fi

printf 'oos-disposition-gate: FAIL non_security_oos=%s filed_urls=%s inline_triage_lines=%s rejected_oos_markers=%s (commit-range %s)\n' \
  "$non_sec" "$filed" "$inline" "$rejected" "$COMMIT_RANGE" >&2
exit 1
