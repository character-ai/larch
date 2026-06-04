#!/usr/bin/env bash
# check-reviewers.sh — Runtime health probe for external reviewer CLIs (Codex, Cursor).
#
# Emits CODEX_PRESENT / CURSOR_PRESENT (and *_AVAILABLE aliases) plus
# CODEX_BINARY_FOUND / CURSOR_BINARY_FOUND so callers can distinguish
# "binary missing" from "binary present but probe failed".

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh" || { echo "check-reviewers.sh: failed to source lib-quiet.sh" >&2; exit 1; }
larch_quiet_init

SKIP_CODEX_PROBE=false
SKIP_CURSOR_PROBE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-codex-probe)   SKIP_CODEX_PROBE=true; shift ;;
        --skip-cursor-probe)  SKIP_CURSOR_PROBE=true; shift ;;
        *) larch_err "check-reviewers.sh: unknown argument: $1"; exit 1 ;;
    esac
done

CODEX_BINARY_FOUND=false
CURSOR_BINARY_FOUND=false
if command -v codex >/dev/null 2>&1; then
    CODEX_BINARY_FOUND=true
fi
if command -v cursor >/dev/null 2>&1; then
    CURSOR_BINARY_FOUND=true
fi

CODEX_PRESENT=false
CURSOR_PRESENT=false

# shellcheck source=scripts/lib-cursor-launcher-common.sh
source "$SCRIPT_DIR/lib-cursor-launcher-common.sh" || { larch_err "check-reviewers.sh: failed to source lib-cursor-launcher-common.sh"; exit 1; }
# shellcheck source=scripts/lib-cursor-auth.sh
source "$SCRIPT_DIR/lib-cursor-auth.sh" || { larch_err "check-reviewers.sh: failed to source lib-cursor-auth.sh"; exit 1; }

LARCH_PROBE_TTL_SECONDS="${LARCH_PROBE_TTL_SECONDS:-60}"
case "$LARCH_PROBE_TTL_SECONDS" in
    ''|*[!0-9]*) LARCH_PROBE_TTL_SECONDS=60 ;;
esac

LARCH_PROBE_TIMEOUT_SECONDS="${LARCH_PROBE_TIMEOUT_SECONDS:-30}"
case "$LARCH_PROBE_TIMEOUT_SECONDS" in
    ''|*[!0-9]*|0) LARCH_PROBE_TIMEOUT_SECONDS=30 ;;
esac

MAX_AUTH_RETRIES="${LARCH_EXTERNAL_AUTH_RETRIES:-5}"
case "$MAX_AUTH_RETRIES" in
    ''|*[!0-9]*|0) MAX_AUTH_RETRIES=5 ;;
esac

HOLD="${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}"

PROBE_TMPFILES=()
PROBE_PIDS=()
PROBE_DIRS=()
larch_probe_exit_cleanup() {
    local i
    for ((i = 0; i < ${#PROBE_TMPFILES[@]}; i++)); do
        rm -f "${PROBE_TMPFILES[i]}"
    done
    for ((i = 0; i < ${#PROBE_PIDS[@]}; i++)); do
        kill "${PROBE_PIDS[i]}" 2>/dev/null || true
    done
    for ((i = 0; i < ${#PROBE_DIRS[@]}; i++)); do
        rm -rf "${PROBE_DIRS[i]}"
    done
}
trap 'larch_probe_exit_cleanup' EXIT

larch_stamp_path() {
    local _u="${USER//[^A-Za-z0-9._-]/}"
    printf '%s' "${TMPDIR:-/tmp}/larch-${1}-present-${_u:-larch}.stamp"
}

larch_codex_probe_stamp_key() {
    if external_codex_env_key_enabled; then
        printf '%s' codex-env-key
    else
        printf '%s' codex-login
    fi
}

# Reads stamp if fresh; sets named variable from first line; returns 0 on hit.
larch_try_read_fresh_stamp() {
    local stamp="$1"
    local out_var="$2"
    local now mtime age line val _tmp

    printf -v "$out_var" '%s' ""

    if (( LARCH_PROBE_TTL_SECONDS <= 0 )); then
        return 1
    fi
    [[ -f "$stamp" ]] || return 1

    mtime=""
    _tmp=""
    if _tmp=$(stat -c %Y "$stamp" 2>/dev/null) && [[ "$_tmp" =~ ^[0-9]+$ ]]; then
        mtime="$_tmp"
    elif _tmp=$(stat -f %m "$stamp" 2>/dev/null) && [[ "$_tmp" =~ ^[0-9]+$ ]]; then
        mtime="$_tmp"
    fi
    [[ -n "$mtime" ]] || return 1

    now=$(date +%s)
    age=$((now - mtime))
    if (( age < 0 )); then
        return 1
    fi
    if (( age > LARCH_PROBE_TTL_SECONDS )); then
        return 1
    fi

    line=""
    IFS= read -r line <"$stamp" || true
    val="${line//$'\r'/}"
    case "$val" in
        true|false) printf -v "$out_var" '%s' "$val"; return 0 ;;
        *) return 1 ;;
    esac
}

larch_write_bool_stamp() {
    local stamp_path="$1" val="$2"
    local stamp_tmp
    stamp_tmp=$(mktemp "${TMPDIR:-/tmp}/larch-probe-stamp.XXXXXX") || return 1
    printf '%s\n' "$val" >"$stamp_tmp"
    mv -f "$stamp_tmp" "$stamp_path"
}

# Sets second argument to wait exit status (0 ok, 124 timeout).
larch_poll_probe_pid() {
    local probe_pid="$1"
    local __rc_name="$2"
    local _poll_rc=""
    local _start=$SECONDS
    while kill -0 "$probe_pid" 2>/dev/null; do
        if (( SECONDS - _start >= LARCH_PROBE_TIMEOUT_SECONDS )); then
            kill "$probe_pid" 2>/dev/null || true
            wait "$probe_pid" 2>/dev/null || true
            _poll_rc=124
            break
        fi
        sleep 1
    done
    if [[ -z "${_poll_rc:-}" ]]; then
        wait "$probe_pid" && _poll_rc=0 || _poll_rc=$?
    fi
    printf -v "$__rc_name" '%s' "$_poll_rc"
}

larch_run_one_cursor_probe() {
    local probe_out probe_pid probe_rc _SERIAL_LOCK _probe_model_args _probe_prompt _wrap_status
    probe_out=$(mktemp "${TMPDIR:-/tmp}/larch-cursor-probe.XXXXXX") || return 1
    PROBE_TMPFILES[${#PROBE_TMPFILES[@]}]="$probe_out"

    _probe_model_args=()
    if MODEL_ARGS_TMP=$(mktemp) && "$SCRIPT_DIR/agent-model-args.sh" --tool cursor > "$MODEL_ARGS_TMP" 2>/dev/null; then
        while IFS= read -r _model_arg; do
            _probe_model_args+=("$_model_arg")
        done < "$MODEL_ARGS_TMP"
    fi
    [[ -n "${MODEL_ARGS_TMP:-}" ]] && rm -f "$MODEL_ARGS_TMP"

    _probe_prompt=$({ "$SCRIPT_DIR/cursor-wrap-prompt.sh" "Respond with OK"; _wrap_status=$?; printf X; exit "$_wrap_status"; }) || { rm -f "$probe_out"; return 1; }
    _probe_prompt=${_probe_prompt%X}

    _SERIAL_LOCK=""
    external_serial_lock_acquire _SERIAL_LOCK "cursor" || { rm -f "$probe_out"; return 1; }
    # shellcheck disable=SC2068
    cursor agent -p "$_probe_prompt" --trust --workspace "$PWD" \
        ${_probe_model_args[@]+"${_probe_model_args[@]}"} >"$probe_out" 2>&1 &
    probe_pid=$!
    PROBE_PIDS[${#PROBE_PIDS[@]}]="$probe_pid"
    external_serial_lock_release_after "$_SERIAL_LOCK" "$HOLD"

    larch_poll_probe_pid "$probe_pid" probe_rc

    if (( probe_rc == 0 )); then
        rm -f "$probe_out"
        return 0
    fi
    if external_is_auth_failure "cursor" "$probe_out"; then
        if (( AUTH_ATTEMPT < MAX_AUTH_RETRIES )); then
            rm -f "$probe_out"
            return 2
        fi
    fi
    rm -f "$probe_out"
    return 1
}

larch_run_one_codex_probe() {
    local probe_out probe_side probe_pid probe_rc _SERIAL_LOCK _probe_model_args _codex_auth_args
    local codex_home model_args_tmp project_key trust_config_arg
    probe_out=$(mktemp "${TMPDIR:-/tmp}/larch-codex-probe.XXXXXX") || return 1
    PROBE_TMPFILES[${#PROBE_TMPFILES[@]}]="$probe_out"
    probe_side="${probe_out}.sidecar"
    : >"$probe_side"
    PROBE_TMPFILES[${#PROBE_TMPFILES[@]}]="$probe_side"
    codex_home=$(mktemp -d "${TMPDIR:-/tmp}/larch-codex-probe-home.XXXXXX") || { rm -f "$probe_out" "$probe_side"; return 1; }
    PROBE_DIRS[${#PROBE_DIRS[@]}]="$codex_home"

    if [[ -f ~/.codex/config.toml ]]; then
        cp ~/.codex/config.toml "$codex_home/config.toml" || { rm -rf "$codex_home"; rm -f "$probe_out" "$probe_side"; return 1; }
    fi
    if ! external_prepare_codex_auth "$codex_home"; then
        if external_codex_env_key_enabled; then
            printf 'codex-env-key-failure: failed to prepare Codex auth material on the OPENAI_API_KEY auth path\n' >>"$probe_side" 2>/dev/null || true
            larch_err "check-reviewers.sh: Codex OPENAI_API_KEY auth setup failed"
        else
            printf 'codex-auth-setup: failed to prepare Codex auth material\n' >>"$probe_side" 2>/dev/null || true
        fi
        rm -rf "$codex_home"
        rm -f "$probe_out" "$probe_side"
        return 1
    fi

    _probe_model_args=()
    if model_args_tmp=$(mktemp) && "$SCRIPT_DIR/agent-model-args.sh" --tool codex --with-effort >"$model_args_tmp" 2>/dev/null; then
        while IFS= read -r _model_arg; do
            _probe_model_args+=("$_model_arg")
        done <"$model_args_tmp"
    fi
    [[ -n "${model_args_tmp:-}" ]] && rm -f "$model_args_tmp"

    project_key=${PWD//\\/\\\\}
    project_key=${project_key//\"/\\\"}
    trust_config_arg="projects.\"$project_key\".trust_level=\"trusted\""
    _codex_auth_args=()
    external_codex_auth_config_args _codex_auth_args

    _SERIAL_LOCK=""
    external_serial_lock_acquire _SERIAL_LOCK "codex" || { rm -rf "$codex_home"; rm -f "$probe_out" "$probe_side"; return 1; }
    CODEX_HOME="$codex_home" codex exec --sandbox read-only -C "$PWD" \
        ${_probe_model_args[@]+"${_probe_model_args[@]}"} \
        -c "$trust_config_arg" \
        ${_codex_auth_args[@]+"${_codex_auth_args[@]}"} \
        --output-last-message "$probe_out" \
        -- "Respond with OK" \
        >/dev/null 2>>"$probe_side" &
    probe_pid=$!
    PROBE_PIDS[${#PROBE_PIDS[@]}]="$probe_pid"
    external_serial_lock_release_after "$_SERIAL_LOCK" "$HOLD"

    larch_poll_probe_pid "$probe_pid" probe_rc

    if (( probe_rc == 0 )); then
        rm -rf "$codex_home"
        rm -f "$probe_out" "$probe_side"
        return 0
    fi
    if external_is_auth_failure "codex" "$probe_out" || external_is_auth_failure "codex" "$probe_side"; then
        if (( AUTH_ATTEMPT < MAX_AUTH_RETRIES )); then
            rm -rf "$codex_home"
            rm -f "$probe_out" "$probe_side"
            return 2
        fi
    fi
    rm -rf "$codex_home"
    rm -f "$probe_out" "$probe_side"
    return 1
}
# --- Cursor ---
if [[ "$CURSOR_BINARY_FOUND" != "true" ]]; then
    CURSOR_PRESENT=false
elif [[ "$SKIP_CURSOR_PROBE" == "true" ]]; then
    CURSOR_PRESENT=false
else
    _CACHED=""
    if larch_try_read_fresh_stamp "$(larch_stamp_path cursor)" _CACHED; then
        CURSOR_PRESENT="$_CACHED"
    else
        _pf_rc=0
        cursor_auth_preflight || _pf_rc=$?
        if (( _pf_rc == 2 )); then
            CURSOR_PRESENT=false
            larch_write_bool_stamp "$(larch_stamp_path cursor)" "$CURSOR_PRESENT" || true
        else
            if ! {
                cursor_preread_service_token &&
                cursor_auth_export_env &&
                cursor_launcher_setup_private_config_dir
            }; then
                CURSOR_PRESENT=false
            else
                AUTH_ATTEMPT=1
                CURSOR_PRESENT=false
                while (( AUTH_ATTEMPT <= MAX_AUTH_RETRIES )); do
                    _one_rc=0
                    larch_run_one_cursor_probe || _one_rc=$?
                    if (( _one_rc == 0 )); then
                        CURSOR_PRESENT=true
                        break
                    fi
                    if (( _one_rc == 2 )); then
                        AUTH_ATTEMPT=$((AUTH_ATTEMPT + 1))
                        continue
                    fi
                    CURSOR_PRESENT=false
                    break
                done
            fi
            cursor_launcher_cleanup_private_config_dir
            larch_write_bool_stamp "$(larch_stamp_path cursor)" "$CURSOR_PRESENT" || true
        fi
    fi
fi

# --- Codex ---
if [[ "$CODEX_BINARY_FOUND" != "true" ]]; then
    CODEX_PRESENT=false
elif [[ "$SKIP_CODEX_PROBE" == "true" ]]; then
    CODEX_PRESENT=false
else
    _CACHED_C=""
    _CODEX_STAMP_KEY=$(larch_codex_probe_stamp_key)
    if larch_try_read_fresh_stamp "$(larch_stamp_path "$_CODEX_STAMP_KEY")" _CACHED_C \
        && [[ "$_CACHED_C" == "true" || "$_CODEX_STAMP_KEY" != "codex-env-key" ]]; then
        CODEX_PRESENT="$_CACHED_C"
    else
        AUTH_ATTEMPT=1
        CODEX_PRESENT=false
        while (( AUTH_ATTEMPT <= MAX_AUTH_RETRIES )); do
            _one_rc=0
            larch_run_one_codex_probe || _one_rc=$?
            if (( _one_rc == 0 )); then
                CODEX_PRESENT=true
                break
            fi
            if (( _one_rc == 2 )); then
                AUTH_ATTEMPT=$((AUTH_ATTEMPT + 1))
                continue
            fi
            CODEX_PRESENT=false
            break
        done
        larch_write_bool_stamp "$(larch_stamp_path "$_CODEX_STAMP_KEY")" "$CODEX_PRESENT" || true
    fi
fi

emit_kv CODEX_BINARY_FOUND "$CODEX_BINARY_FOUND"
emit_kv CURSOR_BINARY_FOUND "$CURSOR_BINARY_FOUND"
emit_kv CODEX_PRESENT "$CODEX_PRESENT"
emit_kv CURSOR_PRESENT "$CURSOR_PRESENT"
emit_kv CODEX_AVAILABLE "$CODEX_PRESENT"
emit_kv CURSOR_AVAILABLE "$CURSOR_PRESENT"
