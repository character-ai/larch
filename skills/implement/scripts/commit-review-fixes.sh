#!/usr/bin/env bash
# commit-review-fixes.sh — Step 7 review-fix commit wrapper.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() { larch_err "Usage: commit-review-fixes.sh [--stage-all] [--message MSG] [files...]"; }

fail_usage() {
    usage
    emit_kv COMMITTED false
    emit_kv SHA ""
    emit_kv ERROR "$1"
    exit 2
}

MESSAGE="Address code review feedback"
STAGE_ALL=false
FILES=()
while [ $# -gt 0 ]; do
    case "$1" in
        --message|-m) [ $# -ge 2 ] || fail_usage "--message requires a value"; MESSAGE=$2; shift 2 ;;
        --stage-all) STAGE_ALL=true; shift ;;
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

read_session_key() {
    local key=$1 default_value=$2 file
    file="${IMPLEMENT_TMPDIR:-}/session-env.sh"
    if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$file" ]; then
        python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$file" --key "$key" --default "$default_value" 2>/dev/null || printf '%s\n' "$default_value"
    else
        printf '%s\n' "$default_value"
    fi
}

if [ -z "${LARCH_TIMING_LEDGER:-}" ] || [ -z "${LARCH_TOKEN_SESSION_ID:-}" ] || [ -z "${LARCH_CLAUDE_SOURCE_FILE:-}" ]; then
    LARCH_TOKEN_SESSION_ID=$(read_session_key LARCH_TOKEN_SESSION_ID "${LARCH_TOKEN_SESSION_ID:-}")
    LARCH_CLAUDE_SOURCE_FILE=$(read_session_key LARCH_CLAUDE_SOURCE_FILE "${LARCH_CLAUDE_SOURCE_FILE:-}")
    LARCH_TIMING_LEDGER=$(read_session_key LARCH_TIMING_LEDGER "${LARCH_TIMING_LEDGER:-}")
    export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
fi

"$PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step 7 — commit review fixes" || true
LARCH_TIMING_SKILL=implement "$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 7 — commit review fixes" || true

if [ "$STAGE_ALL" = true ]; then
    git add -A
fi

if "$PLUGIN_ROOT/scripts/git-commit.sh" -m "$MESSAGE" ${FILES[@]+"${FILES[@]}"} >"$out_file" 2>"$err_file"; then
    sha="$(git rev-parse HEAD 2>/dev/null || true)"
    emit_kv COMMITTED true
    emit_kv SHA "$sha"
    exit 0
else
    rc=$?
fi

emit_kv COMMITTED false
emit_kv SHA ""
emit_kv ERROR "$(tr '\n' ' ' < "$err_file" | head -c 500)"
exit "$rc"
