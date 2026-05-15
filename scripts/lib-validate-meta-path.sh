# shellcheck shell=bash
# lib-validate-meta-path.sh - sourced library; not executable; no shebang.
# Validates scalar paths destined for line-oriented KEY=value .meta sidecars.

if [[ -n "${LARCH_VALIDATE_META_PATH_LOADED:-}" ]]; then
    return 0
fi

validate_meta_scalar_path() {
    local field="$1"
    local value="$2"
    local LC_ALL=C

    if [[ -z "$value" || "$value" == *[!A-Za-z0-9./_-]* ]]; then
        local _msg
        _msg="ERROR: $field contains bytes outside [A-Za-z0-9._/-]; the .meta sidecar parsed by scripts/collect-agent-results.sh requires standalone argv paths so retry substitution stays byte-identical with the CMD_JSON element. Use a path containing only ASCII letters, digits, '.', '/', '_', or '-'."
        if declare -F larch_err >/dev/null 2>&1; then
            larch_err "$_msg"
        else
            printf '%s\n' "$_msg" >&2
        fi
        return 1
    fi

    return 0
}

LARCH_VALIDATE_META_PATH_LOADED=1
