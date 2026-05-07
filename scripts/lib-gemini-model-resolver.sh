# shellcheck shell=bash
# Sourced-only library: no shebang and no `set -e`; callers own exit semantics.
if [[ -n "${LARCH_LIB_GEMINI_MODEL_RESOLVER_LOADED:-}" ]]; then
    return 0
fi

resolve_gemini_model() {
    local LC_ALL=C
    local resolved=""
    local source_label=""
    if [[ -n "${LARCH_GEMINI_MODEL+x}" ]]; then
        resolved="$LARCH_GEMINI_MODEL"
        source_label="LARCH_GEMINI_MODEL"
    elif [[ -n "${CLAUDE_PLUGIN_OPTION_GEMINI_MODEL+x}" ]]; then
        resolved="$CLAUDE_PLUGIN_OPTION_GEMINI_MODEL"
        source_label="CLAUDE_PLUGIN_OPTION_GEMINI_MODEL"
    else
        resolved="gemini-2.5-pro"
        source_label="default"
    fi

    if [[ -z "${resolved//[[:space:]]/}" ]]; then
        echo "ERROR: gemini model from $source_label is blank/whitespace-only; refusing to launch (precedence chain: LARCH_GEMINI_MODEL -> CLAUDE_PLUGIN_OPTION_GEMINI_MODEL -> default)." >&2
        return 1
    fi
    if [[ "$resolved" == *[[:cntrl:]]* ]]; then
        echo "ERROR: gemini model from $source_label contains control bytes; refusing to launch." >&2
        return 1
    fi
    printf '%s' "$resolved"
}

LARCH_LIB_GEMINI_MODEL_RESOLVER_LOADED=1
