# lib-submodule-prohibition.sh — Sourced-only library; no shebang.
# Exposes emit_submodule_prohibition for prompt composers.
# shellcheck shell=bash

emit_submodule_prohibition() {
    local submodules_list="${1:-}"
    printf '%s\n' '## PROHIBITION: Submodules'
    if [[ -n "$submodules_list" && -s "$submodules_list" ]]; then
        printf '%s\n' 'Do NOT read, edit, create, delete, move, or otherwise modify any path equal to or under these submodule paths:'
        sed 's/^/- /' "$submodules_list"
    else
        printf '%s\n' 'No checked-out submodule paths were discovered for this repository.'
    fi
    printf '%s\n' "Do NOT touch \`.git/\`, \`.gitmodules\`, or any path under a submodule. If a finding or fix appears to require touching one of those paths, skip it."
}
