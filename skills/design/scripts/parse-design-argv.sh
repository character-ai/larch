#!/usr/bin/env bash
# parse-design-argv.sh — /design Step 0-pre public argv parser.

set -euo pipefail

_output_path=""

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

write_output_file() {
    local tmp=""
    local out_dir=""
    local out_base=""
    [ -n "${_output_path:-}" ] || return 0
    out_dir=$(dirname "$_output_path") || return 1
    out_base=$(basename "$_output_path") || return 1
    [ -d "$out_dir" ] || return 1
    tmp=$(mktemp "${out_dir}/.${out_base}.XXXXXX") || return 1
    if ! write_output_body "$tmp"; then
        rm -f "$tmp"
        return 1
    fi
    if ! mv "$tmp" "$_output_path"; then
        rm -f "$tmp"
        return 1
    fi
}

write_output_body() {
    local output_tmp="$1"
    : >"$output_tmp" || return 1
    if [ -n "${VALIDATION_ERROR:-}" ]; then
        printf 'VALIDATION_ERROR=' >>"$output_tmp" || return 1
        quote_single "$VALIDATION_ERROR" >>"$output_tmp" || return 1
        printf '\n' >>"$output_tmp" || return 1
        return 0
    fi
    printf 'hard_requested=' >>"$output_tmp" || return 1
    quote_single "$hard_requested" >>"$output_tmp" || return 1
    printf '\npartition_requested=' >>"$output_tmp" || return 1
    quote_single "$partition_requested" >>"$output_tmp" || return 1
    printf '\nbrainstorm_requested=' >>"$output_tmp" || return 1
    quote_single "$brainstorm_requested" >>"$output_tmp" || return 1
    printf '\napprove_requested=' >>"$output_tmp" || return 1
    quote_single "$approve_requested" >>"$output_tmp" || return 1
    printf '\nskip_approve_requested=' >>"$output_tmp" || return 1
    quote_single "$skip_approve_requested" >>"$output_tmp" || return 1
    printf '\nno_dedup_requested=' >>"$output_tmp" || return 1
    quote_single "$no_dedup_requested" >>"$output_tmp" || return 1
    printf '\nrun_id=' >>"$output_tmp" || return 1
    quote_single "$run_id" >>"$output_tmp" || return 1
    printf '\nPOSITIONAL_KIND=' >>"$output_tmp" || return 1
    quote_single "$positional_kind" >>"$output_tmp" || return 1
    printf '\nPOSITIONAL_VALUE=' >>"$output_tmp" || return 1
    quote_single "$positional_value" >>"$output_tmp" || return 1
    printf '\n' >>"$output_tmp" || return 1
}

validation_error() {
    local token="$1"
    case "$token" in
        *$'\n'* | *$'\r'*) token='newline-in-value' ;;
    esac
    VALIDATION_ERROR="$token"
    if ! write_output_file; then
        exit 1
    fi
    printf '%s\n' "VALIDATION_ERROR=$token"
    exit 3
}

assert_safe_kv_value() {
    case "$1" in
        *$'\n'* | *$'\r'*) validation_error 'newline-in-value' ;;
    esac
}

VALIDATION_ERROR=""
case "${1:-}" in
    --output)
        shift
        [ "${1:-}" ] || validation_error "--output"
        _output_path="$1"
        shift
        ;;
esac

hard_requested=false
partition_requested=false
brainstorm_requested=false
approve_requested=false
skip_approve_requested=false
no_dedup_requested=false
run_id=""
first_positional=""
positional_value=""
positional_kind=none

while [ "$#" -gt 0 ]; do
    case "$1" in
        --)
            shift
            break
            ;;
        --hard)
            if [ "$hard_requested" = true ]; then
                validation_error '--hard'
            fi
            hard_requested=true
            shift
            ;;
        -p | --partition)
            partition_requested=true
            shift
            ;;
        --brainstorm)
            brainstorm_requested=true
            shift
            ;;
        --per-round-approval)
            if [ "$approve_requested" = true ]; then
                validation_error '--per-round-approval'
            fi
            approve_requested=true
            shift
            ;;
        --skip-approve | -s)
            if [ "$skip_approve_requested" = true ]; then
                validation_error '--skip-approve'
            fi
            skip_approve_requested=true
            shift
            ;;
        --no-dedup)
            no_dedup_requested=true
            shift
            ;;
        --run-id)
            if [ "$#" -lt 2 ]; then
                validation_error '--run-id'
            fi
            run_id="$2"
            shift 2
            ;;
        --*)
            validation_error "$1"
            ;;
        -* )
            validation_error "$1"
            ;;
        *)
            break
            ;;
    esac
done

if [ "$#" -gt 0 ]; then
    first_positional="$1"
    if [[ "$first_positional" =~ ^[0-9]+$ ]]; then
        positional_value="$first_positional"
    else
        positional_value="$1"
        shift
        while [ "$#" -gt 0 ]; do
            positional_value="$positional_value $1"
            shift
        done
    fi
fi

if [ -z "$first_positional" ]; then
    positional_kind=none
    positional_value=""
elif [[ "$first_positional" =~ ^[0-9]+$ ]]; then
    positional_kind=issue
else
    positional_kind=verbal
fi

assert_safe_kv_value "$run_id"
assert_safe_kv_value "$positional_value"

if ! write_output_file; then
    exit 1
fi

printf '%s\n' "HARD_REQUESTED=$hard_requested"
printf '%s\n' "PARTITION_REQUESTED=$partition_requested"
printf '%s\n' "BRAINSTORM_REQUESTED=$brainstorm_requested"
printf '%s\n' "APPROVE_REQUESTED=$approve_requested"
printf '%s\n' "SKIP_APPROVE_REQUESTED=$skip_approve_requested"
printf '%s\n' "NO_DEDUP_REQUESTED=$no_dedup_requested"
printf '%s\n' "RUN_ID=$run_id"
printf '%s\n' "POSITIONAL_KIND=$positional_kind"
printf '%s\n' "POSITIONAL_VALUE=$positional_value"
