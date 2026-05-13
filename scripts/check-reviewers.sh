#!/usr/bin/env bash
# check-reviewers.sh — Check external reviewer binary availability and optional health probe.
#
# No -e: exit codes from probe subprocesses are informational, not errors.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=scripts/external-tool-registry.sh
source "$SCRIPT_DIR/external-tool-registry.sh" || { echo "check-reviewers.sh: failed to source external-tool-registry.sh" >&2; exit 1; }
[[ "${LARCH_EXTERNAL_TOOL_REGISTRY_LOADED:-}" == "1" ]] || { echo "check-reviewers.sh: external-tool-registry.sh sourced but sentinel missing" >&2; exit 1; }
# shellcheck source=scripts/lib-cursor-auth.sh
source "$SCRIPT_DIR/lib-cursor-auth.sh" || { echo "check-reviewers.sh: failed to source lib-cursor-auth.sh" >&2; exit 1; }
# shellcheck source=scripts/lib-external-launcher-common.sh
source "$SCRIPT_DIR/lib-external-launcher-common.sh" || { echo "check-reviewers.sh: failed to source lib-external-launcher-common.sh" >&2; exit 1; }

PROBE=false
SKIP_CODEX_PROBE=false
SKIP_CURSOR_PROBE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --probe)              PROBE=true; shift ;;
        --skip-codex-probe)   SKIP_CODEX_PROBE=true; shift ;;
        --skip-cursor-probe)  SKIP_CURSOR_PROBE=true; shift ;;
        --artifact-dir)        [[ $# -ge 2 ]] || { echo "check-reviewers.sh: --artifact-dir requires a value" >&2; exit 1; }; shift 2 ;; # accepted for backward compat; no-op (Gemini drift removed)
        *) echo "check-reviewers.sh: unknown argument: $1" >&2; exit 1 ;;
    esac
done

CODEX_AVAILABLE="false"
CURSOR_AVAILABLE="false"

command -v codex >/dev/null 2>&1 && CODEX_AVAILABLE="true"
command -v cursor >/dev/null 2>&1 && CURSOR_AVAILABLE="true"

echo "CODEX_AVAILABLE=$CODEX_AVAILABLE"
echo "CURSOR_AVAILABLE=$CURSOR_AVAILABLE"

normalize_probe_reply() {
    tr -d '[:space:]' | tr '[:upper:]' '[:lower:]'
}

get_available() {
    case "$1" in
        codex) echo "$CODEX_AVAILABLE" ;;
        cursor) echo "$CURSOR_AVAILABLE" ;;
        *) echo "check-reviewers.sh: internal error: unsupported reviewer tool: $1" >&2; exit 1 ;;
    esac
}

get_healthy() {
    case "$1" in
        codex) echo "$CODEX_HEALTHY" ;;
        cursor) echo "$CURSOR_HEALTHY" ;;
        *) echo "check-reviewers.sh: internal error: unsupported reviewer tool: $1" >&2; exit 1 ;;
    esac
}

set_healthy() {
    case "$1" in
        codex) CODEX_HEALTHY="$2" ;;
        cursor) CURSOR_HEALTHY="$2" ;;
        *) echo "check-reviewers.sh: internal error: unsupported reviewer tool: $1" >&2; exit 1 ;;
    esac
}

get_skip() {
    case "$1" in
        codex) echo "$SKIP_CODEX_PROBE" ;;
        cursor) echo "$SKIP_CURSOR_PROBE" ;;
        *) echo "check-reviewers.sh: internal error: unsupported reviewer tool: $1" >&2; exit 1 ;;
    esac
}

set_probe_error() {
    case "$1" in
        codex) CODEX_PROBE_ERROR="$2" ;;
        cursor) CURSOR_PROBE_ERROR="$2" ;;
        *) echo "check-reviewers.sh: internal error: unsupported reviewer tool: $1" >&2; exit 1 ;;
    esac
}

get_probe_error() {
    case "$1" in
        codex) echo "$CODEX_PROBE_ERROR" ;;
        cursor) echo "$CURSOR_PROBE_ERROR" ;;
        *) echo "check-reviewers.sh: internal error: unsupported reviewer tool: $1" >&2; exit 1 ;;
    esac
}

probe_output_path() {
    echo "$PROBE_DIR/$1-probe.txt"
}

clear_probe_files() {
    local output
    output=$(probe_output_path "$1")
    rm -f "$output" "${output}.done" "${output}.meta" "${output}.diag"
}

start_probe() {
    local tool="$1"
    local attempt="$2"
    local output _probe_lock _probe_pid
    output=$(probe_output_path "$tool")
    clear_probe_files "$tool"

    case "$tool" in
        codex)
            # Argv MUST track scripts/launch-review.sh --tool codex / launch-codex-implement.sh:
            # --add-dir "$PROBE_DIR" exercises the same writable-roots flag production
            # uses; model args go through scripts/agent-model-args.sh so invalid
            # LARCH_CODEX_MODEL / CLAUDE_PLUGIN_OPTION_CODEX_MODEL is rejected at
            # probe time with the same blank/[[:cntrl:]] rules production launchers
            # apply (FINDING_2 in /review code review of #1367). --with-effort is
            # intentionally omitted to keep the probe lightweight (matches the
            # negotiation-round helper).
            CODEX_MODEL_ARGS_TMP=$(mktemp "$PROBE_DIR/codex-model-args.XXXXXX") || exit 1
            if "$SCRIPT_DIR/agent-model-args.sh" --tool codex > "$CODEX_MODEL_ARGS_TMP"; then
                :
            else
                rc=$?
                {
                    printf 'Model argument validation failed before launching Codex probe (exit %s)\n' "$rc"
                } > "${output}.diag"
                : > "$output"
                printf '%s\n' "$rc" > "${output}.done"
                ( exit 0 ) &
                printf '%s\n' "$!"
                return
            fi
            CODEX_MODEL_ARGS=()
            while IFS= read -r arg; do
                CODEX_MODEL_ARGS+=("$arg")
            done < "$CODEX_MODEL_ARGS_TMP"
            _probe_lock=""
            external_serial_lock_acquire _probe_lock "codex"
            "$SCRIPT_DIR/run-external-agent.sh" \
                --tool codex \
                --output "$output" \
                --timeout 60 \
                -- codex exec --full-auto -C "$PWD" \
                --add-dir "$PROBE_DIR" \
                ${CODEX_MODEL_ARGS[@]+"${CODEX_MODEL_ARGS[@]}"} \
                --output-last-message "$output" \
                "Respond with OK" \
                >"$PROBE_DIR/codex-wrapper-attempt${attempt}.log" 2>&1 &
            _probe_pid=$!
            external_serial_lock_release_after "$_probe_lock" "${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}"
            printf '%s\n' "$_probe_pid"
            return
            ;;
        cursor)
            CURSOR_MODEL_ARGS_TMP=$(mktemp "$PROBE_DIR/cursor-model-args.XXXXXX") || exit 1
            if "$SCRIPT_DIR/agent-model-args.sh" --tool cursor > "$CURSOR_MODEL_ARGS_TMP"; then
                :
            else
                rc=$?
                {
                    printf 'Model argument validation failed before launching Cursor probe (exit %s)\n' "$rc"
                } > "${output}.diag"
                : > "$output"
                printf '%s\n' "$rc" > "${output}.done"
                ( exit 0 ) &
                printf '%s\n' "$!"
                return
            fi
            CURSOR_MODEL_ARGS=()
            while IFS= read -r arg; do
                CURSOR_MODEL_ARGS+=("$arg")
            done < "$CURSOR_MODEL_ARGS_TMP"
            # Argv MUST track scripts/launch-review.sh --tool cursor: --capture-stdout-only
            # plus --output-format json so the probe exercises the same Cursor CLI
            # path production review launches use. Drift here can produce false
            # healthy/unhealthy probe verdicts when the JSON output mode behaves
            # differently from the pre-JSON default.
            # cursor_auth_preflight is INTENTIONALLY NOT invoked here: this
            # function reports binary health, not configuration validity. A
            # missing keychain entry should not fail the probe — let the real
            # launchers surface the actionable preflight error to the operator
            # at launch time.
            CURSOR_AUTH_ARGS=()
            cursor_auth_argv
            _probe_lock=""
            external_serial_lock_acquire _probe_lock "cursor"
            "$SCRIPT_DIR/run-external-agent.sh" \
                --tool cursor \
                --output "$output" \
                --timeout 60 \
                --capture-stdout-only \
                -- cursor agent -p --force --trust --output-format json ${CURSOR_MODEL_ARGS[@]+"${CURSOR_MODEL_ARGS[@]}"} ${CURSOR_AUTH_ARGS[@]+"${CURSOR_AUTH_ARGS[@]}"} --workspace "$PWD" \
                "Respond with OK" \
                >"$PROBE_DIR/cursor-wrapper-attempt${attempt}.log" 2>&1 &
            _probe_pid=$!
            external_serial_lock_release_after "$_probe_lock" "${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}"
            printf '%s\n' "$_probe_pid"
            return
            ;;
        *)
            echo "check-reviewers.sh: internal error: unsupported reviewer tool: $tool" >&2
            exit 1
            ;;
    esac
}

evaluate_probe() {
    local tool="$1"
    local attempt="$2"
    local output exit_code reply error_text
    output=$(probe_output_path "$tool")

    if [[ ! -f "${output}.done" ]]; then
        set_probe_error "$tool" "Probe attempt $attempt did not complete (sentinel file missing — possible crash or system kill)"
        return
    fi

    exit_code=$(cat "${output}.done" 2>/dev/null || echo "99")
    if [[ "$exit_code" == "0" && -s "$output" ]]; then
        if [[ "$tool" == "cursor" ]]; then
            # Cursor probe uses --output-format json (mirroring scripts/launch-review.sh --tool cursor).
            # The reply text lives at .result; fall back to the raw body for legacy
            # plain-text output if jq is missing or the body is not valid JSON.
            if command -v jq >/dev/null 2>&1 && jq -e . "$output" >/dev/null 2>&1; then
                if jq -e '.error? // empty' "$output" >/dev/null 2>&1; then
                    error_text=$(jq -r '.error' "$output" 2>/dev/null | head -c 200 | tr '\n\r' '  ')
                    set_probe_error "$tool" "Probe attempt $attempt returned Cursor error: $error_text"
                    return
                fi
                reply=$(jq -r '.result // empty' "$output" 2>/dev/null | normalize_probe_reply)
            else
                reply=$(normalize_probe_reply < "$output")
            fi
        else
            reply=$(normalize_probe_reply < "$output")
        fi

        if [[ "$reply" == "ok" ]]; then
            set_healthy "$tool" "true"
            set_probe_error "$tool" ""
        else
            set_probe_error "$tool" "Probe attempt $attempt returned non-OK response: $(head -c 200 "$output" | tr '\n\r' '  ')"
        fi
    elif [[ -f "${output}.diag" ]]; then
        set_probe_error "$tool" "Probe attempt $attempt: $(cat "${output}.diag")"
    elif [[ "$exit_code" == "0" ]]; then
        set_probe_error "$tool" "Probe attempt $attempt exited successfully but produced no output"
    else
        set_probe_error "$tool" "Probe attempt $attempt failed with exit code $exit_code"
    fi
}

if [[ "$PROBE" == "true" ]]; then
    CODEX_HEALTHY="false"
    CURSOR_HEALTHY="false"
    CODEX_PROBE_ERROR=""
    CURSOR_PROBE_ERROR=""

    TOOLS=()
    for tool in "${LARCH_EXTERNAL_TOOLS[@]}"; do
        [[ "$tool" == "gemini" ]] && continue
        TOOLS+=("$tool")
    done

    PROBE_DIR=$(mktemp -d /tmp/larch-probe-XXXXXX)
    trap 'rm -rf "$PROBE_DIR"' EXIT

    MAX_ATTEMPTS=3
    SLEEP_BETWEEN="${LARCH_TEST_PROBE_SLEEP_SECONDS:-10}"

    WAIT_PREFLIGHT_FAILED=false
    WAIT_PREFLIGHT_ERROR=""
    WAIT_USAGE_ERROR=false
    WAIT_INFRA_ERROR_MSG=""
    if [[ -n "${WAIT_FOR_REVIEWERS_POLL_INTERVAL:-}" ]]; then
        case "${WAIT_FOR_REVIEWERS_POLL_INTERVAL}" in
            ''|*[!0-9.]*|.|0|0.|0.0|0.00|0.000)
                WAIT_PREFLIGHT_FAILED=true
                WAIT_PREFLIGHT_ERROR="WAIT_FOR_REVIEWERS_POLL_INTERVAL must be a positive number, got '${WAIT_FOR_REVIEWERS_POLL_INTERVAL}'"
                ;;
            *.*.*)
                WAIT_PREFLIGHT_FAILED=true
                WAIT_PREFLIGHT_ERROR="WAIT_FOR_REVIEWERS_POLL_INTERVAL must be a positive number, got '${WAIT_FOR_REVIEWERS_POLL_INTERVAL}'"
                ;;
        esac
        if [[ "$WAIT_PREFLIGHT_FAILED" == "false" && "${WAIT_FOR_REVIEWERS_POLL_INTERVAL}" != *.* ]]; then
            if (( 10#${WAIT_FOR_REVIEWERS_POLL_INTERVAL} < 1 )); then
                WAIT_PREFLIGHT_FAILED=true
                WAIT_PREFLIGHT_ERROR="WAIT_FOR_REVIEWERS_POLL_INTERVAL must be a positive number, got '${WAIT_FOR_REVIEWERS_POLL_INTERVAL}'"
            fi
        fi
    fi
    if [[ "$WAIT_PREFLIGHT_FAILED" == "true" ]]; then
        echo "Probe infrastructure error: $WAIT_PREFLIGHT_ERROR" >&2
    fi

    if [[ "$WAIT_PREFLIGHT_FAILED" == "false" ]]; then
        for ((attempt=1; attempt<=MAX_ATTEMPTS; attempt++)); do
        TRY_TOOLS=()
        for tool in "${TOOLS[@]}"; do
            if [[ "$(get_available "$tool")" == "true" && "$(get_skip "$tool")" == "false" && "$(get_healthy "$tool")" == "false" ]]; then
                TRY_TOOLS+=("$tool")
            fi
        done

        [[ ${#TRY_TOOLS[@]} -eq 0 ]] && break

        if [[ $attempt -gt 1 ]]; then
            echo "Retrying failed health probes (attempt $attempt of $MAX_ATTEMPTS, after ${SLEEP_BETWEEN}s sleep)..." >&2
            sleep "$SLEEP_BETWEEN"
        fi

        SENTINELS=()
        PROBE_PIDS=()
        for tool in "${TRY_TOOLS[@]}"; do
            pid=$(start_probe "$tool" "$attempt")
            PROBE_PIDS+=("$pid")
            SENTINELS+=("$(probe_output_path "$tool").done")
        done

        WAIT_USAGE_ERROR=false
        if [[ ${#SENTINELS[@]} -gt 0 ]]; then
            "$SCRIPT_DIR/wait-for-reviewers.sh" --timeout 120 "${SENTINELS[@]}" \
                >"$PROBE_DIR/wait-attempt${attempt}.stdout" \
                2>"$PROBE_DIR/wait-attempt${attempt}.stderr"
            WAIT_RC=$?
            {
                cat "$PROBE_DIR/wait-attempt${attempt}.stdout"
                echo "--- stderr ---"
                cat "$PROBE_DIR/wait-attempt${attempt}.stderr"
            } > "$PROBE_DIR/wait-attempt${attempt}.log"

            if [[ $WAIT_RC -ne 0 ]]; then
                WAIT_INFRA_ERROR_MSG="wait-for-reviewers.sh exited $WAIT_RC (see stderr for cause): $(head -c 200 "$PROBE_DIR/wait-attempt${attempt}.stderr" | tr '\n\r' '  ')"
                echo "Probe infrastructure error: $WAIT_INFRA_ERROR_MSG" >&2
                WAIT_USAGE_ERROR=true
            fi
        fi
        if [[ "$WAIT_USAGE_ERROR" == "true" ]]; then
            for _pid in "${PROBE_PIDS[@]}"; do
                kill -TERM "$_pid" 2>/dev/null || true
            done
            for _pid in "${PROBE_PIDS[@]}"; do
                wait "$_pid" 2>/dev/null || true
            done
            break
        fi

        for tool in "${TRY_TOOLS[@]}"; do
            evaluate_probe "$tool" "$attempt"
        done

        STILL_NEEDED=false
        for tool in "${TOOLS[@]}"; do
            if [[ "$(get_available "$tool")" == "true" && "$(get_skip "$tool")" == "false" && "$(get_healthy "$tool")" == "false" ]]; then
                STILL_NEEDED=true
            fi
        done
        [[ "$STILL_NEEDED" == "false" ]] && break
        done
    fi

    if [[ "${WAIT_PREFLIGHT_FAILED:-false}" == "true" || "${WAIT_USAGE_ERROR:-false}" == "true" ]]; then
        _wait_msg="${WAIT_PREFLIGHT_ERROR:-${WAIT_INFRA_ERROR_MSG:-unknown}}"
        _wait_msg=$(printf '%s' "$_wait_msg" | tr '\n\r' '  ')
        echo "WAIT_INFRA_ERROR=$_wait_msg"
        for tool in "${TOOLS[@]}"; do
            upper=$(printf '%s' "$tool" | tr '[:lower:]' '[:upper:]')
            if [[ "$(get_available "$tool")" == "true" ]]; then
                echo "${upper}_HEALTHY=false"
            fi
        done
    else
        for tool in "${TOOLS[@]}"; do
            upper=$(printf '%s' "$tool" | tr '[:lower:]' '[:upper:]')
            if [[ "$(get_available "$tool")" == "true" ]]; then
                echo "${upper}_HEALTHY=$(get_healthy "$tool")"
                err=$(get_probe_error "$tool")
                [[ -n "$err" ]] && echo "${upper}_PROBE_ERROR=$err"
            fi
        done
    fi
fi

exit 0
