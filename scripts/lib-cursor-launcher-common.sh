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

# Resolve run-log directory for cursor-ci stall JSON sidecars: prefer
# .../round-N/ when OUTPUT lives under a round dir; else highest
# $IMPLEMENT_TMPDIR/round-*; else mkdir $IMPLEMENT_TMPDIR/round-1.
# Prints absolute path on success; returns 1 when no writable target.
cursor_launcher_cursor_ci_stall_sidecar_dir() {
    local output_file="$1"
    local impl="${IMPLEMENT_TMPDIR:-}"
    local parent base
    parent="${output_file%/*}"
    base="${parent##*/}"
    case "$base" in
        round-[0-9]*) printf '%s' "$parent"; return 0 ;;
    esac
    if [[ -n "$impl" && -d "$impl" ]]; then
        local d best="" n1 n2
        shopt -s nullglob
        for d in "$impl"/round-[0-9]*; do
            [[ -d "$d" ]] || continue
            if [[ -z "$best" ]]; then
                best="$d"
            else
                n1="${d##*/round-}"
                n2="${best##*/round-}"
                n1="${n1%%[^0-9]*}"
                n2="${n2%%[^0-9]*}"
                case "$n1$n2" in
                    *[!0-9]*) ;;
                    *)
                        if ((10#$n1 > 10#$n2)); then best="$d"; fi
                        ;;
                esac
            fi
        done
        shopt -u nullglob
        if [[ -n "$best" ]]; then printf '%s' "$best"; return 0; fi
        if mkdir -p "$impl/round-1" 2>/dev/null && [[ -d "$impl/round-1" ]]; then
            printf '%s' "$impl/round-1"
            return 0
        fi
    fi
    return 1
}

# Emit round-N/cursor-ci-stall-<unix_ts>.json under the implement run log when
# jq(1) is available. Best-effort only; failures are ignored.
cursor_launcher_emit_cursor_ci_stall_json_sidecar() {
    local channel="$1" target_pid="$2" elapsed="$3" output_file="$4" diag_file="$5"
    local sidecar_dir out_json tmp_json ps_tmp lsof_tmp tr_tmp
    if ! command -v jq >/dev/null 2>&1; then
        return 0
    fi
    if ! sidecar_dir=$(cursor_launcher_cursor_ci_stall_sidecar_dir "$output_file"); then
        return 0
    fi
    [[ -n "$sidecar_dir" && -d "$sidecar_dir" ]] || return 0

    ps_tmp=$(mktemp "${TMPDIR:-/tmp}/larch-stall-ps.XXXXXX") || return 0
    lsof_tmp=$(mktemp "${TMPDIR:-/tmp}/larch-stall-lsof.XXXXXX") || {
        rm -f "$ps_tmp"
        return 0
    }
    tr_tmp=$(mktemp "${TMPDIR:-/tmp}/larch-stall-tr.XXXXXX") || {
        rm -f "$ps_tmp" "$lsof_tmp"
        return 0
    }

    {
        printf '%s\n' "--- stall ps snapshot (target pid=${target_pid}) ---"
        ps -p "$target_pid" -o pid,pcpu,etime,stat 2>/dev/null || printf '%s\n' "(target not found)"
        printf '%s\n' "--- stall ps snapshot (direct children of target; no argv) ---"
        if command -v pgrep >/dev/null 2>&1; then
            while read -r _cpid; do
                [[ -n "${_cpid:-}" ]] || continue
                ps -p "$_cpid" -o pid,pcpu,etime,stat 2>/dev/null || true
            done < <(pgrep -P "$target_pid" 2>/dev/null || true)
        fi
        printf '%s\n' "--- stall ps snapshot (ps -ef | grep [c]ursor; capped) ---"
        # shellcheck disable=SC2009 # full argv context for stall forensics; pgrep -af is narrower than ps -ef
        ps -ef 2>/dev/null | grep '[c]ursor' | head -n 80 || true
    } >"$ps_tmp" || : >"$ps_tmp"

    if command -v lsof >/dev/null 2>&1; then
        lsof -nP -p "$target_pid" 2>/dev/null | head -n 400 >"$lsof_tmp" || : >"$lsof_tmp"
    else
        : >"$lsof_tmp"
    fi

    {
        printf '%s\n' "--- stdout tail ---"
        tail -n 25 "$output_file" 2>/dev/null || true
        printf '%s\n' "--- stderr diag tail ---"
        tail -n 25 "$diag_file" 2>/dev/null || true
    } >"$tr_tmp" || : >"$tr_tmp"

    local git_porcelain="" rebase_patch=""
    git_porcelain=$(git status --porcelain 2>/dev/null || true)
    rebase_patch=$(git rebase --show-current-patch 2>/dev/null | head -n 80 || true)

    out_json="${sidecar_dir}/cursor-ci-stall-$(date +%s).json"
    tmp_json="${out_json}.tmp"
    if ! jq -nc \
        --arg channel "$channel" \
        --argjson pid "$target_pid" \
        --argjson time_since_last_progress "$elapsed" \
        --rawfile ps "$ps_tmp" \
        --rawfile lsof "$lsof_tmp" \
        --rawfile transcript "$tr_tmp" \
        --arg git_status "$git_porcelain" \
        --arg rebase_patch "$rebase_patch" \
        '($transcript | split("\n")) as $lines
        | {
            channel: $channel,
            pid: $pid,
            time_since_last_progress: $time_since_last_progress,
            ps: $ps,
            lsof: $lsof,
            git_state: {status_porcelain: $git_status, rebase_patch_excerpt: $rebase_patch},
            last_transcript_lines: (
              $lines
              | if length > 50 then .[-50:] else . end
            )
          }' >"$tmp_json" 2>/dev/null; then
        rm -f "$ps_tmp" "$lsof_tmp" "$tr_tmp" "$tmp_json"
        return 0
    fi
    rm -f "$ps_tmp" "$lsof_tmp" "$tr_tmp"
    mv -f "$tmp_json" "$out_json" 2>/dev/null || rm -f "$tmp_json"
    return 0
}

# Polls an output channel while target_pid runs; if no progress for stall_threshold
# wall seconds, appends diagnostics to diag_file and kills target_pid (SIGTERM,
# brief wait, SIGKILL). Returns 0 when the child exits on its own or after a
# stall kill. Bash 3.2-safe (no associative arrays / mapfile).
#
# Args: channel output_file stall_threshold_seconds diag_file target_pid
# channel:
#   stdout — watch output_file byte size; only size changes count as progress
#            (a missing file or persistent zero-byte capture does not refresh
#            the last-progress clock, so stall detection matches stall_threshold)
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
            if [[ -n "${tree_baseline:-}" ]]; then
                rm -f "$tree_baseline"
            fi
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
                # Avoid find|head under inherited pipefail: SIGPIPE from head can make the
                # pipeline status non-zero even when a path matched, starving last_prog_ts.
                if (
                    set +o pipefail
                    find "$tree_root" \( -name .git -prune \) -o -newer "$tree_baseline" -print 2>/dev/null | head -n 1 | grep -q .
                ); then
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
                printf '%s\n' "--- stall ps snapshot (direct children of target; no argv) ---"
                if command -v pgrep >/dev/null 2>&1; then
                    while read -r _cpid; do
                        [[ -n "${_cpid:-}" ]] || continue
                        ps -p "$_cpid" -o pid,pcpu,etime,stat 2>/dev/null || true
                    done < <(pgrep -P "$target_pid" 2>/dev/null || true)
                fi
            } >>"$diag_file"
            cursor_launcher_emit_cursor_ci_stall_json_sidecar "$channel" "$target_pid" "$elapsed" "$output_file" "$diag_file" || true
            # Kill inner agent PIDs first (run-external-agent's child), then the wrapper, so
            # SIGKILL on the wrapper cannot leave a long-lived cursor/sleep orphan.
            if command -v pgrep >/dev/null 2>&1; then
                while read -r _cpid; do
                    [[ -n "${_cpid:-}" ]] || continue
                    kill -TERM "$_cpid" 2>/dev/null || true
                done < <(pgrep -P "$target_pid" 2>/dev/null || true)
            fi
            kill -TERM "$target_pid" 2>/dev/null || true
            sleep 2
            if command -v pgrep >/dev/null 2>&1; then
                while read -r _cpid; do
                    [[ -n "${_cpid:-}" ]] || continue
                    kill -KILL "$_cpid" 2>/dev/null || true
                done < <(pgrep -P "$target_pid" 2>/dev/null || true)
            fi
            kill -KILL "$target_pid" 2>/dev/null || true
            if [[ -n "${tree_baseline:-}" ]]; then
                rm -f "$tree_baseline"
            fi
            return 0
        fi

        sleep "$poll_iv"
    done

    if [[ -n "${tree_baseline:-}" ]]; then
        rm -f "$tree_baseline"
    fi
    return 0
}

LARCH_LIB_CURSOR_LAUNCHER_COMMON_LOADED=1
