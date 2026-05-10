#!/usr/bin/env bash
# Classify a git diff by changed-file paths for specialist review prompt routing.
#
# Output:
#   DIFF_MODE=generic|docs-only|test-only|generated-only

set -euo pipefail
export LC_ALL=C

if [[ $# -ne 1 ]]; then
  echo "classify-diff-mode.sh: expected exactly one diff file path" >&2
  exit 2
fi

DIFF_FILE="$1"
if [[ ! -f "$DIFF_FILE" ]]; then
  echo "classify-diff-mode.sh: diff file not found: $DIFF_FILE" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
GENERATORS_TSV="$REPO_ROOT/scripts/generators.tsv"

is_generated_path() {
  local path="$1"
  [[ -f "$GENERATORS_TSV" ]] || return 1
  awk -F '\t' -v path="$path" '
    /^[[:space:]]*($|#)/ { next }
    NF == 2 && $2 == path { found = 1 }
    END { exit found ? 0 : 1 }
  ' "$GENERATORS_TSV"
}

classify_path() {
  local path="$1"
  local base

  if [[ -z "$path" || "$path" == /* || "$path" == *..* ]]; then
    printf 'generic\n'
    return
  fi

  if is_generated_path "$path"; then
    printf 'generated-only\n'
    return
  fi

  base="$(basename "$path")"
  # Test classification: restrict to code/script/data files, not .md siblings.
  case "$path" in
    scripts/test-*.sh|scripts/test-*.py|skills/*/scripts/test-*.sh|*/tests/*|*/test/*)
      printf 'test-only\n'
      return
      ;;
  esac
  case "$base" in
    test_*.sh|test_*.py|test_*.go|*_test.sh|*_test.py|*_test.go|*.test.sh|*.test.py|*.test.go|*.bats)
      printf 'test-only\n'
      return
      ;;
  esac

  # Docs classification: restrict docs/ to prose extensions; bare executables
  # or unknown extensions under docs/ are conservative → generic.
  case "$path" in
    docs/*.md|docs/*.txt|docs/*.rst|docs/*.adoc|\
scripts/*.md|README.md|CHANGELOG.md|SECURITY.md|AGENTS.md|CLAUDE.md|KARPATHY_CLAUDE.md)
      printf 'docs-only\n'
      return
      ;;
  esac

  printf 'generic\n'
}

mode=""
seen_diff=false

while IFS= read -r line || [[ -n "$line" ]]; do
  [[ "$line" == diff\ --git\ * ]] || continue
  seen_diff=true

  if [[ "$line" =~ ^diff[[:space:]]--git[[:space:]]a/([^[:space:]]+)[[:space:]]b/([^[:space:]]+)$ ]]; then
    old_path="${BASH_REMATCH[1]}"
    new_path="${BASH_REMATCH[2]}"
  else
    echo "DIFF_MODE=generic"
    exit 0
  fi

  old_mode="$(classify_path "$old_path")"
  new_mode="$(classify_path "$new_path")"
  if [[ "$old_mode" != "$new_mode" || "$old_mode" == "generic" ]]; then
    echo "DIFF_MODE=generic"
    exit 0
  fi

  if [[ -z "$mode" ]]; then
    mode="$old_mode"
  elif [[ "$mode" != "$old_mode" ]]; then
    echo "DIFF_MODE=generic"
    exit 0
  fi
done < "$DIFF_FILE"

if [[ "$seen_diff" != "true" || -z "$mode" ]]; then
  echo "DIFF_MODE=generic"
else
  echo "DIFF_MODE=$mode"
fi
