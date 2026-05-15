#!/usr/bin/env bash
# token-ledger.sh — Session-scoped JSONL token ledger for /implement.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

SCRIPT_NAME=${0##*/}

warn() {
    larch_err "$SCRIPT_NAME: WARNING: $*"
}

tmp_root() {
    local root="${TMPDIR:-/tmp}"
    (cd "$root" 2>/dev/null && pwd -P) || return 1
}

sha256_hex() {
    if command -v shasum >/dev/null 2>&1; then
        LC_ALL=C shasum -a 256 | awk '{print $1}'
    else
        sha256sum | awk '{print $1}'
    fi
}

resolve_session_id() {
    if [[ -n "${LARCH_TOKEN_SESSION_ID:-}" ]]; then
        printf '%s' "$LARCH_TOKEN_SESSION_ID"
        return 0
    fi
    if [[ -n "${IMPLEMENT_TMPDIR:-}" && -s "$IMPLEMENT_TMPDIR/session-id" ]]; then
        tr -d '\r\n' < "$IMPLEMENT_TMPDIR/session-id"
        return 0
    fi
    pwd -P | sha256_hex
}

validate_under_tmp() {
    local raw="$1"
    local root parent resolved parent_dir base
    root=$(tmp_root) || {
        warn "cannot canonicalize TMPDIR"
        return 1
    }
    if [[ -z "$raw" ]]; then
        warn "--ledger requires a non-empty path"
        return 1
    fi
    case "$raw" in
        */../*|../*|*/..|..) warn "--ledger must not contain '..': $raw"; return 1 ;;
    esac
    if [[ "$raw" = /* ]]; then
        parent="$raw"
    else
        parent="$root/$raw"
    fi
    parent_dir=$(dirname "$parent")
    base=$(basename "$parent")
    mkdir -p "$parent_dir" 2>/dev/null || {
        warn "cannot create ledger parent: $parent_dir"
        return 1
    }
    resolved=$(cd "$parent_dir" 2>/dev/null && pwd -P) || {
        warn "cannot canonicalize ledger parent: $parent_dir"
        return 1
    }
    if [[ "$resolved" != "$root" && "$resolved" != "$root"/* ]]; then
        warn "--ledger must resolve under ${TMPDIR:-/tmp}: $raw"
        return 1
    fi
    printf '%s/%s' "$resolved" "$base"
}

resolve_ledger_path() {
    local override="$1"
    local id slug canon_root
    if [[ -n "$override" ]]; then
        validate_under_tmp "$override"
        return
    fi
    if [[ -n "${LARCH_TOKEN_LEDGER:-}" ]]; then
        local validated_token_ledger
        if validated_token_ledger=$(validate_under_tmp "${LARCH_TOKEN_LEDGER}" 2>/dev/null); then
            printf '%s' "$validated_token_ledger"
            return
        fi
        warn "LARCH_TOKEN_LEDGER not under ${TMPDIR:-/tmp}: ${LARCH_TOKEN_LEDGER}"
    fi
    id=$(resolve_session_id)
    slug=$(printf '%s' "$id" | sha256_hex)
    if [[ -n "${IMPLEMENT_TMPDIR:-}" && -d "$IMPLEMENT_TMPDIR" ]]; then
        canon_root=$(cd "$IMPLEMENT_TMPDIR" 2>/dev/null && pwd -P) || true
        if [[ -n "$canon_root" ]]; then
            printf '%s/larch-tokens-%s.jsonl' "$canon_root" "$slug"
            return
        fi
    fi
    if [[ -n "${SESSION_ENV_PATH:-}" && -d "$(dirname "$SESSION_ENV_PATH")" ]]; then
        canon_root=$(cd "$(dirname "$SESSION_ENV_PATH")" 2>/dev/null && pwd -P) || true
        if [[ -n "$canon_root" ]]; then
            printf '%s/larch-tokens-%s.jsonl' "$canon_root" "$slug"
            return
        fi
    fi
    warn "no per-run ledger root set; expected one of --ledger, LARCH_TOKEN_LEDGER, IMPLEMENT_TMPDIR, or SESSION_ENV_PATH"
    return 1
}

ensure_ledger() {
    local ledger="$1"
    local parent
    parent=$(dirname "$ledger")
    mkdir -p "$parent" 2>/dev/null || return 1
    if [[ ! -e "$ledger" ]]; then
        : > "$ledger" || return 1
    fi
    chmod 600 "$ledger" 2>/dev/null || true
}

append_json() {
    local ledger="$1"
    local json="$2"
    ensure_ledger "$ledger" || return 1
    printf '%s\n' "$json" >> "$ledger"
    chmod 600 "$ledger" 2>/dev/null || true
}

timestamp_utc() {
    date -u '+%Y-%m-%dT%H:%M:%SZ'
}

is_uint() {
    [[ "$1" =~ ^[0-9]+$ ]]
}

cmd_mark() {
    local ledger="$1"
    shift
    local step="${1:-}"
    [[ -n "$step" ]] || { warn "mark requires <step-name>"; return 1; }
    command -v jq >/dev/null 2>&1 || { warn "jq not found"; return 1; }
    local ts json
    ts=$(timestamp_utc)
    json=$(jq -cn --arg type mark --arg step "$step" --arg ts "$ts" \
        '$ARGS.named')
    append_json "$ledger" "$json"
}

cmd_record_vendor() {
    local ledger="$1"
    shift
    local vendor="${1:-}"
    shift || true
    [[ -n "$vendor" ]] || { warn "record-vendor requires <vendor>"; return 1; }
    command -v jq >/dev/null 2>&1 || { warn "jq not found"; return 1; }

    local input=0 output=0 cache_read=0 cache_create=0 total=0 raw="" kv key value
    for kv in "$@"; do
        key=${kv%%=*}
        value=${kv#*=}
        if [[ "$key" == "$kv" ]]; then
            warn "record-vendor argument must be key=value: $kv"
            return 1
        fi
        case "$key" in
            input|output|cache_read|cache_create|total)
                is_uint "$value" || { warn "$key must be a non-negative integer"; return 1; }
                printf -v "$key" '%s' "$value"
                ;;
            raw)
                raw="$value"
                ;;
            *)
                warn "unknown record-vendor key: $key"
                return 1
                ;;
        esac
    done

    local ts json
    ts=$(timestamp_utc)
    json=$(jq -cn \
        --arg type vendor \
        --arg vendor "$vendor" \
        --arg input "$input" \
        --arg output "$output" \
        --arg cache_read "$cache_read" \
        --arg cache_create "$cache_create" \
        --arg total "$total" \
        --arg raw "$raw" \
        --arg ts "$ts" \
        '$ARGS.named
         | .input |= tonumber
         | .output |= tonumber
         | .cache_read |= tonumber
         | .cache_create |= tonumber
         | .total |= tonumber')
    append_json "$ledger" "$json"
}

cmd_dump() {
    local ledger="$1"
    emit "$ledger"
    [[ -s "$ledger" ]] && emit "$(cat "$ledger")"
}

main() {
    local ledger_override="" ledger cmd
    # Strip every `--ledger PATH` pair from anywhere in argv so callers can put
    # the override before the subcommand, immediately after it, or at the tail
    # (`token-ledger.sh mark "Step 2" --ledger /tmp/x.jsonl` is now equivalent
    # to `token-ledger.sh --ledger /tmp/x.jsonl mark "Step 2"`). The pre-pass
    # avoids the prior position-sensitive parser that silently dropped tail
    # overrides on `mark` and produced "unknown record-vendor key: --ledger"
    # warnings on `record-vendor`. Last `--ledger` wins if supplied multiple
    # times — operators should not do that, but the parser stays well-defined.
    local -a remaining=()
    local i
    i=1
    while (( i <= $# )); do
        local arg="${!i}"
        if [[ "$arg" == "--ledger" ]]; then
            local next_i=$(( i + 1 ))
            if (( next_i > $# )); then
                warn "--ledger requires a value"
                return 1
            fi
            ledger_override="${!next_i}"
            i=$(( next_i + 1 ))
        else
            remaining+=("$arg")
            i=$(( i + 1 ))
        fi
    done
    set -- "${remaining[@]}"
    cmd="${1:-}"
    shift || true
    ledger=$(resolve_ledger_path "$ledger_override") || return 1
    case "$cmd" in
        mark) cmd_mark "$ledger" "$@" ;;
        record-vendor) cmd_record_vendor "$ledger" "$@" ;;
        dump) cmd_dump "$ledger" ;;
        *) warn "usage: token-ledger.sh [--ledger PATH] mark <step> | record-vendor <vendor> [key=value ...] | dump"; return 1 ;;
    esac
}

main "$@" || true
exit 0
