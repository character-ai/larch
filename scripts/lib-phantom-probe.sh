# shellcheck shell=bash
# shellcheck disable=SC2317
# Sourced-only: phantom untracked probe + conditional execution-issues warns.
# Callers must export IMPLEMENT_TMPDIR.

if [ "${LARCH_LIB_PHANTOM_PROBE_LOADED:-}" = "1" ]; then
    return 0 2>/dev/null || exit 0
fi
LARCH_LIB_PHANTOM_PROBE_LOADED=1

_phantom_probe_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_phantom_newline_fold() {
    tr '\n' ' ' | sed 's/[[:space:]]\{1,\}/ /g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

_phantom_append_warn_failure() {
    local step_token="$1"
    local combined="$2"
    local err_line folded
    err_line=$(printf '%s\n' "$combined" | grep -E '^ERROR=' | head -1 || true)
    if [ -n "$err_line" ]; then
        folded="${err_line#ERROR=}"
    else
        folded=$(printf '%s\n' "$combined" | tail -n 5 | _phantom_newline_fold)
    fi
    folded=$(printf '%s' "$folded" | _phantom_newline_fold)
    emit_kv PHANTOM_APPEND_WARN_ERROR "$folded"
    LARCH_QUIET_DISABLE=1 "${_phantom_probe_script_dir}/append-execution-issue.sh" \
        --log "${IMPLEMENT_TMPDIR}/execution-issues.md" \
        --category Warnings \
        --entry "- **Step ${step_token} — phantom warning append failed: ${folded}**" \
        >/dev/null 2>&1 || true
}

# Usage: phantom_probe_with_warn <step-token>
phantom_probe_with_warn() {
    local step_token="$1"
    local ph_out ph_status ph_reason ph_count ph_paths line append_combined append_rc folded

    if [ -z "${IMPLEMENT_TMPDIR:-}" ]; then
        emit_kv PHANTOM_STATUS unknown
        emit_kv PHANTOM_REASON "IMPLEMENT_TMPDIR-unset"
        return 0
    fi

    ph_out=$(LARCH_QUIET_DISABLE=1 "${_phantom_probe_script_dir}/check-phantom-dirty.sh" \
        --baseline "${IMPLEMENT_TMPDIR}/untracked-baseline.z" \
        --step "$step_token" \
        --phantom-paths-dir "${IMPLEMENT_TMPDIR}" 2>/dev/null || true)

    ph_status=""
    ph_reason=""
    ph_count=""
    ph_paths=""
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            STATUS=*) ph_status="${line#STATUS=}" ;;
            REASON=*) ph_reason="${line#REASON=}" ;;
            PHANTOM_COUNT=*) ph_count="${line#PHANTOM_COUNT=}" ;;
            PHANTOM_PATHS_FILE=*) ph_paths="${line#PHANTOM_PATHS_FILE=}" ;;
        esac
    done <<<"$ph_out"

    emit_kv PHANTOM_STATUS "${ph_status:-unknown}"
    if [ -n "$ph_reason" ]; then
        emit_kv PHANTOM_REASON "$ph_reason"
    fi
    if [ -n "$ph_count" ]; then
        emit_kv PHANTOM_COUNT "$ph_count"
    fi
    if [ -n "$ph_paths" ]; then
        emit_kv PHANTOM_PATHS_FILE "$ph_paths"
    fi

    case "${ph_status:-}" in
        phantom)
            append_combined=$(mktemp)
            set +e
            LARCH_QUIET_DISABLE=1 "${_phantom_probe_script_dir}/append-execution-issue.sh" \
                --log "${IMPLEMENT_TMPDIR}/execution-issues.md" \
                --category Warnings \
                --entry "- **Step ${step_token} — phantom untracked files:** ${ph_count:-?} file(s) appeared since session baseline (inspect ${IMPLEMENT_TMPDIR}/phantom-paths-${step_token}.z locally)" \
                >"$append_combined" 2>&1
            append_rc=$?
            set -e
            if [ "$append_rc" != "0" ]; then
                folded=$(cat "$append_combined")
                rm -f "$append_combined"
                _phantom_append_warn_failure "$step_token" "$folded"
            else
                rm -f "$append_combined"
            fi
            ;;
        unknown)
            append_combined=$(mktemp)
            set +e
            LARCH_QUIET_DISABLE=1 "${_phantom_probe_script_dir}/append-execution-issue.sh" \
                --log "${IMPLEMENT_TMPDIR}/execution-issues.md" \
                --category Warnings \
                --entry "- **Step ${step_token} — phantom detection inconclusive:** STATUS=unknown REASON=${ph_reason:-unknown}" \
                >"$append_combined" 2>&1
            append_rc=$?
            set -e
            if [ "$append_rc" != "0" ]; then
                folded=$(cat "$append_combined")
                rm -f "$append_combined"
                _phantom_append_warn_failure "$step_token" "$folded"
            else
                rm -f "$append_combined"
            fi
            ;;
        clean|tracked-only) ;;
        *)
            if [ -n "${ph_status:-}" ] \
                && [ "$ph_status" != "unknown" ] \
                && [ "$ph_status" != "phantom" ] \
                && [ "$ph_status" != "clean" ] \
                && [ "$ph_status" != "tracked-only" ]; then
                emit_kv PHANTOM_REASON "unparseable-check-output"
            fi
            ;;
    esac
    return 0
}
