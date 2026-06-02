#!/usr/bin/env bash
# release-prepare.sh — Read-only release prep: baseline, PR list, classify bump.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd -P)"
CLASSIFY_BUMP="$REPO_ROOT/.claude/skills/bump-version/scripts/classify-bump.sh"
GITHUB_REMOTE_REPO="$REPO_ROOT/scripts/github-remote-repo.sh"

REPO="character-ai/larch"
BUMP_OVERRIDE=""
OUT_DIR=""

emit_error() {
  local token=$1
  shift
  echo "ERROR=$token"
  if [[ $# -gt 0 ]]; then
    printf '%s\n' "$@" >&2
  fi
  exit 1
}

tsv_sanitize() {
  local s=$1
  s="${s//$'\n'/ }"
  s="${s//$'\r'/ }"
  s="${s//$'\t'/ }"
  printf '%s' "$s"
}

usage() {
  cat <<'USAGE' >&2
Usage: release-prepare.sh [--repo OWNER/REPO] [--bump major|minor|patch] --out-dir <dir>
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ $# -ge 2 ]] || emit_error invalid-args "--repo requires a value"
      REPO="$2"
      shift 2
      ;;
    --bump)
      [[ $# -ge 2 ]] || emit_error invalid-args "--bump requires a value"
      BUMP_OVERRIDE="$2"
      shift 2
      ;;
    --out-dir)
      [[ $# -ge 2 ]] || emit_error invalid-args "--out-dir requires a value"
      OUT_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      emit_error invalid-args "unknown argument: $1"
      ;;
  esac
done

if [[ -z "$OUT_DIR" ]]; then
  emit_error invalid-args "--out-dir is required"
fi

if [[ -n "$BUMP_OVERRIDE" && ! "$BUMP_OVERRIDE" =~ ^(major|minor|patch)$ ]]; then
  emit_error invalid-args "invalid --bump value: $BUMP_OVERRIDE (expected major|minor|patch)"
fi

if [[ ! "$REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
  emit_error invalid-args "invalid --repo value: $REPO"
fi

if ! command -v gh >/dev/null 2>&1; then
  emit_error dependency-missing "gh not found on PATH"
fi

if ! command -v jq >/dev/null 2>&1; then
  emit_error dependency-missing "jq not found on PATH"
fi

if ! command -v git >/dev/null 2>&1; then
  emit_error dependency-missing "git not found on PATH"
fi

mkdir -p "$OUT_DIR"
cd "$REPO_ROOT"

if [[ ! -x "$GITHUB_REMOTE_REPO" ]]; then
  emit_error dependency-missing "github-remote-repo.sh not found"
fi

origin_repo="$(bash "$GITHUB_REMOTE_REPO" origin 2>/dev/null)" || {
  emit_error origin-repo-mismatch "could not resolve origin remote to owner/repo"
}
if [[ "$origin_repo" != "$REPO" ]]; then
  emit_error origin-repo-mismatch "origin ($origin_repo) does not match --repo ($REPO)"
fi

releases_json="$(gh api "/repos/${REPO}/releases" --paginate 2>/dev/null)" || {
  emit_error gh-release-list-failed "gh api releases failed"
}

latest_tags="$(printf '%s\n' "$releases_json" | jq -s 'add | [.[] | select(.is_latest == true) | .tag_name]')"
latest_count="$(printf '%s\n' "$latest_tags" | jq 'length')"

if [[ "$latest_count" -ne 1 ]]; then
  echo "ERROR=no-unique-latest-release"
  echo "LATEST_COUNT=$latest_count"
  exit 1
fi

BASELINE_TAG="$(printf '%s\n' "$latest_tags" | jq -r '.[0]')"

if ! git fetch origin main --tags 2>/dev/null; then
  emit_error baseline-tag-unresolvable "git fetch origin main --tags failed"
fi

if ! git rev-parse --verify "${BASELINE_TAG}^{commit}" >/dev/null 2>&1; then
  emit_error baseline-tag-unresolvable "baseline tag not resolvable: $BASELINE_TAG"
fi

if ! git rev-parse --verify "main^{commit}" >/dev/null 2>&1 \
  || ! git rev-parse --verify "origin/main^{commit}" >/dev/null 2>&1; then
  emit_error stale-local-main "main or origin/main not resolvable"
fi

main_oid="$(git rev-parse "main^{commit}")"
origin_main_oid="$(git rev-parse "origin/main^{commit}")"
if [[ "$main_oid" != "$origin_main_oid" ]]; then
  emit_error stale-local-main "main ($main_oid) != origin/main ($origin_main_oid)"
fi

open_release_pr="$(gh pr list --repo "$REPO" --state open --json headRefName 2>/dev/null \
  | jq '[.[] | select(.headRefName | startswith("release/v"))] | length' 2>/dev/null || echo 0)"
if [[ "${open_release_pr:-0}" -ne 0 ]] 2>/dev/null; then
  emit_error release-cut-in-progress "open release/v* PR exists on $REPO"
fi

baseline_ver="${BASELINE_TAG#v}"
origin_plugin_json="$(git show "origin/main:.claude-plugin/plugin.json" 2>/dev/null || true)"
if [[ -n "$origin_plugin_json" ]]; then
  origin_ver="$(printf '%s\n' "$origin_plugin_json" | jq -r '.version // empty')"
  if [[ -n "$origin_ver" && "$origin_ver" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    IFS='.' read -r ob_maj ob_min ob_pat <<< "$origin_ver"
    IFS='.' read -r bl_maj bl_min bl_pat <<< "$baseline_ver"
    if (( 10#${ob_maj} > 10#${bl_maj} )) \
      || { (( 10#${ob_maj} == 10#${bl_maj} )) && (( 10#${ob_min} > 10#${bl_min} )); } \
      || { (( 10#${ob_maj} == 10#${bl_maj} )) && (( 10#${ob_min} == 10#${bl_min} )) && (( 10#${ob_pat} > 10#${bl_pat} )); }; then
      if git log "${BASELINE_TAG}..origin/main" --format=%s 2>/dev/null | grep -qE '^Release v[0-9]+\.[0-9]+\.[0-9]+$'; then
        emit_error release-already-cut "origin/main version $origin_ver is ahead of baseline $baseline_ver with Release commit"
      fi
    fi
  fi
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
missing_prs=()

if [[ -n "$pr_numbers" ]]; then
  for pr in $pr_numbers; do
    if ! pr_json="$(gh pr view "$pr" --repo "$REPO" \
      --json number,title,labels,author,url 2>/dev/null)"; then
      missing_prs+=("$pr")
      continue
    fi
    if ! number="$(printf '%s\n' "$pr_json" | jq -e -r '.number' 2>/dev/null)"; then
      missing_prs+=("$pr")
      continue
    fi
    title="$(printf '%s\n' "$pr_json" | jq -e -r '.title' 2>/dev/null | tr '\t' ' ')" || {
      missing_prs+=("$pr")
      continue
    }
    labels="$(printf '%s\n' "$pr_json" | jq -e -r '[.labels[].name] | join(",")' 2>/dev/null)" || {
      missing_prs+=("$pr")
      continue
    }
    author="$(printf '%s\n' "$pr_json" | jq -e -r '.author.login' 2>/dev/null)" || {
      missing_prs+=("$pr")
      continue
    }
    url="$(printf '%s\n' "$pr_json" | jq -e -r '.url' 2>/dev/null)" || {
      missing_prs+=("$pr")
      continue
    }
    title="$(tsv_sanitize "$title")"
    labels="$(tsv_sanitize "$labels")"
    author="$(tsv_sanitize "$author")"
    url="$(tsv_sanitize "$url")"
    printf '%s\t%s\t%s\t%s\t%s\n' "$number" "$title" "$labels" "$author" "$url" >> "$PR_LIST_FILE"
    PR_COUNT=$((PR_COUNT + 1))
  done
fi

if [[ ${#missing_prs[@]} -gt 0 ]]; then
  emit_error pr-metadata-incomplete "could not fetch PR metadata for: ${missing_prs[*]}"
fi

if [[ ! -x "$CLASSIFY_BUMP" ]]; then
  emit_error dependency-missing "classify-bump.sh not found"
fi

classify_err_file="$(mktemp)"
classify_out="$(bash "$CLASSIFY_BUMP" --base "$BASELINE_TAG" --head origin/main 2>"$classify_err_file")" || {
  classify_tail="$(tail -20 "$classify_err_file" 2>/dev/null || true)"
  rm -f "$classify_err_file"
  emit_error classify-bump-failed "classify-bump failed${classify_tail:+: $classify_tail}"
}
rm -f "$classify_err_file"

CURRENT_VERSION="$(printf '%s\n' "$classify_out" | awk -F= '$1=="CURRENT_VERSION"{print substr($0,index($0,"=")+1); exit}')"
NEW_VERSION="$(printf '%s\n' "$classify_out" | awk -F= '$1=="NEW_VERSION"{print substr($0,index($0,"=")+1); exit}')"
BUMP_TYPE="$(printf '%s\n' "$classify_out" | awk -F= '$1=="BUMP_TYPE"{print substr($0,index($0,"=")+1); exit}')"

[[ -n "$CURRENT_VERSION" && -n "$NEW_VERSION" && -n "$BUMP_TYPE" ]] || {
  emit_error classify-bump-failed "classify-bump output incomplete"
}

if [[ -n "$BUMP_OVERRIDE" ]]; then
  case "$BUMP_OVERRIDE" in
    major) BUMP_TYPE="MAJOR" ;;
    minor) BUMP_TYPE="MINOR" ;;
    patch) BUMP_TYPE="PATCH" ;;
  esac
  IFS='.' read -r ver_maj ver_min ver_pat <<< "$CURRENT_VERSION"
  case "$BUMP_TYPE" in
    MAJOR) NEW_VERSION="$((10#${ver_maj} + 1)).0.0" ;;
    MINOR) NEW_VERSION="${ver_maj}.$((10#${ver_min} + 1)).0" ;;
    PATCH) NEW_VERSION="${ver_maj}.${ver_min}.$((10#${ver_pat} + 1))" ;;
  esac
fi

echo "BASELINE_TAG=$BASELINE_TAG"
echo "CURRENT_VERSION=$CURRENT_VERSION"
echo "NEW_VERSION=$NEW_VERSION"
echo "BUMP_TYPE=$BUMP_TYPE"
echo "PR_COUNT=$PR_COUNT"
echo "PR_LIST_FILE=$PR_LIST_FILE"
