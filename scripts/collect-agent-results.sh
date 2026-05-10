#!/usr/bin/env bash
# collect-agent-results.sh — Collect, validate, and optionally retry external reviewer outputs.
#
# Consolidates the post-launch validation+retry pattern used across all skills.
# Wraps wait-for-reviewers.sh, validates each output, retries once on empty via
# .meta files written by run-external-agent.sh, and emits structured results.
#
# Runtime prerequisites: bash >= 3.2 (the retry block is portable to macOS
# /bin/bash 3.2). The empty-output retry path additionally requires `jq` (to
# validate and deserialize CMD_JSON) and `base64 -d` (GNU/BSD/BusyBox-portable
# for argv element decode). Empty-output retries fail closed if either is
# missing — see SECURITY.md "Retry-metadata deserialization" and the
# "Empty-output retry deserializer" section in scripts/collect-agent-results.md.
#
# Usage:
#   collect-agent-results.sh --timeout <seconds> [--write-health <path>] \
#     [--substantive-validation] <output-file> [<output-file> ...]
#
# Options:
#   --timeout <seconds>            Timeout for wait-for-reviewers.sh (e.g., 1860)
#   --write-health <path>          Write updated CODEX_HEALTHY/CURSOR_HEALTHY/GEMINI_HEALTHY to file.
#                                  Health is monotonic per tool: any failure sets the tool
#                                  permanently unhealthy. A later successful instance does
#                                  NOT flip it back to healthy.
#                                  If the file already exists, prior health state is read
#                                  and merged monotonically (prior false is preserved).
#   --substantive-validation       After the existing non-empty + retry path settles,
#                                  invoke scripts/validate-research-output.sh on each
#                                  STATUS=OK entry. On validator failure, rewrite the
#                                  entry as STATUS=NOT_SUBSTANTIVE | HEALTHY=false |
#                                  FAILURE_REASON=<sanitized validator diagnostic>
#                                  and call set_tool_unhealthy to preserve health
#                                  monotonicity. Default OFF — opt-in per caller.
#                                  Currently opted in by: /research research phase
#                                  (Standard / Deep), /research validation phase,
#                                  /review Step 3a, /implement Step 5 quick-mode
#                                  review, /design Step 3 plan-review.
#                                  Closes #416 (Phase 3 of umbrella #413), #661.
#   --validation-mode              Modifier for --substantive-validation: forwards
#                                  --validation-mode to validate-research-output.sh
#                                  so its preset (NO_ISSUES_FOUND short-circuit + 30-
#                                  word floor) applies. Use for short reviewer-style
#                                  outputs whose contract is "numbered findings ...
#                                  If NO issues, output exactly NO_ISSUES_FOUND" —
#                                  /research validation phase, /review, /implement
#                                  Step 5 quick-mode, /design plan-review. The
#                                  /research research phase deliberately omits this
#                                  modifier because its outputs are 2-3-paragraph
#                                  prose, not short findings. No effect when
#                                  --substantive-validation is not also passed.
#                                  See docs/external-reviewers.md Output Validation
#                                  for the per-skill opt-in matrix.
#
# Arguments:
#   One or more output file paths (from run-external-agent.sh invocations).
#   Sentinel paths are derived by appending .done to each output file.
#   Metadata paths are derived by appending .meta to each output file.
#
# Output (KEY=value blocks on stdout, one block per reviewer, separated by blank lines):
#   REVIEWER_FILE=<output-path>
#   TOOL=<registered external tool|unknown>
#   STATUS=<OK|TIMED_OUT|FAILED|EMPTY_OUTPUT|SENTINEL_TIMEOUT|NOT_SUBSTANTIVE|cap_hit>
#   EXIT_CODE=<N>
#   HEALTHY=<true|false>
#   FAILURE_REASON=<explanation>  (non-empty when STATUS != OK; explains the cause of failure)
#
# Exit codes:
#   0 — normal completion (results are informational, not errors)
#   1 — argument error (missing required option or unknown flag) or non-zero
#       exit propagated from wait-for-reviewers.sh.

# No -e: exit codes from reviewer subprocesses and retries are informational.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=scripts/external-tool-registry.sh
source "$SCRIPT_DIR/external-tool-registry.sh" || { echo "collect-agent-results.sh: failed to source external-tool-registry.sh" >&2; exit 1; }
[[ "${LARCH_EXTERNAL_TOOL_REGISTRY_LOADED:-}" == "1" ]] || { echo "collect-agent-results.sh: external-tool-registry.sh sourced but sentinel missing" >&2; exit 1; }

normalize_exit_code_or_99() {
    local raw="$1"
    local context="$2"
    if [[ "$raw" =~ ^[0-9]{1,3}$ ]] && (( 10#$raw <= 255 )); then
        printf '%s' "$raw"
        return 0
    fi
    printf 'collect-agent-results.sh: invalid exit code from %s; forcing EXIT_CODE=99\n' "$context" >&2
    printf '99'
}

# Companion to normalize_exit_code_or_99: returns "true" if the raw input
# would be coerced to 99 (i.e., fails the regex/range gate), "false" otherwise.
# Caller-side mirror of the helper's gate so coercion state can be detected
# WITHOUT relying on subshell variables — normalize_exit_code_or_99 runs inside
# a $(...) subshell so any global it sets cannot propagate back to the parent.
exit_code_was_coerced() {
    local raw="$1"
    if [[ "$raw" =~ ^[0-9]{1,3}$ ]] && (( 10#$raw <= 255 )); then
        printf 'false'
        return 0
    fi
    printf 'true'
}

build_missing_retry_sentinel_result() {
    local orig_output="$1"
    local tool="$2"
    printf 'REVIEWER_FILE=%s|TOOL=%s|STATUS=EMPTY_OUTPUT|EXIT_CODE=99|HEALTHY=false|FAILURE_REASON=Retry process did not complete (sentinel file missing)' \
        "$orig_output" "$tool"
}

if [[ "${BASH_SOURCE[0]}" != "$0" && "${1:-}" == "--source-only" ]]; then
    return 0
fi

TIMEOUT=""
WRITE_HEALTH=""
SUBSTANTIVE_VALIDATION="false"
VALIDATION_MODE="false"
OUTPUT_FILES=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --timeout)
            TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --write-health)
            WRITE_HEALTH="${2:?--write-health requires a path}"; shift 2 ;;
        --substantive-validation)
            SUBSTANTIVE_VALIDATION="true"; shift ;;
        --validation-mode)
            VALIDATION_MODE="true"; shift ;;
        --help)
            echo "Usage: collect-agent-results.sh --timeout <seconds> [--write-health <path>] [--substantive-validation [--validation-mode]] <output-file>..." >&2
            exit 0 ;;
        -*)
            echo "collect-agent-results.sh: unknown option: $1" >&2; exit 1 ;;
        *)
            OUTPUT_FILES+=("$1"); shift ;;
    esac
done

if [[ -z "$TIMEOUT" ]]; then
    echo "collect-agent-results.sh: --timeout is required" >&2
    exit 1
fi

if [[ ${#OUTPUT_FILES[@]} -eq 0 ]]; then
    echo "collect-agent-results.sh: at least one output file is required" >&2
    exit 1
fi

# --- Derive tool name from output filename ---
derive_tool() {
    local meta="${1}.meta"
    local meta_tool=""
    local meta_line=""
    local meta_key=""
    local meta_val=""
    local t
    if [[ -f "$meta" ]]; then
        while IFS= read -r meta_line || [[ -n "$meta_line" ]]; do
            meta_key="${meta_line%%=*}"
            meta_val="${meta_line#*=}"
            [[ "$meta_key" == "TOOL" ]] && meta_tool="$meta_val"
        done < "$meta"
        if [[ -n "$meta_tool" ]] && larch_is_external_tool "$meta_tool"; then
            echo "$meta_tool"
            return
        fi
    fi

    local base
    base=$(basename "$1")
    for t in "${LARCH_EXTERNAL_TOOLS[@]}"; do
        if [[ "$base" == *"$t"* ]]; then
            echo "$t"
            return
        fi
    done

    echo "unknown"
}

# --- Health state tracking (portable, no associative arrays) ---
# Monotonic: once false, stays false for the session.
CODEX_TOOL_HEALTHY="true"
CURSOR_TOOL_HEALTHY="true"
GEMINI_TOOL_HEALTHY="true"

# Read prior health state from existing --write-health file (if it exists).
# This preserves monotonicity across separate collect-agent-results.sh calls.
if [[ -n "$WRITE_HEALTH" && -f "$WRITE_HEALTH" ]]; then
    while IFS='=' read -r key value || [[ -n "$key" ]]; do
        case "$key" in
            CODEX_HEALTHY)  [[ "$value" == "false" ]] && CODEX_TOOL_HEALTHY="false" ;;
            CURSOR_HEALTHY) [[ "$value" == "false" ]] && CURSOR_TOOL_HEALTHY="false" ;;
            GEMINI_HEALTHY) [[ "$value" == "false" ]] && GEMINI_TOOL_HEALTHY="false" ;;
        esac
    done < "$WRITE_HEALTH"
fi

get_tool_healthy() {
    case "$1" in
        codex)  echo "$CODEX_TOOL_HEALTHY" ;;
        cursor) echo "$CURSOR_TOOL_HEALTHY" ;;
        gemini) echo "$GEMINI_TOOL_HEALTHY" ;;
        *)      echo "true" ;;
    esac
}

set_tool_unhealthy() {
    case "$1" in
        codex)  CODEX_TOOL_HEALTHY="false" ;;
        cursor) CURSOR_TOOL_HEALTHY="false" ;;
        gemini) GEMINI_TOOL_HEALTHY="false" ;;
    esac
}

# --- 1. Build sentinel paths and wait ---
SENTINELS=()
for f in "${OUTPUT_FILES[@]}"; do
    SENTINELS+=("${f}.done")
done

# Issue #1188: do not silently swallow wait-for-reviewers.sh's non-zero exit
# (usage errors like a bad --timeout, or fatals like its mktemp failure).
# Stderr goes to a temp file so the success path stays free of poll progress.
# The EXIT trap covers signal-driven exits (e.g., SIGTERM mid-wait) so the
# tempfile is not leaked under ${TMPDIR:-/tmp}; it also subsumes the success
# and failure-branch cleanup.
WAIT_STDERR=$(mktemp "${TMPDIR:-/tmp}/collect-wait-stderr.XXXXXX") || {
    echo "collect-agent-results.sh: mktemp failed" >&2
    exit 1
}
trap 'rm -f -- "$WAIT_STDERR"' EXIT
WAIT_OUTPUT=$("$SCRIPT_DIR/wait-for-reviewers.sh" --timeout "$TIMEOUT" "${SENTINELS[@]}" 2>"$WAIT_STDERR")
WAIT_RC=$?
if [[ "$WAIT_RC" -ne 0 ]]; then
    cat "$WAIT_STDERR" >&2
    printf 'collect-agent-results.sh: wait-for-reviewers.sh exited %s\n' "$WAIT_RC" >&2
    exit 1
fi

# Parse wait output for TIMEOUT indicators (newline-separated indices).
TIMED_OUT_INDEXES=""
while IFS= read -r line; do
    if [[ "$line" == TIMEOUT\ * ]]; then
        # Grammar: "TIMEOUT <idx> <basename>" — extract <idx>.
        rest="${line#TIMEOUT }"
        local_idx="${rest%% *}"
        case "$local_idx" in
            ''|*[!0-9]*) continue ;;
        esac
        TIMED_OUT_INDEXES="${TIMED_OUT_INDEXES}${local_idx}"$'\n'
    fi
done <<< "$WAIT_OUTPUT"

# Check if a wait argv index is in the timed-out list.
is_index_timed_out() {
    local needle="$1"
    echo "$TIMED_OUT_INDEXES" | grep -qxF "$needle"
}

# --- Helper: sanitize a failure-reason string for embedding in pipe-delimited
# RESULTS records. RESULTS entries use `|` as field delimiter and are later
# emitted as KEY=value lines via `tr '|' '\n'`. Multi-line .diag content
# (notably from Gemini's stderr-on-failure path) would inject phantom lines
# after `FAILURE_REASON=...` and corrupt downstream parsers. Replace pipes,
# newlines, and CRs with single spaces; collapse whitespace runs; truncate
# at 500 chars to bound size. ---
sanitize_failure_reason() {
    local s="$1"
    # tr handles bytes; awk collapses whitespace runs
    printf '%s' "$s" | tr '|\n\r' '   ' | awk '{
        gsub(/[[:space:]]+/, " ");
        sub(/^ /, "");
        sub(/ $/, "");
        if (length($0) > 500) {
            print substr($0, 1, 497) "...";
        } else {
            print;
        }
    }'
}

# --- Helper: build failure reason from .diag file or status ---
build_failure_reason() {
    local output_file="$1"
    local status="$2"
    local exit_code="$3"
    local diag_file="${output_file}.diag"
    local raw

    if [[ -f "$diag_file" ]]; then
        raw=$(cat "$diag_file")
    else
        # Fallback: construct reason from status and exit code
        case "$status" in
            SENTINEL_TIMEOUT) raw="Process did not complete (sentinel file missing — possible crash or system kill)" ;;
            TIMED_OUT)        raw="Process timed out (exit code 124)" ;;
            FAILED)           raw="Process failed with exit code $exit_code" ;;
            EMPTY_OUTPUT)     raw="Process exited successfully but produced no output" ;;
            *)                raw="Unknown failure (status=$status, exit_code=$exit_code)" ;;
        esac
    fi
    sanitize_failure_reason "$raw"
}

mark_retry_metadata_invalid() {
    local idx="$1"
    local orig_output="$2"
    local reason="$3"
    local tool
    tool=$(derive_tool "$orig_output")
    RESULTS[idx]="REVIEWER_FILE=$orig_output|TOOL=$tool|STATUS=EMPTY_OUTPUT|EXIT_CODE=99|HEALTHY=false|FAILURE_REASON=$reason"
    set_tool_unhealthy "$tool"
}

cmd_has_token() {
    local needle="$1"
    shift
    local arg
    for arg in "$@"; do
        [[ "$arg" == "$needle" ]] && return 0
    done
    return 1
}

cmd_lacks_forbidden_token() {
    local forbidden="$1"
    shift
    if cmd_has_token "$forbidden" "$@"; then
        return 1
    fi
    return 0
}

cmd_json_shape_valid_for_tool() {
    local tool="$1"
    shift
    local argv0_base
    [[ $# -ge 1 ]] || return 1
    argv0_base=$(basename "$1")
    case "$tool" in
        cursor)
            [[ $# -ge 2 ]] || return 1
            [[ "$argv0_base" == "cursor" ]] || return 1
            [[ "$2" == "agent" ]] || return 1
            cmd_has_token "--workspace" "$@" || return 1
            cmd_lacks_forbidden_token "--add-dir" "$@" || return 1
            ;;
        codex)
            [[ $# -ge 2 ]] || return 1
            [[ "$argv0_base" == "codex" ]] || return 1
            [[ "$2" == "exec" ]] || return 1
            cmd_has_token "-C" "$@" || return 1
            cmd_has_token "--add-dir" "$@" || return 1
            cmd_has_token "--output-last-message" "$@" || return 1
            ;;
        gemini)
            case "$argv0_base" in
                launch-gemini-review.sh|launch-gemini-implement.sh|gemini) ;;
                *) return 1 ;;
            esac
            cmd_lacks_forbidden_token "--add-dir" "$@" || return 1
            cmd_lacks_forbidden_token "-C" "$@" || return 1
            cmd_lacks_forbidden_token "--output-last-message" "$@" || return 1
            cmd_lacks_forbidden_token "--workspace" "$@" || return 1
            ;;
        *)
            return 2
            ;;
    esac
    return 0
}

# --- 2. Validate each output and collect results ---
RETRY_FILES=()
RETRY_INDICES=()
RETRY_TIMEOUTS=()

RESULTS=()
for i in "${!OUTPUT_FILES[@]}"; do
    OUTPUT="${OUTPUT_FILES[$i]}"
    SENTINEL="${OUTPUT}.done"
    META="${OUTPUT}.meta"
    TOOL=$(derive_tool "$OUTPUT")
    STATUS="OK"
    EXIT_CODE="0"
    HEALTHY="true"
    FAILURE_REASON=""

    # wait emits indexed records keyed by argv order. OUTPUT_FILES[$i]
    # (0-based) corresponds to wait's idx (1-based) = i+1.
    if is_index_timed_out "$((i + 1))"; then
        # wait-for-reviewers.sh reported TIMEOUT (sentinel never appeared)
        STATUS="SENTINEL_TIMEOUT"
        EXIT_CODE="124"
        HEALTHY="false"
        FAILURE_REASON=$(build_failure_reason "$OUTPUT" "$STATUS" "$EXIT_CODE")
    elif [[ -f "$SENTINEL" ]]; then
        EXIT_CODE_RAW=$(cat "$SENTINEL" 2>/dev/null || echo "99")
        EXIT_CODE=$(normalize_exit_code_or_99 "$EXIT_CODE_RAW" "initial sentinel")
        EXIT_CODE_COERCED=$(exit_code_was_coerced "$EXIT_CODE_RAW")
        # When normalize_exit_code_or_99 coerced an invalid sentinel to 99 and
        # the output file is empty, route to the retry path rather than an
        # immediate STATUS=FAILED — a corrupt or partially-written .done should
        # not deny the one-shot empty-output recovery when a valid .meta exists.
        # Real (non-coerced) non-zero exits with empty output still route to FAILED.
        if [[ "$EXIT_CODE_COERCED" == "true" && ! -s "$OUTPUT" ]]; then
            EXIT_CODE="0"
        fi
        if [[ "$EXIT_CODE" == "124" ]]; then
            STATUS="TIMED_OUT"
            HEALTHY="false"
            FAILURE_REASON=$(build_failure_reason "$OUTPUT" "$STATUS" "$EXIT_CODE")
        elif [[ "$EXIT_CODE" != "0" ]]; then
            STATUS="FAILED"
            HEALTHY="false"
            FAILURE_REASON=$(build_failure_reason "$OUTPUT" "$STATUS" "$EXIT_CODE")
        elif [[ -s "$OUTPUT" ]] && [[ "$(head -1 "$OUTPUT" 2>/dev/null)" == "STATUS=cap_hit" ]]; then
            # Budget-cap sentinel written by review launchers: reviewer deliberately
            # skipped; not a tool failure, so HEALTHY stays true and the output is
            # not forwarded to substantive validation or reviewer synthesis.
            STATUS="cap_hit"
            FAILURE_REASON="Token budget cap hit; reviewer skipped"
        elif [[ ! -s "$OUTPUT" ]]; then
            # F4 fix: empty output is a retry candidate, NOT an immediate health failure.
            # Health is only set to false after retry also fails (see section 3 below).
            STATUS="EMPTY_OUTPUT"
            HEALTHY="true"  # tentative — will be set false if retry fails
            FAILURE_REASON=$(build_failure_reason "$OUTPUT" "$STATUS" "$EXIT_CODE")
            # Queue for retry if .meta exists
            if [[ -f "$META" ]]; then
                # .meta is one KEY=VALUE record per line. This parser relies on
                # run-external-agent.sh's writer-side field contract to keep
                # values line-oriented; only META_TIMEOUT is needed here.
                ORIG_TIMEOUT=""
                while IFS= read -r meta_line || [[ -n "$meta_line" ]]; do
                    meta_key="${meta_line%%=*}"
                    meta_val="${meta_line#*=}"
                    [[ "$meta_key" == "TIMEOUT" ]] && ORIG_TIMEOUT="$meta_val"
                done < "$META"
                _orig_invalid_reason=""
                if [[ -z "$ORIG_TIMEOUT" ]]; then
                    _orig_invalid_reason="Retry metadata invalid: TIMEOUT missing"
                else
                    case "$ORIG_TIMEOUT" in
                        ''|*[!0-9]*) _orig_invalid_reason="Retry metadata invalid: TIMEOUT not a positive integer" ;;
                        *) if (( 10#$ORIG_TIMEOUT < 1 )); then
                               _orig_invalid_reason="Retry metadata invalid: TIMEOUT not a positive integer"
                           fi ;;
                    esac
                fi
                if [[ -n "$_orig_invalid_reason" ]]; then
                    mark_retry_metadata_invalid "$i" "$OUTPUT" "$_orig_invalid_reason"
                    continue
                fi
                ORIG_TIMEOUT=$((10#$ORIG_TIMEOUT))
                RETRY_FILES+=("$OUTPUT")
                RETRY_INDICES+=("$i")
                RETRY_TIMEOUTS+=("$ORIG_TIMEOUT")
            else
                HEALTHY="false"  # no .meta → can't retry → mark unhealthy
            fi
        fi
    else
        # Sentinel doesn't exist (shouldn't happen after wait, but be defensive)
        STATUS="SENTINEL_TIMEOUT"
        EXIT_CODE="124"
        HEALTHY="false"
        FAILURE_REASON=$(build_failure_reason "$OUTPUT" "$STATUS" "$EXIT_CODE")
    fi

    # Monotonic health: if this tool was already marked unhealthy, keep it
    if [[ "$(get_tool_healthy "$TOOL")" == "false" ]]; then
        HEALTHY="false"
    fi
    if [[ "$HEALTHY" == "false" ]]; then
        set_tool_unhealthy "$TOOL"
    fi

    RESULTS+=("REVIEWER_FILE=$OUTPUT|TOOL=$TOOL|STATUS=$STATUS|EXIT_CODE=$EXIT_CODE|HEALTHY=$HEALTHY|FAILURE_REASON=$FAILURE_REASON")
done

# --- 3. Retry empty outputs using .meta files ---
if [[ ${#RETRY_FILES[@]} -gt 0 ]]; then
    RETRY_SENTINELS=()
    # Tracks which RETRY_FILES indices actually launched a retry child. The
    # second loop (retry-result update) iterates over every j in RETRY_FILES,
    # so without this array, indices that fail-closed via
    # mark_retry_metadata_invalid (and never spawn a child) would have their
    # specific FAILURE_REASON overwritten by the generic
    # "Retry process did not complete (sentinel file missing)" message at
    # the foot of the second loop.
    RETRY_LAUNCHED=()
    # F10/#1330: compute max retry timeout from original reviewer timeouts + grace.
    MAX_RETRY_TIMEOUT=30  # safety floor; loop below raises this to max(ORIG_TIMEOUT+60)
    for j in "${!RETRY_FILES[@]}"; do
        ORIG_OUTPUT="${RETRY_FILES[$j]}"
        META="${ORIG_OUTPUT}.meta"
        RETRY_OUTPUT="${ORIG_OUTPUT%.txt}-retry.txt"
        ORIG_TIMEOUT="${RETRY_TIMEOUTS[$j]}"
        # ORIG_TIMEOUT was validated and 10#-normalized in the queueing block above.
        RETRY_WAIT=$(( ORIG_TIMEOUT + 60 ))
        if [[ $RETRY_WAIT -gt $MAX_RETRY_TIMEOUT ]]; then
            MAX_RETRY_TIMEOUT=$RETRY_WAIT
        fi

        # Parse .meta file (full parse for retry command reconstruction). The
        # line-oriented grammar and field safety guarantees are owned by
        # run-external-agent.sh's .meta writer contract.
        META_TOOL=""
        META_TIMEOUT=""
        META_CAPTURE=""
        META_CAPTURE_STDOUT_ONLY=""
        META_CMD_JSON=""
        META_ORIG_OUTPUT=""
        META_OUTER_LAUNCHER=""
        META_OUTER_LAUNCHER_PROMPT_FILE=""
        META_OUTER_LAUNCHER_WORKDIR=""
        META_OUTER_LAUNCHER_RISK=""
        while IFS= read -r meta_line || [[ -n "$meta_line" ]]; do
            meta_key="${meta_line%%=*}"
            meta_val="${meta_line#*=}"
            case "$meta_key" in
                TOOL)           META_TOOL="$meta_val" ;;
                TIMEOUT)        META_TIMEOUT="$meta_val" ;;
                CAPTURE_STDOUT) META_CAPTURE="$meta_val" ;;
                CAPTURE_STDOUT_ONLY) META_CAPTURE_STDOUT_ONLY="$meta_val" ;;
                OUTPUT_FILE)    META_ORIG_OUTPUT="$meta_val" ;;
                CMD_JSON)       META_CMD_JSON="$meta_val" ;;
                OUTER_LAUNCHER) META_OUTER_LAUNCHER="$meta_val" ;;
                OUTER_LAUNCHER_PROMPT_FILE) META_OUTER_LAUNCHER_PROMPT_FILE="$meta_val" ;;
                OUTER_LAUNCHER_WORKDIR) META_OUTER_LAUNCHER_WORKDIR="$meta_val" ;;
                OUTER_LAUNCHER_RISK) META_OUTER_LAUNCHER_RISK="$meta_val" ;;
            esac
        done < "$META"

        _meta_invalid_reason=""
        if [[ -z "$META_TIMEOUT" ]]; then
            _meta_invalid_reason="Retry metadata invalid: TIMEOUT missing"
        else
            case "$META_TIMEOUT" in
                ''|*[!0-9]*) _meta_invalid_reason="Retry metadata invalid: TIMEOUT not a positive integer" ;;
                *) if (( 10#$META_TIMEOUT < 1 )); then
                       _meta_invalid_reason="Retry metadata invalid: TIMEOUT not a positive integer"
                   fi ;;
            esac
        fi
        if [[ -n "$_meta_invalid_reason" ]]; then
            IDX="${RETRY_INDICES[$j]}"
            mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "$_meta_invalid_reason"
            continue
        fi
        META_TIMEOUT=$((10#$META_TIMEOUT))

        if [[ -n "$META_OUTER_LAUNCHER" || -n "$META_OUTER_LAUNCHER_PROMPT_FILE" || -n "$META_OUTER_LAUNCHER_WORKDIR" ]]; then
            IDX="${RETRY_INDICES[$j]}"
            if [[ -z "$META_OUTER_LAUNCHER" ]]; then
                mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: missing OUTER_LAUNCHER"
                continue
            fi
            if [[ -z "$META_OUTER_LAUNCHER_PROMPT_FILE" ]]; then
                mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: missing OUTER_LAUNCHER_PROMPT_FILE"
                continue
            fi
            if [[ -z "$META_OUTER_LAUNCHER_WORKDIR" ]]; then
                mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: missing OUTER_LAUNCHER_WORKDIR"
                continue
            fi
            case "$META_OUTER_LAUNCHER" in
                *..*) mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: OUTER_LAUNCHER contains .."; continue ;;
            esac
            _launcher_base=$(basename "$META_OUTER_LAUNCHER")
            case "$META_TOOL:$_launcher_base" in
                cursor:launch-cursor-review.sh) _expected_launcher="$SCRIPT_DIR/launch-cursor-review.sh" ;;
                codex:launch-codex-review.sh) _expected_launcher="$SCRIPT_DIR/launch-codex-review.sh" ;;
                cursor:*) _expected_launcher="$SCRIPT_DIR/launch-cursor-review.sh" ;;
                codex:*) _expected_launcher="$SCRIPT_DIR/launch-codex-review.sh" ;;
                *) mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: OUTER_LAUNCHER not canonical launch-cursor-review.sh or launch-codex-review.sh"; continue ;;
            esac
            if ! _expected_launcher_dir=$(cd "$(dirname "$_expected_launcher")" 2>/dev/null && pwd -P 2>/dev/null); then
                mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: OUTER_LAUNCHER not canonical $(basename "$_expected_launcher")"
                continue
            fi
            if ! _candidate_launcher_dir=$(cd "$(dirname "$META_OUTER_LAUNCHER")" 2>/dev/null && pwd -P 2>/dev/null); then
                mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: OUTER_LAUNCHER not canonical $(basename "$_expected_launcher")"
                continue
            fi
            _expected_launcher_canonical="$_expected_launcher_dir/$(basename "$_expected_launcher")"
            _candidate_canonical="$_candidate_launcher_dir/$(basename "$META_OUTER_LAUNCHER")"
            if [[ "$_candidate_canonical" != "$_expected_launcher_canonical" ]]; then
                mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: OUTER_LAUNCHER not canonical $(basename "$_expected_launcher")"
                continue
            fi
            if [[ ! -f "$META_OUTER_LAUNCHER" || -L "$META_OUTER_LAUNCHER" || ! -x "$META_OUTER_LAUNCHER" ]]; then
                # Reject symlinked launchers (R2_FINDING_2 of /review). Mirrors
                # the OUTER_LAUNCHER_PROMPT_FILE non-symlink rule below for
                # uniform defense-in-depth: even though the canonicalization
                # above resolves directory symlinks via `pwd -P`, a leaf
                # symlink at the canonical path could be swapped between the
                # canonical comparison and the exec.
                mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: OUTER_LAUNCHER not a regular non-symlink executable file"
                continue
            fi
            _expected_prompt="${ORIG_OUTPUT}.prompt"
            case "$META_OUTER_LAUNCHER_PROMPT_FILE" in
                *..*) mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: OUTER_LAUNCHER_PROMPT_FILE contains .."; continue ;;
            esac
            if [[ "$META_OUTER_LAUNCHER_PROMPT_FILE" != "$_expected_prompt" ]]; then
                mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: OUTER_LAUNCHER_PROMPT_FILE not the expected sidecar"
                continue
            fi
            if [[ ! -f "$META_OUTER_LAUNCHER_PROMPT_FILE" || -L "$META_OUTER_LAUNCHER_PROMPT_FILE" || ! -r "$META_OUTER_LAUNCHER_PROMPT_FILE" ]]; then
                mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: OUTER_LAUNCHER_PROMPT_FILE not a readable regular non-symlink file"
                continue
            fi
            case "$META_OUTER_LAUNCHER_WORKDIR" in
                *..*) mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: OUTER_LAUNCHER_WORKDIR contains .."; continue ;;
            esac
            if [[ ! -d "$META_OUTER_LAUNCHER_WORKDIR" ]]; then
                mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: OUTER_LAUNCHER_WORKDIR not a directory"
                continue
            fi
            case "$META_OUTER_LAUNCHER_RISK" in
                high|low) ;;
                *) META_OUTER_LAUNCHER_RISK=high ;;
            esac
            (
                cd "$META_OUTER_LAUNCHER_WORKDIR" || exit 1
                # Sanitize test-hook env vars before exec (R2_FINDING_1 of
                # /review). The launcher's per-invocation gating
                # (LARCH_ALLOW_TEST_HOOKS=1 + LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE)
                # is correct for direct callers, but the collector's outer-
                # retry path runs in a silenced background subshell — if those
                # env vars are inherited from the collector process (CI env
                # leak, attacker on same UID, etc.), every retry would
                # silently source an arbitrary file under the collector UID
                # with no log signal. `env -u` clears them just for this
                # exec, defense-in-depth on top of the per-invocation gate.
                # The legacy single-env-var name is also cleared even though
                # the launcher does not honor it, to keep the cleared set
                # symmetric with the launcher's gating contract.
                env -u LARCH_ALLOW_TEST_HOOKS \
                    -u LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE \
                    -u LARCH_TEST_TRAP_AFTER_INNER_DONE \
                    -- "$META_OUTER_LAUNCHER" \
                        --output "$RETRY_OUTPUT" \
                        --timeout "$META_TIMEOUT" \
                        --risk "$META_OUTER_LAUNCHER_RISK" \
                        --prompt-file "$META_OUTER_LAUNCHER_PROMPT_FILE"
            ) >/dev/null 2>&1 &
            RETRY_SENTINELS+=("${RETRY_OUTPUT}.done")
            RETRY_LAUNCHED[j]=1
            continue
        fi

        # Fail closed on missing/malformed retry metadata: immediately mark the
        # original result unhealthy and flip the tool to unhealthy so callers
        # do not see a stale STATUS=EMPTY_OUTPUT|HEALTHY=true when no retry
        # process is launched.
        # Distinct messages so logs and harness assertions reflect which field
        # is actually missing — stale CMD=-only sidecars have TOOL but lack
        # CMD_JSON, and vice versa.
        if [[ -z "$META_CMD_JSON" && -z "$META_TOOL" ]]; then
            IDX="${RETRY_INDICES[$j]}"
            mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: missing CMD_JSON and TOOL"
            continue
        fi
        if [[ -z "$META_CMD_JSON" ]]; then
            IDX="${RETRY_INDICES[$j]}"
            mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: missing CMD_JSON"
            continue
        fi
        if [[ -z "$META_TOOL" ]]; then
            IDX="${RETRY_INDICES[$j]}"
            mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: missing TOOL"
            continue
        fi
        if ! printf '%s' "$META_CMD_JSON" | jq -e 'type=="array" and length>0 and all(.[]; type=="string")' >/dev/null 2>&1; then
            IDX="${RETRY_INDICES[$j]}"
            mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: malformed CMD_JSON"
            continue
        fi

        # Build retry command: run-external-agent.sh with updated output path
        RETRY_ARGS=(--tool "$META_TOOL" --output "$RETRY_OUTPUT" --timeout "$META_TIMEOUT")
        if [[ "$META_CAPTURE" == "true" ]]; then
            RETRY_ARGS+=(--capture-stdout)
        elif [[ "$META_CAPTURE_STDOUT_ONLY" == "true" ]]; then
            RETRY_ARGS+=(--capture-stdout-only)
        fi
        RETRY_ARGS+=(--)

        # Deserialize CMD_JSON into a Bash array. Bash 3.2 portability:
        # mapfile is Bash 4+, and the retry block uses a here-string loop
        # instead of process-substitution redirection. Newline safety: jq emits
        # base64 records, and command substitution appends/removes a sentinel
        # byte so argv elements ending in newlines survive byte-exact.
        CMD_ARR=()
        _decode_failed=false
        _b64_stream=$(printf '%s' "$META_CMD_JSON" | jq -r '.[] | @base64')
        while IFS= read -r _b64 || [[ -n "${_b64:-}" ]]; do
            [[ -z "$_b64" ]] && continue
            if ! _decoded=$({ printf '%s\n' "$_b64" | base64 -d; _decode_status=$?; printf X; exit "$_decode_status"; }); then
                IDX="${RETRY_INDICES[$j]}"
                mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: CMD_JSON decode failed"
                _decode_failed=true
                break
            fi
            CMD_ARR+=("${_decoded%X}")
        done <<< "$_b64_stream"
        # Decode failure path is terminal for this index — skip the
        # empty-array branch below so it does not overwrite the specific
        # "decode failed" reason with the generic "empty after decode" one.
        if [[ "$_decode_failed" == "true" ]]; then
            continue
        fi
        if [[ ${#CMD_ARR[@]} -eq 0 ]]; then
            IDX="${RETRY_INDICES[$j]}"
            mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: empty CMD_JSON array after decode"
            continue
        fi

        _expected_len=$(printf '%s' "$META_CMD_JSON" | jq 'length')
        if [[ "${#CMD_ARR[@]}" -ne "$_expected_len" ]]; then
            IDX="${RETRY_INDICES[$j]}"
            mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: CMD_JSON decode length mismatch"
            continue
        fi

        # Element-wise replacement of the original output path with the retry
        # path. Equality (not substring): argv elements that merely contain the
        # original path, such as prompt text, must not be mutated.
        if [[ -n "$META_ORIG_OUTPUT" ]]; then
            for _i in "${!CMD_ARR[@]}"; do
                if [[ "${CMD_ARR[$_i]}" == "$META_ORIG_OUTPUT" ]]; then
                    CMD_ARR[_i]="$RETRY_OUTPUT"
                fi
            done
        fi

        cmd_json_shape_valid_for_tool "$META_TOOL" "${CMD_ARR[@]}"
        _shape_rc=$?
        if [[ "$_shape_rc" == "2" ]]; then
            IDX="${RETRY_INDICES[$j]}"
            mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: unknown TOOL for CMD_JSON"
            continue
        fi
        if [[ "$_shape_rc" != "0" ]]; then
            IDX="${RETRY_INDICES[$j]}"
            mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: CMD_JSON argv shape rejected for $META_TOOL"
            continue
        fi

        "$SCRIPT_DIR/run-external-agent.sh" "${RETRY_ARGS[@]}" "${CMD_ARR[@]}" >/dev/null 2>&1 &
        RETRY_SENTINELS+=("${RETRY_OUTPUT}.done")
        RETRY_LAUNCHED[j]=1
    done

    # Wait for retry sentinels
    if [[ ${#RETRY_SENTINELS[@]} -gt 0 ]]; then
        "$SCRIPT_DIR/wait-for-reviewers.sh" --timeout "$MAX_RETRY_TIMEOUT" "${RETRY_SENTINELS[@]}" >/dev/null 2>&1 || true

        # Check retry results and update. Indices that fail-closed before
        # launch (mark_retry_metadata_invalid) leave RETRY_LAUNCHED[$j] unset;
        # skip them here so their specific FAILURE_REASON survives.
        for j in "${!RETRY_FILES[@]}"; do
            if [[ "${RETRY_LAUNCHED[$j]:-0}" != "1" ]]; then
                continue
            fi
            ORIG_OUTPUT="${RETRY_FILES[$j]}"
            RETRY_OUTPUT="${ORIG_OUTPUT%.txt}-retry.txt"
            RETRY_SENTINEL="${RETRY_OUTPUT}.done"
            IDX="${RETRY_INDICES[$j]}"
            TOOL=$(derive_tool "$ORIG_OUTPUT")

            if [[ -f "$RETRY_SENTINEL" ]]; then
                RETRY_EXIT=$(cat "$RETRY_SENTINEL" 2>/dev/null || echo "99")
                RETRY_EXIT=$(normalize_exit_code_or_99 "$RETRY_EXIT" "retry sentinel")
                if [[ "$RETRY_EXIT" == "0" && -s "$RETRY_OUTPUT" ]]; then
                    # F4 fix: retry succeeded — tool is healthy (retry recovered from transient failure)
                    HEALTHY="true"
                    # Still respect monotonic health from PRIOR calls (via get_tool_healthy)
                    if [[ "$(get_tool_healthy "$TOOL")" == "false" ]]; then
                        HEALTHY="false"
                    fi
                    RESULTS[IDX]="REVIEWER_FILE=$RETRY_OUTPUT|TOOL=$TOOL|STATUS=OK|EXIT_CODE=0|HEALTHY=$HEALTHY|FAILURE_REASON="
                else
                    # Retry also failed — NOW mark tool unhealthy
                    set_tool_unhealthy "$TOOL"
                    if [[ "$RETRY_EXIT" == "124" ]]; then
                        RETRY_STATUS="TIMED_OUT"
                    elif [[ "$RETRY_EXIT" != "0" ]]; then
                        RETRY_STATUS="FAILED"
                    else
                        RETRY_STATUS="EMPTY_OUTPUT"
                    fi
                    RETRY_REASON=$(build_failure_reason "$RETRY_OUTPUT" "$RETRY_STATUS" "$RETRY_EXIT")
                    RESULTS[IDX]="REVIEWER_FILE=$ORIG_OUTPUT|TOOL=$TOOL|STATUS=EMPTY_OUTPUT|EXIT_CODE=$RETRY_EXIT|HEALTHY=false|FAILURE_REASON=Retry also failed: $RETRY_REASON"
                fi
            else
                # Retry sentinel never appeared — mark unhealthy
                set_tool_unhealthy "$TOOL"
                RESULTS[IDX]=$(build_missing_retry_sentinel_result "$ORIG_OUTPUT" "$TOOL")
            fi
        done
    fi
fi

# --- 3.5. Substantive-content validation (opt-in via --substantive-validation) ---
# After section 3 (retry) every entry in RESULTS reflects its final status. For
# each entry whose STATUS=OK, invoke validate-research-output.sh on its file
# (REVIEWER_FILE — the retry path may have set it to a *-retry.txt). On
# validator failure, rewrite the entry to STATUS=NOT_SUBSTANTIVE with the
# sanitized diagnostic in FAILURE_REASON and HEALTHY=false; call
# set_tool_unhealthy to preserve per-tool health monotonicity. Closes #416.
if [[ "$SUBSTANTIVE_VALIDATION" == "true" ]]; then
    VALIDATOR="$SCRIPT_DIR/validate-research-output.sh"
    VAL_ARGS=()
    if [[ "$VALIDATION_MODE" == "true" ]]; then
        VAL_ARGS+=(--validation-mode)
    fi
    for j in "${!RESULTS[@]}"; do
        entry="${RESULTS[$j]}"
        # Precise field-by-field extraction. Fields 1-5 (REVIEWER_FILE, TOOL,
        # STATUS, EXIT_CODE, HEALTHY) never contain '|' by construction (paths
        # are tmpdir paths; tools are registered LARCH_EXTERNAL_TOOLS ids — kept
        # label-safe per the registry contract — or "unknown"; STATUS/HEALTHY are
        # fixed enums; EXIT_CODE is numeric). FAILURE_REASON (field 6) is the
        # only field that may carry user content, and it's the trailing field
        # — its content cannot collide with the field-1..5 prefixes.
        rf_field="${entry%%|*}"             # REVIEWER_FILE=<path>
        REVIEWER_FILE="${rf_field#REVIEWER_FILE=}"
        rest1="${entry#*|}"                 # TOOL=<name>|...
        tool_field="${rest1%%|*}"           # TOOL=<name>
        ENTRY_TOOL="${tool_field#TOOL=}"
        rest2="${rest1#*|}"                 # STATUS=<S>|...
        status_field="${rest2%%|*}"         # STATUS=<S>
        ENTRY_STATUS="${status_field#STATUS=}"

        if [[ "$ENTRY_STATUS" != "OK" ]]; then
            continue
        fi

        # Run validator. Diagnostic on stdout; capture both stdout and stderr.
        # The collector runs without `set -e`, so a non-zero exit from the
        # validator does NOT abort the loop.
        # bash 3.2 portability: `"${VAL_ARGS[@]}"` on an empty array fires
        # `unbound variable` under `set -u` on macOS /bin/bash (3.2.57); the
        # `${arr[@]+"${arr[@]}"}` guard expands to nothing when empty. #511.
        DIAG=$("$VALIDATOR" "${VAL_ARGS[@]+"${VAL_ARGS[@]}"}" "$REVIEWER_FILE" 2>&1)
        VAL_EXIT=$?
        if [[ "$VAL_EXIT" -ne 0 ]]; then
            # Sanitize: strip '|' (would corrupt pipe-delimited RESULTS), replace
            # newlines with spaces, collapse whitespace, truncate to 200 chars.
            DIAG_SAN=$(printf '%s' "$DIAG" | tr '|\n' '/ ' | tr -s '[:space:]' ' ' | sed 's/^ //; s/ $//' | cut -c1-200)
            RESULTS[j]="REVIEWER_FILE=$REVIEWER_FILE|TOOL=$ENTRY_TOOL|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|HEALTHY=false|FAILURE_REASON=$DIAG_SAN"
            set_tool_unhealthy "$ENTRY_TOOL"
        fi
    done
fi

# --- 4. Emit structured results ---
FIRST=true
for result in "${RESULTS[@]}"; do
    if [[ "$FIRST" == "true" ]]; then
        FIRST=false
    else
        echo ""
    fi
    # Convert pipe-delimited to newlines
    echo "$result" | tr '|' '\n'
done

# --- 5. Write health file (if requested, monotonic per tool) ---
# F2 fix: uses CODEX_TOOL_HEALTHY/CURSOR_TOOL_HEALTHY/GEMINI_TOOL_HEALTHY which were seeded from
# the existing health file (if any) and only downgraded during this run.
if [[ -n "$WRITE_HEALTH" && "$WRITE_HEALTH" != "/dev/null" ]]; then
    HEALTH_TMPFILE=$(mktemp "${WRITE_HEALTH}.tmp.XXXXXX")
    {
        echo "CODEX_HEALTHY=$CODEX_TOOL_HEALTHY"
        echo "CURSOR_HEALTHY=$CURSOR_TOOL_HEALTHY"
        echo "GEMINI_HEALTHY=$GEMINI_TOOL_HEALTHY"
    } > "$HEALTH_TMPFILE"
    mv "$HEALTH_TMPFILE" "$WRITE_HEALTH"
fi
