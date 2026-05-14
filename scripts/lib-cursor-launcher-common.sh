# shellcheck shell=bash
# Sourced-only library: no shebang and no `set -e`; callers own exit semantics.
if [[ -n "${LARCH_LIB_CURSOR_LAUNCHER_COMMON_LOADED:-}" ]]; then
    return 0
fi

# Shared launcher mechanics common to Cursor and Codex live in
# lib-external-launcher-common.sh; the cursor_launcher_* wrappers below
# preserve the existing names so call sites in launch-review.sh --tool cursor
# and launch-cursor-implement.sh stay untouched.
# shellcheck source=scripts/lib-external-launcher-common.sh
# shellcheck disable=SC1091
source "${BASH_SOURCE[0]%/*}/lib-external-launcher-common.sh"

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
    cursor_preread_service_token
    cursor_auth_argv
}

cursor_launcher_append_outer_meta() {
    external_launcher_append_outer_meta "$@"
}

cursor_launcher_promote_inner_done() {
    external_launcher_promote_inner_done "$@"
}

# Give each cursor agent invocation its own private config directory so
# parallel processes do not race on the shared ~/.cursor/cli-config.json.
# CURSOR_CONFIG_DIR is documented at https://cursor.com/docs/cli/reference/configuration
# (not surfaced in `cursor agent --help` as of v2026.05.09-0afadcc).
cursor_launcher_setup_private_config_dir() {
    local cfg_tmp
    cfg_tmp=$(mktemp -d "${TMPDIR:-/tmp}/larch-cursor-cfg.XXXXXX") || return 1
    if [[ -f "$HOME/.cursor/cli-config.json" ]]; then
        cp "$HOME/.cursor/cli-config.json" "$cfg_tmp/cli-config.json" 2>/dev/null || true
    fi
    export CURSOR_CONFIG_DIR="$cfg_tmp"
    # shellcheck disable=SC2034  # consumed by cursor_launcher_cleanup_private_config_dir
    CURSOR_CONFIG_DIR_TMP="$cfg_tmp"
}

cursor_launcher_cleanup_private_config_dir() {
    if [[ -n "${CURSOR_CONFIG_DIR_TMP:-}" ]]; then
        rm -rf "$CURSOR_CONFIG_DIR_TMP" 2>/dev/null || true
        unset CURSOR_CONFIG_DIR_TMP CURSOR_CONFIG_DIR
    fi
}

LARCH_LIB_CURSOR_LAUNCHER_COMMON_LOADED=1
