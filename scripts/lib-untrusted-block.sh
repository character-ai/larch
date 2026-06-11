# shellcheck shell=bash
# shellcheck disable=SC2317
# Sourced-only helpers for literal-redacted untrusted block emission.
if [ "${LARCH_LIB_UNTRUSTED_BLOCK_LOADED:-}" = "1" ]; then
    return 0 2>/dev/null || exit 0
fi
LARCH_LIB_UNTRUSTED_BLOCK_LOADED=1

larch_untrusted_redact_stream() {
    local py_cli="${CLAUDE_PLUGIN_ROOT:-}/python/cli.py"
    if [[ -n "${LARCH_REDACT_SECRETS_SH:-}" && -x "${LARCH_REDACT_SECRETS_SH:-}" ]]; then
        "${LARCH_REDACT_SECRETS_SH}" | sed -E \
            -e 's/&/\\&amp;/g' \
            -e 's/</\\&lt;/g' \
            -e 's/>/\\&gt;/g'
        return
    fi
    if [[ ! -f "$py_cli" ]]; then
        py_cli="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)/python/cli.py"
    fi
    python3 "$py_cli" redact secrets | sed -E \
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
