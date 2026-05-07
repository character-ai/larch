# shellcheck shell=bash
# Sourced-only library: no shebang and no `set -e`; callers own exit semantics.
if [[ -n "${LARCH_LIB_CURSOR_LAUNCHER_COMMON_LOADED:-}" ]]; then
    return 0
fi

cursor_launcher_load_model_args() {
    local model_args_tmp rc arg
    model_args_tmp=$(mktemp) || return 1
    if "$SCRIPT_DIR/agent-model-args.sh" --tool cursor --with-effort > "$model_args_tmp"; then
        :
    else
        rc=$?
        rm -f "$model_args_tmp"
        return "$rc"
    fi
    MODEL_ARGS=()
    while IFS= read -r arg; do
        MODEL_ARGS+=("$arg")
    done < "$model_args_tmp"
    rm -f "$model_args_tmp"
}

cursor_launcher_setup_auth_argv() {
    # shellcheck source=scripts/lib-cursor-auth.sh
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/lib-cursor-auth.sh" || return 1
    cursor_auth_preflight || return $?
    # shellcheck disable=SC2034 # Fixed global consumed by the sourcing launcher.
    CURSOR_AUTH_ARGS=()
    cursor_auth_argv
}

cursor_launcher_append_outer_meta() {
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

cursor_launcher_promote_inner_done() {
    local output_path="$1"
    if [[ -f "${output_path}.inner.done" ]]; then
        mv -f "${output_path}.inner.done" "${output_path}.done"
    fi
}

LARCH_LIB_CURSOR_LAUNCHER_COMMON_LOADED=1
