#!/usr/bin/env bash
# oos-disposition-gate.sh — Mechanical guard: non-security accepted OOS entries
# must have either filed issue URLs or Inline-triage commit breadcrumbs.
#
# Exit 0: pass or skipped (--fork-mode / --repo-unavailable).
# Exit 1: disposition gap (non_security > 0, filed == 0, inline < non_security).
# Exit 2: bad arguments or unreadable inputs required for a non-skip run.

set -euo pipefail

usage() {
  printf 'usage: oos-disposition-gate.sh [--fork-mode] [--repo-unavailable] \\\n' >&2
  printf '  --accepted-files CSV --filed-urls-file PATH --commit-range RANGE\n' >&2
}

count_non_security_oos() {
  local csv="$1" f n sum
  sum=0
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    n=$(awk '
      BEGIN { n = 0; inblk = 0; sec = 0 }
      /^###[[:space:]]+OOS_/ {
        if (inblk && !sec) n++
        inblk = 1
        sec = 0
        next
      }
      inblk && /focus-area[[:space:]]*=[[:space:]]*security/ {
        sec = 1
      }
      END {
        if (inblk && !sec) n++
        print n + 0
      }
    ' "$f" 2>/dev/null || printf '0')
    sum=$((sum + n))
  done <<EOF
$(printf '%s' "$csv" | tr ',' '\n')
EOF
  printf '%s' "$sum"
}

count_filed_urls() {
  local file="$1"
  if [ ! -f "$file" ] || [ ! -s "$file" ]; then
    printf '0'
    return
  fi
  # De-dupe URLs across the sentinel / sidecar file.
  grep -Eo 'https://[^[:space:]]+/issues/[0-9]+' "$file" 2>/dev/null | sort -u | wc -l | tr -d '[:space:]'
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

non_sec=$(count_non_security_oos "$ACCEPTED_FILES")
filed=$(count_filed_urls "$FILED_URLS_FILE")
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

printf 'oos-disposition-gate: FAIL non_security_oos=%s filed_urls=%s inline_triage_lines=%s (commit-range %s)\n' \
  "$non_sec" "$filed" "$inline" "$COMMIT_RANGE" >&2
exit 1
