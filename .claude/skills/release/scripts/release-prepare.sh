#!/usr/bin/env bash
# release-prepare.sh — Read-only release prep: baseline, PR list, classify bump.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd -P)"
CLASSIFY_BUMP="$REPO_ROOT/.claude/skills/bump-version/scripts/classify-bump.sh"

REPO="character-ai/larch"
BUMP_OVERRIDE=""
OUT_DIR=""

usage() {
  cat <<'USAGE' >&2
Usage: release-prepare.sh [--repo OWNER/REPO] [--bump major|minor|patch] --out-dir <dir>
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ $# -ge 2 ]] || { echo "ERROR=--repo requires a value" >&2; exit 1; }
      REPO="$2"
      shift 2
      ;;
    --bump)
      [[ $# -ge 2 ]] || { echo "ERROR=--bump requires a value" >&2; exit 1; }
      BUMP_OVERRIDE="$2"
      shift 2
      ;;
    --out-dir)
      [[ $# -ge 2 ]] || { echo "ERROR=--out-dir requires a value" >&2; exit 1; }
      OUT_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR=unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$OUT_DIR" ]]; then
  echo "ERROR=--out-dir is required" >&2
  exit 1
fi

if [[ -n "$BUMP_OVERRIDE" && ! "$BUMP_OVERRIDE" =~ ^(major|minor|patch)$ ]]; then
  echo "ERROR=invalid --bump value: $BUMP_OVERRIDE (expected major|minor|patch)" >&2
  exit 1
fi

if [[ ! "$REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
  echo "ERROR=invalid --repo value: $REPO" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR=gh not found on PATH" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR=jq not found on PATH" >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR=git not found on PATH" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

releases_json="$(gh release list --repo "$REPO" --limit 200 --json tagName,isLatest 2>/dev/null)" || {
  echo "ERROR=gh release list failed" >&2
  exit 1
}

latest_tags="$(printf '%s\n' "$releases_json" | jq -c '[.[] | select(.isLatest == true) | .tagName]')"
latest_count="$(printf '%s\n' "$latest_tags" | jq 'length')"

if [[ "$latest_count" -ne 1 ]]; then
  echo "ERROR=no-unique-latest-release"
  echo "LATEST_COUNT=$latest_count"
  exit 1
fi

BASELINE_TAG="$(printf '%s\n' "$latest_tags" | jq -r '.[0]')"

if ! git fetch origin main --tags 2>/dev/null; then
  if ! git fetch origin "tag" "$BASELINE_TAG" 2>/dev/null; then
    echo "ERROR=baseline-tag-unresolvable"
    exit 1
  fi
fi

if ! git rev-parse --verify "${BASELINE_TAG}^{commit}" >/dev/null 2>&1; then
  echo "ERROR=baseline-tag-unresolvable"
  exit 1
fi

if ! git rev-parse --verify main^{commit} >/dev/null 2>&1 \
  || ! git rev-parse --verify origin/main^{commit} >/dev/null 2>&1; then
  echo "ERROR=stale-local-main"
  exit 1
fi

main_oid="$(git rev-parse main^{commit})"
origin_main_oid="$(git rev-parse origin/main^{commit})"
if [[ "$main_oid" != "$origin_main_oid" ]]; then
  echo "ERROR=stale-local-main"
  exit 1
fi

pr_numbers="$(git log "${BASELINE_TAG}..origin/main" --format=%s 2>/dev/null \
  | sed -n 's/.*(#\([0-9][0-9]*\))$/\1/p' \
  | sort -nu \
  | tr '\n' ' ')"
pr_numbers="${pr_numbers%% }"
pr_numbers="${pr_numbers## }"

PR_LIST_FILE="$OUT_DIR/pr-list.tsv"
: > "$PR_LIST_FILE"
PR_COUNT=0

if [[ -n "$pr_numbers" ]]; then
  for pr in $pr_numbers; do
    pr_json="$(gh pr view "$pr" --repo "$REPO" \
      --json number,title,labels,author,url 2>/dev/null)" || continue
    number="$(printf '%s\n' "$pr_json" | jq -r '.number')"
    title="$(printf '%s\n' "$pr_json" | jq -r '.title' | tr '\t' ' ')"
    labels="$(printf '%s\n' "$pr_json" | jq -r '[.labels[].name] | join(",")')"
    author="$(printf '%s\n' "$pr_json" | jq -r '.author.login')"
    url="$(printf '%s\n' "$pr_json" | jq -r '.url')"
    printf '%s\t%s\t%s\t%s\t%s\n' "$number" "$title" "$labels" "$author" "$url" >> "$PR_LIST_FILE"
    PR_COUNT=$((PR_COUNT + 1))
  done
fi

if [[ ! -x "$CLASSIFY_BUMP" ]]; then
  echo "ERROR=classify-bump.sh not found" >&2
  exit 1
fi

classify_out="$(bash "$CLASSIFY_BUMP" --base "$BASELINE_TAG" 2>/dev/null)" || {
  echo "ERROR=classify-bump failed" >&2
  exit 1
}

CURRENT_VERSION="$(printf '%s\n' "$classify_out" | awk -F= '$1=="CURRENT_VERSION"{print substr($0,index($0,"=")+1); exit}')"
NEW_VERSION="$(printf '%s\n' "$classify_out" | awk -F= '$1=="NEW_VERSION"{print substr($0,index($0,"=")+1); exit}')"
BUMP_TYPE="$(printf '%s\n' "$classify_out" | awk -F= '$1=="BUMP_TYPE"{print substr($0,index($0,"=")+1); exit}')"

[[ -n "$CURRENT_VERSION" && -n "$NEW_VERSION" && -n "$BUMP_TYPE" ]] || {
  echo "ERROR=classify-bump output incomplete" >&2
  exit 1
}

if [[ -n "$BUMP_OVERRIDE" ]]; then
  case "$BUMP_OVERRIDE" in
    major) BUMP_TYPE="MAJOR" ;;
    minor) BUMP_TYPE="MINOR" ;;
    patch) BUMP_TYPE="PATCH" ;;
  esac
  IFS='.' read -r maj min pat <<< "$CURRENT_VERSION"
  case "$BUMP_TYPE" in
    MAJOR) NEW_VERSION="$((maj + 1)).0.0" ;;
    MINOR) NEW_VERSION="${maj}.$((min + 1)).0" ;;
    PATCH) NEW_VERSION="${maj}.${min}.$((pat + 1))" ;;
  esac
fi

echo "BASELINE_TAG=$BASELINE_TAG"
echo "CURRENT_VERSION=$CURRENT_VERSION"
echo "NEW_VERSION=$NEW_VERSION"
echo "BUMP_TYPE=$BUMP_TYPE"
echo "PR_COUNT=$PR_COUNT"
echo "PR_LIST_FILE=$PR_LIST_FILE"
