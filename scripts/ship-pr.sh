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
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-net.sh
source "$SCRIPT_DIR/lib-net.sh" || { larch_err "ship-pr.sh: failed to source lib-net.sh"; exit 1; }
[[ "${LARCH_LIB_NET_LOADED:-}" == "1" ]] || { larch_err "ship-pr.sh: lib-net.sh sourced but sentinel missing"; exit 1; }
# shellcheck source=scripts/lib-finalize-state-keys.sh
source "$SCRIPT_DIR/lib-finalize-state-keys.sh" || { larch_err "ship-pr.sh: failed to source lib-finalize-state-keys.sh"; exit 1; }
[[ "${LARCH_LIB_FINALIZE_STATE_KEYS_LOADED:-}" == "1" ]] || { larch_err "ship-pr.sh: lib-finalize-state-keys.sh sourced but sentinel missing"; exit 1; }
# shellcheck source=scripts/lib-failed-agent-stderr-tail.sh
source "$SCRIPT_DIR/lib-failed-agent-stderr-tail.sh" || { larch_err "ship-pr.sh: failed to source lib-failed-agent-stderr-tail.sh"; exit 1; }

STATE_FILE=""
IMPLEMENT_TMPDIR=""
MERGE=""
DRAFT=""
FORKED_TARGET=""
NO_ADMIN_FALLBACK="false"
NO_LOGS_COMMIT="false"
REPO_ARG=""
RESUME_PHASE=""
INIT_BRANCH_NAME=""
INIT_BRANCH_NAME_SET=false
INIT_ISSUE_NUMBER=""
INIT_ISSUE_NUMBER_SET=false
INIT_RUN_ID=""
INIT_RUN_ID_SET=false
INIT_MANIFEST_PATH=""
INIT_MANIFEST_PATH_SET=false
INIT_TOOL_LABEL=""
INIT_TOOL_LABEL_SET=false
INIT_EXPECTED_SESSION_ID=""
INIT_EXPECTED_SESSION_ID_SET=false
INIT_EXPECTED_TMPDIR_BASENAME_PREFIX=""
INIT_EXPECTED_TMPDIR_BASENAME_PREFIX_SET=false
FORCE_INIT_STATE=false

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage:
  ship-pr.sh --state-file PATH --implement-tmpdir PATH --merge true|false --draft true|false --forked true|false --repo OWNER/REPO [--branch-name VALUE] [--expected-session-id VALUE] [--expected-tmpdir-basename-prefix VALUE] [--force-init-state true|false] [--issue-number VALUE] [--manifest-path VALUE] [--run-id VALUE] [--tool-label VALUE] [--no-admin-fallback true|false] [--no-logs-commit true|false] [--resume-phase PHASE]
USAGE
}

LAST_LINT_FIX_DELTA_PATHS_FILE=""
ALL_LINT_FIX_DELTA_PATHS_FILE=""
LAST_STAGE_AND_PUSH_PRE_REFRESH_HEAD=""
CI_FIX_REBASE_PENDING=false

_ci_fix_pending_hydrate() {
    if ! state_has_key CI_FIX_REBASE_PENDING; then
        state_set CI_FIX_REBASE_PENDING false
    fi
    case "$(read_state CI_FIX_REBASE_PENDING)" in
        true) CI_FIX_REBASE_PENDING=true ;;
        *) CI_FIX_REBASE_PENDING=false ;;
    esac
}

_ci_fix_pending_set() {
    CI_FIX_REBASE_PENDING=true
    state_set CI_FIX_REBASE_PENDING true
}

_ci_fix_pending_clear() {
    CI_FIX_REBASE_PENDING=false
    state_set CI_FIX_REBASE_PENDING false
}

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

# True when captured helper stdout reports a non-failing terminal state
# (checks ran successfully, or the consumer repo omitted scripts/relevant-checks.sh).
is_relevant_checks_clean() {
    printf '%s\n' "$1" | grep -qE '^RELEVANT_CHECKS_(OK|SKIPPED)=true '
}

_surface_ci_stderr_tail() {
    local stem="$1"
    [[ -n "$stem" ]] || return 0
    emit_failed_agent_stderr_tail_larch_err "$stem" || true
}

_surface_lint_fix_stderr_tail() {
    local fix_out="$1" stem=""
    stem=$(printf '%s\n' "$fix_out" | awk -F= '/^STDERR_TAIL_PATH=/ { print substr($0, index($0,"=")+1); exit }')
    if [[ -z "$stem" ]]; then
        stem=$(printf '%s\n' "$fix_out" | awk -F= '/^CODER_LOG_FILE=/ { print substr($0, index($0,"=")+1); exit }')
    fi
    [[ -n "$stem" ]] || return 0
    _surface_ci_stderr_tail "$stem"
}

run_lint_fix_loop_capture() {
    local fail_file=$1 site=$2 redacted_log=$3 out_var=$4 rc_var=$5 target_cmd_args_file=${6:-}
    local output rc had_errexit=0
    local extra_args=()
    if [[ -n "$target_cmd_args_file" ]]; then
        extra_args=(--target-cmd-args-file "$target_cmd_args_file")
    fi
    case $- in *e*) had_errexit=1 ;; esac
    set +e
    output=$("$SCRIPT_DIR/lint-fix-loop.sh" \
        --tmpdir "$IMPLEMENT_TMPDIR" \
        --site "$site" \
        --checks-log "$redacted_log" \
        ${extra_args[@]+"${extra_args[@]}"} 2>"$fail_file")
    rc=$?
    (( had_errexit )) && set -e
    printf -v "$out_var" '%s' "$output"
    printf -v "$rc_var" '%s' "$rc"
    local lint_status=""
    lint_status=$(printf '%s\n' "$output" | awk -F= '/^LINT_FIX_STATUS=/ { print $2; exit }')
    if [[ "$rc" -ne 0 ]] \
        || [[ "$lint_status" == "failed" || "$lint_status" == "main-agent-required" ]]; then
        _surface_lint_fix_stderr_tail "$output"
    elif [[ -z "$lint_status" ]]; then
        local _tail_stem="" _tail_coder=""
        _tail_stem=$(printf '%s\n' "$output" | awk -F= '/^STDERR_TAIL_PATH=/ { print substr($0, index($0,"=")+1); exit }')
        _tail_coder=$(printf '%s\n' "$output" | awk -F= '/^CODER_LOG_FILE=/ { print substr($0, index($0,"=")+1); exit }')
        if [[ -n "$_tail_stem" && -s "${_tail_stem}.stderr-tail" ]] \
            || [[ -n "$_tail_coder" && -s "${_tail_coder}.stderr-tail" ]]; then
            _surface_lint_fix_stderr_tail "$output"
        fi
    fi
}

_RCC_STATUS=""
_RCC_LAST_LOG_PATH=""
_RCC_DELTA_PATHS_FILE=""
_RCC_RERUN_FN=""
_RCC_SITE=""
_RCC_TARGET_CMD_ARGS_FILE=""
_RCC_MAX_ITER=3
_RCC_CMD_RC=1
_RCC_RAW_LOG_PATH=""
_RCC_DISPATCH_FIRST=0
_RCC_INITIAL_REDACTED_LOG=""
_RCC_LAST_FIX_STATUS=""
_RCC_LAST_FIX_RC=0

# Parses lint-fix-loop output and updates accumulated delta paths or terminal _RCC_STATUS.
# Returns 0 if status is applied/no-changes (caller continues), 1 if a terminal status was set.
_rcc_handle_fix_status() {
    local fix_out=$1 fix_rc=$2
    local fix_status fix_delta_paths_file failure_reason
    fix_status=$(printf '%s\n' "$fix_out" | awk -F= '/^LINT_FIX_STATUS=/ { print $2; exit }')
    fix_delta_paths_file=$(printf '%s\n' "$fix_out" | awk -F= '/^LINT_FIX_DELTA_PATHS_FILE=/ { print substr($0, index($0,"=")+1); exit }')
    failure_reason=$(printf '%s\n' "$fix_out" | awk -F= '/^FAILURE_REASON=/ { print substr($0, index($0,"=")+1); exit }')
    _RCC_LAST_FIX_STATUS="$fix_status"
    _RCC_LAST_FIX_RC="$fix_rc"
    case "$fix_status" in
        applied|no-changes)
            if [[ "$fix_status" == "applied" && -n "$fix_delta_paths_file" && -f "$fix_delta_paths_file" ]]; then
                append_unique_paths_file "$_RCC_DELTA_PATHS_FILE" "$fix_delta_paths_file"
            fi
            return 0
            ;;
        main-agent-required)
            _RCC_STATUS=main-agent-required
            return 1
            ;;
        failed)
            if [[ "$failure_reason" == "head-changed-after-dispatch" ]]; then
                _RCC_STATUS=head-changed
            else
                _RCC_STATUS=dispatch-failed
            fi
            return 1
            ;;
        *)
            _RCC_STATUS=dispatch-failed
            return 1
            ;;
    esac
}

normalize_rcc_max_iter() {
    local raw=${1:-}
    awk -v raw="$raw" '
        BEGIN {
            if (raw !~ /^[0-9]+$/) {
                print 3
                exit
            }
            gsub(/^0+/, "", raw)
            if (raw == "") {
                print 3
                exit
            }
            if (length(raw) > 1) {
                print 6
                exit
            }
            if (raw < 1) {
                print 3
                exit
            }
            if (raw > 6) {
                print 6
                exit
            }
            print raw
        }
    '
}

run_captured_cmd_then_fix_loop() {
    local attempt max_iter fail_file redacted_log fix_out fix_rc
    local empty_failures=0
    local dispatch_first="${_RCC_DISPATCH_FIRST:-0}"
    local redacted_log_for_dispatch=""

    _RCC_STATUS=exhausted
    _RCC_LAST_LOG_PATH=""
    _RCC_LAST_FIX_STATUS=""
    _RCC_LAST_FIX_RC=0
    _RCC_DELTA_PATHS_FILE="$IMPLEMENT_TMPDIR/rcc-delta-paths-$$-$RANDOM.txt"
    : > "$_RCC_DELTA_PATHS_FILE"
    max_iter=$(normalize_rcc_max_iter "${_RCC_MAX_ITER:-3}")

    if [ "$dispatch_first" = "1" ]; then
        redacted_log_for_dispatch="${_RCC_INITIAL_REDACTED_LOG:-}"
    fi

    for ((attempt=1; attempt<=max_iter; attempt++)); do
        if [ "$dispatch_first" = "1" ]; then
            # dispatch-first pattern: lint-fix dispatch on the prior redacted log, then rerun the captured cmd
            if [ -z "$redacted_log_for_dispatch" ] || [ ! -f "$redacted_log_for_dispatch" ]; then
                _RCC_STATUS=dispatch-failed
                return 1
            fi
            fail_file=$(failure_capture_path "${_RCC_PHASE:-evaluate-failure}")
            run_lint_fix_loop_capture "$fail_file" "$_RCC_SITE" "$redacted_log_for_dispatch" fix_out fix_rc "$_RCC_TARGET_CMD_ARGS_FILE"
            printf '%s\n' "$fix_out" >> "$fail_file"
            if ! _rcc_handle_fix_status "$fix_out" "$fix_rc"; then
                return 1
            fi
            # Re-run the captured command to verify the dispatched fix
            "$_RCC_RERUN_FN"
            _RCC_LAST_LOG_PATH="$_RCC_RAW_LOG_PATH"
            if [ "${_RCC_CMD_RC:-1}" -eq 0 ]; then
                _RCC_STATUS=ok
                return 0
            fi
            # Rerun still failing after a no-changes dispatch is a stale-fix signal —
            # repeating won't help. Match the original run_checks_with_lint_fix_loop semantics.
            if [ "$_RCC_LAST_FIX_STATUS" = "no-changes" ]; then
                _RCC_STATUS=no-changes-stale
                return 1
            fi
            # applied + still failing → set up the next iteration's redacted log
            if [ -z "${_RCC_RAW_LOG_PATH:-}" ] || [ ! -f "$_RCC_RAW_LOG_PATH" ]; then
                _RCC_STATUS=exhausted
                return 1
            fi
            redacted_log_for_dispatch="${_RCC_RAW_LOG_PATH}.redacted"
            if ! "$SCRIPT_DIR/redact-secrets.sh" < "$_RCC_RAW_LOG_PATH" > "$redacted_log_for_dispatch" 2>/dev/null; then
                _RCC_STATUS=dispatch-failed
                return 1
            fi
        else
            # check-first pattern: rerun the captured cmd, dispatch lint-fix on failure
            "$_RCC_RERUN_FN"
            _RCC_LAST_LOG_PATH="$_RCC_RAW_LOG_PATH"
            if [ "${_RCC_CMD_RC:-1}" -eq 0 ]; then
                _RCC_STATUS=ok
                return 0
            fi
            if [ -z "${_RCC_RAW_LOG_PATH:-}" ] || [ ! -s "$_RCC_RAW_LOG_PATH" ]; then
                empty_failures=$((empty_failures + 1))
                [ "$empty_failures" -ge 2 ] && { _RCC_STATUS=exhausted; return 1; }
                continue
            fi
            empty_failures=0
            redacted_log="${_RCC_RAW_LOG_PATH}.redacted"
            if ! "$SCRIPT_DIR/redact-secrets.sh" < "$_RCC_RAW_LOG_PATH" > "$redacted_log" 2>/dev/null; then
                _RCC_STATUS=dispatch-failed
                return 1
            fi
            fail_file=$(failure_capture_path "${_RCC_PHASE:-evaluate-failure}")
            run_lint_fix_loop_capture "$fail_file" "$_RCC_SITE" "$redacted_log" fix_out fix_rc "$_RCC_TARGET_CMD_ARGS_FILE"
            printf '%s\n' "$fix_out" >> "$fail_file"
            if ! _rcc_handle_fix_status "$fix_out" "$fix_rc"; then
                return 1
            fi
        fi
    done
    _RCC_STATUS=exhausted
    return 1
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

# True when path resolves under IMPLEMENT_TMPDIR (physical dirs; handles /tmp
# vs /private/tmp symlink split on macOS).
_plan_resolved_under_implement_tmpdir() {
    local path=$1 impl_abs path_abs
    case "$path" in
        /*) ;;
        *) return 1 ;;
    esac
    impl_abs=$(cd "$IMPLEMENT_TMPDIR" && pwd -P) || return 1
    path_abs=$(cd "$(dirname "$path")" && pwd -P)/$(basename "$path") || return 1
    case "$path_abs" in
        "$impl_abs"/* | "$impl_abs") return 0 ;;
        *) return 1 ;;
    esac
}

# Returns a validated plan file path (under IMPLEMENT_TMPDIR, file exists) or empty.
# Logs a Warnings entry and returns empty on security/availability violations.
resolve_plan_file() {
    local path
    path=$(read_session_plan_file)
    if [ -z "$path" ] && [ -f "$IMPLEMENT_TMPDIR/plan.txt" ]; then
        path="$IMPLEMENT_TMPDIR/plan.txt"
    fi
    [ -n "$path" ] || return 0
    if ! _plan_resolved_under_implement_tmpdir "$path"; then
        "$SCRIPT_DIR/append-execution-issue.sh" \
            --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
            --category Warnings \
            --entry "PLAN_FILE ($path) is outside IMPLEMENT_TMPDIR; skipping plan context." \
            >/dev/null 2>&1 || true
        if [ -f "$IMPLEMENT_TMPDIR/plan.txt" ]; then
            path="$IMPLEMENT_TMPDIR/plan.txt"
        else
            return 0
        fi
    fi
    if [ ! -f "$path" ]; then
        "$SCRIPT_DIR/append-execution-issue.sh" \
            --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
            --category Warnings \
            --entry "PLAN_FILE ($path) set but file not found; proceeding without plan context." \
            >/dev/null 2>&1 || true
        if [ -f "$IMPLEMENT_TMPDIR/plan.txt" ]; then
            path="$IMPLEMENT_TMPDIR/plan.txt"
        else
            return 0
        fi
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
    if [ "$INIT_ISSUE_NUMBER_SET" = "true" ]; then
        issue=$INIT_ISSUE_NUMBER
    else
        issue=""
    fi
    if [ "$INIT_RUN_ID_SET" = "true" ]; then
        run_id=$INIT_RUN_ID
    else
        run_id="${LARCH_RUN_ID:-${RUN_ID:-$(basename "$IMPLEMENT_TMPDIR")}}"
    fi
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
        if [ "$INIT_BRANCH_NAME_SET" = "true" ]; then
            printf 'BRANCH_NAME=%s\n' "$INIT_BRANCH_NAME"
        else
            printf 'BRANCH_NAME=%s\n' "$branch"
        fi
        printf 'ISSUE_NUMBER=%s\n' "$issue"
        printf 'RUN_ID=%s\n' "$run_id"
        printf 'REPO=%s\n' "$repo"
        printf 'REPO_UNAVAILABLE=%s\n' "$([ -n "$repo" ] && echo false || echo true)"
        printf 'FORKED_TARGET=%s\n' "${FORKED_TARGET:-false}"
        printf 'MERGE=%s\n' "${MERGE:-false}"
        printf 'DRAFT=%s\n' "${DRAFT:-false}"
        printf 'DEFERRED=false\n'
        printf 'PR_CLOSED=false\n'
        printf 'DONE_RENAME_APPLIED=false\n'
        printf 'STALL_TRACKING=false\n'
        printf 'STALL_STEP=\n'
        printf 'BAIL_NEEDS_USER_INPUT=false\n'
        printf 'BAIL_REASON=\n'
        printf 'BAIL_FAILURE_DETAIL_LOG=\n'
        printf 'CI_PASSED=false\n'
        printf 'OOS_PENDING=false\n'
        printf 'PR_NUMBER=\n'
        printf 'PR_URL=\n'
        printf 'PR_TITLE=\n'
        printf 'RESUME_PHASE=\n'
        printf 'CALLER_KIND=\n'
        printf 'REBASE_COUNT=0\n'
        printf 'CI_FIX_REBASE_PENDING=false\n'
        printf 'FIX_ATTEMPTS=0\n'
        printf 'ITERATION=0\n'
        printf 'TRANSIENT_RETRIES=0\n'
        printf 'FAILED_RUN_ID=\n'
        if [ "$INIT_MANIFEST_PATH_SET" = "true" ]; then
            printf 'MANIFEST_PATH=%s\n' "$INIT_MANIFEST_PATH"
        else
            printf 'MANIFEST_PATH=%s\n' "${MANIFEST_PATH:-}"
        fi
        if [ "$INIT_TOOL_LABEL_SET" = "true" ]; then
            printf 'TOOL_LABEL=%s\n' "$INIT_TOOL_LABEL"
        else
            printf 'TOOL_LABEL=%s\n' "${TOOL_LABEL:-claude}"
        fi
        printf 'DESIGN_ONLY_DONE=false\n'
        if [ "$INIT_EXPECTED_SESSION_ID_SET" = "true" ]; then
            printf 'EXPECTED_SESSION_ID=%s\n' "$INIT_EXPECTED_SESSION_ID"
        else
            printf 'EXPECTED_SESSION_ID=%s\n' "$session_id"
        fi
        if [ "$INIT_EXPECTED_TMPDIR_BASENAME_PREFIX_SET" = "true" ]; then
            printf 'EXPECTED_TMPDIR_BASENAME_PREFIX=%s\n' "$INIT_EXPECTED_TMPDIR_BASENAME_PREFIX"
        else
            printf 'EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-%s-\n' "$clone_tag_full"
        fi
        printf 'NO_LOGS_COMMIT=%s\n' "${NO_LOGS_COMMIT:-false}"
        printf 'IMPLEMENT_TMPDIR=%s\n' "$IMPLEMENT_TMPDIR"
    } > "$tmp" && mv "$tmp" "$STATE_FILE"
}

require_key() {
    state_has_key "$1" || die_usage "state-file missing required key: $1"
}

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
                "$SCRIPT_DIR/redact-secrets.sh" < "$output_file" | sanitize_diagnostic_line | while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done || \
                    sanitize_diagnostic_line < "$output_file" | while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done
            else
                sanitize_diagnostic_line < "$output_file" | while IFS= read -r line || [[ -n "$line" ]]; do larch_err "$line"; done
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

# Canonical path for plan-review accepted OOS (mirrors skills/implement/SKILL.md disposition gate).
resolve_oos_accepted_design_path() {
    local impl="$1"
    if [[ -n "${DESIGN_TMPDIR:-}" && -f "${DESIGN_TMPDIR%/}/oos-accepted-design.md" ]]; then
        printf '%s\n' "${DESIGN_TMPDIR%/}/oos-accepted-design.md"
        return
    fi
    if [[ -f "$impl/design-export/oos-accepted-design.md" ]]; then
        printf '%s\n' "$impl/design-export/oos-accepted-design.md"
        return
    fi
    printf '%s\n' "$impl/oos-accepted-design.md"
}

# Mechanical OOS disposition check before any ship-pr path clears OOS_PENDING to
# false (mirrors skills/implement/SKILL.md Step 8+ gate argv shape).
run_oos_disposition_gate_if_required_before_oos_pending_false() {
    local gate_script="$PLUGIN_ROOT/skills/implement/scripts/oos-disposition-gate.sh"
    local forked repo_un repo_root oos_mb oos_range run_id oos_ndjson oos_list oos_n gate_log gate_rc oos_design_path _had_errexit=0
    forked=$(read_state FORKED_TARGET)
    repo_un=$(read_state REPO_UNAVAILABLE)
    if [ "$forked" = "true" ] || [ "$repo_un" = "true" ]; then
        return 0
    fi
    if [ ! -f "$gate_script" ]; then
        larch_err "ship-pr.sh: oos-disposition-gate.sh missing at $gate_script"
        return 2
    fi
    repo_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
    oos_range="HEAD"
    if [ -n "$repo_root" ] && git -C "$repo_root" rev-parse -q --verify origin/main >/dev/null 2>&1; then
        oos_mb=$(git -C "$repo_root" merge-base HEAD origin/main 2>/dev/null || true)
        if [ -n "$oos_mb" ]; then
            oos_range="${oos_mb}..HEAD"
        else
            oos_range="origin/main..HEAD"
        fi
    fi
    run_id=$(tr -d '\r\n' < "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)
    oos_ndjson=""
    if [ -n "$run_id" ]; then
        oos_ndjson="$IMPLEMENT_TMPDIR/larch-logs/implement/$run_id/oos-issues.ndjson"
    fi
    if [ -z "$oos_ndjson" ] || [ ! -f "$oos_ndjson" ]; then
        oos_list=$(find "$IMPLEMENT_TMPDIR/larch-logs/implement" -mindepth 2 -maxdepth 2 -name oos-issues.ndjson -type f 2>/dev/null | LC_ALL=C sort || true)
        oos_n=$(printf '%s\n' "$oos_list" | sed '/^$/d' | wc -l | tr -d '[:space:]')
        if [ "${oos_n:-0}" -eq 1 ]; then
            oos_ndjson=$(printf '%s\n' "$oos_list" | sed '/^$/d' | head -n 1)
        elif [ "${oos_n:-0}" -gt 1 ] && [ -z "$run_id" ]; then
            larch_err "ship-pr.sh: ambiguous oos-issues.ndjson without session-id; refusing to clear OOS_PENDING"
            return 2
        fi
    fi
    gate_extra=()
    if [ -n "$oos_ndjson" ] && [ -f "$oos_ndjson" ]; then
        gate_extra+=(--oos-issues-ndjson "$oos_ndjson")
    fi
    oos_design_path=$(resolve_oos_accepted_design_path "$IMPLEMENT_TMPDIR")
    local non_sec_oos=0 oos_acc n
    while IFS= read -r oos_acc; do
        [ -z "$oos_acc" ] && continue
        [ -f "$oos_acc" ] || continue
        n=$(awk -f "$PLUGIN_ROOT/skills/implement/scripts/oos-non-security-block-count.awk" "$oos_acc" 2>/dev/null | tr -d '[:space:]' || printf '0')
        non_sec_oos=$((non_sec_oos + n))
    done <<EOF
$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md
$oos_design_path
$IMPLEMENT_TMPDIR/oos-accepted-review.md
EOF
    if [ "${non_sec_oos:-0}" -gt 0 ] && { [ -z "$oos_ndjson" ] || [ ! -f "$oos_ndjson" ]; }; then
        larch_err "ship-pr.sh: non-security accepted OOS requires oos-issues.ndjson evidence before clearing OOS_PENDING"
        return 2
    fi
    if [ -s "$IMPLEMENT_TMPDIR/security-oos-observations.md" ]; then
        larch_err "ship-pr.sh: security-routed manifest OOS requires private SECURITY.md disposition before clearing OOS_PENDING"
        return 2
    fi
    gate_log="$IMPLEMENT_TMPDIR/oos-disposition-gate.stderr.log"
    case $- in *e*) _had_errexit=1 ;; esac
    set +e
    bash "$gate_script" \
        "${gate_extra[@]+"${gate_extra[@]}"}" \
        --accepted-files "$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md,$oos_design_path,$IMPLEMENT_TMPDIR/oos-accepted-review.md" \
        --filed-urls-file "$IMPLEMENT_TMPDIR/oos-issues-created.md" \
        --filed-urls-strict-file "$oos_design_path" \
        --commit-range "$oos_range" 2>"$gate_log"
    gate_rc=$?
    (( _had_errexit )) && set -e
    return "$gate_rc"
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
    larch_err "⛔ ship-pr: stalled at step $1"
    state_set_many STALL_TRACKING true STALL_STEP "$1"
}

clear_stall_keys_for_postmerge() {
    state_set_many BAIL_REASON "" STALL_TRACKING false STALL_STEP ""
}

exit_stall() {
    mark_stall "$1"
    state_set EXIT_CODE 4
    exit 4
}

exit_transient_net() {
    larch_err "⚠ ship-pr: transient network failure"
    # Truncate to first line to keep BAIL_REASON a single KEY=value line in state.
    local reason
    reason=$(printf '%s' "$1" | head -1 | cut -c1-200)
    state_set_many BAIL_REASON "$reason" STALL_TRACKING false EXIT_CODE 6
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
        printf 'BUMP_TYPE=NONE\n'
        printf 'NEW_VERSION=\n'
        printf 'RUN_ID=%s\n' "$(read_state RUN_ID)"
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

# Stage, commit, and push the working-tree edits the checks recovery waterfall
# just produced. Returns 0 on success (or when there is nothing to publish) and
# non-zero on stage/commit/push failure. Each failure is recorded under the
# default "Tool Failures" category and the caller is responsible for the stall.
# Existing pattern (#2395 review): replaced `git add -A | git-commit | git-push`
# with trailing `|| true` so a hook rejection or non-fast-forward push no longer
# silently advances `PHASE` to `bump` on a dirty or unpushed tree.
commit_post_waterfall_checks_fix_or_stall() {
    local fail_file rc_post porcelain
    porcelain=$(git status --porcelain 2>/dev/null || true)
    if [[ -z "$porcelain" ]]; then
        return 0
    fi
    fail_file=$(failure_capture_path checks)
    rc_post=0
    git add -A >>"$fail_file" 2>&1 || rc_post=$?
    if [ "$rc_post" -ne 0 ]; then
        record_failure checks "git add -A (post-checks-waterfall)" "$rc_post" "$fail_file"
        return 1
    fi
    "$SCRIPT_DIR/git-commit.sh" -m "Fix checks (recovery waterfall)" >>"$fail_file" 2>&1 || rc_post=$?
    if [ "$rc_post" -ne 0 ]; then
        record_failure checks "git-commit.sh (post-checks-waterfall)" "$rc_post" "$fail_file"
        return 1
    fi
    "$SCRIPT_DIR/git-push.sh" >>"$fail_file" 2>&1 || rc_post=$?
    if [ "$rc_post" -ne 0 ]; then
        record_failure checks "git-push.sh (post-checks-waterfall)" "$rc_post" "$fail_file"
        return 1
    fi
    return 0
}

run_checks_phase() {
    local out rc fail_file redacted_log fix_out fix_status fix_rc
    local lint_attempt
    larch_err "→ ship-pr: checks"
    fail_file=$(failure_capture_path checks)
    capture_command_output out "$fail_file" "$SCRIPT_DIR/run-relevant-checks-captured.sh" --site step6 --tmpdir "$IMPLEMENT_TMPDIR"
    rc=$?
    printf '%s\n' "$out" >> "$fail_file"
    if [ "$rc" -eq 0 ] && is_relevant_checks_clean "$out"; then
        advance_phase bump
        return 0
    fi
    redacted_log=$(printf '%s\n' "$out" | awk -F= '/^REDACTED_LOG_FILE=/ { print substr($0, index($0,"=")+1); exit }')
    redacted_log=$(resolve_checks_log_path "$redacted_log") || {
        record_failure checks "run-relevant-checks-captured.sh" "$rc" "$fail_file"
        if run_recovery_waterfall checks fix "$fail_file" checks-step6; then
            commit_post_waterfall_checks_fix_or_stall || exit_stall 6
            advance_phase bump
            return 0
        fi
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
                if [ "$rc" -eq 0 ] && is_relevant_checks_clean "$out"; then
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
    if run_recovery_waterfall checks fix "$fail_file" checks-step6; then
        commit_post_waterfall_checks_fix_or_stall || exit_stall 6
        advance_phase bump
        return 0
    fi
    exit_stall 6
}

lint_fix_site_for_phase() {
    case "$1" in
        ci-initial|checks) printf '%s\n' ship-pr-ci-initial ;;
        ci-merge|evaluate-failure) printf '%s\n' ship-pr-ci-merge ;;
        *) return 1 ;;
    esac
}

# Rerun callback used by run_checks_with_lint_fix_loop via run_captured_cmd_then_fix_loop.
# Reads $_RCWL_CHECKS_SITE for the --site arg. Sets _RCC_RAW_LOG_PATH to the script's
# REDACTED_LOG_FILE and _RCC_CMD_RC to 0/1 based on RELEVANT_CHECKS_OK.
_RCWL_CHECKS_SITE=""

_run_relevant_checks_capture() {
    local out rc redacted_log fail_file
    fail_file=$(failure_capture_path "${_RCC_PHASE:-evaluate-failure}")
    capture_command_output out "$fail_file" "$SCRIPT_DIR/run-relevant-checks-captured.sh" --site "$_RCWL_CHECKS_SITE" --tmpdir "$IMPLEMENT_TMPDIR"
    rc=$?
    printf '%s\n' "$out" >> "$fail_file"
    if [ "$rc" -eq 0 ] && is_relevant_checks_clean "$out"; then
        _RCC_RAW_LOG_PATH=""
        _RCC_CMD_RC=0
        return
    fi
    redacted_log=$(printf '%s\n' "$out" | awk -F= '/^REDACTED_LOG_FILE=/ { print substr($0, index($0,"=")+1); exit }')
    redacted_log=$(resolve_checks_log_path "$redacted_log") || redacted_log=""
    _RCC_RAW_LOG_PATH="$redacted_log"
    _RCC_CMD_RC=1
}

run_checks_with_lint_fix_loop() {
    local phase=$1 checks_site=$2 fix_site redacted_log
    local fail_category fail_file out rc vendor_dirty_paths_file

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
    if [ "$rc" -eq 0 ] && is_relevant_checks_clean "$out"; then
        return 0
    fi
    redacted_log=$(printf '%s\n' "$out" | awk -F= '/^REDACTED_LOG_FILE=/ { print substr($0, index($0,"=")+1); exit }')
    redacted_log=$(resolve_checks_log_path "$redacted_log") || {
        record_failure "$phase" "run-relevant-checks-captured.sh" "$rc" "$fail_file" "$fail_category"
        return 1
    }
    vendor_dirty_paths_file="$IMPLEMENT_TMPDIR/${phase}-vendor-dirty-paths.txt"
    capture_dirty_paths > "$vendor_dirty_paths_file"

    # Delegate the inner dispatch+recheck loop to the shared capture/fix helper.
    # _RCC_DISPATCH_FIRST=1 routes through the dispatch-then-rerun pattern that matches
    # this site's original semantics (initial check happened above; loop body re-checks
    # after each lint-fix dispatch and short-circuits on no-changes-then-fail).
    _RCWL_CHECKS_SITE="$checks_site"
    _RCC_PHASE="$phase"
    _RCC_RERUN_FN=_run_relevant_checks_capture
    _RCC_SITE="$fix_site"
    _RCC_TARGET_CMD_ARGS_FILE=""
    _RCC_MAX_ITER=3
    _RCC_DISPATCH_FIRST=1
    _RCC_INITIAL_REDACTED_LOG="$redacted_log"
    run_captured_cmd_then_fix_loop
    # Reset dispatch-first so subsequent (per-job) calls inherit defaults.
    _RCC_DISPATCH_FIRST=0
    _RCC_INITIAL_REDACTED_LOG=""

    case "$_RCC_STATUS" in
        ok)
            if [[ -s "$_RCC_DELTA_PATHS_FILE" ]]; then
                cp "$_RCC_DELTA_PATHS_FILE" "$ALL_LINT_FIX_DELTA_PATHS_FILE"
                LAST_LINT_FIX_DELTA_PATHS_FILE="$ALL_LINT_FIX_DELTA_PATHS_FILE"
            fi
            return 0
            ;;
        no-changes-stale|exhausted)
            fail_file=$(failure_capture_path "$phase")
            record_failure "$phase" "run-relevant-checks-captured.sh" 1 "$fail_file" "$fail_category"
            return 1
            ;;
        main-agent-required|dispatch-failed|head-changed)
            fail_file=$(failure_capture_path "$phase")
            record_failure "$phase" "lint-fix-loop.sh" "${_RCC_LAST_FIX_RC:-1}" "$fail_file" "$fail_category"
            return 1
            ;;
        *)
            fail_file=$(failure_capture_path "$phase")
            record_failure "$phase" "lint-fix-loop.sh" 1 "$fail_file" "$fail_category"
            return 1
            ;;
    esac
}

run_ship_branch_guard() {
    local failure_phase=$1 stall_token=${2:-bump-branch-guard}
    local forked _ship_guard_state_branch _ship_guard_branch _ship_guard_fail
    forked=$(read_state FORKED_TARGET)
    _ship_guard_state_branch=$(read_state BRANCH_NAME)
    # Match scripts/git-current-branch.sh: symbolic-ref works on older Git than
    # `git branch --show-current` (2.22+); empty here means detached / no branch.
    _ship_guard_branch=$(git symbolic-ref -q --short HEAD 2>/dev/null || echo "")
    if [[ -z "$_ship_guard_state_branch" || -z "$_ship_guard_branch" ]]; then
        _ship_guard_fail=$(failure_capture_path "$failure_phase")
        printf 'ship-branch-guard: BRANCH_NAME=%s current=%s\n' \
            "$_ship_guard_state_branch" "$_ship_guard_branch" > "$_ship_guard_fail"
        record_failure "$failure_phase" "ship-branch-guard" 1 "$_ship_guard_fail"
        exit_stall "$stall_token"
    fi
    if [[ "$_ship_guard_branch" != "$_ship_guard_state_branch" ]]; then
        _ship_guard_fail=$(failure_capture_path "$failure_phase")
        printf 'ship-branch-guard: BRANCH_NAME=%s current=%s\n' \
            "$_ship_guard_state_branch" "$_ship_guard_branch" > "$_ship_guard_fail"
        record_failure "$failure_phase" "ship-branch-guard" 1 "$_ship_guard_fail"
        exit_stall "$stall_token"
    fi
    # FORKED_TARGET=true is an intentional operator/runbook trust signal
    # documented in scripts/ship-pr.md: when BRANCH_NAME matches checkout, ship may
    # proceed on main/master for forked upstream-target flows. Non-forked runs
    # always stall here on those branch names even when checkout matches.
    # There is no extra fork-evidence probe beyond state + branch-name alignment.
    if [[ "$forked" != "true" ]] && { [[ "$_ship_guard_state_branch" == "main" ]] || [[ "$_ship_guard_state_branch" == "master" ]]; }; then
        _ship_guard_fail=$(failure_capture_path "$failure_phase")
        printf 'ship-branch-guard: BRANCH_NAME=%s current=%s\n' \
            "$_ship_guard_state_branch" "$_ship_guard_branch" > "$_ship_guard_fail"
        record_failure "$failure_phase" "ship-branch-guard" 1 "$_ship_guard_fail"
        exit_stall "$stall_token"
    fi
}

_clear_phase1_postbump_residue() {
    local resume
    rm -f "${IMPLEMENT_TMPDIR}/.postbump-phase" 2>/dev/null || true
    state_set CALLER_KIND ""
    resume=$(read_state RESUME_PHASE)
    case "$resume" in
        force-push-gate|step8b_rebase|step8_apply_bump_same_version|bump)
            state_set RESUME_PHASE ""
            ;;
    esac
}

run_bump_phase() {
    local finalize_out status rc fail_file
    _clear_phase1_postbump_residue
    run_ship_branch_guard bump bump-branch-guard
    larch_err "→ ship-pr: ship (no per-PR version bump)"

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
            emit '⏩ 8: version bump status=skip reason=phase1-no-per-pr-bump'
            advance_phase pr-prep
            ;;
        rebase-failed|push-failed|remote-check-failed|branch-mismatch|postbump-state-corrupt)
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
    local summary tests closes code_flow_file composed_summary plan_goals_file run_id fail_file gate_rc oos_design_path _had_errexit=0 manifest_path materialize_oos materialize_rc
    larch_err "→ ship-pr: PR prep"
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
        printf '<details><summary>Code Flow Diagram</summary>\n\n'
        sanitize_diagram_or_placeholder "$code_flow_file" "Code flow diagram not available." code-flow
        printf '\n</details>\n\n'
        printf '<details><summary>Test plan</summary>\n\n%s\n\n</details>\n\n' "$tests"
        printf '%s\n\nGenerated with [Claude Code](https://claude.com/claude-code)\n' "$closes"
    } > "$IMPLEMENT_TMPDIR/pr-body.md"

    manifest_path=$(read_state MANIFEST_PATH)
    materialize_oos="$PLUGIN_ROOT/skills/implement/scripts/materialize-manifest-oos.sh"
    if [ -n "$manifest_path" ] && [ -f "$manifest_path" ]; then
        materialize_count=""
        materialize_count_rc=0
        materialize_count=$(bash "$materialize_oos" --count-only --manifest-path "$manifest_path" --implement-tmpdir "$IMPLEMENT_TMPDIR" 2>/dev/null) || materialize_count_rc=$?
        fail_file=$(failure_capture_path pr-prep)
        _had_errexit=0
        case $- in *e*) _had_errexit=1 ;; esac
        set +e
        bash "$materialize_oos" --manifest-path "$manifest_path" --implement-tmpdir "$IMPLEMENT_TMPDIR" >"$fail_file" 2>&1
        materialize_rc=$?
        (( _had_errexit )) && set -e
        if [ "$materialize_rc" -ne 0 ]; then
            record_failure pr-prep "materialize-manifest-oos.sh" "$materialize_rc" "$fail_file" Tool Failures
            if [ "$materialize_count_rc" -ne 0 ] || [ "${materialize_count:-0}" -gt 0 ]; then
                state_set OOS_PENDING true
                advance_phase pr-create
                exit 0
            fi
        fi
    fi

    oos_design_path=$(resolve_oos_accepted_design_path "$IMPLEMENT_TMPDIR")
    if [ -s "$IMPLEMENT_TMPDIR/security-oos-observations.md" ]; then
        state_set OOS_PENDING true
        advance_phase pr-create
        exit 0
    fi
    fail_file=$(failure_capture_path pr-prep)
    _had_errexit=0
    case $- in *e*) _had_errexit=1 ;; esac
    set +e
    run_oos_disposition_gate_if_required_before_oos_pending_false
    gate_rc=$?
    (( _had_errexit )) && set -e
    if [ "$gate_rc" -ne 0 ]; then
        if [ -f "$IMPLEMENT_TMPDIR/oos-disposition-gate.stderr.log" ]; then
            cp "$IMPLEMENT_TMPDIR/oos-disposition-gate.stderr.log" "$fail_file" 2>/dev/null || true
        fi
        record_failure pr-prep "oos-disposition-gate.sh" "$gate_rc" "$fail_file" Warnings
        if run_recovery_waterfall pr-prep fix "$fail_file" pr-prep-oos; then
            _had_errexit=0
            case $- in *e*) _had_errexit=1 ;; esac
            set +e
            run_oos_disposition_gate_if_required_before_oos_pending_false
            gate_rc=$?
            (( _had_errexit )) && set -e
            if [ "$gate_rc" -eq 0 ]; then
                state_set OOS_PENDING false
                advance_phase pr-create
                return 0
            fi
        fi
        exit_stall 9a1
    fi
    state_set OOS_PENDING false
    advance_phase pr-create
}

run_pr_create_phase() {
    local title out rc pr_number pr_url pr_status repo_args draft_args fail_file _merge_base final_report_output issue_num
    larch_err "→ ship-pr: opening PR"
    if [ "$(read_state OOS_PENDING)" = "true" ]; then
        larch_err "ship-pr.sh: refusing PR creation while OOS_PENDING=true"
        advance_phase pr-prep
        exit 0
    fi
    _merge_base=$(git merge-base HEAD origin/main 2>/dev/null) || _merge_base=
    if [ -n "$_merge_base" ]; then
        title=$(git log --format=%s "${_merge_base}..HEAD" 2>/dev/null | grep -v '^chore(larch-logs): flush ' | tail -1)
    else
        title=$(git log --format=%s HEAD 2>/dev/null | grep -v '^chore(larch-logs): flush ' | tail -1)
    fi
    title=${title:-"Implement requested changes"}
    issue_num=$(read_state ISSUE_NUMBER)
    [ -n "$issue_num" ] && title="Fixes #${issue_num}: ${title}"
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
    ship_pr_with_transient_retry transient_envelope_predicate_none "$fail_file" \
        "$SCRIPT_DIR/../skills/implement/scripts/write-final-report.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"
    rc=$_WTR_RC
    final_report_output=$_WTR_OUT
    if [ "$rc" -ne 0 ]; then
        record_failure pr-create "write-final-report.sh" "$rc" "$fail_file" Warnings
        if run_recovery_waterfall pr-create fix "$fail_file" write-final-pre; then
            ship_pr_with_transient_retry transient_envelope_predicate_none "$fail_file" \
                "$SCRIPT_DIR/../skills/implement/scripts/write-final-report.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"
            rc=$_WTR_RC
            final_report_output=$_WTR_OUT
        fi
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
    ship_pr_with_transient_retry transient_envelope_predicate_none "$fail_file" \
        "$SCRIPT_DIR/create-pr.sh" --title "$title" --body-file "$IMPLEMENT_TMPDIR/pr-body.md" "${draft_args[@]+"${draft_args[@]}"}" "${repo_args[@]+"${repo_args[@]}"}"
    rc=$_WTR_RC
    out=$_WTR_OUT
    if [ "$rc" -ne 0 ]; then
        record_failure pr-create "create-pr.sh" "$rc" "$fail_file" Warnings
        if run_recovery_waterfall pr-create fix "$fail_file" create-pr "$title" "$IMPLEMENT_TMPDIR/pr-body.md"; then
            ship_pr_with_transient_retry transient_envelope_predicate_none "$fail_file" \
                "$SCRIPT_DIR/create-pr.sh" --title "$title" --body-file "$IMPLEMENT_TMPDIR/pr-body.md" "${draft_args[@]+"${draft_args[@]}"}" "${repo_args[@]+"${repo_args[@]}"}"
            rc=$_WTR_RC
            out=$_WTR_OUT
        fi
    fi
    if [ "$rc" -ne 0 ]; then
        # Terminal create-pr failure (recovery waterfall did not recover) — log under
        # the default "Tool Failures" category so test-ship-pr.sh and downstream
        # operators keying off the "### Tool Failures" heading see the hard failure.
        record_failure pr-create "create-pr.sh" "$rc" "$fail_file"
        exit_stall 9b
    fi
    pr_number=$(kv_value PR_NUMBER "$out")
    pr_url=$(kv_value PR_URL "$out")
    pr_status=$(kv_value PR_STATUS "$out")
    state_set_many PR_NUMBER "$pr_number" PR_URL "$pr_url" PR_TITLE "$title"
    larch_err "→ ship-pr: PR #${pr_number} opened"
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
        if ship_pr_with_transient_retry transient_envelope_predicate_none "$fail_file" \
            gh pr edit "$pr_number" "${repo_args[@]+"${repo_args[@]}"}" --title "$title"; then
            rc=0
        else
            rc=$_WTR_RC
        fi
        [ "$rc" -eq 0 ] || record_failure pr-create "gh pr edit --title" "$rc" "$fail_file"
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
        fix-attempts-exhausted|design-flaw|escalate|all-vendors-failed|first-fixer-non-health) return 0 ;;
        *) return 1 ;;
    esac
}

# Exit-3 bails that skip AskUserQuestion / BAIL_NEEDS_USER_INPUT (orchestrator handles autonomously).
is_autonomous_exit3_bail_reason() {
    [[ "$1" == "first-fixer-non-health" ]]
}

# Last LAUNCHER_FAILURE_CLASS= line from launcher capture (stdout+stderr file); unknown/missing → health.
ship_pr_read_launcher_failure_class() {
    local log_file=$1 class=""
    [[ -f "$log_file" ]] || {
        printf 'health\n'
        return 0
    }
    class=$(awk -F= '/^LAUNCHER_FAILURE_CLASS=/ { v=$2; gsub(/\r/, "", v); last=v } END { print last }' "$log_file" 2>/dev/null || true)
    case "$class" in
        none|health|other) printf '%s\n' "$class" ;;
        *) printf 'health\n' ;;
    esac
}

# Canonical LAUNCHER_FAILURE_* token pin (tests grep): none health other auth
# quota binary-missing health-probe timeout parse refusal unknown

# Revert tier-introduced working-tree deltas against a single snapshot captured at
# run_ci_fix_vendor entry (not per-tier). Preserves paths dirty/untracked/staged
# at baseline; skips submodule gitlinks (inner state out of scope) with Warnings.
_ci_fix_rollback() {
    local phase=$1 baseline_tracked=$2 baseline_untracked=$3 baseline_staged=$4
    local tracked_now untracked_now staged_now p rb_warn

    tracked_now=$(capture_tracked_dirty_paths)
    untracked_now=$(capture_untracked_dirty_paths)
    staged_now=$(git diff --name-only --cached 2>/dev/null || true)

    rb_warn="$IMPLEMENT_TMPDIR/_ci_fix_rollback_warn_${phase}_$$.log"
    : > "$rb_warn"

    while IFS= read -r p || [[ -n "$p" ]]; do
        [[ -z "$p" ]] && continue
        if git ls-files --stage -- "$p" 2>/dev/null | grep -q '^160000 '; then
            printf 'submodule gitlink path %s skipped by _ci_fix_rollback\n' "$p" >> "$rb_warn"
            continue
        fi
        if grep -qFx -- "$p" "$baseline_tracked" 2>/dev/null; then
            continue
        fi
        git checkout -- "$p" 2>/dev/null || true
    done < <(printf '%s\n' "$tracked_now")

    while IFS= read -r p || [[ -n "$p" ]]; do
        [[ -z "$p" ]] && continue
        if grep -qFx -- "$p" "$baseline_untracked" 2>/dev/null; then
            continue
        fi
        rm -f -- "$p" 2>/dev/null || true
    done < <(printf '%s\n' "$untracked_now")

    while IFS= read -r p || [[ -n "$p" ]]; do
        [[ -z "$p" ]] && continue
        if grep -qFx -- "$p" "$baseline_staged" 2>/dev/null; then
            continue
        fi
        git restore --staged -- "$p" 2>/dev/null || true
        if ! { grep -qFx -- "$p" "$baseline_tracked" 2>/dev/null || grep -qFx -- "$p" "$baseline_untracked" 2>/dev/null; }; then
            rm -f -- "$p" 2>/dev/null || true
        fi
    done < <(printf '%s\n' "$staged_now")

    if [[ -s "$rb_warn" ]]; then
        record_failure "$phase" "_ci_fix_rollback: submodule path(s) skipped" 0 "$rb_warn" Warnings
    fi
}

rename_done_best_effort() {
    local issue repo rc fail_file
    issue=$(read_state ISSUE_NUMBER)
    repo=$(read_state REPO)
    [ -n "$issue" ] || return 0
    [ "$(read_state REPO_UNAVAILABLE)" = "false" ] || return 0
    fail_file=$(failure_capture_path postmerge)
    if [ -n "$repo" ]; then
        "$SCRIPT_DIR/tracking-issue-write.sh" rename --issue "$issue" --state "done" --repo "$repo" > "$fail_file" 2>&1
        rc=$?
    else
        "$SCRIPT_DIR/tracking-issue-write.sh" rename --issue "$issue" --state "done" > "$fail_file" 2>&1
        rc=$?
    fi
    [ "$rc" -eq 0 ] || record_failure postmerge "tracking-issue-write.sh rename" "$rc" "$fail_file"
    state_set DONE_RENAME_APPLIED true
}

_resolve_effective_failed_jobs_tsv() {
    local phase=$1 failed_jobs_tsv=${2:-}
    if [ -n "$failed_jobs_tsv" ] && [ -f "$failed_jobs_tsv" ] && grep -q '[^[:space:]]' "$failed_jobs_tsv"; then
        printf '%s' "$failed_jobs_tsv"
        return 0
    fi
    local persisted="$IMPLEMENT_TMPDIR/ci-failed-jobs-${phase}.tsv"
    if [ -f "$persisted" ] && grep -q '[^[:space:]]' "$persisted"; then
        printf '%s' "$persisted"
        return 0
    fi
    return 1
}

_commit_ci_fix_stage_paths() {
    local phase=$1 fail_label=$2
    local vendor_tracked=$3 vendor_untracked=$4 tracked=$5 untracked=$6 delta_paths_file=${7:-}
    local fail_file rc stage_paths=() stage_path

    if [[ ! -s "$tracked" && ! -s "$untracked" ]] \
        && [[ -z "$vendor_tracked" || ! -s "$vendor_tracked" ]] \
        && [[ -z "$vendor_untracked" || ! -s "$vendor_untracked" ]] \
        && [[ -z "$delta_paths_file" || ! -f "$delta_paths_file" || ! -s "$delta_paths_file" ]]; then
        return 0
    fi

    while IFS= read -r stage_path || [[ -n "$stage_path" ]]; do
        [[ -n "$stage_path" ]] || continue
        stage_paths+=("$stage_path")
    done < <(collect_ci_stage_paths "$vendor_tracked" "$vendor_untracked" "$tracked" "$untracked" "${delta_paths_file:-}")
    if [[ "${#stage_paths[@]}" -eq 0 ]]; then
        return 0
    fi
    fail_file=$(failure_capture_path "$phase")
    git add -- "${stage_paths[@]}" > "$fail_file" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        record_failure "$phase" "$fail_label" "$rc" "$fail_file" "CI Issues"
        return 1
    fi
    if ! git diff --cached --quiet 2>/dev/null; then
        fail_file=$(failure_capture_path "$phase")
        "$SCRIPT_DIR/git-commit.sh" -m "Fix CI failure" > "$fail_file" 2>&1
        rc=$?
        if [ "$rc" -ne 0 ]; then
            record_failure "$phase" "${fail_label}git-commit.sh" "$rc" "$fail_file" "CI Issues"
            return 1
        fi
    fi
    return 0
}

_run_post_rebase_verify_gates() {
    local phase=$1 checks_site=$2 failed_jobs_tsv=$3
    local tracked_dirty_paths_file=$4 untracked_dirty_paths_file=$5
    local verify_rc fail_file rc delta_paths_file stage_paths stage_path effective_tsv

    effective_tsv=$(_resolve_effective_failed_jobs_tsv "$phase" "$failed_jobs_tsv") || effective_tsv=""
    if [ -z "$effective_tsv" ] || ! grep -q '[^[:space:]]' "$effective_tsv" 2>/dev/null; then
        larch_err "⚠ ship-pr: no failed-jobs TSV; post-rebase verify uses relevant-checks only"
        verify_rc=0
        if [ -n "$checks_site" ]; then
            if ! run_checks_with_lint_fix_loop "$phase" "$checks_site"; then
                verify_rc=1
            fi
        fi
        case "$verify_rc" in
            0)
                delta_paths_file="$LAST_LINT_FIX_DELTA_PATHS_FILE"
                _commit_ci_fix_stage_paths "$phase" "git add -- post-rebase lint delta" \
                    "$tracked_dirty_paths_file" "$untracked_dirty_paths_file" \
                    "$tracked_dirty_paths_file" "$untracked_dirty_paths_file" "$delta_paths_file" \
                    || return 1
                return 0
                ;;
            *) return 1 ;;
        esac
    fi

    verify_rc=0
    _verify_failed_jobs_locally "$phase" "$effective_tsv"
    verify_rc=$?
    if [ "$verify_rc" -eq 0 ] && [ -n "$checks_site" ]; then
        if ! run_checks_with_lint_fix_loop "$phase" "$checks_site"; then
            verify_rc=1
        fi
    fi
    case "$verify_rc" in
        0)
            delta_paths_file="$LAST_LINT_FIX_DELTA_PATHS_FILE"
            _commit_ci_fix_stage_paths "$phase" "git add -- post-rebase lint delta" \
                "$tracked_dirty_paths_file" "$untracked_dirty_paths_file" \
                "$tracked_dirty_paths_file" "$untracked_dirty_paths_file" "$delta_paths_file" \
                || return 1
            return 0
            ;;
        2) return 2 ;;
        4) return 4 ;;
        *) return 1 ;;
    esac
}

_stage_and_push_ci_fixes() {
    local phase=$1 token_record_input=${2:-} checks_site=${3:-} failed_jobs_tsv=${4:-}
    local rc fail_file vendor_tracked_dirty_paths_file vendor_untracked_dirty_paths_file
    local tracked_dirty_paths_file untracked_dirty_paths_file delta_paths_file
    local base_remote base_ref behind_out behind did_rebase verify_rc pending_retry verify_passed=false

    LAST_STAGE_AND_PUSH_PRE_REFRESH_HEAD=""
    pending_retry=false
    if [ "$CI_FIX_REBASE_PENDING" = true ]; then
        pending_retry=true
    fi

    tracked_dirty_paths_file="$IMPLEMENT_TMPDIR/${phase}-post-success-tracked-dirty-paths.txt"
    untracked_dirty_paths_file="$IMPLEMENT_TMPDIR/${phase}-post-success-untracked-dirty-paths.txt"

    if [ "$pending_retry" != true ]; then
        fail_file=$(failure_capture_path "$phase")
        "$SCRIPT_DIR/append-token-record.sh" --input "$token_record_input" --tmpdir "$IMPLEMENT_TMPDIR" > "$fail_file" 2>&1
        rc=$?
        [ "$rc" -eq 0 ] || record_failure "$phase" "append-token-record.sh" "$rc" "$fail_file" Warnings

        vendor_tracked_dirty_paths_file="$IMPLEMENT_TMPDIR/${phase}-vendor-tracked-dirty-paths.txt"
        vendor_untracked_dirty_paths_file="$IMPLEMENT_TMPDIR/${phase}-vendor-untracked-dirty-paths.txt"
        capture_tracked_dirty_paths > "$vendor_tracked_dirty_paths_file"
        capture_untracked_dirty_paths > "$vendor_untracked_dirty_paths_file"

        if [[ -n "$checks_site" ]]; then
            if ! run_checks_with_lint_fix_loop "$phase" "$checks_site"; then
                return 1
            fi
        fi

        capture_tracked_dirty_paths > "$tracked_dirty_paths_file"
        capture_untracked_dirty_paths > "$untracked_dirty_paths_file"
        delta_paths_file="$LAST_LINT_FIX_DELTA_PATHS_FILE"
        _commit_ci_fix_stage_paths "$phase" "git add -- <tracked+allowlisted-untracked>" \
            "$vendor_tracked_dirty_paths_file" "$vendor_untracked_dirty_paths_file" \
            "$tracked_dirty_paths_file" "$untracked_dirty_paths_file" "$delta_paths_file" \
            || return 1
    else
        capture_tracked_dirty_paths > "$tracked_dirty_paths_file"
        capture_untracked_dirty_paths > "$untracked_dirty_paths_file"
    fi
    LAST_STAGE_AND_PUSH_PRE_REFRESH_HEAD=$(git rev-parse HEAD 2>/dev/null || echo unknown)

    if [ "$(read_state FORKED_TARGET)" = "true" ]; then
        base_remote=upstream
        base_ref=main
    else
        base_remote=origin
        base_ref=main
    fi
    did_rebase=false
    if [ "$pending_retry" != true ]; then
        fail_file=$(failure_capture_path "$phase")
        behind_out=$("$SCRIPT_DIR/ci-behind-count.sh" --base-remote "$base_remote" --base-ref "$base_ref" 2>"$fail_file")
        behind=$(kv_value BEHIND_COUNT "$behind_out")
        case "$behind" in
            ''|*[!0-9]*) behind=0 ;;
        esac
        if [ "$behind" -gt 0 ]; then
            local effective_tsv_for_rebase
            effective_tsv_for_rebase=$(_resolve_effective_failed_jobs_tsv "$phase" "$failed_jobs_tsv") || effective_tsv_for_rebase=""
            if [ -z "$effective_tsv_for_rebase" ] || ! grep -q '[^[:space:]]' "$effective_tsv_for_rebase" 2>/dev/null; then
                larch_err "⚠ ship-pr: behind main but failed-jobs unknown; skipping defer-rebase"
            else
                did_rebase=true
                run_rebase_rebump "$phase" defer-push "$base_remote" "$base_ref"
                LAST_STAGE_AND_PUSH_PRE_REFRESH_HEAD=$(git rev-parse HEAD 2>/dev/null || echo unknown)
                capture_tracked_dirty_paths > "$tracked_dirty_paths_file"
                capture_untracked_dirty_paths > "$untracked_dirty_paths_file"
            fi
        fi
    fi

    if [ "$did_rebase" = true ] || [ "$pending_retry" = true ]; then
        _run_post_rebase_verify_gates "$phase" "$checks_site" "$failed_jobs_tsv" \
            "$tracked_dirty_paths_file" "$untracked_dirty_paths_file"
        verify_rc=$?
        case "$verify_rc" in
            0) verify_passed=true ;;
            2|4) return "$verify_rc" ;;
            *) return 1 ;;
        esac
    fi

    fail_file=$(failure_capture_path "$phase")
    "$SCRIPT_DIR/refresh-run-logs.sh" \
        --state-file "$STATE_FILE" \
        --implement-tmpdir "$IMPLEMENT_TMPDIR" > "$fail_file" 2>&1 || true

    fail_file=$(failure_capture_path "$phase")
    if [ "$did_rebase" = true ] || [ "$CI_FIX_REBASE_PENDING" = true ]; then
        "$SCRIPT_DIR/git-force-push.sh" > "$fail_file" 2>&1
    else
        "$SCRIPT_DIR/git-push.sh" > "$fail_file" 2>&1
    fi
    rc=$?
    if [ "$rc" -ne 0 ]; then
        if [ "$verify_passed" = true ]; then
            _ci_fix_pending_set
            record_failure "$phase" "git-force-push.sh" "$rc" "$fail_file" "CI Issues"
        elif [ "$did_rebase" = true ] || [ "$CI_FIX_REBASE_PENDING" = true ]; then
            record_failure "$phase" "git-force-push.sh" "$rc" "$fail_file" "CI Issues"
        else
            record_failure "$phase" "git-push.sh" "$rc" "$fail_file" "CI Issues"
        fi
        return 1
    fi
    _ci_fix_pending_clear
}

run_ci_fix_vendor() {
    local phase=$1 run_id=$2 gh_logs_capture=${3:-} gh_logs_rc=${4:-1} failed_jobs_tsv=${5:-} start_attempt=${6:-0}
    local rc fail_file tool_label plan_file checks_site delta_paths_file verify_rc stage_rc
    local plan_args=() vendor_tracked_dirty_paths_file vendor_untracked_dirty_paths_file tracked_dirty_paths_file untracked_dirty_paths_file
    local gh_logs_capture_redacted _failure_log_args=()
    local ci_fix_out_base tier_out wrapper_rc launcher_exit winning_tier launcher
    local baseline_tracked_file baseline_untracked_file baseline_staged_file baseline_head
    local detail_log pre_refresh_head
    local tiers=(codex cursor claude) tier tier_idx offset waterfall_iter=0 first_tier

    larch_err "⚠ ship-pr: CI failed; dispatching fix"

    baseline_tracked_file="$IMPLEMENT_TMPDIR/ci-fix-baseline-${phase}-$$-tracked.txt"
    baseline_untracked_file="$IMPLEMENT_TMPDIR/ci-fix-baseline-${phase}-$$-untracked.txt"
    baseline_staged_file="$IMPLEMENT_TMPDIR/ci-fix-baseline-${phase}-$$-staged.txt"
    capture_tracked_dirty_paths > "$baseline_tracked_file"
    capture_untracked_dirty_paths > "$baseline_untracked_file"
    { git diff --name-only --cached 2>/dev/null || true; } > "$baseline_staged_file"
    baseline_head=$(git rev-parse HEAD 2>/dev/null || echo unknown)

    gh_logs_capture_redacted=""
    if [ "$gh_logs_rc" -eq 0 ] && [ -n "$gh_logs_capture" ] && [ -s "$gh_logs_capture" ]; then
        gh_logs_capture_redacted="${gh_logs_capture}.redacted"
        if ! "$SCRIPT_DIR/redact-secrets.sh" < "$gh_logs_capture" > "$gh_logs_capture_redacted" 2>/dev/null; then
            gh_logs_capture_redacted=""
        fi
    fi

    plan_file=$(resolve_plan_file)
    if [ -n "$plan_file" ]; then
        plan_args=(--plan-file "$plan_file")
    fi

    ci_fix_out_base="$IMPLEMENT_TMPDIR/ci-fix-${phase}-$(date +%s)"
    winning_tier=""
    wrapper_rc=1
    launcher_exit=1

    offset=$(( start_attempt % 3 ))
    first_tier=${tiers[$offset]}
    for tier_idx in 0 1 2; do
        tier=${tiers[$(((tier_idx + offset) % 3))]}
        if [ "$tier" = "claude" ] && [ ! -x "$SCRIPT_DIR/launch-claude-ci.sh" ]; then
            fail_file=$(failure_capture_path "$phase")
            printf 'launch-claude-ci.sh unavailable (missing or not executable)\n' > "$fail_file"
            record_failure "$phase" "launch-claude-ci.sh unavailable" 1 "$fail_file" Warnings
            waterfall_iter=$(( waterfall_iter + 1 ))
            continue
        fi
        case "$tier" in
            cursor) launcher="$SCRIPT_DIR/launch-cursor-ci.sh" ;;
            codex) launcher="$SCRIPT_DIR/launch-codex-ci.sh" ;;
            claude) launcher="$SCRIPT_DIR/launch-claude-ci.sh" ;;
        esac

        tier_out="${ci_fix_out_base}.${tier}"
        fail_file=$(failure_capture_path "$phase")
        _failure_log_args=()
        if [ "$gh_logs_rc" -eq 0 ] && [ -n "$gh_logs_capture_redacted" ] && [ -s "$gh_logs_capture_redacted" ]; then
            _failure_log_args=(--failure-log "$gh_logs_capture_redacted")
        fi

        "$launcher" --role fix --output "$tier_out" --run-id "$run_id" \
            --repo "$(read_state REPO)" ${plan_args[@]+"${plan_args[@]}"} \
            ${_failure_log_args[@]+"${_failure_log_args[@]}"} --timeout 1800 > "$fail_file" 2>&1
        wrapper_rc=$?
        launcher_exit=$(awk -F= '/^LAUNCHER_EXIT=/ {print $2; exit}' "$fail_file")
        launcher_exit="${launcher_exit:-0}"

        if [ "$wrapper_rc" -eq 2 ]; then
            _surface_ci_stderr_tail "$tier_out"
            record_failure "$phase" "$(basename "$launcher") fix (validation)" "$wrapper_rc" "$fail_file" "CI Issues"
            _ci_fix_rollback "$phase" "$baseline_tracked_file" "$baseline_untracked_file" "$baseline_staged_file"
            waterfall_iter=$(( waterfall_iter + 1 ))
            continue
        fi
        if [ "$wrapper_rc" -eq 0 ] && [ "${launcher_exit:-0}" -eq 0 ]; then
            tool_label="$(basename "$launcher") fix"
            winning_tier=$tier
            break
        fi
        _surface_ci_stderr_tail "$tier_out"
        record_failure "$phase" "$(basename "$launcher") fix (wrapper_rc=$wrapper_rc, launcher_exit=${launcher_exit:-0})" "${launcher_exit:-$wrapper_rc}" "$fail_file" "CI Issues"
        _ci_fix_rollback "$phase" "$baseline_tracked_file" "$baseline_untracked_file" "$baseline_staged_file"
        if [ "$waterfall_iter" -eq 0 ] && [ "$wrapper_rc" -eq 0 ] && [ "$tier" = "$first_tier" ]; then
            local _lf_class
            _lf_class=$(ship_pr_read_launcher_failure_class "$fail_file")
            if [ "$_lf_class" = "other" ]; then
                larch_err "⚠ ship-pr: first fixer failed non-health; skipping waterfall"
                state_set_many BAIL_REASON first-fixer-non-health BAIL_FAILURE_DETAIL_LOG "$fail_file"
                return 1
            fi
        fi
        waterfall_iter=$(( waterfall_iter + 1 ))
    done

    if [ -z "$winning_tier" ] || [ "$wrapper_rc" -ne 0 ] || [ "${launcher_exit:-0}" -ne 0 ]; then
        return 1
    fi

    checks_site="$([ "$phase" = "ci-initial" ] && echo step10 || echo step12c)"
    _verify_failed_jobs_locally "$phase" "$failed_jobs_tsv"
    verify_rc=$?
    case "$verify_rc" in
        0) ;;
        2) return 2 ;;
        4) return 4 ;;
        *) return 1 ;;
    esac
    _stage_and_push_ci_fixes "$phase" "${ci_fix_out_base}.${winning_tier}.token-record" "$checks_site" "$failed_jobs_tsv"
    stage_rc=$?
    case "$stage_rc" in
        0)
            pre_refresh_head=${LAST_STAGE_AND_PUSH_PRE_REFRESH_HEAD:-}
            if [[ "$baseline_head" =~ ^[0-9a-f]{40}$ ]] \
                && [[ "$pre_refresh_head" =~ ^[0-9a-f]{40}$ ]] \
                && [ "$baseline_head" = "$pre_refresh_head" ]; then
                detail_log="$IMPLEMENT_TMPDIR/ci-fix-no-commit-${phase}-$$.log"
                {
                    printf 'vendor=%s\n' "$winning_tier"
                    printf 'launcher_exit=0\n'
                    printf 'baseline_head=%s\n' "$baseline_head"
                    printf 'pre_refresh_head=%s\n' "$pre_refresh_head"
                    printf 'reason=vendor exited 0 and CI-fix staging/push left HEAD unchanged; classifying as first-fixer-non-health to route to autonomous main-agent CI-fix\n'
                } > "$detail_log"
                larch_err "⚠ ship-pr: vendor exit 0 with no commits; escalating to first-fixer-non-health"
                state_set_many BAIL_REASON first-fixer-non-health BAIL_FAILURE_DETAIL_LOG "$detail_log"
                _ffnh_tier_stem="${ci_fix_out_base}.${winning_tier}"
                if [[ ! -s "${_ffnh_tier_stem}.stderr-tail" ]]; then
                    if [[ -s "${_ffnh_tier_stem}.diag" ]]; then
                        write_failed_agent_stderr_tail "${_ffnh_tier_stem}.diag" "$_ffnh_tier_stem" || true
                    fi
                fi
                _surface_ci_stderr_tail "$_ffnh_tier_stem"
                record_failure "$phase" "vendor exit 0 with no commits ($winning_tier)" 1 "$detail_log" "CI Issues"
                return 1
            fi
            return 0
            ;;
        2) return 2 ;;
        4) return 4 ;;
        *) return 1 ;;
    esac
}

_PJA_ARGV=()
_PJL_LOG_PATH=""
_PJL_JOB_TOKEN=""

_per_job_argv() {
    local job_name=$1 shard=${2:-}
    _PJA_ARGV=()
    case "$job_name" in
        lint)
            _PJA_ARGV=(env "SKIP=agnix,lint-mermaid-fences,shellcheck" make lint-only)
            ;;
        lint-mermaid)
            _PJA_ARGV=(make lint-mermaid)
            ;;
        shellcheck)
            _PJA_ARGV=(make shellcheck)
            ;;
        test-harnesses)
            if [[ "$shard" =~ ^[0-9]+$ ]]; then
                _PJA_ARGV=(make "test-harnesses-${shard}")
            else
                _PJA_ARGV=(make test-harnesses)
            fi
            ;;
        agent-lint)
            _PJA_ARGV=(make agent-lint)
            ;;
        agnix)
            _PJA_ARGV=(make agnix)
            ;;
        smoke-dialectic)
            _PJA_ARGV=(make smoke-dialectic)
            ;;
        agent-sync)
            _PJA_ARGV=(make agent-sync)
            ;;
        python-lint)
            _PJA_ARGV=(make py-lint)
            ;;
        python-tests)
            _PJA_ARGV=(make py-test)
            ;;
        *)
            return 1
            ;;
    esac
}

_prepare_python_job_toolchain() {
    local job_name=$1 req_file="" missing="" tool=""
    case "$job_name" in
        python-lint)
            req_file="$PLUGIN_ROOT/python/requirements-dev.txt"
            if [ -f "$req_file" ] && command -v python3 >/dev/null 2>&1; then
                python3 -m pip install -q -r "$req_file" 2>/dev/null || true
            fi
            for tool in ruff pylint pyright; do
                if ! command -v "$tool" >/dev/null 2>&1; then
                    missing="${missing}${missing:+ }$tool"
                fi
            done
            if [ -n "$missing" ]; then
                larch_err "⚠ ship-pr: python-lint replay skipped — missing tools on PATH ($missing); install python/requirements-dev.txt (and Node for pyright) or rely on vendor fixer"
                return 1
            fi
            if ! command -v node >/dev/null 2>&1; then
                larch_err "⚠ ship-pr: python-lint replay may fail — node not on PATH (pyright requires Node)"
            fi
            ;;
        python-tests)
            req_file="$PLUGIN_ROOT/python/requirements-test.txt"
            if [ -f "$req_file" ] && command -v python3 >/dev/null 2>&1; then
                python3 -m pip install -q -r "$req_file" 2>/dev/null || true
            fi
            if ! command -v pytest >/dev/null 2>&1; then
                larch_err "⚠ ship-pr: python-tests replay skipped — pytest not on PATH; install python/requirements-test.txt or rely on vendor fixer"
                return 1
            fi
            ;;
        *) return 0 ;;
    esac
}

_write_per_job_args_file() {
    local path=$1 token
    : > "$path"
    for token in "${_PJA_ARGV[@]}"; do
        printf '%s\n' "$token" >> "$path"
    done
}

_run_per_job_command_capture() {
    larch_err "⚠ ship-pr: running local CI job ${_PJL_JOB_TOKEN:-unknown}"
    _RCC_RAW_LOG_PATH="$_PJL_LOG_PATH"
    _RCC_CMD_RC=0
    "${_PJA_ARGV[@]}" > "$_RCC_RAW_LOG_PATH" 2>&1 || _RCC_CMD_RC=$?
}

_run_per_job_command_once() {
    local log_path=$1 _once_rc=0
    larch_err "⚠ ship-pr: verifying local CI job ${_PJL_JOB_TOKEN:-unknown}"
    "${_PJA_ARGV[@]}" > "$log_path" 2>&1 || _once_rc=$?
    return "$_once_rc"
}

_sanitize_bail_list() {
    tr -cd '[:alnum:]_,-'
}

_verify_failed_jobs_locally() {
    local phase=$1 failed_jobs_tsv=${2:-}
    local job_name shard class job_token args_file verify_log detail_file tsv_line
    local fixable_jobs=() fixable_shards=() phase_a_ok_jobs=() phase_a_ok_shards=() unfixable=()
    local i sanitized

    if [ -z "$failed_jobs_tsv" ] || [ ! -f "$failed_jobs_tsv" ] || ! grep -q '[^[:space:]]' "$failed_jobs_tsv"; then
        larch_err "⚠ ship-pr: no failed-jobs TSV; skipping per-job verification (falling back to relevant-checks.sh only)"
        return 0
    fi

    ALL_LINT_FIX_DELTA_PATHS_FILE="$IMPLEMENT_TMPDIR/${phase}-vendor-verify-lint-fix-delta-paths.txt"
    LAST_LINT_FIX_DELTA_PATHS_FILE=""
    : > "$ALL_LINT_FIX_DELTA_PATHS_FILE"

    while IFS= read -r tsv_line || [[ -n "$tsv_line" ]]; do
        job_name=$(printf '%s\n' "$tsv_line" | awk -F '\t' '{print $1}')
        shard=$(printf '%s\n' "$tsv_line" | awk -F '\t' '{print $2}')
        class=$(printf '%s\n' "$tsv_line" | awk -F '\t' '{print $3}')
        [[ -n "$job_name" ]] || continue
        job_token=$job_name
        [[ -n "$shard" ]] && job_token="${job_token}-${shard}"
        case "$class" in
            fixable)
                if _per_job_argv "$job_name" "$shard"; then
                    fixable_jobs+=("$job_name")
                    fixable_shards+=("$shard")
                else
                    unfixable+=("$job_token")
                fi
                ;;
            *)
                unfixable+=("$job_token")
                ;;
        esac
    done < "$failed_jobs_tsv"

    for i in "${!fixable_jobs[@]}"; do
        job_name=${fixable_jobs[$i]}
        shard=${fixable_shards[$i]}
        job_token=$job_name
        [[ -n "$shard" ]] && job_token="${job_token}-${shard}"
        _per_job_argv "$job_name" "$shard" || { unfixable+=("$job_token"); continue; }
        _prepare_python_job_toolchain "$job_name" || { unfixable+=("$job_token"); continue; }
        args_file="$IMPLEMENT_TMPDIR/per-job-${phase}-${job_token}-args.txt"
        _write_per_job_args_file "$args_file"
        _PJL_LOG_PATH="$IMPLEMENT_TMPDIR/per-job-${phase}-${job_token}.verify.log"
        _PJL_JOB_TOKEN="$job_token"
        _RCC_PHASE="$phase"
        _RCC_RERUN_FN=_run_per_job_command_capture
        _RCC_SITE=ship-pr-ci-per-job
        _RCC_TARGET_CMD_ARGS_FILE="$args_file"
        _RCC_MAX_ITER=$(normalize_rcc_max_iter "${LARCH_CI_LOCAL_FIX_ITER:-6}")
        verify_log="$IMPLEMENT_TMPDIR/per-job-${phase}-${job_token}-verify.log"
        if _run_per_job_command_once "$verify_log"; then
            phase_a_ok_jobs+=("$job_name")
            phase_a_ok_shards+=("$shard")
            continue
        fi
        run_captured_cmd_then_fix_loop
        case "$_RCC_STATUS" in
            ok)
                append_unique_paths_file "$ALL_LINT_FIX_DELTA_PATHS_FILE" "$_RCC_DELTA_PATHS_FILE"
                phase_a_ok_jobs+=("$job_name")
                phase_a_ok_shards+=("$shard")
                ;;
            head-changed)
                return 2
                ;;
            main-agent-required|dispatch-failed|exhausted|no-changes-stale)
                unfixable+=("$job_token")
                ;;
            *)
                unfixable+=("$job_token")
                ;;
        esac
    done

    for i in "${!phase_a_ok_jobs[@]}"; do
        job_name=${phase_a_ok_jobs[$i]}
        shard=${phase_a_ok_shards[$i]}
        job_token=$job_name
        [[ -n "$shard" ]] && job_token="${job_token}-${shard}"
        _per_job_argv "$job_name" "$shard" || { unfixable+=("$job_token"); continue; }
        _PJL_JOB_TOKEN="$job_token"
        verify_log="$IMPLEMENT_TMPDIR/per-job-${phase}-${job_token}-verify.log"
        if ! _run_per_job_command_once "$verify_log"; then
            return 4
        fi
    done

    if [[ -s "$ALL_LINT_FIX_DELTA_PATHS_FILE" ]]; then
        LAST_LINT_FIX_DELTA_PATHS_FILE="$ALL_LINT_FIX_DELTA_PATHS_FILE"
    fi

    if [[ "${#unfixable[@]}" -gt 0 ]]; then
        detail_file="$IMPLEMENT_TMPDIR/ci-local-unfixable-${phase}-verify.txt"
        : > "$detail_file"
        for job_token in "${unfixable[@]}"; do
            sanitized=$(printf '%s\n' "$job_token" | _sanitize_bail_list)
            [ -n "$sanitized" ] || sanitized=unknown
            printf '%s\n' "$sanitized" >> "$detail_file"
        done
        sanitized=$(printf '%s\n' "${unfixable[@]}" | paste -sd, - | _sanitize_bail_list)
        state_set_many BAIL_REASON "ci-local-unfixable:${sanitized}" BAIL_FAILURE_DETAIL_LOG "$detail_file"
        exit 3
    fi

    return 0
}

run_per_job_local_fix_loop() {
    local phase=$1 failed_jobs_tsv=$2
    local job_name shard class job_token args_file verify_log detail_file tsv_line
    local fixable_jobs=() fixable_shards=() phase_a_ok_jobs=() phase_a_ok_shards=() unfixable=()
    local i sanitized

    ALL_LINT_FIX_DELTA_PATHS_FILE="$IMPLEMENT_TMPDIR/${phase}-per-job-lint-fix-delta-paths.txt"
    LAST_LINT_FIX_DELTA_PATHS_FILE=""
    : > "$ALL_LINT_FIX_DELTA_PATHS_FILE"

    while IFS= read -r tsv_line || [[ -n "$tsv_line" ]]; do
        job_name=$(printf '%s\n' "$tsv_line" | awk -F '\t' '{print $1}')
        shard=$(printf '%s\n' "$tsv_line" | awk -F '\t' '{print $2}')
        class=$(printf '%s\n' "$tsv_line" | awk -F '\t' '{print $3}')
        [[ -n "$job_name" ]] || continue
        job_token=$job_name
        [[ -n "$shard" ]] && job_token="${job_token}-${shard}"
        case "$class" in
            fixable)
                if _per_job_argv "$job_name" "$shard"; then
                    fixable_jobs+=("$job_name")
                    fixable_shards+=("$shard")
                else
                    unfixable+=("$job_token")
                fi
                ;;
            *)
                unfixable+=("$job_token")
                ;;
        esac
    done < "$failed_jobs_tsv"

    for i in "${!fixable_jobs[@]}"; do
        job_name=${fixable_jobs[$i]}
        shard=${fixable_shards[$i]}
        job_token=$job_name
        [[ -n "$shard" ]] && job_token="${job_token}-${shard}"
        _per_job_argv "$job_name" "$shard" || { unfixable+=("$job_token"); continue; }
        _prepare_python_job_toolchain "$job_name" || { unfixable+=("$job_token"); continue; }
        args_file="$IMPLEMENT_TMPDIR/per-job-${phase}-${job_token}-args.txt"
        _write_per_job_args_file "$args_file"
        _PJL_LOG_PATH="$IMPLEMENT_TMPDIR/per-job-${phase}-${job_token}.log"
        _PJL_JOB_TOKEN="$job_token"
        _RCC_PHASE="$phase"
        _RCC_RERUN_FN=_run_per_job_command_capture
        _RCC_SITE=ship-pr-ci-per-job
        _RCC_TARGET_CMD_ARGS_FILE="$args_file"
        _RCC_MAX_ITER=$(normalize_rcc_max_iter "${LARCH_CI_LOCAL_FIX_ITER:-6}")
        run_captured_cmd_then_fix_loop
        case "$_RCC_STATUS" in
            ok)
                append_unique_paths_file "$ALL_LINT_FIX_DELTA_PATHS_FILE" "$_RCC_DELTA_PATHS_FILE"
                phase_a_ok_jobs+=("$job_name")
                phase_a_ok_shards+=("$shard")
                ;;
            head-changed)
                return 2
                ;;
            main-agent-required|dispatch-failed|exhausted)
                return 1
                ;;
            *)
                return 1
                ;;
        esac
    done

    for i in "${!phase_a_ok_jobs[@]}"; do
        job_name=${phase_a_ok_jobs[$i]}
        shard=${phase_a_ok_shards[$i]}
        job_token=$job_name
        [[ -n "$shard" ]] && job_token="${job_token}-${shard}"
        _per_job_argv "$job_name" "$shard" || { unfixable+=("$job_token"); continue; }
        _PJL_JOB_TOKEN="$job_token"
        verify_log="$IMPLEMENT_TMPDIR/per-job-${phase}-${job_token}-verify.log"
        if ! _run_per_job_command_once "$verify_log"; then
            return 4
        fi
    done

    if [[ -s "$ALL_LINT_FIX_DELTA_PATHS_FILE" ]]; then
        LAST_LINT_FIX_DELTA_PATHS_FILE="$ALL_LINT_FIX_DELTA_PATHS_FILE"
    fi

    if [[ "${#unfixable[@]}" -gt 0 ]]; then
        detail_file="$IMPLEMENT_TMPDIR/ci-local-unfixable-${phase}.txt"
        : > "$detail_file"
        for job_token in "${unfixable[@]}"; do
            sanitized=$(printf '%s\n' "$job_token" | _sanitize_bail_list)
            [ -n "$sanitized" ] || sanitized=unknown
            printf '%s\n' "$sanitized" >> "$detail_file"
        done
        sanitized=$(printf '%s\n' "${unfixable[@]}" | paste -sd, - | _sanitize_bail_list)
        state_set_many BAIL_REASON "ci-local-unfixable:${sanitized}" BAIL_FAILURE_DETAIL_LOG "$detail_file"
        exit 3
    fi
    return 0
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
    # Retry loop with cap, detached-HEAD check, and jittered backoff. This caps
    # each run_evaluate_failure invocation at 3 outer attempts (each attempt runs
    # a 3-tier inner waterfall: Codex → Cursor → Claude = up to 9 launcher calls
    # per phase, down from 15 today); the persisted FIX_ATTEMPTS counter still
    # tracks successful fix pushes across the wider phase for reporting/state purposes.
    local _max_fix=3 _fix_attempt gh_logs_capture gh_logs_rc ci_failed_out ci_failed_rc ci_failed_count ci_failed_capture ci_failed_tsv checks_site per_job_rc per_job_verification_retry vendor_rc stage_rc
    _fix_attempt=0
    while [ "$_fix_attempt" -lt "$_max_fix" ]; do
        vendor_rc=
        state_set_many BAIL_REASON "" BAIL_FAILURE_DETAIL_LOG ""
        # Detached-HEAD guard before each vendor+push attempt.
        if ! git symbolic-ref --quiet HEAD >/dev/null 2>&1; then
            fail_file=$(failure_capture_path "$phase")
            printf 'run_evaluate_failure: not on a named branch (detached HEAD)\n' > "$fail_file"
            record_failure "$phase" "evaluate-failure detached-head" 1 "$fail_file" "CI Issues"
            exit_stall "$([ "$phase" = "ci-initial" ] && echo 10-detached-head || echo 12-detached-head)"
        fi
        fail_file=$(failure_capture_path "$phase")
        "$SCRIPT_DIR/gh-run-logs.sh" --run-id "$failed_run" --repo "$(read_state REPO)" > "$fail_file" 2>&1
        gh_logs_rc=$?
        [ "$gh_logs_rc" -eq 0 ] || [ "$gh_logs_rc" -eq 3 ] || record_failure "$phase" "gh-run-logs.sh" "$gh_logs_rc" "$fail_file" "CI Issues"
        gh_logs_capture="$fail_file"
        fail_file=""
        ci_failed_tsv="$IMPLEMENT_TMPDIR/ci-failed-jobs-${phase}.tsv"
        checks_site="$([ "$phase" = "ci-initial" ] && echo step10 || echo step12c)"
        if [ "$CI_FIX_REBASE_PENDING" = true ]; then
            _stage_and_push_ci_fixes "$phase" "" "$checks_site" "$ci_failed_tsv"
            stage_rc=$?
            case "$stage_rc" in
                0)
                    state_set_many TRANSIENT_RETRIES 0 FIX_ATTEMPTS "$(( $(read_state FIX_ATTEMPTS) + 1 ))"
                    return 0
                    ;;
                2)
                    exit_stall "$([ "$phase" = "ci-initial" ] && echo 10-head-changed || echo 12-head-changed)"
                    ;;
                4)
                    per_job_verification_retry=true
                    ;;
            esac
            _fix_attempt=$(( _fix_attempt + 1 ))
            if [ "$_fix_attempt" -lt "$_max_fix" ]; then
                local _base _jitter _sleep
                _base=$(( 2 * 2 ** (_fix_attempt - 1) ))
                _jitter=$(( RANDOM % (_base / 2 + 1) ))
                _sleep=$(( _base + _jitter - _base / 4 ))
                [ "$_sleep" -lt 1 ] && _sleep=1
                sleep "$_sleep"
                continue
            fi
            break
        fi
        if [ "$gh_logs_rc" -eq 3 ]; then
            printf 'ship-pr %s: CI still in progress (gh-run-logs rc=3); deferring vendor dispatch this attempt.\n' "$phase"
        elif [ "$gh_logs_rc" -eq 0 ]; then
            per_job_verification_retry=false
            ci_failed_capture="$IMPLEMENT_TMPDIR/ci-failed-jobs-${phase}.out"
            ci_failed_tsv="$IMPLEMENT_TMPDIR/ci-failed-jobs-${phase}.tsv"
            ci_failed_out=$("$SCRIPT_DIR/ci-failed-jobs.sh" --run-id "$failed_run" --repo "$(read_state REPO)" --output-tsv "$ci_failed_tsv" 2>"$ci_failed_capture")
            ci_failed_rc=$?
            printf '%s\n' "$ci_failed_out" >> "$ci_failed_capture"
            if [ "$ci_failed_rc" -eq 0 ]; then
                ci_failed_count=$(kv_value FAILED_JOBS_COUNT "$ci_failed_out")
                case "$ci_failed_count" in ''|*[!0-9]*) ci_failed_count=0 ;; esac
                if [ "$ci_failed_count" -gt 0 ] && [ -s "$ci_failed_tsv" ]; then
                    checks_site="$([ "$phase" = "ci-initial" ] && echo step10 || echo step12c)"
                    run_per_job_local_fix_loop "$phase" "$ci_failed_tsv"
                    per_job_rc=$?
                    if [ "$per_job_rc" -eq 0 ]; then
                        _stage_and_push_ci_fixes "$phase" "" "$checks_site" "$ci_failed_tsv"
                        per_job_rc=$?
                        case "$per_job_rc" in
                            0)
                                state_set_many TRANSIENT_RETRIES 0 FIX_ATTEMPTS "$(( $(read_state FIX_ATTEMPTS) + 1 ))"
                                return 0
                                ;;
                            2)
                                exit_stall "$([ "$phase" = "ci-initial" ] && echo 10-head-changed || echo 12-head-changed)"
                                ;;
                            4)
                                per_job_verification_retry=true
                                ;;
                        esac
                        _fix_attempt=$(( _fix_attempt + 1 ))
                        if [ "$_fix_attempt" -lt "$_max_fix" ]; then
                            local _base _jitter _sleep
                            _base=$(( 2 * 2 ** (_fix_attempt - 1) ))
                            _jitter=$(( RANDOM % (_base / 2 + 1) ))
                            _sleep=$(( _base + _jitter - _base / 4 ))
                            [ "$_sleep" -lt 1 ] && _sleep=1
                            sleep "$_sleep"
                            continue
                        fi
                        break
                    fi
                    case "$per_job_rc" in
                        2)
                            exit_stall "$([ "$phase" = "ci-initial" ] && echo 10-head-changed || echo 12-head-changed)"
                            ;;
                        4)
                            per_job_verification_retry=true
                            ;;
                    esac
                fi
            else
                record_failure "$phase" "ci-failed-jobs.sh" "$ci_failed_rc" "$ci_failed_capture" Warnings
            fi
            if [[ "$per_job_verification_retry" == true ]]; then
                _stage_and_push_ci_fixes "$phase" "" "$checks_site" "$ci_failed_tsv"
                stage_rc=$?
                case "$stage_rc" in
                    0)
                        state_set_many TRANSIENT_RETRIES 0 FIX_ATTEMPTS "$(( $(read_state FIX_ATTEMPTS) + 1 ))"
                        return 0
                        ;;
                    2)
                        exit_stall "$([ "$phase" = "ci-initial" ] && echo 10-head-changed || echo 12-head-changed)"
                        ;;
                    4)
                        per_job_verification_retry=true
                        ;;
                esac
            else
                if run_ci_fix_vendor "$phase" "$failed_run" "$gh_logs_capture" "$gh_logs_rc" "$ci_failed_tsv" "$_fix_attempt"; then
                    vendor_rc=0
                else
                    vendor_rc=$?
                fi
                case "$vendor_rc" in
                    0)
                        state_set_many TRANSIENT_RETRIES 0 FIX_ATTEMPTS "$(( $(read_state FIX_ATTEMPTS) + 1 ))"
                        return 0
                        ;;
                    2)
                        exit_stall "$([ "$phase" = "ci-initial" ] && echo 10-head-changed || echo 12-head-changed)"
                        ;;
                    4)
                        per_job_verification_retry=true
                        ;;
                    *)
                        ;;
                esac
            fi
        else
            if run_ci_fix_vendor "$phase" "$failed_run" "$gh_logs_capture" "$gh_logs_rc" "" "$_fix_attempt"; then
                vendor_rc=0
            else
                vendor_rc=$?
            fi
            case "$vendor_rc" in
                0)
                    state_set_many TRANSIENT_RETRIES 0 FIX_ATTEMPTS "$(( $(read_state FIX_ATTEMPTS) + 1 ))"
                    return 0
                    ;;
                2)
                    exit_stall "$([ "$phase" = "ci-initial" ] && echo 10-head-changed || echo 12-head-changed)"
                    ;;
                4)
                    per_job_verification_retry=true
                    ;;
                *)
                    ;;
            esac
        fi
        if [ "$(read_state BAIL_REASON)" = "first-fixer-non-health" ]; then
            exit 3
        fi
        _fix_attempt=$(( _fix_attempt + 1 ))
        if [ "$_fix_attempt" -lt "$_max_fix" ]; then
            # Jittered backoff: 2s/4s ±25% (8s/16s ladder entries reserved for higher _max_fix values; unused at _max_fix=3)
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

transient_envelope_predicate_merge_pr() {
    local out=$1
    local mr err
    mr=$(printf '%s\n' "$out" | awk -F= '/^MERGE_RESULT=/ { print $2; exit }')
    err=$(printf '%s\n' "$out" | awk -F= '/^ERROR=/ { print substr($0, index($0, "=") + 1); exit }')
    case "$mr" in
        error|admin_failed)
            is_transient_net_signature "$err" && return 0
            ;;
    esac
    return 1
}

transient_envelope_predicate_ci_wait() {
    local out=$1
    local action br
    action=$(printf '%s\n' "$out" | awk -F= '/^ACTION=/ { print $2; exit }')
    br=$(printf '%s\n' "$out" | awk -F= '/^BAIL_REASON=/ { print substr($0, index($0, "=") + 1); exit }')
    [ "$action" = "bail" ] && is_transient_net_signature "$br" && return 0
    return 1
}

# ship-pr terminal-exit wrapper around lib-net's return-style with_transient_retry.
ship_pr_with_transient_retry() {
    local pred=$1 ff=$2
    with_transient_retry "$@"
    local rc=$_WTR_RC
    local ff_content
    ff_content=$(cat "$ff" 2>/dev/null || true)
    # Envelope still transient after exhaustion (e.g. MERGE_RESULT=error / ACTION=bail
    # with a transient ERROR=): preserve ship-pr's terminal-exit semantics regardless of rc.
    if "$pred" "$ff_content"; then
        exit_transient_net "Transient envelope exhausted"
    fi
    [ "$rc" -eq 0 ] && return 0
    is_transient_net_signature "$ff_content" \
        && exit_transient_net "Transient retries exhausted"
    return "$rc"
}

recovery_waterfall_paths_delta_revert() {
    local baseline_tracked=$1 baseline_untracked=$2 wf_log=$3
    local cur_tracked cur_untracked path
    cur_tracked=$(mktemp "${IMPLEMENT_TMPDIR}/wf-cur-tr.XXXXXX")
    cur_untracked=$(mktemp "${IMPLEMENT_TMPDIR}/wf-cur-un.XXXXXX")
    capture_tracked_dirty_paths > "$cur_tracked"
    capture_untracked_dirty_paths > "$cur_untracked"
    while IFS= read -r path || [ -n "$path" ]; do
        [ -n "$path" ] || continue
        grep -Fxq "$path" "$baseline_tracked" 2>/dev/null && continue
        if grep -Fxq "$path" "$cur_untracked" 2>/dev/null; then
            rm -f -- "$path" 2>>"$wf_log" || true
        else
            git restore --staged -- "$path" 2>>"$wf_log" || true
            git checkout -- "$path" 2>>"$wf_log" || true
        fi
    done < "$cur_tracked"
    while IFS= read -r path || [ -n "$path" ]; do
        [ -n "$path" ] || continue
        grep -Fxq "$path" "$baseline_untracked" 2>/dev/null && continue
        rm -f -- "$path" 2>>"$wf_log" || true
    done < "$cur_untracked"
    rm -f "$cur_tracked" "$cur_untracked"
}

run_recovery_waterfall() {
    local wf_phase=$1 wf_role=$2 fail_log_path=$3 verify_kind=$4
    local pr_title=${5:-} pr_body=${6:-}
    local baseline_dir baseline_head cur_head wf_log tier_rc verify_rc
    local out output plan_file plan_args=() fl_arg=() run_id repo_r
    baseline_dir=$(mktemp -d "${IMPLEMENT_TMPDIR}/recovery-wf.XXXXXX")
    wf_log="$baseline_dir/wf.log"
    git rev-parse HEAD > "$baseline_dir/head" 2>/dev/null || printf '\n' > "$baseline_dir/head"
    capture_tracked_dirty_paths > "$baseline_dir/tracked"
    capture_untracked_dirty_paths > "$baseline_dir/untracked"
    baseline_head=$(cat "$baseline_dir/head" 2>/dev/null || true)
    plan_file=$(resolve_plan_file)
    [ -n "$plan_file" ] && plan_args=(--plan-file "$plan_file")
    if [ -n "$fail_log_path" ] && [ -f "$fail_log_path" ]; then
        case "$fail_log_path" in
            "$IMPLEMENT_TMPDIR"/*) fl_arg=(--failure-log "$fail_log_path") ;;
            *) fl_arg=() ;;
        esac
    else
        fl_arg=()
    fi
    run_id=$(read_state RUN_ID)
    repo_r=$(read_state REPO)
    _wf_conflict_csv="${LARCH_WF_CONFLICT_CSV:-}"
    _wf_extra=()
    [ -n "$_wf_conflict_csv" ] && [ "$wf_role" = "resolve-conflict" ] && _wf_extra=(--conflict-files "$_wf_conflict_csv")
    for tier in codex cursor claude; do
        cur_head=$(git rev-parse HEAD 2>/dev/null || true)
        if [ "$cur_head" != "$baseline_head" ]; then
            larch_err "ship-pr recovery-waterfall: head changed after dispatch (abort rollback tier=$tier)"
            rm -rf "$baseline_dir"
            return 1
        fi
        tier_rc=1
        launcher_exit=0
        output="$IMPLEMENT_TMPDIR/recovery-${wf_phase}-${tier}-$(date +%s).out"
        launcher_stdout="$IMPLEMENT_TMPDIR/recovery-${wf_phase}-${tier}-launcher-$$.out"
        case "$tier" in
            cursor)
                if command -v cursor >/dev/null 2>&1; then
                    "$SCRIPT_DIR/launch-cursor-ci.sh" --role "$wf_role" --output "$output" --run-id "$run_id" \
                        --repo "$repo_r" ${plan_args[@]+"${plan_args[@]}"} ${_wf_extra[@]+"${_wf_extra[@]}"} ${fl_arg[@]+"${fl_arg[@]}"} --timeout 1800 >"$launcher_stdout" 2>>"$wf_log" && tier_rc=0 || tier_rc=$?
                fi
                ;;
            codex)
                if command -v codex >/dev/null 2>&1; then
                    "$SCRIPT_DIR/launch-codex-ci.sh" --role "$wf_role" --output "$output" --run-id "$run_id" \
                        --repo "$repo_r" ${plan_args[@]+"${plan_args[@]}"} ${_wf_extra[@]+"${_wf_extra[@]}"} ${fl_arg[@]+"${fl_arg[@]}"} --timeout 1800 >"$launcher_stdout" 2>>"$wf_log" && tier_rc=0 || tier_rc=$?
                fi
                ;;
            claude)
                if command -v claude >/dev/null 2>&1; then
                    "$SCRIPT_DIR/launch-claude-ci.sh" --role "$wf_role" --output "$output" --run-id "$run_id" \
                        --repo "$repo_r" ${plan_args[@]+"${plan_args[@]}"} ${_wf_extra[@]+"${_wf_extra[@]}"} ${fl_arg[@]+"${fl_arg[@]}"} --timeout 1800 >"$launcher_stdout" 2>>"$wf_log" && tier_rc=0 || tier_rc=$?
                fi
                ;;
        esac
        launcher_exit=$(awk -F= '/^LAUNCHER_EXIT=/ { print $2; exit }' "$launcher_stdout" 2>/dev/null || true)
        launcher_exit="${launcher_exit:-0}"
        rm -f "$launcher_stdout"
        if [ "$tier_rc" -ne 0 ] || [ "$launcher_exit" -ne 0 ] || [ -s "${output}.stderr-tail" ]; then
            _surface_ci_stderr_tail "$output"
        fi
        if [ "$tier_rc" -ne 0 ]; then
            recovery_waterfall_paths_delta_revert "$baseline_dir/tracked" "$baseline_dir/untracked" "$wf_log"
            continue
        fi
        if [ "$launcher_exit" -ne 0 ] || [ -s "${output}.stderr-tail" ]; then
            recovery_waterfall_paths_delta_revert "$baseline_dir/tracked" "$baseline_dir/untracked" "$wf_log"
            continue
        fi
        # Detached HEAD usually means the launcher abandoned the branch, but during
        # an in-progress rebase HEAD is legitimately detached and the rebase-nonbump
        # verifier (`git rebase --continue` below) is the operation that restores
        # the symbolic ref. Skip the detached-HEAD bail for that verifier so the
        # rebase recovery path can actually run.
        if [ "$verify_kind" != "rebase-nonbump" ] && ! git symbolic-ref --quiet HEAD >/dev/null 2>&1; then
            recovery_waterfall_paths_delta_revert "$baseline_dir/tracked" "$baseline_dir/untracked" "$wf_log"
            continue
        fi
        verify_rc=1
        case "$verify_kind" in
            checks-step6)
                capture_command_output out "$wf_log" "$SCRIPT_DIR/run-relevant-checks-captured.sh" --site step6 --tmpdir "$IMPLEMENT_TMPDIR"
                verify_rc=$?
                printf '%s\n' "$out" >> "$wf_log"
                if [ "$verify_rc" -eq 0 ] && is_relevant_checks_clean "$out"; then
                    verify_rc=0
                else
                    verify_rc=1
                fi
                ;;
            pr-prep-oos)
                run_oos_disposition_gate_if_required_before_oos_pending_false
                verify_rc=$?
                ;;
            write-final-pre)
                capture_command_output out "$wf_log" "$SCRIPT_DIR/../skills/implement/scripts/write-final-report.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"
                verify_rc=$?
                printf '%s\n' "$out" >> "$wf_log"
                [ "$verify_rc" -eq 0 ] && printf '%s\n' "$out" | grep -q '^STATUS=ok$' && verify_rc=0 || verify_rc=1
                ;;
            create-pr)
                local repo_args=() draft_args=()
                [ -n "$(read_state REPO)" ] && repo_args=(--repo "$(read_state REPO)")
                [ "$(read_state DRAFT)" = "true" ] && draft_args=(--draft)
                capture_command_output out "$wf_log" "$SCRIPT_DIR/create-pr.sh" --title "$pr_title" --body-file "$pr_body" \
                    ${draft_args[@]+"${draft_args[@]}"} ${repo_args[@]+"${repo_args[@]}"}
                verify_rc=$?
                printf '%s\n' "$out" >> "$wf_log"
                ;;
            rebase-nonbump)
                local rphase=${LARCH_WF_REBASE_PHASE:-ci-initial}
                if GIT_EDITOR=true git rebase --continue >>"$wf_log" 2>&1; then
                    _run_rebase_rebump_verify_plain_no_push "$rphase"
                    verify_rc=0
                else
                    verify_rc=1
                fi
                ;;
            *) verify_rc=1 ;;
        esac
        if [ "$verify_rc" -ne 0 ]; then
            recovery_waterfall_paths_delta_revert "$baseline_dir/tracked" "$baseline_dir/untracked" "$wf_log"
            continue
        fi
        rm -rf "$baseline_dir"
        return 0
    done
    rm -rf "$baseline_dir"
    return 1
}

# True when every path in the comma-separated vendor conflict list is a
# non-version file (exclude .claude-plugin/plugin.json, version-adjacent basenames
# handled by the deterministic pre-pass, and any repo-relative path listed in
# LARCH_VERSION_FILES when set. LARCH_BUMP_FILES is accepted as a deprecated
# compatibility alias when LARCH_VERSION_FILES is unset.
ship_pr_vendor_conflict_csv_is_non_bump_only() {
    local csv=$1 _ofs _p _bn _seg _trimmed _bf _version_files
    local -a _bump_set=()
    [ -n "$csv" ] || return 1
    _version_files="${LARCH_VERSION_FILES:-}"
    if [[ -z "$_version_files" && -n "${LARCH_BUMP_FILES:-}" ]]; then
        _version_files=$LARCH_BUMP_FILES
        larch_err "⚠ ship-pr: LARCH_BUMP_FILES is deprecated; use LARCH_VERSION_FILES"
    fi
    if [[ -n "$_version_files" ]]; then
        local -a _segments=()
        IFS=':' read -ra _segments <<< "$_version_files" || true
        for _seg in "${_segments[@]+"${_segments[@]}"}"; do
            _trimmed="${_seg#"${_seg%%[![:space:]]*}"}"
            _trimmed="${_trimmed%"${_trimmed##*[![:space:]]}"}"
            [[ -n "$_trimmed" ]] && _bump_set+=("$_trimmed")
        done
    fi
    _ofs=$IFS
    IFS=,
    set -f
    for _p in $csv; do
        IFS=$_ofs
        set +f
        _bn=${_p##*/}
        if [[ "$_p" == .claude-plugin/plugin.json || "$_p" == */.claude-plugin/plugin.json ]]; then
            return 1
        fi
        case "$_bn" in
            version.go|go.sum) return 1 ;;
        esac
        for _bf in "${_bump_set[@]+"${_bump_set[@]}"}"; do
            if [[ "$_p" == "$_bf" ]]; then
                return 1
            fi
        done
    done
    IFS=$_ofs
    set +f
    return 0
}

_run_rebase_rebump_verify_plain_no_push() {
    local phase=$1 base_remote=${2:-origin} base_ref=${3:-main} rebase_out rebase_rc fail_file
    fail_file=$(failure_capture_path rebase)
    rebase_out=$("$SCRIPT_DIR/rebase-push.sh" --no-push --base-remote "$base_remote" --base-ref "$base_ref" 2>"$fail_file")
    rebase_rc=$?
    printf '%s\n' "$rebase_out" >> "$fail_file"
    if [ "$rebase_rc" -ne 0 ]; then
        record_failure rebase "rebase-push.sh --no-push" "$rebase_rc" "$fail_file" "CI Issues"
        larch_err "⚠ ship-pr: merge conflict on rebase"
        exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
    fi
}

_run_rebase_rebump_from_step3() {
    local phase=$1 defer_push=${2:-false} base_remote=${3:-origin} base_ref=${4:-main}
    local fail_file rc

    fail_file=$(failure_capture_path rebase)
    "$SCRIPT_DIR/git-sync-local-main.sh" --base-remote "$base_remote" --base-ref "$base_ref" > "$fail_file" 2>&1
    rc=$?
    [ "$rc" -eq 0 ] || record_failure rebase "git-sync-local-main.sh" "$rc" "$fail_file" Warnings

    fail_file=$(failure_capture_path rebase)
    "$SCRIPT_DIR/refresh-run-logs.sh" \
        --state-file "$STATE_FILE" \
        --implement-tmpdir "$IMPLEMENT_TMPDIR" > "$fail_file" 2>&1 || true

    if [ "$defer_push" != true ]; then
        fail_file=$(failure_capture_path rebase)
        "$SCRIPT_DIR/git-force-push.sh" > "$fail_file" 2>&1
        rc=$?
        if [ "$rc" -ne 0 ]; then
            record_failure rebase "git-force-push.sh" "$rc" "$fail_file" "CI Issues"
            exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
        fi
    fi

    state_set_many \
        REBASE_COUNT "$(( $(read_state REBASE_COUNT) + 1 ))" \
        ITERATION "$(( $(read_state ITERATION) + 1 ))" \
        TRANSIENT_RETRIES 0
}

run_rebase_rebump() {
    local phase=$1 defer_push=false base_remote=origin base_ref=main
    local rebase_out rebase_rc conflict_out run_id
    local fail_file rc tool_label plan_file
    local plan_args=()
    shift
    while [ "$#" -gt 0 ]; do
        case "$1" in
            defer-push) defer_push=true; shift ;;
            *)
                base_remote=$1
                shift
                [ "$#" -gt 0 ] || break
                base_ref=$1
                shift
                ;;
        esac
    done
    larch_err "⚠ ship-pr: rebase (CI-fix, no re-bump)"

    # Resume after prompt-side Conflict Resolution Procedure (Phase 1–4) for
    # non-bump conflicts: verify tree, then continue the rebase/push path.
    if [ -f "${IMPLEMENT_TMPDIR}/ship-pr-rrr-after-phase14.flag" ]; then
        _run_rebase_rebump_verify_plain_no_push "$phase" "$base_remote" "$base_ref"
        _run_rebase_rebump_from_step3 "$phase" "$defer_push" "$base_remote" "$base_ref"
        rm -f "${IMPLEMENT_TMPDIR}/ship-pr-rrr-after-phase14.flag"
        state_set_many RESUME_PHASE "" CALLER_KIND ""
        return 0
    fi

    run_ship_branch_guard rebase "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"

    # Cap rebase retries to prevent indefinite storms (e.g. concurrent merges
    # to main that keep triggering ACTION=rebase from ci-wait.sh).
    local _max_rebases=20
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

    # 0. Pre-flush any pending larch-log writes before rebase (issue #2952 Bug B).
    # Failure is non-fatal: refresh-run-logs.sh short-circuits cleanly on post-merge
    # or missing-state.
    fail_file=$(failure_capture_path rebase)
    "$SCRIPT_DIR/refresh-run-logs.sh" \
        --state-file "$STATE_FILE" \
        --implement-tmpdir "$IMPLEMENT_TMPDIR" > "$fail_file" 2>&1 || true

    # 0b. Commit tracked larch-logs/ leftovers before rebase when porcelain remains
    # (issue #3209). Scoped to larch-logs/ only; best-effort failure is non-fatal.
    ship_pr_pre_rebase_larch_logs_fixup() {
        local msg="$1"
        fail_file=$(failure_capture_path rebase)
        git add -u -- larch-logs/ > "$fail_file" 2>&1
        rc=$?
        if [ "$rc" -ne 0 ]; then
            record_failure rebase "git add -u -- larch-logs/ (pre-rebase fixup)" "$rc" "$fail_file" Warnings
            return 1
        fi
        if git diff --cached --quiet -- larch-logs/ 2>/dev/null; then
            return 0
        fi
        fail_file=$(failure_capture_path rebase)
        "$SCRIPT_DIR/git-commit.sh" -m "$msg" > "$fail_file" 2>&1
        rc=$?
        if [ "$rc" -ne 0 ]; then
            record_failure rebase "git-commit.sh (pre-rebase fixup)" "$rc" "$fail_file" Warnings
            return 1
        fi
        return 0
    }
    if [[ -n "$(git status --porcelain --untracked-files=no -- larch-logs/ 2>/dev/null)" ]]; then
        ship_pr_pre_rebase_larch_logs_fixup "chore: pre-rebase working-tree fixup (#3209)" || true
        if [[ -n "$(git status --porcelain --untracked-files=no -- larch-logs/ 2>/dev/null)" ]]; then
            ship_pr_pre_rebase_larch_logs_fixup "chore: pre-rebase working-tree fixup (#3209) — follow-up" || true
        fi
    fi

    run_id=$(read_state RUN_ID)

    # 1. Rebase without pushing; keep in-progress on conflict for vendor resolution
    fail_file=$(failure_capture_path rebase)
    ship_pr_with_transient_retry transient_envelope_predicate_none "$fail_file" \
        "$SCRIPT_DIR/rebase-push.sh" --no-push --keep-on-conflict --base-remote "$base_remote" --base-ref "$base_ref"
    rebase_rc=$_WTR_RC
    rebase_out=$_WTR_OUT
    if [ "$rebase_rc" -eq 1 ]; then
        # Conflict — deterministic pre-pass, then Phase 1–4 (non-bump) or vendor resolve-conflict
        larch_err "⚠ ship-pr: rebase-push keep-on-conflict pause (exit 1); deterministic pre-pass / vendor / Phase 1–4 handoff follows"
        conflict_files_kv=$(kv_value CONFLICT_FILES "$rebase_out")
        _orchestrator_conflict_csv="$conflict_files_kv"
        skip_vendor=false
        vendor_conflict_csv=""
        if [ -n "$conflict_files_kv" ]; then
            needs_vendor=false
            remaining_csv=""
            _ofs=$IFS
            IFS=,
            set -f
            # shellcheck disable=SC2086
            for _cf in $conflict_files_kv; do
                IFS=$_ofs
                set +f
                _base_cf=${_cf##*/}
                _unresolved=false
                case "$_base_cf" in
                    plugin.json)
                        if [[ "$_cf" == .claude-plugin/plugin.json || "$_cf" == */.claude-plugin/plugin.json ]]; then
                            if ! git checkout --ours -- "$_cf" || ! git add -- "$_cf"; then
                                needs_vendor=true
                                _unresolved=true
                            fi
                        else
                            needs_vendor=true
                            _unresolved=true
                        fi
                        ;;
                    version.go|go.sum)
                        if ! git checkout --ours -- "$_cf" || ! git add -- "$_cf"; then
                            needs_vendor=true
                            _unresolved=true
                        fi
                        ;;
                    *)
                        needs_vendor=true
                        _unresolved=true
                        ;;
                esac
                if [ "$_unresolved" = true ]; then
                    remaining_csv="${remaining_csv:+$remaining_csv,}${_cf}"
                fi
            done
            IFS=$_ofs
            set +f
            if [ "$needs_vendor" = false ]; then
                if GIT_EDITOR=true git rebase --continue >>"$fail_file" 2>&1; then
                    skip_vendor=true
                else
                    needs_vendor=true
                    vendor_conflict_csv=$(git diff --name-only --diff-filter=U 2>/dev/null | tr '\n' ',' | sed 's/,$//')
                    if [ -z "$vendor_conflict_csv" ]; then
                        vendor_conflict_csv=$_orchestrator_conflict_csv
                    fi
                fi
            else
                vendor_conflict_csv=$remaining_csv
            fi
        else
            needs_vendor=true
            vendor_conflict_csv=""
        fi

        if [ "$skip_vendor" = false ] && [ -z "$vendor_conflict_csv" ]; then
            vendor_conflict_csv=$(git diff --name-only --diff-filter=U 2>/dev/null | tr '\n' ',' | sed 's/,$//')
        fi
        if [ "$skip_vendor" = false ] && [ -z "$vendor_conflict_csv" ] && [ -n "$_orchestrator_conflict_csv" ]; then
            vendor_conflict_csv=$_orchestrator_conflict_csv
        fi

        if [ "$skip_vendor" = false ] && [ "$needs_vendor" = true ] && [ -n "$vendor_conflict_csv" ] \
            && ship_pr_vendor_conflict_csv_is_non_bump_only "$vendor_conflict_csv"; then
            local _rrr_phase14_flag wf_fail
            _rrr_phase14_flag="${IMPLEMENT_TMPDIR}/ship-pr-rrr-after-phase14.flag"
            wf_fail=$(failure_capture_path rebase)
            printf 'ship-pr: non-bump-only rebase conflicts; attempting recovery waterfall\n' >>"$wf_fail"
            export LARCH_WF_CONFLICT_CSV="$vendor_conflict_csv"
            export LARCH_WF_REBASE_PHASE="$phase"
            if run_recovery_waterfall rebase-nonbump resolve-conflict "$wf_fail" rebase-nonbump; then
                unset LARCH_WF_CONFLICT_CSV LARCH_WF_REBASE_PHASE
                skip_vendor=true
            else
                unset LARCH_WF_CONFLICT_CSV LARCH_WF_REBASE_PHASE
                if ! : >"$_rrr_phase14_flag"; then
                    printf 'ERROR: ship-pr: cannot write %s\n' "$_rrr_phase14_flag" >> "$fail_file"
                    record_failure rebase "ship-pr-rrr-after-phase14.flag" 1 "$fail_file" "CI Issues"
                    exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
                fi
                state_set_many RESUME_PHASE ship-pr-rrr-phase14 CALLER_KIND ship_pr_pre_push
                larch_err "⚠ ship-pr: recovery waterfall exhausted; legacy Phase 1–4 handoff (stall)"
                larch_err "⚠ ship-pr: dispatching Phase 1–4 conflict-resolution (caller_kind=ship_pr_pre_push; aggregator-dispatch=conflict-resolution.md)"
                emit_kv CONFLICT_FILES "$vendor_conflict_csv"
                exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
            fi
        fi

        if [ "$skip_vendor" = false ]; then
            conflict_out="$IMPLEMENT_TMPDIR/rebase-conflict-$(date +%s).out"
            fail_file=$(failure_capture_path conflict-resolution)
            _launch_extra=()
            [ -n "$vendor_conflict_csv" ] && _launch_extra+=(--conflict-files "$vendor_conflict_csv")
            if command -v codex >/dev/null 2>&1; then
                tool_label="launch-codex-ci.sh resolve-conflict"
                "$SCRIPT_DIR/launch-codex-ci.sh" --role resolve-conflict --output "$conflict_out" \
                    --run-id "$run_id" --repo "$(read_state REPO)" ${plan_args[@]+"${plan_args[@]}"} \
                    ${_launch_extra[@]+"${_launch_extra[@]}"} --timeout 600 > "$fail_file" 2>&1
                rc=$?
            else
                tool_label="launch-cursor-ci.sh resolve-conflict"
                "$SCRIPT_DIR/launch-cursor-ci.sh" --role resolve-conflict --output "$conflict_out" \
                    --run-id "$run_id" --repo "$(read_state REPO)" ${plan_args[@]+"${plan_args[@]}"} \
                    ${_launch_extra[@]+"${_launch_extra[@]}"} --timeout 600 > "$fail_file" 2>&1
                rc=$?
            fi
            local _conflict_launcher_exit
            _conflict_launcher_exit=$(awk -F= '/^LAUNCHER_EXIT=/ {print $2; exit}' "$fail_file" 2>/dev/null || true)
            _conflict_launcher_exit="${_conflict_launcher_exit:-0}"
            if [ "$rc" -ne 0 ] || [ "$_conflict_launcher_exit" -ne 0 ] || [ -s "${conflict_out}.stderr-tail" ]; then
                _surface_ci_stderr_tail "$conflict_out"
            fi
            [ "$rc" -eq 0 ] || record_failure conflict-resolution "$tool_label" "$rc" "$fail_file" "External Reviewer Issues"
            fail_file=$(failure_capture_path conflict-resolution)
            "$SCRIPT_DIR/append-token-record.sh" --input "${conflict_out}.token-record" \
                --tmpdir "$IMPLEMENT_TMPDIR" > "$fail_file" 2>&1
            rc=$?
            [ "$rc" -eq 0 ] || record_failure conflict-resolution "append-token-record.sh" "$rc" "$fail_file" Warnings
        fi
        # Fresh rebase after vendor fix: if vendor ran git rebase --continue, the
        # branch is already rebased and this returns SKIPPED_ALREADY_FRESH. If the
        # vendor left a conflict or broke the tree it fails, causing exit_stall.
        _run_rebase_rebump_verify_plain_no_push "$phase" "$base_remote" "$base_ref"
    elif [ "$rebase_rc" -ne 0 ]; then
        record_failure rebase "rebase-push.sh --keep-on-conflict" "$rebase_rc" "$fail_file" "CI Issues"
        # Classify against combined stderr + stdout — git/network helpers
        # emit transient signals on stderr that $rebase_out alone misses.
        if is_transient_net_signature "$(cat "$fail_file" 2>/dev/null)"; then
            exit_transient_net "rebase: $rebase_out"
        fi
        larch_err "⚠ ship-pr: merge conflict on rebase"
        exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
    fi

    _run_rebase_rebump_from_step3 "$phase" "$defer_push" "$base_remote" "$base_ref"
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
    larch_err "→ ship-pr: CI watch (${phase})"

    ci_args=()
    while IFS= read -r arg; do ci_args+=("$arg"); done <<EOF
$(ci_common_args)
EOF
    fail_file=$(failure_capture_path "$phase")
    ship_pr_with_transient_retry transient_envelope_predicate_ci_wait "$fail_file" "$SCRIPT_DIR/ci-wait.sh" "${ci_args[@]}"
    rc=$_WTR_RC
    out=$_WTR_OUT
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
                larch_err "→ ship-pr: CI green"
                advance_phase ci-merge
                return 0
            fi
            merge_args=(--pr "$(read_state PR_NUMBER)" --repo "$(read_state REPO)")
            [ "$NO_ADMIN_FALLBACK" = "true" ] && merge_args+=(--no-admin-fallback)
            fail_file=$(failure_capture_path ci-merge)
            ship_pr_with_transient_retry transient_envelope_predicate_merge_pr "$fail_file" \
                "$SCRIPT_DIR/merge-pr.sh" "${merge_args[@]}"
            rc=$_WTR_RC
            merge_out=$_WTR_OUT
            merge_result=$(kv_value MERGE_RESULT "$merge_out")
            error_text=$(kv_value ERROR "$merge_out")
            if [ "$rc" -ne 0 ]; then
                record_failure ci-merge "merge-pr.sh" "$rc" "$fail_file" "CI Issues"
            fi
            case "$merge_result" in
                merged|admin_merged)
                    state_set_many PR_CLOSED true MERGE_RESULT "$merge_result" BAIL_REASON "" STALL_TRACKING false STALL_STEP ""
                    larch_err "→ ship-pr: merged"
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
                        larch_err "→ ship-pr: merged"
                        rename_done_best_effort
                        write_post_merge_sentinel
                        advance_phase postmerge
                    else
                        run_rebase_rebump "$phase"
                    fi
                    return 0
                    ;;
                policy_denied|admin_failed|error)
                    if [[ "$merge_result" == "error" ]] && is_head_divergence_recoverable "$error_text"; then
                        run_rebase_rebump "$phase"
                        return 0
                    fi
                    if [[ "$merge_result" == "admin_failed" ]] && [[ "$error_text" == *"Base branch was modified"* ]]; then
                        run_rebase_rebump "$phase"
                        return 0
                    fi
                    [ "$rc" -ne 0 ] || record_failure ci-merge "merge-pr.sh envelope" 1 "$fail_file" "CI Issues"
                    state_set_many BAIL_REASON "$error_text" STALL_TRACKING true STALL_STEP 12d EXIT_CODE 4
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
            larch_err "→ ship-pr: merged"
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
                if ! is_autonomous_exit3_bail_reason "$bail_reason"; then
                    state_set BAIL_NEEDS_USER_INPUT true
                fi
                exit 3
            fi
            exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12d)"
            ;;
        *) exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)" ;;
    esac
}

run_postmerge_phase() {
    local rc fail_file final_report_output
    larch_err "→ ship-pr: postmerge"
    write_finalize_state
    fail_file=$(failure_capture_path postmerge)
    "$SCRIPT_DIR/implement-finalize.sh" postmerge --state-file "$IMPLEMENT_TMPDIR/finalize-state.sh" --final-bail-reason-file "$IMPLEMENT_TMPDIR/final-bail-reason.txt" > "$fail_file" 2>&1
    rc=$?
    [ "$rc" -eq 0 ] || record_failure postmerge "implement-finalize.sh postmerge" "$rc" "$fail_file"
    # Finalize manifest to status=done here so the update survives if the
    # LLM session ends before prompt-side Step 18 teardown runs. The tmpdir
    # manifest and tmpdir summary-final.md are updated in place (run-log mirror
    # at final-summary.md when not --comment-only); no post-merge git
    # commit is made (policy: NEVER commit after post-merge-sentinel exists,
    # see skills/implement/SKILL.md NEVER #19).
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
            # Manifest recovery failed; skip final manifest (status=done), final-summary re-render,
            # and write-final-report.sh — downstream assumes a coherent manifest tree.
            :
        else
            local manifest_ok=false final_report_rc=1
            fail_file=$(failure_capture_path postmerge)
            "$SCRIPT_DIR/larch-log.sh" manifest \
                --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                --skill implement --run-id "$flush_run_id" \
                --field "status=done" \
                --field "pr_number=$pr_num" \
                > "$fail_file" 2>&1
            rc=$?
            if [ "$rc" -eq 0 ]; then
                manifest_ok=true
            else
                record_failure postmerge "larch-log.sh manifest" "$rc" "$fail_file" Warnings
            fi
            final_report_rc=1
            final_report_output=""
            if [ "$manifest_ok" = true ]; then
                # Re-render summary-final.md under $IMPLEMENT_TMPDIR now that MERGE_RESULT is set
                # in state, so tmpdir summary-final.md / run-log final-summary.md mirror align with merged OUTCOME
                # (pre-merge pass wrote bailed). NEVER #19: no post-merge git commit publishes this.
                fail_file=$(failure_capture_path postmerge)
                ship_pr_with_transient_retry transient_envelope_predicate_none "$fail_file" \
                    "$SCRIPT_DIR/../skills/implement/scripts/write-final-report.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"
                final_report_rc=$_WTR_RC
                final_report_output=$_WTR_OUT
                if [ "$final_report_rc" -ne 0 ]; then
                    record_failure postmerge "write-final-report.sh (postmerge)" "$final_report_rc" "$fail_file" Warnings
                fi
            fi
        fi
    fi
    advance_phase "done"
    exit 0
}

main() {
    larch_quiet_init
    while [ $# -gt 0 ]; do
        case "$1" in
            --state-file) [ $# -ge 2 ] || die_usage "--state-file requires a value"; STATE_FILE=$2; shift 2 ;;
            --implement-tmpdir) [ $# -ge 2 ] || die_usage "--implement-tmpdir requires a value"; IMPLEMENT_TMPDIR=$2; shift 2 ;;
            --merge) [ $# -ge 2 ] || die_usage "--merge requires a value"; MERGE=$2; shift 2 ;;
            --draft) [ $# -ge 2 ] || die_usage "--draft requires a value"; DRAFT=$2; shift 2 ;;
            --forked) [ $# -ge 2 ] || die_usage "--forked requires a value"; FORKED_TARGET=$2; shift 2 ;;
            --branch-name) [ $# -ge 2 ] || die_usage "--branch-name requires a value"; INIT_BRANCH_NAME=$2; INIT_BRANCH_NAME_SET=true; shift 2 ;;
            --expected-session-id) [ $# -ge 2 ] || die_usage "--expected-session-id requires a value"; INIT_EXPECTED_SESSION_ID=$2; INIT_EXPECTED_SESSION_ID_SET=true; shift 2 ;;
            --expected-tmpdir-basename-prefix) [ $# -ge 2 ] || die_usage "--expected-tmpdir-basename-prefix requires a value"; INIT_EXPECTED_TMPDIR_BASENAME_PREFIX=$2; INIT_EXPECTED_TMPDIR_BASENAME_PREFIX_SET=true; shift 2 ;;
            --force-init-state) [ $# -ge 2 ] || die_usage "--force-init-state requires a value"; FORCE_INIT_STATE=$2; shift 2 ;;
            --issue-number) [ $# -ge 2 ] || die_usage "--issue-number requires a value"; INIT_ISSUE_NUMBER=$2; INIT_ISSUE_NUMBER_SET=true; shift 2 ;;
            --manifest-path) [ $# -ge 2 ] || die_usage "--manifest-path requires a value"; INIT_MANIFEST_PATH=$2; INIT_MANIFEST_PATH_SET=true; shift 2 ;;
            --run-id) [ $# -ge 2 ] || die_usage "--run-id requires a value"; INIT_RUN_ID=$2; INIT_RUN_ID_SET=true; shift 2 ;;
            --tool-label) [ $# -ge 2 ] || die_usage "--tool-label requires a value"; INIT_TOOL_LABEL=$2; INIT_TOOL_LABEL_SET=true; shift 2 ;;
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
    is_bool "$NO_ADMIN_FALLBACK" || die_usage "--no-admin-fallback must be true or false"
    is_bool "$NO_LOGS_COMMIT" || die_usage "--no-logs-commit must be true or false"
    [ -z "$MERGE" ] || is_bool "$MERGE" || die_usage "--merge must be true or false"
    [ -z "$DRAFT" ] || is_bool "$DRAFT" || die_usage "--draft must be true or false"
    [ -z "$FORKED_TARGET" ] || is_bool "$FORKED_TARGET" || die_usage "--forked must be true or false"
    is_bool "$FORCE_INIT_STATE" || die_usage "--force-init-state must be true or false"
    if [ "$INIT_BRANCH_NAME_SET" = "true" ]; then
        case "$INIT_BRANCH_NAME" in *$'\r'*|*$'\n'*) die_usage "--branch-name must not contain CR or LF" ;; esac
    fi
    if [ "$INIT_EXPECTED_SESSION_ID_SET" = "true" ]; then
        case "$INIT_EXPECTED_SESSION_ID" in *$'\r'*|*$'\n'*) die_usage "--expected-session-id must not contain CR or LF" ;; esac
    fi
    if [ "$INIT_EXPECTED_TMPDIR_BASENAME_PREFIX_SET" = "true" ]; then
        case "$INIT_EXPECTED_TMPDIR_BASENAME_PREFIX" in *$'\r'*|*$'\n'*) die_usage "--expected-tmpdir-basename-prefix must not contain CR or LF" ;; esac
    fi
    if [ "$INIT_ISSUE_NUMBER_SET" = "true" ]; then
        case "$INIT_ISSUE_NUMBER" in *$'\r'*|*$'\n'*) die_usage "--issue-number must not contain CR or LF" ;; esac
    fi
    if [ "$INIT_MANIFEST_PATH_SET" = "true" ]; then
        case "$INIT_MANIFEST_PATH" in *$'\r'*|*$'\n'*) die_usage "--manifest-path must not contain CR or LF" ;; esac
    fi
    if [ "$INIT_RUN_ID_SET" = "true" ]; then
        case "$INIT_RUN_ID" in *$'\r'*|*$'\n'*) die_usage "--run-id must not contain CR or LF" ;; esac
    fi
    if [ "$INIT_TOOL_LABEL_SET" = "true" ]; then
        case "$INIT_TOOL_LABEL" in *$'\r'*|*$'\n'*) die_usage "--tool-label must not contain CR or LF" ;; esac
    fi
    export IMPLEMENT_TMPDIR
    export LARCH_NO_LOGS_COMMIT="$NO_LOGS_COMMIT"

    if [ ! -e "$STATE_FILE" ] || [ "$FORCE_INIT_STATE" = "true" ]; then
        write_initial_state
    fi
    [ -r "$STATE_FILE" ] || die_usage "--state-file must be readable"
    validate_state_syntax
    _ci_fix_pending_hydrate

    for key in \
        PHASE BRANCH_NAME ISSUE_NUMBER RUN_ID REPO REPO_UNAVAILABLE FORKED_TARGET \
        MERGE DRAFT DEFERRED PR_CLOSED \
        DONE_RENAME_APPLIED STALL_TRACKING STALL_STEP BAIL_NEEDS_USER_INPUT \
        CI_PASSED OOS_PENDING PR_NUMBER PR_URL PR_TITLE RESUME_PHASE CALLER_KIND \
        REBASE_COUNT FIX_ATTEMPTS ITERATION TRANSIENT_RETRIES FAILED_RUN_ID \
        MANIFEST_PATH TOOL_LABEL \
        BAIL_REASON BAIL_FAILURE_DETAIL_LOG DESIGN_ONLY_DONE EXPECTED_SESSION_ID \
        EXPECTED_TMPDIR_BASENAME_PREFIX NO_LOGS_COMMIT IMPLEMENT_TMPDIR
    do
        require_key "$key"
    done

    for key in REPO_UNAVAILABLE FORKED_TARGET MERGE DRAFT DEFERRED PR_CLOSED DONE_RENAME_APPLIED STALL_TRACKING BAIL_NEEDS_USER_INPUT CI_PASSED OOS_PENDING CI_FIX_REBASE_PENDING DESIGN_ONLY_DONE NO_LOGS_COMMIT; do
        is_bool "$(read_state "$key")" || die_usage "state-file key $key must be true or false"
    done

    manifest_path_check=$(read_state MANIFEST_PATH)
    if [ -n "$manifest_path_check" ]; then
        if [ ! -r "$manifest_path_check" ] || ! jq empty "$manifest_path_check" >/dev/null 2>&1; then
            die_usage "MANIFEST_PATH must be empty or a readable JSON file (got: $manifest_path_check)"
        fi
    fi
    unset manifest_path_check

    if [ -n "$RESUME_PHASE" ]; then
        case "$RESUME_PHASE" in
            force-push-gate|bump|step8b_rebase|step8_apply_bump_same_version)
                case "$RESUME_PHASE" in
                    step8b_rebase|step8_apply_bump_same_version)
                        larch_err "⚠ ship-pr: tolerating legacy --resume-phase $RESUME_PHASE (Phase 1 #3364)"
                        ;;
                esac
                advance_phase bump
                state_set_many RESUME_PHASE "" CALLER_KIND ""
                ;;
            pr-create) advance_phase pr-prep ;;
            ci-initial) advance_phase ci-initial ;;
            ci-merge) state_set CI_PASSED false; advance_phase ci-merge ;;
            evaluate-failure) advance_phase evaluate-failure ;;
            postmerge) advance_phase postmerge ;;
            ship-pr-rrr-phase14)
                _rrr_ph=$(read_state PHASE)
                case "$_rrr_ph" in
                    ci-initial|ci-merge) ;;
                    *) die_usage "ship-pr-rrr-phase14 resume requires PHASE ci-initial or ci-merge, got: ${_rrr_ph:-empty}" ;;
                esac
                if [ ! -f "${IMPLEMENT_TMPDIR}/ship-pr-rrr-after-phase14.flag" ]; then
                    die_usage "ship-pr-rrr-phase14 resume requires ship-pr-rrr-after-phase14.flag under IMPLEMENT_TMPDIR (missing handoff token)"
                fi
                advance_phase "$_rrr_ph"
                run_rebase_rebump "$_rrr_ph"
                state_set_many RESUME_PHASE "" CALLER_KIND ""
                ;;
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
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then main "$@"; fi
