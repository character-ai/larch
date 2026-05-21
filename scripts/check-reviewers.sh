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

larch_stamp_path_cursor() {
    printf '%s' "${TMPDIR:-/tmp}/larch-cursor-present-${USER:-larch}.stamp"
}

larch_stamp_path_codex() {
    printf '%s' "${TMPDIR:-/tmp}/larch-codex-present-${USER:-larch}.stamp"
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
    stamp_tmp=$(mktemp -p "${TMPDIR:-/tmp}" "larch-probe-stamp.XXXXXX") || return 1
    printf '%s\n' "$val" >"$stamp_tmp"
    mv -f "$stamp_tmp" "$stamp_path"
}

larch_run_one_cursor_probe() {
    local probe_out probe_pid probe_rc _SERIAL_LOCK
    probe_out=$(mktemp "${TMPDIR:-/tmp}/larch-cursor-probe.XXXXXX") || return 1

    _SERIAL_LOCK=""
    external_serial_lock_acquire _SERIAL_LOCK "cursor"
    # shellcheck disable=SC2086
    cursor agent -p "Respond with OK" --trust --workspace "$PWD" \
        ${CURSOR_AUTH_ARGS[@]+"${CURSOR_AUTH_ARGS[@]}"} >"$probe_out" 2>&1 &
    probe_pid=$!
    external_serial_lock_release_after "$_SERIAL_LOCK" "$HOLD"

    SECONDS=0
    probe_rc=""
    while kill -0 "$probe_pid" 2>/dev/null; do
        if (( SECONDS >= LARCH_PROBE_TIMEOUT_SECONDS )); then
            kill "$probe_pid" 2>/dev/null || true
            wait "$probe_pid" 2>/dev/null || true
            probe_rc=124
            break
        fi
        sleep 1
    done
    if [[ -z "${probe_rc:-}" ]]; then
        wait "$probe_pid" && probe_rc=0 || probe_rc=$?
    fi

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
    local probe_out probe_side probe_pid probe_rc _SERIAL_LOCK
    probe_out=$(mktemp "${TMPDIR:-/tmp}/larch-codex-probe.XXXXXX") || return 1
    probe_side="${probe_out}.sidecar"
    : >"$probe_side"

    _SERIAL_LOCK=""
    external_serial_lock_acquire _SERIAL_LOCK "codex"
    codex exec --sandbox read-only -C "$PWD" --output-last-message "$probe_out" -- "Respond with OK" \
        >/dev/null 2>>"$probe_side" &
    probe_pid=$!
    external_serial_lock_release_after "$_SERIAL_LOCK" "$HOLD"

    SECONDS=0
    probe_rc=""
    while kill -0 "$probe_pid" 2>/dev/null; do
        if (( SECONDS >= LARCH_PROBE_TIMEOUT_SECONDS )); then
            kill "$probe_pid" 2>/dev/null || true
            wait "$probe_pid" 2>/dev/null || true
            probe_rc=124
            break
        fi
        sleep 1
    done
    if [[ -z "${probe_rc:-}" ]]; then
        wait "$probe_pid" && probe_rc=0 || probe_rc=$?
    fi

    if (( probe_rc == 0 )); then
        rm -f "$probe_out" "$probe_side"
        return 0
    fi
    if external_is_auth_failure "codex" "$probe_out" || external_is_auth_failure "codex" "$probe_side"; then
        if (( AUTH_ATTEMPT < MAX_AUTH_RETRIES )); then
            rm -f "$probe_out" "$probe_side"
            return 2
        fi
    fi
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
    if larch_try_read_fresh_stamp "$(larch_stamp_path_cursor)" _CACHED; then
        CURSOR_PRESENT="$_CACHED"
    else
        _pf_rc=0
        cursor_auth_preflight || _pf_rc=$?
        if (( _pf_rc == 2 )); then
            CURSOR_PRESENT=false
            larch_write_bool_stamp "$(larch_stamp_path_cursor)" "$CURSOR_PRESENT"
        else
            CURSOR_AUTH_ARGS=()
            cursor_preread_service_token
            cursor_auth_argv
            if ! cursor_launcher_setup_private_config_dir; then
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
            larch_write_bool_stamp "$(larch_stamp_path_cursor)" "$CURSOR_PRESENT"
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
    if larch_try_read_fresh_stamp "$(larch_stamp_path_codex)" _CACHED_C; then
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
        larch_write_bool_stamp "$(larch_stamp_path_codex)" "$CODEX_PRESENT"
    fi
fi

emit_kv CODEX_BINARY_FOUND "$CODEX_BINARY_FOUND"
emit_kv CURSOR_BINARY_FOUND "$CURSOR_BINARY_FOUND"
emit_kv CODEX_PRESENT "$CODEX_PRESENT"
emit_kv CURSOR_PRESENT "$CURSOR_PRESENT"
emit_kv CODEX_AVAILABLE "$CODEX_PRESENT"
emit_kv CURSOR_AVAILABLE "$CURSOR_PRESENT"
