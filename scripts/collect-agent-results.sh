#!/usr/bin/env bash
# collect-agent-results.sh — Collect, validate, and optionally retry external reviewer outputs.
#
# Consolidates the post-launch validation+retry pattern used across all skills.
# Wraps wait-for-reviewers.sh, validates each output, retries once on empty or
# transient network failure via .meta files written by run-external-agent.sh,
# and emits structured results.
#
# Runtime prerequisites: bash >= 3.2 (the retry block is portable to macOS
# /bin/bash 3.2). The empty-output retry path additionally requires `jq` (to
# validate and deserialize CMD_JSON) and `base64 -d` (GNU/BSD/BusyBox-portable
# for argv element decode). Empty-output retries fail closed if either is
# missing — see SECURITY.md "Retry-metadata deserialization" and the
# "Empty-output retry deserializer" section in scripts/collect-agent-results.md.
#
# Usage:
#   collect-agent-results.sh --timeout <seconds> \
#     [--substantive-validation] [--structured-reviewer-validation] \
#     [--summary-only] \
#     [--paths-file <file>] \
#     <output-file> [<output-file> ...]
#
#   When --paths-file is set, it is mutually exclusive with positional output-file
#   arguments: paths are read one per line from the file (blank lines skipped) and
#   the collector must still resolve to at least one non-blank path line.
#
# Options:
#   --timeout <seconds>            Timeout for wait-for-reviewers.sh (e.g., 1860)
#   --substantive-validation       After the existing non-empty + retry path settles,
#                                  invoke scripts/validate-research-output.sh on each
#                                  STATUS=OK entry. On validator failure, rewrite the
#                                  entry as STATUS=NOT_SUBSTANTIVE |
#                                  FAILURE_REASON=<sanitized validator diagnostic>
#                                  Default OFF — opt-in per caller.
#                                  Currently opted in by: /research research phase
#                                  (Standard / Deep), /research validation phase,
#                                  /review Step 3a
#                                  review, /design Step 3 plan-review.
#                                  Closes #416 (Phase 3 of umbrella #413), #661.
#   --validation-mode              Modifier for --substantive-validation: forwards
#                                  --validation-mode to validate-research-output.sh
#                                  so its preset (JSON no-findings sentinel and
#                                  legacy NO_ISSUES_FOUND short-circuit, explicit
#                                  CURSOR_EMPTY_RESPONSE mapping, and 30-word floor)
#                                  applies. Use for short reviewer-style outputs:
#                                  /research validation phase, /review, /implement
#                                  /design plan-review. The
#                                  /research research phase deliberately omits this
#                                  modifier because its outputs are 2-3-paragraph
#                                  prose, not short findings. No effect when
#                                  --substantive-validation is not also passed.
#                                  See docs/external-reviewers.md Output Validation
#                                  for the per-skill opt-in matrix.
#   --structured-reviewer-validation
#                                  After retry and substantive validation settle,
#                                  invoke scripts/validate-research-output.sh
#                                  --structured-reviewer-mode on each STATUS=OK
#                                  entry. Valid records are written to a derived
#                                  sidecar path and emitted as STRUCTURED_SIDECAR.
#                                  On validator failure, rewrite the entry as
#                                  STATUS=NOT_SUBSTANTIVE. Default OFF — opt-in per caller.
#   --summary-only                 Emit only REVIEWER_FILE, TOOL, STATUS,
#                                  and EXIT_CODE for each reviewer.
#                                  Wait/retry/validation behavior is unchanged;
#                                  FAILURE_REASON and STRUCTURED_SIDECAR are suppressed.
#   --paths-file <file>             Read output paths from a line-oriented file instead
#                                  of positional arguments. Mutually exclusive with
#                                  positional output paths. Missing/unreadable files,
#                                  empty files, and whitespace-only files exit 1.
#
# Arguments:
#   One or more output file paths (from run-external-agent.sh invocations), unless
#   --paths-file supplies the path list.
#   Sentinel paths are derived by appending .done to each output file.
#   Metadata paths are derived by appending .meta to each output file.
#
# Output (KEY=value blocks on stdout, one block per reviewer, separated by blank lines):
#   REVIEWER_FILE=<output-path>
#   TOOL=<registered external tool|unknown>
#   STATUS=<OK|TIMED_OUT|FAILED|EMPTY_OUTPUT|SENTINEL_TIMEOUT|NOT_SUBSTANTIVE|cap_hit>
#   EXIT_CODE=<N>
#   STRUCTURED_SIDECAR=<path>  (non-empty only when structured validation succeeds)
#   FAILURE_REASON=<explanation>  (non-empty when STATUS != OK; explains the cause of failure)
#   With --summary-only, only REVIEWER_FILE, TOOL, STATUS, and EXIT_CODE are emitted.
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
# shellcheck source=scripts/lib-net.sh
source "$SCRIPT_DIR/lib-net.sh" || { echo "collect-agent-results.sh: failed to source lib-net.sh" >&2; exit 1; }
[[ "${LARCH_LIB_NET_LOADED:-}" == "1" ]] || { echo "collect-agent-results.sh: lib-net.sh sourced but sentinel missing" >&2; exit 1; }
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh" || { echo "collect-agent-results.sh: failed to source lib-quiet.sh" >&2; exit 1; }
# shellcheck source=scripts/lib-failed-agent-stderr-tail.sh
source "$SCRIPT_DIR/lib-failed-agent-stderr-tail.sh" || { echo "collect-agent-results.sh: failed to source lib-failed-agent-stderr-tail.sh" >&2; exit 1; }

normalize_exit_code_or_99() {
    local raw="$1"
    local context="$2"
    if [[ "$raw" =~ ^[0-9]{1,3}$ ]] && (( 10#$raw <= 255 )); then
        printf '%s' "$raw"
        return 0
    fi
    larch_errf 'collect-agent-results.sh: invalid exit code from %s; forcing EXIT_CODE=99\n' "$context"
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
    printf 'REVIEWER_FILE=%s|TOOL=%s|STATUS=EMPTY_OUTPUT|EXIT_CODE=99|STRUCTURED_SIDECAR=|FAILURE_REASON=Retry process did not complete (sentinel file missing)' \
        "$orig_output" "$tool"
}

first_pass_sidecar_path() {
    local orig_output="$1"
    case "$orig_output" in
        *.txt) printf '%s-first-pass.txt' "${orig_output%.txt}" ;;
        *) printf '%s-first-pass' "$orig_output" ;;
    esac
}

preserve_and_publish_ns_retry() {
    local orig_output="$1"
    local retry_output="$2"
    local retry_label="$3"
    local first_pass_sidecar=""
    local orig_dir=""
    local orig_base=""
    local publish_tmp=""

    first_pass_sidecar="$(first_pass_sidecar_path "$orig_output")"
    if cp "$orig_output" "$first_pass_sidecar" 2>/dev/null; then
        larch_err "ns-retry: first-pass content preserved at $(basename "$first_pass_sidecar")"
    else
        larch_err "collect-agent-results.sh: $retry_label: failed to preserve first-pass content at $first_pass_sidecar; leaving STATUS=NOT_SUBSTANTIVE"
        return 1
    fi

    orig_dir="$(dirname "$orig_output")"
    orig_base="$(basename "$orig_output")"
    if ! publish_tmp="$(mktemp "$orig_dir/.${orig_base}.ns-retry.XXXXXX" 2>/dev/null)"; then
        rm -f "$first_pass_sidecar" 2>/dev/null || true
        larch_err "collect-agent-results.sh: $retry_label: failed to allocate temp publish path for $orig_output; leaving STATUS=NOT_SUBSTANTIVE"
        return 1
    fi

    if cp "$retry_output" "$publish_tmp" 2>/dev/null && mv -f "$publish_tmp" "$orig_output" 2>/dev/null; then
        larch_err "ns-retry: published retry content to $orig_base; retry artifact retained at $(basename "$retry_output")"
        return 0
    fi

    rm -f "$publish_tmp" "$first_pass_sidecar" 2>/dev/null || true
    larch_err "collect-agent-results.sh: $retry_label: failed to publish retry output to $orig_output; leaving STATUS=NOT_SUBSTANTIVE"
    return 1
}

if [[ "${BASH_SOURCE[0]}" != "$0" && "${1:-}" == "--source-only" ]]; then
    return 0
fi

larch_quiet_init

TIMEOUT=""
SUBSTANTIVE_VALIDATION="false"
VALIDATION_MODE="false"
STRUCTURED_REVIEWER_VALIDATION="false"
SUMMARY_ONLY="false"
COLLECT_PATHS_FILE=""
OUTPUT_FILES=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --timeout)
            TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --substantive-validation)
            SUBSTANTIVE_VALIDATION="true"; shift ;;
        --validation-mode)
            VALIDATION_MODE="true"; shift ;;
        --structured-reviewer-validation)
            STRUCTURED_REVIEWER_VALIDATION="true"; shift ;;
        --summary-only)
            SUMMARY_ONLY="true"; shift ;;
        --paths-file)
            COLLECT_PATHS_FILE="${2:?--paths-file requires a value}"; shift 2 ;;
        --help)
            larch_err "Usage: collect-agent-results.sh --timeout <seconds> [--substantive-validation [--validation-mode]] [--structured-reviewer-validation] [--summary-only] [--paths-file <file>] <output-file>...  (--paths-file is mutually exclusive with positional output-file arguments)"
            exit 0 ;;
        -*)
            larch_err "collect-agent-results.sh: unknown option: $1"; exit 1 ;;
        *)
            OUTPUT_FILES+=("$1"); shift ;;
    esac
done

if [[ -z "$TIMEOUT" ]]; then
    larch_err "collect-agent-results.sh: --timeout is required"
    exit 1
fi

if [[ -n "$COLLECT_PATHS_FILE" && ${#OUTPUT_FILES[@]} -gt 0 ]]; then
    larch_err "collect-agent-results.sh: --paths-file is mutually exclusive with positional output-file arguments"
    exit 1
fi

if [[ -n "$COLLECT_PATHS_FILE" ]]; then
    if [[ ! -r "$COLLECT_PATHS_FILE" ]]; then
        larch_err "collect-agent-results.sh: paths-file not readable: $COLLECT_PATHS_FILE"
        exit 1
    fi
    if [[ ! -f "$COLLECT_PATHS_FILE" ]]; then
        larch_err "collect-agent-results.sh: paths-file is not a regular file: $COLLECT_PATHS_FILE"
        exit 1
    fi
    while IFS= read -r path || [[ -n "$path" ]]; do
        if [[ "$path" == *[![:space:]]* ]]; then
            case "$path" in
                *$'\n'*|*$'\r'*)
                    larch_err "collect-agent-results.sh: paths-file line contains a newline or carriage return (line-oriented paths-file contract): $COLLECT_PATHS_FILE"
                    exit 1
                    ;;
            esac
            OUTPUT_FILES+=("$path")
        fi
    done < "$COLLECT_PATHS_FILE"
    if [[ ${#OUTPUT_FILES[@]} -eq 0 ]]; then
        larch_err "collect-agent-results.sh: paths-file contains no entries (preserves anti-pattern #4)"
        exit 1
    fi
fi

if [[ ${#OUTPUT_FILES[@]} -eq 0 ]]; then
    larch_err "collect-agent-results.sh: at least one output file is required"
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
    larch_err "collect-agent-results.sh: mktemp failed"
    exit 1
}
trap 'rm -f -- "$WAIT_STDERR"' EXIT
WAIT_OUTPUT=$("$SCRIPT_DIR/wait-for-reviewers.sh" --timeout "$TIMEOUT" "${SENTINELS[@]}" 2>"$WAIT_STDERR")
WAIT_RC=$?
if [[ "$WAIT_RC" -ne 0 ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$(printf '%s' "$line" | sanitize_diagnostic_line)"; done < "$WAIT_STDERR"
    larch_errf 'collect-agent-results.sh: wait-for-reviewers.sh exited %s\n' "$WAIT_RC"
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
# from stderr-on-failure paths would inject phantom lines
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

with_structured_sidecar_field() {
    local entry="$1"
    local sidecar="$2"
    if [[ "$entry" == *"|STRUCTURED_SIDECAR="* ]]; then
        printf '%s' "$entry"
        return 0
    fi
    printf '%s|STRUCTURED_SIDECAR=%s|FAILURE_REASON=%s' \
        "${entry%|FAILURE_REASON=*}" \
        "$sidecar" \
        "${entry##*|FAILURE_REASON=}"
}

result_field_value() {
    local entry="$1"
    local key="$2"
    local field=""
    while [[ -n "$entry" ]]; do
        if [[ "$entry" == *"|"* ]]; then
            field="${entry%%|*}"
            entry="${entry#*|}"
        else
            field="$entry"
            entry=""
        fi
        case "$field" in
            "$key"=*)
                printf '%s' "${field#*=}"
                return 0
                ;;
        esac
    done
    return 1
}

# --- Helper: map NOT_SUBSTANTIVE classification to NS_RETRY_REASON token ---
# args: val_exit (validate-research-output.sh exit code), ns_mode (substantive|structured)
# output: one of NO_ISSUES_FOUND_TOO_THIN OUTPUT_EMPTY JSON_PARSE_FAIL UNKNOWN
derive_ns_retry_reason() {
    local val_exit="$1"
    local ns_mode="$2"
    case "$ns_mode" in
        structured)
            case "$val_exit" in
                5) printf 'JSON_PARSE_FAIL' ;;
                *) printf 'UNKNOWN' ;;
            esac ;;
        *)
            case "$val_exit" in
                2|3) printf 'NO_ISSUES_FOUND_TOO_THIN' ;;
                4)   printf 'OUTPUT_EMPTY' ;;
                *)   printf 'UNKNOWN' ;;
            esac ;;
    esac
}

# --- Helper: build failure reason from .diag file or status ---
build_failure_reason() {
    local output_file="$1"
    local status="$2"
    local exit_code="$3"
    local diag_file="${output_file}.diag"
    local raw

    if [[ -s "$diag_file" ]]; then
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

_classify_sentinel_status() {
    local _file="$1"
    [[ -f "$_file" && -s "$_file" ]] || return 1
    local _first
    _first=$(awk '/[^[:space:]]/ { sub(/^[[:space:]]+/, ""); sub(/[[:space:]]+$/, ""); print; exit }' "$_file" 2>/dev/null)
    [[ "$_first" == "CURSOR_EMPTY_RESPONSE" || "$_first" == "CURSOR_DEGRADED_RESPONSE" ]]
}

mark_retry_metadata_invalid() {
    local idx="$1"
    local orig_output="$2"
    local reason="$3"
    local tool
    tool=$(derive_tool "$orig_output")
    RESULTS[idx]="REVIEWER_FILE=$orig_output|TOOL=$tool|STATUS=EMPTY_OUTPUT|EXIT_CODE=99|FAILURE_REASON=$reason"
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
        *)
            return 2
            ;;
    esac
    return 0
}

parse_retry_meta() {
    local meta_path="$1"
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
    done < "$meta_path"
}

validate_retry_timeout_or_mark() {
    local idx="$1"
    local orig_output="$2"
    local timeout_value="$3"
    local invalid_reason=""
    if [[ -z "$timeout_value" ]]; then
        invalid_reason="Retry metadata invalid: TIMEOUT missing"
    else
        case "$timeout_value" in
            ''|*[!0-9]*) invalid_reason="Retry metadata invalid: TIMEOUT not a positive integer" ;;
            *) if (( 10#$timeout_value < 1 )); then
                   invalid_reason="Retry metadata invalid: TIMEOUT not a positive integer"
               fi ;;
        esac
    fi
    if [[ -n "$invalid_reason" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "$invalid_reason"
        return 1
    fi
    META_TIMEOUT=$((10#$timeout_value))
    return 0
}

launch_outer_retry_or_mark() {
    local idx="$1"
    local orig_output="$2"
    local retry_output="$3"
    local prompt_file="$4"
    local timeout_value="$5"
    local launched_var="$6"
    local sentinels_var="$7"

    if [[ -z "$META_OUTER_LAUNCHER" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: missing OUTER_LAUNCHER"
        return 1
    fi
    if [[ -z "$META_OUTER_LAUNCHER_PROMPT_FILE" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: missing OUTER_LAUNCHER_PROMPT_FILE"
        return 1
    fi
    if [[ -z "$META_OUTER_LAUNCHER_WORKDIR" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: missing OUTER_LAUNCHER_WORKDIR"
        return 1
    fi
    case "$META_OUTER_LAUNCHER" in
        *..*) mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: OUTER_LAUNCHER contains .."; return 1 ;;
    esac
    _launcher_base=$(basename "$META_OUTER_LAUNCHER")
    case "$META_TOOL:$_launcher_base" in
        cursor:launch-review.sh|codex:launch-review.sh) _expected_launcher="$SCRIPT_DIR/launch-review.sh" ;;
        cursor:*|codex:*) _expected_launcher="$SCRIPT_DIR/launch-review.sh" ;;
        *) mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: OUTER_LAUNCHER not canonical launch-review.sh"; return 1 ;;
    esac
    if ! _expected_launcher_dir=$(cd "$(dirname "$_expected_launcher")" 2>/dev/null && pwd -P 2>/dev/null); then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: OUTER_LAUNCHER not canonical $(basename "$_expected_launcher")"
        return 1
    fi
    if ! _candidate_launcher_dir=$(cd "$(dirname "$META_OUTER_LAUNCHER")" 2>/dev/null && pwd -P 2>/dev/null); then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: OUTER_LAUNCHER not canonical $(basename "$_expected_launcher")"
        return 1
    fi
    _expected_launcher_canonical="$_expected_launcher_dir/$(basename "$_expected_launcher")"
    _candidate_canonical="$_candidate_launcher_dir/$(basename "$META_OUTER_LAUNCHER")"
    if [[ "$_candidate_canonical" != "$_expected_launcher_canonical" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: OUTER_LAUNCHER not canonical $(basename "$_expected_launcher")"
        return 1
    fi
    if [[ ! -f "$META_OUTER_LAUNCHER" || -L "$META_OUTER_LAUNCHER" || ! -x "$META_OUTER_LAUNCHER" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: OUTER_LAUNCHER not a regular non-symlink executable file"
        return 1
    fi
    _expected_prompt="${orig_output}.prompt"
    case "$META_OUTER_LAUNCHER_PROMPT_FILE" in
        *..*) mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: OUTER_LAUNCHER_PROMPT_FILE contains .."; return 1 ;;
    esac
    if [[ "$META_OUTER_LAUNCHER_PROMPT_FILE" != "$_expected_prompt" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: OUTER_LAUNCHER_PROMPT_FILE not the expected sidecar"
        return 1
    fi
    if [[ ! -f "$META_OUTER_LAUNCHER_PROMPT_FILE" || -L "$META_OUTER_LAUNCHER_PROMPT_FILE" || ! -r "$META_OUTER_LAUNCHER_PROMPT_FILE" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: OUTER_LAUNCHER_PROMPT_FILE not a readable regular non-symlink file"
        return 1
    fi
    case "$META_OUTER_LAUNCHER_WORKDIR" in
        *..*) mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: OUTER_LAUNCHER_WORKDIR contains .."; return 1 ;;
    esac
    if [[ ! -d "$META_OUTER_LAUNCHER_WORKDIR" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: OUTER_LAUNCHER_WORKDIR not a directory"
        return 1
    fi
    case "$META_OUTER_LAUNCHER_RISK" in
        high|low) ;;
        *) META_OUTER_LAUNCHER_RISK=high ;;
    esac
    (
        cd "$META_OUTER_LAUNCHER_WORKDIR" || exit 1
        env -u LARCH_ALLOW_TEST_HOOKS \
            -u LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE \
            -u LARCH_TEST_TRAP_AFTER_INNER_DONE \
            -- "$META_OUTER_LAUNCHER" \
                --tool "$META_TOOL" \
                --output "$retry_output" \
                --timeout "$timeout_value" \
                --risk "$META_OUTER_LAUNCHER_RISK" \
                --prompt-file "$prompt_file"
    ) >/dev/null 2>&1 &
    eval "$launched_var=1"
    eval "$sentinels_var+=(\"\${retry_output}.done\")"
    return 0
}

launch_cmd_json_retry_or_mark() {
    local idx="$1"
    local orig_output="$2"
    local retry_output="$3"
    local launched_var="$4"
    local sentinels_var="$5"

    if [[ -z "$META_CMD_JSON" && -z "$META_TOOL" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: missing CMD_JSON and TOOL"
        return 1
    fi
    if [[ -z "$META_CMD_JSON" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: missing CMD_JSON"
        return 1
    fi
    if [[ -z "$META_TOOL" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: missing TOOL"
        return 1
    fi
    if ! printf '%s' "$META_CMD_JSON" | jq -e 'type=="array" and length>0 and all(.[]; type=="string")' >/dev/null 2>&1; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: malformed CMD_JSON"
        return 1
    fi

    RETRY_ARGS=(--tool "$META_TOOL" --output "$retry_output" --timeout "$META_TIMEOUT")
    if [[ "$META_CAPTURE" == "true" ]]; then
        RETRY_ARGS+=(--capture-stdout)
    elif [[ "$META_CAPTURE_STDOUT_ONLY" == "true" ]]; then
        RETRY_ARGS+=(--capture-stdout-only)
    fi
    RETRY_ARGS+=(--)

    CMD_ARR=()
    _decode_failed=false
    _b64_stream=$(printf '%s' "$META_CMD_JSON" | jq -r '.[] | @base64')
    while IFS= read -r _b64 || [[ -n "${_b64:-}" ]]; do
        [[ -z "$_b64" ]] && continue
        if ! _decoded=$({ printf '%s\n' "$_b64" | base64 -d; _decode_status=$?; printf X; exit "$_decode_status"; }); then
            mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: CMD_JSON decode failed"
            _decode_failed=true
            break
        fi
        CMD_ARR+=("${_decoded%X}")
    done <<< "$_b64_stream"
    if [[ "$_decode_failed" == "true" ]]; then
        return 1
    fi
    if [[ ${#CMD_ARR[@]} -eq 0 ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: empty CMD_JSON array after decode"
        return 1
    fi

    _expected_len=$(printf '%s' "$META_CMD_JSON" | jq 'length')
    if [[ "${#CMD_ARR[@]}" -ne "$_expected_len" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: CMD_JSON decode length mismatch"
        return 1
    fi

    if [[ -n "$META_ORIG_OUTPUT" ]]; then
        for _i in "${!CMD_ARR[@]}"; do
            if [[ "${CMD_ARR[$_i]}" == "$META_ORIG_OUTPUT" ]]; then
                CMD_ARR[_i]="$retry_output"
            fi
        done
    fi
    cmd_json_shape_valid_for_tool "$META_TOOL" "${CMD_ARR[@]}"
    _shape_rc=$?
    if [[ "$_shape_rc" == "2" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: unknown TOOL for CMD_JSON"
        return 1
    fi
    if [[ "$_shape_rc" != "0" ]]; then
        mark_retry_metadata_invalid "$idx" "$orig_output" "Retry metadata invalid: CMD_JSON argv shape rejected for $META_TOOL"
        return 1
    fi

    _last_idx=$((${#CMD_ARR[@]} - 1))
    CMD_ARR[_last_idx]="${NS_STRONG_HEADER}${CMD_ARR[_last_idx]}"

    "$SCRIPT_DIR/run-external-agent.sh" "${RETRY_ARGS[@]}" "${CMD_ARR[@]}" >/dev/null 2>&1 &
    eval "$launched_var=1"
    eval "$sentinels_var+=(\"\${retry_output}.done\")"
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
    FAILURE_REASON=""

    # wait emits indexed records keyed by argv order. OUTPUT_FILES[$i]
    # (0-based) corresponds to wait's idx (1-based) = i+1.
    if is_index_timed_out "$((i + 1))"; then
        # wait-for-reviewers.sh reported TIMEOUT (sentinel never appeared)
        STATUS="SENTINEL_TIMEOUT"
        EXIT_CODE="124"
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
            FAILURE_REASON=$(build_failure_reason "$OUTPUT" "$STATUS" "$EXIT_CODE")
        elif [[ "$EXIT_CODE" != "0" ]]; then
            STATUS="FAILED"
            FAILURE_REASON=$(build_failure_reason "$OUTPUT" "$STATUS" "$EXIT_CODE")
        elif [[ -s "$OUTPUT" ]] && [[ "$(head -1 "$OUTPUT" 2>/dev/null)" == "STATUS=cap_hit" ]]; then
            # Budget-cap sentinel written by review launchers: reviewer deliberately
            # skipped; not forwarded to substantive validation or reviewer synthesis.
            STATUS="cap_hit"
            FAILURE_REASON="Token budget cap hit; reviewer skipped"
        elif [[ ! -s "$OUTPUT" ]]; then
            # F4 fix: empty output is a retry candidate, not an immediate hard failure.
            STATUS="EMPTY_OUTPUT"
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
                : # no .meta; keep EMPTY_OUTPUT and let callers decide fallback.
            fi
        fi
    else
        # Sentinel doesn't exist (shouldn't happen after wait, but be defensive)
        STATUS="SENTINEL_TIMEOUT"
        EXIT_CODE="124"
        FAILURE_REASON=$(build_failure_reason "$OUTPUT" "$STATUS" "$EXIT_CODE")
    fi

    # Require a .diag file so the generic TIMED_OUT fallback text ("Process timed
    # out (exit code 124)") — which contains "timed out" — does not falsely match
    # the transient-network heuristic.  Real network failures always produce a
    # .diag because the launcher captures the CLI stderr there.
    if [[ "$STATUS" == "FAILED" || "$STATUS" == "TIMED_OUT" || "$STATUS" == "SENTINEL_TIMEOUT" ]] \
        && [[ -f "${OUTPUT}.diag" ]] \
        && is_transient_net_signature "$FAILURE_REASON" \
        && [[ -f "$META" ]]; then
        ORIG_TIMEOUT=""
        while IFS= read -r meta_line || [[ -n "$meta_line" ]]; do
            meta_key="${meta_line%%=*}"
            meta_val="${meta_line#*=}"
            [[ "$meta_key" == "TIMEOUT" ]] && ORIG_TIMEOUT="$meta_val"
        done < "$META"
        case "$ORIG_TIMEOUT" in
            ''|*[!0-9]*) ;;
            *)
                if (( 10#$ORIG_TIMEOUT >= 1 )); then
                    ORIG_TIMEOUT=$((10#$ORIG_TIMEOUT))
                    STATUS="EMPTY_OUTPUT"
                    larch_err "collect-agent-results.sh: transient diagnostic for $(basename "$OUTPUT"); retrying once"
                    RETRY_FILES+=("$OUTPUT")
                    RETRY_INDICES+=("$i")
                    RETRY_TIMEOUTS+=("$ORIG_TIMEOUT")
                fi
                ;;
        esac
    fi

    if [[ "$STATUS" == "OK" ]] && _classify_sentinel_status "$OUTPUT"; then
        STATUS="CURSOR_EMPTY_RESPONSE"
        FAILURE_REASON="cursor narration-only / degraded backend response"
    fi
    RESULTS+=("REVIEWER_FILE=$OUTPUT|TOOL=$TOOL|STATUS=$STATUS|EXIT_CODE=$EXIT_CODE|FAILURE_REASON=$FAILURE_REASON")
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
                cursor:launch-review.sh|codex:launch-review.sh) _expected_launcher="$SCRIPT_DIR/launch-review.sh" ;;
                cursor:*|codex:*) _expected_launcher="$SCRIPT_DIR/launch-review.sh" ;;
                *) mark_retry_metadata_invalid "$IDX" "$ORIG_OUTPUT" "Retry metadata invalid: OUTER_LAUNCHER not canonical launch-review.sh"; continue ;;
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
                        --tool "$META_TOOL" \
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
        # original result so callers do not see a stale successful result when
        # no retry process is launched.
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
                    # F4 fix: retry succeeded — recovered from transient failure.
                    if _classify_sentinel_status "$RETRY_OUTPUT"; then
                        RESULTS[IDX]="REVIEWER_FILE=$RETRY_OUTPUT|TOOL=$TOOL|STATUS=CURSOR_EMPTY_RESPONSE|EXIT_CODE=0|FAILURE_REASON=cursor narration-only / degraded backend response (retry)"
                    else
                        RESULTS[IDX]="REVIEWER_FILE=$RETRY_OUTPUT|TOOL=$TOOL|STATUS=OK|EXIT_CODE=0|FAILURE_REASON="
                    fi
                    rm -f "${ORIG_OUTPUT}.stderr-tail"
                else
                    # Retry also failed.
                    if [[ "$RETRY_EXIT" == "124" ]]; then
                        RETRY_STATUS="TIMED_OUT"
                    elif [[ "$RETRY_EXIT" != "0" ]]; then
                        RETRY_STATUS="FAILED"
                    else
                        RETRY_STATUS="EMPTY_OUTPUT"
                    fi
                    RETRY_REASON=$(build_failure_reason "$RETRY_OUTPUT" "$RETRY_STATUS" "$RETRY_EXIT")
                    RESULTS[IDX]="REVIEWER_FILE=$ORIG_OUTPUT|TOOL=$TOOL|STATUS=EMPTY_OUTPUT|EXIT_CODE=$RETRY_EXIT|FAILURE_REASON=Retry also failed: $RETRY_REASON"
                fi
            else
                # Retry sentinel never appeared.
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
# sanitized diagnostic in FAILURE_REASON. Closes #416.
if [[ "$SUBSTANTIVE_VALIDATION" == "true" ]]; then
    VALIDATOR="$SCRIPT_DIR/validate-research-output.sh"
    VAL_ARGS=()
    if [[ "$VALIDATION_MODE" == "true" ]]; then
        VAL_ARGS+=(--validation-mode)
    fi
    for j in "${!RESULTS[@]}"; do
        entry="${RESULTS[$j]}"
        # Precise field-by-field extraction. Fields 1-5 (REVIEWER_FILE, TOOL,
        # STATUS, EXIT_CODE) never contain '|' by construction (paths are tmpdir
        # paths; tools are registered LARCH_EXTERNAL_TOOLS ids — kept label-safe
        # per the registry contract — or "unknown"; STATUS is a fixed enum;
        # EXIT_CODE is numeric). FAILURE_REASON (field 5) is the
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
            if [[ "$VAL_EXIT" -eq 5 ]]; then
                RESULTS[j]="REVIEWER_FILE=$REVIEWER_FILE|TOOL=$ENTRY_TOOL|STATUS=CURSOR_EMPTY_RESPONSE|EXIT_CODE=0|FAILURE_REASON=$DIAG_SAN"
            else
                RESULTS[j]="REVIEWER_FILE=$REVIEWER_FILE|TOOL=$ENTRY_TOOL|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|NS_RETRY_MODE=substantive|NS_RETRY_REASON=$(derive_ns_retry_reason "$VAL_EXIT" "substantive")|FAILURE_REASON=$DIAG_SAN"
            fi
        fi
    done
fi

# --- 3.6. Structured reviewer validation (opt-in) ---
if [[ "$STRUCTURED_REVIEWER_VALIDATION" == "true" ]]; then
    VALIDATOR="$SCRIPT_DIR/validate-research-output.sh"
    for j in "${!RESULTS[@]}"; do
        entry="${RESULTS[$j]}"
        rf_field="${entry%%|*}"
        REVIEWER_FILE="${rf_field#REVIEWER_FILE=}"
        rest1="${entry#*|}"
        tool_field="${rest1%%|*}"
        ENTRY_TOOL="${tool_field#TOOL=}"
        rest2="${rest1#*|}"
        status_field="${rest2%%|*}"
        ENTRY_STATUS="${status_field#STATUS=}"

        if [[ "$ENTRY_STATUS" != "OK" ]]; then
            RESULTS[j]=$(with_structured_sidecar_field "$entry" "")
            continue
        fi

        case "$ENTRY_TOOL" in
            cursor|codex) STRUCTURED_SIDECAR="${REVIEWER_FILE}.tsv" ;;
            *) STRUCTURED_SIDECAR="${REVIEWER_FILE}.jsonl" ;;
        esac

        DIAG=$("$VALIDATOR" --structured-reviewer-mode --write-structured "$STRUCTURED_SIDECAR" "$REVIEWER_FILE" 2>&1)
        VAL_EXIT=$?
        if [[ "$VAL_EXIT" -eq 0 ]]; then
            RESULTS[j]=$(with_structured_sidecar_field "$entry" "$STRUCTURED_SIDECAR")
        else
            DIAG_SAN=$(printf '%s' "$DIAG" | tr '|\n' '/ ' | tr -s '[:space:]' ' ' | sed 's/^ //; s/ $//' | cut -c1-200)
            RESULTS[j]="REVIEWER_FILE=$REVIEWER_FILE|TOOL=$ENTRY_TOOL|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|NS_RETRY_MODE=structured|NS_RETRY_REASON=$(derive_ns_retry_reason "$VAL_EXIT" "structured")|STRUCTURED_SIDECAR=|FAILURE_REASON=$DIAG_SAN"
        fi
    done
fi

# --- 3.7. Retry NOT_SUBSTANTIVE entries once with a structured-output demand ---
# For each entry downgraded to NOT_SUBSTANTIVE in sections 3.5 or 3.6, preserve
# the reason for the downgrade so the retry can re-run the matching validator.
# Retry metadata reuses the same canonical outer-launcher / CMD_JSON checks as
# the empty-output path before any replay is attempted.
if [[ "$SUBSTANTIVE_VALIDATION" == "true" || "$STRUCTURED_REVIEWER_VALIDATION" == "true" ]]; then
    NS_RETRY_FILES=()
    NS_RETRY_INDICES=()
    NS_RETRY_TIMEOUTS=()
    NS_RETRY_MODES=()

    for j in "${!RESULTS[@]}"; do
        entry="${RESULTS[$j]}"
        rf_field="${entry%%|*}"
        REVIEWER_FILE="${rf_field#REVIEWER_FILE=}"
        rest1="${entry#*|}"
        tool_field="${rest1%%|*}"
        ENTRY_TOOL="${tool_field#TOOL=}"
        rest2="${rest1#*|}"
        status_field="${rest2%%|*}"
        ENTRY_STATUS="${status_field#STATUS=}"
        NS_RETRY_MODE=$(result_field_value "$entry" "NS_RETRY_MODE" || true)

        [[ "$ENTRY_STATUS" == "NOT_SUBSTANTIVE" ]] || continue
        [[ -n "$NS_RETRY_MODE" ]] || continue
        META="${REVIEWER_FILE}.meta"
        [[ -f "$META" ]] || continue
        parse_retry_meta "$META"
        validate_retry_timeout_or_mark "$j" "$REVIEWER_FILE" "$META_TIMEOUT" || continue

        NS_RETRY_FILES+=("$REVIEWER_FILE")
        NS_RETRY_INDICES+=("$j")
        NS_RETRY_TIMEOUTS+=("$META_TIMEOUT")
        NS_RETRY_MODES+=("$NS_RETRY_MODE")
    done

    if [[ ${#NS_RETRY_FILES[@]} -gt 0 ]]; then
        NS_RETRY_SENTINELS=()
        NS_RETRY_LAUNCHED=()
        NS_RETRY_PROMPTS=()
        NS_MAX_RETRY_TIMEOUT=30
        # Structured-output demand prepended to the reviewer prompt on retry.
        NS_STRONG_HEADER="IMPORTANT: Your previous response was not structured correctly. You MUST output findings in the exact format your original prompt requires, or the literal NO_ISSUES_FOUND if no issues exist. Do NOT write narrative, process descriptions, or reading logs. Begin your response directly with the format your prompt demands.

"
        for j in "${!NS_RETRY_FILES[@]}"; do
            ORIG_OUTPUT="${NS_RETRY_FILES[$j]}"
            META="${ORIG_OUTPUT}.meta"
            NS_RETRY_OUTPUT="${ORIG_OUTPUT%.txt}-ns-retry.txt"
            IDX="${NS_RETRY_INDICES[$j]}"
            parse_retry_meta "$META"
            validate_retry_timeout_or_mark "$IDX" "$ORIG_OUTPUT" "$META_TIMEOUT" || continue

            NS_RETRY_WAIT=$(( META_TIMEOUT + 60 ))
            [[ $NS_RETRY_WAIT -gt $NS_MAX_RETRY_TIMEOUT ]] && NS_MAX_RETRY_TIMEOUT=$NS_RETRY_WAIT

            if [[ -n "$META_OUTER_LAUNCHER" || -n "$META_OUTER_LAUNCHER_PROMPT_FILE" || -n "$META_OUTER_LAUNCHER_WORKDIR" ]]; then
                _ns_strong_prompt=$(mktemp "${TMPDIR:-/tmp}/larch-ns-retry-prompt.XXXXXX") || continue
                { printf '%s' "$NS_STRONG_HEADER"; cat "$META_OUTER_LAUNCHER_PROMPT_FILE"; } > "$_ns_strong_prompt" 2>/dev/null || {
                    rm -f "$_ns_strong_prompt"; continue
                }
                launch_outer_retry_or_mark "$IDX" "$ORIG_OUTPUT" "$NS_RETRY_OUTPUT" "$_ns_strong_prompt" "$META_TIMEOUT" "NS_RETRY_LAUNCHED[$j]" "NS_RETRY_SENTINELS" || {
                    rm -f "$_ns_strong_prompt"
                    continue
                }
                NS_RETRY_PROMPTS+=("$_ns_strong_prompt")
                continue
            fi

            launch_cmd_json_retry_or_mark "$IDX" "$ORIG_OUTPUT" "$NS_RETRY_OUTPUT" "NS_RETRY_LAUNCHED[$j]" "NS_RETRY_SENTINELS" || continue
        done

        if [[ ${#NS_RETRY_SENTINELS[@]} -gt 0 ]]; then
            "$SCRIPT_DIR/wait-for-reviewers.sh" --timeout "$NS_MAX_RETRY_TIMEOUT" \
                "${NS_RETRY_SENTINELS[@]}" >/dev/null 2>&1 || true

            VAL_ARGS_NS=()
            [[ "$VALIDATION_MODE" == "true" ]] && VAL_ARGS_NS+=(--validation-mode)

            for j in "${!NS_RETRY_FILES[@]}"; do
                [[ "${NS_RETRY_LAUNCHED[$j]:-0}" == "1" ]] || continue
                ORIG_OUTPUT="${NS_RETRY_FILES[$j]}"
                NS_RETRY_OUTPUT="${ORIG_OUTPUT%.txt}-ns-retry.txt"
                NS_RETRY_SENTINEL="${NS_RETRY_OUTPUT}.done"
                IDX="${NS_RETRY_INDICES[$j]}"
                # Extract before RESULTS[IDX] may be overwritten on retry success.
                _ns_meta_reason=$(result_field_value "${RESULTS[$IDX]}" "NS_RETRY_REASON" || true)
                [[ -z "$_ns_meta_reason" ]] && _ns_meta_reason="UNKNOWN"

                # Write classification reason before any branch-local `continue` so audit bins always see it.
                NS_RETRY_META="${NS_RETRY_OUTPUT}.meta"
                if [[ -f "$NS_RETRY_META" && ! -L "$NS_RETRY_META" ]]; then
                    printf 'NS_RETRY_REASON=%s\n' "$_ns_meta_reason" >> "$NS_RETRY_META" 2>/dev/null || true
                fi

                if [[ -f "$NS_RETRY_SENTINEL" && -s "$NS_RETRY_OUTPUT" ]]; then
                    NS_EXIT=$(cat "$NS_RETRY_SENTINEL" 2>/dev/null || echo "99")
                    case "$NS_EXIT" in ''|*[!0-9]*) NS_EXIT=99 ;; esac
                    if [[ "$NS_EXIT" == "0" ]]; then
                        entry="${RESULTS[$IDX]}"
                        ENTRY_TOOL=$(result_field_value "$entry" "TOOL" || true)
                        NS_RETRY_MODE="${NS_RETRY_MODES[$j]}"
                        if [[ "$NS_RETRY_MODE" == "structured" ]]; then
                            case "$ENTRY_TOOL" in
                                cursor|codex) STRUCTURED_SIDECAR="${NS_RETRY_OUTPUT}.tsv" ;;
                                *) STRUCTURED_SIDECAR="${NS_RETRY_OUTPUT}.jsonl" ;;
                            esac
                            "$SCRIPT_DIR/validate-research-output.sh" \
                                --structured-reviewer-mode --write-structured "$STRUCTURED_SIDECAR" "$NS_RETRY_OUTPUT" >/dev/null 2>&1
                            NS_VAL_EXIT=$?
                            if [[ "$NS_VAL_EXIT" -eq 0 ]]; then
                                if [[ ! -f "$STRUCTURED_SIDECAR" ]]; then
                                    larch_err "collect-agent-results.sh: structured NS retry: missing structured retry sidecar after validation; leaving STATUS=NOT_SUBSTANTIVE"
                                    continue
                                fi
                                if ! preserve_and_publish_ns_retry "$ORIG_OUTPUT" "$NS_RETRY_OUTPUT" "structured NS retry"; then
                                    continue
                                fi
                                _ns_sidecar_ext="${STRUCTURED_SIDECAR##*.}"
                                _ns_new_sidecar="${ORIG_OUTPUT}.${_ns_sidecar_ext}"
                                if cp "$STRUCTURED_SIDECAR" "$_ns_new_sidecar" 2>/dev/null; then
                                    STRUCTURED_SIDECAR="$_ns_new_sidecar"
                                else
                                    larch_err "collect-agent-results.sh: structured NS retry: failed to publish structured sidecar to $_ns_new_sidecar; keeping retry sidecar path"
                                fi
                                if _classify_sentinel_status "$ORIG_OUTPUT"; then
                                    RESULTS[IDX]="REVIEWER_FILE=$ORIG_OUTPUT|TOOL=$ENTRY_TOOL|STATUS=CURSOR_EMPTY_RESPONSE|EXIT_CODE=0|FAILURE_REASON=cursor narration-only / degraded backend response (structured ns-retry)"
                                    rm -f "${ORIG_OUTPUT}.stderr-tail"
                                else
                                    RESULTS[IDX]="REVIEWER_FILE=$ORIG_OUTPUT|TOOL=$ENTRY_TOOL|STATUS=OK|EXIT_CODE=0|STRUCTURED_SIDECAR=$STRUCTURED_SIDECAR|FAILURE_REASON="
                                    rm -f "${ORIG_OUTPUT}.stderr-tail"
                                fi
                            fi
                        else
                            "$SCRIPT_DIR/validate-research-output.sh" \
                                "${VAL_ARGS_NS[@]+"${VAL_ARGS_NS[@]}"}" "$NS_RETRY_OUTPUT" >/dev/null 2>&1
                            NS_VAL_EXIT=$?
                            if [[ "$NS_VAL_EXIT" -eq 0 ]]; then
                                if ! preserve_and_publish_ns_retry "$ORIG_OUTPUT" "$NS_RETRY_OUTPUT" "substantive NS retry"; then
                                    continue
                                fi
                                if _classify_sentinel_status "$ORIG_OUTPUT"; then
                                    RESULTS[IDX]="REVIEWER_FILE=$ORIG_OUTPUT|TOOL=$ENTRY_TOOL|STATUS=CURSOR_EMPTY_RESPONSE|EXIT_CODE=0|FAILURE_REASON=cursor narration-only / degraded backend response (substantive ns-retry)"
                                    rm -f "${ORIG_OUTPUT}.stderr-tail"
                                else
                                    RESULTS[IDX]="REVIEWER_FILE=$ORIG_OUTPUT|TOOL=$ENTRY_TOOL|STATUS=OK|EXIT_CODE=0|FAILURE_REASON="
                                    rm -f "${ORIG_OUTPUT}.stderr-tail"
                                fi
                            fi
                        fi
                    fi
                fi
            done
        fi
        rm -f "${NS_RETRY_PROMPTS[@]+"${NS_RETRY_PROMPTS[@]}"}"
    fi
fi

# --- 3.8 Emit failed-agent stderr tails (FD 2 only; stdout KV contract unchanged) ---
# Skipped under --summary-only (dispatch-with-waterfall phase collects) so transient
# phase-1 failures do not emit tails before a later phase succeeds.
if [[ "$SUMMARY_ONLY" != "true" ]]; then
_failed_stderr_sig_map=$(mktemp "${TMPDIR:-/tmp}/larch-collector-stderr-sig.XXXXXX") || exit 1
_cleanup_collector_dedup_tail_file() {
    [[ "${_dedup_tail_file:-}" == *"/larch-launch-stderr-tail."* ]] && rm -f "$_dedup_tail_file"
}
_emit_collector_stderr_tail_file() {
    local tail_file="$1"
    [[ -s "$tail_file" ]] || return 1
    larch_err '--- failed agent stderr tail ---'
    while IFS= read -r _tail_line || [[ -n "$_tail_line" ]]; do
        [[ -n "$_tail_line" ]] || continue
        if declare -f sanitize_diagnostic_line &>/dev/null; then
            larch_err "$(printf '%s' "$_tail_line" | sanitize_diagnostic_line)"
        else
            larch_err "$_tail_line"
        fi
    done <"$tail_file"
    larch_err '--- end failed agent stderr tail ---'
}
_collector_stderr_tail_candidates() {
    local reviewer_file="$1"
    printf '%s\n' "$reviewer_file"
    case "$reviewer_file" in
        *-phase3.txt)
            printf '%s\n' "${reviewer_file%-phase3.txt}-phase2.txt"
            printf '%s\n' "${reviewer_file%-phase3.txt}.txt"
            ;;
        *-phase2.txt)
            printf '%s\n' "${reviewer_file%-phase2.txt}.txt"
            ;;
        *-phase1.txt)
            printf '%s\n' "${reviewer_file%-phase1.txt}.txt"
            ;;
    esac
}
_resolve_collector_stderr_tail_file() {
    local reviewer_file="$1" _retry_tail _ns_retry_tail _candidate _launch_stderr _tmp_tail
    _retry_tail="${reviewer_file%.txt}-retry.txt.stderr-tail"
    if [[ -s "$_retry_tail" ]]; then
        printf '%s' "$_retry_tail"
        return 0
    fi
    _ns_retry_tail="${reviewer_file%.txt}-ns-retry.txt.stderr-tail"
    if [[ -s "$_ns_retry_tail" ]]; then
        printf '%s' "$_ns_retry_tail"
        return 0
    fi
    while IFS= read -r _candidate || [[ -n "$_candidate" ]]; do
        [[ -n "$_candidate" ]] || continue
        if [[ -s "${_candidate}.stderr-tail" ]]; then
            printf '%s' "${_candidate}.stderr-tail"
            return 0
        fi
    done < <(_collector_stderr_tail_candidates "$reviewer_file")
    while IFS= read -r _candidate || [[ -n "$_candidate" ]]; do
        [[ -n "$_candidate" ]] || continue
        if [[ -s "${_candidate}.launch-stderr" ]]; then
            _tmp_tail=$(mktemp "${TMPDIR:-/tmp}/larch-launch-stderr-tail.XXXXXX") || return 1
            if render_failed_agent_stderr_tail "${_candidate}.launch-stderr" >"$_tmp_tail" 2>/dev/null && [[ -s "$_tmp_tail" ]]; then
                printf '%s' "$_tmp_tail"
                return 0
            fi
            rm -f "$_tmp_tail"
        fi
    done < <(_collector_stderr_tail_candidates "$reviewer_file")
    return 1
}
for _dedup_result in "${RESULTS[@]}"; do
    _dedup_status=""
    _dedup_tool=""
    _dedup_reviewer=""
    _dedup_rest="$_dedup_result"
    while [[ -n "$_dedup_rest" ]]; do
        if [[ "$_dedup_rest" == *"|"* ]]; then
            _dedup_field="${_dedup_rest%%|*}"
            _dedup_rest="${_dedup_rest#*|}"
        else
            _dedup_field="$_dedup_rest"
            _dedup_rest=""
        fi
        case "$_dedup_field" in
            STATUS=*) _dedup_status="${_dedup_field#STATUS=}" ;;
            TOOL=*) _dedup_tool="${_dedup_field#TOOL=}" ;;
            REVIEWER_FILE=*) _dedup_reviewer="${_dedup_field#REVIEWER_FILE=}" ;;
        esac
    done
    case "$_dedup_status" in
        OK|cap_hit|'') continue ;;
    esac
    [[ -n "$_dedup_reviewer" ]] || continue
    _dedup_tail_file=""
    _dedup_tail_file=$(_resolve_collector_stderr_tail_file "$_dedup_reviewer" || true)
    [[ -n "$_dedup_tail_file" && -s "$_dedup_tail_file" ]] || continue
    _dedup_sig=$(failed_agent_stderr_signature "$_dedup_tail_file" || true)
    if [[ -z "$_dedup_sig" ]]; then
        _emit_collector_stderr_tail_file "$_dedup_tail_file" || true
        _cleanup_collector_dedup_tail_file
        continue
    fi
    _dedup_base=$(basename "$_dedup_reviewer")
    _dedup_tab=$'\t'
    if command grep -Fq "${_dedup_sig}${_dedup_tab}" "$_failed_stderr_sig_map" 2>/dev/null; then
        _dedup_first=$(command grep -F "${_dedup_sig}${_dedup_tab}" "$_failed_stderr_sig_map" | head -n 1)
        _dedup_first_base="${_dedup_first#*"${_dedup_tab}"}"
        larch_err "↩ ${_dedup_tool:-unknown} ${_dedup_base}: identical failure to ${_dedup_first_base} (root-cause sig ${_dedup_sig}); stderr tail suppressed"
        _cleanup_collector_dedup_tail_file
        continue
    fi
    printf '%s\t%s\n' "$_dedup_sig" "$_dedup_base" >>"$_failed_stderr_sig_map"
    _emit_collector_stderr_tail_file "$_dedup_tail_file" || true
    _cleanup_collector_dedup_tail_file
done
rm -f "$_failed_stderr_sig_map"
fi

# --- 4. Emit structured results ---
emit_summary_result() {
    local entry="$1"
    local rest="$entry"
    local field=""
    local emitted=0
    while [[ -n "$rest" && $emitted -lt 5 ]]; do
        if [[ "$rest" == *"|"* ]]; then
            field="${rest%%|*}"
            rest="${rest#*|}"
        else
            field="$rest"
            rest=""
        fi
        case "$field" in
            REVIEWER_FILE=*|TOOL=*|STATUS=*|EXIT_CODE=*)
                emit "$field"
                emitted=$((emitted + 1))
                ;;
        esac
    done
}

FIRST=true
for result in "${RESULTS[@]}"; do
    if [[ "$FIRST" == "true" ]]; then
        FIRST=false
    else
        emit ""
    fi
    if [[ "$SUMMARY_ONLY" == "true" ]]; then
        emit_summary_result "$result"
        continue
    fi
    # Convert pipe-delimited to newlines
    result=$(with_structured_sidecar_field "$result" "")
    while IFS= read -r field || [[ -n "$field" ]]; do
        emit "$field"
    done < <(printf '%s' "$result" | tr '|' '\n')
done
