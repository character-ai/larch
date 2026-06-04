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

if ! jq -e 'type == "object"' "$manifest_path" >/dev/null 2>&1; then
  echo "manifest must be a JSON object" >&2
  exit 1
fi

count=$(jq 'if (.oos_observations | type == "array") then (.oos_observations | length) else 0 end' "$manifest_path") || exit 1
[ "${count:-0}" -gt 0 ] || exit 0

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
  local title=$1
  awk -v wanted="$title" '
    /^### OOS_[0-9]+:/ {
      line = $0
      sub(/^### OOS_[0-9]+:[[:space:]]*/, "", line)
      if (line == wanted) found = 1
    }
    END { exit(found ? 0 : 1) }
  ' "$out"
}

security_focus_area() {
  awk '
    /^[[:space:]]*-[[:space:]]+\*\*focus-area\*\*:[[:space:]]*/ {
      value = $0
      sub(/^[[:space:]]*-[[:space:]]+\*\*focus-area\*\*:[[:space:]]*/, "", value)
      value = tolower(value)
      if (value ~ /^security(-[[:alnum:]_]+)*([[:space:]]|$)/) found = 1
    }
    END { exit(found ? 0 : 1) }
  '
}

write_description() {
  local description=$1 first=true line
  while IFS= read -r line || [ -n "$line" ]; do
    if [ "$first" = "true" ]; then
      printf -- '- **Description**: %s\n' "$line"
      first=false
    else
      printf '  %s\n' "$line"
    fi
  done <<EOF_DESC
$description
EOF_DESC
  if [ "$first" = "true" ]; then
    printf -- '- **Description**: \n'
  fi
}

i=0
while [ "$i" -lt "$count" ]; do
  title=$(jq -r --argjson i "$i" '.oos_observations[$i].title // ""' "$manifest_path") || exit 1
  description=$(jq -r --argjson i "$i" '.oos_observations[$i].description // ""' "$manifest_path") || exit 1
  phase=$(jq -r --argjson i "$i" '.oos_observations[$i].phase // "implement"' "$manifest_path") || exit 1
  title=$(printf '%s' "$title" | tr -d '\r')
  phase=$(printf '%s' "$phase" | tr -d '\r')
  if [ -z "$title" ]; then
    title="Untitled external implementer OOS"
  fi
  if printf '%s\n' "$description" | security_focus_area; then
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
