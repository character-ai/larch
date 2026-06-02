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
    cursor_preread_service_token
    # Auth is delivered via the CURSOR_API_KEY environment variable (issue
    # #3375), NOT a `--api-key` argv element — the Cursor child inherits the
    # normalized env key from this launcher process. The function name retains
    # the historical `_argv` suffix; callers pass no auth argv element.
    cursor_auth_export_env
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

# Resolve run-log directory for cursor-ci stall JSON sidecars: walk up from
# OUTPUT's directory for the nearest round-N ancestor; else mkdir
# $IMPLEMENT_TMPDIR/round-1 (never pick max(round) when OUTPUT is not under a
# round path — that mis-attributed sidecars to the wrong review round).
# Prints absolute path on success; returns 1 when no writable target.
cursor_launcher_cursor_ci_stall_sidecar_dir() {
    local output_file="$1"
    local impl="${IMPLEMENT_TMPDIR:-}"
    local base d_try="${output_file%/*}"
    while [[ -n "$d_try" ]]; do
        base="${d_try##*/}"
        case "$base" in
            round-[0-9]*) printf '%s' "$d_try"; return 0 ;;
        esac
        [[ "$d_try" == "/" ]] && break
        d_try="${d_try%/*}"
    done
    if [[ -n "$impl" && -d "$impl" ]]; then
        if mkdir -p "$impl/round-1" 2>/dev/null && [[ -d "$impl/round-1" ]]; then
            printf '%s' "$impl/round-1"
            return 0
        fi
    fi
    return 1
}

# Redact a bounded UTF-8-ish blob for stall JSON git_state fields using the same
# wall-clock envelope as ps/lsof/transcript captures.
_cursor_launcher_redact_stall_blob() {
    local _blob="$1" _rf="$2" _tb
    _tb=$(mktemp "${TMPDIR:-/tmp}/larch-stall-gitblob.XXXXXX") || {
        printf '%s' '[omitted: redact-secrets temp failed]'
        return 0
    }
    printf '%s' "$_blob" >"$_tb" || {
        rm -f "$_tb"
        printf '%s' '[omitted: redact-secrets temp failed]'
        return 0
    }
    if [[ ! -x "$_rf" ]]; then
        rm -f "$_tb"
        printf '%s' '[omitted: redact-secrets unavailable or not executable]'
        return 0
    fi
    if command -v timeout >/dev/null 2>&1; then
        if timeout 8 "$_rf" <"$_tb" >"${_tb}.r" 2>/dev/null; then
            cat "${_tb}.r"
        else
            printf '%s' '[omitted: redact-secrets failed or timed out]'
        fi
        rm -f "$_tb" "${_tb}.r"
    elif command -v gtimeout >/dev/null 2>&1; then
        if gtimeout 8 "$_rf" <"$_tb" >"${_tb}.r" 2>/dev/null; then
            cat "${_tb}.r"
        else
            printf '%s' '[omitted: redact-secrets failed or timed out]'
        fi
        rm -f "$_tb" "${_tb}.r"
    else
        rm -f "$_tb"
        printf '%s' '[omitted: redact-secrets skipped without timeout(1) wall-clock wrapper]'
    fi
}

# Emit round-N/cursor-ci-stall-<unix_ts>-<pid>-<rand>.json under the implement run log when
# jq(1) is available. Best-effort only; failures are ignored.
# Optional 6th arg: path to a pre-filled transcript tail snapshot (captured before SIGTERM);
# when empty or unreadable, tails are read after the caller's signal phase (legacy fallback).
# Optional 7th arg: path to a pre-filled lsof snapshot (captured before SIGTERM on the
# stalled wrapper pid). When non-empty and readable, seeds the sidecar `lsof` field so Linux
# CI does not lose FD rows after the wrapper exits during the TERM grace window; otherwise
# falls back to a post-signal `lsof -p` probe.
cursor_launcher_emit_cursor_ci_stall_json_sidecar() {
    local channel="$1" target_pid="$2" elapsed="$3" output_file="$4" diag_file="$5" transcript_pre="${6:-}" lsof_pre_path="${7:-}"
    local sidecar_dir out_json tmp_json ps_tmp lsof_tmp tr_tmp myuid os _scr _rf _p
    local transcript_tail_phase="post_sigterm" _tr_owned=1
    local _git_ws="${PWD:-.}"
    case "$channel" in
        tree:*) _git_ws="${channel#tree:}" ;;
    esac
    if ! git -C "$_git_ws" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        _git_ws="${PWD:-.}"
    fi
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

    if [[ -n "$transcript_pre" && -f "$transcript_pre" ]]; then
        tr_tmp="$transcript_pre"
        _tr_owned=0
        transcript_tail_phase="pre_sigterm"
    else
        tr_tmp=$(mktemp "${TMPDIR:-/tmp}/larch-stall-tr.XXXXXX") || {
            rm -f "$ps_tmp" "$lsof_tmp"
            return 0
        }
    fi

    myuid=$(id -u 2>/dev/null || echo 0)
    os=$(uname -s 2>/dev/null || echo "")
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
        printf '%s\n' "--- stall ps snapshot (this uid only; argv; capped; residual cross-uid argv match risk) ---"
        # shellcheck disable=SC2009 # argv snapshot for stall forensics; uid-scoped ps + grep '[c]ursor' (not full ps -ef) for privacy/portability — see diag_capture_note in emitted JSON.
        case "$os" in
            Darwin) ps -ax -u "$myuid" -o pid=,pcpu=,etime=,command= 2>/dev/null | grep '[c]ursor' | head -n 80 || true ;;
            *) ps -u "$myuid" -ww -o pid=,pcpu=,etime=,args= 2>/dev/null | grep '[c]ursor' | head -n 80 || true ;;
        esac
    } >"$ps_tmp" || : >"$ps_tmp"

    local lsof_capture_phase="post_sigterm"
    : >"$lsof_tmp"
    if [[ -n "$lsof_pre_path" && -f "$lsof_pre_path" ]]; then
        cat "$lsof_pre_path" >"$lsof_tmp" 2>/dev/null || : >"$lsof_tmp"
    fi
    if [[ -s "$lsof_tmp" ]]; then
        lsof_capture_phase="pre_sigterm"
    elif command -v lsof >/dev/null 2>&1; then
        if command -v timeout >/dev/null 2>&1; then
            # Subshell + pipefail off: SIGPIPE from head must not clobber a partial lsof snapshot.
            (
                set +o pipefail
                timeout 3 lsof -nP -p "$target_pid" 2>/dev/null | head -n 400
            ) >"$lsof_tmp" || true
        elif command -v gtimeout >/dev/null 2>&1; then
            (
                set +o pipefail
                gtimeout 3 lsof -nP -p "$target_pid" 2>/dev/null | head -n 400
            ) >"$lsof_tmp" || true
        else
            # No wall-clock wrapper for lsof(1): omit rather than risk an unbounded hang.
            : >"$lsof_tmp"
        fi
        if [[ -s "$lsof_tmp" ]]; then
            lsof_capture_phase="post_sigterm"
        fi
    fi

    if [[ "$_tr_owned" -eq 1 ]]; then
        {
            printf '%s\n' "--- stdout tail ---"
            tail -n 50 "$output_file" 2>/dev/null || true
            printf '%s\n' "--- stderr diag tail ---"
            tail -n 50 "$diag_file" 2>/dev/null || true
        } >"$tr_tmp" || : >"$tr_tmp"
    fi

    _scr="${SCRIPT_DIR:-}"
    [[ -z "$_scr" ]] && _scr="$(cd "${BASH_SOURCE[0]%/*}" && pwd)"
    _rf="$_scr/redact-secrets.sh"
    if [[ -x "$_rf" ]]; then
        if command -v timeout >/dev/null 2>&1; then
            for _p in "$ps_tmp" "$lsof_tmp" "$tr_tmp"; do
                rm -f "${_p}.r"
                if timeout 8 "$_rf" <"$_p" >"${_p}.r" 2>/dev/null; then
                    mv -f "${_p}.r" "$_p" 2>/dev/null || rm -f "${_p}.r"
                else
                    rm -f "${_p}.r"
                    printf '%s\n' '[omitted: redact-secrets failed or timed out]' >"$_p"
                fi
            done
        elif command -v gtimeout >/dev/null 2>&1; then
            for _p in "$ps_tmp" "$lsof_tmp" "$tr_tmp"; do
                rm -f "${_p}.r"
                if gtimeout 8 "$_rf" <"$_p" >"${_p}.r" 2>/dev/null; then
                    mv -f "${_p}.r" "$_p" 2>/dev/null || rm -f "${_p}.r"
                else
                    rm -f "${_p}.r"
                    printf '%s\n' '[omitted: redact-secrets failed or timed out]' >"$_p"
                fi
            done
        else
            for _p in "$ps_tmp" "$lsof_tmp" "$tr_tmp"; do
                printf '%s\n' '[omitted: redact-secrets skipped without timeout(1) wall-clock wrapper]' >"$_p"
            done
        fi
    else
        for _p in "$ps_tmp" "$lsof_tmp" "$tr_tmp"; do
            printf '%s\n' '[omitted: redact-secrets unavailable or not executable]' >"$_p"
        done
    fi

    local git_porcelain="" rebase_patch=""
    if command -v timeout >/dev/null 2>&1; then
        git_porcelain=$(timeout 3 git -C "$_git_ws" status --porcelain 2>/dev/null | head -n 200 || true)
    elif command -v gtimeout >/dev/null 2>&1; then
        git_porcelain=$(gtimeout 3 git -C "$_git_ws" status --porcelain 2>/dev/null | head -n 200 || true)
    else
        git_porcelain=""
    fi
    # Inherited pipefail + SIGPIPE from head -c must not abort assembly before jq.
    git_porcelain=$(set +o pipefail 2>/dev/null || true; printf '%s' "$git_porcelain" | head -c 32000)
    git_porcelain=$(_cursor_launcher_redact_stall_blob "$git_porcelain" "$_rf")
    local _rgd=""
    _rgd=$(git -C "$_git_ws" rev-parse --absolute-git-dir 2>/dev/null) || _rgd=""
    if [[ -n "$_rgd" && (-d "$_rgd/rebase-merge" || -d "$_rgd/rebase-apply") ]]; then
        if command -v timeout >/dev/null 2>&1; then
            rebase_patch=$(timeout 3 git -C "$_git_ws" rebase --show-current-patch 2>/dev/null | head -n 80 || true)
        elif command -v gtimeout >/dev/null 2>&1; then
            rebase_patch=$(gtimeout 3 git -C "$_git_ws" rebase --show-current-patch 2>/dev/null | head -n 80 || true)
        else
            rebase_patch=""
        fi
        rebase_patch=$(set +o pipefail 2>/dev/null || true; printf '%s' "$rebase_patch" | head -c 32000)
        rebase_patch=$(_cursor_launcher_redact_stall_blob "$rebase_patch" "$_rf")
    else
        rebase_patch=""
    fi

    out_json="${sidecar_dir}/cursor-ci-stall-$(date +%s)-$$-${RANDOM}.json"
    tmp_json=$(mktemp "${sidecar_dir}/.cursor-ci-stall.XXXXXX") || {
        rm -f "$ps_tmp" "$lsof_tmp"
        [[ -n "${tr_tmp:-}" ]] && rm -f "$tr_tmp"
        return 0
    }
    local _cap_note="The lsof field prefers a pre-SIGTERM snapshot of the stalled wrapper (lsof_capture_phase pre_sigterm) so FD rows survive fast wrapper exit on Linux CI; when that file is empty, a bounded post-SIGTERM lsof -p probe is used (post_sigterm). ps and argv sections are still captured after SIGTERM (capture_phase post_sigterm for the combined ps blob); merged stdout/stderr transcript tails in last_transcript_lines are snapshotted at stall detection before those signals (transcript_tail_capture_phase). The first Stall detected block in OUTPUT.diag is appended before SIGTERM and reflects an immediate pre-kill ps snapshot. The ps field uses uid-scoped ps(1) plus a deliberate grep '[c]ursor' argv filter (capped lines), not a full ps -ef tree — see scripts/launch-cursor-ci.md."
    if ! jq -nc \
        --arg channel "$channel" \
        --argjson pid "$target_pid" \
        --argjson time_since_last_progress "$elapsed" \
        --arg capture_phase "post_sigterm" \
        --arg lsof_capture_phase "$lsof_capture_phase" \
        --arg transcript_tail_capture_phase "$transcript_tail_phase" \
        --arg diag_capture_note "$_cap_note" \
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
            capture_phase: $capture_phase,
            lsof_capture_phase: $lsof_capture_phase,
            transcript_tail_capture_phase: $transcript_tail_capture_phase,
            diag_capture_note: $diag_capture_note,
            ps: $ps,
            lsof: $lsof,
            git_state: {status_porcelain: $git_status, rebase_patch_excerpt: $rebase_patch},
            transcript_tail_contract: "non_interleaved: stdout_block_then_stderr_block",
            last_transcript_lines: (
              $lines
              | if length > 110 then .[-110:] else . end
            )
          }' >"$tmp_json" 2>/dev/null; then
        {
            printf '%s\n' "cursor-ci-stall-json: jq assembly failed (sidecar omitted); channel=${channel} pid=${target_pid} elapsed=${elapsed}s"
        } >>"$diag_file" 2>/dev/null || true
        rm -f "$ps_tmp" "$lsof_tmp" "$tmp_json"
        [[ -n "${tr_tmp:-}" ]] && rm -f "$tr_tmp"
        return 0
    fi
    rm -f "$ps_tmp" "$lsof_tmp"
    [[ -n "${tr_tmp:-}" ]] && rm -f "$tr_tmp"
    if mv -f "$tmp_json" "$out_json" 2>/dev/null; then
        :
    else
        rm -f "$tmp_json"
        {
            printf '%s\n' "cursor-ci-stall-json: write failed (mv to sidecar path); channel=${channel} pid=${target_pid} elapsed=${elapsed}s target=${out_json}"
        } >>"$diag_file" 2>/dev/null || true
    fi
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
            local tr_pre=""
            tr_pre=$(mktemp "${TMPDIR:-/tmp}/larch-stall-tr-pre.XXXXXX") || tr_pre=""
            if [[ -n "$tr_pre" ]]; then
                {
                    printf '%s\n' "--- stdout tail ---"
                    tail -n 50 "$output_file" 2>/dev/null || true
                    printf '%s\n' "--- stderr diag tail ---"
                    tail -n 50 "$diag_file" 2>/dev/null || true
                } >"$tr_pre" || : >"$tr_pre"
            fi
            # Snapshot FDs while the stalled wrapper is still alive. Post-SIGTERM lsof in the
            # sidecar emitter often races a fast-exiting PID on Linux CI, yielding empty output.
            local lsof_pre=""
            lsof_pre=$(mktemp "${TMPDIR:-/tmp}/larch-stall-lsof-pre.XXXXXX") || lsof_pre=""
            if [[ -n "$lsof_pre" ]]; then
                if command -v lsof >/dev/null 2>&1; then
                    if command -v timeout >/dev/null 2>&1; then
                        (
                            set +o pipefail
                            timeout 3 lsof -nP -p "$target_pid" 2>/dev/null | head -n 400
                        ) >"$lsof_pre" || true
                    elif command -v gtimeout >/dev/null 2>&1; then
                        (
                            set +o pipefail
                            gtimeout 3 lsof -nP -p "$target_pid" 2>/dev/null | head -n 400
                        ) >"$lsof_pre" || true
                    else
                        : >"$lsof_pre"
                    fi
                else
                    : >"$lsof_pre"
                fi
            fi
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
            # Kill inner agent PIDs first (run-external-agent's child), then the wrapper, so
            # SIGKILL on the wrapper cannot leave a long-lived cursor/sleep orphan.
            if command -v pgrep >/dev/null 2>&1; then
                while read -r _cpid; do
                    [[ -n "${_cpid:-}" ]] || continue
                    kill -TERM "$_cpid" 2>/dev/null || true
                done < <(pgrep -P "$target_pid" 2>/dev/null || true)
            fi
            kill -TERM "$target_pid" 2>/dev/null || true
            # Stall JSON assembly (jq/redact/git) runs concurrently with the TERM grace window so
            # heavy forensics cannot extend the window before SIGKILL.
            local emit_pid=""
            ( cursor_launcher_emit_cursor_ci_stall_json_sidecar "$channel" "$target_pid" "$elapsed" "$output_file" "$diag_file" "$tr_pre" "${lsof_pre:-}" ) &
            emit_pid=$!
            sleep 2
            if command -v pgrep >/dev/null 2>&1; then
                while read -r _cpid; do
                    [[ -n "${_cpid:-}" ]] || continue
                    kill -KILL "$_cpid" 2>/dev/null || true
                done < <(pgrep -P "$target_pid" 2>/dev/null || true)
            fi
            kill -KILL "$target_pid" 2>/dev/null || true
            if [[ -n "${emit_pid:-}" ]]; then
                wait "$emit_pid" 2>/dev/null || true
            fi
            if [[ -n "${tr_pre:-}" ]]; then
                rm -f "$tr_pre"
            fi
            if [[ -n "${lsof_pre:-}" ]]; then
                rm -f "$lsof_pre"
            fi
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
