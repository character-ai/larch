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
        echo "ERROR: $field contains bytes outside [A-Za-z0-9._/-]; the .meta sidecar parsed by scripts/collect-agent-results.sh requires shell-quote-passthrough paths so retry substitution stays byte-identical with the printf '%q'-quoted CMD= field. Use a path containing only ASCII letters, digits, '.', '/', '_', or '-'." >&2
        return 1
    fi

    return 0
}

LARCH_VALIDATE_META_PATH_LOADED=1
