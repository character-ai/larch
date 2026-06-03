#!/usr/bin/env bash
# promote-release.sh — Promote a GitHub Release to "Latest" and clear pre-release.
#
# Takes a semver version (X.Y.Z, no "v" prefix) and marks the
# corresponding GitHub Release as "Latest" and clears the pre-release
# flag via gh release edit.
#
# Usage:
#   promote-release.sh X.Y.Z
#
# Exit codes:
#   0 — release promoted (or already latest)
#   1 — release not found or gh error
#   2 — usage/argument error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() { larch_err "Usage: promote-release.sh X.Y.Z [--repo OWNER/REPO]"; }

VERSION=""
REPO_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo)
            [[ $# -ge 2 ]] || { larch_err "ERROR: --repo requires a value"; exit 2; }
            if [[ ! "$2" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
                larch_err "ERROR: invalid --repo value: $2"
                usage
                exit 2
            fi
            REPO_ARGS=(--repo "$2")
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            larch_err "ERROR: unknown option: $1"
            usage
            exit 2
            ;;
        *)
            if [[ -n "$VERSION" ]]; then
                larch_err "ERROR: unexpected extra argument: $1"
                usage
                exit 2
            fi
            VERSION="$1"
            shift
            ;;
    esac
done

if [[ -z "$VERSION" ]]; then
    usage
    exit 2
fi

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    larch_err "ERROR: invalid semver format: $VERSION (expected X.Y.Z)"
    usage
    exit 2
fi

TAG="v${VERSION}"

if ! gh release view "$TAG" ${REPO_ARGS[@]+"${REPO_ARGS[@]}"} >/dev/null; then
    larch_err "ERROR: release $TAG not found."
    exit 1
fi

CURRENT_LATEST=$(gh release list ${REPO_ARGS[@]+"${REPO_ARGS[@]}"} --json tagName,isLatest --jq 'map(select(.isLatest)) | .[0].tagName // ""') || exit 1

if [[ "$CURRENT_LATEST" == "$TAG" ]]; then
    IS_PRERELEASE=$(gh release view "$TAG" ${REPO_ARGS[@]+"${REPO_ARGS[@]}"} --json isPrerelease --jq '.isPrerelease')
    if [[ "$IS_PRERELEASE" == "true" ]]; then
        gh release edit "$TAG" ${REPO_ARGS[@]+"${REPO_ARGS[@]}"} --prerelease=false || exit 1
        emit "$TAG is already the latest release; cleared pre-release flag."
    else
        emit "$TAG is already the latest release."
    fi
    exit 0
fi

gh release edit "$TAG" ${REPO_ARGS[@]+"${REPO_ARGS[@]}"} --latest --prerelease=false || exit 1
emit "Promoted $TAG to latest release."
