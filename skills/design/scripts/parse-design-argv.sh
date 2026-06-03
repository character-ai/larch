#!/usr/bin/env bash
# parse-design-argv.sh — /design Step 0-pre public argv parser.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$REPO_ROOT/scripts/lib-quiet.sh"
LARCH_QUIET_DISABLE=1 larch_quiet_init

validation_error() {
    local token="$1"
    case "$token" in
        *$'\n'* | *$'\r'*) token='newline-in-value' ;;
    esac
    printf '%s\n' "VALIDATION_ERROR=$token"
    exit 3
}

assert_safe_kv_value() {
    case "$1" in
        *$'\n'* | *$'\r'*) validation_error 'newline-in-value' ;;
    esac
}

hard_requested=false
partition_requested=false
brainstorm_requested=false
manual_requested=false
no_dedup_requested=false
run_id=""
first_positional=""
positional_value=""

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
        --manual | -m)
            manual_requested=true
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
        -*)
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

printf '%s\n' "HARD_REQUESTED=$hard_requested"
printf '%s\n' "PARTITION_REQUESTED=$partition_requested"
printf '%s\n' "BRAINSTORM_REQUESTED=$brainstorm_requested"
printf '%s\n' "MANUAL_REQUESTED=$manual_requested"
printf '%s\n' "NO_DEDUP_REQUESTED=$no_dedup_requested"
printf '%s\n' "RUN_ID=$run_id"
printf '%s\n' "POSITIONAL_KIND=$positional_kind"
printf '%s\n' "POSITIONAL_VALUE=$positional_value"
