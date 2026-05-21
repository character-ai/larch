# Shared helpers for OOS disposition gate and audit oos-silent-drop scan.
# shellcheck shell=bash
# Intended to be dotted from oos-disposition-gate.sh (same directory) or
# audit-scan-run.sh (relative path to this repo's skills/implement/scripts/).

count_filed_urls_union_files() {
  local tmp acc
  tmp=$(mktemp "${TMPDIR:-/tmp}/oos-disposition-urls.XXXXXX")
  : >"$tmp"
  for f in "$@"; do
    if [ -f "$f" ] && [ -s "$f" ]; then
      grep -EhEo 'https://[^[:space:]]+/issues/[0-9]+' "$f" 2>/dev/null >>"$tmp" || true
    fi
  done
  if [ ! -s "$tmp" ]; then
    rm -f "$tmp"
    printf '0'
    return
  fi
  acc=$(sort -u "$tmp" | wc -l | tr -d '[:space:]')
  rm -f "$tmp"
  printf '%s' "$acc"
}

count_rejected_oos_markers_from_ndjson() {
  local ndjson="$1"
  local sum=0 line b tail n
  [ ! -f "$ndjson" ] || [ ! -s "$ndjson" ] && {
    printf '0'
    return
  }
  while IFS= read -r line || [ -n "${line:-}" ]; do
    [ -z "$line" ] && continue
    b=$(printf '%s' "$line" | jq -r '.body // empty' 2>/dev/null) || continue
    case "$b" in
      *'Rejected / Out-of-Scope'* | *'## Rejected'*) ;;
      *) continue ;;
    esac
    tail=$(printf '%s\n' "$b" | awk '
      BEGIN { inj = 0 }
      /^##[[:space:]]*Rejected/ { inj = 1; next }
      inj == 1 && /^##[[:space:]]+/ && !/^##[[:space:]]*Rejected/ { exit }
      inj == 1 { print }
    ')
    n=0
    if [ -n "$tail" ]; then
      n=$(printf '%s\n' "$tail" | grep -cE '^###[[:space:]]+OOS_|^[[:space:]]*-[[:space:]]*\*\*OOS_[0-9]' 2>/dev/null || true)
    fi
    sum=$((sum + n))
  done <"$ndjson"
  printf '%s' "$sum"
}
