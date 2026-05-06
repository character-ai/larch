#!/usr/bin/env bash
# implement-finalize.sh — Mechanical finalizer for /implement Steps 14, 15, 16a, and 18.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

STATE_FILE=""
FINAL_BAIL_REASON_FILE=""
IMPLEMENT_TMPDIR=""
WARNINGS=0

usage() {
    cat >&2 <<'USAGE'
Usage:
  implement-finalize.sh postmerge --state-file PATH --final-bail-reason-file PATH
  implement-finalize.sh slack     --state-file PATH --final-bail-reason-file PATH
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
    case "$1" in
        /tmp/*|/private/tmp/*) return 0 ;;
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

validate_common_state_args() {
    [ -n "$STATE_FILE" ] || die_usage "--state-file is required"
    is_tmp_path "$STATE_FILE" || die_usage "--state-file must be under /tmp/ or /private/tmp/"
    [ -r "$STATE_FILE" ] || die_usage "--state-file must exist and be readable"
}

validate_bail_file_arg() {
    [ -n "$FINAL_BAIL_REASON_FILE" ] || die_usage "--final-bail-reason-file is required"
    is_tmp_path "$FINAL_BAIL_REASON_FILE" || die_usage "--final-bail-reason-file must be under /tmp/ or /private/tmp/"
}

validate_tmpdir_arg() {
    [ -n "$IMPLEMENT_TMPDIR" ] || die_usage "--implement-tmpdir is required"
    is_tmp_path "$IMPLEMENT_TMPDIR" || die_usage "--implement-tmpdir must be under /tmp/ or /private/tmp/"
    case "$STATE_FILE" in
        "$IMPLEMENT_TMPDIR"/*) ;;
        *) die_usage "--state-file must live under --implement-tmpdir for teardown" ;;
    esac
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
        DRAFT MERGE SLACK_ENABLED SLACK_AVAILABLE DEFERRED REPO_UNAVAILABLE \
        PR_CLOSED DESIGN_ONLY_DONE BAIL_NEEDS_USER_INPUT STALL_TRACKING DONE_RENAME_APPLIED
    do
        state_has_key "$key" || die_usage "state-file missing required key: $key"
    done
}

require_bool_state() {
    local key value
    for key in \
        DRAFT MERGE SLACK_ENABLED SLACK_AVAILABLE DEFERRED REPO_UNAVAILABLE \
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
        printf '⏭️ 14: local cleanup — skipped (--draft set, staying on %s for further iteration) (%s)\n' "$branch" "$(elapsed "$start")"
        local_status=skipped-draft
    elif [ "$merge" != "true" ]; then
        printf '⏭️ 14: local cleanup — skipped (--merge not set), still on %s (%s)\n' "$branch" "$(elapsed "$start")"
        local_status=skipped-merge-false
    elif bail_reason_nonempty; then
        warn_line "$(printf '**⚠ 14: local cleanup — skipped (PR not merged), still on %s (%s)**' "$branch" "$(elapsed "$start")")"
        local_status=skipped-bail
    else
        [ -n "$branch" ] || die_usage "state-file key BRANCH_NAME must be non-empty for postmerge cleanup"
        [ "$branch" != "main" ] || die_usage "state-file key BRANCH_NAME must not be main"

        set +e
        out=$("$SCRIPT_DIR/local-cleanup.sh" --branch "$branch")
        rc=$?
        set -e
        cleanup_success=$(kv_value CLEANUP_SUCCESS "$out")
        current_branch=$(kv_value CURRENT_BRANCH "$out")
        branch_deleted=$(kv_value BRANCH_DELETED "$out")

        if [ "$rc" -eq 0 ] && [ "$cleanup_success" = "true" ]; then
            printf '✅ 14: local cleanup — switched to main, deleted %s (%s)\n' "$branch" "$(elapsed "$start")"
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
        set -e
        verified=$(kv_value VERIFIED "$out")
        commit_hash=$(kv_value COMMIT_HASH "$out")
        commit_message=$(kv_value COMMIT_MESSAGE "$out")
        if [ "$rc" -eq 0 ] && [ "$verified" = "true" ]; then
            printf '✅ 15: verify main — at %s "%s" (%s)\n' "$commit_hash" "$commit_message" "$(elapsed "$start")"
            verify_status=verified
        else
            warn_line "$(printf '**⚠ 15: verify main — unexpected HEAD: %s "%s". Expected: "%s" (%s)**' "$commit_hash" "$commit_message" "$expected_title" "$(elapsed "$start")")"
            verify_status=unexpected
        fi
    fi

    echo "LOCAL_CLEANUP_STATUS=$local_status"
    echo "VERIFY_MAIN_STATUS=$verify_status"
    echo "FINALIZE_SUBCOMMAND=postmerge"
    echo "FINALIZE_WARNINGS=$WARNINGS"
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

run_slack() {
    local start slack_enabled slack_available deferred repo_unavailable issue_number
    local repo pr_url run_outcome detail out rc slack_ts args

    start=$(date +%s)
    validate_bail_file_arg
    load_and_validate_state

    slack_enabled=$(read_state SLACK_ENABLED)
    slack_available=$(read_state SLACK_AVAILABLE)
    deferred=$(read_state DEFERRED)
    repo_unavailable=$(read_state REPO_UNAVAILABLE)
    issue_number=$(read_state ISSUE_NUMBER)
    repo=$(read_state REPO)
    pr_url=$(read_state PR_URL)
    run_outcome=$(compute_run_outcome)
    slack_ts=""

    if [ "$slack_enabled" = "false" ]; then
        printf '⏭️ 16a: slack issue post — skipped (--no-slack) (%s)\n' "$(elapsed "$start")"
    elif [ "$slack_available" = "false" ]; then
        printf '⏭️ 16a: slack issue post — skipped (Slack not configured) (%s)\n' "$(elapsed "$start")"
    elif [ "$deferred" = "true" ] || [ -z "$issue_number" ]; then
        printf '⏭️ 16a: slack issue post — skipped (no tracking issue) (%s)\n' "$(elapsed "$start")"
    elif [ "$repo_unavailable" = "true" ]; then
        printf '⏭️ 16a: slack issue post — skipped (repo unavailable) (%s)\n' "$(elapsed "$start")"
    else
        args=("$SCRIPT_DIR/post-issue-slack.sh" --issue-number "$issue_number" --status "$run_outcome" --repo "$repo")
        if [ "$run_outcome" != "design-only" ] && [ -n "$pr_url" ]; then
            args=("${args[@]}" --pr-url "$pr_url")
        fi
        if [ "$run_outcome" = "blocked" ] && bail_reason_nonempty; then
            detail=$(normalized_bail_reason)
            args=("${args[@]}" --detail "$detail")
        elif [ "$run_outcome" = "user-input" ]; then
            args=("${args[@]}" --detail "conflict resolution needs user input (auto-mode bail)")
        fi

        set +e
        out=$("${args[@]}")
        rc=$?
        set -e
        slack_ts=$(kv_value SLACK_TS "$out")
        if [ "$rc" -ne 0 ] || [ -z "$slack_ts" ]; then
            warn_line '**⚠ 16a: slack issue post — failed. Continuing.**'
        else
            printf '✅ 16a: slack issue post — posted (%s)\n' "$(elapsed "$start")"
        fi
    fi

    echo "RUN_OUTCOME=$run_outcome"
    echo "SLACK_TS=$slack_ts"
    echo "FINALIZE_SUBCOMMAND=slack"
    echo "FINALIZE_WARNINGS=$WARNINGS"
}

rename_issue() {
    local issue=$1 state=$2 label=$3 repo=$4 out rc failed round_trip body_tmp title
    round_trip=false
    body_tmp=""
    title=""
    if [ -n "$IMPLEMENT_TMPDIR" ] && is_tmp_path "$IMPLEMENT_TMPDIR" && [ -d "$IMPLEMENT_TMPDIR" ]; then
        body_tmp="$IMPLEMENT_TMPDIR/round-trip-input-issue-body-step18-${issue}.txt"
    else
        body_tmp=$(mktemp)
    fi
    # Build gh args; pass --repo when available so the body+title fetch
    # targets the same issue scope as the rename call below (FINDING_F2).
    set +e
    if [ -n "$repo" ]; then
        out=$(gh issue view "$issue" --repo "$repo" --json title,body --jq '"TITLE=\(.title // "")\n" + (.body // "")')
    else
        out=$(gh issue view "$issue" --json title,body --jq '"TITLE=\(.title // "")\n" + (.body // "")')
    fi
    rc=$?
    set -e
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
        set -e
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
    out=$("$SCRIPT_DIR/tracking-issue-write.sh" rename --issue "$issue" --state "$state" --round-trip "$round_trip")
    rc=$?
    set -e
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
    set -e
    if [ "$rc" -ne 0 ] || [ -z "$repo_root" ]; then
        warn_line '**⚠ 18: auto-stash failed: could not resolve repo root. Continuing.**'
        return 0
    fi

    set +e
    status_out=$(git -C "$repo_root" status --porcelain 2>/dev/null)
    rc=$?
    set -e
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
    set -e
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
    set -e
    if [ "$rc" -ne 0 ] || [ -z "$stash_ref" ]; then
        # Fallback to the previous heuristic; emit a warning so a missing or
        # mismatched ref is observable.
        set +e
        stash_ref=$(git -C "$repo_root" stash list -1 --format='%gD' 2>/dev/null)
        rc=$?
        set -e
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
    set -e
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

run_teardown() {
    local start issue_number repo repo_unavailable stall_tracking done_rename_applied pr_number design_only
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
            set -e
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
        set -e
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

    set +e
    out=$("$SCRIPT_DIR/cleanup-tmpdir.sh" --dir "$IMPLEMENT_TMPDIR")
    cleanup_rc=$?
    set -e
    if [ "$cleanup_rc" -ne 0 ]; then
        warn_line '**⚠ 18: cleanup-tmpdir failed. Continuing.**'
    fi

    if [ -n "$issue_url" ]; then
        printf '📎 Tracking issue: %s\n' "$issue_url"
    fi

    printf '✅ 18: cleanup — implement complete! (%s)\n' "$(elapsed "$start")"
    echo "RENAME_BRANCH=$rename_branch"
    echo "RENAME_STATUS=$rename_status"
    echo "ISSUE_URL=$issue_url"
    echo "STASH_REF=$stash_ref"
    echo "SENTINEL_WRITTEN=$sentinel_written"
    echo "FINALIZE_SUBCOMMAND=teardown"
    echo "FINALIZE_WARNINGS=$WARNINGS"
}

main() {
    local subcommand
    [ $# -gt 0 ] || die_usage "missing subcommand"
    subcommand=$1
    shift
    parse_common_args "$@"

    case "$subcommand" in
        postmerge) run_postmerge ;;
        slack) run_slack ;;
        teardown) run_teardown ;;
        *) die_usage "unknown subcommand: $subcommand" ;;
    esac
}

main "$@"
