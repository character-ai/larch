#!/usr/bin/env bash
# implement-bootstrap.sh — /implement Step 0 phase dispatcher (infra + tracking phases).

set -uo pipefail
# Intentional: best-effort failure model. Errexit is OFF file-wide. Each leaf
# invocation captures rc via 'rc=$?' after the call; hard failures exit 2 with
# STEP_FAILED=... Do NOT enable -e without auditing every call site.

# Contract KV must land on stdout for orchestrator command substitution. Quiet
# redirection would route emit_kv to FD3 only; keep quiet disabled for this
# entrypoint so stdout carries the full KV stream. Human-facing warnings use
# stderr so parsers can treat stdout as KEY=value only.
export LARCH_QUIET_DISABLE="${LARCH_QUIET_DISABLE:-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-execution-issues.sh
source "$SCRIPT_DIR/lib-execution-issues.sh"

if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    CLAUDE_PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
export CLAUDE_PLUGIN_ROOT

UP_TO_PHASE=""
CALLER_ENV_OPT=""
ISSUE_NUMBER_OPT=""
FORKED_TARGET=false
EMERGENCY_REQUESTED=false
EMERGENCY_REQUESTED_ARG_SEEN=false
UPSTREAM_REPO_OPT=""
RUN_ID_OPT=""
PREFLIGHT_TMPDIR_OPT=""
CODER_OPT=""
IMPLEMENT_BAIL_REASON=""
SKIP_CODEX_PROBE_FLAG=false
SKIP_CURSOR_PROBE_FLAG=false
RESUME_PLAN_TAIL=false
RUN_PLAN_LOGGED=false
PLAN_SUMMARY_POSTED=false

# Parsed / derived in phase_infra (defaults for tail when phases skip)
CURRENT_BRANCH=""
IS_MAIN=""
IS_USER_BRANCH=""
USER_PREFIX=""
ENTRY_GATE=""
SKIP_BRANCH_CHECK=""
SESSION_TMPDIR=""
SESSION_ID=""
REPO=""
REPO_UNAVAILABLE=""
CODEX_PRESENT=""
CURSOR_PRESENT=""
CODEX_BINARY_FOUND=""
CURSOR_BINARY_FOUND=""
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-}"
CLAUDE_SOURCE_OK=""
LARCH_TOKEN_SESSION_ID=""
LARCH_CLAUDE_SOURCE_FILE=""
LARCH_TIMING_LEDGER=""
codex_available=""
cursor_available=""
ISSUE_NUMBER_RESOLVED=""
RUN_ID=""
BRANCH_SELECTED=""
DEFERRED=false
STALL_TRACKING=false
BRANCH_NAME=""
BRANCH_ACTION=""
PLAN_FILE=""
coder=""
coder_fallback=""

usage() {
    larch_err "Usage: implement-bootstrap.sh --up-to-phase <infra|tracking|plan|coder|all> [--caller-env PATH] [--issue-number N] [--forked-target true|false] [--emergency-requested true|false] [--upstream-repo OWNER/REPO] [--run-id ID] [--coder claude|codex|cursor] [--preflight-tmpdir PATH] [--resume-plan-tail]"
}

die_usage() {
    larch_err "implement-bootstrap.sh: $1"
    usage
    exit 2
}

# Apply one KEY=value line to known globals (best-effort).
ingest_kv_line() {
    local line=$1 key val
    line=${line%%$'\r'}
    case "$line" in
        ''|\#*) return 0 ;;
        *=*)
            key=${line%%=*}
            val=${line#*=}
            case "$key" in
                CURRENT_BRANCH) CURRENT_BRANCH=$val ;;
                IS_MAIN) IS_MAIN=$val ;;
                IS_USER_BRANCH) IS_USER_BRANCH=$val ;;
                USER_PREFIX) USER_PREFIX=$val ;;
                ENTRY_GATE) ENTRY_GATE=$val ;;
                SKIP_BRANCH_CHECK) SKIP_BRANCH_CHECK=$val ;;
                SESSION_TMPDIR) SESSION_TMPDIR=$val ;;
                SESSION_ID) SESSION_ID=$val ;;
                REPO) REPO=$val ;;
                REPO_UNAVAILABLE) REPO_UNAVAILABLE=$val ;;
                CODEX_PRESENT) CODEX_PRESENT=$val ;;
                CURSOR_PRESENT) CURSOR_PRESENT=$val ;;
                CODEX_BINARY_FOUND) CODEX_BINARY_FOUND=$val ;;
                CURSOR_BINARY_FOUND) CURSOR_BINARY_FOUND=$val ;;
            esac
            ;;
    esac
}

ingest_kv_block() {
    local data=$1 line
    [ -z "$data" ] && return 0
    while IFS= read -r line || [ -n "$line" ]; do
        ingest_kv_line "$line"
    done < <(printf '%s\n' "$data")
}

kv_value_from_block() {
    local key=$1 data=$2
    printf '%s\n' "$data" | awk -F= -v k="$key" 'BEGIN{e=""} $1 == k {e=substr($0,index($0,"=")+1); exit} END{print e}'
}

valid_run_id() {
    local value=$1
    case "$value" in
        ""|*[!A-Za-z0-9._-]*) return 1 ;;
        *) return 0 ;;
    esac
}

valid_issue_number() {
    local value=$1
    case "$value" in
        ""|*[!0-9]*) return 1 ;;
        *) return 0 ;;
    esac
}

resolve_run_id() {
    local candidate=""

    if [ -n "${RUN_ID_OPT:-}" ]; then
        candidate=$RUN_ID_OPT
    elif valid_run_id "${RUN_ID:-}"; then
        candidate=$RUN_ID
    else
        candidate=$(tr -d '\r\n' < "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)
        if ! valid_run_id "$candidate"; then
            candidate=${LARCH_TOKEN_SESSION_ID:-}
        fi
    fi

    valid_run_id "$candidate" || return 1
    printf '%s\n' "$candidate"
}

emit_skip_breadcrumb_if_enabled() {
    local reason=$1
    if larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}"; then
        emit_breadcrumb "⏩ step0: tracking — skip ($reason)"
    fi
}

emit_tracking_breadcrumb_if_enabled() {
    if larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}"; then
        emit_breadcrumb "→ step0: tracking adopted #${ISSUE_NUMBER_RESOLVED:-} (run=${RUN_ID:-} branch=${BRANCH_SELECTED:-})"
    fi
}

emit_plan_materialize_breadcrumbs_if_enabled() {
    if larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}"; then
        if [ "${RUN_PLAN_LOGGED:-false}" = "true" ]; then
            emit_breadcrumb "→ step0: branch ${BRANCH_NAME:-} + plan logged"
        else
            emit_breadcrumb "→ step0: branch ${BRANCH_NAME:-}"
        fi
        if [ "${PLAN_SUMMARY_POSTED:-false}" = "true" ]; then
            emit_breadcrumb "→ step0: larch:plan posted"
        fi
    fi
}

persist_run_flags() {
    local workflow_path=$1
    local persist_rc

    "$SCRIPT_DIR/persist-implement-run-flags.sh" \
        --implement-tmpdir "$IMPLEMENT_TMPDIR" \
        --no-issues false \
        --workflow-path "$workflow_path" \
        --emergency-requested "$EMERGENCY_REQUESTED" \
        >"$IMPLEMENT_TMPDIR/persist-implement-run-flags.out" \
        2>"$IMPLEMENT_TMPDIR/persist-implement-run-flags.stderr.log"
    persist_rc=$?
    if [ "$persist_rc" -ne 0 ]; then
        STALL_TRACKING=true
        IMPLEMENT_BAIL_REASON=run-flags-persist-failed
        return 1
    fi
    return 0
}

restore_emergency_requested_from_run_flags_if_unset() {
    local prior_emergency=""
    [ "${EMERGENCY_REQUESTED_ARG_SEEN:-false}" = "true" ] && return 0
    [ -n "${IMPLEMENT_TMPDIR:-}" ] || return 0
    [ -f "$IMPLEMENT_TMPDIR/run-flags.sh" ] || return 0
    prior_emergency=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/run-flags.sh" --key EMERGENCY_REQUESTED --default "")
    case "$prior_emergency" in
        true|false) EMERGENCY_REQUESTED=$prior_emergency ;;
    esac
}

redact_file_best_effort() {
    local input_file=$1 output_file=$2 redact_tmp rc
    [ -f "$input_file" ] || return 1
    redact_tmp="$(mktemp "${TMPDIR:-/tmp}/implement-bootstrap-redact.XXXXXX")" || return 1
    if [ -x "$SCRIPT_DIR/redact-secrets.sh" ]; then
        if ! "$SCRIPT_DIR/redact-secrets.sh" <"$input_file" >"$redact_tmp" 2>/dev/null; then
            rc=$?
            rm -f "$redact_tmp"
            return "$rc"
        fi
    else
        cat "$input_file" >"$redact_tmp"
    fi
    if [ -x "$SCRIPT_DIR/redact-tmpdir-paths.sh" ]; then
        if ! "$SCRIPT_DIR/redact-tmpdir-paths.sh" <"$redact_tmp" >"$output_file" 2>/dev/null; then
            rc=$?
            rm -f "$redact_tmp"
            return "$rc"
        fi
        rm -f "$redact_tmp"
        return 0
    fi
    if mv "$redact_tmp" "$output_file"; then
        return 0
    fi
    rc=$?
    rm -f "$redact_tmp"
    return "$rc"
}

append_emergency_bypass_log_if_present() {
    local bypass_log append_rc fallback_entry fallback_content kind issue redact_source
    local consumed_sentinel

    [ "${EMERGENCY_REQUESTED:-false}" = "true" ] || return 0

    bypass_log="$PREFLIGHT_TMPDIR_OPT/emergency-bypass.log"
    [ -s "$bypass_log" ] || return 0
    consumed_sentinel="$IMPLEMENT_TMPDIR/.emergency-bypass-log-consumed"
    [ -e "$consumed_sentinel" ] && return 0

    local bypass_log_valid=true
    while IFS= read -r _line || [ -n "$_line" ]; do
        [ -n "$_line" ] || continue
        case "$_line" in
            BYPASS\ kind=*\ issue=*)
                kind=${_line#BYPASS kind=}
                kind=${kind%% issue=*}
                issue=${_line##* issue=}
                case "$kind" in
                    ""|*[!a-z0-9-]*) bypass_log_valid=false; break ;;
                esac
                case "$issue" in
                    ""|*[!0-9]*) bypass_log_valid=false; break ;;
                esac
                ;;
            *)
                bypass_log_valid=false
                break
                ;;
        esac
    done <"$bypass_log"
    if [ "$bypass_log_valid" != "true" ]; then
        fallback_content="$(mktemp "${TMPDIR:-/tmp}/implement-bootstrap-emergency-bypass.XXXXXX")" || return 1
        redact_source="$(mktemp "${TMPDIR:-/tmp}/implement-bootstrap-emergency-bypass-source.XXXXXX")" || {
            rm -f "$fallback_content"
            return 1
        }
        if ! redact_file_best_effort "$bypass_log" "$redact_source"; then
            printf '%s\n' '<redaction failed; raw emergency bypass log omitted>' >"$redact_source"
        fi
        {
            printf '%s\n' 'Invalid emergency bypass log format. Expected one line per bypass:'
            printf '%s\n\n' 'BYPASS kind=<lowercase-token> issue=<number>'
            cat "$redact_source"
        } >"$fallback_content"
        rm -f "$redact_source"
        bypass_log=$fallback_content
        append_rc=99
    else
        append_rc=0
    fi

    if [ "$append_rc" -eq 0 ]; then
        "$SCRIPT_DIR/append-tool-failure.sh" \
            --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
            --site "implement-bootstrap emergency-bypass-log" \
            --tool "/implement --emergency preflight" \
            --exit-code 0 \
            --category Warnings \
            --output-file "$bypass_log" \
            --status-label bypassed \
            --redact
        append_rc=$?
    fi

    if [ "$append_rc" -ne 0 ]; then
        fallback_entry="$(mktemp "${TMPDIR:-/tmp}/implement-bootstrap-emergency-bypass-entry.XXXXXX")" || return 1
        redact_source="$(mktemp "${TMPDIR:-/tmp}/implement-bootstrap-emergency-bypass-fallback.XXXXXX")" || {
            rm -f "$fallback_entry"
            return 1
        }
        if ! redact_file_best_effort "$bypass_log" "$redact_source"; then
            printf '%s\n' '<redaction failed; raw emergency bypass log omitted>' >"$redact_source"
        fi
        {
            if [ "$append_rc" -eq 99 ]; then
                printf '%s\n' '- **Step implement-bootstrap emergency-bypass-log — /implement --emergency preflight invalid-format (exit 99)**:'
            else
                printf '%s\n' '- **Step implement-bootstrap emergency-bypass-log — /implement --emergency preflight bypassed (fallback append; helper failed)**:'
            fi
            printf '  ```\n'
            cat "$redact_source"
            if [ -s "$redact_source" ] && [ "$(tail -c 1 "$redact_source" | wc -c | tr -d ' ')" != "0" ]; then
                printf '\n'
            fi
            printf '  ```\n'
        } >"$fallback_entry"
        "$SCRIPT_DIR/append-execution-issue.sh" \
            --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
            --category Warnings \
            --entry-file "$fallback_entry"
        rm -f "$redact_source"
        rm -f "$fallback_entry"
    fi

    : >"$consumed_sentinel"
    rm -f "${fallback_content:-}"
}

post_tracking_metadata() {
    local write_sentinel=$1
    local post_out post_rc posted
    local args

    args=(
        --implement-tmpdir "$IMPLEMENT_TMPDIR"
    )
    if [ "$write_sentinel" = "true" ]; then
        args+=(--issue-number "$ISSUE_NUMBER_RESOLVED")
    fi
    args+=(
        --run-id "$RUN_ID"
        --adopted true
        --emergency-requested "$EMERGENCY_REQUESTED"
    )

    post_out=$("$CLAUDE_PLUGIN_ROOT/skills/implement/scripts/post-tracking-issue.sh" \
        "${args[@]}" \
        2>"$IMPLEMENT_TMPDIR/post-tracking-issue.stderr.log")
    post_rc=$?
    posted=$(kv_value_from_block POSTED "$post_out")
    if [ "$post_rc" -ne 0 ] || [ "$posted" != "true" ]; then
        DEFERRED=true
        [ "$write_sentinel" = "true" ] && rm -f "$IMPLEMENT_TMPDIR/parent-issue.md"
        return 1
    fi
    return 0
}

should_run_post_tracking_phase() {
    # Post-tracking phases run on every non-bail / non-stall path. Specific
    # phase functions own narrower skips such as REPO_UNAVAILABLE or missing
    # plan artifacts.
    [ -z "${IMPLEMENT_BAIL_REASON:-}" ] \
        && [ "${STALL_TRACKING:-false}" != "true" ]
}

should_run_phase_plan_materialize() {
    [ -z "${IMPLEMENT_BAIL_REASON:-}" ] \
        && [ "${STALL_TRACKING:-false}" != "true" ] \
        && [ "${REPO_UNAVAILABLE:-false}" != "true" ]
}

resume_tail_plan_artifacts_ready() {
    [ -n "${IMPLEMENT_TMPDIR:-}" ] || return 1
    [ -f "$IMPLEMENT_TMPDIR/plan.txt" ] || return 1
    [ -f "$IMPLEMENT_TMPDIR/feature-description.txt" ] || return 1
    [ -n "${ISSUE_NUMBER_OPT:-}" ] || return 1
}

ensure_untracked_baseline_snapshot() {
    local snapshot_out

    [ -n "${IMPLEMENT_TMPDIR:-}" ] || return 0
    [ "${RESUME_PLAN_TAIL:-false}" != "true" ] || return 0

    snapshot_out="$IMPLEMENT_TMPDIR/untracked-baseline.z"
    [ -e "$snapshot_out" ] && return 0

    "$SCRIPT_DIR/snapshot-untracked.sh" --output "$snapshot_out" --nul || true
}

run_dirty_tree_checkpoint() {
    local dirty_out dirty_rc dirty_status

    dirty_out=$("$SCRIPT_DIR/check-mid-run-dirty-tree.sh" --mode checkpoint 2>"$IMPLEMENT_TMPDIR/check-mid-run-dirty-tree.stderr.log")
    dirty_rc=$?
    if [ "$dirty_rc" -ne 0 ]; then
        dirty_status=unknown
    else
        dirty_status=$(kv_value_from_block STATUS "$dirty_out")
        [ -n "$dirty_status" ] || dirty_status=unknown
    fi
    case "$dirty_status" in
        dirty|unknown)
            IMPLEMENT_BAIL_REASON=dirty-tree
            return 1
            ;;
    esac
    IMPLEMENT_BAIL_REASON=""
    return 0
}

tracking_init_failed() {
    IMPLEMENT_BAIL_REASON=tracking-init-failed
    STALL_TRACKING=true
}

run_larch_log_init() {
    local issue=$1 run_id=$2 site=$3
    local init_out init_rc init_err
    init_err=$(mktemp "${TMPDIR:-/tmp}/larch-ib-log-init.XXXXXX")
    init_out=$("$SCRIPT_DIR/larch-log.sh" init \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --skill implement \
        --run-id "$run_id" \
        --issue "$issue" 2>"$init_err")
    init_rc=$?
    if [ "$init_rc" -ne 0 ]; then
        cp "$init_err" "$IMPLEMENT_TMPDIR/tracking-larch-log-init.stderr.log" 2>/dev/null || true
        if [ -n "${init_out:-}" ]; then
            printf '%s\n' "$init_out" >>"$IMPLEMENT_TMPDIR/tracking-larch-log-init.stderr.log" 2>/dev/null || true
        fi
        larch_err "**⚠ Step 0 tracking: larch-log init failed during $site.**"
        rm -f "$init_err"
        tracking_init_failed
        return 1
    fi
    rm -f "$init_err"
    return 0
}

rename_to_implementing() {
    local issue=$1 site=$2
    local rename_out rename_rc rename_failed rename_log
    [ -n "$issue" ] || return 0
    rename_log="$IMPLEMENT_TMPDIR/tracking-rename.stderr.log"
    rename_out=$("$SCRIPT_DIR/tracking-issue-write.sh" rename --issue "$issue" --state implementing 2>&1)
    rename_rc=$?
    printf '%s\n' "$rename_out" >"$rename_log" 2>/dev/null || true
    rename_failed=$(kv_value_from_block FAILED "$rename_out")
    if [ "$rename_rc" -ne 0 ] || [ "$rename_failed" = "true" ]; then
        "$SCRIPT_DIR/append-tool-failure.sh" \
            --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
            --site "Step 0 tracking adoption — $site rename to implementing" \
            --tool "tracking-issue-write.sh rename" \
            --exit-code "$rename_rc" \
            --category "Tool Failures" \
            --output-file "$rename_log" \
            --redact || true
    fi
    return 0
}

phase_infra() {
    local gate_err setup_out setup_err branch_out gate_out
    local branch_rc gate_rc setup_rc
    local dynamic_archetypes_value="" caller_dynamic_archetypes
    local session_env_args _source_exit
    local resume_existing_tmpdir=""

    branch_out=$("$SCRIPT_DIR/create-branch.sh" --check)
    branch_rc=$?
    if [ "$branch_rc" -ne 0 ]; then
        emit_kv STEP_FAILED create-branch
        exit 2
    fi
    ingest_kv_block "$branch_out"

    gate_err=$(mktemp "${TMPDIR:-/tmp}/larch-ib-gate.XXXXXX")
    gate_out=$("$SCRIPT_DIR/session-entry-gate.sh" \
        --mode implement \
        --current-branch "$CURRENT_BRANCH" \
        --is-main "$IS_MAIN" \
        --is-user-branch "$IS_USER_BRANCH" \
        --user-prefix "$USER_PREFIX" 2>"$gate_err")
    gate_rc=$?
    if [ "$gate_rc" -ne 0 ]; then
        if [ -s "$gate_err" ]; then
            _gh_out=$(grep '^GATE_ERROR=' "$gate_err" 2>/dev/null | head -n 1 || true)
            if [ -n "$_gh_out" ]; then
                printf '%s\n' "$_gh_out"
            else
                while IFS= read -r _gln || [ -n "$_gln" ]; do
                    larch_err "$_gln"
                done <"$gate_err"
            fi
        fi
        emit_kv STEP_FAILED session-entry-gate
        rm -f "$gate_err"
        exit 2
    fi
    rm -f "$gate_err"
    ingest_kv_block "$gate_out"

    if [ "$RESUME_PLAN_TAIL" = "true" ] \
        && [ -n "${IMPLEMENT_TMPDIR:-}" ] \
        && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
        resume_existing_tmpdir=$IMPLEMENT_TMPDIR
    fi

    if [ -n "$resume_existing_tmpdir" ]; then
        SESSION_TMPDIR=$resume_existing_tmpdir
        SESSION_ID=$(tr -d '\r\n' <"$SESSION_TMPDIR/session-id" 2>/dev/null || true)
        IMPLEMENT_TMPDIR=$SESSION_TMPDIR
        export IMPLEMENT_TMPDIR
        restore_emergency_requested_from_run_flags_if_unset

        REPO=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key REPO --default "")
        REPO_UNAVAILABLE=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key REPO_UNAVAILABLE --default "false")
        CODEX_PRESENT=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CODEX_PRESENT --default "false")
        CURSOR_PRESENT=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CURSOR_PRESENT --default "false")
        CODEX_BINARY_FOUND=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CODEX_BINARY_FOUND --default "false")
        CURSOR_BINARY_FOUND=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CURSOR_BINARY_FOUND --default "false")
        LARCH_TOKEN_SESSION_ID=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
        LARCH_CLAUDE_SOURCE_FILE=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
        LARCH_TIMING_LEDGER=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
        export LARCH_TIMING_LEDGER

        if [ -n "${LARCH_CLAUDE_SOURCE_FILE:-}" ]; then
            CLAUDE_SOURCE_OK=true
        else
            CLAUDE_SOURCE_OK=false
        fi
    else

        local setup_cmd
        setup_cmd=("$SCRIPT_DIR/session-setup.sh" --prefix claude-implement --check-reviewers)
        if [ "$SKIP_BRANCH_CHECK" = "true" ]; then
            setup_cmd+=(--skip-branch-check)
        fi
        if larch_quiet_truthy "$SKIP_CODEX_PROBE_FLAG"; then
            setup_cmd+=(--skip-codex-probe)
        fi
        if larch_quiet_truthy "$SKIP_CURSOR_PROBE_FLAG"; then
            setup_cmd+=(--skip-cursor-probe)
        fi
        if [ -n "$CALLER_ENV_OPT" ]; then
            setup_cmd+=(--caller-env "$CALLER_ENV_OPT")
        fi

        setup_err=$(mktemp "${TMPDIR:-/tmp}/larch-ib-setup.XXXXXX")
        setup_out=$("${setup_cmd[@]}" 2>"$setup_err")
        setup_rc=$?
        if [ "$setup_rc" -ne 0 ]; then
            printf '%s\n' "$setup_out"
            emit_kv STEP_FAILED session-setup
            rm -f "$setup_err"
            exit 2
        fi
        if [ -s "$setup_err" ]; then
            while IFS= read -r _seln || [ -n "$_seln" ]; do
                [ -z "$_seln" ] && continue
                larch_err "$_seln"
            done <"$setup_err"
        fi
        rm -f "$setup_err"
        ingest_kv_block "$setup_out"

        IMPLEMENT_TMPDIR="$SESSION_TMPDIR"
        export IMPLEMENT_TMPDIR

        "$SCRIPT_DIR/write-session-id.sh" --output "$IMPLEMENT_TMPDIR/session-id"
        LARCH_TOKEN_SESSION_ID=$(tr -d '\r\n' <"$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)
        export LARCH_TIMING_LEDGER="$IMPLEMENT_TMPDIR/timing-ledger.tsv"

        if "$SCRIPT_DIR/token-claude-source.sh" \
            >"$IMPLEMENT_TMPDIR/claude-source.env" \
            2>"$IMPLEMENT_TMPDIR/claude-source-error.log"; then
            LARCH_CLAUDE_SOURCE_FILE="$IMPLEMENT_TMPDIR/claude-source.env"
            CLAUDE_SOURCE_OK=true
        else
            _source_exit=$?
            "$SCRIPT_DIR/append-tool-failure.sh" \
                --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
                --site "Step 0" \
                --tool "token-claude-source.sh" \
                --exit-code "$_source_exit" \
                --category Warnings \
                --output-file "$IMPLEMENT_TMPDIR/claude-source-error.log" \
                --redact || true
            CLAUDE_SOURCE_OK=false
            LARCH_CLAUDE_SOURCE_FILE=""
        fi

        dynamic_archetypes_value=""
        if [ -z "${dynamic_archetypes_value:-}" ] && [ -n "${CALLER_ENV_OPT:-}" ] && [ -r "$CALLER_ENV_OPT" ]; then
            caller_dynamic_archetypes=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$CALLER_ENV_OPT" --key LARCH_DYNAMIC_ARCHETYPES_MAX --default "")
            case "$caller_dynamic_archetypes" in
                "") ;;
                [0-8]) dynamic_archetypes_value=$caller_dynamic_archetypes ;;
                *)
                    larch_err '**⚠ /implement: ignoring invalid LARCH_DYNAMIC_ARCHETYPES_MAX from caller session-env (must be 0..8).**'
                    ;;
            esac
        fi

        session_env_args=(
            --output "$IMPLEMENT_TMPDIR/session-env.sh"
            --repo "$REPO"
            --repo-unavailable "$REPO_UNAVAILABLE"
            --codex-present "$CODEX_PRESENT"
            --cursor-present "$CURSOR_PRESENT"
            --codex-binary-found "$CODEX_BINARY_FOUND"
            --cursor-binary-found "$CURSOR_BINARY_FOUND"
            --timing-ledger "$IMPLEMENT_TMPDIR/timing-ledger.tsv"
            --token-session-id "$LARCH_TOKEN_SESSION_ID"
            --prev-implement-tmpdir "$IMPLEMENT_TMPDIR"
            --forked-target "$FORKED_TARGET"
        )
        [ -n "${LARCH_CLAUDE_SOURCE_FILE:-}" ] && session_env_args+=(--claude-source-file "$LARCH_CLAUDE_SOURCE_FILE")
        [ -n "${dynamic_archetypes_value:-}" ] && session_env_args+=(--dynamic-archetypes "$dynamic_archetypes_value")
        _wse_rc=0
        "$SCRIPT_DIR/write-session-env.sh" "${session_env_args[@]}" || _wse_rc=$?
        if [ "$_wse_rc" -ne 0 ]; then
            emit_kv STEP_FAILED write-session-env
            exit 2
        fi
        "$SCRIPT_DIR/token-ledger.sh" mark "Step 0 — preflight" || true
        "$SCRIPT_DIR/timing-ledger.sh" mark "Step 0 — preflight" || true

        LARCH_TOKEN_SESSION_ID=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")
        LARCH_CLAUDE_SOURCE_FILE=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "")
        LARCH_TIMING_LEDGER=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")
    fi

    restore_emergency_requested_from_run_flags_if_unset

    if [ "$REPO_UNAVAILABLE" = "true" ]; then
        larch_err '**⚠ Could not determine repository name. CI monitoring (Steps 10, 12) and merge (Step 12b) will be skipped.**'
    fi

    local _cb _cp
    _cb=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CODEX_BINARY_FOUND --default "false")
    _cp=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CODEX_PRESENT --default "false")
    if [ "$_cb" != "true" ]; then
        larch_err '**⚠ Codex not available (binary not found). Proceeding without Codex reviewer.**'
    elif [ "$_cp" != "true" ]; then
        larch_err '**⚠ Codex not healthy for this session (runtime probe failed, skipped probe, auth error, or timeout). Using Claude replacement.**'
    fi
    local _cub _cup
    _cub=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CURSOR_BINARY_FOUND --default "false")
    _cup=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CURSOR_PRESENT --default "false")
    if [ "$_cub" != "true" ]; then
        larch_err '**⚠ Cursor not available (binary not found). Proceeding without Cursor reviewer.**'
    elif [ "$_cup" != "true" ]; then
        larch_err '**⚠ Cursor not healthy for this session (runtime probe failed, skipped probe, auth error, or timeout). Using Claude replacement.**'
    fi

    if [ "$_cb" = "true" ] && [ "$_cp" = "true" ]; then
        codex_available=true
    else
        codex_available=false
    fi
    if [ "$_cub" = "true" ] && [ "$_cup" = "true" ]; then
        cursor_available=true
    else
        cursor_available=false
    fi

    if larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}"; then
        emit_breadcrumb --category=progress "→ step0: infra ready (tmpdir=$IMPLEMENT_TMPDIR session=$SESSION_ID)"
    fi

    return 0
}

phase_tracking() {
    local sentinel read_out read_rc read_failed sentinel_issue sentinel_run_id sentinel_adopted
    local state_out state_rc state_failed issue_state issue_is_pr
    local post_out post_rc posted

    "$SCRIPT_DIR/token-ledger.sh" mark "Step 0 — tracking issue" || true
    "$SCRIPT_DIR/timing-ledger.sh" mark "Step 0 — tracking issue" || true

    if [ "${REPO_UNAVAILABLE:-}" = "true" ]; then
        BRANCH_SELECTED=repo-unavailable-skip
        DEFERRED=true
        emit_skip_breadcrumb_if_enabled repo-unavailable
        return 0
    fi

    if [ "$FORKED_TARGET" = "true" ]; then
        BRANCH_SELECTED=forked-target-skip
        DEFERRED=true
        local upstream_context_rc
        if [ -n "$UPSTREAM_REPO_OPT" ] && [ -n "$ISSUE_NUMBER_OPT" ]; then
            if "$SCRIPT_DIR/get-issue-context.sh" \
                --issue "$ISSUE_NUMBER_OPT" \
                --repo "$UPSTREAM_REPO_OPT" \
                --tmpdir "$IMPLEMENT_TMPDIR" \
                >"$IMPLEMENT_TMPDIR/upstream-context.out" \
                2>"$IMPLEMENT_TMPDIR/upstream-context.log"; then
                :
            else
                upstream_context_rc=$?
                "$SCRIPT_DIR/append-tool-failure.sh" \
                    --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
                    --site "Step 0 tracking adoption — forked target upstream context" \
                    --tool "get-issue-context.sh" \
                    --exit-code "$upstream_context_rc" \
                    --category "Warnings" \
                    --output-file "$IMPLEMENT_TMPDIR/upstream-context.log" \
                    --redact || true
            fi
        fi
        emit_skip_breadcrumb_if_enabled forked-target
        return 0
    fi

    if [ "$RESUME_PLAN_TAIL" = "true" ]; then
        sentinel="$IMPLEMENT_TMPDIR/parent-issue.md"
        if [ -f "$sentinel" ]; then
            if [ -z "$ISSUE_NUMBER_OPT" ]; then
                larch_err "**⚠ Step 0 tracking: --issue-number is required to resume an adopted tracking sentinel.**"
                emit_kv STEP_FAILED issue-number-required-for-resume
                exit 2
            fi
            read_out=$("$SCRIPT_DIR/tracking-issue-read.sh" --sentinel "$sentinel" 2>"$IMPLEMENT_TMPDIR/tracking-issue-read.stderr.log")
            read_rc=$?
            read_failed=$(kv_value_from_block FAILED "$read_out")
            sentinel_issue=$(kv_value_from_block ISSUE_NUMBER "$read_out")
            sentinel_run_id=$(kv_value_from_block RUN_ID "$read_out")
            sentinel_adopted=$(kv_value_from_block ADOPTED "$read_out")

            if [ "$read_rc" -eq 0 ] && [ "$read_failed" != "true" ] && [ "$sentinel_adopted" = "true" ] \
                && valid_issue_number "$sentinel_issue" && valid_run_id "$sentinel_run_id"; then
                if [ "$sentinel_issue" != "$ISSUE_NUMBER_OPT" ]; then
                    larch_err "**⚠ Step 0 tracking: --resume-plan-tail requires the adopted tracking sentinel to match --issue-number.**"
                    emit_kv STEP_FAILED resume-plan-tail-sentinel
                    exit 2
                fi
                BRANCH_SELECTED=branch-1-resume
                ISSUE_NUMBER_RESOLVED=$sentinel_issue
                RUN_ID=$sentinel_run_id
                return 0
            fi
            larch_err "**⚠ Step 0 tracking: --resume-plan-tail requires a valid adopted tracking sentinel.**"
            emit_kv STEP_FAILED resume-plan-tail-sentinel
            exit 2
        fi
        if resume_tail_plan_artifacts_ready; then
            ISSUE_NUMBER_RESOLVED=$ISSUE_NUMBER_OPT
            if ! valid_run_id "${RUN_ID:-}"; then
                RUN_ID=$(resolve_run_id 2>/dev/null || true)
            fi
            BRANCH_SELECTED=branch-2-adopt
            DEFERRED=true
            return 0
        fi
        larch_err "**⚠ Step 0 tracking: --resume-plan-tail requires \$IMPLEMENT_TMPDIR/parent-issue.md or existing plan artifacts in \$IMPLEMENT_TMPDIR.**"
        emit_kv STEP_FAILED resume-plan-tail-sentinel
        exit 2
    fi

    sentinel="$IMPLEMENT_TMPDIR/parent-issue.md"
    if [ -f "$sentinel" ]; then
        if [ -z "$ISSUE_NUMBER_OPT" ]; then
            larch_err "**⚠ Step 0 tracking: --issue-number is required to resume an adopted tracking sentinel.**"
            emit_kv STEP_FAILED issue-number-required-for-resume
            exit 2
        fi
        read_out=$("$SCRIPT_DIR/tracking-issue-read.sh" --sentinel "$sentinel" 2>"$IMPLEMENT_TMPDIR/tracking-issue-read.stderr.log")
        read_rc=$?
        read_failed=$(kv_value_from_block FAILED "$read_out")
        sentinel_issue=$(kv_value_from_block ISSUE_NUMBER "$read_out")
        sentinel_run_id=$(kv_value_from_block RUN_ID "$read_out")
        sentinel_adopted=$(kv_value_from_block ADOPTED "$read_out")

        if [ "$read_rc" -eq 0 ] && [ "$read_failed" != "true" ] && [ "$sentinel_adopted" = "true" ] \
            && valid_issue_number "$sentinel_issue" && valid_run_id "$sentinel_run_id"; then
            if [ -n "$ISSUE_NUMBER_OPT" ] && [ "$sentinel_issue" != "$ISSUE_NUMBER_OPT" ]; then
                if [ "$RESUME_PLAN_TAIL" = "true" ]; then
                    larch_err "**⚠ Step 0 tracking: --resume-plan-tail requires the adopted tracking sentinel to match --issue-number.**"
                    emit_kv STEP_FAILED resume-plan-tail-sentinel
                    exit 2
                fi
                larch_err "**⚠ Step 0 tracking: sentinel mismatch (sentinel has #$sentinel_issue, argv requested #$ISSUE_NUMBER_OPT). Clearing sentinel and re-adopting.**"
                rm -f "$sentinel"
            else
                BRANCH_SELECTED=branch-1-resume
                ISSUE_NUMBER_RESOLVED=$sentinel_issue
                RUN_ID=$sentinel_run_id
                rename_to_implementing "$ISSUE_NUMBER_RESOLVED" "Branch 1 resume"
                run_larch_log_init "$ISSUE_NUMBER_RESOLVED" "$RUN_ID" "Branch 1 resume" || return 0
                persist_run_flags HARD || return 0
                post_tracking_metadata false || true
                emit_tracking_breadcrumb_if_enabled
                return 0
            fi
        else
            if [ "$RESUME_PLAN_TAIL" = "true" ]; then
                larch_err "**⚠ Step 0 tracking: --resume-plan-tail requires a valid adopted tracking sentinel.**"
                emit_kv STEP_FAILED resume-plan-tail-sentinel
                exit 2
            fi
            larch_err "**⚠ Step 0 tracking: malformed tracking sentinel. Clearing sentinel and re-adopting.**"
            rm -f "$sentinel"
        fi
    elif [ "$RESUME_PLAN_TAIL" = "true" ]; then
        larch_err "**⚠ Step 0 tracking: --resume-plan-tail requires \$IMPLEMENT_TMPDIR/parent-issue.md.**"
        emit_kv STEP_FAILED resume-plan-tail-sentinel
        exit 2
    fi

    [ -n "$ISSUE_NUMBER_OPT" ] || return 0

    state_out=$("$SCRIPT_DIR/get-issue-state.sh" --issue "$ISSUE_NUMBER_OPT" 2>"$IMPLEMENT_TMPDIR/get-issue-state.stderr.log")
    state_rc=$?
    state_failed=$(kv_value_from_block FAILED "$state_out")
    if [ "$state_rc" -ne 0 ] || [ "$state_failed" = "true" ]; then
        emit_kv STEP_FAILED get-issue-state
        exit 2
    fi

    issue_is_pr=$(kv_value_from_block IS_PR "$state_out")
    issue_state=$(kv_value_from_block STATE "$state_out")
    if [ "$issue_is_pr" = "true" ]; then
        IMPLEMENT_BAIL_REASON=adopted-issue-is-pr
        return 0
    fi
    if [ "$issue_state" = "CLOSED" ]; then
        IMPLEMENT_BAIL_REASON=adopted-issue-closed
        return 0
    fi
    if [ "$issue_state" != "OPEN" ]; then
        emit_kv STEP_FAILED get-issue-state
        exit 2
    fi

    BRANCH_SELECTED=branch-2-adopt
    ISSUE_NUMBER_RESOLVED=$ISSUE_NUMBER_OPT
    rename_to_implementing "$ISSUE_NUMBER_RESOLVED" "Branch 2 adopt"
    if ! RUN_ID=$(resolve_run_id); then
        tracking_init_failed
        return 0
    fi

    run_larch_log_init "$ISSUE_NUMBER_RESOLVED" "$RUN_ID" "Branch 2 adopt" || return 0
    persist_run_flags HARD || return 0
    post_tracking_metadata true || return 0

    emit_tracking_breadcrumb_if_enabled
    return 0
}

phase_plan_materialize() {
    local plan_src gh_issue_arg feature_file gh_rc gh_err
    local issue_title slug branch_name_derived create_out create_rc create_err
    local branch_out branch_rc branch_value
    local goal_text_raw goal_text run_plan_rc run_plan_err goal_redact_rc goal_redact_err
    local tally_body_raw tally_body tally_rc tally_err
    local summary_body_raw summary_body summary_rc summary_err
    local summary_args

    gh_issue_arg=$ISSUE_NUMBER_RESOLVED
    [ "$FORKED_TARGET" = "true" ] && gh_issue_arg=$ISSUE_NUMBER_OPT
    PLAN_FILE="$IMPLEMENT_TMPDIR/plan.txt"
    feature_file="$IMPLEMENT_TMPDIR/feature-description.txt"
    if ! valid_run_id "${RUN_ID:-}"; then
        RUN_ID=$(resolve_run_id 2>/dev/null || true)
    fi

    if [ "$RESUME_PLAN_TAIL" != "true" ]; then
        ensure_untracked_baseline_snapshot

        "$SCRIPT_DIR/token-ledger.sh" mark "implement Step 0 — plan materialization" || true
        "$SCRIPT_DIR/timing-ledger.sh" mark "implement Step 0 — plan materialization" || true

        plan_src="$PREFLIGHT_TMPDIR_OPT/plan-from-issue.txt"
        if ! cp "$plan_src" "$PLAN_FILE" 2>"$IMPLEMENT_TMPDIR/copy-plan.stderr.log"; then
            emit_kv IMPLEMENT_TMPDIR "${IMPLEMENT_TMPDIR:-}"
            emit_kv STEP_FAILED copy-plan
            exit 2
        fi
        if ! append_emergency_bypass_log_if_present; then
            emit_kv IMPLEMENT_TMPDIR "${IMPLEMENT_TMPDIR:-}"
            emit_kv STEP_FAILED emergency-bypass-log
            exit 2
        fi

        gh_err="$IMPLEMENT_TMPDIR/gh-issue-view.stderr.log"
        if [ "$FORKED_TARGET" = "true" ]; then
            if [ -z "$UPSTREAM_REPO_OPT" ]; then
                printf '%s\n' 'forked-target requires --upstream-repo for gh issue view' >"$gh_err"
                emit_kv IMPLEMENT_TMPDIR "${IMPLEMENT_TMPDIR:-}"
                emit_kv STEP_FAILED gh-issue-view
                exit 2
            fi
            gh issue view "$gh_issue_arg" --repo "$UPSTREAM_REPO_OPT" --json title,body --template "{{.title}}\n\n{{.body}}" >"$feature_file" 2>"$gh_err"
        else
            gh issue view "$gh_issue_arg" --json title,body --template "{{.title}}\n\n{{.body}}" >"$feature_file" 2>"$gh_err"
        fi
        gh_rc=$?
        if [ "$gh_rc" -ne 0 ]; then
            emit_kv IMPLEMENT_TMPDIR "${IMPLEMENT_TMPDIR:-}"
            emit_kv STEP_FAILED gh-issue-view
            exit 2
        fi

        "$SCRIPT_DIR/timing-ledger.sh" workflow-path "HARD" || true

        persist_run_flags HARD || return 0
    else
        if ! append_emergency_bypass_log_if_present; then
            emit_kv IMPLEMENT_TMPDIR "${IMPLEMENT_TMPDIR:-}"
            emit_kv STEP_FAILED emergency-bypass-log
            exit 2
        fi
        persist_run_flags HARD || return 0
    fi
    # Resume-tail idempotency: see implement-bootstrap.md § Resume-tail idempotency
    if ! run_dirty_tree_checkpoint; then
        return 0
    fi

    if [ "$FORKED_TARGET" != "true" ] && [ "${IS_USER_BRANCH:-false}" != "true" ]; then
        issue_title=$(head -1 "$feature_file" 2>/dev/null || true)
        slug=$(printf '%s' "$issue_title" \
            | tr '[:upper:]' '[:lower:]' \
            | tr -c 'a-z0-9' '-' \
            | sed 's/--*/-/g; s/^-//; s/-$//' \
            | cut -c1-40 \
            | sed 's/-*$//')
        [ -n "$slug" ] || slug=issue
        branch_name_derived="${USER_PREFIX}/${slug}-${ISSUE_NUMBER_RESOLVED}"
        create_err="$IMPLEMENT_TMPDIR/create-branch.stderr.log"
        create_out=$("$SCRIPT_DIR/create-branch.sh" --branch "$branch_name_derived" 2>"$create_err")
        create_rc=$?
        if [ "$create_rc" -ne 0 ]; then
            STALL_TRACKING=true
            IMPLEMENT_BAIL_REASON=branch-create-failed
            return 0
        fi
        BRANCH_ACTION=$(kv_value_from_block ACTION "$create_out")
    fi

    branch_out=$("$SCRIPT_DIR/git-current-branch.sh" 2>"$IMPLEMENT_TMPDIR/git-current-branch.stderr.log")
    branch_rc=$?
    if [ "$branch_rc" -eq 0 ]; then
        branch_value=$(kv_value_from_block BRANCH "$branch_out")
        if [ -n "$branch_value" ]; then
            BRANCH_NAME=$branch_value
        else
            STALL_TRACKING=true
            IMPLEMENT_BAIL_REASON=branch-create-failed
            return 0
        fi
    else
        STALL_TRACKING=true
        IMPLEMENT_BAIL_REASON=branch-create-failed
        return 0
    fi

    issue_title=$(head -1 "$feature_file" 2>/dev/null || true)
    goal_text_raw="Implement issue #${gh_issue_arg}: ${issue_title:-planned change}."
    goal_redact_err="$IMPLEMENT_TMPDIR/goal-text-redact.stderr.log"
    goal_text=$(printf '%s\n' "$goal_text_raw" | "$SCRIPT_DIR/redact-secrets.sh" | "$SCRIPT_DIR/redact-tmpdir-paths.sh" 2>"$goal_redact_err")
    goal_redact_rc=$?
    if [ "$goal_redact_rc" -ne 0 ]; then
        goal_text="Implement issue #${gh_issue_arg}: <REDACTED-TITLE>."
        "$SCRIPT_DIR/append-tool-failure.sh" \
            --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
            --site "Step 0 plan materialization — goal text redaction" \
            --tool "redact-secrets.sh | redact-tmpdir-paths.sh" \
            --exit-code "$goal_redact_rc" \
            --category Warnings \
            --output-file "$goal_redact_err" \
            --redact || true
    fi
    run_plan_err="$IMPLEMENT_TMPDIR/run-step1-plan-log.stderr.log"
    "$SCRIPT_DIR/run-step1-plan-log.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" --goal-text "$goal_text" >"$IMPLEMENT_TMPDIR/run-step1-plan-log.out" 2>"$run_plan_err"
    run_plan_rc=$?
    if [ "$run_plan_rc" -ne 0 ]; then
        "$SCRIPT_DIR/append-tool-failure.sh" \
            --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
            --site "Step 0 plan materialization — plan-goals-test" \
            --tool "run-step1-plan-log.sh" \
            --exit-code "$run_plan_rc" \
            --category Warnings \
            --output-file "$run_plan_err" \
            --redact || true
    else
        RUN_PLAN_LOGGED=true
    fi

    if ! valid_run_id "${RUN_ID:-}"; then
        printf '%s\n' 'RUN_ID missing or invalid after resolution; skipping plan-review tally and larch:plan summary.' >"$IMPLEMENT_TMPDIR/run-id-resolution.warning.log"
        "$SCRIPT_DIR/append-tool-failure.sh" \
            --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
            --site "Step 0 plan materialization — run id resolution" \
            --tool "resolve_run_id" \
            --exit-code 1 \
            --category Warnings \
            --output-file "$IMPLEMENT_TMPDIR/run-id-resolution.warning.log" \
            --redact || true
    else
        tally_body_raw="$IMPLEMENT_TMPDIR/plan-review-tally-body.raw.md"
        {
            printf '%s\n' '# Plan Review Tally'
            printf '\n'
            printf 'Plan read from issue larch:plan block for issue #%s.\n' "${gh_issue_arg:-}"
        } >"$tally_body_raw"
        tally_body="$IMPLEMENT_TMPDIR/plan-review-tally-body.md"
        if ! "$SCRIPT_DIR/redact-secrets.sh" <"$tally_body_raw" | "$SCRIPT_DIR/redact-tmpdir-paths.sh" >"$tally_body" 2>/dev/null; then
            cp "$tally_body_raw" "$tally_body" 2>/dev/null || true
        fi
        tally_err="$IMPLEMENT_TMPDIR/write-tally.stderr.log"
        "$SCRIPT_DIR/write-tally.sh" \
            --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
            --skill implement \
            --run-id "$RUN_ID" \
            --phase plan-review \
            --mode hard \
            --rounds 0 \
            --accepted 0 \
            --rejected 0 \
            --body-file "$tally_body" \
            >"$IMPLEMENT_TMPDIR/write-tally.out" \
            2>"$tally_err"
        tally_rc=$?
        if [ "$tally_rc" -ne 0 ]; then
            "$SCRIPT_DIR/append-tool-failure.sh" \
                --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
                --site "Step 0 plan materialization — plan-review tally" \
                --tool "write-tally.sh" \
                --exit-code "$tally_rc" \
                --category Warnings \
                --output-file "$tally_err" \
                --redact || true
        fi
    fi

    if valid_run_id "${RUN_ID:-}" && [ "$FORKED_TARGET" != "true" ] && [ -n "${ISSUE_NUMBER_RESOLVED:-}" ]; then
        summary_body_raw="$IMPLEMENT_TMPDIR/larch-plan-summary.raw.md"
        {
            printf "Plan materialized for run \`%s\`.\n" "${RUN_ID:-}"
            printf '\n'
            printf "- Branch: \`%s\`\n" "${BRANCH_NAME:-}"
            printf "- Plan file: \`%s\`\n" "${PLAN_FILE:-}"
        } >"$summary_body_raw"
        summary_body="$IMPLEMENT_TMPDIR/larch-plan-summary.md"
        summary_err="$IMPLEMENT_TMPDIR/tracking-issue-summary.stderr.log"
        summary_redact_err="$IMPLEMENT_TMPDIR/larch-plan-summary.redact.stderr.log"
        if ! "$SCRIPT_DIR/redact-secrets.sh" <"$summary_body_raw" | "$SCRIPT_DIR/redact-tmpdir-paths.sh" >"$summary_body" 2>"$summary_redact_err"; then
            "$SCRIPT_DIR/append-tool-failure.sh" \
                --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
                --site "Step 0 plan materialization — larch:plan summary redaction" \
                --tool "redact-secrets.sh | redact-tmpdir-paths.sh" \
                --exit-code 1 \
                --category Warnings \
                --output-file "$summary_redact_err" \
                --redact || true
            cp "$summary_body_raw" "$summary_body" 2>/dev/null || true
        fi
        summary_args=(upsert-summary --issue "$ISSUE_NUMBER_RESOLVED" --marker "<!-- larch:plan v1 runid=$RUN_ID -->" --content-file "$summary_body")
        "$SCRIPT_DIR/tracking-issue-summary.sh" "${summary_args[@]}" >"$IMPLEMENT_TMPDIR/tracking-issue-summary.out" 2>"$summary_err"
        summary_rc=$?
        if [ "$summary_rc" -ne 0 ]; then
            "$SCRIPT_DIR/append-tool-failure.sh" \
                --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
                --site "Step 0 plan materialization — larch:plan summary" \
                --tool "tracking-issue-summary.sh" \
                --exit-code "$summary_rc" \
                --category Warnings \
                --output-file "$summary_err" \
                --redact || true
        else
            PLAN_SUMMARY_POSTED=true
        fi
    fi

    emit_plan_materialize_breadcrumbs_if_enabled
    return 0
}

phase_coder_select() {
    # Belt-and-suspenders: the case-block guard already enforces these.
    [ -z "${IMPLEMENT_BAIL_REASON:-}" ] || return 0
    [ "${STALL_TRACKING:-false}" != "true" ] || return 0

    # Step 2 requires both plan artifacts. Do not emit a coder on paths that
    # cannot legally dispatch implementation.
    if [ "${REPO_UNAVAILABLE:-false}" = "true" ] \
        || [ -z "${PLAN_FILE:-}" ] \
        || [ ! -f "${PLAN_FILE:-/nonexistent}" ] \
        || [ ! -f "${IMPLEMENT_TMPDIR:-/nonexistent}/feature-description.txt" ]; then
        return 0
    fi

    "$SCRIPT_DIR/token-ledger.sh" mark "implement Step 0 — coder select" || true
    LARCH_TIMING_SKILL=implement "$SCRIPT_DIR/timing-ledger.sh" mark "implement Step 0 — coder select" || true

    local codex_binary_found cursor_binary_found
    codex_binary_found=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CODEX_BINARY_FOUND --default "")
    cursor_binary_found=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key CURSOR_BINARY_FOUND --default "")

    if [ -n "$CODER_OPT" ]; then
        _phase_coder_explicit "$CODER_OPT" "$codex_binary_found" "$cursor_binary_found"
    else
        _phase_coder_implicit
    fi

    emit_coder_breadcrumb_if_enabled
    return 0
}

_phase_coder_explicit() {
    local choice=$1 codex_binary_found=$2 cursor_binary_found=$3
    case "$choice" in
        claude)
            coder=claude
            ;;
        cursor)
            if [ "${cursor_available:-false}" = "true" ]; then
                coder=cursor
            else
                _phase_coder_explicit_unavailable cursor "$cursor_binary_found"
            fi
            ;;
        codex)
            if [ "${codex_available:-false}" = "true" ]; then
                coder=codex
            else
                _phase_coder_explicit_unavailable codex "$codex_binary_found"
            fi
            ;;
    esac
}

_phase_coder_explicit_unavailable() {
    local tool=$1 binary_found=$2
    local tool_caps binary_key other1 other2
    case "$tool" in
        cursor)
            tool_caps=Cursor
            binary_key=CURSOR_BINARY_FOUND
            other1=codex
            other2=claude
            ;;
        codex)
            tool_caps=Codex
            binary_key=CODEX_BINARY_FOUND
            other1=cursor
            other2=claude
            ;;
        *)
            tool_caps=$tool
            binary_key=
            other1=claude
            other2=
            ;;
    esac

    if [ "$binary_found" = "false" ]; then
        larch_err "**⚠ /implement Step 0 (implementer waterfall): --coder=${tool} requested but ${tool_caps} binary not found. Re-run without --coder, or with --coder=${other1}|${other2}.**"
    elif [ -z "$binary_found" ]; then
        larch_err "**⚠ /implement Step 0 (implementer waterfall): --coder=${tool} requested but ${binary_key} could not be determined (Step 0 may have failed). Re-run to re-probe.**"
    else
        larch_err "**⚠ /implement Step 0 (implementer waterfall): --coder=${tool} requested but ${tool_caps} runtime probe failed / auth error. Re-run without --coder, or with --coder=${other1}|${other2}.**"
    fi
    IMPLEMENT_BAIL_REASON="coder-unavailable"
    STALL_TRACKING=true
}

_phase_coder_implicit() {
    # Phase 4 issue #2738 moves /implement's omitted-coder default to
    # Cursor -> Codex -> Claude. Review/fix dispatchers remain Codex-first.
    if [ "${cursor_available:-false}" = "true" ]; then
        coder=cursor
        return 0
    fi

    larch_err "**⚠ Cursor unavailable — falling back to Codex implementer.**"
    _phase_coder_append_warning "Step 0 — Cursor unavailable: waterfall fallback to codex"
    if [ "${codex_available:-false}" = "true" ]; then
        coder=codex
        return 0
    fi

    larch_err "**⚠ Codex unavailable — falling back to Claude implementer.**"
    _phase_coder_append_warning "Step 0 — Cursor and Codex unavailable: waterfall fallback to claude"
    coder=claude
    coder_fallback=true
    _phase_coder_manifest_fallback || true
}

_phase_coder_append_warning() {
    local message=$1 tmpfile
    [ -n "${IMPLEMENT_TMPDIR:-}" ] || return 0
    tmpfile=$(mktemp "${IMPLEMENT_TMPDIR:-${TMPDIR:-/tmp}}/larch-coder-warn.XXXXXX") || return 0
    printf '%s\n' "$message" >"$tmpfile"
    "$SCRIPT_DIR/append-tool-failure.sh" \
        --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
        --site "Step 0 (implementer waterfall)" \
        --tool "phase_coder_select" \
        --exit-code 0 \
        --category Warnings \
        --output-file "$tmpfile" >/dev/null 2>&1 || true
    rm -f "$tmpfile"
}

_phase_coder_manifest_fallback() {
    if [ -z "${RUN_ID:-}" ]; then
        return 0
    fi
    "$SCRIPT_DIR/larch-log.sh" manifest \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --skill implement \
        --run-id "$RUN_ID" \
        --field coder_fallback=true >/dev/null 2>&1 || true
}

emit_coder_breadcrumb_if_enabled() {
    if ! larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}"; then
        return 0
    fi
    if [ -z "${coder:-}" ] || [ -n "${IMPLEMENT_BAIL_REASON:-}" ]; then
        return 0
    fi
    emit_breadcrumb "→ step0: coder=${coder}"
    return 0
}

emit_infra_kv_block() {
    emit_kv CURRENT_BRANCH "${CURRENT_BRANCH:-}"
    emit_kv IS_MAIN "${IS_MAIN:-}"
    emit_kv IS_USER_BRANCH "${IS_USER_BRANCH:-}"
    emit_kv USER_PREFIX "${USER_PREFIX:-}"
    emit_kv ENTRY_GATE "${ENTRY_GATE:-}"
    emit_kv SKIP_BRANCH_CHECK "${SKIP_BRANCH_CHECK:-}"
    emit_kv IMPLEMENT_TMPDIR "${IMPLEMENT_TMPDIR:-}"
    emit_kv SESSION_ID "${SESSION_ID:-}"
    emit_kv CODEX_PRESENT "${CODEX_PRESENT:-}"
    emit_kv CURSOR_PRESENT "${CURSOR_PRESENT:-}"
    emit_kv CODEX_BINARY_FOUND "${CODEX_BINARY_FOUND:-}"
    emit_kv CURSOR_BINARY_FOUND "${CURSOR_BINARY_FOUND:-}"
    emit_kv REPO "${REPO:-}"
    emit_kv REPO_UNAVAILABLE "${REPO_UNAVAILABLE:-}"
    emit_kv CLAUDE_SOURCE_OK "${CLAUDE_SOURCE_OK:-}"
    emit_kv LARCH_TOKEN_SESSION_ID "${LARCH_TOKEN_SESSION_ID:-}"
    emit_kv LARCH_CLAUDE_SOURCE_FILE "${LARCH_CLAUDE_SOURCE_FILE:-}"
    emit_kv LARCH_TIMING_LEDGER "${LARCH_TIMING_LEDGER:-}"
    emit_kv codex_available "${codex_available:-}"
    emit_kv cursor_available "${cursor_available:-}"
}

emit_final_tail() {
    local issue_tail
    emit_infra_kv_block
    case "${BRANCH_SELECTED:-}" in
        forked-target-skip|repo-unavailable-skip)
            issue_tail=""
            ;;
        branch-1-resume|branch-2-adopt)
            issue_tail="${ISSUE_NUMBER_RESOLVED:-}"
            ;;
        *)
            case "${IMPLEMENT_BAIL_REASON:-}" in
                adopted-issue-closed|adopted-issue-is-pr) issue_tail="" ;;
                *) issue_tail="${ISSUE_NUMBER_RESOLVED:-${ISSUE_NUMBER_OPT:-}}" ;;
            esac
            ;;
    esac
    emit_kv ISSUE_NUMBER "$issue_tail"
    emit_kv RUN_ID "${RUN_ID:-}"
    emit_kv BRANCH_SELECTED "${BRANCH_SELECTED:-}"
    emit_kv DEFERRED "${DEFERRED:-false}"
    emit_kv STALL_TRACKING "${STALL_TRACKING:-false}"
    emit_kv BRANCH_NAME "${BRANCH_NAME:-}"
    emit_kv BRANCH_ACTION "${BRANCH_ACTION:-}"
    emit_kv PLAN_FILE "${PLAN_FILE:-}"
    emit_kv EMERGENCY_REQUESTED "${EMERGENCY_REQUESTED:-false}"
    emit_kv coder "${coder:-}"
    emit_kv coder_fallback "${coder_fallback:-}"
    emit_kv IMPLEMENT_BAIL_REASON "${IMPLEMENT_BAIL_REASON:-}"
}

main() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --up-to-phase)
                [ $# -ge 2 ] || die_usage "--up-to-phase requires a value"
                UP_TO_PHASE=$2
                shift 2
                ;;
            --caller-env)
                [ $# -ge 2 ] || die_usage "--caller-env requires a value"
                CALLER_ENV_OPT=$2
                shift 2
                ;;
            --issue-number)
                [ $# -ge 2 ] || die_usage "--issue-number requires a value"
                ISSUE_NUMBER_OPT=$2
                shift 2
                ;;
            --forked-target)
                [ $# -ge 2 ] || die_usage "--forked-target requires a value"
                case "$2" in
                    true|false) FORKED_TARGET=$2 ;;
                    *) die_usage "--forked-target must be true or false" ;;
                esac
                shift 2
                ;;
            --emergency-requested)
                [ $# -ge 2 ] || die_usage "--emergency-requested requires a value"
                case "$2" in
                    true|false) EMERGENCY_REQUESTED=$2; EMERGENCY_REQUESTED_ARG_SEEN=true ;;
                    *) die_usage "--emergency-requested must be true or false" ;;
                esac
                shift 2
                ;;
            --upstream-repo)
                [ $# -ge 2 ] || die_usage "--upstream-repo requires a value"
                UPSTREAM_REPO_OPT=$2
                shift 2
                ;;
            --run-id)
                [ $# -ge 2 ] || die_usage "--run-id requires a value"
                RUN_ID_OPT=$2
                shift 2
                ;;
            --coder)
                [ $# -ge 2 ] || die_usage "--coder requires a value"
                case "$2" in
                    claude|codex|cursor) CODER_OPT=$2 ;;
                    *) die_usage "--coder must be claude, codex, or cursor" ;;
                esac
                shift 2
                ;;
            --preflight-tmpdir)
                [ $# -ge 2 ] || die_usage "--preflight-tmpdir requires a value"
                PREFLIGHT_TMPDIR_OPT=$2
                shift 2
                ;;
            --resume-plan-tail)
                RESUME_PLAN_TAIL=true
                shift
                ;;
            --skip-codex-probe)
                SKIP_CODEX_PROBE_FLAG=true
                shift
                ;;
            --skip-cursor-probe)
                SKIP_CURSOR_PROBE_FLAG=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                die_usage "unknown argument: $1"
                ;;
        esac
    done

    [ -n "$UP_TO_PHASE" ] || die_usage "--up-to-phase is required"
    if [ -n "$ISSUE_NUMBER_OPT" ]; then
        case "$ISSUE_NUMBER_OPT" in
            *[!0-9]*|"") die_usage "--issue-number must be numeric" ;;
        esac
    fi
    if [ -n "$RUN_ID_OPT" ] && ! valid_run_id "$RUN_ID_OPT"; then
        die_usage "--run-id must match ^[A-Za-z0-9._-]+$"
    fi
    if [ -n "$UPSTREAM_REPO_OPT" ]; then
        if [[ ! "$UPSTREAM_REPO_OPT" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
            die_usage "--upstream-repo must be OWNER/REPO"
        fi
    fi
    if [ "$FORKED_TARGET" = "true" ] && [ -n "$UPSTREAM_REPO_OPT" ] && [ -z "$ISSUE_NUMBER_OPT" ]; then
        die_usage "--issue-number is required with --upstream-repo"
    fi
    if [ "$RESUME_PLAN_TAIL" = "true" ]; then
        [ -n "${IMPLEMENT_TMPDIR:-}" ] || die_usage "--resume-plan-tail requires IMPLEMENT_TMPDIR in the environment"
        [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ] || die_usage "--resume-plan-tail requires \$IMPLEMENT_TMPDIR/session-env.sh"
    fi
    case "$UP_TO_PHASE" in
        plan|coder|all)
            if [ -n "$ISSUE_NUMBER_OPT" ] && [ -z "$PREFLIGHT_TMPDIR_OPT" ]; then
                die_usage "--preflight-tmpdir is required with --issue-number when --up-to-phase is plan, coder, or all"
            fi
            ;;
    esac

    phase_infra

    case "$UP_TO_PHASE" in
        infra) ;;
        tracking)
            phase_tracking
            ;;
        plan)
            phase_tracking
            if [ "${REPO_UNAVAILABLE:-false}" = "true" ]; then
                ensure_untracked_baseline_snapshot
            fi
            if should_run_phase_plan_materialize; then
                phase_plan_materialize
            fi
            ;;
        coder)
            phase_tracking
            if [ "${REPO_UNAVAILABLE:-false}" = "true" ]; then
                ensure_untracked_baseline_snapshot
            fi
            if should_run_phase_plan_materialize; then
                phase_plan_materialize
            fi
            if should_run_post_tracking_phase; then
                phase_coder_select
            fi
            ;;
        all)
            phase_tracking
            if [ "${REPO_UNAVAILABLE:-false}" = "true" ]; then
                ensure_untracked_baseline_snapshot
            fi
            if should_run_phase_plan_materialize; then
                phase_plan_materialize
            fi
            if should_run_post_tracking_phase; then
                phase_coder_select
            fi
            ;;
        *)
            die_usage "invalid --up-to-phase: $UP_TO_PHASE (expected infra|tracking|plan|coder|all)"
            ;;
    esac

    emit_final_tail
    exit 0
}

main "$@"
