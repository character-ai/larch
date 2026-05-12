#!/usr/bin/env bash
# lib-larch-log.sh — shared helpers for scripts/larch-log.sh.

set -euo pipefail

LARCH_LOG_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
LARCH_LOG_REPO_ROOT="$(cd "$LARCH_LOG_LIB_DIR/.." && pwd -P)"

# shellcheck source=scripts/larch-log-batches.sh
# shellcheck disable=SC1091
source "$LARCH_LOG_LIB_DIR/larch-log-batches.sh"

larch_log_fail() {
    local code="$1"
    local message="$2"
    echo "LOG_WRITTEN=false"
    echo "LOG_PATH="
    echo "BYTES=0"
    echo "SHA256="
    echo "COMMIT_SHA="
    echo "UNCHANGED=false"
    echo "ERROR=$message"
    exit "$code"
}

larch_log_validate_slug() {
    local kind="$1"
    local value="$2"
    case "$value" in
        ""|*[!A-Za-z0-9._-]*|.*|*..*|*/*|*\\*) larch_log_fail 1 "invalid $kind: $value" ;;
    esac
}

larch_log_root() {
    if [ -n "${LARCH_LOG_ROOT:-}" ]; then
        printf '%s\n' "$LARCH_LOG_ROOT"
    else
        printf '%s/larch-logs\n' "$LARCH_LOG_REPO_ROOT"
    fi
}

larch_log_run_dir() {
    local skill="$1"
    local run_id="$2"
    printf '%s/%s/%s\n' "$(larch_log_root)" "$skill" "$run_id"
}

larch_log_batch_path() {
    local skill="$1"
    local run_id="$2"
    local batch="$3"
    local ext
    ext="$(larch_log_batch_extension "$batch")" || larch_log_fail 1 "unknown batch: $batch"
    printf '%s/%s%s\n' "$(larch_log_run_dir "$skill" "$run_id")" "$batch" "$ext"
}

larch_log_sha256() {
    local file="$1"
    if command -v shasum >/dev/null 2>&1; then
        LC_ALL=C shasum -a 256 "$file" | awk '{ print $1 }'
    else
        LC_ALL=C sha256sum "$file" | awk '{ print $1 }'
    fi
}

larch_log_bytes() {
    wc -c < "$1" | tr -d ' '
}

larch_log_redact_file() {
    local input="$1"
    local output="$2"
    local redact_tmp="$LARCH_LOG_LIB_DIR/redact-tmpdir-paths.sh"
    local redact_secrets="$LARCH_LOG_LIB_DIR/redact-secrets.sh"
    [ -x "$redact_tmp" ] || larch_log_fail 2 "redaction helper missing: $redact_tmp"
    [ -x "$redact_secrets" ] || larch_log_fail 2 "redaction helper missing: $redact_secrets"
    "$redact_tmp" < "$input" | "$redact_secrets" > "$output" || larch_log_fail 2 "redaction failed"
}

larch_log_validate_batch_payload() {
    local batch="$1"
    local file="$2"
    local sanitizer
    sanitizer="$(larch_log_batch_sanitizer "$batch")" || larch_log_fail 1 "unknown batch: $batch"
    case "$sanitizer" in
        none) ;;
        mermaid)
            "$LARCH_LOG_LIB_DIR/sanitize-mermaid-fragment.sh" --input "$file" --from-md >/dev/null \
                || larch_log_fail 2 "mermaid sanitizer rejected $batch"
            ;;
        *) larch_log_fail 1 "unknown sanitizer for $batch: $sanitizer" ;;
    esac
}

larch_log_atomic_replace() {
    local src="$1"
    local dest="$2"
    local dir tmp
    dir="$(dirname "$dest")"
    mkdir -p "$dir" || larch_log_fail 2 "cannot create log directory: $dir"
    tmp="$(mktemp "$dir/.tmp.$(basename "$dest").XXXXXX")" || larch_log_fail 2 "cannot create temp file"
    cp "$src" "$tmp" || {
        rm -f "$tmp"
        larch_log_fail 2 "cannot stage log payload"
    }
    mv -f "$tmp" "$dest" || {
        rm -f "$tmp"
        larch_log_fail 2 "cannot publish log payload"
    }
}

larch_log_emit_success() {
    local path="$1"
    local written="$2"
    local unchanged="$3"
    local commit_sha="${4:-}"
    local bytes sha
    if [ -f "$path" ]; then
        bytes="$(larch_log_bytes "$path")"
        sha="$(larch_log_sha256 "$path")"
    else
        bytes=0
        sha=""
    fi
    echo "LOG_WRITTEN=$written"
    echo "LOG_PATH=$path"
    echo "BYTES=$bytes"
    echo "SHA256=$sha"
    echo "COMMIT_SHA=$commit_sha"
    echo "UNCHANGED=$unchanged"
}
