# Shared helpers for OOS disposition gate and audit oos-silent-drop scan.
# shellcheck shell=bash
# Dotted from `scripts/oos-disposition-gate.sh` (via repo `scripts/`) and
# `.claude/skills/audit-runs/scripts/audit-scan-run.sh` — single contract
# surface for URL / rejection counting helpers.

# Count GitHub issue URLs on github.com, or on $GH_HOST when set for
# Enterprise Server (still https:// only; arbitrary hosts are ignored).
_oos_github_issue_url_ere() {
  local esc host_ere
  if [ -n "${GH_HOST:-}" ] && [ "$GH_HOST" != "github.com" ]; then
    esc=$(printf '%s\n' "$GH_HOST" | sed 's/\./\\./g')
    host_ere="(${esc}|github\\.com)"
  else
    host_ere="github\\.com"
  fi
  printf '%s' "https://${host_ere}/[^[:space:]/]+/[^[:space:]/]+/issues/[0-9]+"
}

count_filed_urls_union_files() {
  local tmp acc ere
  ere=$(_oos_github_issue_url_ere)
  tmp=$(mktemp "${TMPDIR:-/tmp}/oos-disposition-urls.XXXXXX")
  : >"$tmp"
  for f in "$@"; do
    if [ -f "$f" ] && [ -s "$f" ]; then
      grep -EhEo "$ere" "$f" 2>/dev/null >>"$tmp" || true
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

# Count unique GitHub issue URLs that appear only on dedicated markdown list lines
# `- **Filed URL**: <url>` (ignores incidental URLs elsewhere in the file).
count_filed_url_field_lines() {
  local tmp acc ere pat
  ere=$(_oos_github_issue_url_ere)
  tmp=$(mktemp "${TMPDIR:-/tmp}/oos-disposition-field-urls.XXXXXX")
  : >"$tmp"
  pat="^[[:space:]]*-[[:space:]]+\*\*Filed[[:space:]]URL\*\*:[[:space:]]+${ere}$"
  for f in "$@"; do
    if [ -f "$f" ] && [ -s "$f" ]; then
      grep -E "$pat" "$f" 2>/dev/null | grep -Eo "$ere" >>"$tmp" || true
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
  local line b tail tmp uniq_n jq_failed=0
  tmp=$(mktemp "${TMPDIR:-/tmp}/oos-rej-oos-tags.XXXXXX")
  : >"$tmp"
  [ ! -f "$ndjson" ] || [ ! -s "$ndjson" ] && {
    rm -f "$tmp"
    printf '0'
    return 0
  }
  while IFS= read -r line || [ -n "${line:-}" ]; do
    [ -z "$line" ] && continue
    if ! printf '%s' "$line" | jq -e 'type == "object"' >/dev/null 2>&1; then
      printf '%s\n' 'oos-disposition-shared: jq failed parsing oos-issues.ndjson line' >&2
      jq_failed=1
      continue
    fi
    b=$(printf '%s' "$line" | jq -r '.body // ""')
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
  if [ "$jq_failed" -ne 0 ]; then
    return 2
  fi
  return 0
}
