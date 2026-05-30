#!/usr/bin/env bash
# ci-behind-count.sh — Count commits the current HEAD is behind a base ref.
#
# Usage:
#   ci-behind-count.sh [--base-remote NAME] [--base-ref BRANCH] [--no-fetch]
#
# Output (stdout):
#   BEHIND_COUNT=<N>
#
# Exit codes:
#   0 — always (count errors fail open to BEHIND_COUNT=0)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

BASE_REMOTE="origin"
BASE_REF="main"
NO_FETCH=false

usage() {
    larch_err "Usage: ci-behind-count.sh [--base-remote NAME] [--base-ref BRANCH] [--no-fetch]"
}

die_usage() {
    larch_err "ci-behind-count.sh: $1"
    usage
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --base-remote) [ "$#" -ge 2 ] || die_usage "--base-remote requires a value"; BASE_REMOTE=$2; shift 2 ;;
        --base-ref) [ "$#" -ge 2 ] || die_usage "--base-ref requires a value"; BASE_REF=$2; shift 2 ;;
        --no-fetch) NO_FETCH=true; shift ;;
        --help) usage; exit 0 ;;
        *) die_usage "unknown option: $1" ;;
    esac
done

if [[ ! "$BASE_REMOTE" =~ ^[A-Za-z0-9._/-]+$ ]] || [[ ! "$BASE_REF" =~ ^[A-Za-z0-9._/-]+$ ]]; then
    larch_err "ci-behind-count.sh: --base-remote/--base-ref contain unsupported characters"
    emit_kv BEHIND_COUNT 0
    exit 0
fi

BASE_TARGET="${BASE_REMOTE}/${BASE_REF}"

if [ "$NO_FETCH" = false ]; then
    if ! git fetch "$BASE_REMOTE" "$BASE_REF" --quiet 2>/dev/null; then
        larch_err "⚠ ci-behind-count.sh: git fetch $BASE_REMOTE $BASE_REF failed — emitting BEHIND_COUNT=0"
        emit_kv BEHIND_COUNT 0
        exit 0
    fi
fi

_behind_raw=$(git rev-list "HEAD..$BASE_TARGET" --count 2>/dev/null || echo "")
if [[ -z "$_behind_raw" ]] || [[ ! "$_behind_raw" =~ ^[0-9]+$ ]]; then
    larch_err "⚠ ci-behind-count.sh: git rev-list HEAD..$BASE_TARGET --count failed — emitting BEHIND_COUNT=0"
    emit_kv BEHIND_COUNT 0
    exit 0
fi

emit_kv BEHIND_COUNT "$_behind_raw"
exit 0
