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

# Polls an output channel while target_pid runs; if no progress for stall_threshold
# wall seconds, appends diagnostics to diag_file and kills target_pid (SIGTERM,
# brief wait, SIGKILL). Returns 0 when the child exits on its own or after a
# stall kill. Bash 3.2-safe (no associative arrays / mapfile).
#
# Args: channel output_file stall_threshold_seconds diag_file target_pid
# channel:
#   stdout — watch output_file byte size (missing file = 0 bytes)
#   file:<path> — watch path size + mtime
#   tree:<root> — watch for any filesystem change under root excluding .git
#                 (baseline temp file + find -newer; touch baseline on progress)
cursor_launcher_run_stall_monitor() {
    local channel="$1" output_file="$2" stall_threshold="$3" diag_file="$4" target_pid="$5"
    local poll_iv="${RUN_EXTERNAL_AGENT_POLL_INTERVAL:-10}"
    local mode="" fpath="" tree_root="" tree_baseline=""
    local last_prog_ts now elapsed has_prog
    local last_size=0 cur_size=0
    local last_mtime=0 cur_mtime=0 last_fsize=0 cur_fsize=0

    # shellcheck disable=SC2209 # case arms assign string tags to mode=, not command substitutions
    case "$channel" in
        stdout) mode=stdout ;;
        file:*) mode=file; fpath="${channel#file:}" ;;
        tree:*) mode=tree; tree_root="${channel#tree:}" ;;
        *) return 0 ;;
    esac

    case "$stall_threshold" in ''|*[!0-9]*|0) return 0 ;; esac

    if [[ "$mode" == tree ]]; then
        tree_baseline=$(mktemp "${TMPDIR:-/tmp}/larch-stall-tree.XXXXXX") || return 0
        if ! touch "$tree_baseline"; then
            rm -f "$tree_baseline"
            return 0
        fi
    fi

    last_prog_ts=$(date +%s)
    if [[ "$mode" == stdout ]]; then
        if [[ -f "$output_file" ]]; then
            last_size=$(wc -c <"$output_file" 2>/dev/null | tr -d ' ' || echo 0)
        else
            last_size=0
        fi
    elif [[ "$mode" == file ]]; then
        if [[ -f "$fpath" ]]; then
            last_fsize=$(wc -c <"$fpath" 2>/dev/null | tr -d ' ' || echo 0)
            if cur_mtime=$(stat -f %m "$fpath" 2>/dev/null); then
                last_mtime=$cur_mtime
            elif cur_mtime=$(stat -c %Y "$fpath" 2>/dev/null); then
                last_mtime=$cur_mtime
            else
                last_mtime=0
            fi
        else
            last_fsize=0
            last_mtime=0
        fi
    fi

    while kill -0 "$target_pid" 2>/dev/null; do
        has_prog=false
        now=$(date +%s)

        case "$mode" in
            stdout)
                cur_size=0
                if [[ -f "$output_file" ]]; then
                    cur_size=$(wc -c <"$output_file" 2>/dev/null | tr -d ' ' || echo 0)
                fi
                if [[ "$cur_size" != "$last_size" ]]; then
                    has_prog=true
                    last_size=$cur_size
                fi
                ;;
            file)
                cur_fsize=0
                cur_mtime=0
                if [[ -f "$fpath" ]]; then
                    cur_fsize=$(wc -c <"$fpath" 2>/dev/null | tr -d ' ' || echo 0)
                    if cur_mtime=$(stat -f %m "$fpath" 2>/dev/null); then
                        :
                    elif cur_mtime=$(stat -c %Y "$fpath" 2>/dev/null); then
                        :
                    else
                        cur_mtime=0
                    fi
                fi
                if [[ "$cur_fsize" != "$last_fsize" || "$cur_mtime" != "$last_mtime" ]]; then
                    has_prog=true
                    last_fsize=$cur_fsize
                    last_mtime=$cur_mtime
                fi
                ;;
            tree)
                if find "$tree_root" \( -name .git -prune \) -o -newer "$tree_baseline" -print 2>/dev/null | head -n 1 | grep -q .; then
                    has_prog=true
                    touch "$tree_baseline" || true
                fi
                ;;
        esac

        if [[ "$has_prog" == true ]]; then
            last_prog_ts=$now
        fi

        elapsed=$((now - last_prog_ts))
        if [[ "$elapsed" -ge "$stall_threshold" ]]; then
            {
                printf '%s\n' "Stall detected: channel=${channel} time_since_last_progress=${elapsed}s"
                printf '%s\n' "--- stall ps snapshot (target pid=${target_pid}) ---"
                ps -p "$target_pid" -o pid,pcpu,etime,stat 2>/dev/null || printf '%s\n' "(target not found)"
                printf '%s\n' "--- stall ps snapshot (cursor-related) ---"
                # shellcheck disable=SC2009 # ps columns per contract; pgrep cannot emit this shape
                ps axww -o pid,pcpu,etime,stat,command 2>/dev/null | grep '[c]ursor' | head -n 20 || true
            } >>"$diag_file"
            kill -TERM "$target_pid" 2>/dev/null || true
            sleep 2
            kill -KILL "$target_pid" 2>/dev/null || true
            rm -f "$tree_baseline"
            return 0
        fi

        sleep "$poll_iv"
    done

    rm -f "$tree_baseline"
    return 0
}

LARCH_LIB_CURSOR_LAUNCHER_COMMON_LOADED=1
