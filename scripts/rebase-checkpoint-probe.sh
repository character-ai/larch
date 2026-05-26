#!/usr/bin/env bash
# Combined /implement rebase checkpoint + post-rebase phantom probe.
# See scripts/rebase-checkpoint-probe.md for argv, exit codes, and KV grammar.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
# shellcheck source=scripts/lib-phantom-probe.sh
source "$SCRIPT_DIR/lib-phantom-probe.sh"

usage() {
    printf 'usage: %s <step-prefix> <short-name> [--base-remote <name>] [--base-ref <branch>]\n' "$(basename "$0")" >&2
    exit 2
}

step_prefix="${1:-}"
short_name="${2:-}"
if [ -z "$step_prefix" ] || [ -z "$short_name" ]; then
    usage
fi
shift 2

base_remote=""
base_ref=""
while [ $# -gt 0 ]; do
    case "$1" in
        --base-remote)
            [ $# -ge 2 ] || usage
            base_remote="$2"
            shift 2
            ;;
        --base-ref)
            [ $# -ge 2 ] || usage
            base_ref="$2"
            shift 2
            ;;
        *) usage ;;
    esac
done

emit_breadcrumb --category=progress "→ rebase-probe: ${step_prefix} ${short_name}"

rebase_args=(--no-push --skip-if-pushed --keep-on-conflict)
if [ -n "$base_remote" ]; then
    rebase_args+=(--base-remote "$base_remote")
fi
if [ -n "$base_ref" ]; then
    rebase_args+=(--base-ref "$base_ref")
fi

rb_stdout=$(mktemp)
rb_stderr=$(mktemp)
trap 'rm -f "$rb_stdout" "$rb_stderr"' EXIT

set +e
LARCH_QUIET_DISABLE=1 "${SCRIPT_DIR}/rebase-push.sh" "${rebase_args[@]}" >"$rb_stdout" 2>"$rb_stderr"
rc=$?
set -e

_rebase_sanitize() {
    printf '%s' "$1" | tr '\n' ' ' | sed 's/[[:space:]]\{1,\}/ /g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

_parse_conflict_files() {
    local line cf
    cf=""
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            CONFLICT_FILES=*) cf="${line#CONFLICT_FILES=}" ;;
        esac
    done <"$rb_stdout"
    if [ -z "$cf" ]; then
        cf=$(git diff --name-only --diff-filter=U 2>/dev/null | tr '\n' ',' | sed 's/,$//')
    fi
    printf '%s' "$cf"
}

_parse_rebase_error() {
    local line err
    err=""
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            REBASE_ERROR=*) err="${line#REBASE_ERROR=}"; printf '%s' "$err"; return 0 ;;
        esac
    done <"$rb_stdout"
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            REBASE_ERROR=*) err="${line#REBASE_ERROR=}"; printf '%s' "$err"; return 0 ;;
        esac
    done <"$rb_stderr"
    return 1
}

if [ "$rc" -eq 0 ]; then
    # SKIPPED_ALREADY_PUSHED before SKIPPED_ALREADY_FRESH (precedence).
    if grep -Fx "SKIPPED_ALREADY_PUSHED=true" "$rb_stdout" >/dev/null 2>&1; then
        emit_kv SKIPPED_ALREADY_PUSHED "true"
        emit_kv REBASE_OUTCOME "skipped"
    elif grep -Fx "SKIPPED_ALREADY_FRESH=true" "$rb_stdout" >/dev/null 2>&1; then
        emit_kv SKIPPED_ALREADY_FRESH "true"
        emit_kv REBASE_OUTCOME "skipped"
    else
        emit_kv REBASE_OUTCOME "ok"
    fi
    phantom_probe_with_warn "${step_prefix}-post-rebase"
    exit 0
fi

if [ "$rc" -eq 1 ]; then
    cf=$(_parse_conflict_files)
    emit_kv REBASE_OUTCOME "conflict"
    emit_kv CONFLICT_FILES "$cf"
    exit 1
fi

if [ "$rc" -eq 3 ]; then
    if raw_err=$(_parse_rebase_error); then
        :
    else
        raw_err=""
    fi
    emit_kv REBASE_OUTCOME "failed"
    emit_kv REBASE_ERROR "$(_rebase_sanitize "${raw_err:-rebase-failed}")"
    exit 3
fi

emit_kv REBASE_OUTCOME "failed"
emit_kv REBASE_ERROR "unexpected-rc-${rc}"
exit "$rc"
