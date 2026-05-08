# shellcheck shell=bash
# Sourced-only library: no shebang and no `set -e`; callers own exit semantics.
if [[ -n "${LARCH_LIB_EXTERNAL_LAUNCHER_COMMON_LOADED:-}" ]]; then
    return 0
fi

external_launcher_promote_inner_done() {
    local output_path="$1"
    if [[ -f "${output_path}.inner.done" ]]; then
        mv -f "${output_path}.inner.done" "${output_path}.done"
    fi
}

external_launcher_append_outer_meta() {
    local meta_path="$1"
    local outer_launcher_path="$2"
    local prompt_file_sidecar="$3"
    local workdir="$4"
    [[ -f "$meta_path" ]] || return 0
    {
        printf 'OUTER_LAUNCHER=%s\n' "$outer_launcher_path"
        printf 'OUTER_LAUNCHER_PROMPT_FILE=%s\n' "$prompt_file_sidecar"
        printf 'OUTER_LAUNCHER_WORKDIR=%s\n' "$workdir"
    } >> "$meta_path"
}

LARCH_LIB_EXTERNAL_LAUNCHER_COMMON_LOADED=1
