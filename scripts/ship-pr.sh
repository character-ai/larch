#!/usr/bin/env bash
# ship-pr.sh — Deterministic /implement post-review state machine.

set -uo pipefail
# Intentionally no `set -e`: this script composes best-effort helpers whose
# outcome is communicated through stdout envelopes. Each helper call captures
# rc explicitly so state can be checkpointed before returning to SKILL.md.
LC_ALL=C
export LC_ALL

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-net.sh
source "$SCRIPT_DIR/lib-net.sh" || { larch_err "ship-pr.sh: failed to source lib-net.sh"; exit 1; }
[[ "${LARCH_LIB_NET_LOADED:-}" == "1" ]] || { larch_err "ship-pr.sh: lib-net.sh sourced but sentinel missing"; exit 1; }
# shellcheck source=scripts/lib-finalize-state-keys.sh
source "$SCRIPT_DIR/lib-finalize-state-keys.sh" || { larch_err "ship-pr.sh: failed to source lib-finalize-state-keys.sh"; exit 1; }
[[ "${LARCH_LIB_FINALIZE_STATE_KEYS_LOADED:-}" == "1" ]] || { larch_err "ship-pr.sh: lib-finalize-state-keys.sh sourced but sentinel missing"; exit 1; }

STATE_FILE=""
IMPLEMENT_TMPDIR=""
MERGE=""
DRAFT=""
FORKED_TARGET=""
AUTO_MODE="false"
NO_ADMIN_FALLBACK="false"
NO_LOGS_COMMIT="false"
REPO_ARG=""
RESUME_PHASE=""

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage:
  ship-pr.sh --state-file PATH --implement-tmpdir PATH --merge true|false --draft true|false --forked true|false --repo OWNER/REPO [--auto-mode true|false] [--no-admin-fallback true|false] [--no-logs-commit true|false] [--resume-phase PHASE]
USAGE
}

LAST_LINT_FIX_DELTA_PATHS_FILE=""
ALL_LINT_FIX_DELTA_PATHS_FILE=""

capture_dirty_paths() {
    {
        git diff --name-only HEAD 2>/dev/null || true
        git ls-files --others --exclude-standard 2>/dev/null || true
    } | awk 'NF && !seen[$0]++ { print }'
}

capture_tracked_dirty_paths() {
    git diff --name-only HEAD 2>/dev/null || true
}

capture_untracked_dirty_paths() {
    git ls-files --others --exclude-standard 2>/dev/null || true
}

append_unique_paths_file() {
    local target=$1 source=${2:-}
    [[ -n "$target" && -n "$source" && -f "$source" ]] || return 0
    mkdir -p "$(dirname "$target")"
    if [[ -f "$target" ]]; then
        awk 'NF && !seen[$0]++ { print }' "$target" "$source" > "${target}.tmp" && mv "${target}.tmp" "$target"
    else
        awk 'NF && !seen[$0]++ { print }' "$source" > "$target"
    fi
}

run_lint_fix_loop_capture() {
    local fail_file=$1 site=$2 redacted_log=$3 out_var=$4 rc_var=$5
    local output rc had_errexit=0
    case $- in *e*) had_errexit=1 ;; esac
    set +e
    output=$("$SCRIPT_DIR/lint-fix-loop.sh" \
        --tmpdir "$IMPLEMENT_TMPDIR" \
        --site "$site" \
        --checks-log "$redacted_log" 2>"$fail_file")
    rc=$?
    (( had_errexit )) && set -e
    printf -v "$out_var" '%s' "$output"
    printf -v "$rc_var" '%s' "$rc"
}

collect_ci_stage_paths() {
    local vendor_tracked_dirty_file=$1 vendor_untracked_dirty_file=$2 tracked_dirty_file=$3 untracked_dirty_file=$4 allowlisted_delta_file=$5
    awk '
        FNR == NR {
            if (NF) vendor_tracked[$0]=1
            next
        }
        FILENAME == ARGV[2] {
            if (NF) vendor_untracked[$0]=1
            next
        }
        FILENAME == ARGV[3] {
            if (NF && !seen[$0]++) print
            next
        }
        FILENAME == ARGV[4] {
            if (NF) current_untracked[$0]=1
            next
        }
        {
            if (!NF || seen[$0]++) next
            if (current_untracked[$0]) print
        }
    ' \
        "${vendor_tracked_dirty_file:-/dev/null}" \
        "${vendor_untracked_dirty_file:-/dev/null}" \
        "${tracked_dirty_file:-/dev/null}" \
        "${untracked_dirty_file:-/dev/null}" \
        "${allowlisted_delta_file:-/dev/null}"
}

die_usage() {
    larch_err "ship-pr.sh: $1"
    usage
    exit 2
}

is_bool() {
    case "$1" in true|false) return 0 ;; *) return 1 ;; esac
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

while [ $# -gt 0 ]; do
    case "$1" in
        --state-file) [ $# -ge 2 ] || die_usage "--state-file requires a value"; STATE_FILE=$2; shift 2 ;;
        --implement-tmpdir) [ $# -ge 2 ] || die_usage "--implement-tmpdir requires a value"; IMPLEMENT_TMPDIR=$2; shift 2 ;;
        --merge) [ $# -ge 2 ] || die_usage "--merge requires a value"; MERGE=$2; shift 2 ;;
        --draft) [ $# -ge 2 ] || die_usage "--draft requires a value"; DRAFT=$2; shift 2 ;;
        --forked) [ $# -ge 2 ] || die_usage "--forked requires a value"; FORKED_TARGET=$2; shift 2 ;;
        --auto-mode) [ $# -ge 2 ] || die_usage "--auto-mode requires a value"; AUTO_MODE=$2; shift 2 ;;
        --no-admin-fallback) [ $# -ge 2 ] || die_usage "--no-admin-fallback requires a value"; NO_ADMIN_FALLBACK=$2; shift 2 ;;
        --no-logs-commit) [ $# -ge 2 ] || die_usage "--no-logs-commit requires a value"; NO_LOGS_COMMIT=$2; shift 2 ;;
        --repo) [ $# -ge 2 ] || die_usage "--repo requires a value"; REPO_ARG=$2; shift 2 ;;
        --resume-phase) [ $# -ge 2 ] || die_usage "--resume-phase requires a value"; RESUME_PHASE=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) die_usage "unknown option: $1" ;;
    esac
done

[ -n "$STATE_FILE" ] || die_usage "--state-file is required"
[ -n "$IMPLEMENT_TMPDIR" ] || die_usage "--implement-tmpdir is required"
is_tmp_path "$STATE_FILE" || die_usage "--state-file must be under /tmp/, /private/tmp/, /var/folders/, or the larch cache sessions root"
is_tmp_path "$IMPLEMENT_TMPDIR" || die_usage "--implement-tmpdir must be under /tmp/, /private/tmp/, /var/folders/, or the larch cache sessions root"
[ -d "$IMPLEMENT_TMPDIR" ] || die_usage "--implement-tmpdir must exist"
case "$STATE_FILE" in "$IMPLEMENT_TMPDIR"/*) ;; *) die_usage "--state-file must live under --implement-tmpdir" ;; esac
is_bool "$AUTO_MODE" || die_usage "--auto-mode must be true or false"
is_bool "$NO_ADMIN_FALLBACK" || die_usage "--no-admin-fallback must be true or false"
is_bool "$NO_LOGS_COMMIT" || die_usage "--no-logs-commit must be true or false"
[ -z "$MERGE" ] || is_bool "$MERGE" || die_usage "--merge must be true or false"
[ -z "$DRAFT" ] || is_bool "$DRAFT" || die_usage "--draft must be true or false"
[ -z "$FORKED_TARGET" ] || is_bool "$FORKED_TARGET" || die_usage "--forked must be true or false"
# Export so child processes inherit the session tmpdir path regardless of
# whether the caller shell already had it exported (e.g. after a session
# restart where the orchestrator env was fresh). Log helpers resolve their run
# context from this tmpdir.
export IMPLEMENT_TMPDIR
export LARCH_NO_LOGS_COMMIT="$NO_LOGS_COMMIT"

validate_state_syntax() {
    local line line_no
    line_no=0
    while IFS= read -r line || [ -n "$line" ]; do
        line_no=$((line_no + 1))
        case "$line" in ""|\#*) continue ;; esac
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

write_post_merge_sentinel() {
    local tmp sentinel
    sentinel="$IMPLEMENT_TMPDIR/post-merge-sentinel"
    tmp="$IMPLEMENT_TMPDIR/.post-merge-sentinel.$$"
    if ! printf 'MERGE_RESULT=%s\n' "$(read_state MERGE_RESULT)" > "$tmp" || ! mv -f "$tmp" "$sentinel"; then
        rm -f "$tmp" 2>/dev/null || true
        larch_err "ship-pr.sh: failed to write post-merge sentinel: $sentinel"
        exit_stall 12b
    fi
}

read_session_plan_file() {
    local session_env="$IMPLEMENT_TMPDIR/session-env.sh"
    [ -f "$session_env" ] || return 0
    awk 'BEGIN{k="PLAN_FILE"; kl=length(k)} substr($0,1,kl)==k && substr($0,kl+1,1)=="=" {print substr($0,kl+2); exit}' "$session_env"
}

# Returns a validated plan file path (under IMPLEMENT_TMPDIR, file exists) or empty.
# Logs a Warnings entry and returns empty on security/availability violations.
resolve_plan_file() {
    local path
    path=$(read_session_plan_file)
    [ -n "$path" ] || return 0
    case "$path" in
        "$IMPLEMENT_TMPDIR"/*)
            ;;
        *)
            "$SCRIPT_DIR/append-execution-issue.sh" \
                --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
                --category Warnings \
                --entry "PLAN_FILE ($path) is outside IMPLEMENT_TMPDIR; skipping plan context." \
                >/dev/null 2>&1 || true
            return 0 ;;
    esac
    if [ ! -f "$path" ]; then
        "$SCRIPT_DIR/append-execution-issue.sh" \
            --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
            --category Warnings \
            --entry "PLAN_FILE ($path) set but file not found; proceeding without plan context." \
            >/dev/null 2>&1 || true
        return 0
    fi
    printf '%s\n' "$path"
}

write_initial_state() {
    local tmp branch repo issue run_id session_id clone_tag clone_tag_full
    mkdir -p "$IMPLEMENT_TMPDIR" || die_usage "cannot create --implement-tmpdir"
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
    repo=$REPO_ARG
    if [ -z "$repo" ]; then
        repo=$("$SCRIPT_DIR/resolve-repo.sh" 2>/dev/null | awk -F= '$1=="REPO"{print substr($0,index($0,"=")+1); exit}' || true)
    fi
    issue=""
    run_id="${LARCH_RUN_ID:-${RUN_ID:-$(basename "$IMPLEMENT_TMPDIR")}}"
    session_id=$(cat "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || echo "")
    if [ -n "${CLONE_TAG:-}" ]; then
        clone_tag_full=$CLONE_TAG
    else
        clone_tag=$(basename "$PWD")
        clone_tag_full=$(printf '%s' "$clone_tag" | tr -c 'A-Za-z0-9_-' '_')
        clone_tag_full=${clone_tag_full%????????????????????????????????*}
        clone_tag_full=$(printf '%.32s' "$clone_tag_full")
        [ -n "$clone_tag_full" ] || clone_tag_full="_"
    fi
    tmp="$STATE_FILE.tmp.$$"
    {
        printf 'PHASE=checks\n'
        printf 'BRANCH_NAME=%s\n' "$branch"
        printf 'ISSUE_NUMBER=%s\n' "$issue"
        printf 'RUN_ID=%s\n' "$run_id"
        printf 'REPO=%s\n' "$repo"
        printf 'REPO_UNAVAILABLE=%s\n' "$([ -n "$repo" ] && echo false || echo true)"
        printf 'FORKED_TARGET=%s\n' "${FORKED_TARGET:-false}"
        printf 'HAS_BUMP=true\n'
        printf 'BUMP_TYPE=NONE\n'
        printf 'NEW_VERSION=\n'
        printf 'MERGE=%s\n' "${MERGE:-false}"
        printf 'DRAFT=%s\n' "${DRAFT:-false}"
        printf 'DEFERRED=false\n'
        printf 'PR_CLOSED=false\n'
        printf 'DONE_RENAME_APPLIED=false\n'
        printf 'STALL_TRACKING=false\n'
        printf 'STALL_STEP=\n'
        printf 'BAIL_NEEDS_USER_INPUT=false\n'
        printf 'BAIL_REASON=\n'
        printf 'CI_PASSED=false\n'
        printf 'OOS_PENDING=false\n'
        printf 'PR_NUMBER=\n'
        printf 'PR_URL=\n'
        printf 'PR_TITLE=\n'
        printf 'RESUME_PHASE=\n'
        printf 'CALLER_KIND=\n'
        printf 'REBASE_COUNT=0\n'
        printf 'FIX_ATTEMPTS=0\n'
        printf 'ITERATION=0\n'
        printf 'TRANSIENT_RETRIES=0\n'
        printf 'FAILED_RUN_ID=\n'
        printf 'MANIFEST_PATH=%s\n' "${MANIFEST_PATH:-}"
        printf 'TOOL_LABEL=%s\n' "${TOOL_LABEL:-claude}"
        printf 'DESIGN_ONLY_DONE=false\n'
        printf 'EXPECTED_SESSION_ID=%s\n' "$session_id"
        printf 'EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-%s-\n' "$clone_tag_full"
    } > "$tmp" && mv "$tmp" "$STATE_FILE"
}

if [ ! -e "$STATE_FILE" ]; then
    write_initial_state
fi
[ -r "$STATE_FILE" ] || die_usage "--state-file must be readable"
validate_state_syntax

require_key() {
    state_has_key "$1" || die_usage "state-file missing required key: $1"
}

for key in \
    PHASE BRANCH_NAME ISSUE_NUMBER RUN_ID REPO REPO_UNAVAILABLE FORKED_TARGET \
    HAS_BUMP BUMP_TYPE NEW_VERSION MERGE DRAFT DEFERRED PR_CLOSED \
    DONE_RENAME_APPLIED STALL_TRACKING STALL_STEP BAIL_NEEDS_USER_INPUT \
    CI_PASSED OOS_PENDING PR_NUMBER PR_URL PR_TITLE RESUME_PHASE CALLER_KIND \
    REBASE_COUNT FIX_ATTEMPTS ITERATION TRANSIENT_RETRIES FAILED_RUN_ID \
    MANIFEST_PATH TOOL_LABEL
do
    require_key "$key"
done

for key in REPO_UNAVAILABLE FORKED_TARGET HAS_BUMP MERGE DRAFT DEFERRED PR_CLOSED DONE_RENAME_APPLIED STALL_TRACKING BAIL_NEEDS_USER_INPUT CI_PASSED OOS_PENDING; do
    is_bool "$(read_state "$key")" || die_usage "state-file key $key must be true or false"
done

# Fail fast at the entry boundary if MANIFEST_PATH points at a non-JSON file
# (e.g. the /design Step 5 manifest.env shell KV file mistakenly routed here).
# See issue #2233: without this guard, a bad MANIFEST_PATH surfaces four phases
# downstream inside collect_changelog_bullets with no actionable diagnostic.
manifest_path_check=$(read_state MANIFEST_PATH)
if [ -n "$manifest_path_check" ]; then
    if [ ! -r "$manifest_path_check" ] || ! jq empty "$manifest_path_check" >/dev/null 2>&1; then
        die_usage "MANIFEST_PATH must be empty or a readable JSON file (got: $manifest_path_check)"
    fi
fi
unset manifest_path_check

kv_value() {
    local key=$1 input=$2
    printf '%s\n' "$input" | awk -F= -v k="$key" '$1 == k {print substr($0, index($0, "=") + 1); found=1} END {if (!found) print ""}' | tail -n 1
}

capture_command_output() {
    local __outvar=$1 __fail_file=$2
    shift 2
    local __captured __rc
    if __captured=$("$@" 2>"$__fail_file"); then
        __rc=0
    else
        __rc=$?
    fi
    printf -v "$__outvar" '%s' "$__captured"
    return "$__rc"
}

resolve_existing_file() {
    local input=$1 dir base real_dir
    [ -n "$input" ] || return 1
    [ -f "$input" ] || return 1
    [ ! -L "$input" ] || return 1
    dir=$(dirname "$input")
    base=$(basename "$input")
    real_dir=$(cd "$dir" 2>/dev/null && pwd -P) || return 1
    printf '%s/%s\n' "$real_dir" "$base"
}

resolve_checks_log_path() {
    local candidate resolved allowed_root
    candidate=$1
    resolved=$(resolve_existing_file "$candidate") || return 1
    allowed_root=$(cd "$IMPLEMENT_TMPDIR" 2>/dev/null && pwd -P) || return 1
    case "$resolved" in
        "$allowed_root"/*) printf '%s\n' "$resolved" ;;
        *) return 1 ;;
    esac
}

semver_lt() {
    local a_maj a_min a_pat b_maj b_min b_pat
    IFS='.' read -r a_maj a_min a_pat <<< "$1"
    IFS='.' read -r b_maj b_min b_pat <<< "$2"
    if [[ $a_maj -lt $b_maj ]]; then return 0; fi
    if [[ $a_maj -gt $b_maj ]]; then return 1; fi
    if [[ $a_min -lt $b_min ]]; then return 0; fi
    if [[ $a_min -gt $b_min ]]; then return 1; fi
    if [[ $a_pat -lt $b_pat ]]; then return 0; fi
    return 1
}

rewrite_reasoning_new_version() {
    local file=$1 classified_version=$2 origin_version=$3 corrected_version=$4 tmp_file
    [ -n "$file" ] && [ -f "$file" ] || return 1
    tmp_file="${file}.tmp.$$"
    awk -v new_version="$corrected_version" \
        -v classified="$classified_version" \
        -v origin="$origin_version" '
        BEGIN { replaced=0 }
        /^- \*\*New version\*\*: / {
            print "- **New version**: `" new_version "`"
            replaced=1
            next
        }
        { print }
        END {
            if (replaced) {
                print ""
                print "### Rebase + Re-bump Correction"
                print ""
                print "- **Classified version**: `" classified "`"
                print "- **origin/main version at correction time**: `" origin "`"
                print "- **Corrected version applied by `ship-pr.sh`**: `" new_version "`"
                exit 0
            }
            exit 3
        }
    ' "$file" > "$tmp_file" &&
        grep -Fqx -- "- **New version**: \`$corrected_version\`" "$tmp_file" &&
        mv "$tmp_file" "$file"
    local rc=$?
    [ $rc -eq 0 ] || rm -f "$tmp_file"
    return $rc
}

write_corrected_reasoning_fallback() {
    local file=$1 classified_version=$2 origin_version=$3 corrected_version=$4 tmp_file
    [ -n "$file" ] || return 1
    tmp_file="$(dirname "$file")/bump-version-reasoning-corrected-$$.md"
    {
        printf '%s\n\n' '# Version Bump Reasoning'
        printf '%s\n\n' '## Result: Corrected after rebase'
        printf -- "- **New version**: \`%s\`\n\n" "$corrected_version"
        printf '%s\n\n' '### Rebase + Re-bump Correction'
        printf -- "- **Classified version**: \`%s\`\n" "$classified_version"
        printf -- "- **origin/main version at correction time**: \`%s\`\n" "$origin_version"
        printf -- "- **Corrected version applied by \`ship-pr.sh\`**: \`%s\`\n" "$corrected_version"
        if [ -f "$file" ]; then
            printf '\n%s\n\n' '### Original reasoning snapshot'
            cat "$file"
            printf '\n'
        fi
    } > "$tmp_file" || {
        rm -f "$tmp_file"
        return 1
    }
    printf '%s\n' "$tmp_file"
}

FAILURE_LOG_SEQ=0

failure_capture_path() {
    local phase=$1
    FAILURE_LOG_SEQ=$((FAILURE_LOG_SEQ + 1))
    printf '%s/ship-pr-fail-%s-%s.log' "$IMPLEMENT_TMPDIR" "$phase" "$FAILURE_LOG_SEQ"
}

append_tool_failure_local() {
    local site="" tool="" exit_code="" category="Tool Failures" output_file="" log_tmpdir
    while [ $# -gt 0 ]; do
        case "$1" in
            --site) site=$2; shift 2 ;;
            --tool) tool=$2; shift 2 ;;
            --exit-code) exit_code=$2; shift 2 ;;
            --category) category=$2; shift 2 ;;
            --output-file) output_file=$2; shift 2 ;;
            *) larch_err "ship-pr.sh: append_tool_failure_local: unknown option: $1"; return 2 ;;
        esac
    done
    log_tmpdir=$(read_state IMPLEMENT_TMPDIR "$IMPLEMENT_TMPDIR")
    # Re-validate the state-supplied tmpdir against the same allowed-roots
    # set as the argv-supplied one. A tampered ship-pr-state.sh value must
    # NOT redirect failure logging outside the validated session tree.
    if [ -n "$log_tmpdir" ] && ! is_tmp_path "$log_tmpdir"; then
        larch_err "ship-pr.sh: refusing state-supplied IMPLEMENT_TMPDIR outside allowed roots: $log_tmpdir"
        log_tmpdir="$IMPLEMENT_TMPDIR"
    fi
    if [ -z "$log_tmpdir" ] || [ ! -x "$SCRIPT_DIR/append-tool-failure.sh" ]; then
        larch_err "ship-pr.sh: cannot append tool failure for $tool (site=$site); helper or tmpdir unavailable"
        # Pipe the capture through redact-secrets.sh before stderr replay so
        # the fallback path mirrors the success-path --redact behavior and
        # never leaks tokens to operator transcripts.
        if [ -n "$output_file" ] && [ -f "$output_file" ]; then
            if [ -x "$SCRIPT_DIR/redact-secrets.sh" ]; then
                "$SCRIPT_DIR/redact-secrets.sh" < "$output_file" | while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done || \
                    while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done < "$output_file"
            else
                while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done < "$output_file"
            fi
        fi
        return 0
    fi
    # Tee append-tool-failure diagnostics to a sibling log so post-mortem can
    # see when the failure-logging helper itself failed (issue: operators
    # otherwise lose signal that the verbatim record never landed).
    local append_diag="$log_tmpdir/ship-pr-append-failure.log"
    if ! "$SCRIPT_DIR/append-tool-failure.sh" \
        --log "$log_tmpdir/execution-issues.md" \
        --site "$site" \
        --tool "$tool" \
        --exit-code "$exit_code" \
        --category "$category" \
        --output-file "$output_file" \
        --redact >>"$append_diag" 2>&1; then
        larch_err "ship-pr.sh: append-tool-failure.sh failed for $tool (site=$site); see $append_diag"
    fi
    return 0
}

record_failure() {
    local site=$1 tool=$2 exit_code=$3 output_file=$4 category=${5:-Tool Failures}
    emit_kv FAILURE_DETAIL_LOG "$output_file"
    append_tool_failure_local \
        --site "$site" \
        --tool "$tool" \
        --exit-code "$exit_code" \
        --category "$category" \
        --output-file "$output_file"
}

state_set() {
    local key=$1 value=$2 tmp
    tmp="$STATE_FILE.tmp.$$"
    awk -v k="$key" -v v="$value" -F= '
        BEGIN { written = 0 }
        $1 == k {
            print k "=" v
            written = 1
            next
        }
        { print }
        END {
            if (!written) print k "=" v
        }
    ' "$STATE_FILE" > "$tmp" && mv "$tmp" "$STATE_FILE"
}

state_set_many() {
    while [ $# -gt 0 ]; do
        state_set "$1" "$2"
        shift 2
    done
}

advance_phase() {
    state_set PHASE "$1"
}

mark_stall() {
    emit_breadcrumb "⛔ ship-pr: stalled at step $1"
    state_set_many STALL_TRACKING true STALL_STEP "$1"
}

clear_stall_keys_for_postmerge() {
    state_set_many BAIL_REASON "" STALL_TRACKING false STALL_STEP ""
}

exit_stall() {
    mark_stall "$1"
    exit 4
}

exit_transient_net() {
    emit_breadcrumb "⚠ ship-pr: transient network failure"
    # Truncate to first line to keep BAIL_REASON a single KEY=value line in state.
    local reason
    reason=$(printf '%s' "$1" | head -1 | cut -c1-200)
    state_set_many BAIL_REASON "$reason" STALL_TRACKING false
    exit 6
}

write_postbump_state() {
    local tmp
    tmp="$IMPLEMENT_TMPDIR/postbump-state.sh.tmp.$$"
    {
        printf 'BRANCH_NAME=%s\n' "$(read_state BRANCH_NAME)"
        printf 'ISSUE_NUMBER=%s\n' "$(read_state ISSUE_NUMBER)"
        printf 'PR_TITLE=%s\n' "$(read_state PR_TITLE)"
        printf 'REPO=%s\n' "$(read_state REPO)"
        printf 'REPO_UNAVAILABLE=%s\n' "$(read_state REPO_UNAVAILABLE)"
        printf 'FORKED_TARGET=%s\n' "$(read_state FORKED_TARGET)"
        printf 'HAS_BUMP=%s\n' "$(read_state HAS_BUMP)"
        printf 'BUMP_TYPE=%s\n' "$(read_state BUMP_TYPE)"
        printf 'NEW_VERSION=%s\n' "$(read_state NEW_VERSION)"
        printf 'RUN_ID=%s\n' "$(read_state RUN_ID)"
        printf 'BUMP_REASONING_FILE=%s\n' "${BUMP_REASONING_FILE:-$(read_state BUMP_REASONING_FILE)}"
        printf 'MANIFEST_PATH=%s\n' "$(read_state MANIFEST_PATH)"
        printf 'TOOL_LABEL=%s\n' "$(read_state TOOL_LABEL)"
    } > "$tmp" && mv "$tmp" "$IMPLEMENT_TMPDIR/postbump-state.sh"
}

write_finalize_state() {
    local tmp key default value
    tmp="$IMPLEMENT_TMPDIR/finalize-state.sh.tmp.$$"
    {
        for key in "${LARCH_FINALIZE_STATE_KEYS[@]}"; do
            default=$(larch_finalize_state_default "$key")
            if [ "$key" = "NO_LOGS_COMMIT" ]; then
                value=$NO_LOGS_COMMIT
            else
                value=$(read_state "$key" "$default")
            fi
            printf '%s=%s\n' "$key" "$value"
        done
    } > "$tmp" && mv "$tmp" "$IMPLEMENT_TMPDIR/finalize-state.sh"
    printf '%s' "$(read_state BAIL_REASON)" > "$IMPLEMENT_TMPDIR/final-bail-reason.txt"
}

run_checks_phase() {
    local out rc fail_file redacted_log fix_out fix_status fix_rc
    local lint_attempt
    emit_breadcrumb "→ ship-pr: checks"
    fail_file=$(failure_capture_path checks)
    capture_command_output out "$fail_file" "$SCRIPT_DIR/run-relevant-checks-captured.sh" --site step6 --tmpdir "$IMPLEMENT_TMPDIR"
    rc=$?
    printf '%s\n' "$out" >> "$fail_file"
    if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -q '^RELEVANT_CHECKS_OK=true '; then
        advance_phase bump
        return 0
    fi
    redacted_log=$(printf '%s\n' "$out" | awk -F= '/^REDACTED_LOG_FILE=/ { print substr($0, index($0,"=")+1); exit }')
    redacted_log=$(resolve_checks_log_path "$redacted_log") || {
        record_failure checks "run-relevant-checks-captured.sh" "$rc" "$fail_file"
        exit_stall 6
    }
    for lint_attempt in 1 2 3; do
        fail_file=$(failure_capture_path checks)
        run_lint_fix_loop_capture "$fail_file" ship-pr-ci-initial "$redacted_log" fix_out fix_rc
        printf '%s\n' "$fix_out" >> "$fail_file"
        fix_status=$(printf '%s\n' "$fix_out" | awk -F= '/^LINT_FIX_STATUS=/ { print $2; exit }')
        case "$fix_status" in
            applied|no-changes)
                # Re-run checks after any fix attempt; applied means coder made changes,
                # no-changes means no changes were made — either way re-verify once.
                printf 'ship-pr checks: lint fix %s (attempt %d/3), re-running checks...\n' "$fix_status" "$lint_attempt"
                fail_file=$(failure_capture_path checks)
                capture_command_output out "$fail_file" "$SCRIPT_DIR/run-relevant-checks-captured.sh" --site step6 --tmpdir "$IMPLEMENT_TMPDIR"
                rc=$?
                printf '%s\n' "$out" >> "$fail_file"
                if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -q '^RELEVANT_CHECKS_OK=true '; then
                    advance_phase bump
                    return 0
                fi
                # no-changes means the coder made no fixes; further dispatch won't help.
                if [ "$fix_status" = "no-changes" ]; then
                    break
                fi
                redacted_log=$(printf '%s\n' "$out" | awk -F= '/^REDACTED_LOG_FILE=/ { print substr($0, index($0,"=")+1); exit }')
                redacted_log=$(resolve_checks_log_path "$redacted_log") || {
                    break
                }
                ;;
            *)
                # failed, main-agent-required, or empty — fall through to stall.
                printf 'ship-pr checks: lint fix %s (attempt %d/3, rc=%s), stalling.\n' "${fix_status:-unknown}" "$lint_attempt" "${fix_rc:-unknown}"
                break
                ;;
        esac
    done
    record_failure checks "run-relevant-checks-captured.sh" "$rc" "$fail_file"
    exit_stall 6
}

lint_fix_site_for_phase() {
    case "$1" in
        ci-initial|checks) printf '%s\n' ship-pr-ci-initial ;;
        ci-merge|evaluate-failure) printf '%s\n' ship-pr-ci-merge ;;
        *) return 1 ;;
    esac
}

run_checks_with_lint_fix_loop() {
    local phase=$1 checks_site=$2 fix_site redacted_log fix_out fix_status fix_rc
    local fail_category fail_file out rc attempt fix_delta_paths_file vendor_dirty_paths_file

    LAST_LINT_FIX_DELTA_PATHS_FILE=""
    ALL_LINT_FIX_DELTA_PATHS_FILE="$IMPLEMENT_TMPDIR/${phase}-lint-fix-delta-paths.txt"
    : > "$ALL_LINT_FIX_DELTA_PATHS_FILE"

    fix_site=$(lint_fix_site_for_phase "$phase") || return 2
    case "$phase" in
        ci-initial|ci-merge|evaluate-failure)
            fail_category="CI Issues"
            ;;
        *)
            return 2
            ;;
    esac

    fail_file=$(failure_capture_path "$phase")
    capture_command_output out "$fail_file" "$SCRIPT_DIR/run-relevant-checks-captured.sh" --site "$checks_site" --tmpdir "$IMPLEMENT_TMPDIR"
    rc=$?
    printf '%s\n' "$out" >> "$fail_file"
    if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -q '^RELEVANT_CHECKS_OK=true '; then
        return 0
    fi
    redacted_log=$(printf '%s\n' "$out" | awk -F= '/^REDACTED_LOG_FILE=/ { print substr($0, index($0,"=")+1); exit }')
    redacted_log=$(resolve_checks_log_path "$redacted_log") || {
        record_failure "$phase" "run-relevant-checks-captured.sh" "$rc" "$fail_file" "$fail_category"
        return 1
    }
    vendor_dirty_paths_file="$IMPLEMENT_TMPDIR/${phase}-vendor-dirty-paths.txt"
    capture_dirty_paths > "$vendor_dirty_paths_file"
    for attempt in 1 2 3; do
        fail_file=$(failure_capture_path "$phase")
        run_lint_fix_loop_capture "$fail_file" "$fix_site" "$redacted_log" fix_out fix_rc
        printf '%s\n' "$fix_out" >> "$fail_file"
        fix_status=$(printf '%s\n' "$fix_out" | awk -F= '/^LINT_FIX_STATUS=/ { print $2; exit }')
        fix_delta_paths_file=$(printf '%s\n' "$fix_out" | awk -F= '/^LINT_FIX_DELTA_PATHS_FILE=/ { print substr($0, index($0,"=")+1); exit }')
        case "$fix_status" in
            applied|no-changes)
                if [[ "$fix_status" == "applied" && -n "$fix_delta_paths_file" && -f "$fix_delta_paths_file" ]]; then
                    append_unique_paths_file "$ALL_LINT_FIX_DELTA_PATHS_FILE" "$fix_delta_paths_file"
                fi
                printf 'ship-pr %s: lint fix %s (attempt %d/3), re-running checks...\n' "$phase" "$fix_status" "$attempt"
                fail_file=$(failure_capture_path "$phase")
                capture_command_output out "$fail_file" "$SCRIPT_DIR/run-relevant-checks-captured.sh" --site "$checks_site" --tmpdir "$IMPLEMENT_TMPDIR"
                rc=$?
                printf '%s\n' "$out" >> "$fail_file"
                if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -q '^RELEVANT_CHECKS_OK=true '; then
                    if [[ -s "$ALL_LINT_FIX_DELTA_PATHS_FILE" ]]; then
                        LAST_LINT_FIX_DELTA_PATHS_FILE="$ALL_LINT_FIX_DELTA_PATHS_FILE"
                    elif [[ "$fix_status" == "applied" && -n "$fix_delta_paths_file" ]]; then
                        LAST_LINT_FIX_DELTA_PATHS_FILE="$fix_delta_paths_file"
                    fi
                    return 0
                fi
                if [ "$fix_status" = "no-changes" ]; then
                    record_failure "$phase" "run-relevant-checks-captured.sh" "$rc" "$fail_file" "$fail_category"
                    return 1
                fi
                redacted_log=$(printf '%s\n' "$out" | awk -F= '/^REDACTED_LOG_FILE=/ { print substr($0, index($0,"=")+1); exit }')
                redacted_log=$(resolve_checks_log_path "$redacted_log") || {
                    record_failure "$phase" "run-relevant-checks-captured.sh" "$rc" "$fail_file" "$fail_category"
                    return 1
                }
                ;;
            *)
                record_failure "$phase" "lint-fix-loop.sh" "${fix_rc:-1}" "$fail_file" "$fail_category"
                printf 'ship-pr %s: lint fix %s (attempt %d/3, rc=%s), stalling.\n' "$phase" "${fix_status:-unknown}" "$attempt" "${fix_rc:-unknown}"
                return 1
                ;;
        esac
    done

    record_failure "$phase" "run-relevant-checks-captured.sh" "$rc" "$fail_file" "$fail_category"
    return 1
}

run_bump_phase() {
    local forked has_bump commits_before classify_out apply_out finalize_out status resume_phase error_text rc fail_file
    emit_breadcrumb "→ ship-pr: version bump"
    forked=$(read_state FORKED_TARGET)
    has_bump=$(read_state HAS_BUMP)
    if [ "$forked" = "true" ] || [ "$has_bump" = "false" ]; then
        state_set_many HAS_BUMP false BUMP_TYPE NONE NEW_VERSION "" BUMP_REASONING_FILE ""
    else
        commits_before=$(git rev-list --count HEAD 2>/dev/null || echo 0)
        fail_file=$(failure_capture_path bump)
        classify_out=$("$PLUGIN_ROOT/.claude/skills/bump-version/scripts/classify-bump.sh" 2>"$fail_file")
        rc=$?
        printf '%s\n' "$classify_out" >> "$fail_file"
        if [ "$rc" -ne 0 ]; then
            record_failure bump "classify-bump.sh" "$rc" "$fail_file"
            exit_stall 8
        fi
        state_set_many \
            HAS_BUMP true \
            BUMP_TYPE "$(kv_value BUMP_TYPE "$classify_out")" \
            NEW_VERSION "$(kv_value NEW_VERSION "$classify_out")" \
            BUMP_REASONING_FILE "$(kv_value REASONING_FILE "$classify_out")"
        if [ "$(read_state BUMP_TYPE)" != "NONE" ]; then
            fail_file=$(failure_capture_path bump)
            apply_out=$("$PLUGIN_ROOT/.claude/skills/bump-version/scripts/apply-bump.sh" --new-version "$(read_state NEW_VERSION)" 2>"$fail_file")
            rc=$?
            printf '%s\n' "$apply_out" >> "$fail_file"
            if [ "$rc" -ne 0 ] || [ "$(kv_value APPLIED "$apply_out")" != "true" ]; then
                record_failure bump "apply-bump.sh" "$rc" "$fail_file"
                error_text=$(kv_value ERROR "$apply_out")
                case "$error_text" in
                    origin/main\ has\ already\ bumped\ to*)
                        state_set_many RESUME_PHASE bump CALLER_KIND step8b_same_version
                        exit 5
                        ;;
                    version\ regression:*)
                        state_set_many RESUME_PHASE bump CALLER_KIND step8b_same_version
                        exit 5
                        ;;
                    *) exit_stall 8 ;;
                esac
            fi
            fail_file=$(failure_capture_path bump)
            "$SCRIPT_DIR/check-bump-version.sh" --mode post --before-count "$commits_before" > "$fail_file" 2>&1
            rc=$?
            if [ "$rc" -ne 0 ]; then
                record_failure bump "check-bump-version.sh" "$rc" "$fail_file"
                exit_stall 8
            fi
        fi
    fi

    # Refresh larch-log token/timing artifacts before push via postbump (Trigger C).
    fail_file=$(failure_capture_path bump)
    "$SCRIPT_DIR/refresh-run-logs.sh" \
        --state-file "$STATE_FILE" \
        --implement-tmpdir "$IMPLEMENT_TMPDIR" > "$fail_file" 2>&1 || true

    write_postbump_state
    fail_file=$(failure_capture_path bump)
    finalize_out=$("$SCRIPT_DIR/implement-finalize.sh" postbump --state-file "$IMPLEMENT_TMPDIR/postbump-state.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" 2>"$fail_file")
    rc=$?
    printf '%s\n' "$finalize_out" >> "$fail_file"
    status=$(kv_value STATUS "$finalize_out")
    if [ "$rc" -ne 0 ]; then
        record_failure bump "implement-finalize.sh postbump" "$rc" "$fail_file"
    fi
    case "$status" in
        ok|skipped)
            local _cur _new _btype
            _cur=$(kv_value CURRENT_VERSION "$classify_out")
            _new=$(read_state NEW_VERSION)
            _btype=$(read_state BUMP_TYPE)
            case "$_btype" in
                PATCH|MINOR|MAJOR)
                    emit "$(printf '✅ 8: version bump — %s → %s (%s)' "$_cur" "$_new" "$_btype")"
                    ;;
                *)
                    if [ "$forked" = "true" ]; then
                        emit '⏩ 8: version bump status=skip reason=forked'
                    else
                        emit "$(printf '⏩ 8: version bump status=skip reason=%s' "${_btype:-NONE}")"
                    fi
                    ;;
            esac
            advance_phase pr-prep
            ;;
        conflict)
            resume_phase=$(kv_value RESUME_PHASE "$finalize_out")
            if [ "$resume_phase" = "force-push-gate" ]; then
                state_set_many RESUME_PHASE force-push-gate CALLER_KIND step8b_rebase
                exit 5
            fi
            exit_stall 8b
            ;;
        changelog-failed|rebase-failed|push-failed|remote-check-failed|branch-mismatch|postbump-state-corrupt)
            exit_stall 8b
            ;;
        *)
            exit_stall 8
            ;;
    esac
}

manifest_summary() {
    local manifest
    manifest=$(read_state MANIFEST_PATH)
    if [ -n "$manifest" ] && [ -f "$manifest" ] && command -v jq >/dev/null 2>&1; then
        jq -r '(.summary_bullets // []) | if type == "array" then .[] else empty end' "$manifest" 2>/dev/null | sed 's/^/- /'
    fi
}

manifest_tests() {
    local manifest
    manifest=$(read_state MANIFEST_PATH)
    if [ -n "$manifest" ] && [ -f "$manifest" ] && command -v jq >/dev/null 2>&1; then
        jq -r '(.tests_added_or_modified // []) | if type == "array" then .[] else empty end' "$manifest" 2>/dev/null | sed 's/^/- [x] /'
    fi
}

sanitize_diagram_or_placeholder() {
    local file=$1 placeholder=$2 label=$3 out reason rc fail_file
    if [ -n "$file" ] && [ -f "$file" ]; then
        fail_file=$(failure_capture_path pr-prep)
        out=$("$SCRIPT_DIR/sanitize-mermaid-fragment.sh" --input "$file" --from-md --warnings-step "9a" 2>"$fail_file")
        rc=$?
        printf '%s\n' "$out" >> "$fail_file"
        if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -q '^STATUS=ok$'; then
            cat "$file"
            return 0
        fi
        record_failure pr-prep "sanitize-mermaid-fragment.sh ($label)" "$rc" "$fail_file" Warnings
        reason=$(kv_value REASON_TOKEN "$out")
        [ -n "$reason" ] || reason="unknown"
        "$SCRIPT_DIR/append-execution-issue.sh" --log "$IMPLEMENT_TMPDIR/execution-issues.md" --category Warnings --entry "Step 9a — PR-body diagram $label rejected: $reason" >/dev/null 2>&1 || true
    fi
    printf '%s\n' "$placeholder"
}

run_pr_prep_phase() {
    local summary tests closes architecture_file code_flow_file composed_summary plan_goals_file run_id
    emit_breadcrumb "→ ship-pr: PR prep"
    summary=$(manifest_summary)
    if [ -z "$summary" ]; then
        run_id=$(read_state RUN_ID)
        plan_goals_file="$IMPLEMENT_TMPDIR/larch-logs/implement/$run_id/plan-goals-test.md"
        composed_summary=$("$SCRIPT_DIR/compose-pr-summary.sh" --plan-goals-file "$plan_goals_file" 2>/dev/null) || composed_summary=""
        [ -n "$composed_summary" ] && summary="$composed_summary"
    fi
    [ -n "$summary" ] || summary="- Implemented the requested changes."
    tests=$(manifest_tests)
    [ -n "$tests" ] || tests="- [x] Ran relevant checks."
    architecture_file="${ARCHITECTURE_DIAGRAM_FILE:-}"
    if [ -z "$architecture_file" ] || [ ! -f "$architecture_file" ]; then
        "$SCRIPT_DIR/compose-architecture-sketch.sh" --output "$IMPLEMENT_TMPDIR/architecture-sketch.md" 2>/dev/null || true
        [ -s "$IMPLEMENT_TMPDIR/architecture-sketch.md" ] && architecture_file="$IMPLEMENT_TMPDIR/architecture-sketch.md"
    fi
    code_flow_file="$IMPLEMENT_TMPDIR/code-flow-diagram.md"
    if [ "$(read_state FORKED_TARGET)" = "true" ]; then
        closes="_Fork CI dry-run — upstream auto-close intentionally omitted._"
    elif [ -n "$(read_state ISSUE_NUMBER)" ] && [ "$(read_state REPO_UNAVAILABLE)" = "false" ]; then
        closes="Closes #$(read_state ISSUE_NUMBER)"
    else
        closes="_No tracking issue — auto-close N/A._"
    fi
    {
        printf '## Summary\n%s\n\n' "$summary"
        printf '<details><summary>Architecture Diagram</summary>\n\n'
        sanitize_diagram_or_placeholder "$architecture_file" "Architecture diagram not available." architecture
        printf '\n</details>\n\n'
        printf '<details><summary>Code Flow Diagram</summary>\n\n'
        sanitize_diagram_or_placeholder "$code_flow_file" "Code flow diagram not available." code-flow
        printf '\n</details>\n\n'
        printf '<details><summary>Test plan</summary>\n\n%s\n\n</details>\n\n' "$tests"
        printf '%s\n\nGenerated with [Claude Code](https://claude.com/claude-code)\n' "$closes"
    } > "$IMPLEMENT_TMPDIR/pr-body.md"

    if [ -s "$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md" ] || [ -s "$IMPLEMENT_TMPDIR/oos-accepted-design.md" ] || [ -s "$IMPLEMENT_TMPDIR/oos-accepted-review.md" ]; then
        state_set OOS_PENDING true
        advance_phase pr-create
        exit 0
    fi
    state_set OOS_PENDING false
    advance_phase pr-create
}

run_pr_create_phase() {
    local title out rc pr_number pr_url pr_status repo_args draft_args fail_file _merge_base final_report_output
    emit_breadcrumb "→ ship-pr: opening PR"
    _merge_base=$(git merge-base HEAD origin/main 2>/dev/null) || _merge_base=
    if [ -n "$_merge_base" ]; then
        title=$(git log --format=%s "${_merge_base}..HEAD" 2>/dev/null | grep -v '^chore(larch-logs): flush ' | head -1)
    else
        title=$(git log --format=%s HEAD 2>/dev/null | grep -v '^chore(larch-logs): flush ' | head -1)
    fi
    title=${title:-"Implement requested changes"}
    repo_args=()
    if [ -n "$(read_state REPO)" ]; then
        repo_args=(--repo "$(read_state REPO)")
    fi
    draft_args=()
    [ "$(read_state DRAFT)" = "true" ] && draft_args=(--draft)
    # Write final-summary.md with placeholder PR fields before push so the
    # commit rides in Push #1 (via create-pr.sh). This also upserts the
    # tracking-issue larch:final-summary comment before PR creation, so a
    # helper failure here stalls Step 9b with no PR yet. PR_URL defaults to
    # "N/A".
    fail_file=$(failure_capture_path pr-create)
    final_report_output=$("$SCRIPT_DIR/../skills/implement/scripts/write-final-report.sh" \
        --implement-tmpdir "$IMPLEMENT_TMPDIR" 2>"$fail_file")
    rc=$?
    printf '%s\n' "$final_report_output" >> "$fail_file"
    if [ "$rc" -ne 0 ] && is_transient_net_signature "$(cat "$fail_file" 2>/dev/null)"; then
        record_failure pr-create "write-final-report.sh" "$rc" "$fail_file" Warnings
        exit_transient_net "write-final-report: $final_report_output"
    fi
    if [ "$rc" -ne 0 ]; then
        record_failure pr-create "write-final-report.sh" "$rc" "$fail_file" Warnings
        exit_stall 9b
    fi
    # Fold final-summary.md into the branch before the PR-create push so
    # the remote PR tip carries it. Gated on LARCH_NO_LOGS_COMMIT; a
    # best-effort log-commit failure must not block create-pr.sh.
    if [ "${LARCH_NO_LOGS_COMMIT:-false}" != "true" ]; then
        local flush_run_id
        flush_run_id=$(read_state RUN_ID)
        [ -n "$flush_run_id" ] || flush_run_id="${LARCH_RUN_ID:-${RUN_ID:-$(basename "$IMPLEMENT_TMPDIR")}}"
        if [ -n "$flush_run_id" ]; then
            fail_file=$(failure_capture_path pr-create)
            "$SCRIPT_DIR/larch-log.sh" commit \
                --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                --skill implement \
                --run-id "$flush_run_id" \
                > "$fail_file" 2>&1
            rc=$?
            [ "$rc" -eq 0 ] || record_failure pr-create "larch-log.sh commit (pre-pr-create)" "$rc" "$fail_file" Warnings
        fi
    fi
    fail_file=$(failure_capture_path pr-create)
    out=$("$SCRIPT_DIR/create-pr.sh" --title "$title" --body-file "$IMPLEMENT_TMPDIR/pr-body.md" "${draft_args[@]+"${draft_args[@]}"}" "${repo_args[@]+"${repo_args[@]}"}" 2>"$fail_file")
    rc=$?
    printf '%s\n' "$out" >> "$fail_file"
    # Classify against combined stderr + stdout (fail_file) — real helpers
    # emit common network failures on stderr; checking only $out (stdout)
    # would stall transient failures as non-transient. Streamed via cat to
    # avoid argv-sized payloads on huge logs.
    if [ "$rc" -ne 0 ] && is_transient_net_signature "$(cat "$fail_file" 2>/dev/null)"; then
        record_failure pr-create "create-pr.sh" "$rc" "$fail_file"
        exit_transient_net "create-pr: $out"
    fi
    if [ "$rc" -ne 0 ]; then
        record_failure pr-create "create-pr.sh" "$rc" "$fail_file"
        exit_stall 9b
    fi
    pr_number=$(kv_value PR_NUMBER "$out")
    pr_url=$(kv_value PR_URL "$out")
    pr_status=$(kv_value PR_STATUS "$out")
    state_set_many PR_NUMBER "$pr_number" PR_URL "$pr_url" PR_TITLE "$title"
    emit_breadcrumb "→ ship-pr: PR #${pr_number} opened"
    # Re-run write-final-report.sh with the live PR_URL to refresh the
    # tracking-issue larch:final-summary comment and tmp summary-final.md for
    # the upsert. No extra git commit or second push happens here. Best-effort:
    # a failure here must not stall since the PR was already created.
    fail_file=$(failure_capture_path pr-create)
    final_report_output=$("$SCRIPT_DIR/../skills/implement/scripts/write-final-report.sh" \
        --implement-tmpdir "$IMPLEMENT_TMPDIR" --comment-only 2>"$fail_file")
    rc=$?
    printf '%s\n' "$final_report_output" >> "$fail_file"
    [ "$rc" -eq 0 ] || record_failure pr-create "write-final-report.sh post" "$rc" "$fail_file" Warnings
    if [ "$pr_status" = "existing" ]; then
        fail_file=$(failure_capture_path pr-create)
        "$SCRIPT_DIR/gh-pr-body-update.sh" --pr "$pr_number" --body-file "$IMPLEMENT_TMPDIR/pr-body.md" "${repo_args[@]+"${repo_args[@]}"}" > "$fail_file" 2>&1
        rc=$?
        [ "$rc" -eq 0 ] || record_failure pr-create "gh-pr-body-update.sh" "$rc" "$fail_file"
    fi
    advance_phase ci-initial
}

ci_common_args() {
    printf '%s\n' --pr "$(read_state PR_NUMBER)"
    printf '%s\n' --repo "$(read_state REPO)"
    printf '%s\n' --rebase-count "$(read_state REBASE_COUNT)"
    printf '%s\n' --fix-attempts "$(read_state FIX_ATTEMPTS)"
    printf '%s\n' --iteration "$(read_state ITERATION)"
    if [ "$(read_state FORKED_TARGET)" = "true" ]; then
        printf '%s\n' --base-remote
        printf '%s\n' upstream
        printf '%s\n' --base-ref
        printf '%s\n' main
        printf '%s\n' --empty-checks-grace
        printf '%s\n' 30
    fi
}

record_ci_counters() {
    local out=$1
    state_set_many \
        ITERATION "$(kv_value ITERATION "$out")" \
        FAILED_RUN_ID "$(kv_value FAILED_RUN_ID "$out")"
}

needs_user_bail_reason() {
    case "$1" in
        fix-attempts-exhausted|design-flaw|escalate|all-vendors-failed) return 0 ;;
        *) return 1 ;;
    esac
}

rename_done_best_effort() {
    local issue repo rc fail_file
    issue=$(read_state ISSUE_NUMBER)
    repo=$(read_state REPO)
    [ -n "$issue" ] || return 0
    [ "$(read_state REPO_UNAVAILABLE)" = "false" ] || return 0
    fail_file=$(failure_capture_path postmerge)
    if [ -n "$repo" ]; then
        "$SCRIPT_DIR/tracking-issue-write.sh" rename --issue "$issue" --state "done" --round-trip false --repo "$repo" > "$fail_file" 2>&1
        rc=$?
    else
        "$SCRIPT_DIR/tracking-issue-write.sh" rename --issue "$issue" --state "done" --round-trip false > "$fail_file" 2>&1
        rc=$?
    fi
    [ "$rc" -eq 0 ] || record_failure postmerge "tracking-issue-write.sh rename" "$rc" "$fail_file"
    state_set DONE_RENAME_APPLIED true
}

run_ci_fix_vendor() {
    local phase=$1 run_id=$2 output rc fail_file tool_label plan_file checks_site delta_paths_file
    local plan_args=() vendor_tracked_dirty_paths_file vendor_untracked_dirty_paths_file tracked_dirty_paths_file untracked_dirty_paths_file
    emit_breadcrumb "⚠ ship-pr: CI failed; dispatching fix"
    output="$IMPLEMENT_TMPDIR/ci-fix-${phase}-$(date +%s).out"
    plan_file=$(resolve_plan_file)
    if [ -n "$plan_file" ]; then
        plan_args=(--plan-file "$plan_file")
    fi
    for vendor_attempt in 1 2 3; do
        fail_file=$(failure_capture_path "$phase")
        if command -v cursor >/dev/null 2>&1; then
            tool_label="launch-cursor-ci.sh fix"
            "$SCRIPT_DIR/launch-cursor-ci.sh" --role fix --output "$output" --run-id "$run_id" --repo "$(read_state REPO)" ${plan_args[@]+"${plan_args[@]}"} --timeout 1800 > "$fail_file" 2>&1
            rc=$?
        else
            tool_label="launch-codex-ci.sh fix"
            "$SCRIPT_DIR/launch-codex-ci.sh" --role fix --output "$output" --run-id "$run_id" --repo "$(read_state REPO)" ${plan_args[@]+"${plan_args[@]}"} --timeout 1800 > "$fail_file" 2>&1
            rc=$?
        fi
        if [ "$rc" -eq 0 ]; then
            break
        fi
        record_failure "$phase" "$tool_label" "$rc" "$fail_file" "CI Issues"
        if [ "$vendor_attempt" -lt 3 ]; then
            printf 'ship-pr %s: vendor launch failed (attempt %d/3), retrying.\n' "$phase" "$vendor_attempt"
        fi
    done
    [ "$rc" -eq 0 ] || return 1
    fail_file=$(failure_capture_path "$phase")
    "$SCRIPT_DIR/append-token-record.sh" --input "${output}.token-record" --tmpdir "$IMPLEMENT_TMPDIR" > "$fail_file" 2>&1
    rc=$?
    [ "$rc" -eq 0 ] || record_failure "$phase" "append-token-record.sh" "$rc" "$fail_file" Warnings
    vendor_tracked_dirty_paths_file="$IMPLEMENT_TMPDIR/${phase}-vendor-tracked-dirty-paths.txt"
    vendor_untracked_dirty_paths_file="$IMPLEMENT_TMPDIR/${phase}-vendor-untracked-dirty-paths.txt"
    capture_tracked_dirty_paths > "$vendor_tracked_dirty_paths_file"
    capture_untracked_dirty_paths > "$vendor_untracked_dirty_paths_file"
    checks_site="$([ "$phase" = "ci-initial" ] && echo step10 || echo step12c)"
    if ! run_checks_with_lint_fix_loop "$phase" "$checks_site"; then
        return 1
    fi
    tracked_dirty_paths_file="$IMPLEMENT_TMPDIR/${phase}-post-success-tracked-dirty-paths.txt"
    untracked_dirty_paths_file="$IMPLEMENT_TMPDIR/${phase}-post-success-untracked-dirty-paths.txt"
    capture_tracked_dirty_paths > "$tracked_dirty_paths_file"
    capture_untracked_dirty_paths > "$untracked_dirty_paths_file"
    # Only commit when the vendor or lint-fix path left dirty tracked changes,
    # or intended untracked files created by the vendor/lint-fix step.
    if [[ -s "$tracked_dirty_paths_file" || -s "$untracked_dirty_paths_file" ]]; then
        fail_file=$(failure_capture_path "$phase")
        delta_paths_file="$LAST_LINT_FIX_DELTA_PATHS_FILE"
        rc=0
        if [[ -s "$vendor_tracked_dirty_paths_file" || -s "$vendor_untracked_dirty_paths_file" || -s "$tracked_dirty_paths_file" ]] || [[ -n "$delta_paths_file" && -f "$delta_paths_file" && -s "$delta_paths_file" ]]; then
            local stage_paths=() stage_path
            while IFS= read -r stage_path || [[ -n "$stage_path" ]]; do
                [[ -n "$stage_path" ]] || continue
                stage_paths+=("$stage_path")
            done < <(collect_ci_stage_paths "$vendor_tracked_dirty_paths_file" "$vendor_untracked_dirty_paths_file" "$tracked_dirty_paths_file" "$untracked_dirty_paths_file" "$delta_paths_file")
            if [[ "${#stage_paths[@]}" -gt 0 ]]; then
                git add -- "${stage_paths[@]}" > "$fail_file" 2>&1
            else
                : > "$fail_file"
            fi
        fi
        rc=$?
        if [ "$rc" -ne 0 ]; then
            record_failure "$phase" "git add -- <tracked+allowlisted-untracked>" "$rc" "$fail_file" "CI Issues"
            return 1
        fi
        if ! git diff --cached --quiet 2>/dev/null; then
            fail_file=$(failure_capture_path "$phase")
            "$SCRIPT_DIR/git-commit.sh" -m "Fix CI failure" > "$fail_file" 2>&1
            rc=$?
            if [ "$rc" -ne 0 ]; then
                record_failure "$phase" "git-commit.sh" "$rc" "$fail_file" "CI Issues"
                return 1
            fi
        fi
    fi
    # Refresh larch-log token/timing artifacts before push (Trigger B).
    fail_file=$(failure_capture_path "$phase")
    "$SCRIPT_DIR/refresh-run-logs.sh" \
        --state-file "$STATE_FILE" \
        --implement-tmpdir "$IMPLEMENT_TMPDIR" > "$fail_file" 2>&1 || true

    fail_file=$(failure_capture_path "$phase")
    "$SCRIPT_DIR/git-push.sh" > "$fail_file" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        record_failure "$phase" "git-push.sh" "$rc" "$fail_file" "CI Issues"
        return 1
    fi
}

run_evaluate_failure() {
    local phase=$1 failed_run rerun_out retries rc fail_file
    failed_run=$(read_state FAILED_RUN_ID)
    [ -n "$failed_run" ] || exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12c)"
    retries=$(read_state TRANSIENT_RETRIES)
    if [ "$retries" -lt 1 ]; then
        fail_file=$(failure_capture_path "$phase")
        rerun_out=$("$SCRIPT_DIR/ci-rerun-failed.sh" --run-id "$failed_run" --repo "$(read_state REPO)" 2>"$fail_file")
        rc=$?
        printf '%s\n' "$rerun_out" >> "$fail_file"
        if [ "$rc" -eq 0 ] && [ "$(kv_value RERUN_SUBMITTED "$rerun_out")" = "true" ]; then
            # Only count toward the retry budget when a new rerun was actually submitted;
            # "already running" means CI is in flight and no new run was queued.
            if [ "$(kv_value ALREADY_RUNNING "$rerun_out")" != "true" ]; then
                state_set TRANSIENT_RETRIES "$((retries + 1))"
            fi
            return 0
        fi
        record_failure "$phase" "ci-rerun-failed.sh" "$rc" "$fail_file" "CI Issues"
    fi
    fail_file=$(failure_capture_path "$phase")
    "$SCRIPT_DIR/gh-run-logs.sh" --run-id "$failed_run" --repo "$(read_state REPO)" > "$fail_file" 2>&1
    rc=$?
    [ "$rc" -eq 0 ] || record_failure "$phase" "gh-run-logs.sh" "$rc" "$fail_file" "CI Issues"
    # Retry loop with cap, detached-HEAD check, and jittered backoff. This caps
    # each run_evaluate_failure invocation at 5 vendor+push attempts; the
    # persisted FIX_ATTEMPTS counter still tracks successful fix pushes across
    # the wider phase for reporting/state purposes.
    local _max_fix=5 _fix_attempt
    _fix_attempt=0
    while [ "$_fix_attempt" -lt "$_max_fix" ]; do
        # Detached-HEAD guard before each vendor+push attempt.
        if ! git symbolic-ref --quiet HEAD >/dev/null 2>&1; then
            fail_file=$(failure_capture_path "$phase")
            printf 'run_evaluate_failure: not on a named branch (detached HEAD)\n' > "$fail_file"
            record_failure "$phase" "evaluate-failure detached-head" 1 "$fail_file" "CI Issues"
            exit_stall "$([ "$phase" = "ci-initial" ] && echo 10-detached-head || echo 12-detached-head)"
        fi
        if run_ci_fix_vendor "$phase" "$failed_run"; then
            state_set_many TRANSIENT_RETRIES 0 FIX_ATTEMPTS "$(( $(read_state FIX_ATTEMPTS) + 1 ))"
            return 0
        fi
        _fix_attempt=$(( _fix_attempt + 1 ))
        if [ "$_fix_attempt" -lt "$_max_fix" ]; then
            # Jittered backoff: 2s/4s/8s/16s ±25 %
            local _base _jitter _sleep
            _base=$(( 2 * 2 ** (_fix_attempt - 1) ))
            _jitter=$(( RANDOM % (_base / 2 + 1) ))
            _sleep=$(( _base + _jitter - _base / 4 ))
            [ "$_sleep" -lt 1 ] && _sleep=1
            sleep "$_sleep"
        fi
    done
    exit_stall "$([ "$phase" = "ci-initial" ] && echo 10-max-retries || echo 12-max-retries)"
}

is_head_divergence_recoverable() {
    local text="$1"
    local local_head="" pr_head_oid="" current_head=""
    case "$text" in
        *local\ HEAD*does\ not\ match\ PR\ head\ OID*) ;;
        *) return 1 ;;
    esac
    if [[ "$text" =~ local\ HEAD\ \(([[:alnum:]]+)\)\ does\ not\ match\ PR\ head\ OID\ \(([[:alnum:]]+)\) ]]; then
        local_head="${BASH_REMATCH[1]}"
        pr_head_oid="${BASH_REMATCH[2]}"
    else
        return 1
    fi
    current_head=$(git rev-parse HEAD 2>/dev/null || echo "")
    [[ -n "$current_head" ]] || return 1
    [[ "$current_head" == "$local_head" ]] || return 1
    git merge-base --is-ancestor "$pr_head_oid" "$current_head" 2>/dev/null
}

run_rebase_rebump() {
    local phase=$1 drop_out rebase_out rebase_rc conflict_out run_id classify_out classify_rc
    local apply_out new_version bump_type reasoning_file
    local fail_file rc tool_label plan_file
    local plan_args=()
    local _origin_ver="" _classified_version="" _corrected=""
    emit_breadcrumb "⚠ ship-pr: rebase + re-bump"

    # Cap rebase retries to prevent indefinite storms (e.g. concurrent merges
    # to main that keep triggering ACTION=rebase from ci-wait.sh).
    local _max_rebases=5
    if [ "$(read_state REBASE_COUNT)" -ge "$_max_rebases" ]; then
        fail_file=$(failure_capture_path rebase)
        printf 'run_rebase_rebump: REBASE_COUNT >= %d; bailing to prevent infinite retry storm\n' "$_max_rebases" > "$fail_file"
        record_failure rebase "run_rebase_rebump max-retries" 1 "$fail_file" "CI Issues"
        exit_stall "$([ "$phase" = "ci-initial" ] && echo 10-max-retries || echo 12-max-retries)"
    fi

    # Detached-HEAD check: a prior rebase may have left HEAD detached.  Detect
    # before attempting another rebase so we bail immediately rather than
    # retrying into an unrecoverable state.
    if ! git symbolic-ref --quiet HEAD >/dev/null 2>&1; then
        fail_file=$(failure_capture_path rebase)
        printf 'run_rebase_rebump: not on a named branch (detached HEAD)\n' > "$fail_file"
        record_failure rebase "run_rebase_rebump detached-head" 1 "$fail_file" "CI Issues"
        exit_stall "$([ "$phase" = "ci-initial" ] && echo 10-detached-head || echo 12-detached-head)"
    fi

    plan_file=$(resolve_plan_file)
    if [ -n "$plan_file" ]; then
        plan_args=(--plan-file "$plan_file")
    fi

    # 1. Drop existing bump commit (non-fatal; CI-fix commits may sit on top)
    fail_file=$(failure_capture_path rebase)
    drop_out=$("$SCRIPT_DIR/drop-bump-commit.sh" 2>"$fail_file")
    rc=$?
    printf '%s\n' "$drop_out" >> "$fail_file"
    [ "$rc" -eq 0 ] || record_failure rebase "drop-bump-commit.sh" "$rc" "$fail_file" Warnings

    run_id=$(read_state RUN_ID)

    # 2. Rebase without pushing; keep in-progress on conflict for vendor resolution
    fail_file=$(failure_capture_path rebase)
    rebase_out=$("$SCRIPT_DIR/rebase-push.sh" --no-push --keep-on-conflict 2>"$fail_file")
    rebase_rc=$?
    printf '%s\n' "$rebase_out" >> "$fail_file"
    if [ "$rebase_rc" -eq 1 ]; then
        record_failure rebase "rebase-push.sh --keep-on-conflict" "$rebase_rc" "$fail_file" "CI Issues"
        # Conflict — vendor waterfall with resolve-conflict role
        conflict_out="$IMPLEMENT_TMPDIR/rebase-conflict-$(date +%s).out"
        fail_file=$(failure_capture_path conflict-resolution)
        if command -v cursor >/dev/null 2>&1; then
            tool_label="launch-cursor-ci.sh resolve-conflict"
            "$SCRIPT_DIR/launch-cursor-ci.sh" --role resolve-conflict --output "$conflict_out" \
                --run-id "$run_id" --repo "$(read_state REPO)" ${plan_args[@]+"${plan_args[@]}"} --timeout 1800 > "$fail_file" 2>&1
            rc=$?
        else
            tool_label="launch-codex-ci.sh resolve-conflict"
            "$SCRIPT_DIR/launch-codex-ci.sh" --role resolve-conflict --output "$conflict_out" \
                --run-id "$run_id" --repo "$(read_state REPO)" ${plan_args[@]+"${plan_args[@]}"} --timeout 1800 > "$fail_file" 2>&1
            rc=$?
        fi
        [ "$rc" -eq 0 ] || record_failure conflict-resolution "$tool_label" "$rc" "$fail_file" "External Reviewer Issues"
        fail_file=$(failure_capture_path conflict-resolution)
        "$SCRIPT_DIR/append-token-record.sh" --input "${conflict_out}.token-record" \
            --tmpdir "$IMPLEMENT_TMPDIR" > "$fail_file" 2>&1
        rc=$?
        [ "$rc" -eq 0 ] || record_failure conflict-resolution "append-token-record.sh" "$rc" "$fail_file" Warnings
        # Fresh rebase after vendor fix: if vendor ran git rebase --continue, the
        # branch is already rebased and this returns SKIPPED_ALREADY_FRESH. If the
        # vendor left a conflict or broke the tree it fails, causing exit_stall.
        fail_file=$(failure_capture_path rebase)
        rebase_out=$("$SCRIPT_DIR/rebase-push.sh" --no-push 2>"$fail_file")
        rebase_rc=$?
        printf '%s\n' "$rebase_out" >> "$fail_file"
        if [ "$rebase_rc" -ne 0 ]; then
            record_failure rebase "rebase-push.sh --no-push" "$rebase_rc" "$fail_file" "CI Issues"
            emit_breadcrumb "⚠ ship-pr: merge conflict on rebase"
            exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
        fi
    elif [ "$rebase_rc" -ne 0 ]; then
        record_failure rebase "rebase-push.sh --keep-on-conflict" "$rebase_rc" "$fail_file" "CI Issues"
        # Classify against combined stderr + stdout — git/network helpers
        # emit transient signals on stderr that $rebase_out alone misses.
        if is_transient_net_signature "$(cat "$fail_file" 2>/dev/null)"; then
            exit_transient_net "rebase: $rebase_out"
        fi
        emit_breadcrumb "⚠ ship-pr: merge conflict on rebase"
        exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
    fi

    # 3. Fast-forward local main so classify-bump.sh uses the correct merge-base
    fail_file=$(failure_capture_path rebase)
    "$SCRIPT_DIR/git-sync-local-main.sh" > "$fail_file" 2>&1
    rc=$?
    [ "$rc" -eq 0 ] || record_failure rebase "git-sync-local-main.sh" "$rc" "$fail_file" Warnings

    # 4. Re-bump using classify-bump.sh + apply-bump.sh directly
    if [ "$(read_state HAS_BUMP)" != "false" ]; then
        fail_file=$(failure_capture_path rebase)
        classify_out=$("$PLUGIN_ROOT/.claude/skills/bump-version/scripts/classify-bump.sh" 2>"$fail_file")
        classify_rc=$?
        printf '%s\n' "$classify_out" >> "$fail_file"
        if [ "$classify_rc" -ne 0 ]; then
            record_failure rebase "classify-bump.sh" "$classify_rc" "$fail_file" "CI Issues"
            exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
        fi
        new_version=$(kv_value NEW_VERSION "$classify_out")
        bump_type=$(kv_value BUMP_TYPE "$classify_out")
        reasoning_file=$(kv_value REASONING_FILE "$classify_out")
        reasoning_log_file=$reasoning_file
        _classified_version="$new_version"
        # Version-regression guard: when rebase conflict was resolved to the branch's
        # stale version instead of origin/main's, classify-bump produces NEW_VERSION <
        # ORIGIN_VERSION. Correct by applying bump_type to origin/main's version.
        if [ "$bump_type" != "NONE" ] && [ -n "$new_version" ]; then
            if [[ ! "$new_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                printf 'ERROR: run_rebase_rebump: classify-bump produced invalid NEW_VERSION: %s\n' \
                    "$new_version" >> "$fail_file"
                record_failure rebase "classify-bump.sh" 1 "$fail_file" "CI Issues"
                exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
            fi
            _origin_ver=$(git show origin/main:.claude-plugin/plugin.json 2>/dev/null \
                | jq -r '.version // empty' 2>/dev/null || echo "")
            if [[ "$_origin_ver" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] && semver_lt "$new_version" "$_origin_ver"; then
                IFS='.' read -r _ov_maj _ov_min _ov_pat <<< "$_origin_ver"
                case "$bump_type" in
                    MAJOR) _corrected="$(( _ov_maj + 1 )).0.0" ;;
                    MINOR) _corrected="${_ov_maj}.$(( _ov_min + 1 )).0" ;;
                    PATCH) _corrected="${_ov_maj}.${_ov_min}.$(( _ov_pat + 1 ))" ;;
                    *)     _corrected="$new_version" ;;
                esac
                printf 'WARN: run_rebase_rebump: version regression detected: classify-bump produced %s < origin/main %s; corrected to %s\n' \
                    "$new_version" "$_origin_ver" "$_corrected" >> "$fail_file"
                new_version="$_corrected"
                if [ -n "$reasoning_file" ] && [ -f "$reasoning_file" ]; then
                    if ! rewrite_reasoning_new_version "$reasoning_file" "$_classified_version" "$_origin_ver" "$_corrected"; then
                        reasoning_log_file=$(write_corrected_reasoning_fallback \
                            "$reasoning_file" "$_classified_version" "$_origin_ver" "$_corrected" 2>/dev/null || true)
                        if [ -n "$reasoning_log_file" ] && [ -f "$reasoning_log_file" ]; then
                            printf 'WARN: run_rebase_rebump: failed to rewrite reasoning file after version correction; using fallback reasoning snapshot: %s\n' \
                                "$reasoning_log_file" >> "$fail_file"
                        else
                            printf 'WARN: run_rebase_rebump: failed to rewrite reasoning file after version correction and could not build fallback snapshot: %s\n' \
                                "$reasoning_file" >> "$fail_file"
                            reasoning_log_file=""
                        fi
                    fi
                fi
            fi
        fi
        state_set_many BUMP_TYPE "$bump_type" NEW_VERSION "$new_version" BUMP_REASONING_FILE "$reasoning_log_file"
        if [ "$bump_type" != "NONE" ] && [ -n "$new_version" ]; then
            fail_file=$(failure_capture_path rebase)
            apply_out=$("$PLUGIN_ROOT/.claude/skills/bump-version/scripts/apply-bump.sh" \
                --new-version "$new_version" 2>"$fail_file")
            rc=$?
            printf '%s\n' "$apply_out" >> "$fail_file"
            if [ "$rc" -ne 0 ] || [ "$(kv_value APPLIED "$apply_out")" != "true" ]; then
                record_failure rebase "apply-bump.sh" "$rc" "$fail_file" "CI Issues"
                exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
            fi
            # Sync the PR title to the re-bumped version so the squash-merge
            # commit on main is not misattributed to the superseded version.
            local pr_n repo_r
            pr_n=$(read_state PR_NUMBER); repo_r=$(read_state REPO)
            if [ -n "$pr_n" ] && [ -n "$repo_r" ]; then
                gh pr edit "$pr_n" --repo "$repo_r" \
                    --title "Bump version to $new_version" >/dev/null 2>&1 || true
            fi
            # Refresh version-bump-reasoning larch-log so the audit trail
            # reflects the actually-landed version rather than the race target.
            if [ -n "$reasoning_log_file" ] && [ -f "$reasoning_log_file" ]; then
                run_id=$(read_state RUN_ID)
                if [ -n "$run_id" ]; then
                    "$SCRIPT_DIR/larch-log.sh" write \
                        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                        --skill implement \
                        --run-id "$run_id" \
                        --batch version-bump-reasoning \
                        --input-file "$reasoning_log_file" 2>/dev/null || true
                fi
            fi
        fi
    fi

    # Refresh larch-log token/timing artifacts before push (Trigger A).
    fail_file=$(failure_capture_path rebase)
    "$SCRIPT_DIR/refresh-run-logs.sh" \
        --state-file "$STATE_FILE" \
        --implement-tmpdir "$IMPLEMENT_TMPDIR" > "$fail_file" 2>&1 || true

    # 5. Force-push the rebased + re-bumped branch
    fail_file=$(failure_capture_path rebase)
    "$SCRIPT_DIR/git-force-push.sh" > "$fail_file" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        record_failure rebase "git-force-push.sh" "$rc" "$fail_file" "CI Issues"
        exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
    fi

    # 6. Increment counters, reset transient retries
    state_set_many \
        REBASE_COUNT "$(( $(read_state REBASE_COUNT) + 1 ))" \
        ITERATION "$(( $(read_state ITERATION) + 1 ))" \
        TRANSIENT_RETRIES 0
}

run_ci_phase() {
    local phase=$1 out action bail_reason merge_out merge_result error_text rc ci_args merge_args fail_file pr_number pr_repo pr_state
    if [ "$(read_state REPO_UNAVAILABLE)" = "true" ] || [ -z "$(read_state PR_NUMBER)" ]; then
        if [ "$phase" = "ci-initial" ]; then
            advance_phase ci-merge
        else
            clear_stall_keys_for_postmerge
            advance_phase postmerge
        fi
        return 0
    fi
    if [ "$phase" = "ci-merge" ] && { [ "$(read_state MERGE)" != "true" ] || [ "$(read_state DRAFT)" = "true" ] || [ "$(read_state FORKED_TARGET)" = "true" ]; }; then
        clear_stall_keys_for_postmerge
        advance_phase postmerge
        return 0
    fi
    emit_breadcrumb "→ ship-pr: CI watch (${phase})"

    ci_args=()
    while IFS= read -r arg; do ci_args+=("$arg"); done <<EOF
$(ci_common_args)
EOF
    fail_file=$(failure_capture_path "$phase")
    out=$("$SCRIPT_DIR/ci-wait.sh" "${ci_args[@]}" 2>"$fail_file")
    rc=$?
    printf '%s\n' "$out" >> "$fail_file"
    if [ "$rc" -ne 0 ]; then
        record_failure "$phase" "ci-wait.sh" "$rc" "$fail_file" "CI Issues"
        exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
    fi
    record_ci_counters "$out"
    action=$(kv_value ACTION "$out")
    case "$action" in
        merge)
            if [ "$phase" = "ci-initial" ]; then
                state_set CI_PASSED true
                emit_breadcrumb "→ ship-pr: CI green"
                advance_phase ci-merge
                return 0
            fi
            merge_args=(--pr "$(read_state PR_NUMBER)" --repo "$(read_state REPO)")
            [ "$NO_ADMIN_FALLBACK" = "true" ] && merge_args+=(--no-admin-fallback)
            fail_file=$(failure_capture_path ci-merge)
            merge_out=$("$SCRIPT_DIR/merge-pr.sh" "${merge_args[@]}" 2>"$fail_file")
            rc=$?
            printf '%s\n' "$merge_out" >> "$fail_file"
            merge_result=$(kv_value MERGE_RESULT "$merge_out")
            error_text=$(kv_value ERROR "$merge_out")
            if [ "$rc" -ne 0 ]; then
                record_failure ci-merge "merge-pr.sh" "$rc" "$fail_file" "CI Issues"
            fi
            case "$merge_result" in
                merged|admin_merged)
                    state_set_many PR_CLOSED true MERGE_RESULT "$merge_result" BAIL_REASON "" STALL_TRACKING false STALL_STEP ""
                    emit_breadcrumb "→ ship-pr: merged"
                    rename_done_best_effort
                    write_post_merge_sentinel
                    advance_phase postmerge
                    ;;
                main_advanced|ci_not_ready)
                    return 0
                    ;;
                version_already_published)
                    pr_number=$(read_state PR_NUMBER)
                    pr_repo=$(read_state REPO)
                    pr_state=""
                    if [ -n "$pr_number" ] && [ -n "$pr_repo" ]; then
                        pr_state=$(gh pr view "$pr_number" --repo "$pr_repo" --json state --jq '.state' 2>/dev/null || true)
                    fi
                    if [ "$pr_state" = "MERGED" ]; then
                        state_set_many PR_CLOSED true MERGE_RESULT already_merged BAIL_REASON "" STALL_TRACKING false STALL_STEP ""
                        emit_breadcrumb "→ ship-pr: merged"
                        rename_done_best_effort
                        write_post_merge_sentinel
                        advance_phase postmerge
                    else
                        run_rebase_rebump "$phase"
                    fi
                    return 0
                    ;;
                policy_denied|admin_failed|error)
                    if [[ "$merge_result" == "error" || "$merge_result" == "admin_failed" ]] && is_transient_net_signature "$error_text"; then
                        exit_transient_net "merge-pr: $error_text"
                    fi
                    if [[ "$merge_result" == "error" ]] && is_head_divergence_recoverable "$error_text"; then
                        run_rebase_rebump "$phase"
                        return 0
                    fi
                    [ "$rc" -ne 0 ] || record_failure ci-merge "merge-pr.sh envelope" 1 "$fail_file" "CI Issues"
                    state_set_many BAIL_REASON "$error_text" STALL_TRACKING true STALL_STEP 12d
                    printf '\n--- ORCHESTRATOR DIRECTIVE (STALL_STEP=12d) ---\nDO NOT improvise recovery. Do NOT patch state files, do NOT force-push, do NOT re-invoke ship-pr.sh manually.\nCorrect action: read STALL_TRACKING and STALL_STEP from state, then continue to Step 16 per skills/implement/SKILL.md.\n' >> "$fail_file"
                    exit 4
                    ;;
                *) exit_stall 12b ;;
            esac
            ;;
        rebase)
            if [ "$(read_state FORKED_TARGET)" = "true" ]; then
                fail_file=$(failure_capture_path rebase)
                "$SCRIPT_DIR/rebase-push.sh" --base-remote upstream --base-ref main > "$fail_file" 2>&1
                rc=$?
                if [ "$rc" -ne 0 ]; then
                    record_failure rebase "rebase-push.sh fork" "$rc" "$fail_file" "CI Issues"
                    exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
                fi
                state_set_many REBASE_COUNT "$(( $(read_state REBASE_COUNT) + 1 ))" ITERATION "$(( $(read_state ITERATION) + 1 ))" TRANSIENT_RETRIES 0
                return 0
            fi
            run_rebase_rebump "$phase"
            return 0
            ;;
        rebase_then_evaluate)
            run_rebase_rebump "$phase"
            run_evaluate_failure "$phase"
            ;;
        already_merged)
            state_set_many PR_CLOSED true MERGE_RESULT already_merged BAIL_REASON "" STALL_TRACKING false STALL_STEP ""
            emit_breadcrumb "→ ship-pr: merged"
            rename_done_best_effort
            write_post_merge_sentinel
            advance_phase postmerge
            ;;
        evaluate_failure)
            run_evaluate_failure "$phase"
            ;;
        bail)
            bail_reason=$(kv_value BAIL_REASON "$out")
            state_set BAIL_REASON "$bail_reason"
            if is_transient_net_signature "$bail_reason"; then
                exit_transient_net "ci-wait: $bail_reason"
            fi
            if needs_user_bail_reason "$bail_reason"; then
                state_set BAIL_NEEDS_USER_INPUT true
                exit 3
            fi
            exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12d)"
            ;;
        *) exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)" ;;
    esac
}

run_postmerge_phase() {
    local rc fail_file
    emit_breadcrumb "→ ship-pr: postmerge"
    write_finalize_state
    fail_file=$(failure_capture_path postmerge)
    "$SCRIPT_DIR/implement-finalize.sh" postmerge --state-file "$IMPLEMENT_TMPDIR/finalize-state.sh" --final-bail-reason-file "$IMPLEMENT_TMPDIR/final-bail-reason.txt" > "$fail_file" 2>&1
    rc=$?
    [ "$rc" -eq 0 ] || record_failure postmerge "implement-finalize.sh postmerge" "$rc" "$fail_file"
    # Finalize manifest to status=done here so the update survives if the
    # LLM session ends before prompt-side Step 18 teardown runs. The manifest
    # fields are committed by the session-transcript capture in Step 18.
    local flush_run_id pr_num manifest_path_pm flush_issue_num recovery_ok
    flush_run_id=$(read_state RUN_ID)
    pr_num=$(read_state PR_NUMBER)
    if [ -n "$flush_run_id" ] && [ -n "$pr_num" ] && [ "$(read_state REPO_UNAVAILABLE)" = "false" ] && [ "$(read_state PR_CLOSED)" = "true" ]; then
        manifest_path_pm="$IMPLEMENT_TMPDIR/larch-logs/implement/$flush_run_id/manifest.json"
        recovery_ok=true
        if [ ! -f "$manifest_path_pm" ]; then
            flush_issue_num=$(read_state ISSUE_NUMBER)
            fail_file=$(failure_capture_path postmerge)
            if [ -n "$flush_issue_num" ]; then
                "$SCRIPT_DIR/larch-log.sh" init \
                    --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                    --skill implement --run-id "$flush_run_id" \
                    --issue "$flush_issue_num" \
                    > "$fail_file" 2>&1
            else
                "$SCRIPT_DIR/larch-log.sh" init \
                    --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                    --skill implement --run-id "$flush_run_id" \
                    > "$fail_file" 2>&1
            fi
            rc=$?
            if [ "$rc" -ne 0 ]; then
                record_failure postmerge "larch-log.sh init (manifest-recovery)" "$rc" "$fail_file" Warnings
                recovery_ok=false
            else
                fail_file=$(failure_capture_path postmerge)
                "$SCRIPT_DIR/larch-log.sh" manifest \
                    --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                    --skill implement --run-id "$flush_run_id" \
                    --field "status=partial" \
                    --field "recovery_reason=manifest_lost_mid_run" \
                    > "$fail_file" 2>&1
                rc=$?
                [ "$rc" -eq 0 ] || record_failure postmerge "larch-log.sh manifest (partial-tag)" "$rc" "$fail_file" Warnings
            fi
        fi
        if [ "$recovery_ok" = "false" ]; then
            # Skip commit: manifest synthesis failed, committing would produce a partial dir.
            :
        else
            fail_file=$(failure_capture_path postmerge)
            "$SCRIPT_DIR/larch-log.sh" manifest \
                --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                --skill implement --run-id "$flush_run_id" \
                --field "status=done" \
                --field "pr_number=$pr_num" \
                > "$fail_file" 2>&1
            rc=$?
            [ "$rc" -eq 0 ] || record_failure postmerge "larch-log.sh manifest" "$rc" "$fail_file" Warnings
        fi
    fi
    advance_phase "done"
    exit 0
}

if [ -n "$RESUME_PHASE" ]; then
    case "$RESUME_PHASE" in
        force-push-gate|bump) advance_phase bump ;;
        pr-create) state_set OOS_PENDING false; advance_phase pr-create ;;
        ci-initial) advance_phase ci-initial ;;
        ci-merge) state_set CI_PASSED false; advance_phase ci-merge ;;
        evaluate-failure) advance_phase evaluate-failure ;;
        postmerge) advance_phase postmerge ;;
        *) die_usage "unknown --resume-phase: $RESUME_PHASE" ;;
    esac
fi

while :; do
    case "$(read_state PHASE)" in
        checks) run_checks_phase ;;
        bump) run_bump_phase ;;
        pr-prep) run_pr_prep_phase ;;
        pr-create) run_pr_create_phase ;;
        ci-initial) run_ci_phase ci-initial ;;
        ci-merge) run_ci_phase ci-merge ;;
        evaluate-failure)
            # Use CALLER_KIND to pass the originating CI phase so stall-step
            # numbers are correct (step 10 vs 12c).
            case "$(read_state CALLER_KIND)" in
                step10_rebase_then_evaluate) run_evaluate_failure ci-initial ;;
                *)                          run_evaluate_failure ci-merge ;;
            esac
            advance_phase ci-merge
            ;;
        postmerge) run_postmerge_phase ;;
        done) exit 0 ;;
        *) die_usage "unknown PHASE in state-file: $(read_state PHASE)" ;;
    esac
done
