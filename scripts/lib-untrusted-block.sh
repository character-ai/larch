# shellcheck shell=bash
# shellcheck disable=SC2317
# Sourced-only helpers for literal-redacted untrusted block emission.
if [ "${LARCH_LIB_UNTRUSTED_BLOCK_LOADED:-}" = "1" ]; then
    return 0 2>/dev/null || exit 0
fi
LARCH_LIB_UNTRUSTED_BLOCK_LOADED=1

larch_untrusted_redact_stream() {
    local redact_sh="${LARCH_REDACT_SECRETS_SH:-}"
    if [[ -z "$redact_sh" || ! -x "$redact_sh" ]]; then
        redact_sh="${CLAUDE_PLUGIN_ROOT:-}/scripts/redact-secrets.sh"
    fi
    if [[ ! -x "$redact_sh" ]]; then
        redact_sh="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/redact-secrets.sh"
    fi
    "$redact_sh" | sed -E \
        -e 's/&/\&amp;/g' \
        -e 's/</\&lt;/g' \
        -e 's/>/\&gt;/g'
}

larch_xml_escape_attr() {
    sed -E \
        -e 's/&/\&amp;/g' \
        -e 's/"/\&quot;/g' \
        -e 's/</\&lt;/g' \
        -e 's/>/\&gt;/g'
}

larch_emit_untrusted_file_block() {
    local tag="$1" file="$2"
    printf '<%s encoding="literal-redacted">\n' "$tag"
    larch_untrusted_redact_stream <"$file"
    printf '\n</%s>\n\n' "$tag"
}
