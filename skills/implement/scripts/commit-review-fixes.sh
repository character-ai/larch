#!/usr/bin/env bash
# commit-review-fixes.sh — Step 7 review-fix commit wrapper.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() { larch_err "Usage: commit-review-fixes.sh [--message MSG] [files...]"; }

fail_usage() {
    usage
    emit_kv COMMITTED false
    emit_kv SHA ""
    emit_kv ERROR "$1"
    exit 2
}

MESSAGE="Address code review feedback"
FILES=()
while [ $# -gt 0 ]; do
    case "$1" in
        --message|-m) [ $# -ge 2 ] || fail_usage "--message requires a value"; MESSAGE=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        --) shift; FILES+=("$@"); break ;;
        -*) fail_usage "unknown option: $1" ;;
        *) FILES+=("$1"); shift ;;
    esac
done

[ -n "$(printf '%s' "$MESSAGE" | tr -d '[:space:]')" ] || fail_usage "--message must be non-empty"

out_file="${TMPDIR:-/tmp}/commit-review-fixes.$$.out"
err_file="${TMPDIR:-/tmp}/commit-review-fixes.$$.err"
trap 'rm -f "$out_file" "$err_file"' EXIT

if "$PLUGIN_ROOT/scripts/git-commit.sh" -m "$MESSAGE" "${FILES[@]}" >"$out_file" 2>"$err_file"; then
    sha="$(git rev-parse HEAD 2>/dev/null || true)"
    emit_kv COMMITTED true
    emit_kv SHA "$sha"
    exit 0
fi

rc=$?
emit_kv COMMITTED false
emit_kv SHA ""
emit_kv ERROR "$(tr '\n' ' ' < "$err_file" | head -c 500)"
exit "$rc"
