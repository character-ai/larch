#!/usr/bin/env bash
# Walk scripts/generators.tsv and run each registered generator in --check mode.

set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REGISTRY="scripts/generators.tsv"

usage() {
  echo "Usage: $0" >&2
}

fail() {
  echo "$*" >&2
  exit 1
}

path_has_segment() {
  local path="$1"
  local segment="$2"
  [[ "$path" == "$segment" || "$path" == "$segment/"* || "$path" == */"$segment" || "$path" == */"$segment"/* ]]
}

validate_path() {
  local row="$1"
  local label="$2"
  local path="$3"

  [[ -n "$path" ]] || fail "$REGISTRY:$row: empty $label path"
  [[ "$path" != /* ]] || fail "$REGISTRY:$row: absolute path not allowed for $label: $path"
  [[ "$path" != ./* ]] || fail "$REGISTRY:$row: $label path must not start with ./ : $path"
  [[ "$path" != -* ]] || fail "$REGISTRY:$row: $label path must not start with -: $path"
  [[ "$path" != *"//"* ]] || fail "$REGISTRY:$row: $label path must not contain duplicate slash: $path"
  [[ "$path" != *$'\t'* ]] || fail "$REGISTRY:$row: $label path must not contain tabs"
  [[ "$path" != *$'\n'* ]] || fail "$REGISTRY:$row: $label path must not contain newlines"
  if path_has_segment "$path" ".."; then
    fail "$REGISTRY:$row: $label path must not contain parent traversal: $path"
  fi
  if path_has_segment "$path" "."; then
    fail "$REGISTRY:$row: $label path must not contain . path segments: $path"
  fi
}

contains_seen() {
  local needle="$1"
  shift
  local item
  for item in "$@"; do
    [[ "$item" == "$needle" ]] && return 0
  done
  return 1
}

if [[ $# -ne 0 ]]; then
  usage
  exit 2
fi

cd "$REPO_ROOT"
git rev-parse --show-toplevel >/dev/null 2>&1 || fail "check-generators: not inside a git work tree"
[[ -f "$REGISTRY" ]] || fail "check-generators: registry not found: $REGISTRY"

generators=()
output_paths=()
line_no=0

while IFS= read -r line || [[ -n "$line" ]]; do
  line_no=$((line_no + 1))

  if [[ "$line" == *$'\r' ]]; then
    fail "$REGISTRY:$line_no: CRLF line endings not allowed (use LF)"
  fi
  [[ -z "$line" ]] && continue
  [[ "${line:0:1}" == "#" ]] && continue

  if ! parsed="$(awk -F '\t' '{ if (NF != 2 || $1 == "" || $2 == "") exit 1; print $1; print $2 }' <<<"$line")"; then
    fail "$REGISTRY:$line_no: malformed row; expected exactly two non-empty tab-separated columns"
  fi

  generator="${parsed%%$'\n'*}"
  output="${parsed#*$'\n'}"

  validate_path "$line_no" "generator" "$generator"
  validate_path "$line_no" "output" "$output"

  [[ -f "$generator" ]] || fail "$REGISTRY:$line_no: generator script not found: $generator"
  [[ -f "$output" ]] || fail "$REGISTRY:$line_no: output path not found: $output"
  git ls-files --error-unmatch -- "$output" >/dev/null 2>&1 || fail "$REGISTRY:$line_no: output path is not tracked by git: $output"

  if contains_seen "$generator" "${generators[@]+"${generators[@]}"}"; then
    fail "$REGISTRY:$line_no: duplicate generator script: $generator"
  fi
  if contains_seen "$output" "${output_paths[@]+"${output_paths[@]}"}"; then
    fail "$REGISTRY:$line_no: duplicate output path: $output"
  fi

  generators+=("$generator")
  output_paths+=("$output")
done <"$REGISTRY"

[[ "${#generators[@]}" -gt 0 ]] || fail "$REGISTRY: no rows registered"

idx=0
while [[ "$idx" -lt "${#generators[@]}" ]]; do
  generator="${generators[$idx]}"
  output="${output_paths[$idx]}"
  if ! bash "$generator" --check; then
    fail "check-generators: drift detected by $generator (output: $output)"
  fi
  idx=$((idx + 1))
done

if ! git diff --exit-code -- "${output_paths[@]}"; then
  fail "check-generators: post-run working-tree delta detected at: ${output_paths[*]}"
fi
