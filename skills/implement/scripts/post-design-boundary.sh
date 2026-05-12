#!/usr/bin/env bash
# post-design-boundary.sh — Mechanical gate immediately after /design returns.

set -euo pipefail

# shellcheck disable=SC2317
on_err() {
    echo "MANIFEST_FAILED=true"
    echo "ERROR=internal-error"
    exit 0
}
trap on_err ERR

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$REPO_ROOT}"

IMPLEMENT_TMPDIR=""
SESSION_ENV_PATH=""
DESIGN_ONLY=false
HOOK_MODE=false

fail_closed() {
    echo "MANIFEST_FAILED=true"
    echo "ERROR=$1"
    exit 0
}

has_control_char() {
    local value="$1"
    case "$value" in
        *$'\001'*|*$'\002'*|*$'\003'*|*$'\004'*|*$'\005'*|*$'\006'*|*$'\007'*|*$'\010'*|*$'\011'*|*$'\012'*|*$'\013'*|*$'\014'*|*$'\015'*|*$'\016'*|*$'\017'*|*$'\020'*|*$'\021'*|*$'\022'*|*$'\023'*|*$'\024'*|*$'\025'*|*$'\026'*|*$'\027'*|*$'\030'*|*$'\031'*|*$'\032'*|*$'\033'*|*$'\034'*|*$'\035'*|*$'\036'*|*$'\037'*|*$'\177'*)
            return 0
            ;;
    esac
    return 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --implement-tmpdir)
            [[ $# -ge 2 ]] || fail_closed "missing-implement-tmpdir"
            IMPLEMENT_TMPDIR="$2"
            shift 2
            ;;
        --session-env)
            [[ $# -ge 2 ]] || fail_closed "missing-session-env"
            SESSION_ENV_PATH="$2"
            shift 2
            ;;
        --design-only)
            [[ $# -ge 2 ]] || fail_closed "missing-design-only"
            DESIGN_ONLY="$2"
            shift 2
            ;;
        --hook-mode)
            [[ $# -ge 2 ]] || fail_closed "missing-hook-mode"
            HOOK_MODE="$2"
            shift 2
            ;;
        *)
            fail_closed "unknown-flag"
            ;;
    esac
done

case "$DESIGN_ONLY" in
    true|false) ;;
    *) fail_closed "invalid-design-only" ;;
esac
case "$HOOK_MODE" in
    true|false) ;;
    *) fail_closed "invalid-hook-mode" ;;
esac

if [[ -z "$IMPLEMENT_TMPDIR" || "$IMPLEMENT_TMPDIR" != /* ]] || has_control_char "$IMPLEMENT_TMPDIR" || [[ ! -d "$IMPLEMENT_TMPDIR" ]]; then
    fail_closed "invalid-tmpdir"
fi
if [[ -n "$SESSION_ENV_PATH" ]]; then
    if [[ "$SESSION_ENV_PATH" != /* ]] || has_control_char "$SESSION_ENV_PATH"; then
        fail_closed "invalid-session-env"
    fi
fi

READER_OUT=$("$PLUGIN_ROOT/skills/design/scripts/read-design-manifest.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" --emit-load-breadcrumb)
if printf '%s\n' "$READER_OUT" | grep -q '^MANIFEST_FAILED=true$'; then
    printf '%s\n' "$READER_OUT"
    exit 0
fi
if ! printf '%s\n' "$READER_OUT" | grep -q '^MANIFEST_OK=true$'; then
    fail_closed "manifest-reader-no-status"
fi

WARNINGS=""

append_warning() {
    WARNINGS+="WARN=$1"$'\n'
}

parse_session_env_key() {
    local file="$1"
    local wanted="$2"
    local line key value
    [[ -f "$file" ]] || return 0
    while IFS= read -r line || [[ -n "$line" ]]; do
        case "$line" in
            *=*) ;;
            *) continue ;;
        esac
        key=${line%%=*}
        value=${line#*=}
        [[ "$key" = "$wanted" ]] || continue
        printf '%s\n' "$value"
        return 0
    done < "$file"
}

read_health_sidecar_value() {
    local file="$1"
    local wanted="$2"
    local line key value
    [[ -f "$file" ]] || return 0
    while IFS= read -r line || [[ -n "$line" ]]; do
        case "$line" in
            *=*) ;;
            *) continue ;;
        esac
        key=${line%%=*}
        value=${line#*=}
        [[ "$key" = "$wanted" ]] || continue
        case "$value" in
            true|false)
                printf '%s\n' "$value"
                return 0
                ;;
            *)
                printf '%s\n' "__INVALID__"
                return 0
                ;;
        esac
    done < "$file"
}

health_merge() {
    local sidecar="${SESSION_ENV_PATH}.health"
    local repo repo_unavailable
    local cur_codex cur_cursor cur_gemini cur_timing_ledger cur_token_session_id cur_claude_source_file
    local side_codex side_cursor side_gemini
    local merged_codex merged_cursor merged_gemini
    local flipped=false

    [[ -n "$SESSION_ENV_PATH" && -f "$sidecar" ]] || return 0

    repo=$(parse_session_env_key "$SESSION_ENV_PATH" "REPO")
    repo_unavailable=$(parse_session_env_key "$SESSION_ENV_PATH" "REPO_UNAVAILABLE")

    cur_codex=$(parse_session_env_key "$SESSION_ENV_PATH" "CODEX_HEALTHY")
    cur_cursor=$(parse_session_env_key "$SESSION_ENV_PATH" "CURSOR_HEALTHY")
    cur_gemini=$(parse_session_env_key "$SESSION_ENV_PATH" "GEMINI_HEALTHY")
    cur_timing_ledger=$(parse_session_env_key "$SESSION_ENV_PATH" "LARCH_TIMING_LEDGER")
    cur_token_session_id=$(parse_session_env_key "$SESSION_ENV_PATH" "LARCH_TOKEN_SESSION_ID")
    cur_claude_source_file=$(parse_session_env_key "$SESSION_ENV_PATH" "LARCH_CLAUDE_SOURCE_FILE")
    [[ -z "$cur_timing_ledger" ]] && cur_timing_ledger="$IMPLEMENT_TMPDIR/timing-ledger.tsv"

    side_codex=$(read_health_sidecar_value "$sidecar" "CODEX_HEALTHY")
    side_cursor=$(read_health_sidecar_value "$sidecar" "CURSOR_HEALTHY")
    side_gemini=$(read_health_sidecar_value "$sidecar" "GEMINI_HEALTHY")
    if [[ "$side_codex" = "__INVALID__" ]]; then
        append_warning "health-value-invalid:CODEX_HEALTHY"
        side_codex="$cur_codex"
    fi
    if [[ "$side_cursor" = "__INVALID__" ]]; then
        append_warning "health-value-invalid:CURSOR_HEALTHY"
        side_cursor="$cur_cursor"
    fi
    if [[ "$side_gemini" = "__INVALID__" ]]; then
        append_warning "health-value-invalid:GEMINI_HEALTHY"
        side_gemini="$cur_gemini"
    fi

    merged_codex="$cur_codex"
    merged_cursor="$cur_cursor"
    merged_gemini="$cur_gemini"
    [[ -z "$merged_codex" ]] && merged_codex=true
    [[ -z "$merged_cursor" ]] && merged_cursor=true
    [[ -z "$merged_gemini" ]] && merged_gemini=true

    if [[ "$cur_codex" = false || "$side_codex" = false ]]; then merged_codex=false; fi
    if [[ "$cur_cursor" = false || "$side_cursor" = false ]]; then merged_cursor=false; fi
    if [[ "$cur_gemini" = false || "$side_gemini" = false ]]; then merged_gemini=false; fi

    if [[ "$cur_codex" != "$merged_codex" || "$cur_cursor" != "$merged_cursor" || "$cur_gemini" != "$merged_gemini" ]]; then
        flipped=true
    fi

    if [[ "$flipped" = true ]]; then
        local write_args=(
            --output "$SESSION_ENV_PATH"
            --repo "$repo"
            --repo-unavailable "$repo_unavailable"
            --codex-healthy "$merged_codex"
            --cursor-healthy "$merged_cursor"
            --gemini-healthy "$merged_gemini"
            --timing-ledger "$cur_timing_ledger"
        )
        [[ -n "$cur_token_session_id" ]] && write_args+=(--token-session-id "$cur_token_session_id")
        [[ -n "$cur_claude_source_file" ]] && write_args+=(--claude-source-file "$cur_claude_source_file")
        if ! "$PLUGIN_ROOT/scripts/write-session-env.sh" "${write_args[@]}" >/dev/null 2>&1; then
            append_warning "health-merge-failed"
        fi
    fi
}

health_merge

capture_branch_once() {
    local out branch
    out=$("$PLUGIN_ROOT/scripts/git-current-branch.sh" 2>/dev/null) || return 1
    branch=$(printf '%s\n' "$out" | awk -F= '/^BRANCH=/{print substr($0, 8); exit}')
    [[ -n "$branch" ]] || return 1
    printf '%s\n' "$branch"
}

BRANCH=""
if ! BRANCH=$(capture_branch_once); then
    if ! BRANCH=$(capture_branch_once); then
        fail_closed "branch-capture-failed"
    fi
fi

if [[ "$HOOK_MODE" = true ]]; then
    # Hook-mode: do NOT create .boundary-gate-passed. The Stop hook blocks when
    # the sentinel is absent, so skipping the touch here ensures that if the
    # orchestrator ignores the injected directive and halts, the Stop hook fires
    # and blocks the session. The orchestrator's mandatory Bash call (non-hook-mode)
    # is the load-bearing gate that creates the sentinel.
    # All hard gates passed — emit success envelope immediately (no late-failure path).
    printf '%s\n' "$READER_OUT"
    printf 'BRANCH=%s\n' "$BRANCH"
    if [[ "$DESIGN_ONLY" = true ]]; then
        echo "NEXT_ACTION=plan-goals-test-and-plan-review-tally-then-diagrams-then-step-9a1"
    else
        echo "NEXT_ACTION=larch-log-batches-then-1r-then-step2"
    fi
    echo "POST_DESIGN_BOUNDARY_HOOK_INJECTED=true"
    printf '%s' "$WARNINGS"
    if [[ "$DESIGN_ONLY" = true ]]; then
        echo "➡️ 1: design plan — hook injected boundary context (design-only); NEXT REQUIRED: invoke post-design-boundary.sh --implement-tmpdir ... as a Bash tool call — do NOT skip the wrapper call"
    else
        echo "➡️ 1: design plan — hook injected boundary context; NEXT REQUIRED: invoke post-design-boundary.sh --implement-tmpdir ... as a Bash tool call — do NOT skip the wrapper call"
    fi
else
    # Normal (orchestrator-driven) mode: write the sentinel BEFORE emitting buffered
    # reader output. Failure is fatal because the Stop hook treats sentinel absence as
    # "halted mid-Step-1" and would otherwise trap a legitimate success path.
    # Buffering avoids the dual-envelope footgun where MANIFEST_OK and a later
    # MANIFEST_FAILED could coexist on a late-failure path.
    if ! touch "$IMPLEMENT_TMPDIR/.boundary-gate-passed" 2>/dev/null; then
        fail_closed "boundary-gate-sentinel-write-failed"
    fi
    # All hard gates have passed. Emit the unified success envelope:
    # (1) reader stdout (MANIFEST_OK + KV + 📥 breadcrumb), then (2) wrapper extensions.
    printf '%s\n' "$READER_OUT"
    printf 'BRANCH=%s\n' "$BRANCH"
    if [[ "$DESIGN_ONLY" = true ]]; then
        echo "NEXT_ACTION=plan-goals-test-and-plan-review-tally-then-diagrams-then-step-9a1"
    else
        echo "NEXT_ACTION=larch-log-batches-then-1r-then-step2"
    fi
    echo "POST_DESIGN_BOUNDARY_OK=true"
    printf '%s' "$WARNINGS"
    if [[ "$DESIGN_ONLY" = true ]]; then
        echo "➡️ 1: design plan — boundary gate passed (design-only); NEXT REQUIRED: write plan-goals-test + plan-review-tally log batches → write diagrams log batch → Step 9a.1 OOS pipeline"
    else
        echo "➡️ 1: design plan — boundary gate passed; NEXT REQUIRED: write larch-log batches → Step 1.r rebase → Step 2 entry"
    fi
fi
