#!/usr/bin/env bash
# read-result-env.sh — safely convert result-env KVs into a sourceable allowlisted env.
# Delegates allowlist filtering, symlink refusal, and CR/LF rejection to
# phase_driver_read_result_env (skills/design/scripts/lib-phase-driver.sh);
# this script adds: fallback-input logic, WARN/ERROR stdout replay, and
# single-quote encoding of values for sourceable output.

set -euo pipefail

_RRE_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=skills/design/scripts/lib-phase-driver.sh
source "$_RRE_SCRIPT_DIR/../skills/design/scripts/lib-phase-driver.sh"

usage() {
    printf '%s\n' 'usage: read-result-env.sh --input PATH [--fallback-input PATH] --allow KEY ... --output PATH' >&2
}

quote_single() {
    local value="$1"
    local out=""
    local prefix=""
    while :; do
        case "$value" in
            *"'"*)
                prefix="${value%%\'*}"
                out="${out}${prefix}'\"'\"'"
                value="${value#*\'}"
                ;;
            *)
                out="${out}${value}"
                break
                ;;
        esac
    done
    printf "'%s'" "$out"
}

valid_var_name() {
    case "$1" in
        ''|[0-9]*|*[!A-Za-z0-9_]*) return 1 ;;
        *) return 0 ;;
    esac
}

replay_warn_error() {
    local input_path="$1"
    local line key value
    while IFS= read -r line || [ -n "$line" ]; do
        [ -z "$line" ] && continue
        case "$line" in
            *=*) ;;
            *) continue ;;
        esac
        key="${line%%=*}"
        value="${line#*=}"
        case "$key" in
            WARN) printf '%s\n' "WARN=$value" ;;
            ERROR) printf '%s\n' "ERROR=$value" ;;
        esac
    done <"$input_path"
}

INPUT_PATH=""
FALLBACK_INPUT=""
OUTPUT_PATH=""
ALLOW_KEYS_ARRAY=()

while [ "$#" -gt 0 ]; do
    case "$1" in
        --input)
            [ "$#" -ge 2 ] || { usage; exit 1; }
            INPUT_PATH="$2"
            shift 2
            ;;
        --fallback-input)
            [ "$#" -ge 2 ] || { usage; exit 1; }
            FALLBACK_INPUT="$2"
            shift 2
            ;;
        --allow)
            [ "$#" -ge 2 ] || { usage; exit 1; }
            valid_var_name "$2" || { usage; exit 1; }
            ALLOW_KEYS_ARRAY+=("$2")
            shift 2
            ;;
        --output)
            [ "$#" -ge 2 ] || { usage; exit 1; }
            OUTPUT_PATH="$2"
            shift 2
            ;;
        *)
            usage
            exit 1
            ;;
    esac
done

[ -n "$INPUT_PATH" ] || { usage; exit 1; }
[ -n "$OUTPUT_PATH" ] || { usage; exit 1; }

SOURCE_PATH=""
PRIMARY_KIND="regular"
if [ -L "$INPUT_PATH" ]; then
    PRIMARY_KIND="symlink"
elif [ ! -e "$INPUT_PATH" ]; then
    PRIMARY_KIND="missing"
elif [ ! -f "$INPUT_PATH" ]; then
    PRIMARY_KIND="nonregular"
fi

case "$PRIMARY_KIND" in
    regular)
        SOURCE_PATH="$INPUT_PATH"
        ;;
    symlink|missing|nonregular)
        if [ -z "$FALLBACK_INPUT" ]; then
            exit 1
        fi
        if [ "$PRIMARY_KIND" = symlink ]; then
            case "$INPUT_PATH" in
                *.design-init-runparams-result.env)
                    printf '%s\n' '**⚠ Step 0b: design-init-runparams result env is a symlink; refusing to source**'
                    ;;
                *)
                    printf '%s\n' "WARN=read-result-env input is a symlink; refusing primary path: $INPUT_PATH"
                    ;;
            esac
        fi
        if [ -L "$FALLBACK_INPUT" ] || [ ! -f "$FALLBACK_INPUT" ]; then
            exit 1
        fi
        SOURCE_PATH="$FALLBACK_INPUT"
        ;;
esac

out_dir=$(dirname "$OUTPUT_PATH") || exit 1
out_base=$(basename "$OUTPUT_PATH") || exit 1
[ -d "$out_dir" ] || exit 1
output_tmp=$(mktemp "${out_dir}/.${out_base}.XXXXXX") || exit 1
cleanup_tmp=true
trap 'if [ "${cleanup_tmp:-false}" = true ]; then rm -f "$output_tmp"; fi' EXIT HUP INT TERM

# Replay WARN/ERROR lines to stdout before allowlisted KV parsing.
replay_warn_error "$SOURCE_PATH"

# Delegate KV parsing to phase_driver_read_result_env, then quote_single-encode
# each value to produce sourceable output.
_rre_write_allowlisted_pairs() {
    local _source="$1"
    : >"$output_tmp" || return 1
    while IFS= read -r _rre_pair || [ -n "$_rre_pair" ]; do
        _rre_key="${_rre_pair%%=*}"
        _rre_value="${_rre_pair#*=}"
        printf '%s=' "$_rre_key" >>"$output_tmp" || return 1
        quote_single "$_rre_value" >>"$output_tmp" || return 1
        printf '\n' >>"$output_tmp" || return 1
    done < <(phase_driver_read_result_env "$_source" "${ALLOW_KEYS_ARRAY[@]}")
    return 0
}

_rre_write_allowlisted_pairs "$SOURCE_PATH" || exit 1
if [ ! -s "$output_tmp" ] && [ "$PRIMARY_KIND" = "regular" ] && [ -n "$FALLBACK_INPUT" ] && [ -f "$FALLBACK_INPUT" ] && [ ! -L "$FALLBACK_INPUT" ]; then
    SOURCE_PATH="$FALLBACK_INPUT"
    replay_warn_error "$SOURCE_PATH"
    _rre_write_allowlisted_pairs "$SOURCE_PATH" || exit 1
fi

if ! mv "$output_tmp" "$OUTPUT_PATH"; then
    exit 1
fi
cleanup_tmp=false
trap - EXIT HUP INT TERM
exit 0
