#!/usr/bin/env bash
# ship-pr.sh — Deterministic /implement post-review state machine.

set -uo pipefail
# Intentionally no `set -e`: this script composes best-effort helpers whose
# outcome is communicated through stdout envelopes. Each helper call captures
# rc explicitly so state can be checkpointed before returning to SKILL.md.
LC_ALL=C
export LC_ALL

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"

STATE_FILE=""
IMPLEMENT_TMPDIR=""
MERGE=""
DRAFT=""
FORKED_TARGET=""
AUTO_MODE="false"
NO_ADMIN_FALLBACK="false"
REPO_ARG=""
RESUME_PHASE=""

usage() {
    cat >&2 <<'USAGE'
Usage:
  ship-pr.sh --state-file PATH --implement-tmpdir PATH --merge true|false --draft true|false --forked true|false --repo OWNER/REPO [--auto-mode true|false] [--no-admin-fallback true|false] [--resume-phase PHASE]
USAGE
}

die_usage() {
    echo "ship-pr.sh: $1" >&2
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
        /tmp/*|/private/tmp/*) return 0 ;;
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
        --repo) [ $# -ge 2 ] || die_usage "--repo requires a value"; REPO_ARG=$2; shift 2 ;;
        --resume-phase) [ $# -ge 2 ] || die_usage "--resume-phase requires a value"; RESUME_PHASE=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) die_usage "unknown option: $1" ;;
    esac
done

[ -n "$STATE_FILE" ] || die_usage "--state-file is required"
[ -n "$IMPLEMENT_TMPDIR" ] || die_usage "--implement-tmpdir is required"
is_tmp_path "$STATE_FILE" || die_usage "--state-file must be under /tmp/, /private/tmp/, or the larch cache sessions root"
is_tmp_path "$IMPLEMENT_TMPDIR" || die_usage "--implement-tmpdir must be under /tmp/, /private/tmp/, or the larch cache sessions root"
[ -d "$IMPLEMENT_TMPDIR" ] || die_usage "--implement-tmpdir must exist"
case "$STATE_FILE" in "$IMPLEMENT_TMPDIR"/*) ;; *) die_usage "--state-file must live under --implement-tmpdir" ;; esac
is_bool "$AUTO_MODE" || die_usage "--auto-mode must be true or false"
is_bool "$NO_ADMIN_FALLBACK" || die_usage "--no-admin-fallback must be true or false"
[ -z "$MERGE" ] || is_bool "$MERGE" || die_usage "--merge must be true or false"
[ -z "$DRAFT" ] || is_bool "$DRAFT" || die_usage "--draft must be true or false"
[ -z "$FORKED_TARGET" ] || is_bool "$FORKED_TARGET" || die_usage "--forked must be true or false"

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

kv_value() {
    local key=$1 input=$2
    printf '%s\n' "$input" | awk -F= -v k="$key" '$1 == k {print substr($0, index($0, "=") + 1); found=1} END {if (!found) print ""}' | tail -n 1
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
    state_set_many STALL_TRACKING true STALL_STEP "$1"
}

exit_stall() {
    mark_stall "$1"
    exit 4
}

write_postbump_state() {
    local tmp
    tmp="$IMPLEMENT_TMPDIR/postbump-state.sh.tmp.$$"
    {
        printf 'BRANCH_NAME=%s\n' "$(read_state BRANCH_NAME)"
        printf 'ISSUE_NUMBER=%s\n' "$(read_state ISSUE_NUMBER)"
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
    local tmp
    tmp="$IMPLEMENT_TMPDIR/finalize-state.sh.tmp.$$"
    {
        printf 'BRANCH_NAME=%s\n' "$(read_state BRANCH_NAME)"
        printf 'PR_NUMBER=%s\n' "$(read_state PR_NUMBER)"
        printf 'PR_TITLE=%s\n' "$(read_state PR_TITLE)"
        printf 'PR_URL=%s\n' "$(read_state PR_URL)"
        printf 'ISSUE_NUMBER=%s\n' "$(read_state ISSUE_NUMBER)"
        printf 'REPO=%s\n' "$(read_state REPO)"
        printf 'DRAFT=%s\n' "$(read_state DRAFT)"
        printf 'MERGE=%s\n' "$(read_state MERGE)"
        printf 'DEFERRED=%s\n' "$(read_state DEFERRED)"
        printf 'REPO_UNAVAILABLE=%s\n' "$(read_state REPO_UNAVAILABLE)"
        printf 'PR_CLOSED=%s\n' "$(read_state PR_CLOSED)"
        printf 'DESIGN_ONLY_DONE=%s\n' "$(read_state DESIGN_ONLY_DONE false)"
        printf 'BAIL_NEEDS_USER_INPUT=%s\n' "$(read_state BAIL_NEEDS_USER_INPUT)"
        printf 'STALL_TRACKING=%s\n' "$(read_state STALL_TRACKING)"
        printf 'STALL_STEP=%s\n' "$(read_state STALL_STEP)"
        printf 'DONE_RENAME_APPLIED=%s\n' "$(read_state DONE_RENAME_APPLIED)"
        printf 'RUN_ID=%s\n' "$(read_state RUN_ID)"
        printf 'EXPECTED_SESSION_ID=%s\n' "$(read_state EXPECTED_SESSION_ID)"
        printf 'EXPECTED_TMPDIR_BASENAME_PREFIX=%s\n' "$(read_state EXPECTED_TMPDIR_BASENAME_PREFIX)"
    } > "$tmp" && mv "$tmp" "$IMPLEMENT_TMPDIR/finalize-state.sh"
    printf '%s' "$(read_state BAIL_REASON)" > "$IMPLEMENT_TMPDIR/final-bail-reason.txt"
}

run_checks_phase() {
    local out rc
    out=$("$SCRIPT_DIR/run-relevant-checks-captured.sh" --site step6 --tmpdir "$IMPLEMENT_TMPDIR" 2>&1)
    rc=$?
    printf '%s\n' "$out"
    if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -q '^RELEVANT_CHECKS_OK=true '; then
        advance_phase bump
        return 0
    fi
    exit_stall 6
}

run_bump_phase() {
    local forked has_bump commits_before classify_out apply_out finalize_out status resume_phase error_text rc
    forked=$(read_state FORKED_TARGET)
    has_bump=$(read_state HAS_BUMP)
    if [ "$forked" = "true" ] || [ "$has_bump" = "false" ]; then
        state_set_many HAS_BUMP false BUMP_TYPE NONE NEW_VERSION "" BUMP_REASONING_FILE ""
    else
        commits_before=$(git rev-list --count HEAD 2>/dev/null || echo 0)
        classify_out=$("$PLUGIN_ROOT/.claude/skills/bump-version/scripts/classify-bump.sh" 2>&1)
        rc=$?
        printf '%s\n' "$classify_out"
        [ "$rc" -eq 0 ] || exit_stall 8
        state_set_many \
            HAS_BUMP true \
            BUMP_TYPE "$(kv_value BUMP_TYPE "$classify_out")" \
            NEW_VERSION "$(kv_value NEW_VERSION "$classify_out")" \
            BUMP_REASONING_FILE "$(kv_value REASONING_FILE "$classify_out")"
        if [ "$(read_state BUMP_TYPE)" != "NONE" ]; then
            apply_out=$("$PLUGIN_ROOT/.claude/skills/bump-version/scripts/apply-bump.sh" --new-version "$(read_state NEW_VERSION)" 2>&1)
            rc=$?
            printf '%s\n' "$apply_out"
            if [ "$rc" -ne 0 ] || [ "$(kv_value APPLIED "$apply_out")" != "true" ]; then
                error_text=$(kv_value ERROR "$apply_out")
                case "$error_text" in
                    origin/main\ has\ already\ bumped\ to*)
                        state_set_many RESUME_PHASE bump CALLER_KIND step8b_same_version
                        exit 5
                        ;;
                    *) exit_stall 8 ;;
                esac
            fi
            "$SCRIPT_DIR/check-bump-version.sh" --mode post --before-count "$commits_before" || exit_stall 8
        fi
    fi

    write_postbump_state
    finalize_out=$("$SCRIPT_DIR/implement-finalize.sh" postbump --state-file "$IMPLEMENT_TMPDIR/postbump-state.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" 2>&1)
    printf '%s\n' "$finalize_out"
    status=$(kv_value STATUS "$finalize_out")
    case "$status" in
        ok|skipped)
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
    local file=$1 placeholder=$2 label=$3 out reason
    if [ -n "$file" ] && [ -f "$file" ]; then
        out=$("$SCRIPT_DIR/sanitize-mermaid-fragment.sh" --input "$file" --from-md --warnings-step "9a" 2>&1)
        if printf '%s\n' "$out" | grep -q '^STATUS=ok$'; then
            cat "$file"
            return 0
        fi
        reason=$(kv_value REASON_TOKEN "$out")
        [ -n "$reason" ] || reason="unknown"
        "$SCRIPT_DIR/append-execution-issue.sh" --log "$IMPLEMENT_TMPDIR/execution-issues.md" --category Warnings --entry "Step 9a — PR-body diagram $label rejected: $reason" >/dev/null 2>&1 || true
    fi
    printf '%s\n' "$placeholder"
}

run_pr_prep_phase() {
    local summary tests closes architecture_file code_flow_file
    summary=$(manifest_summary)
    [ -n "$summary" ] || summary="- Implemented the requested changes."
    tests=$(manifest_tests)
    [ -n "$tests" ] || tests="- [x] Ran relevant checks."
    architecture_file="${ARCHITECTURE_DIAGRAM_FILE:-}"
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
    local title out rc pr_number pr_url pr_status repo_args draft_args
    title=$(git log -1 --format=%s 2>/dev/null || echo "Implement requested changes")
    repo_args=()
    if [ -n "$(read_state REPO)" ]; then
        repo_args=(--repo "$(read_state REPO)")
    fi
    draft_args=()
    [ "$(read_state DRAFT)" = "true" ] && draft_args=(--draft)
    out=$("$SCRIPT_DIR/create-pr.sh" --title "$title" --body-file "$IMPLEMENT_TMPDIR/pr-body.md" "${draft_args[@]+"${draft_args[@]}"}" "${repo_args[@]+"${repo_args[@]}"}" 2>&1)
    rc=$?
    printf '%s\n' "$out"
    [ "$rc" -eq 0 ] || exit_stall 9b
    pr_number=$(kv_value PR_NUMBER "$out")
    pr_url=$(kv_value PR_URL "$out")
    pr_status=$(kv_value PR_STATUS "$out")
    state_set_many PR_NUMBER "$pr_number" PR_URL "$pr_url" PR_TITLE "$title"
    if [ "$pr_status" = "existing" ]; then
        "$SCRIPT_DIR/gh-pr-body-update.sh" --pr "$pr_number" --body-file "$IMPLEMENT_TMPDIR/pr-body.md" "${repo_args[@]+"${repo_args[@]}"}" || true
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
    local issue repo
    issue=$(read_state ISSUE_NUMBER)
    repo=$(read_state REPO)
    [ -n "$issue" ] || return 0
    [ "$(read_state REPO_UNAVAILABLE)" = "false" ] || return 0
    if [ -n "$repo" ]; then
        "$SCRIPT_DIR/tracking-issue-write.sh" rename --issue "$issue" --state "done" --round-trip false --repo "$repo" >/dev/null 2>&1 || true
    else
        "$SCRIPT_DIR/tracking-issue-write.sh" rename --issue "$issue" --state "done" --round-trip false >/dev/null 2>&1 || true
    fi
    state_set DONE_RENAME_APPLIED true
}

run_ci_fix_vendor() {
    local phase=$1 run_id=$2 output rc checks_out
    output="$IMPLEMENT_TMPDIR/ci-fix-${phase}-$(date +%s).out"
    if command -v cursor >/dev/null 2>&1; then
        "$SCRIPT_DIR/launch-cursor-ci.sh" --role fix --output "$output" --run-id "$run_id" --repo "$(read_state REPO)" --timeout 1800 || true
    else
        "$SCRIPT_DIR/launch-codex-ci.sh" --role fix --output "$output" --run-id "$run_id" --repo "$(read_state REPO)" --timeout 1800 || true
    fi
    "$SCRIPT_DIR/append-token-record.sh" --input "${output}.token-record" --tmpdir "$IMPLEMENT_TMPDIR" || true
    checks_out=$("$SCRIPT_DIR/run-relevant-checks-captured.sh" --site "$([ "$phase" = "ci-initial" ] && echo step10 || echo step12c)" --tmpdir "$IMPLEMENT_TMPDIR" 2>&1)
    rc=$?
    printf '%s\n' "$checks_out"
    [ "$rc" -eq 0 ] && printf '%s\n' "$checks_out" | grep -q '^RELEVANT_CHECKS_OK=true ' || return 1
    "$SCRIPT_DIR/git-commit.sh" -m "Fix CI failure" || return 1
    "$SCRIPT_DIR/git-push.sh" || return 1
}

run_evaluate_failure() {
    local phase=$1 failed_run rerun_out retries
    failed_run=$(read_state FAILED_RUN_ID)
    [ -n "$failed_run" ] || exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12c)"
    retries=$(read_state TRANSIENT_RETRIES)
    if [ "$retries" -lt 2 ]; then
        rerun_out=$("$SCRIPT_DIR/ci-rerun-failed.sh" --run-id "$failed_run" --repo "$(read_state REPO)" 2>&1)
        printf '%s\n' "$rerun_out"
        if [ "$(kv_value RERUN_SUBMITTED "$rerun_out")" = "true" ]; then
            state_set TRANSIENT_RETRIES "$((retries + 1))"
            return 0
        fi
    fi
    "$SCRIPT_DIR/gh-run-logs.sh" --run-id "$failed_run" --repo "$(read_state REPO)" || true
    run_ci_fix_vendor "$phase" "$failed_run" || exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12c)"
    state_set_many TRANSIENT_RETRIES 0 FIX_ATTEMPTS "$(( $(read_state FIX_ATTEMPTS) + 1 ))"
}

run_ci_phase() {
    local phase=$1 out action bail_reason merge_out merge_result error_text rc ci_args merge_args
    if [ "$(read_state REPO_UNAVAILABLE)" = "true" ] || [ -z "$(read_state PR_NUMBER)" ]; then
        if [ "$phase" = "ci-initial" ]; then
            advance_phase ci-merge
        else
            advance_phase postmerge
        fi
        return 0
    fi
    # Flush pending larch-log writes (version-bump-reasoning, oos-issues,
    # execution-issues, etc.) before merge so they land in the PR. The
    # rebase-rebump sub-procedure (step 1b) already does this on any rebase
    # path; this covers the happy path where no rebase was needed.
    if [ "$phase" = "ci-merge" ]; then
        local flush_run_id
        flush_run_id=$(read_state RUN_ID)
        if [ -n "$flush_run_id" ]; then
            "$SCRIPT_DIR/larch-log.sh" commit --skill implement --run-id "$flush_run_id" 2>/dev/null || true
        fi
    fi

    if [ "$phase" = "ci-merge" ] && { [ "$(read_state MERGE)" != "true" ] || [ "$(read_state DRAFT)" = "true" ] || [ "$(read_state FORKED_TARGET)" = "true" ]; }; then
        advance_phase postmerge
        return 0
    fi

    ci_args=()
    while IFS= read -r arg; do ci_args+=("$arg"); done <<EOF
$(ci_common_args)
EOF
    out=$("$SCRIPT_DIR/ci-wait.sh" "${ci_args[@]}" 2>&1)
    rc=$?
    printf '%s\n' "$out"
    [ "$rc" -eq 0 ] || exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
    record_ci_counters "$out"
    action=$(kv_value ACTION "$out")
    case "$action" in
        merge)
            if [ "$phase" = "ci-initial" ]; then
                state_set CI_PASSED true
                advance_phase ci-merge
                exit 0
            fi
            merge_args=(--pr "$(read_state PR_NUMBER)" --repo "$(read_state REPO)")
            [ "$NO_ADMIN_FALLBACK" = "true" ] && merge_args+=(--no-admin-fallback)
            merge_out=$("$SCRIPT_DIR/merge-pr.sh" "${merge_args[@]}" 2>&1)
            printf '%s\n' "$merge_out"
            merge_result=$(kv_value MERGE_RESULT "$merge_out")
            error_text=$(kv_value ERROR "$merge_out")
            case "$merge_result" in
                merged|admin_merged)
                    state_set PR_CLOSED true
                    rename_done_best_effort
                    advance_phase postmerge
                    ;;
                main_advanced|ci_not_ready)
                    return 0
                    ;;
                version_already_published|policy_denied|admin_failed|error)
                    state_set_many BAIL_REASON "$error_text" STALL_TRACKING true STALL_STEP 12d
                    exit 4
                    ;;
                *) exit_stall 12b ;;
            esac
            ;;
        rebase)
            if [ "$(read_state FORKED_TARGET)" = "true" ]; then
                "$SCRIPT_DIR/rebase-push.sh" --base-remote upstream --base-ref main || exit_stall "$([ "$phase" = "ci-initial" ] && echo 10 || echo 12)"
                state_set_many REBASE_COUNT "$(( $(read_state REBASE_COUNT) + 1 ))" ITERATION "$(( $(read_state ITERATION) + 1 ))" TRANSIENT_RETRIES 0
                return 0
            fi
            state_set_many RESUME_PHASE "$phase" CALLER_KIND "$([ "$phase" = "ci-initial" ] && echo step10_rebase || echo step12_rebase)"
            exit 5
            ;;
        rebase_then_evaluate)
            state_set_many RESUME_PHASE evaluate-failure CALLER_KIND "$([ "$phase" = "ci-initial" ] && echo step10_rebase_then_evaluate || echo step12_rebase_then_evaluate)"
            exit 5
            ;;
        already_merged)
            state_set PR_CLOSED true
            rename_done_best_effort
            advance_phase postmerge
            ;;
        evaluate_failure)
            run_evaluate_failure "$phase"
            ;;
        bail)
            bail_reason=$(kv_value BAIL_REASON "$out")
            state_set BAIL_REASON "$bail_reason"
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
    local issue_number repo repo_unavailable forked run_id stall_tracking pr_url
    local token_session source_file
    write_finalize_state
    "$SCRIPT_DIR/implement-finalize.sh" postmerge --state-file "$IMPLEMENT_TMPDIR/finalize-state.sh" --final-bail-reason-file "$IMPLEMENT_TMPDIR/final-bail-reason.txt"

    issue_number=$(read_state ISSUE_NUMBER)
    repo=$(read_state REPO)
    repo_unavailable=$(read_state REPO_UNAVAILABLE)
    forked=$(read_state FORKED_TARGET)
    run_id=$(read_state RUN_ID)
    stall_tracking=$(read_state STALL_TRACKING)
    pr_url=$(read_state PR_URL)
    token_session=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "" 2>/dev/null || true)
    source_file=$("$SCRIPT_DIR/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_CLAUDE_SOURCE_FILE --default "" 2>/dev/null || true)
    export LARCH_TOKEN_SESSION_ID=$token_session LARCH_CLAUDE_SOURCE_FILE=$source_file
    "$SCRIPT_DIR/token-report.sh" --full --output "$IMPLEMENT_TMPDIR/token-report-rendered.md" 2>/dev/null || true
    if [ "$forked" != "true" ] && [ -n "$issue_number" ] && [ "$repo_unavailable" != "true" ]; then
        printf 'Status: %s | PR: %s\nLogs: larch-logs/implement/%s/\n' \
            "$stall_tracking" "${pr_url:-N/A}" "$run_id" > "$IMPLEMENT_TMPDIR/summary-final.md"
        "$SCRIPT_DIR/tracking-issue-summary.sh" upsert-summary \
            --issue "$issue_number" \
            --marker "<!-- larch:final-summary v1 runid=${run_id} -->" \
            --content-file "$IMPLEMENT_TMPDIR/summary-final.md" \
            --repo "$repo" 2>/dev/null || true
    fi
    advance_phase "done"
    "$SCRIPT_DIR/implement-finalize.sh" teardown --state-file "$IMPLEMENT_TMPDIR/finalize-state.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"
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
