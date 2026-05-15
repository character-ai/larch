#!/usr/bin/env bash
# Promote the latest non-draft larch release from pre-release to latest.

set -euo pipefail

REPO="character-ai/larch"
DRY_RUN=false

usage() {
  cat <<'USAGE'
Usage: promote-latest-release.sh [--repo OWNER/REPO] [--dry-run]

Finds the latest non-draft release, clears its pre-release flag, marks it as
latest, verifies the resulting state, and prints RELEASE_* key-value lines.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ $# -ge 2 ]] || { echo 'ERROR=--repo requires a value' >&2; exit 1; }
      REPO="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR=Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v gh >/dev/null 2>&1; then
  echo 'ERROR=gh not found on PATH' >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo 'ERROR=jq not found on PATH' >&2
  exit 1
fi

if [[ ! "$REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
  echo "ERROR=Invalid --repo value: $REPO" >&2
  exit 1
fi

releases_json="$(gh release list \
  --repo "$REPO" \
  --limit 100 \
  --exclude-drafts \
  --json tagName,isPrerelease,isLatest,publishedAt,createdAt)"

# Sort by publishedAt descending to ensure we pick the truly newest release
latest_json="$(printf '%s\n' "$releases_json" | jq -cer 'sort_by(.publishedAt) | reverse | .[0] // empty')" || {
  echo "ERROR=No non-draft releases found for $REPO" >&2
  exit 1
}

tag="$(printf '%s\n' "$latest_json" | jq -er '.tagName')"
was_prerelease="$(printf '%s\n' "$latest_json" | jq -er '.isPrerelease')"
was_latest="$(printf '%s\n' "$latest_json" | jq -er '.isLatest')"
published_at="$(printf '%s\n' "$latest_json" | jq -r '.publishedAt // .createdAt // ""')"

echo "RELEASE_REPO=$REPO"
echo "RELEASE_TAG=$tag"
echo "RELEASE_PUBLISHED_AT=$published_at"
echo "RELEASE_WAS_PRERELEASE=$was_prerelease"
echo "RELEASE_WAS_LATEST=$was_latest"

if [[ "$DRY_RUN" == "true" ]]; then
  echo 'DRY_RUN=true'
  exit 0
fi

gh release edit "$tag" \
  --repo "$REPO" \
  --prerelease=false \
  --latest

verified_json="$(gh release view "$tag" \
  --repo "$REPO" \
  --json tagName,isPrerelease,isLatest)" || {
  echo "ERROR=Promoted release $tag was not found during verification" >&2
  exit 1
}

is_prerelease="$(printf '%s\n' "$verified_json" | jq -er '.isPrerelease')"
is_latest="$(printf '%s\n' "$verified_json" | jq -er '.isLatest')"

echo "RELEASE_IS_PRERELEASE=$is_prerelease"
echo "RELEASE_IS_LATEST=$is_latest"

if [[ "$is_prerelease" != "false" || "$is_latest" != "true" ]]; then
  echo "ERROR=Release $tag verification failed: isPrerelease=$is_prerelease isLatest=$is_latest" >&2
  exit 1
fi
