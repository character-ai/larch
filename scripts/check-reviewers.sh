#!/usr/bin/env bash
# check-reviewers.sh — Check external reviewer binary availability and optional health probe.
#
# Checks if codex and cursor binaries are installed; Gemini is checked only
# when --include-gemini is passed. With --probe, also sends a
# trivial prompt ("Respond with OK") to each available tool with a 60-second
# timeout and validates that the normalized response is "ok" (all whitespace
# stripped, then lowercased — case-insensitive exact match). Catches auth
# failures, network issues, outages, and banner-style responses that produce
# non-empty but non-OK output.
# Failed probes are retried up to 2 additional times (3 total attempts) with a
# 10-second sleep between attempts to tolerate transient timeouts.
#
# Usage:
#   check-reviewers.sh [--probe] [--skip-codex-probe] [--skip-cursor-probe] [--include-gemini] [--skip-gemini-probe]
#
# Outputs (key=value to stdout):
#   CODEX_AVAILABLE=true|false    — binary exists on PATH
#   CURSOR_AVAILABLE=true|false   — binary exists on PATH
#   GEMINI_AVAILABLE=true|false   — binary exists on PATH (only with --include-gemini)
#   CODEX_HEALTHY=true|false      — (only with --probe) exit 0 and normalized output == "ok"
#   CURSOR_HEALTHY=true|false     — (only with --probe) exit 0 and normalized output == "ok"
#   GEMINI_HEALTHY=true|false     — (only with --probe and --include-gemini) exit 0 and normalized output == "ok"
#
# Exit codes:
#   0 — always (availability/health are informational, not errors)

# No -e: exit codes from probe subprocesses are informational, not errors.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROBE=false
SKIP_CODEX_PROBE=false
SKIP_CURSOR_PROBE=false
SKIP_GEMINI_PROBE=false
INCLUDE_GEMINI=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --probe)              PROBE=true; shift ;;
        --skip-codex-probe)   SKIP_CODEX_PROBE=true; shift ;;
        --skip-cursor-probe)  SKIP_CURSOR_PROBE=true; shift ;;
        --include-gemini)     INCLUDE_GEMINI=true; shift ;;
        --skip-gemini-probe)  SKIP_GEMINI_PROBE=true; shift ;;
        *) echo "check-reviewers.sh: unknown argument: $1" >&2; exit 1 ;;
    esac
done

CODEX_AVAILABLE="false"
CURSOR_AVAILABLE="false"
GEMINI_AVAILABLE="false"

if command -v codex >/dev/null 2>&1; then
    CODEX_AVAILABLE="true"
fi

if command -v cursor >/dev/null 2>&1; then
    CURSOR_AVAILABLE="true"
fi

if [[ "$INCLUDE_GEMINI" == "true" ]] && command -v gemini >/dev/null 2>&1; then
    GEMINI_AVAILABLE="true"
fi

echo "CODEX_AVAILABLE=$CODEX_AVAILABLE"
echo "CURSOR_AVAILABLE=$CURSOR_AVAILABLE"
if [[ "$INCLUDE_GEMINI" == "true" ]]; then
    echo "GEMINI_AVAILABLE=$GEMINI_AVAILABLE"
fi

if [[ "$PROBE" == "true" ]]; then
    CODEX_HEALTHY="false"
    CURSOR_HEALTHY="false"
    GEMINI_HEALTHY="false"
    CODEX_PROBE_ERROR=""
    CURSOR_PROBE_ERROR=""
    GEMINI_PROBE_ERROR=""

    PROBE_DIR=$(mktemp -d /tmp/larch-probe-XXXXXX)
    # Clean up probe tmpdir on exit
    trap 'rm -rf "$PROBE_DIR"' EXIT

    # Skipped probes are immediately settled as unhealthy with no error message
    # (consistent with the prior behavior — *_HEALTHY=false, no *_PROBE_ERROR).
    # The retry loop only ever launches probes for tools that are AVAILABLE and
    # not SKIPped and not yet HEALTHY.

    MAX_ATTEMPTS=3
    SLEEP_BETWEEN="${LARCH_CHECK_REVIEWERS_RETRY_SLEEP:-10}"

    for ((attempt=1; attempt<=MAX_ATTEMPTS; attempt++)); do
        # Decide which tools still need a probe this round.
        TRY_CODEX=false
        TRY_CURSOR=false
        TRY_GEMINI=false
        if [[ "$CODEX_AVAILABLE" == "true" && "$SKIP_CODEX_PROBE" == "false" && "$CODEX_HEALTHY" == "false" ]]; then
            TRY_CODEX=true
        fi
        if [[ "$CURSOR_AVAILABLE" == "true" && "$SKIP_CURSOR_PROBE" == "false" && "$CURSOR_HEALTHY" == "false" ]]; then
            TRY_CURSOR=true
        fi
        if [[ "$INCLUDE_GEMINI" == "true" && "$GEMINI_AVAILABLE" == "true" && "$SKIP_GEMINI_PROBE" == "false" && "$GEMINI_HEALTHY" == "false" ]]; then
            TRY_GEMINI=true
        fi

        # No tool needs probing — either both healthy already, or both skipped/unavailable.
        if [[ "$TRY_CODEX" == "false" && "$TRY_CURSOR" == "false" && "$TRY_GEMINI" == "false" ]]; then
            break
        fi

        # Inter-attempt sleep (only between attempts, not before the first or after the last).
        if [[ $attempt -gt 1 ]]; then
            echo "Retrying failed health probes (attempt $attempt of $MAX_ATTEMPTS, after ${SLEEP_BETWEEN}s sleep)..." >&2
            sleep "$SLEEP_BETWEEN"
        fi

        SENTINELS=()

        if [[ "$TRY_CODEX" == "true" ]]; then
            # Clear any state from a prior attempt for this tool.
            rm -f "$PROBE_DIR/codex-probe.txt" \
                  "$PROBE_DIR/codex-probe.txt.done" \
                  "$PROBE_DIR/codex-probe.txt.meta" \
                  "$PROBE_DIR/codex-probe.txt.diag"
            # Health probe tests basic Codex availability without forcing a model.
            # agent-model-args.sh defaults to gpt-5.5, which may not be available
            # on all accounts; the probe should verify Codex works, not that a
            # specific model is accessible. Operators set LARCH_CODEX_MODEL to
            # control the model used in actual work.
            "$SCRIPT_DIR/run-external-agent.sh" \
                --tool codex \
                --output "$PROBE_DIR/codex-probe.txt" \
                --timeout 60 \
                -- codex exec --full-auto -C "$PWD" \
                --output-last-message "$PROBE_DIR/codex-probe.txt" \
                "Respond with OK" \
                >"$PROBE_DIR/codex-wrapper-attempt${attempt}.log" 2>&1 &
            SENTINELS+=("$PROBE_DIR/codex-probe.txt.done")
        fi

        if [[ "$TRY_CURSOR" == "true" ]]; then
            rm -f "$PROBE_DIR/cursor-probe.txt" \
                  "$PROBE_DIR/cursor-probe.txt.done" \
                  "$PROBE_DIR/cursor-probe.txt.meta" \
                  "$PROBE_DIR/cursor-probe.txt.diag"
            CURSOR_MODEL_ARGS=$("$SCRIPT_DIR/agent-model-args.sh" --tool cursor)
            # Health probe: "Respond with OK" is passed verbatim — NOT wrapped via
            # scripts/cursor-wrap-prompt.sh. Probes exist to verify reachability and
            # auth within a 60s budget; engaging max-mode here would add latency and
            # cost without diagnostic value.
            # shellcheck disable=SC2086
            "$SCRIPT_DIR/run-external-agent.sh" \
                --tool cursor \
                --output "$PROBE_DIR/cursor-probe.txt" \
                --timeout 60 \
                --capture-stdout \
                -- cursor agent -p --force --trust $CURSOR_MODEL_ARGS --workspace "$PWD" \
                "Respond with OK" \
                >"$PROBE_DIR/cursor-wrapper-attempt${attempt}.log" 2>&1 &
            SENTINELS+=("$PROBE_DIR/cursor-probe.txt.done")
        fi

        if [[ "$TRY_GEMINI" == "true" ]]; then
            rm -f "$PROBE_DIR/gemini-probe.txt" \
                  "$PROBE_DIR/gemini-probe.txt.done" \
                  "$PROBE_DIR/gemini-probe.txt.meta" \
                  "$PROBE_DIR/gemini-probe.txt.diag"
            GEMINI_MODEL_ARGS=$("$SCRIPT_DIR/agent-model-args.sh" --tool gemini)
            # shellcheck disable=SC2086
            "$SCRIPT_DIR/run-external-agent.sh" \
                --tool gemini \
                --output "$PROBE_DIR/gemini-probe.txt" \
                --timeout 60 \
                --capture-stdout \
                -- gemini --prompt "Respond with OK" --output-format text $GEMINI_MODEL_ARGS \
                >"$PROBE_DIR/gemini-wrapper-attempt${attempt}.log" 2>&1 &
            SENTINELS+=("$PROBE_DIR/gemini-probe.txt.done")
        fi

        if [[ ${#SENTINELS[@]} -gt 0 ]]; then
            # Wait for probes (120s = 60s timeout + 60s grace)
            "$SCRIPT_DIR/wait-for-reviewers.sh" --timeout 120 "${SENTINELS[@]}" \
                >"$PROBE_DIR/wait-attempt${attempt}.log" 2>&1 || true
        fi

        # Evaluate this round's results.
        if [[ "$TRY_CODEX" == "true" ]]; then
            if [[ -f "$PROBE_DIR/codex-probe.txt.done" ]]; then
                CODEX_EXIT=$(cat "$PROBE_DIR/codex-probe.txt.done")
                if [[ "$CODEX_EXIT" == "0" && -s "$PROBE_DIR/codex-probe.txt" ]]; then
                    CODEX_PROBE_REPLY=$(tr -d '[:space:]' < "$PROBE_DIR/codex-probe.txt" | tr '[:upper:]' '[:lower:]')
                    if [[ "$CODEX_PROBE_REPLY" == "ok" ]]; then
                        CODEX_HEALTHY="true"
                        CODEX_PROBE_ERROR=""
                    else
                        CODEX_PROBE_ERROR="Probe attempt $attempt returned non-OK response: $(head -c 200 "$PROBE_DIR/codex-probe.txt" | tr '\n\r' '  ')"
                    fi
                elif [[ -f "$PROBE_DIR/codex-probe.txt.diag" ]]; then
                    CODEX_PROBE_ERROR="Probe attempt $attempt: $(cat "$PROBE_DIR/codex-probe.txt.diag")"
                elif [[ "$CODEX_EXIT" == "0" ]]; then
                    CODEX_PROBE_ERROR="Probe attempt $attempt exited successfully but produced no output"
                else
                    CODEX_PROBE_ERROR="Probe attempt $attempt failed with exit code $CODEX_EXIT"
                fi
            else
                CODEX_PROBE_ERROR="Probe attempt $attempt did not complete (sentinel file missing — possible crash or system kill)"
            fi
        fi

        if [[ "$TRY_CURSOR" == "true" ]]; then
            if [[ -f "$PROBE_DIR/cursor-probe.txt.done" ]]; then
                CURSOR_EXIT=$(cat "$PROBE_DIR/cursor-probe.txt.done")
                if [[ "$CURSOR_EXIT" == "0" && -s "$PROBE_DIR/cursor-probe.txt" ]]; then
                    CURSOR_PROBE_REPLY=$(tr -d '[:space:]' < "$PROBE_DIR/cursor-probe.txt" | tr '[:upper:]' '[:lower:]')
                    if [[ "$CURSOR_PROBE_REPLY" == "ok" ]]; then
                        CURSOR_HEALTHY="true"
                        CURSOR_PROBE_ERROR=""
                    else
                        CURSOR_PROBE_ERROR="Probe attempt $attempt returned non-OK response: $(head -c 200 "$PROBE_DIR/cursor-probe.txt" | tr '\n\r' '  ')"
                    fi
                elif [[ -f "$PROBE_DIR/cursor-probe.txt.diag" ]]; then
                    CURSOR_PROBE_ERROR="Probe attempt $attempt: $(cat "$PROBE_DIR/cursor-probe.txt.diag")"
                elif [[ "$CURSOR_EXIT" == "0" ]]; then
                    CURSOR_PROBE_ERROR="Probe attempt $attempt exited successfully but produced no output"
                else
                    CURSOR_PROBE_ERROR="Probe attempt $attempt failed with exit code $CURSOR_EXIT"
                fi
            else
                CURSOR_PROBE_ERROR="Probe attempt $attempt did not complete (sentinel file missing — possible crash or system kill)"
            fi
        fi

        if [[ "$TRY_GEMINI" == "true" ]]; then
            if [[ -f "$PROBE_DIR/gemini-probe.txt.done" ]]; then
                GEMINI_EXIT=$(cat "$PROBE_DIR/gemini-probe.txt.done")
                if [[ "$GEMINI_EXIT" == "0" && -s "$PROBE_DIR/gemini-probe.txt" ]]; then
                    GEMINI_PROBE_REPLY=$(tr -d '[:space:]' < "$PROBE_DIR/gemini-probe.txt" | tr '[:upper:]' '[:lower:]')
                    if [[ "$GEMINI_PROBE_REPLY" == "ok" ]]; then
                        GEMINI_HEALTHY="true"
                        GEMINI_PROBE_ERROR=""
                    else
                        GEMINI_PROBE_ERROR="Probe attempt $attempt returned non-OK response: $(head -c 200 "$PROBE_DIR/gemini-probe.txt" | tr '\n\r' '  ')"
                    fi
                elif [[ -f "$PROBE_DIR/gemini-probe.txt.diag" ]]; then
                    GEMINI_PROBE_ERROR="Probe attempt $attempt: $(cat "$PROBE_DIR/gemini-probe.txt.diag")"
                elif [[ "$GEMINI_EXIT" == "0" ]]; then
                    GEMINI_PROBE_ERROR="Probe attempt $attempt exited successfully but produced no output"
                else
                    GEMINI_PROBE_ERROR="Probe attempt $attempt failed with exit code $GEMINI_EXIT"
                fi
            else
                GEMINI_PROBE_ERROR="Probe attempt $attempt did not complete (sentinel file missing — possible crash or system kill)"
            fi
        fi

        # Early exit if everything we wanted is now healthy.
        STILL_NEEDED=false
        if [[ "$CODEX_AVAILABLE" == "true" && "$SKIP_CODEX_PROBE" == "false" && "$CODEX_HEALTHY" == "false" ]]; then
            STILL_NEEDED=true
        fi
        if [[ "$CURSOR_AVAILABLE" == "true" && "$SKIP_CURSOR_PROBE" == "false" && "$CURSOR_HEALTHY" == "false" ]]; then
            STILL_NEEDED=true
        fi
        if [[ "$INCLUDE_GEMINI" == "true" && "$GEMINI_AVAILABLE" == "true" && "$SKIP_GEMINI_PROBE" == "false" && "$GEMINI_HEALTHY" == "false" ]]; then
            STILL_NEEDED=true
        fi
        if [[ "$STILL_NEEDED" == "false" ]]; then
            break
        fi
    done

    # Only emit health keys for tools that are installed — absent binaries
    # are already handled by *_AVAILABLE=false and should not propagate a
    # misleading *_HEALTHY=false into session-env.
    if [[ "$CODEX_AVAILABLE" == "true" ]]; then
        echo "CODEX_HEALTHY=$CODEX_HEALTHY"
        if [[ -n "$CODEX_PROBE_ERROR" ]]; then
            echo "CODEX_PROBE_ERROR=$CODEX_PROBE_ERROR"
        fi
    fi
    if [[ "$CURSOR_AVAILABLE" == "true" ]]; then
        echo "CURSOR_HEALTHY=$CURSOR_HEALTHY"
        if [[ -n "$CURSOR_PROBE_ERROR" ]]; then
            echo "CURSOR_PROBE_ERROR=$CURSOR_PROBE_ERROR"
        fi
    fi
    if [[ "$INCLUDE_GEMINI" == "true" && "$GEMINI_AVAILABLE" == "true" ]]; then
        echo "GEMINI_HEALTHY=$GEMINI_HEALTHY"
        if [[ -n "$GEMINI_PROBE_ERROR" ]]; then
            echo "GEMINI_PROBE_ERROR=$GEMINI_PROBE_ERROR"
        fi
    fi

fi
