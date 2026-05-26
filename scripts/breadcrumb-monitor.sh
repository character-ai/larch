#!/usr/bin/env bash
# breadcrumb-monitor.sh — foreground consumer for LARCH_BREADCRUMB_STREAM files.
# Bash 3.2-safe. See scripts/breadcrumb-monitor.md.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
# shellcheck source=scripts/lib-larch-log.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-larch-log.sh"

LARCH_QUIET_DISABLE=1
export LARCH_QUIET_DISABLE

STREAM=""
DONE_SENTINEL=""
STATUS_FILE=""
QUIET_LOG=""
SURFACED_SENT=""
PAIRED_PID_FILE=""
POLL_INTERVAL=1
RATE_CAP=5
FINAL_TAIL_LINES=30
MODE="tail"

usage() {
    printf 'Usage: %s --stream PATH --done-sentinel PATH --status-file PATH --quiet-log PATH --surfaced-sentinel PATH [--paired-pid-file PATH] [--poll-interval=SEC] [--rate-cap=N] [--final-tail-lines=N] [--mode=tail|monitor]\n' "$(basename "$0")" >&2
}

larch_bm_validate_path() {
    local label=$1 path=$2
    if [[ -z "$path" || "$path" != /* ]]; then
        larch_err "${label}: path must be absolute"
        return 2
    fi
    if [[ "$path" == *..* ]]; then
        larch_err "${label}: path must not contain .."
        return 2
    fi
    if [[ -L "$path" ]]; then
        larch_err "${label}: symlinks are rejected"
        return 2
    fi
    if ! ( LARCH_LOG_ROOT="${LARCH_LOG_ROOT:-/.__larch_no_log_root__/larch-logs}" larch_log_breadcrumbs_under_session_tmp "$path" ); then
        larch_err "${label}: path must be under IMPLEMENT_TMPDIR, DESIGN_TMPDIR, REVIEW_TMPDIR, or RESEARCH_TMPDIR"
        return 2
    fi
    if [[ -e "$path" ]] && [[ ! -f "$path" ]]; then
        larch_err "${label}: not a regular file"
        return 2
    fi
    return 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --stream) STREAM="${2:?}"; shift 2 ;;
        --done-sentinel) DONE_SENTINEL="${2:?}"; shift 2 ;;
        --status-file) STATUS_FILE="${2:?}"; shift 2 ;;
        --quiet-log) QUIET_LOG="${2:?}"; shift 2 ;;
        --surfaced-sentinel) SURFACED_SENT="${2:?}"; shift 2 ;;
        --paired-pid-file) PAIRED_PID_FILE="${2:?}"; shift 2 ;;
        --poll-interval=*) POLL_INTERVAL="${1#*=}"; shift ;;
        --rate-cap=*) RATE_CAP="${1#*=}"; shift ;;
        --final-tail-lines=*) FINAL_TAIL_LINES="${1#*=}"; shift ;;
        --mode=*) MODE="${1#*=}"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done

[[ -n "$STREAM" && -n "$DONE_SENTINEL" && -n "$STATUS_FILE" && -n "$QUIET_LOG" && -n "$SURFACED_SENT" ]] || {
    usage
    exit 2
}

larch_bm_validate_path --stream "$STREAM" || exit 2
larch_bm_validate_path --done-sentinel "$DONE_SENTINEL" || exit 2
larch_bm_validate_path --status-file "$STATUS_FILE" || exit 2
larch_bm_validate_path --quiet-log "$QUIET_LOG" || exit 2
larch_bm_validate_path --surfaced-sentinel "$SURFACED_SENT" || exit 2
if [[ -n "$PAIRED_PID_FILE" ]]; then
    larch_bm_validate_path --paired-pid-file "$PAIRED_PID_FILE" || exit 2
fi

printf 'MODE=%s\n' "$MODE"

if [[ -s "$SURFACED_SENT" ]]; then
    exit 0
fi

OFFSET_FILE="${STREAM}.bc-offset"
REDACT_STATE="${STREAM}.bc-redact-state"
printf 'in_pem=0\n' >"$REDACT_STATE"

last_off=0
if [[ -f "$OFFSET_FILE" ]]; then
    last_off=$(tr -d ' ' <"$OFFSET_FILE" || echo 0)
fi

buf=""
rate_bucket=0
rate_ts=$(date +%s)
START_TS=$rate_ts
TIMEOUT_SECONDS=1800
case "${LARCH_BM_TEST_TIMEOUT_SECONDS:-}" in
    ''|*[!0-9]*) ;;
    *)
        if (( 10#$LARCH_BM_TEST_TIMEOUT_SECONDS > 0 )); then
            TIMEOUT_SECONDS=$((10#$LARCH_BM_TEST_TIMEOUT_SECONDS))
        fi
        ;;
esac

larch_bm_rate_allow() {
    local now=$1
    if (( now - rate_ts >= 1 )); then
        rate_bucket=0
        rate_ts=$now
    fi
    if (( rate_bucket >= RATE_CAP )); then
        printf '%s\n' "WARN rate-capped"
        return 1
    fi
    rate_bucket=$((rate_bucket + 1))
    return 0
}

larch_bm_emit_line() {
    local line=$1 now=$2 _cval
    case "$line" in
        larch:bc*)
            _cval=$(printf '%s\n' "$line" | awk '{
              for (i = 1; i <= NF; i++)
                if ($i ~ /^c=/) { sub(/^c=/, "", $i); print $i; exit }
            }')
            larch_quiet_bc_valid_category "$_cval" || return 0
            ;;
        *)
            larch_err "WARN drop-non-breadcrumb-line"
            return 0
            ;;
    esac
    local out
    if ! out=$(printf '%s\n' "$line" | "$SCRIPT_DIR/lib-redact-streaming.sh" --state-file="$REDACT_STATE"); then
        larch_err "WARN redact-drop-line"
        return 0
    fi
    if larch_bm_rate_allow "$now"; then
        printf '%s\n' "$out"
    fi
}

larch_bm_process_chunk() {
    local chunk=$1 now=$2
    buf="${buf}${chunk}"
    while [[ "$buf" == *$'\n'* ]]; do
        local line="${buf%%$'\n'*}"
        buf="${buf#*$'\n'}"
        larch_bm_emit_line "$line" "$now"
    done
}

larch_bm_read_chunk() {
    local file=$1 offset=$2 count=$3 out
    out="$(
        {
            dd if="$file" bs=1 skip="$offset" count="$count" 2>/dev/null || true
            printf '\001'
        }
    )"
    chunk="${out%$'\001'}"
}

larch_bm_warn_bad_paired_pid() {
    larch_err "WARN paired-pid-file-missing"
    return 0
}

larch_bm_signal_paired_pid() {
    local raw pid len poll_count
    if [[ -z "$PAIRED_PID_FILE" || ! -f "$PAIRED_PID_FILE" ]]; then
        larch_bm_warn_bad_paired_pid
        return 0
    fi
    raw="$(
        {
            dd if="$PAIRED_PID_FILE" bs=1 count=33 2>/dev/null || exit 1
            printf '\001'
        }
    )" || {
        larch_bm_warn_bad_paired_pid
        return 0
    }
    raw="${raw%$'\001'}"
    len=$(LC_ALL=C printf '%s' "$raw" | wc -c | tr -d ' ')
    if [[ -z "$raw" || "$len" -gt 32 ]]; then
        larch_bm_warn_bad_paired_pid
        return 0
    fi
    case "$raw" in
        *$'\n') raw="${raw%$'\n'}" ;;
    esac
    case "$raw" in
        *$'\n'*|*$'\r'*)
            larch_bm_warn_bad_paired_pid
            return 0
            ;;
    esac
    if ! LC_ALL=C printf '%s' "$raw" | grep -Eq '^[0-9]+$'; then
        larch_bm_warn_bad_paired_pid
        return 0
    fi
    case "$raw" in
        *[1-9]*) ;;
        *)
            larch_bm_warn_bad_paired_pid
            return 0
            ;;
    esac
    pid="$raw"
    kill -TERM "$pid" 2>/dev/null || true
    poll_count=0
    while (( poll_count < 5 )); do
        poll_count=$((poll_count + 1))
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
    done
    kill -KILL "$pid" 2>/dev/null || true
    return 0
}

while true; do
    now=$(date +%s)
    if (( now - START_TS > TIMEOUT_SECONDS )); then
        larch_err "breadcrumb-monitor: timeout waiting for done sentinel"
        if [[ -n "$PAIRED_PID_FILE" ]]; then
            larch_bm_signal_paired_pid
        fi
        exit 4
    fi
    if [[ -s "$DONE_SENTINEL" ]]; then
        break
    fi
    new_sz=0
    if [[ -f "$STREAM" ]]; then
        new_sz=$(wc -c <"$STREAM" | tr -d ' ' || echo 0)
    fi
    if (( new_sz < last_off )); then
        printf '%s\n' "WARN reset"
        last_off=0
        buf=""
    fi
    if (( new_sz > last_off )); then
        delta=$((new_sz - last_off))
        if (( delta > 10485760 )); then
            printf '%s\n' "WARN stream-growth-exceeds-soft-cap"
        fi
        chunk=""
        larch_bm_read_chunk "$STREAM" "$last_off" "$delta"
        larch_bm_process_chunk "$chunk" "$now"
        last_off=$new_sz
        printf '%s\n' "$last_off" >"${OFFSET_FILE}.tmp" && mv -f "${OFFSET_FILE}.tmp" "$OFFSET_FILE"
    fi
    # shellcheck disable=SC2086
    sleep "$POLL_INTERVAL"
done

if [[ -n "$buf" ]]; then
    larch_bm_emit_line "$buf" "$(date +%s)"
    buf=""
fi

if [[ -f "$STREAM" ]]; then
    new_sz=$(wc -c <"$STREAM" | tr -d ' ' || echo 0)
    if (( new_sz > last_off )); then
        delta=$((new_sz - last_off))
        chunk=""
        larch_bm_read_chunk "$STREAM" "$last_off" "$delta"
        larch_bm_process_chunk "$chunk" "$(date +%s)"
        if [[ -n "$buf" ]]; then
            larch_bm_emit_line "$buf" "$(date +%s)"
            buf=""
        fi
    fi
fi

exit_code=0
if [[ -f "$STATUS_FILE" ]]; then
    exit_code=$(awk -F= '/^EXIT_CODE=/{print $2; exit}' "$STATUS_FILE" 2>/dev/null || echo 0)
fi

if [[ "$exit_code" != "0" ]]; then
    printf '%s\n' "--- Failure tail (status=${exit_code}) ---"
    if [[ -f "$QUIET_LOG" ]]; then
        tail_state="${REDACT_STATE}.tail"
        printf 'in_pem=0\n' >"$tail_state"
        if ! tail -n "$FINAL_TAIL_LINES" "$QUIET_LOG" | "$SCRIPT_DIR/lib-redact-streaming.sh" --state-file="$tail_state"; then
            larch_err "WARN redact-drop-line"
        fi
    fi
fi

exit 0
