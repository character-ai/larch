#!/usr/bin/env bash
# upsert-diagrams-comment.sh — merge and upsert the shared larch:diagrams comment.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

MARKER='<!-- larch:diagrams v1 -->'
ISSUE=""
REPO=""
ARCH_FILE=""
CODE_FILE=""
ARCH_CLEAR=false
CODE_CLEAR=false
ALLOW_EXTERNAL_PATHS=false
DRY_RUN=false

TMP_FILES=""

cleanup() {
    local f
    for f in $TMP_FILES; do
        rm -f "$f" 2>/dev/null || true
    done
}
trap cleanup EXIT

tmp_file() {
    local f
    f="$(mktemp)"
    TMP_FILES="$TMP_FILES $f"
    printf '%s\n' "$f"
}

usage() {
    larch_err "Usage: upsert-diagrams-comment.sh --issue N [--repo OWNER/REPO] [--architecture-file PATH | --clear-architecture] [--code-flow-file PATH | --clear-code-flow] [--marker '<!-- larch:diagrams v1 -->'] [--allow-external-paths] [--dry-run]"
}

emit_failure() {
    local msg=$1
    emit_kv UPSERT_STATUS failed
    emit_kv COMMENT_URL ""
    emit_kv UPDATED false
    emit_kv ARCHITECTURE_SOURCE "${ARCHITECTURE_SOURCE:-absent}"
    emit_kv CODE_FLOW_SOURCE "${CODE_FLOW_SOURCE:-absent}"
    emit_kv ERROR "$msg"
}

fail() {
    local code=$1 msg=$2
    emit_failure "$msg"
    exit "$code"
}

redact_gh_error() {
    local text=$1 redacted status=0
    [ -x "$SCRIPT_DIR/redact-secrets.sh" ] || {
        printf '%s' 'gh failure: redaction unavailable'
        return 0
    }
    redacted=$(printf '%s' "$text" | "$SCRIPT_DIR/redact-secrets.sh" 2>/dev/null) || status=$?
    if [ "$status" -ne 0 ]; then
        printf '%s' 'gh failure: redaction unavailable'
        return 0
    fi
    case "$redacted" in
        *'[content truncated'*)
            printf '%s' 'gh failure: redaction unavailable'
            return 0
            ;;
    esac
    printf '%s' "$redacted" | tr '\n' ' ' | head -c 500
}

print_data() {
    if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
        printf '%s' "$1" >&3
    else
        printf '%s' "$1"
    fi
}

redact_file() {
    local in_file=$1 out_file=$2 tmp_redacted
    [ -x "$SCRIPT_DIR/redact-secrets.sh" ] || fail 3 "redaction helper missing: redact-secrets.sh"
    [ -x "$SCRIPT_DIR/redact-tmpdir-paths.sh" ] || fail 3 "redaction helper missing: redact-tmpdir-paths.sh"
    tmp_redacted="$(tmp_file)"
    "$SCRIPT_DIR/redact-secrets.sh" <"$in_file" >"$tmp_redacted" || fail 3 "redact-secrets.sh failed"
    "$SCRIPT_DIR/redact-tmpdir-paths.sh" <"$tmp_redacted" >"$out_file" || fail 3 "redact-tmpdir-paths.sh failed"
}

normalize_first_line() {
    local line=$1
    if [[ "${line:0:3}" == $'\xef\xbb\xbf' ]]; then
        line="${line:3}"
    fi
    line="${line%$'\r'}"
    printf '%s' "$line"
}

canonical_path() {
    local path=$1 dir base
    dir="$(dirname "$path")"
    base="$(basename "$path")"
    (
        cd "$dir" 2>/dev/null &&
            printf '%s/%s\n' "$(pwd -P)" "$base"
    )
}

assert_tmp_scoped_input() {
    local label=$1 path=$2 resolved tmp_root canonical_root
    [ -n "$path" ] || return 0
    [ "$ALLOW_EXTERNAL_PATHS" = "true" ] && return 0
    [ -r "$path" ] || fail 1 "$label file not readable: $path"
    resolved="$(canonical_path "$path")" || fail 1 "$label file path is invalid: $path"
    for tmp_root in "${TMPDIR:-}" /tmp /private/tmp /var/folders; do
        [ -n "$tmp_root" ] || continue
        canonical_root="$(canonical_path "$tmp_root" 2>/dev/null || printf '%s' "$tmp_root")"
        case "$resolved" in
            "$canonical_root"|"$canonical_root"/*)
                return 0
                ;;
        esac
    done
    fail 1 "$label file must be under a temporary directory (or pass --allow-external-paths)"
}

sanitize_section_file() {
    local label=$1 path=$2 rc
    [ -s "$path" ] || return 0
    [ -x "$SCRIPT_DIR/sanitize-mermaid-fragment.sh" ] || fail 3 "sanitizer helper missing: sanitize-mermaid-fragment.sh"
    set +e
    "$SCRIPT_DIR/sanitize-mermaid-fragment.sh" --input "$path" --from-md > /dev/null 2>&1
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        fail 1 "sanitize-mermaid-fragment.sh rejected $label section"
    fi
}

extract_section() {
    local body_file=$1 wanted=$2 out_file=$3
    awk -v wanted="$wanted" '
        function trim(line) {
            sub(/^[[:space:]]+/, "", line)
            sub(/[[:space:]]+$/, "", line)
            return line
        }
        function is_target(line) {
            return line == ("## " wanted " Diagram")
        }
        function is_section_heading(line) {
            return line == "## Architecture Diagram" || line == "## Code Flow Diagram"
        }
        function is_section_start(idx,    j, probe) {
            if (!is_section_heading(lines[idx])) return 0
            for (j = idx + 1; j <= count && j <= idx + 3; j++) {
                probe = trim(lines[j])
                if (probe == "") continue
                return probe ~ /^(```|~~~)/
            }
            return 0
        }
        {
            lines[++count] = $0
        }
        END {
            start = 0
            end = 0
            for (i = 1; i <= count; i++) {
                if (!is_section_start(i)) continue
                if (start == 0 && is_target(lines[i])) {
                    start = i
                    continue
                }
                if (start != 0) {
                    end = i - 1
                    break
                }
            }
            if (start == 0) exit 0
            if (end == 0) end = count
            for (i = start; i <= end; i++) {
                print lines[i]
            }
        }
    ' "$body_file" >"$out_file"
}

append_nonempty_section() {
    local section_file=$1 out_file=$2
    [ -s "$section_file" ] || return 0
    if [ -s "$out_file" ]; then
        printf '\n\n' >>"$out_file"
    fi
    cat "$section_file" >>"$out_file"
}

resolve_mode() {
    local kind=$1 mode_file=$2 clear_flag=$3 existing_file=$4 out_file=$5
    : >"$out_file"
    if [ "$clear_flag" = "true" ]; then
        if [ "$kind" = "architecture" ]; then
            ARCHITECTURE_SOURCE=cleared
        else
            CODE_FLOW_SOURCE=cleared
        fi
        return 0
    fi
    if [ -n "$mode_file" ] && [ -s "$mode_file" ]; then
        cat "$mode_file" >"$out_file"
        if [ "$kind" = "architecture" ]; then
            ARCHITECTURE_SOURCE=new
        else
            CODE_FLOW_SOURCE=new
        fi
        return 0
    fi
    if [ -s "$existing_file" ]; then
        cat "$existing_file" >"$out_file"
        if [ "$kind" = "architecture" ]; then
            ARCHITECTURE_SOURCE=preserved
        else
            CODE_FLOW_SOURCE=preserved
        fi
        return 0
    fi
    if [ "$kind" = "architecture" ]; then
        ARCHITECTURE_SOURCE=absent
    else
        CODE_FLOW_SOURCE=absent
    fi
}

while [ $# -gt 0 ]; do
    case "$1" in
        --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
        --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
        --architecture-file) ARCH_FILE="${2:?--architecture-file requires a value}"; shift 2 ;;
        --clear-architecture) ARCH_CLEAR=true; shift ;;
        --code-flow-file) CODE_FILE="${2:?--code-flow-file requires a value}"; shift 2 ;;
        --clear-code-flow) CODE_CLEAR=true; shift ;;
        --marker) MARKER="${2:?--marker requires a value}"; shift 2 ;;
        --allow-external-paths) ALLOW_EXTERNAL_PATHS=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --help) usage; exit 0 ;;
        *) usage; fail 1 "unknown option: $1" ;;
    esac
done

[ -n "$ISSUE" ] || fail 1 "--issue is required"
case "$ISSUE" in *[!0-9]*|"") fail 1 "invalid issue: $ISSUE" ;; esac
case "$MARKER" in '<!-- larch:'*' -->') ;; *) fail 1 "invalid marker: $MARKER" ;; esac
if [ -n "$ARCH_FILE" ] && [ "$ARCH_CLEAR" = "true" ]; then
    fail 1 "--architecture-file and --clear-architecture are mutually exclusive"
fi
if [ -n "$CODE_FILE" ] && [ "$CODE_CLEAR" = "true" ]; then
    fail 1 "--code-flow-file and --clear-code-flow are mutually exclusive"
fi
if [ -z "$ARCH_FILE" ] && [ "$ARCH_CLEAR" != "true" ] && [ -z "$CODE_FILE" ] && [ "$CODE_CLEAR" != "true" ]; then
    fail 1 "at least one section mode is required"
fi
assert_tmp_scoped_input architecture "$ARCH_FILE"
assert_tmp_scoped_input code-flow "$CODE_FILE"

body_existing="$(tmp_file)"
arch_existing="$(tmp_file)"
code_existing="$(tmp_file)"

if [ "$DRY_RUN" != "true" ]; then
    if [ -z "$REPO" ]; then
        REPO="$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || true)"
        [ -n "$REPO" ] || fail 2 "could not determine repo"
    fi
    list_err="$(tmp_file)"
    list_out="$(gh api "/repos/${REPO}/issues/${ISSUE}/comments" --paginate --jq '.[] | (.id|tostring) + "\t" + ((.body // "") | split("\n")[0])' 2>"$list_err")" || {
        err="$(cat "$list_err" 2>/dev/null || true)"
        fail 2 "gh api comments fetch failed: $(redact_gh_error "$err")"
    }
    ids="$(printf '%s\n' "$list_out" | while IFS=$'\t' read -r id first_line; do
        [ -n "$id" ] || continue
        first_line="$(normalize_first_line "$first_line")"
        if [ "$first_line" = "$MARKER" ]; then
            printf '%s\n' "$id"
        fi
    done)"
    count="$(printf '%s\n' "$ids" | awk 'NF { n++ } END { print n + 0 }')"
    if [ "$count" -gt 1 ]; then
        flat="$(printf '%s' "$ids" | paste -sd, -)"
        fail 2 "multiple summary comments found for marker (ids: $flat)"
    fi
    if [ "$count" -eq 1 ]; then
        comment_id="$(printf '%s\n' "$ids" | awk 'NF { print; exit }')"
        body_err="$(tmp_file)"
        gh api "/repos/${REPO}/issues/comments/${comment_id}" --jq '.body // ""' >"$body_existing" 2>"$body_err" || {
            err="$(cat "$body_err" 2>/dev/null || true)"
            fail 2 "gh api comment fetch failed: $(redact_gh_error "$err")"
        }
    fi
fi

extract_section "$body_existing" Architecture "$arch_existing"
extract_section "$body_existing" "Code Flow" "$code_existing"

arch_final="$(tmp_file)"
code_final="$(tmp_file)"
sections_raw="$(tmp_file)"
sections_redacted="$(tmp_file)"

ARCHITECTURE_SOURCE=absent
CODE_FLOW_SOURCE=absent
resolve_mode architecture "$ARCH_FILE" "$ARCH_CLEAR" "$arch_existing" "$arch_final"
resolve_mode code-flow "$CODE_FILE" "$CODE_CLEAR" "$code_existing" "$code_final"
sanitize_section_file architecture "$arch_final"
sanitize_section_file code-flow "$code_final"

: >"$sections_raw"
append_nonempty_section "$arch_final" "$sections_raw"
append_nonempty_section "$code_final" "$sections_raw"
redact_file "$sections_raw" "$sections_redacted"

if [ "$DRY_RUN" = "true" ]; then
    preview="$(tmp_file)"
    {
        printf '%s\n\n' "$MARKER"
        cat "$sections_redacted"
        printf '\n\n--- content-file ---\n'
        cat "$sections_redacted"
    } >"$preview"
    print_data "$(cat "$preview")"
    emit_kv UPSERT_STATUS ok
    emit_kv COMMENT_URL ""
    emit_kv UPDATED false
    emit_kv ARCHITECTURE_SOURCE "$ARCHITECTURE_SOURCE"
    emit_kv CODE_FLOW_SOURCE "$CODE_FLOW_SOURCE"
    exit 0
fi

if [ ! -s "$sections_redacted" ] && [ "${comment_id:-}" = "" ]; then
    if [ "$ARCH_CLEAR" = "true" ] && [ "$ARCHITECTURE_SOURCE" = "cleared" ]; then
        ARCHITECTURE_SOURCE=absent
    fi
    if [ "$CODE_CLEAR" = "true" ] && [ "$CODE_FLOW_SOURCE" = "cleared" ]; then
        CODE_FLOW_SOURCE=absent
    fi
    emit_kv UPSERT_STATUS no-op
    emit_kv COMMENT_URL ""
    emit_kv UPDATED false
    emit_kv ARCHITECTURE_SOURCE "$ARCHITECTURE_SOURCE"
    emit_kv CODE_FLOW_SOURCE "$CODE_FLOW_SOURCE"
    exit 0
fi

if [ ! -s "$sections_redacted" ] && [ "${comment_id:-}" != "" ]; then
    delete_err="$(tmp_file)"
    gh api "/repos/${REPO}/issues/comments/${comment_id}" -X DELETE > /dev/null 2>"$delete_err" || {
        err="$(cat "$delete_err" 2>/dev/null || true)"
        fail 2 "gh api comment delete failed: $(redact_gh_error "$err")"
    }
    emit_kv UPSERT_STATUS ok
    emit_kv COMMENT_URL ""
    emit_kv UPDATED true
    emit_kv ARCHITECTURE_SOURCE "$ARCHITECTURE_SOURCE"
    emit_kv CODE_FLOW_SOURCE "$CODE_FLOW_SOURCE"
    exit 0
fi

upsert_out="$(tmp_file)"
upsert_err="$(tmp_file)"
set +e
"$SCRIPT_DIR/tracking-issue-summary.sh" upsert-summary \
    --issue "$ISSUE" \
    --marker "$MARKER" \
    --content-file "$sections_redacted" \
    ${comment_id:+--comment-id "$comment_id"} \
    ${REPO:+--repo "$REPO"} >"$upsert_out" 2>"$upsert_err"
upsert_rc=$?
set -e
if [ "$upsert_rc" -ne 0 ]; then
    err="$(cat "$upsert_err" 2>/dev/null || true)"
    fail 2 "tracking-issue-summary.sh failed: $(redact_gh_error "$err")"
fi

emit_kv UPSERT_STATUS ok
emit_kv COMMENT_URL "$(awk -F= '$1=="COMMENT_URL"{print substr($0,index($0,"=")+1); exit}' "$upsert_out")"
emit_kv UPDATED "$(awk -F= '$1=="UPDATED"{print substr($0,index($0,"=")+1); exit}' "$upsert_out")"
emit_kv ARCHITECTURE_SOURCE "$ARCHITECTURE_SOURCE"
emit_kv CODE_FLOW_SOURCE "$CODE_FLOW_SOURCE"
