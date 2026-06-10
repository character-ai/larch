#!/usr/bin/env bash
# read-result-env.sh — safely convert result-env KVs into a sourceable allowlisted env.

set -euo pipefail

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

is_allowed_key() {
    local key="$1"
    local allowed=""
    while IFS= read -r allowed || [ -n "$allowed" ]; do
        [ -z "$allowed" ] && continue
        [ "$key" = "$allowed" ] && return 0
    done <<EOF_ALLOW
$ALLOW_KEYS
EOF_ALLOW
    return 1
}

parse_env_file() {
    local input_path="$1"
    local output_tmp="$2"
    local line=""
    local key=""
    local value=""
    : >"$output_tmp" || return 1
    while IFS= read -r line || [ -n "$line" ]; do
        [ -z "$line" ] && continue
        case "$line" in
            *=*) ;;
            *) return 1 ;;
        esac
        key="${line%%=*}"
        value="${line#*=}"
        case "$value" in
            *$'\r'*) return 1 ;;
        esac
        case "$key" in
            WARN) printf '%s\n' "WARN=$value" ;;
            ERROR) printf '%s\n' "ERROR=$value" ;;
            *)
                if is_allowed_key "$key"; then
                    printf '%s=' "$key" >>"$output_tmp" || return 1
                    quote_single "$value" >>"$output_tmp" || return 1
                    printf '\n' >>"$output_tmp" || return 1
                fi
                ;;
        esac
    done <"$input_path"
}

INPUT_PATH=""
FALLBACK_INPUT=""
OUTPUT_PATH=""
ALLOW_KEYS=""

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
            ALLOW_KEYS="${ALLOW_KEYS}${ALLOW_KEYS:+
}$2"
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

if ! parse_env_file "$SOURCE_PATH" "$output_tmp"; then
    exit 1
fi
if ! mv "$output_tmp" "$OUTPUT_PATH"; then
    exit 1
fi
cleanup_tmp=false
trap - EXIT HUP INT TERM
exit 0
