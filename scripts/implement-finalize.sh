#!/usr/bin/env bash
# implement-finalize.sh — Mechanical finalizer for /implement Step 8 post-bump work and Steps 14, 15, and 18.

set -uo pipefail
# Intentional: best-effort failure model. Errexit is OFF file-wide. Every
# leaf-script invocation captures its own rc explicitly via 'rc=$?' after the
# call; helper failures surface through warning breadcrumbs and tail records,
# NEVER through script exit. Do NOT enable -e without auditing every leaf-
# script call site. Each guarded probe begins with a redundant 'set +e' as a
# defensive no-op (so a future accidental file-wide 'set -e' still leaves the
# probe non-fatal), and ends with another 'set +e' to keep the invariant
# explicit at the boundary.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

STATE_FILE=""
FINAL_BAIL_REASON_FILE=""
IMPLEMENT_TMPDIR=""
WARNINGS=0
CHANGELOG_BULLETS_FILE=""
POSTBUMP_CHECKPOINT_PHASE=""

usage() {
    cat >&2 <<'USAGE'
Usage:
  implement-finalize.sh postbump  --state-file PATH --implement-tmpdir PATH [--changelog-bullets-file PATH]
  implement-finalize.sh postmerge --state-file PATH --final-bail-reason-file PATH
  implement-finalize.sh teardown  --state-file PATH --implement-tmpdir PATH
USAGE
}

die_usage() {
    echo "implement-finalize.sh: $1" >&2
    usage
    exit 2
}

elapsed() {
    local start=$1 now
    now=$(date +%s)
    printf '%ss' "$((now - start))"
}

is_tmp_path() {
    local cache_root
    cache_root="${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions"
    case "$1" in
        /tmp/*|/private/tmp/*|/var/folders/*|/private/var/folders/*) return 0 ;;
        "$cache_root"/*) return 0 ;;
        *) return 1 ;;
    esac
}

parse_common_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --state-file)
                [ $# -ge 2 ] || die_usage "--state-file requires a value"
                STATE_FILE=$2
                shift 2
                ;;
            --final-bail-reason-file)
                [ $# -ge 2 ] || die_usage "--final-bail-reason-file requires a value"
                FINAL_BAIL_REASON_FILE=$2
                shift 2
                ;;
            --implement-tmpdir)
                [ $# -ge 2 ] || die_usage "--implement-tmpdir requires a value"
                IMPLEMENT_TMPDIR=$2
                shift 2
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                die_usage "unknown option: $1"
                ;;
        esac
    done
}

parse_postbump_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --state-file)
                [ $# -ge 2 ] || die_usage "--state-file requires a value"
                STATE_FILE=$2
                shift 2
                ;;
            --implement-tmpdir)
                [ $# -ge 2 ] || die_usage "--implement-tmpdir requires a value"
                IMPLEMENT_TMPDIR=$2
                shift 2
                ;;
            --changelog-bullets-file)
                [ $# -ge 2 ] || die_usage "--changelog-bullets-file requires a value"
                CHANGELOG_BULLETS_FILE=$2
                is_tmp_path "$CHANGELOG_BULLETS_FILE" || die_usage "--changelog-bullets-file must be under /tmp/, /private/tmp/, /var/folders/, or the larch cache sessions root"
                shift 2
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                die_usage "unknown option: $1"
                ;;
        esac
    done
}

validate_common_state_args() {
    [ -n "$STATE_FILE" ] || die_usage "--state-file is required"
    is_tmp_path "$STATE_FILE" || die_usage "--state-file must be under /tmp/, /private/tmp/, /var/folders/, or the larch cache sessions root"
    [ -r "$STATE_FILE" ] || die_usage "--state-file must exist and be readable"
}

validate_bail_file_arg() {
    [ -n "$FINAL_BAIL_REASON_FILE" ] || die_usage "--final-bail-reason-file is required"
    is_tmp_path "$FINAL_BAIL_REASON_FILE" || die_usage "--final-bail-reason-file must be under /tmp/, /private/tmp/, /var/folders/, or the larch cache sessions root"
}

validate_tmpdir_arg() {
    [ -n "$IMPLEMENT_TMPDIR" ] || die_usage "--implement-tmpdir is required"
    is_tmp_path "$IMPLEMENT_TMPDIR" || die_usage "--implement-tmpdir must be under /tmp/, /private/tmp/, /var/folders/, or the larch cache sessions root"
    case "$STATE_FILE" in
        "$IMPLEMENT_TMPDIR"/*) ;;
        *) die_usage "--state-file must live under --implement-tmpdir for teardown" ;;
    esac
    # Export so child processes inherit the session tmpdir path. larch-log.sh
    # receives its root explicitly via --log-root.
    # The postbump path also has export in load_and_validate_postbump_state;
    # this covers the teardown path which calls validate_tmpdir_arg directly.
    export IMPLEMENT_TMPDIR
}

validate_state_file_syntax() {
    local line line_no
    line_no=0
    while IFS= read -r line || [ -n "$line" ]; do
        line_no=$((line_no + 1))
        case "$line" in
            ""|\#*) continue ;;
        esac
        if ! printf '%s\n' "$line" | grep -Eq '^[A-Z_][A-Z0-9_]*=.*$'; then
            die_usage "malformed state-file line $line_no"
        fi
    done < "$STATE_FILE"
}

state_has_key() {
    grep -q "^$1=" "$STATE_FILE"
}

read_state() {
    local key=$1 default=${2-}
    awk -F= -v k="$key" -v d="$default" '
        $1 == k {
            print substr($0, index($0, "=") + 1)
            found = 1
            exit
        }
        END {
            if (!found) print d
        }
    ' "$STATE_FILE"
}

require_state_keys() {
    local key
    for key in \
        BRANCH_NAME PR_NUMBER PR_TITLE PR_URL ISSUE_NUMBER REPO \
        DRAFT MERGE DEFERRED REPO_UNAVAILABLE \
        PR_CLOSED DESIGN_ONLY_DONE BAIL_NEEDS_USER_INPUT STALL_TRACKING DONE_RENAME_APPLIED
    do
        state_has_key "$key" || die_usage "state-file missing required key: $key"
    done
}

require_bool_state() {
    local key value
    for key in \
        DRAFT MERGE DEFERRED REPO_UNAVAILABLE \
        PR_CLOSED DESIGN_ONLY_DONE BAIL_NEEDS_USER_INPUT STALL_TRACKING DONE_RENAME_APPLIED
    do
        value=$(read_state "$key")
        case "$value" in
            true|false) ;;
            *) die_usage "state-file key $key must be true or false" ;;
        esac
    done
}

load_and_validate_state() {
    validate_common_state_args
    validate_state_file_syntax
    require_state_keys
    require_bool_state
}

kv_value() {
    local key=$1 input=$2 line
    line=$(printf '%s\n' "$input" | awk -F= -v k="$key" '$1 == k {print substr($0, index($0, "=") + 1); exit}')
    printf '%s' "$line"
}

sha256_file() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        sha256sum "$1" | awk '{print $1}'
    fi
}

sha256_stream() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | awk '{print $1}'
    else
        sha256sum | awk '{print $1}'
    fi
}

normalize_body_for_hash() {
    # Strip leading '### Category' header line, strip leading/trailing blank lines.
    # Internal content (including code fences) is preserved verbatim.
    awk '
        NR == 1 && /^### / { next }
        { lines[++n] = $0 }
        END {
            s = 1; while (s <= n && lines[s] ~ /^[[:space:]]*$/) s++
            e = n; while (e >= s && lines[e] ~ /^[[:space:]]*$/) e--
            for (i = s; i <= e; i++) print lines[i]
        }
    '
}

json_escape_stream_python() {
    # python3 JSON-escape fallback when jq is absent. Handles full string
    # contract (control chars, \r, \b, \f, NUL, surrogate-safe). Returns
    # non-zero if python3 is unavailable; caller routes to a loud failure.
    command -v python3 >/dev/null 2>&1 || return 2
    python3 -c '
import json, sys
sys.stdout.write(json.dumps(sys.stdin.read()))
' || return 1
}

write_execution_issues_records() {
    local input_file=$1 record_file=$2 sha=$3 batch_path=${4:-}
    local current_cat body_file line rc=0 norm_sha rec_sha skip_section
    : > "$record_file"
    if command -v jq >/dev/null 2>&1; then
        body_file=$(mktemp "${TMPDIR:-/tmp}/exec-issue-section.XXXXXX") || return 1
        current_cat="Tool Failures"
        : > "$body_file"
        while IFS= read -r line || [ -n "$line" ]; do
            case "$line" in
                '### '*)
                    if [ -s "$body_file" ]; then
                        norm_sha=$(normalize_body_for_hash < "$body_file" | sha256_stream 2>/dev/null || true)
                        skip_section=false
                        if [ -n "$norm_sha" ] && [ -n "$batch_path" ] && [ -f "$batch_path" ] && \
                           grep -Fq '"source_sha256":"'"$norm_sha"'"' "$batch_path" 2>/dev/null; then
                            skip_section=true
                        fi
                        if [ "$skip_section" = "false" ]; then
                            rec_sha="${norm_sha:-$sha}"
                            jq -c -Rs --arg sha "$rec_sha" --arg cat "$current_cat" '{
                                phase: "implement", step: "18", category: $cat,
                                source: "execution-issues.md safety-net",
                                source_sha256: $sha, body: .
                            }' "$body_file" >> "$record_file" || rc=1
                        fi
                    fi
                    current_cat="${line#'### '}"
                    : > "$body_file"
                    ;;
                *)
                    printf '%s\n' "$line" >> "$body_file"
                    ;;
            esac
        done < "$input_file"
        if [ -s "$body_file" ]; then
            norm_sha=$(normalize_body_for_hash < "$body_file" | sha256_stream 2>/dev/null || true)
            skip_section=false
            if [ -n "$norm_sha" ] && [ -n "$batch_path" ] && [ -f "$batch_path" ] && \
               grep -Fq '"source_sha256":"'"$norm_sha"'"' "$batch_path" 2>/dev/null; then
                skip_section=true
            fi
            if [ "$skip_section" = "false" ]; then
                rec_sha="${norm_sha:-$sha}"
                jq -c -Rs --arg sha "$rec_sha" --arg cat "$current_cat" '{
                    phase: "implement", step: "18", category: $cat,
                    source: "execution-issues.md safety-net",
                    source_sha256: $sha, body: .
                }' "$body_file" >> "$record_file" || rc=1
            fi
        fi
        rm -f "$body_file"
        return $rc
    fi
    # No jq: fall back to python3. The awk-only escape was incomplete (no
    # \r/\b/\f/control-char handling), which produced invalid NDJSON for
    # binary-ish stderr captures and silently broke larch-log append on
    # hosts without jq. Refuse to write a record at all rather than emit
    # malformed NDJSON. python3 fallback emits one record for the whole file.
    local body_json escape_rc
    set +e
    body_json=$(json_escape_stream_python < "$input_file")
    escape_rc=$?
    set -e
    if [ "$escape_rc" -ne 0 ]; then
        warn_line '**⚠ 18: execution-issues safety-net needs jq or python3 to compose NDJSON. Neither found. Skipping safety-net flush.**'
        return 1
    fi
    {
        printf '{"phase":"implement","step":"18","category":"Tool Failures",'
        printf '"source":"execution-issues.md safety-net","source_sha256":"%s","body":%s}\n' "$sha" "$body_json"
    } > "$record_file"
}

flush_execution_issues_safety_net() {
    local run_id issue_log sha sentinel batch_path record_file out rc
    run_id=$(read_state RUN_ID)
    [ -n "$run_id" ] || return 0
    issue_log="$IMPLEMENT_TMPDIR/execution-issues.md"
    [ -s "$issue_log" ] || return 0
    sha=$(sha256_file "$issue_log" 2>/dev/null || true)
    [ -n "$sha" ] || return 0
    sentinel="$IMPLEMENT_TMPDIR/.execution-issues-flushed.sha"
    if [ -f "$sentinel" ] && [ "$(cat "$sentinel" 2>/dev/null || true)" = "$sha" ]; then
        return 0
    fi
    batch_path="$IMPLEMENT_TMPDIR/larch-logs/implement/$run_id/execution-issues.ndjson"
    if [ -f "$batch_path" ] && grep -Fq '"source_sha256":"'"$sha"'"' "$batch_path" 2>/dev/null; then
        printf '%s\n' "$sha" > "$sentinel" 2>/dev/null || true
        return 0
    fi
    record_file="$IMPLEMENT_TMPDIR/execution-issues-safety-net.ndjson"
    write_execution_issues_records "$issue_log" "$record_file" "$sha" "$batch_path" || {
        warn_line '**⚠ 18: execution-issues safety-net record compose failed. Continuing.**'
        return 0
    }
    if [ ! -s "$record_file" ]; then
        printf '%s\n' "$sha" > "$sentinel" 2>/dev/null || true
        return 0
    fi
    set +e
    out=$("$SCRIPT_DIR/larch-log.sh" append \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --skill implement \
        --run-id "$run_id" \
        --batch execution-issues \
        --record-file "$record_file" 2>&1)
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
        printf '%s\n' "$sha" > "$sentinel" 2>/dev/null || true
    else
        warn_line '**⚠ 18: execution-issues safety-net flush failed. Continuing.**'
        printf '%s\n' "$out" >&2
    fi
}

bail_reason_nonempty() {
    [ -f "$FINAL_BAIL_REASON_FILE" ] && [ -s "$FINAL_BAIL_REASON_FILE" ]
}

normalized_bail_reason() {
    if [ -f "$FINAL_BAIL_REASON_FILE" ]; then
        tr '\n' ' ' < "$FINAL_BAIL_REASON_FILE" | head -c 1024
    fi
}

warn_line() {
    WARNINGS=$((WARNINGS + 1))
    printf '%s\n' "$1"
}

append_execution_issue() {
    local text=$1
    [ -f "$IMPLEMENT_TMPDIR/execution-issues.md" ] || return 0
    {
        printf '\n## Tool Failures\n\n'
        printf -- '- %s\n' "$text"
    } >> "$IMPLEMENT_TMPDIR/execution-issues.md" 2>/dev/null || true
}

require_postbump_state_keys() {
    local key
    for key in \
        BRANCH_NAME ISSUE_NUMBER REPO REPO_UNAVAILABLE FORKED_TARGET HAS_BUMP \
        BUMP_TYPE NEW_VERSION BUMP_REASONING_FILE MANIFEST_PATH TOOL_LABEL
    do
        state_has_key "$key" || die_usage "state-file missing required key: $key"
    done
}

require_postbump_bool_state() {
    local key value
    for key in HAS_BUMP FORKED_TARGET REPO_UNAVAILABLE; do
        value=$(read_state "$key")
        case "$value" in
            true|false) ;;
            *) die_usage "state-file key $key must be true or false" ;;
        esac
    done
}

require_postbump_enum_state() {
    local value
    value=$(read_state BUMP_TYPE)
    case "$value" in
        MAJOR|MINOR|PATCH|NONE) ;;
        *) die_usage "state-file key BUMP_TYPE must be one of MAJOR, MINOR, PATCH, NONE" ;;
    esac
}

validate_postbump_state_branch() {
    local check_current=${1:-false} branch current rc
    branch=$(read_state BRANCH_NAME)
    [ -n "$branch" ] || die_usage "state-file key BRANCH_NAME must be non-empty for postbump"
    case "$branch" in
        main|master) die_usage "state-file key BRANCH_NAME must not be main or master" ;;
    esac
    if [ "$check_current" = "true" ]; then
        set +e
        current=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
        rc=$?
        set +e
        if [ "$rc" -ne 0 ] || [ "$current" != "$branch" ]; then
            return 1
        fi
    fi
    return 0
}

load_and_validate_postbump_state() {
    local bump_type new_version
    validate_common_state_args
    validate_tmpdir_arg
    export IMPLEMENT_TMPDIR
    validate_state_file_syntax
    require_postbump_state_keys
    require_postbump_bool_state
    require_postbump_enum_state
    validate_postbump_state_branch false
    bump_type=$(read_state BUMP_TYPE)
    new_version=$(read_state NEW_VERSION)
    if [ "$bump_type" != "NONE" ] && ! printf '%s\n' "$new_version" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
        die_usage "state-file key NEW_VERSION must be semver when BUMP_TYPE is not NONE"
    fi
}

postbump_checkpoint_path() {
    printf '%s/.postbump-phase' "$IMPLEMENT_TMPDIR"
}

write_postbump_checkpoint() {
    local tmp checkpoint
    checkpoint=$(postbump_checkpoint_path)
    tmp="$checkpoint.tmp.$$"
    printf 'force-push-gate\n' > "$tmp" && mv "$tmp" "$checkpoint"
}

read_postbump_checkpoint() {
    local checkpoint size phase
    POSTBUMP_CHECKPOINT_PHASE=""
    checkpoint=$(postbump_checkpoint_path)
    [ -e "$checkpoint" ] || return 0
    if [ ! -f "$checkpoint" ] || [ -L "$checkpoint" ]; then
        return 1
    fi
    size=$(wc -c < "$checkpoint" 2>/dev/null | tr -d '[:space:]' || echo 9999)
    case "$size" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ "$size" -le 64 ] || return 1
    phase=$(tr -d '\r' < "$checkpoint" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
    printf '%s\n' "$phase" | grep -Eq '^[a-z][a-z0-9-]*$' || return 1
    case "$phase" in
        force-push-gate) POSTBUMP_CHECKPOINT_PHASE=$phase ;;
        *) return 1 ;;
    esac
    return 0
}

clear_postbump_checkpoint() {
    rm -f "$(postbump_checkpoint_path)" 2>/dev/null || true
}

postbump_tail() {
    local status=$1 anchor_status=$2 changelog_status=$3 rebase_status=$4 force_push_status=$5 resume_phase=${6:-}
    emit_kv LOG_WRITE_STATUS "$anchor_status"
    emit_kv CHANGELOG_STATUS "$changelog_status"
    emit_kv REBASE_STATUS "$rebase_status"
    emit_kv FORCE_PUSH_STATUS "$force_push_status"
    if [ -n "$resume_phase" ]; then
        emit_kv RESUME_PHASE "$resume_phase"
        emit_kv CALLER_KIND "step8b_rebase"
    fi
    emit_kv STATUS "$status"
    emit_kv FINALIZE_SUBCOMMAND postbump
    emit_kv FINALIZE_WARNINGS "$WARNINGS"
}

postbump_mark() {
    local label=$1 token_session source_file
    token_session=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "" 2>/dev/null || true)
    source_file=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "" 2>/dev/null || true)
    export LARCH_TOKEN_SESSION_ID=$token_session
    export LARCH_CLAUDE_SOURCE_FILE=$source_file
    "$SCRIPT_DIR/token-ledger.sh" mark "$label" 2>/dev/null || true
    "$SCRIPT_DIR/timing-ledger.sh" mark "$label" 2>/dev/null || true
}

postbump_report_since_mark() {
    "$SCRIPT_DIR/token-report.sh" --since-last-mark --terse 2>/dev/null || true
    "$SCRIPT_DIR/timing-report.sh" --since-last-mark --terse 2>/dev/null || true
}

validate_bump_reasoning_file() {
    local path=$1 basename size
    [ -n "$path" ] || return 1
    is_tmp_path "$path" || return 1
    [ -f "$path" ] || return 1
    [ ! -L "$path" ] || return 1
    basename=$(basename "$path")
    case "$basename" in
        bump-version-reasoning*.md|version-bump-reasoning-sanitized.md) ;;
        *) return 1 ;;
    esac
    size=$(wc -c < "$path" 2>/dev/null | tr -d '[:space:]' || echo 999999)
    case "$size" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ "$size" -le 65536 ] || return 1
}

validate_small_tmp_file() {
    local path=$1 size
    [ -n "$path" ] || return 1
    is_tmp_path "$path" || return 1
    [ -f "$path" ] || return 1
    [ ! -L "$path" ] || return 1
    size=$(wc -c < "$path" 2>/dev/null | tr -d '[:space:]' || echo 999999)
    case "$size" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ "$size" -le 65536 ] || return 1
}

write_version_reasoning_fragment() {
    local start issue_number repo_unavailable reasoning_file content out rc failed run_id input_file
    start=$(date +%s)
    issue_number=$(read_state ISSUE_NUMBER)
    repo_unavailable=$(read_state REPO_UNAVAILABLE)
    reasoning_file=$(read_state BUMP_REASONING_FILE)
    mkdir -p "$IMPLEMENT_TMPDIR/larch-log-batches"
    if validate_bump_reasoning_file "$reasoning_file"; then
        content=$(cat "$reasoning_file" 2>/dev/null || true)
    else
        content="No version bump reasoning available (skill may have skipped via BUMP_TYPE=NONE, or /bump-version was not invoked)."
        append_execution_issue "Step 8 postbump larch-log used fallback version-bump reasoning because BUMP_REASONING_FILE failed validation."
        warn_line '**⚠ 8: larch-log — version-bump-reasoning input failed validation; fallback text used. Continuing.**'
    fi
    input_file="$IMPLEMENT_TMPDIR/larch-log-batches/version-bump-reasoning.md"
    printf '%s\n' "$content" \
        | awk '/^[[:space:]]*$/{blank=1; next} {if(blank){print ""; blank=0}; print}' \
        > "$input_file"
    [ -s "$input_file" ] || printf '\n' > "$input_file"

    LOG_WRITE_STATUS=skipped
    if [ -n "$issue_number" ] && [ "$repo_unavailable" = "false" ]; then
        run_id="${LARCH_RUN_ID:-${RUN_ID:-$(read_state RUN_ID)}}"
        if [ -z "$run_id" ]; then
            run_id="$(basename "$IMPLEMENT_TMPDIR")"
            run_id="${run_id##*-}"
        fi
        set +e
        out=$("$SCRIPT_DIR/larch-log.sh" write --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$run_id" --batch version-bump-reasoning --input-file "$input_file")
        rc=$?
        set +e
        written=$(kv_value LOG_WRITTEN "$out")
        unchanged=$(kv_value UNCHANGED "$out")
        if [ "$rc" -eq 0 ] && { [ "$written" = "true" ] || [ "$unchanged" = "true" ]; }; then
            LOG_WRITE_STATUS=ok
        else
            LOG_WRITE_STATUS=failed
            append_execution_issue "Step 8 postbump version-bump-reasoning log write failed."
            warn_line '**⚠ 8: larch-log — version-bump-reasoning write failed. Continuing.**'
        fi
    fi
    emit_breadcrumb "$(printf '✅ 8: larch-log status=complete elapsed=%s' "$(elapsed "$start")")"
}

changelog_categories_to_markdown() {
    local dir=$1 out=$2 category file title had_any
    : > "$out"
    had_any=false
    for category in Added Changed Fixed Removed Security; do
        file="$dir/$category"
        [ -s "$file" ] || continue
        [ "$had_any" = "true" ] && printf '\n' >> "$out"
        had_any=true
        printf '### %s\n\n' "$category" >> "$out"
        while IFS= read -r title || [ -n "$title" ]; do
            [ -n "$title" ] || continue
            printf -- '- %s\n' "$title" >> "$out"
        done < "$file"
    done
    [ "$had_any" = "true" ]
}

collect_changelog_bullets() {
    local dir=$1 manifest_path=$2 line category bullet categorized
    mkdir -p "$dir"
    : > "$dir/Added"; : > "$dir/Changed"; : > "$dir/Fixed"; : > "$dir/Removed"; : > "$dir/Security"
    if [ -n "$manifest_path" ]; then
        if ! validate_small_tmp_file "$manifest_path"; then
            return 1
        fi
        categorized=$(jq -c '(.summary_bullets_categorized // {}) | if type == "object" then . else {} end' "$manifest_path" 2>/dev/null || echo '{}')
        if [ "$categorized" != "{}" ]; then
            for category in Added Changed Fixed Removed Security; do
                jq -r --arg c "$category" '(.summary_bullets_categorized // {})[$c] // [] | if type == "array" then .[] else empty end' "$manifest_path" 2>/dev/null >> "$dir/$category" || return 1
            done
        else
            jq -r '(.summary_bullets // []) | if type == "array" then .[] else empty end' "$manifest_path" 2>/dev/null >> "$dir/Changed" || return 1
        fi
    else
        # No manifest and no bullets file → empty categories, not an error (skipped-no-bullets path)
        [ -n "${CHANGELOG_BULLETS_FILE:-}" ] || return 0
        validate_small_tmp_file "$CHANGELOG_BULLETS_FILE" || return 1
        while IFS= read -r line || [ -n "$line" ]; do
            [ -n "$line" ] || continue
            case "$line" in
                *"	"*)
                    category=${line%%	*}
                    bullet=${line#*	}
                    ;;
                *)
                    category=Changed
                    bullet=$line
                    ;;
            esac
            case "$category" in
                Added|Changed|Fixed|Removed|Security) ;;
                *) category=Changed ;;
            esac
            printf '%s\n' "$bullet" >> "$dir/$category"
        done < "$CHANGELOG_BULLETS_FILE"
    fi
}

write_changelog_entry() {
    local version=$1 categories_file=$2 output=$3 today tmp
    today=$(date +%Y-%m-%d)
    tmp="$output.entry.$$"
    {
        printf '## [%s] - %s\n\n' "$version" "$today"
        cat "$categories_file"
    } > "$tmp"
    awk -v version="$version" -v entry="$tmp" '
        BEGIN {
            while ((getline line < entry) > 0) e[++en] = line
            close(entry)
            has_unreleased = 0
            inserted = 0
            skipping = 0
            in_unreleased = 0
            match_count = 0
            entry_from_version_match = 0
        }
        FNR == NR {
            if (/^## \[Unreleased\]/) has_unreleased = 1
            next
        }
        $0 ~ "^## \\[" version "\\] - " {
            match_count++
            if (match_count > 1) exit 4
            if (in_unreleased) {
                in_unreleased = 0
            }
            if (!inserted) {
                for (i = 1; i <= en; i++) print e[i]
                inserted = 1
                entry_from_version_match = 1
            }
            skipping = 1
            next
        }
        skipping && /^## \[/ {
            if (entry_from_version_match) print ""
            skipping = 0
        }
        skipping {
            next
        }
        /^## \[Unreleased\]/ {
            print
            in_unreleased = 1
            next
        }
        in_unreleased && /^## \[/ {
            in_unreleased = 0
            if (!inserted) {
                for (i = 1; i <= en; i++) print e[i]
                print ""
                inserted = 1
            }
            print
            next
        }
        in_unreleased {
            print
            next
        }
        !has_unreleased && /and this project adheres to \[Semantic Versioning\]/ {
            print
            if (!inserted) {
                print ""
                for (i = 1; i <= en; i++) print e[i]
                inserted = 1
            }
            next
        }
        !inserted && /^## \[/ {
            for (i = 1; i <= en; i++) print e[i]
            print ""
            inserted = 1
        }
        { print }
        END {
            if (in_unreleased && !inserted) {
                print ""
                for (i = 1; i <= en; i++) print e[i]
                inserted = 1
            }
            if (!inserted) exit 3
        }
    ' CHANGELOG.md CHANGELOG.md > "$output"
    rc=$?
    rm -f "$tmp"
    return "$rc"
}

maybe_update_changelog() {
    local start out rc present forked_target has_bump bump_type new_version manifest_path tmpdir categories_md tmp_changelog status_out
    start=$(date +%s)
    CHANGELOG_STATUS="skipped-no-bump"
    set +e
    out=$("$SCRIPT_DIR/check-changelog-present.sh")
    rc=$?
    set +e
    present=$(kv_value CHANGELOG_PRESENT "$out")
    if [ "$rc" -ne 0 ] || [ "$present" != "true" ]; then
        CHANGELOG_STATUS="skipped-absent"
        emit_breadcrumb "$(printf '⏩ 8a: changelog status=skip reason=changelog-absent elapsed=%s' "$(elapsed "$start")")"
        return 0
    fi
    forked_target=$(read_state FORKED_TARGET)
    if [ "$forked_target" = "true" ]; then
        CHANGELOG_STATUS="skipped-fork"
        emit_breadcrumb "$(printf '⏩ 8a: changelog status=skip reason=forked-dry-run elapsed=%s' "$(elapsed "$start")")"
        return 0
    fi
    has_bump=$(read_state HAS_BUMP)
    bump_type=$(read_state BUMP_TYPE)
    if [ "$has_bump" != "true" ] || [ "$bump_type" = "NONE" ]; then
        CHANGELOG_STATUS="skipped-no-bump"
        emit_breadcrumb "$(printf '⏩ 8a: changelog status=skip reason=no-bump-commit elapsed=%s' "$(elapsed "$start")")"
        return 0
    fi

    new_version=$(read_state NEW_VERSION)
    manifest_path=$(read_state MANIFEST_PATH)
    tmpdir="$IMPLEMENT_TMPDIR/postbump-changelog.$$"
    mkdir -p "$tmpdir"
    if ! collect_changelog_bullets "$tmpdir/categories" "$manifest_path"; then
        CHANGELOG_STATUS=failed
        append_execution_issue "Step 8a changelog failed while reading changelog bullets."
        warn_line '**⚠ Step 8a: changelog update failed while reading bullets. Bailing to cleanup.**'
        rm -rf "$tmpdir"
        return 1
    fi
    categories_md="$tmpdir/categories.md"
    if ! changelog_categories_to_markdown "$tmpdir/categories" "$categories_md"; then
        CHANGELOG_STATUS="skipped-no-bullets"
        append_execution_issue "Step 8a changelog skipped because no summary bullets were available."
        warn_line '**⚠ 8a: changelog — no summary bullets available; amend skipped. Continuing.**'
        rm -rf "$tmpdir"
        return 0
    fi

    # Only mark now that we have confirmed there are bullets to write
    postbump_mark "Step 8a — changelog"
    tmp_changelog="$tmpdir/CHANGELOG.md"
    set +e
    write_changelog_entry "$new_version" "$categories_md" "$tmp_changelog"
    rc=$?
    set +e
    if [ "$rc" -eq 4 ]; then
        CHANGELOG_STATUS=failed
        append_execution_issue "Step 8a changelog failed because CHANGELOG.md has multiple existing ## [$new_version] - headings."
        warn_line "**⚠ Step 8a: changelog update failed (multiple existing ## [$new_version] headings — fix CHANGELOG.md by hand and rerun). Bailing to cleanup.**"
        rm -rf "$tmpdir"
        postbump_report_since_mark
        return 1
    fi
    if [ "$rc" -ne 0 ]; then
        CHANGELOG_STATUS=failed
        append_execution_issue "Step 8a changelog failed because CHANGELOG.md had no insertion anchor."
        warn_line '**⚠ Step 8a: changelog update failed (no insertion anchor). Bailing to cleanup.**'
        rm -rf "$tmpdir"
        postbump_report_since_mark
        return 1
    fi
    if ! mv "$tmp_changelog" CHANGELOG.md 2>/dev/null; then
        CHANGELOG_STATUS=failed
        append_execution_issue "Step 8a changelog failed while writing CHANGELOG.md."
        warn_line '**⚠ Step 8a: changelog write failed. Bailing to cleanup.**'
        rm -rf "$tmpdir"
        postbump_report_since_mark
        return 1
    fi
    set +e
    out=$("$SCRIPT_DIR/git-amend-add.sh" CHANGELOG.md 2>&1)
    rc=$?
    set +e
    if [ "$rc" -ne 0 ]; then
        git checkout -- CHANGELOG.md 2>/dev/null || true
        CHANGELOG_STATUS=failed
        append_execution_issue "Step 8a changelog amend failed."
        warn_line '**⚠ Step 8a: changelog amend failed. Bailing to cleanup.**'
        rm -rf "$tmpdir"
        postbump_report_since_mark
        return 1
    fi
    set +e
    status_out=$(git status --porcelain CHANGELOG.md 2>/dev/null)
    rc=$?
    set +e
    if [ "$rc" -ne 0 ] || [ -n "$status_out" ]; then
        git checkout -- CHANGELOG.md 2>/dev/null || true
        CHANGELOG_STATUS=failed
        append_execution_issue "Step 8a changelog remained dirty after amend."
        warn_line '**⚠ Step 8a: changelog remained dirty after amend. Bailing to cleanup.**'
        rm -rf "$tmpdir"
        postbump_report_since_mark
        return 1
    fi
    CHANGELOG_STATUS=updated
    emit_breadcrumb "$(printf '✅ 8a: changelog status=complete to=v%s elapsed=%s' "$new_version" "$(elapsed "$start")")"
    rm -rf "$tmpdir"
    postbump_report_since_mark
    return 0
}

run_step8b_rebase() {
    local start forked_target repo_unavailable out rc skipped error_text
    start=$(date +%s)
    postbump_mark "Step 8b — rebase"
    REBASE_STATUS=failed
    if ! validate_postbump_state_branch true; then
        append_execution_issue "Step 8b postbump branch mismatch before rebase."
        warn_line '**⚠ Step 8b: branch mismatch before rebase. Bailing to cleanup.**'
        set +e
        postbump_report_since_mark
        return 4
    fi
    emit_breadcrumb '🔃 8b: rebase'
    forked_target=$(read_state FORKED_TARGET)
    repo_unavailable=$(read_state REPO_UNAVAILABLE)
    set +e
    if [ "$forked_target" = "true" ]; then
        out=$("$SCRIPT_DIR/rebase-push.sh" --no-push --base-remote upstream --base-ref main 2>&1)
    else
        out=$("$SCRIPT_DIR/rebase-push.sh" --no-push 2>&1)
    fi
    rc=$?
    set +e
    skipped=$(kv_value SKIPPED_ALREADY_FRESH "$out")
    case "$rc" in
        0)
            if [ "$skipped" = "true" ]; then
                REBASE_STATUS=already-fresh
            else
                REBASE_STATUS=rebased
                emit_breadcrumb "$(printf '✅ 8b: rebase status=complete outcome=rebased elapsed=%s' "$(elapsed "$start")")"
            fi
            postbump_report_since_mark
            return 0
            ;;
        1)
            if [ "$forked_target" = "true" ]; then
                REBASE_STATUS=failed
                warn_line '**⚠ Step 8b: rebase onto upstream/main failed (conflict under --forked). Resolve manually and rerun.**'
                set +e
                postbump_report_since_mark
                return 2
            elif [ "$repo_unavailable" = "true" ]; then
                REBASE_STATUS=failed
                warn_line '**⚠ Step 8b: rebase onto main failed (conflict, repo_unavailable=true so sub-procedure auto-recovery is skipped). Bailing to cleanup.**'
                set +e
                postbump_report_since_mark
                return 2
            else
                REBASE_STATUS=conflict
                write_postbump_checkpoint
                emit_breadcrumb '🔃 8b: rebase — conflict detected; handing off to Rebase + Re-bump Sub-procedure (caller_kind=step8b_rebase)'
                set +e
                postbump_report_since_mark
                return 1
            fi
            ;;
        3)
            error_text=$(kv_value REBASE_ERROR "$out")
            [ -n "$error_text" ] || error_text="exit 3"
            REBASE_STATUS=failed
            warn_line "$(printf '**⚠ Step 8b: rebase failed (non-conflict): %s. Bailing to cleanup.**' "$error_text")"
            set +e
            postbump_report_since_mark
            return 2
            ;;
        *)
            REBASE_STATUS=failed
            warn_line "$(printf '**⚠ Step 8b: rebase failed unexpectedly (exit %s). Bailing to cleanup.**' "$rc")"
            set +e
            postbump_report_since_mark
            return 2
            ;;
    esac
}

run_force_push_gate() {
    local start repo_unavailable branch out rc state remote_rc error push_status
    start=$(date +%s)
    FORCE_PUSH_STATUS=absent
    repo_unavailable=$(read_state REPO_UNAVAILABLE)
    if [ "$repo_unavailable" = "true" ]; then
        FORCE_PUSH_STATUS="skipped-repo-unavailable"
        clear_postbump_checkpoint
        emit_breadcrumb "$(printf '⏭️ 8b: rebase status=bypass reason=repo-unavailable elapsed=%s' "$(elapsed "$start")")"
        return 0
    fi
    if ! validate_postbump_state_branch true; then
        append_execution_issue "Step 8b postbump branch mismatch before force-push gate."
        warn_line '**⚠ Step 8b: branch mismatch before force-push gate. Bailing to cleanup.**'
        set +e
        return 4
    fi
    branch=$(read_state BRANCH_NAME)
    set +e
    out=$("$SCRIPT_DIR/check-remote-branch.sh" --branch "$branch")
    rc=$?
    set +e
    state=$(kv_value STATE "$out")
    remote_rc=$(kv_value RC "$out")
    error=$(kv_value ERROR "$out")
    case "$state" in
        present)
            set +e
            out=$("$SCRIPT_DIR/git-force-push.sh" 2>&1)
            rc=$?
            set +e
            push_status=$(kv_value STATUS "$out")
            case "$push_status" in
                pushed|noop_same_ref)
                    FORCE_PUSH_STATUS=$push_status
                    clear_postbump_checkpoint
                    emit_breadcrumb "$(printf '✅ 8b: rebase status=complete outcome=force-pushed elapsed=%s' "$(elapsed "$start")")"
                    return 0
                    ;;
                *)
                    FORCE_PUSH_STATUS=failed
                    append_execution_issue "Step 8b force-push failed after rebase."
                    warn_line '**⚠ Step 8b: force-push failed after rebase (lease check refused). Bailing to cleanup.**'
                    set +e
                    return 3
                    ;;
            esac
            ;;
        absent)
            FORCE_PUSH_STATUS=absent
            clear_postbump_checkpoint
            return 0
            ;;
        *)
            FORCE_PUSH_STATUS=failed
            append_execution_issue "Step 8b check-remote-branch failed before force-push."
            warn_line "$(printf '**⚠ Step 8b: check-remote-branch failed (RC=%s, ERROR=%s; transport or auth error). Bailing to cleanup.**' "$remote_rc" "$error")"
            set +e
            return 5
            ;;
    esac
}

run_postbump() {
    local rc repo_root
    LOG_WRITE_STATUS=skipped
    CHANGELOG_STATUS="skipped-resume"
    REBASE_STATUS="skipped-resume"
    FORCE_PUSH_STATUS=absent
    set +e
    repo_root=$(git rev-parse --show-toplevel 2>/dev/null)
    rc=$?
    set +e
    if [ "$rc" -ne 0 ] || [ -z "$repo_root" ]; then
        warn_line '**⚠ Step 8: postbump must run inside a git working tree (cwd is not in a repo). Bailing to cleanup.**'
        postbump_tail postbump-cwd-not-repo skipped skipped-no-bump skipped-resume absent
        return 0
    fi
    cd "$repo_root" || {
        warn_line "**⚠ Step 8: postbump could not cd to repo root '$repo_root'. Bailing to cleanup.**"
        postbump_tail postbump-cwd-not-repo skipped skipped-no-bump skipped-resume absent
        return 0
    }
    load_and_validate_postbump_state
    if ! read_postbump_checkpoint; then
        append_execution_issue "Step 8 postbump checkpoint file was corrupt."
        warn_line '**⚠ Step 8: postbump checkpoint file corrupt. Bailing to cleanup.**'
        postbump_tail postbump-state-corrupt skipped skipped-resume skipped-resume absent
        return 0
    fi
    if [ "$POSTBUMP_CHECKPOINT_PHASE" = "force-push-gate" ]; then
        LOG_WRITE_STATUS=skipped
        CHANGELOG_STATUS="skipped-resume"
        REBASE_STATUS="skipped-resume"
        set +e
        run_force_push_gate
        rc=$?
        set +e
        case "$rc" in
            0) postbump_tail ok "$LOG_WRITE_STATUS" "$CHANGELOG_STATUS" "$REBASE_STATUS" "$FORCE_PUSH_STATUS" ;;
            3) postbump_tail push-failed "$LOG_WRITE_STATUS" "$CHANGELOG_STATUS" "$REBASE_STATUS" "$FORCE_PUSH_STATUS" ;;
            4) postbump_tail branch-mismatch "$LOG_WRITE_STATUS" "$CHANGELOG_STATUS" "$REBASE_STATUS" "$FORCE_PUSH_STATUS" ;;
            5) postbump_tail remote-check-failed "$LOG_WRITE_STATUS" "$CHANGELOG_STATUS" "$REBASE_STATUS" "$FORCE_PUSH_STATUS" ;;
            *) postbump_tail push-failed "$LOG_WRITE_STATUS" "$CHANGELOG_STATUS" "$REBASE_STATUS" "$FORCE_PUSH_STATUS" ;;
        esac
        return 0
    fi

    write_version_reasoning_fragment
    if ! maybe_update_changelog; then
        postbump_tail changelog-failed "$LOG_WRITE_STATUS" "$CHANGELOG_STATUS" skipped-resume absent
        return 0
    fi
    set +e
    run_step8b_rebase
    rc=$?
    set +e
    case "$rc" in
        0) ;;
        1) postbump_tail conflict "$LOG_WRITE_STATUS" "$CHANGELOG_STATUS" "$REBASE_STATUS" absent force-push-gate; return 0 ;;
        4) postbump_tail branch-mismatch "$LOG_WRITE_STATUS" "$CHANGELOG_STATUS" "$REBASE_STATUS" absent; return 0 ;;
        *) postbump_tail rebase-failed "$LOG_WRITE_STATUS" "$CHANGELOG_STATUS" "$REBASE_STATUS" absent; return 0 ;;
    esac
    set +e
    run_force_push_gate
    rc=$?
    set +e
    case "$rc" in
        0) postbump_tail ok "$LOG_WRITE_STATUS" "$CHANGELOG_STATUS" "$REBASE_STATUS" "$FORCE_PUSH_STATUS" ;;
        3) postbump_tail push-failed "$LOG_WRITE_STATUS" "$CHANGELOG_STATUS" "$REBASE_STATUS" "$FORCE_PUSH_STATUS" ;;
        4) postbump_tail branch-mismatch "$LOG_WRITE_STATUS" "$CHANGELOG_STATUS" "$REBASE_STATUS" "$FORCE_PUSH_STATUS" ;;
        5) postbump_tail remote-check-failed "$LOG_WRITE_STATUS" "$CHANGELOG_STATUS" "$REBASE_STATUS" "$FORCE_PUSH_STATUS" ;;
        *) postbump_tail push-failed "$LOG_WRITE_STATUS" "$CHANGELOG_STATUS" "$REBASE_STATUS" "$FORCE_PUSH_STATUS" ;;
    esac
}

clone_basename_prefix() {
    local clone_tag
    clone_tag=$(basename "$PWD")
    clone_tag=$(printf '%s' "$clone_tag" | tr -c 'A-Za-z0-9_-' '_')
    clone_tag=${clone_tag:0:32}
    [ -n "$clone_tag" ] || clone_tag="_"
    printf 'claude-implement-%s-' "$clone_tag"
}

verify_cleanup_target() {
    local expected_session_id expected_prefix actual_basename actual_session_id
    local basename_ok session_ok session_match_display

    expected_session_id=$(read_state EXPECTED_SESSION_ID "")
    expected_prefix=$(read_state EXPECTED_TMPDIR_BASENAME_PREFIX "")
    [ -n "$expected_prefix" ] || expected_prefix=$(clone_basename_prefix)

    actual_basename=$(basename "$IMPLEMENT_TMPDIR")
    basename_ok=false
    case "$actual_basename" in
        "$expected_prefix"*) basename_ok=true ;;
    esac

    session_ok=true
    session_match_display=skipped
    if [ -z "$expected_session_id" ]; then
        warn_line '**⚠ 18: cleanup sanity check — EXPECTED_SESSION_ID missing; using basename-only validation.**'
    else
        actual_session_id=$(cat "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)
        session_ok=false
        session_match_display=n
        if [ "$actual_session_id" = "$expected_session_id" ]; then
            session_ok=true
            session_match_display=y
        fi
    fi

    if [ "$basename_ok" = "true" ] && [ "$session_ok" = "true" ]; then
        return 0
    fi

    # When EXPECTED_SESSION_ID was present and the session-id file matches, the UUID is a
    # sufficient identity guarantee — authorize cleanup even if the basename prefix doesn't
    # match. A prefix mismatch can result from the stray-underscore bug fixed in #1563 or
    # the literal-quote bug fixed in #1572. See #1784.
    if [ "$session_ok" = "true" ] && [ -n "$expected_session_id" ]; then
        warn_line "$(printf '**⚠ 18: cleanup target basename prefix mismatch (expected=%s, actual=%s) — session-id match authorizes cleanup. Proceeding.**' "$expected_prefix" "$actual_basename")"
        return 0
    fi

    append_execution_issue "Step 18 cleanup target failed sanity check (basename=$actual_basename, session-id-match=$session_match_display); cleanup skipped."
    warn_line "$(printf '**⚠ 18: cleanup target failed sanity check (basename=%s, session-id-match=%s) — refusing to rm-rf. Operator must clean manually.**' "$actual_basename" "$session_match_display")"
    return 1
}

run_postmerge() {
    local start branch pr_title pr_number draft merge local_status verify_status
    local out rc cleanup_success current_branch branch_deleted expected_title
    local verified commit_hash commit_message

    start=$(date +%s)
    validate_bail_file_arg
    load_and_validate_state

    branch=$(read_state BRANCH_NAME)
    pr_title=$(read_state PR_TITLE)
    pr_number=$(read_state PR_NUMBER)
    draft=$(read_state DRAFT)
    merge=$(read_state MERGE)
    verify_status=skipped

    if [ "$draft" = "true" ]; then
        emit_breadcrumb "$(printf '⏭️ 14: local cleanup status=bypass reason=draft-set elapsed=%s' "$(elapsed "$start")")"
        local_status="skipped-draft"
    elif [ "$merge" != "true" ]; then
        emit_breadcrumb "$(printf '⏭️ 14: local cleanup status=bypass reason=merge-not-set elapsed=%s' "$(elapsed "$start")")"
        local_status="skipped-merge-false"
    elif bail_reason_nonempty; then
        warn_line "$(printf '**⚠ 14: local cleanup — skipped (PR not merged), still on %s (%s)**' "$branch" "$(elapsed "$start")")"
        local_status="skipped-bail"
    else
        [ -n "$branch" ] || die_usage "state-file key BRANCH_NAME must be non-empty for postmerge cleanup"
        [ "$branch" != "main" ] || die_usage "state-file key BRANCH_NAME must not be main"

        set +e
        out=$("$SCRIPT_DIR/local-cleanup.sh" --branch "$branch")
        rc=$?
        set +e
        cleanup_success=$(kv_value CLEANUP_SUCCESS "$out")
        current_branch=$(kv_value CURRENT_BRANCH "$out")
        branch_deleted=$(kv_value BRANCH_DELETED "$out")

        if [ "$rc" -eq 0 ] && [ "$cleanup_success" = "true" ]; then
            emit_breadcrumb "$(printf '✅ 14: local cleanup status=complete outcome=branch-deleted elapsed=%s' "$(elapsed "$start")")"
            local_status=success
        else
            [ -n "$current_branch" ] || current_branch=unknown
            [ -n "$branch_deleted" ] || branch_deleted=false
            warn_line "$(printf '**⚠ 14: local cleanup — partially failed, branch: %s, deleted: %s (%s)**' "$current_branch" "$branch_deleted" "$(elapsed "$start")")"
            local_status=partial
        fi

        expected_title="$pr_title (#$pr_number)"
        set +e
        out=$("$SCRIPT_DIR/verify-main.sh" --expected-title "$expected_title")
        rc=$?
        set +e
        verified=$(kv_value VERIFIED "$out")
        commit_hash=$(kv_value COMMIT_HASH "$out")
        commit_message=$(kv_value COMMIT_MESSAGE "$out")
        if [ "$rc" -eq 0 ] && [ "$verified" = "true" ]; then
            emit_breadcrumb "$(printf '✅ 15: verify main status=complete sha=%s elapsed=%s' "$commit_hash" "$(elapsed "$start")")"
            verify_status=verified
        else
            warn_line "$(printf '**⚠ 15: verify main — unexpected HEAD: %s "%s". Expected: "%s" (%s)**' "$commit_hash" "$commit_message" "$expected_title" "$(elapsed "$start")")"
            verify_status=unexpected
        fi
    fi

    emit_kv LOCAL_CLEANUP_STATUS "$local_status"
    emit_kv VERIFY_MAIN_STATUS "$verify_status"
    emit_kv FINALIZE_SUBCOMMAND postmerge
    emit_kv FINALIZE_WARNINGS "$WARNINGS"
}

compute_run_outcome() {
    local pr_closed design_only bail_needs_user_input merge draft
    pr_closed=$(read_state PR_CLOSED)
    design_only=$(read_state DESIGN_ONLY_DONE)
    bail_needs_user_input=$(read_state BAIL_NEEDS_USER_INPUT)
    merge=$(read_state MERGE)
    draft=$(read_state DRAFT)

    if [ "$pr_closed" = "true" ]; then
        echo "closed"
    elif [ "$design_only" = "true" ]; then
        echo "design-only"
    elif [ "$bail_needs_user_input" = "true" ]; then
        echo "user-input"
    elif bail_reason_nonempty; then
        echo "blocked"
    elif [ "$merge" != "true" ] || [ "$draft" = "true" ]; then
        echo "pr-opened"
    else
        echo "blocked"
    fi
}

rename_issue() {
    local issue=$1 state=$2 label=$3 repo=$4 out rc failed round_trip body_tmp title
    round_trip=false
    body_tmp=""
    title=""
    if [ -n "$IMPLEMENT_TMPDIR" ] && is_tmp_path "$IMPLEMENT_TMPDIR" && [ -d "$IMPLEMENT_TMPDIR" ]; then
        body_tmp="$IMPLEMENT_TMPDIR/round-trip-input-issue-body-step18-${issue}.txt"
    else
        # set -uo pipefail (no -e) here, so an mktemp failure (full disk,
        # bad TMPDIR) would otherwise leave body_tmp empty and let the
        # later printf > "$body_tmp" write to "" silently. Guard explicitly
        # and skip detection on failure (post-review).
        body_tmp=$(mktemp 2>/dev/null) || body_tmp=""
        if [ -z "$body_tmp" ] || [ ! -f "$body_tmp" ]; then
            warn_line "Step 18: round-trip detection skipped: mktemp failed"
            out=$("$SCRIPT_DIR/tracking-issue-write.sh" rename --issue "$issue" --state "$state" --round-trip "$round_trip" ${repo:+--repo "$repo"})
            rc=$?
            failed=$(kv_value FAILED "$out")
            if [ "$rc" -ne 0 ] || [ "$failed" = "true" ]; then
                warn_line "$(printf '**⚠ 18: tracking-issue rename to %s failed. Continuing.**' "$label")"
                return 1
            fi
            return 0
        fi
    fi
    # Build gh args; pass --repo when available so the body+title fetch
    # targets the same issue scope as the rename call below (FINDING_F2).
    if [ -z "$repo" ]; then
        repo=$("$SCRIPT_DIR/resolve-repo.sh" 2>/dev/null) || repo=""
    fi
    set +e
    if [ -n "$repo" ]; then
        out=$(gh issue view "$issue" --repo "$repo" --json title,body --jq '"TITLE=\(.title // "")\n" + (.body // "")')
    else
        out=$(gh issue view "$issue" --json title,body --jq '"TITLE=\(.title // "")\n" + (.body // "")')
        warn_line "Step 18: round-trip detection: gh issue view executed without --repo (resolve-repo.sh returned empty)"
    fi
    rc=$?
    set +e
    if [ "$rc" -ne 0 ]; then
        # Preserve any stderr the gh call printed by relying on caller's
        # default stderr passthrough; emit our own warn here too (FINDING_F3).
        warn_line "Step 18: round-trip detection skipped: gh issue title/body fetch failed"
        round_trip=false
    elif [ ! -x "$SCRIPT_DIR/round-trip-detect.sh" ]; then
        warn_line "Step 18: round-trip detection skipped: detector unavailable"
        round_trip=false
    else
        # Extract first-line TITLE marker; remainder is body. Empty-title is
        # tolerated (--text-string "" is a no-op for the detector).
        title=$(printf '%s' "$out" | awk 'NR==1 && /^TITLE=/ { sub(/^TITLE=/, ""); print; exit }')
        printf '%s' "$out" | awk 'NR>1 || !/^TITLE=/ { print }' > "$body_tmp"
        set +e
        # Do NOT redirect detector stderr — preserve warn_false signals so
        # operators can see degraded-path diagnostics (FINDING_F3).
        out=$("$SCRIPT_DIR/round-trip-detect.sh" --text-string "$title" --text-file "$body_tmp")
        rc=$?
        set +e
        if [ "$rc" -ne 0 ]; then
            warn_line "Step 18: round-trip detection skipped: detector failed"
            round_trip=false
        else
            round_trip=$(kv_value ROUND_TRIP "$out")
            case "$round_trip" in
                true|false) ;;
                *)
                    warn_line "Step 18: round-trip detection skipped: detector output missing"
                    round_trip=false
                    ;;
            esac
        fi
    fi
    rm -f "$body_tmp" 2>/dev/null || true
    set +e
    if [ -n "$repo" ]; then
        out=$("$SCRIPT_DIR/tracking-issue-write.sh" rename --issue "$issue" --state "$state" --round-trip "$round_trip" --repo "$repo")
    else
        out=$("$SCRIPT_DIR/tracking-issue-write.sh" rename --issue "$issue" --state "$state" --round-trip "$round_trip")
    fi
    rc=$?
    set +e
    failed=$(kv_value FAILED "$out")
    if [ "$rc" -ne 0 ] || [ "$failed" = "true" ]; then
        warn_line "$(printf '**⚠ 18: tracking-issue rename to %s failed. Continuing.**' "$label")"
        return 1
    fi
    return 0
}

auto_stash_stalled_changes() {
    local issue_number=$1 stall_step=$2 repo_root status_out stash_out rc stash_ref
    local timestamp label issue_label

    AUTO_STASH_REF=""
    set +e
    repo_root=$(git rev-parse --show-toplevel 2>/dev/null)
    rc=$?
    set +e
    if [ "$rc" -ne 0 ] || [ -z "$repo_root" ]; then
        warn_line '**⚠ 18: auto-stash failed: could not resolve repo root. Continuing.**'
        return 0
    fi

    set +e
    status_out=$(git -C "$repo_root" status --porcelain 2>/dev/null)
    rc=$?
    set +e
    # On `git status` failure we cannot tell clean from dirty; warn so the
    # operator does not falsely read teardown silence as proof of a clean tree.
    if [ "$rc" -ne 0 ]; then
        warn_line '**⚠ 18: auto-stash skipped: git status failed; cannot assert clean tree. Continuing.**'
        return 0
    fi
    if [ -z "$status_out" ]; then
        return 0
    fi

    timestamp=$(date -u +%Y%m%dT%H%M%SZ)
    issue_label=${issue_number:-unknown}
    label="larch-stalled-${issue_label}-${stall_step} ${timestamp}"

    set +e
    stash_out=$(git -C "$repo_root" stash push -u -m "$label" 2>&1)
    rc=$?
    set +e
    if [ "$rc" -ne 0 ]; then
        warn_line "$(printf '**⚠ 18: auto-stash failed: %s. Continuing.**' "$stash_out")"
        return 0
    fi

    # Resolve the stash ref by matching our label rather than blindly taking
    # `stash list -1`. Concurrent activity could insert another stash on top;
    # `-1` would then surface someone else's ref. We grep for the literal
    # label we just pushed.
    set +e
    stash_ref=$(git -C "$repo_root" stash list --format='%gD %gs' 2>/dev/null \
        | grep -F -- "$label" \
        | head -n 1 \
        | awk '{print $1}')
    rc=$?
    set +e
    if [ "$rc" -ne 0 ] || [ -z "$stash_ref" ]; then
        # Fallback to the previous heuristic; emit a warning so a missing or
        # mismatched ref is observable.
        set +e
        stash_ref=$(git -C "$repo_root" stash list -1 --format='%gD' 2>/dev/null)
        rc=$?
        set +e
        if [ "$rc" -ne 0 ] || [ -z "$stash_ref" ]; then
            warn_line '**⚠ 18: auto-stash succeeded but stash ref could not be resolved. Continuing.**'
            stash_ref=""
        fi
    fi
    AUTO_STASH_REF=$stash_ref
}

write_stalled_run_sentinel() {
    local issue_number=$1 issue_url=$2 stall_step=$3 stash_ref=$4
    local git_dir tmp timestamp rc

    set +e
    git_dir=$(git rev-parse --git-dir 2>/dev/null)
    rc=$?
    set +e
    if [ "$rc" -ne 0 ] || [ -z "$git_dir" ]; then
        warn_line '**⚠ 18: stalled-run sentinel write failed: could not resolve git dir. Continuing.**'
        return 1
    fi

    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    tmp="${git_dir}/larch-stalled-run.txt.tmp.$$"
    if ! {
        printf 'ISSUE_NUMBER=%s\n' "$issue_number"
        printf 'ISSUE_URL=%s\n' "$issue_url"
        printf 'STALL_STEP=%s\n' "$stall_step"
        printf 'STASH_REF=%s\n' "$stash_ref"
        printf 'TIMESTAMP=%s\n' "$timestamp"
    } > "$tmp"; then
        warn_line '**⚠ 18: stalled-run sentinel write failed. Continuing.**'
        return 1
    fi
    if ! mv "$tmp" "${git_dir}/larch-stalled-run.txt" 2>/dev/null; then
        rm -f "$tmp" 2>/dev/null || true
        warn_line '**⚠ 18: stalled-run sentinel write failed. Continuing.**'
        return 1
    fi
    return 0
}

kill_session_background_processes() {
    [ -n "$IMPLEMENT_TMPDIR" ] || return 0
    local my_pid=$$
    local ppid
    ppid=$(ps -o ppid= -p "$my_pid" 2>/dev/null | tr -d ' ') || ppid=""
    local pid killed=0 survivors=0 pids_out canonical_tmpdir
    canonical_tmpdir=$(cd "$IMPLEMENT_TMPDIR" 2>/dev/null && pwd -P) || canonical_tmpdir=""
    # Use awk index() for fixed-string match: pgrep -f and grep -E treat the path as a regex,
    # and larch session tmpdirs contain dots that would match unintended characters. Check the
    # lexical and physical tmpdir forms because /tmp may appear as /private/tmp in process argv.
    pids_out=$(ps -A -o pid= -o args= 2>/dev/null | awk -v needle="$IMPLEMENT_TMPDIR" -v physical="$canonical_tmpdir" '
        index($0, needle) > 0 || (physical != "" && physical != needle && index($0, physical) > 0) {print $1}
    ') || return 0
    [ -n "$pids_out" ] || return 0
    while IFS= read -r pid; do
        [ -z "$pid" ] && continue
        [ "$pid" = "$my_pid" ] && continue
        [ -n "$ppid" ] && [ "$pid" = "$ppid" ] && continue
        if kill -TERM "$pid" 2>/dev/null; then killed=$((killed + 1)); fi
    done <<< "$pids_out"
    if [ "$killed" -gt 0 ]; then
        sleep 1
        while IFS= read -r pid; do
            [ -z "$pid" ] && continue
            [ "$pid" = "$my_pid" ] && continue
            [ -n "$ppid" ] && [ "$pid" = "$ppid" ] && continue
            if kill -0 "$pid" 2>/dev/null; then
                if kill -KILL "$pid" 2>/dev/null; then survivors=$((survivors + 1)); fi
            fi
        done <<< "$pids_out"
        warn_line "$(printf '**⚠ 18: killed %d stale background process(es) from this session (SIGKILL applied to %d survivor(s)).**' "$killed" "$survivors")"
    fi
}

run_teardown() {
    local start issue_number repo repo_unavailable stall_tracking done_rename_applied pr_number design_only pr_closed
    local rename_branch rename_status out rc value issue_url cleanup_rc
    local stall_step stash_ref sentinel_written

    start=$(date +%s)
    load_and_validate_state
    validate_tmpdir_arg

    issue_number=$(read_state ISSUE_NUMBER)
    repo=$(read_state REPO)
    repo_unavailable=$(read_state REPO_UNAVAILABLE)
    stall_tracking=$(read_state STALL_TRACKING)
    done_rename_applied=$(read_state DONE_RENAME_APPLIED)
    pr_number=$(read_state PR_NUMBER)
    design_only=$(read_state DESIGN_ONLY_DONE)
    rename_branch=skipped
    rename_status=skipped
    issue_url=""
    stall_step=$(read_state STALL_STEP unknown)
    stash_ref=""
    sentinel_written=false

    if [ -n "$issue_number" ] && [ "$repo_unavailable" = "false" ]; then
        if [ "$stall_tracking" = "true" ]; then
            rename_branch=A
            set +e
            out=$("$SCRIPT_DIR/get-issue-info.sh" --issue "$issue_number" --field state)
            rc=$?
            set +e
            value=$(kv_value VALUE "$out")
            if [ "$rc" -eq 0 ] && [ "$value" = "OPEN" ]; then
                if rename_issue "$issue_number" stalled STALLED "$repo"; then
                    rename_status=ok
                else
                    rename_status=failed
                fi
            fi
        elif [ "$done_rename_applied" != "true" ] && { [ -n "$pr_number" ] || [ "$design_only" = "true" ]; }; then
            rename_branch=B
            if rename_issue "$issue_number" "done" DONE "$repo"; then
                rename_status=ok
            else
                rename_status=failed
            fi
        else
            rename_branch=C
            rename_status=skipped
        fi
    fi

    if [ -n "$issue_number" ] && [ "$repo_unavailable" = "false" ]; then
        set +e
        out=$("$SCRIPT_DIR/get-issue-info.sh" --issue "$issue_number" --field url)
        rc=$?
        set +e
        value=$(kv_value VALUE "$out")
        if [ "$rc" -eq 0 ] && [ -n "$value" ]; then
            issue_url=$value
        fi
    fi

    if [ "$stall_tracking" = "true" ]; then
        auto_stash_stalled_changes "$issue_number" "$stall_step"
        stash_ref=$AUTO_STASH_REF
        if write_stalled_run_sentinel "$issue_number" "$issue_url" "$stall_step" "$stash_ref"; then
            sentinel_written=true
        fi
    fi

    # Halt-protection sentinel: release the post-/design Stop hook before
    # cleanup target validation so refused cleanup paths cannot trap exit.
    # Surface failure so a silent ENOSPC / FS-permission / read-only-mount
    # mishap does not leave the Stop hook blocking the next session: emit a
    # warning via warn_line (writes to stdout and increments
    # FINALIZE_WARNINGS) and continue with best-effort posture.
    if ! touch "$IMPLEMENT_TMPDIR/.run-cleaned-up" 2>/dev/null; then
        warn_line '**⚠ 18: halt-protection sentinel write failed (touch .run-cleaned-up); Stop hook may continue blocking on next session. Continuing.**'
    fi

    # Flush any pending larch-log writes for the current run (best-effort).
    # This handles stalled/failed runs where the ci-merge flush in ship-pr.sh
    # never ran. Root-cause prevention lives in ship-pr.sh (ci-merge flush) and
    # write_version_reasoning_fragment (correct run-id from state file).
    local larch_flush_run_id manifest_path_teardown larch_recovery_ok
    larch_flush_run_id=$(read_state RUN_ID)
    flush_execution_issues_safety_net
    if [ -n "$larch_flush_run_id" ] && [ "$repo_unavailable" = "false" ]; then
        manifest_path_teardown="$IMPLEMENT_TMPDIR/larch-logs/implement/$larch_flush_run_id/manifest.json"
        larch_recovery_ok=true
        if [ ! -f "$manifest_path_teardown" ]; then
            if [ -n "$issue_number" ]; then
                "$SCRIPT_DIR/larch-log.sh" init \
                    --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                    --skill implement --run-id "$larch_flush_run_id" \
                    --issue "$issue_number" \
                    2>/dev/null || { warn_line '**⚠ 18: larch-log manifest recovery init failed. Continuing.**'; larch_recovery_ok=false; }
            else
                "$SCRIPT_DIR/larch-log.sh" init \
                    --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                    --skill implement --run-id "$larch_flush_run_id" \
                    2>/dev/null || { warn_line '**⚠ 18: larch-log manifest recovery init failed. Continuing.**'; larch_recovery_ok=false; }
            fi
            if [ "$larch_recovery_ok" = "true" ]; then
                "$SCRIPT_DIR/larch-log.sh" manifest \
                    --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                    --skill implement --run-id "$larch_flush_run_id" \
                    --field "status=partial" \
                    --field "recovery_reason=manifest_lost_mid_run" \
                    2>/dev/null || warn_line '**⚠ 18: larch-log manifest recovery partial-tag failed. Continuing.**'
            fi
        fi
        # Finalize manifest status before committing so the update lands in the
        # same flush commit. Best-effort recovery above synthesizes a manifest
        # when the run directory survived but manifest.json was lost mid-run.
        # Skip all manifest + commit calls when synthesis failed (larch_recovery_ok=false)
        # to avoid committing a manifest-less run directory.
        if [ "$larch_recovery_ok" = "false" ]; then
            :
        elif [ "$stall_tracking" = "true" ]; then
            "$SCRIPT_DIR/larch-log.sh" manifest \
                --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                --skill implement --run-id "$larch_flush_run_id" \
                --field "status=stalled" \
                --field "stalled_at_step=$stall_step" \
                2>/dev/null || true
        elif [ -n "$pr_number" ]; then
            "$SCRIPT_DIR/larch-log.sh" manifest \
                --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                --skill implement --run-id "$larch_flush_run_id" \
                --field "status=done" \
                --field "pr_number=$pr_number" \
                2>/dev/null || true
        elif [ "$design_only" = "true" ]; then
            "$SCRIPT_DIR/larch-log.sh" manifest \
                --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                --skill implement --run-id "$larch_flush_run_id" \
                --field "status=done" \
                2>/dev/null || true
        fi
    fi

    kill_session_background_processes

    if verify_cleanup_target; then
        set +e
        out=$("$SCRIPT_DIR/cleanup-tmpdir.sh" --dir "$IMPLEMENT_TMPDIR")
        cleanup_rc=$?
        set +e
        if [ "$cleanup_rc" -ne 0 ]; then
            warn_line '**⚠ 18: cleanup-tmpdir failed. Continuing.**'
        fi
    else
        :
    fi

    if [ -n "$issue_url" ]; then
        emit_breadcrumb "$(printf '📎 Tracking issue: %s' "$issue_url")"
    fi

    emit_breadcrumb "$(printf '✅ 18: cleanup status=complete elapsed=%s' "$(elapsed "$start")")"
    emit_kv RENAME_BRANCH "$rename_branch"
    emit_kv RENAME_STATUS "$rename_status"
    emit_kv ISSUE_URL "$issue_url"
    emit_kv STASH_REF "$stash_ref"
    emit_kv SENTINEL_WRITTEN "$sentinel_written"
    emit_kv FINALIZE_SUBCOMMAND teardown
    emit_kv FINALIZE_WARNINGS "$WARNINGS"
}

main() {
    local subcommand
    [ $# -gt 0 ] || die_usage "missing subcommand"
    subcommand=$1
    shift

    case "$subcommand" in
        postbump)
            parse_postbump_args "$@"
            run_postbump
            ;;
        postmerge)
            parse_common_args "$@"
            run_postmerge
            ;;
        teardown)
            parse_common_args "$@"
            run_teardown
            ;;
        *) die_usage "unknown subcommand: $subcommand" ;;
    esac
}

main "$@"
