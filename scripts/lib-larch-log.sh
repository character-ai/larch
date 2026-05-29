#!/usr/bin/env bash
# lib-larch-log.sh — shared helpers for scripts/larch-log.sh.

set -euo pipefail

LARCH_LOG_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# Resolve repo root from caller's CWD (consumer repo) so larch-logs land
# in the project being worked on, not the plugin install cache. Remains empty
# outside a git worktree.
LARCH_LOG_REPO_ROOT="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)" || true

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

# Returns 0 when value matches the slug rules shared with larch_log_validate_slug;
# returns 1 with no stdout (for callers that must not emit the larch-log contract).
larch_log_slug_is_valid() {
    local value="$1"
    case "$value" in
        ""|*[!A-Za-z0-9._-]*|.*|*..*|*/*|*\\*) return 1 ;;
        *) return 0 ;;
    esac
}

larch_log_validate_slug() {
    local kind="$1"
    local value="$2"
    if ! larch_log_slug_is_valid "$value"; then
        larch_log_fail 1 "invalid $kind: $value"
    fi
}

larch_log_root() {
    if [ -n "${LARCH_LOG_ROOT:-}" ]; then
        printf '%s\n' "$LARCH_LOG_ROOT"
    else
        larch_log_fail 1 "LARCH_LOG_ROOT is not set; pass --log-root to larch-log.sh (or export LARCH_LOG_ROOT for test isolation)"
    fi
}

larch_log_repo_run_dir() {
    local skill="$1" run_id="$2"
    printf '%s/larch-logs/%s/%s\n' "$LARCH_LOG_REPO_ROOT" "$skill" "$run_id"
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
    local sanitizer impl_tmp
    sanitizer="$(larch_log_batch_sanitizer "$batch")" || larch_log_fail 1 "unknown batch: $batch"
    case "$sanitizer" in
        none) ;;
        plan-goals)
            impl_tmp="$(mktemp "${TMPDIR:-/tmp}/larch-log-plan-goals.XXXXXX")" \
                || larch_log_fail 2 "cannot create plan-goals sanitizer temp"
            if ! awk '
                $0 == "## Implementation Plan" {
                    if (!saw) in_section = 1
                    saw = 1
                    next
                }
                in_section {
                    lines[++count] = $0
                    if ($0 == "## Test plan") last_test_plan = count
                }
                END {
                    if (!saw) exit 3
                    limit = count
                    if (last_test_plan > 0) limit = last_test_plan - 1
                    for (i = 1; i <= limit; i++) print lines[i]
                }
            ' "$file" > "$impl_tmp"; then
                rm -f "$impl_tmp"
                larch_log_fail 2 "plan-goals sanitizer rejected: missing Implementation Plan section"
            fi
            if ! awk 'NF { found = 1 } END { exit(found ? 0 : 1) }' "$impl_tmp"; then
                rm -f "$impl_tmp"
                larch_log_fail 2 "plan-goals sanitizer rejected: Implementation Plan body is empty"
            fi
            if awk '
                NF {
                    count++
                    if (count == 1) {
                        line = $0
                        gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
                        first = tolower(line)
                    }
                }
                END {
                    if (first ~ /^(see plan\.txt|see attached|see linked|tbd|todo)\.?$/) exit 0
                    exit 1
                }
            ' "$impl_tmp"; then
                rm -f "$impl_tmp"
                larch_log_fail 2 "plan-goals sanitizer rejected: Implementation Plan body is a pointer-only placeholder"
            fi
            rm -f "$impl_tmp"
            ;;
        mermaid)
            "$LARCH_LOG_LIB_DIR/sanitize-mermaid-fragment.sh" --input "$file" --from-md >/dev/null \
                || larch_log_fail 2 "mermaid sanitizer rejected $batch"
            ;;
        json-lines)
            [ -s "$file" ] || return 0
            while IFS= read -r line || [ -n "$line" ]; do
                [ -z "$line" ] && continue
                printf '%s' "$line" | jq . >/dev/null 2>&1 \
                    || larch_log_fail 2 "json-lines sanitizer rejected $batch: invalid JSON line"
            done < "$file"
            ;;
        json-object)
            jq -e -s 'length == 1 and (.[0] | type == "object")' "$file" >/dev/null 2>&1 \
                || larch_log_fail 2 "json-object sanitizer rejected $batch: expected exactly one top-level JSON object"
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

larch_log_session_tmp_contains() {
    local root="$1" path="$2"
    case "$path" in
        "$root") return 0 ;;
        "$root"/*) return 0 ;;
        *) return 1 ;;
    esac
}

larch_log_path_has_dotdot_component() {
    case "$1" in
        ../*|*/../*|*/..|..)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

larch_log_canonical_dir() {
    local path="$1"
    (
        cd "$path" 2>/dev/null && pwd -P
    )
}

larch_log_canonical_path() {
    local path="$1" parent base parent_canon
    if [ -L "$path" ]; then
        return 1
    fi
    if [ -d "$path" ]; then
        larch_log_canonical_dir "$path"
        return $?
    fi
    if [ -e "$path" ]; then
        parent="$(dirname "$path")"
        base="$(basename "$path")"
        parent_canon="$(larch_log_canonical_dir "$parent")" || return 1
        printf '%s/%s\n' "$parent_canon" "$base"
        return 0
    fi
    parent="$(dirname "$path")"
    base="$(basename "$path")"
    parent_canon="$(larch_log_canonical_dir "$parent")" || return 1
    printf '%s/%s\n' "$parent_canon" "$base"
}

larch_log_session_tmp_root_canon_for_path() {
    local path="$1" path_canon root_canon log_root
    if larch_log_path_has_dotdot_component "$path"; then
        return 1
    fi
    path_canon="$(larch_log_canonical_path "$path")" || return 1
    if [ -n "${IMPLEMENT_TMPDIR:-}" ]; then
        root_canon="$(larch_log_canonical_dir "$IMPLEMENT_TMPDIR")" || return 1
        if larch_log_session_tmp_contains "$root_canon" "$path_canon"; then
            printf '%s\n' "$root_canon"
            return 0
        fi
    fi
    if [ -n "${DESIGN_TMPDIR:-}" ]; then
        root_canon="$(larch_log_canonical_dir "$DESIGN_TMPDIR")" || return 1
        if larch_log_session_tmp_contains "$root_canon" "$path_canon"; then
            printf '%s\n' "$root_canon"
            return 0
        fi
    fi
    if [ -n "${REVIEW_TMPDIR:-}" ]; then
        root_canon="$(larch_log_canonical_dir "$REVIEW_TMPDIR")" || return 1
        if larch_log_session_tmp_contains "$root_canon" "$path_canon"; then
            printf '%s\n' "$root_canon"
            return 0
        fi
    fi
    if [ -n "${RESEARCH_TMPDIR:-}" ]; then
        root_canon="$(larch_log_canonical_dir "$RESEARCH_TMPDIR")" || return 1
        if larch_log_session_tmp_contains "$root_canon" "$path_canon"; then
            printf '%s\n' "$root_canon"
            return 0
        fi
    fi
    log_root="$(larch_log_root)"
    case "$log_root" in
        */larch-logs)
            root_canon="$(larch_log_canonical_dir "${log_root%/larch-logs}")" || return 1
            if larch_log_session_tmp_contains "$root_canon" "$path_canon"; then
                printf '%s\n' "$root_canon"
                return 0
            fi
            ;;
    esac
    return 1
}

larch_log_breadcrumbs_under_session_tmp() {
    larch_log_session_tmp_root_canon_for_path "$1" >/dev/null
}

larch_log_stat_link_count() {
    local path="$1"
    if stat -f '%l' "$path" >/dev/null 2>&1; then
        stat -f '%l' "$path"
    else
        stat -c '%h' "$path"
    fi
}

larch_log_cleanup_breadcrumb_staging() {
    rm -rf "$1" "$2"
}

larch_log_publish_breadcrumbs_swap() {
    local staging_dir="$1" dest_dir="$2" on_error="$3"
    local parent new_dir backup_dir
    parent="$(dirname "$dest_dir")"
    mkdir -p "$parent" || {
        "$on_error" "cannot create breadcrumbs parent directory"
        return 1
    }
    new_dir="$parent/.breadcrumbs.new.$$"
    backup_dir="$parent/.breadcrumbs.old.$$"
    rm -rf "$new_dir" "$backup_dir" 2>/dev/null || true
    mv "$staging_dir" "$new_dir" || {
        "$on_error" "cannot prepare breadcrumbs directory"
        return 1
    }
    if [ -e "$dest_dir" ]; then
        mv "$dest_dir" "$backup_dir" || {
            rm -rf "$new_dir" 2>/dev/null || true
            "$on_error" "cannot replace breadcrumbs directory"
            return 1
        }
    fi
    if mv "$new_dir" "$dest_dir"; then
        rm -rf "$backup_dir" 2>/dev/null || true
        return 0
    fi
    if [ -e "$backup_dir" ]; then
        mv "$backup_dir" "$dest_dir" 2>/dev/null || true
    fi
    rm -rf "$new_dir" "$backup_dir" 2>/dev/null || true
    "$on_error" "cannot publish breadcrumbs directory"
    return 1
}

larch_log_publish_breadcrumbs_stage_file() {
    local staging_parent="$1" staging_dir="$2" f="$3" on_error="$4"
    local base state_file tmp_out link_count

    [ -e "$f" ] || return 0
    [ ! -L "$f" ] || {
        rm -rf "$staging_parent"
        "$on_error" "breadcrumbs source file must not be a symlink: $f"
        return 1
    }
    [ -f "$f" ] || return 0
    if ! larch_log_breadcrumbs_under_session_tmp "$f"; then
        rm -rf "$staging_parent"
        "$on_error" "breadcrumbs source file must stay under the session tmpdir: $f"
        return 1
    fi
    link_count="$(larch_log_stat_link_count "$f" 2>/dev/null || printf '0')"
    if [ "${link_count:-0}" -gt 1 ]; then
        rm -rf "$staging_parent"
        "$on_error" "breadcrumbs source file must not be a hardlink: $f"
        return 1
    fi
    base="$(basename "$f")"
    case "$base" in
        */*|.*|*..*)
            rm -rf "$staging_parent"
            "$on_error" "invalid breadcrumbs basename: $base"
            return 1
            ;;
    esac
    state_file="$staging_parent/${base}.state"
    tmp_out="$staging_dir/$base"
    printf 'in_pem=0\n' >"$state_file" || {
        rm -rf "$staging_parent"
        "$on_error" "cannot create breadcrumbs redaction state"
        return 1
    }
    if ! "$LARCH_LOG_LIB_DIR/redact-tmpdir-paths.sh" <"$f" | "$LARCH_LOG_LIB_DIR/redact-secrets.sh" --streaming --state-file "$state_file" >"$tmp_out"; then
        rm -rf "$staging_parent" 2>/dev/null || true
        "$on_error" "breadcrumbs redaction failed for $f"
        return 1
    fi
    return 0
}

larch_log_publish_breadcrumbs_shared() {
    local source_hint_dir="$1" dest_dir="$2" on_error="$3"
    local staging_parent staging_dir f base found_any=false
    local session_root

    [ -n "$source_hint_dir" ] || return 0
    session_root="$(dirname "$source_hint_dir")"

    if ! larch_log_breadcrumbs_under_session_tmp "$session_root"; then
        return 0
    fi

    staging_parent="$(mktemp -d "${TMPDIR:-/tmp}/larch-log-breadcrumbs.XXXXXX")" || {
        "$on_error" "cannot create breadcrumbs staging temp"
        return 1
    }
    staging_dir="$staging_parent/breadcrumbs"
    mkdir -p "$staging_dir" || {
        rm -rf "$staging_parent"
        "$on_error" "cannot create breadcrumbs staging directory"
        return 1
    }

    for f in "$session_root"/larch-quiet-*-*.log; do
        [ -e "$f" ] || continue
        base="$(basename "$f")"
        case "$base" in
            larch-quiet-*-*.log) ;;
            *) continue ;;
        esac
        if ! larch_log_publish_breadcrumbs_stage_file "$staging_parent" "$staging_dir" "$f" "$on_error"; then
            return 1
        fi
        [ -e "$staging_dir/$base" ] || continue
        found_any=true
    done

    if [ "$found_any" != "true" ]; then
        rm -rf "$staging_parent"
        return 0
    fi
    larch_log_publish_breadcrumbs_swap "$staging_dir" "$dest_dir" "$on_error" || {
        larch_log_cleanup_breadcrumb_staging "$staging_parent" "$staging_dir"
        return 1
    }
    rm -rf "$staging_parent" 2>/dev/null || true
}
