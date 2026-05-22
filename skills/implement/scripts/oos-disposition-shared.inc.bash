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
  local line b tail tmp uniq_n
  tmp=$(mktemp "${TMPDIR:-/tmp}/oos-rej-oos-tags.XXXXXX")
  : >"$tmp"
  [ ! -f "$ndjson" ] || [ ! -s "$ndjson" ] && {
    rm -f "$tmp"
    printf '0'
    return 0
  }
  while IFS= read -r line || [ -n "${line:-}" ]; do
    [ -z "$line" ] && continue
    b=$(printf '%s' "$line" | jq -r '.body // empty' 2>/dev/null) || {
      printf '%s\n' 'oos-disposition-shared: jq failed parsing oos-issues.ndjson line (skipping line)' >&2
      continue
    }
    case "$b" in
      *'Rejected / Out-of-Scope'* | *'## Rejected'*) ;;
      *) continue ;;
    esac
    tail=$(printf '%s\n' "$b" | awk '
      BEGIN { inj = 0 }
      function rej_heading(l,    t) {
        t = tolower(l)
        return (t ~ /^##[[:space:]]*rejected/ || t ~ /rejected[[:space:]]*\/[[:space:]]*out-of-scope/)
      }
      rej_heading($0) { inj = 1; next }
      inj == 1 && /^##[[:space:]]+/ && !rej_heading($0) { exit }
      inj == 1 { print }
    ')
    if [ -n "$tail" ]; then
      printf '%s\n' "$tail" | grep -ohE 'OOS_[0-9]+' >>"$tmp" || true
    fi
  done <"$ndjson"
  uniq_n=0
  if [ -s "$tmp" ]; then
    uniq_n=$(sort -u "$tmp" | wc -l | tr -d '[:space:]')
  fi
  rm -f "$tmp"
  printf '%s' "${uniq_n:-0}"
}
