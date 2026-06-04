#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: materialize-manifest-oos.sh --manifest-path PATH --implement-tmpdir DIR" >&2
  exit 1
}

manifest_path=""
implement_tmpdir=""
while [ $# -gt 0 ]; do
  case "$1" in
    --manifest-path)
      [ $# -ge 2 ] || usage
      manifest_path=$2
      shift 2
      ;;
    --implement-tmpdir)
      [ $# -ge 2 ] || usage
      implement_tmpdir=$2
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      usage
      ;;
  esac
done

[ -n "$manifest_path" ] || usage
[ -n "$implement_tmpdir" ] || usage
[ -f "$manifest_path" ] || { echo "manifest not readable: $manifest_path" >&2; exit 1; }
[ -d "$implement_tmpdir" ] || { echo "implement tmpdir missing: $implement_tmpdir" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "jq is required" >&2; exit 1; }
plugin_root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd -P)}"
redact_secrets="$plugin_root/scripts/redact-secrets.sh"

if ! jq -e 'type == "object"' "$manifest_path" >/dev/null 2>&1; then
  echo "manifest must be a JSON object" >&2
  exit 1
fi

count=$(jq '
  if has("oos_observations") and (.oos_observations | type != "array") then
    error("oos_observations must be an array")
  elif (.oos_observations | type == "array") then
    (.oos_observations | length)
  else
    0
  end
' "$manifest_path") || exit 1
[ "${count:-0}" -gt 0 ] || exit 0
if [ ! -x "$redact_secrets" ]; then
  echo "redact-secrets.sh missing or not executable: $redact_secrets" >&2
  exit 1
fi

out="$implement_tmpdir/oos-accepted-main-agent.md"
mkdir -p "$(dirname "$out")"
[ -f "$out" ] || : > "$out"

max_n=$(awk '
  /^### OOS_[0-9]+:/ {
    n = $0
    sub(/^### OOS_/, "", n)
    sub(/:.*/, "", n)
    if ((n + 0) > max) max = n + 0
  }
  END { print max + 0 }
' "$out")
next_n=$((max_n + 1))

has_title() {
  local title key
  title=$(normalize_title "$1")
  key=$(printf '%s' "$title" | awk '{ print tolower($0) }')
  awk -v wanted="$key" '
    /^### OOS_[0-9]+:/ {
      line = $0
      sub(/^### OOS_[0-9]+:[[:space:]]*/, "", line)
      gsub(/[[:space:]]+/, " ", line)
      sub(/^[[:space:]]+/, "", line)
      sub(/[[:space:]]+$/, "", line)
      if (tolower(line) == wanted) found = 1
    }
    END { exit(found ? 0 : 1) }
  ' "$out"
}

security_focus_area() {
  awk '
    /^[[:space:]]*-[[:space:]]*\*\*focus-area\*\*[[:space:]]*:[[:space:]]*/ {
      value = $0
      sub(/^[[:space:]]*-[[:space:]]*\*\*focus-area\*\*[[:space:]]*:[[:space:]]*/, "", value)
      value = tolower(value)
      if (value ~ /^security([-[:alnum:][:space:]_]*)([[:space:]]|$|\(|#|\.|,)/) found = 1
    }
    END { exit(found ? 0 : 1) }
  '
}

sanitize_public_text() {
  printf '%s' "$1" | "$redact_secrets" | sed -E \
    -e 's#https?://(localhost|127\.0\.0\.1|10\.[0-9.]+|192\.168\.[0-9.]+|172\.(1[6-9]|2[0-9]|3[0-1])\.[0-9.]+|169\.254\.[0-9.]+|fc[0-9a-f]{2}:|fd[0-9a-f]{2}:|fe80:|[^[:space:]/]+[.](internal|local|corp|lan|intranet|test|example|invalid))[^[:space:]]*#<INTERNAL-URL>#Ig' \
    -e 's#\b(localhost|127\.0\.0\.1|10\.[0-9.]+|192\.168\.[0-9.]+|172\.(1[6-9]|2[0-9]|3[0-1])\.[0-9.]+|169\.254\.[0-9.]+|[^[:space:]/]+[.](internal|local|corp|lan|intranet))\b#<INTERNAL-URL>#Ig' \
    -e 's/\b(account|user|customer|employee|tenant|org)[_-]?[[:alnum:]]{8,}\b/<REDACTED-PII>/Ig' \
    -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<REDACTED-PII>/g' \
    -e 's/([0-9]{3}-[0-9]{2}-[0-9]{4})/<REDACTED-PII>/g' \
    -e 's/(\+?1[ .-]?)?\(?[0-9]{3}\)?[ .-]?[0-9]{3}[ .-]?[0-9]{4}/<REDACTED-PII>/g'
}

security_signal() {
  local title=$1 description=$2 focus_area=$3
  if [ -n "$focus_area" ] && printf -- '- **focus-area**: %s\n' "$focus_area" | security_focus_area; then
    return 0
  fi
  printf '%s\n' "$description" | security_focus_area
}

normalize_title() {
  sanitize_public_text "$1" | tr '\000-\037\177' ' ' | awk '
    {
      gsub(/[[:space:]]+/, " ")
      sub(/^[[:space:]]+/, "")
      sub(/[[:space:]]+$/, "")
      printf "%s", $0
    }
  '
}

write_description() {
  local description=$1 first=true line
  if [ -z "$description" ]; then
    printf -- '- **Description**: \n'
    return
  fi
  sanitize_public_text "$description" | while IFS= read -r line || [ -n "$line" ]; do
    if [ "$first" = "true" ]; then
      printf -- '- **Description**: %s\n' "$line"
      first=false
    else
      printf '  %s\n' "$line"
    fi
  done
}

security_has_title() {
  local title=$1 audit="$implement_tmpdir/security-oos-observations.md"
  [ -f "$audit" ] || return 1
  grep -Fqx "### Security OOS: $title" "$audit"
}

append_security_audit() {
  local title=$1 description=$2 phase=$3 focus_area=$4 audit="$implement_tmpdir/security-oos-observations.md" had_audit_content=false entry
  if security_has_title "$title"; then
    return 0
  fi
  [ -s "$audit" ] && had_audit_content=true
  {
    [ "$had_audit_content" = "true" ] && printf '\n'
    printf '### Security OOS: %s\n' "$title"
    write_description "$description"
    printf -- '- **Phase**: %s\n' "$phase"
    if [ -n "$focus_area" ]; then
      printf -- '- **focus-area**: %s\n' "$(normalize_title "$focus_area")"
    fi
    printf -- '- **Disposition**: security-routed; not materialized for public OOS filing\n'
  } >> "$audit"
  entry='- **materialize-manifest-oos.sh**: security-routed manifest OOS retained in security-oos-observations.md'
  if [ -x "$plugin_root/scripts/append-execution-issue.sh" ]; then
    "$plugin_root/scripts/append-execution-issue.sh" \
      --log "$implement_tmpdir/execution-issues.md" \
      --category Warnings \
      --entry "$entry" >/dev/null 2>&1 || printf '\n### Warnings\n%s\n' "$entry" >> "$implement_tmpdir/execution-issues.md"
  else
    printf '\n### Warnings\n%s\n' "$entry" >> "$implement_tmpdir/execution-issues.md"
  fi
}

i=0
while [ "$i" -lt "$count" ]; do
  title=$(jq -r --argjson i "$i" '.oos_observations[$i].title // ""' "$manifest_path") || exit 1
  description=$(jq -r --argjson i "$i" '.oos_observations[$i].description // ""' "$manifest_path") || exit 1
  phase=$(jq -r --argjson i "$i" '.oos_observations[$i].phase // "implement"' "$manifest_path") || exit 1
  focus_area=$(jq -r --argjson i "$i" '.oos_observations[$i]["focus-area"] // .oos_observations[$i].focus_area // ""' "$manifest_path") || exit 1
  title=$(normalize_title "$title")
  phase=$(normalize_title "$phase")
  if [ -z "$title" ]; then
    title="Untitled external implementer OOS $((i + 1))"
  fi
  if security_signal "$title" "$description" "$focus_area"; then
    append_security_audit "$title" "$description" "$phase" "$focus_area"
    i=$((i + 1))
    continue
  fi
  if has_title "$title"; then
    i=$((i + 1))
    continue
  fi
  had_content=false
  if [ -s "$out" ]; then
    had_content=true
  fi
  {
    if [ "$had_content" = "true" ]; then printf '\n'; fi
    printf '### OOS_%s: %s\n' "$next_n" "$title"
    write_description "$description"
    printf -- '- **Reviewer**: External implementer\n'
    printf -- '- **Vote tally**: N/A — auto-filed per policy\n'
    printf -- '- **Phase**: %s\n' "$phase"
  } >> "$out"
  next_n=$((next_n + 1))
  i=$((i + 1))
done
