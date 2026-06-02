#!/usr/bin/env bash
# release-finish.sh — Tag, GitHub Release, and promote after release PR merge.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd -P)"
PROMOTE_RELEASE="${LARCH_RELEASE_FINISH_PROMOTE_SCRIPT:-$REPO_ROOT/scripts/promote-release.sh}"
GITHUB_REMOTE_REPO="$REPO_ROOT/scripts/github-remote-repo.sh"
REDACT_SECRETS="$REPO_ROOT/scripts/redact-secrets.sh"

VERSION=""
NOTES_FILE=""
REPO=""
PR_NUMBER=""
REDACTED_NOTES_FILE=""

usage() {
  cat <<'USAGE' >&2
Usage: release-finish.sh --version <X.Y.Z> --notes-file <path> --repo OWNER/REPO --pr <N>
USAGE
}

cleanup() {
  [[ -n "$REDACTED_NOTES_FILE" && -f "$REDACTED_NOTES_FILE" ]] && rm -f "$REDACTED_NOTES_FILE"
}
trap cleanup EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      [[ $# -ge 2 ]] || { echo "ERROR=--version requires a value" >&2; exit 2; }
      VERSION="$2"
      shift 2
      ;;
    --notes-file)
      [[ $# -ge 2 ]] || { echo "ERROR=--notes-file requires a value" >&2; exit 2; }
      NOTES_FILE="$2"
      shift 2
      ;;
    --repo)
      [[ $# -ge 2 ]] || { echo "ERROR=--repo requires a value" >&2; exit 2; }
      REPO="$2"
      shift 2
      ;;
    --pr)
      [[ $# -ge 2 ]] || { echo "ERROR=--pr requires a value" >&2; exit 2; }
      PR_NUMBER="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR=unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$VERSION" || -z "$NOTES_FILE" || -z "$REPO" || -z "$PR_NUMBER" ]]; then
  echo "ERROR=missing required arguments" >&2
  usage
  exit 2
fi

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "ERROR=invalid semver: $VERSION" >&2
  exit 2
fi

if [[ ! -f "$NOTES_FILE" ]]; then
  echo "ERROR=notes file not found: $NOTES_FILE" >&2
  exit 2
fi

if [[ ! "$REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
  echo "ERROR=invalid --repo value: $REPO" >&2
  exit 2
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

if [[ ! -x "$REDACT_SECRETS" ]]; then
  echo "ERROR=redact-secrets.sh not found" >&2
  exit 1
fi

cd "$REPO_ROOT"

if [[ ! -x "$GITHUB_REMOTE_REPO" ]]; then
  echo "ERROR=github-remote-repo.sh not found" >&2
  exit 1
fi

if [[ -n "${LARCH_RELEASE_FINISH_ORIGIN_REPO:-}" ]]; then
  origin_repo="$LARCH_RELEASE_FINISH_ORIGIN_REPO"
else
  origin_repo="$(bash "$GITHUB_REMOTE_REPO" origin 2>/dev/null)" || {
    echo "ERROR=origin-remote-unresolvable" >&2
    exit 1
  }
fi
if [[ "$origin_repo" != "$REPO" ]]; then
  echo "ERROR=origin-repo-mismatch: origin ($origin_repo) != --repo ($REPO)" >&2
  exit 1
fi

REDACTED_NOTES_FILE="$(mktemp)"
if ! "$REDACT_SECRETS" < "$NOTES_FILE" > "$REDACTED_NOTES_FILE"; then
  echo "ERROR=notes redaction failed" >&2
  exit 1
fi

TAG="v${VERSION}"

merge_oid=""
for _attempt in 1 2 3 4 5; do
  merge_oid="$(gh pr view "$PR_NUMBER" --repo "$REPO" --json mergeCommit -q '.mergeCommit.oid // empty' 2>/dev/null || true)"
  merge_oid="${merge_oid//$'\n'/}"
  merge_oid="${merge_oid%% *}"
  if [[ -n "$merge_oid" && "$merge_oid" != "null" ]]; then
    break
  fi
  sleep 2
done

if [[ -z "$merge_oid" || "$merge_oid" == "null" ]]; then
  echo "ERROR=merge-commit-missing" >&2
  exit 1
fi

TARGET_OID="$merge_oid"

if [[ -n "${LARCH_RELEASE_FINISH_AT_VERSION:-}" ]]; then
  at_version="$LARCH_RELEASE_FINISH_AT_VERSION"
else
  plugin_blob="$(git show "${TARGET_OID}:.claude-plugin/plugin.json" 2>/dev/null)" || {
    echo "ERROR=could not read plugin.json at TARGET_OID" >&2
    exit 1
  }
  at_version="$(printf '%s\n' "$plugin_blob" | jq -r '.version // empty' 2>/dev/null)" || {
    echo "ERROR=could not parse plugin.json at TARGET_OID" >&2
    exit 1
  }
fi

if [[ "$at_version" != "$VERSION" ]]; then
  echo "ERROR=version mismatch at TARGET_OID: expected $VERSION got ${at_version:-<empty>}" >&2
  exit 1
fi

remote_oid="$(git ls-remote origin "refs/tags/${TAG}" 2>/dev/null | awk '{print $1; exit}')"
remote_oid="${remote_oid:-}"

if [[ -n "$remote_oid" && "$remote_oid" != "$TARGET_OID" ]]; then
  echo "ERROR=remote tag $TAG exists on different commit ($remote_oid != $TARGET_OID)" >&2
  exit 1
fi

if git rev-parse --verify "${TAG}^{commit}" >/dev/null 2>&1; then
  local_oid="$(git rev-parse "${TAG}^{commit}")"
  if [[ "$local_oid" != "$TARGET_OID" ]]; then
    echo "ERROR=local tag $TAG points at $local_oid not $TARGET_OID" >&2
    exit 1
  fi
else
  git tag "$TAG" "$TARGET_OID"
fi

if [[ -z "$remote_oid" ]]; then
  remote_oid="$(git ls-remote origin "refs/tags/${TAG}" 2>/dev/null | awk '{print $1; exit}')"
  remote_oid="${remote_oid:-}"
fi

if [[ -z "$remote_oid" ]]; then
  if ! git push origin "$TAG" 2>/dev/null; then
    remote_oid="$(git ls-remote origin "refs/tags/${TAG}" 2>/dev/null | awk '{print $1; exit}')"
    remote_oid="${remote_oid:-}"
    if [[ "$remote_oid" != "$TARGET_OID" ]]; then
      echo "ERROR=tag push failed and remote tag missing or on wrong OID" >&2
      exit 1
    fi
  fi
fi

RELEASE_ACTION=""
if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  gh release edit "$TAG" --repo "$REPO" --title "$TAG" --notes-file "$REDACTED_NOTES_FILE" || exit 1
  RELEASE_ACTION=edit
else
  gh release create "$TAG" --repo "$REPO" --title "$TAG" --notes-file "$REDACTED_NOTES_FILE" || exit 1
  RELEASE_ACTION=create
fi

if [[ ! -x "$PROMOTE_RELEASE" ]]; then
  echo "ERROR=promote-release.sh not found" >&2
  exit 1
fi

if ! "$PROMOTE_RELEASE" "$VERSION" --repo "$REPO"; then
  echo "ERROR=promote-release-failed" >&2
  exit 1
fi

echo "RELEASE_ACTION=$RELEASE_ACTION"
echo "TARGET_OID=$TARGET_OID"
echo "TAG=$TAG"
echo "VERSION=$VERSION"
