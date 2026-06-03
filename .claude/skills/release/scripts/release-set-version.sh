#!/usr/bin/env bash
# release-set-version.sh — Atomically set .claude-plugin/plugin.json .version (no git).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd -P)"
PLUGIN_JSON="${LARCH_RELEASE_SET_VERSION_PLUGIN_JSON:-$REPO_ROOT/.claude-plugin/plugin.json}"

cd "$REPO_ROOT"

usage() {
  echo "Usage: release-set-version.sh <X.Y.Z>" >&2
}

semver_lt() {
  local a_maj a_min a_pat b_maj b_min b_pat
  IFS='.' read -r a_maj a_min a_pat <<< "$1"
  IFS='.' read -r b_maj b_min b_pat <<< "$2"
  if (( 10#${a_maj} < 10#${b_maj} )); then return 0; fi
  if (( 10#${a_maj} > 10#${b_maj} )); then return 1; fi
  if (( 10#${a_min} < 10#${b_min} )); then return 0; fi
  if (( 10#${a_min} > 10#${b_min} )); then return 1; fi
  if (( 10#${a_pat} < 10#${b_pat} )); then return 0; fi
  return 1
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

NEW_VERSION="$1"

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR=jq not found on PATH" >&2
  exit 1
fi

if [[ ! "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "ERROR=invalid semver: $NEW_VERSION" >&2
  exit 1
fi

[[ -f "$PLUGIN_JSON" ]] || { echo "ERROR=$PLUGIN_JSON not found" >&2; exit 1; }
jq empty "$PLUGIN_JSON" 2>/dev/null || { echo "ERROR=$PLUGIN_JSON is not valid JSON" >&2; exit 1; }

CURRENT_VERSION=$(jq -r '.version // empty' "$PLUGIN_JSON")
[[ -n "$CURRENT_VERSION" ]] || { echo "ERROR=$PLUGIN_JSON missing .version" >&2; exit 1; }
[[ "$CURRENT_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
  echo "ERROR=current version is not semver: $CURRENT_VERSION" >&2
  exit 1
}

if [[ "$NEW_VERSION" == "$CURRENT_VERSION" ]]; then
  echo "ERROR=no-op: version already $CURRENT_VERSION" >&2
  exit 1
fi

if semver_lt "$NEW_VERSION" "$CURRENT_VERSION"; then
  echo "ERROR=downgrade refused: $NEW_VERSION < $CURRENT_VERSION" >&2
  exit 1
fi

_tmp="${PLUGIN_JSON}.tmp.$$"
if ! jq --arg v "$NEW_VERSION" '.version = $v' "$PLUGIN_JSON" > "$_tmp"; then
  rm -f "$_tmp"
  echo "ERROR=jq rewrite failed" >&2
  exit 1
fi
mv "$_tmp" "$PLUGIN_JSON"

echo "PREVIOUS_VERSION=$CURRENT_VERSION"
echo "NEW_VERSION=$NEW_VERSION"
