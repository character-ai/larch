#!/usr/bin/env bash
# sessionstart-health.sh — SessionStart hook that probes required CLI tools
# and leftover git state at session start, then emits a spec-compliant
# advisory to Claude's session context when anything needs attention.
#
# INVARIANT: all dynamic content MUST be interpolated only via `jq -n --arg`.
# The jq-missing branch is hardcoded to fixed JSON literals (one per
# GIT_AVAILABLE value) — no `%s` formatting, no variable interpolation. Future
# probes that interpolate user-influenced content into MSG are still safe in
# the jq-missing branch because that branch does not read MSG.
#
# SessionStart is non-blocking by spec: the script ALWAYS exits 0. A failing
# probe produces advisory JSON on stdout; a healthy environment produces
# nothing. When jq is available, the hook reads stdin for `cwd` and
# `session_id` so it can resolve active /implement boundary state.

set -euo pipefail

SCRIPT_DIR="$(cd "${BASH_SOURCE[0]%/*}" && pwd -P)"
# SessionStart health deliberately runs under stripped PATHs in both tests and
# real hook environments. When dirname/mkdir are unavailable, skip quiet
# redirection and keep hook advisories on stdout.
if command -v dirname >/dev/null 2>&1 && command -v mkdir >/dev/null 2>&1; then
    hook_log_base=${0##*/}
    hook_log_dir=${IMPLEMENT_TMPDIR:-${DESIGN_TMPDIR:-${TMPDIR:-/tmp}}}
    hook_log_file="${LARCH_QUIET_LOG_FILE:-$hook_log_dir/larch-quiet-${hook_log_base:-sessionstart-health.sh}-$$.log}"
    hook_log_parent=$(dirname "$hook_log_file" 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}")
    if mkdir -p "$hook_log_parent" 2>/dev/null && : >"$hook_log_file" 2>/dev/null; then
        exec 3>&1
        hook_emit() { printf '%s
' "$1" >&3; }
        exec >>"$hook_log_file" 2>&1
    else
        hook_emit() { printf '%s
' "$1"; }
    fi
else
    hook_emit() { printf '%s
' "$1"; }
fi
LC_ALL=C

INPUT=$(cat 2>/dev/null) || INPUT=''
MSG=""
HOOK_CWD=""
SID=""
JQ_AVAILABLE=true
GIT_AVAILABLE=true

append_msg() {
    if [[ -n "$MSG" ]]; then
        MSG="$MSG "
    fi
    MSG="${MSG}$1"
}

implement_session_dir_exists() {
    [[ -n "$HOOK_CWD" ]] || return 1
    local roots=(
        "${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions"
        "/tmp"
        "/private/tmp"
    )
    local root dir
    for root in "${roots[@]}"; do
        [[ -d "$root" ]] || continue
        for dir in "$root"/claude-implement-*; do
            [[ -d "$dir" ]] && return 0
        done
    done
    return 1
}

probe_sparse_cone_drift() {
    local restore_errexit=false
    local restore_nounset=false
    local home_dir marketplace_clone configured expected

    case $- in
        *e*) restore_errexit=true ;;
    esac
    case $- in
        *u*) restore_nounset=true ;;
    esac
    set +e
    set +u

    home_dir="${HOME:-}"
    if [[ -z "$home_dir" ]]; then
        [[ "$restore_nounset" == "true" ]] && set -u
        [[ "$restore_errexit" == "true" ]] && set -e
        return 0
    fi

    marketplace_clone="$home_dir/.claude/plugins/marketplaces/larch-local"
    if [[ ! -d "$marketplace_clone/.git" || -d "$marketplace_clone/larch-logs" ]]; then
        [[ "$restore_nounset" == "true" ]] && set -u
        [[ "$restore_errexit" == "true" ]] && set -e
        return 0
    fi

    configured=$(git -C "$marketplace_clone" sparse-checkout list 2>/dev/null | sed '/^$/d' | sort || true)
    expected=$(python3 "$SCRIPT_DIR/../python/cli.py" upgrade-larch sparse-dirs 2>/dev/null || true)
    if [[ -n "$configured" && -n "$expected" && "$configured" != "$expected" ]]; then
        append_msg "larch hook preflight: larch-local marketplace sparse checkout is out of date; run /upgrade-larch to repair it."
    fi

    [[ "$restore_nounset" == "true" ]] && set -u
    [[ "$restore_errexit" == "true" ]] && set -e
    return 0
}

if ! command -v jq >/dev/null 2>&1; then
    JQ_AVAILABLE=false
    append_msg "larch hook preflight: jq not on PATH (install: brew install jq / apt install jq). Claude Code JSON parsing and several larch scripts depend on jq."
fi
if ! command -v git >/dev/null 2>&1; then
    GIT_AVAILABLE=false
    append_msg "larch hook preflight: git not on PATH. The submodule-edit guard and most larch scripts depend on git."
fi

if [[ "$JQ_AVAILABLE" == "true" && "$GIT_AVAILABLE" == "true" ]]; then
    probe_sparse_cone_drift

    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        if ! status_out=$(git status --porcelain 2>/dev/null); then
            status_out=""
        fi
        if [[ -n "$status_out" ]]; then
            append_msg "larch hook preflight: working tree has uncommitted changes; the next /implement will fail preflight or inherit them."
        fi

        if ! stash_out=$(git stash list 2>/dev/null); then
            stash_out=""
        fi
        if printf '%s\n' "$stash_out" | grep -q ': .*larch-'; then
            append_msg "larch hook preflight: leftover larch-managed stash detected (run 'git stash list | grep larch-' to inspect)."
        fi

        interrupted=false
        for state_path in REBASE_HEAD MERGE_HEAD CHERRY_PICK_HEAD; do
            if ! git_state_path=$(git rev-parse --git-path "$state_path" 2>/dev/null); then
                git_state_path=""
            fi
            if [[ -n "$git_state_path" && -e "$git_state_path" ]]; then
                interrupted=true
            fi
        done
        if [[ "$interrupted" == "true" ]]; then
            append_msg "larch hook preflight: interrupted rebase/merge/cherry-pick state on disk."
        fi

        # Only probe unmerged branches when local `main` actually exists; clones
        # whose integration branch is `master` (or where `main` was never created)
        # would otherwise silently skip with a misleading-empty result.
        if git rev-parse --verify --quiet refs/heads/main >/dev/null 2>&1; then
            if ! unmerged_branches=$(git branch --no-merged main 2>/dev/null | grep -v '^\*'); then
                unmerged_branches=""
            fi
            if [[ -n "$unmerged_branches" ]]; then
                append_msg "larch hook preflight: local feature branch(es) not merged into main; consider deleting or pushing."
            fi
        fi

        if ! sentinel_path=$(git rev-parse --git-path larch-stalled-run.txt 2>/dev/null); then
            sentinel_path=""
        fi
        if [[ -n "$sentinel_path" && -f "$sentinel_path" ]]; then
            issue_number=$(python3 "$SCRIPT_DIR/../python/cli.py" kv get --file "$sentinel_path" --key ISSUE_NUMBER --match first 2>/dev/null || true)
            stall_step=$(python3 "$SCRIPT_DIR/../python/cli.py" kv get --file "$sentinel_path" --key STALL_STEP --match first 2>/dev/null || true)
            stash_ref=$(python3 "$SCRIPT_DIR/../python/cli.py" kv get --file "$sentinel_path" --key STASH_REF --match first 2>/dev/null || true)
            issue_number=${issue_number:-unknown}
            stall_step=${stall_step:-unknown}
            # Branch on whether a stash was actually recorded — empty STASH_REF
            # means the prior run had a clean tree at stall time (or the
            # auto-stash failed), and `git stash apply no stash` is invalid.
            if [[ -n "$stash_ref" ]]; then
                append_msg "larch hook preflight: a prior /implement run for #${issue_number} stalled at step ${stall_step}. Working-tree edits stashed as ${stash_ref}. Resume via 'git stash apply ${stash_ref}' or drop via 'git stash drop ${stash_ref}'."
            else
                append_msg "larch hook preflight: a prior /implement run for #${issue_number} stalled at step ${stall_step}. No working-tree edits were stashed; inspect 'git status' / the issue for context."
            fi
        fi
    fi
fi

if [[ "$JQ_AVAILABLE" == "true" && -n "$INPUT" ]]; then
    HOOK_CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null) || HOOK_CWD=""
    SID=$(printf '%s' "$INPUT" | jq -r '.session_id // ""' 2>/dev/null) || SID=""
fi

if [[ -n "$HOOK_CWD" ]]; then
    PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
    if [[ -n "$SID" ]]; then
        export LARCH_TOKEN_SESSION_ID="$SID"
    else
        unset LARCH_TOKEN_SESSION_ID || true
    fi
    IMPLEMENT_TMPDIR=""
    if implement_session_dir_exists && command -v python3 >/dev/null 2>&1; then
        IMPLEMENT_TMPDIR=$(python3 "$PLUGIN_ROOT/python/cli.py" session resolve-implement-tmpdir --cwd "$HOOK_CWD" 2>/dev/null) || IMPLEMENT_TMPDIR=""
    fi
    if [[ -n "$IMPLEMENT_TMPDIR" ]]; then
        if [[ ! -f "$IMPLEMENT_TMPDIR/.run-cleaned-up" ]]; then
            TMPDIR_BASENAME=$(basename "$IMPLEMENT_TMPDIR" 2>/dev/null) \
                || TMPDIR_BASENAME="<implement-tmpdir>"
            if [[ -f "$IMPLEMENT_TMPDIR/review-round-summary.md" && \
                  ! -f "$IMPLEMENT_TMPDIR/.review-boundary-passed" ]]; then
                append_msg "larch hook preflight: pending post-/review boundary in active /implement tmpdir (${TMPDIR_BASENAME}); NEXT REQUIRED: execute Cross-Skill Presence Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb in order per skills/implement/SKILL.md Step 5, then touch .review-boundary-passed."
            fi
        fi
    fi
fi

if [[ -n "$MSG" ]]; then
    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        ADVISORY=$(jq -n --arg ctx "$MSG" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}' 2>/dev/null) || ADVISORY=''
        [ -n "$ADVISORY" ] && hook_emit "$ADVISORY"
    else
        if [[ "$GIT_AVAILABLE" == "true" ]]; then
            hook_emit '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"larch hook preflight: jq not on PATH (install jq for advisory hook output)."}}'
        else
            hook_emit '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"larch hook preflight: jq not on PATH and git not on PATH; install jq and git for advisory hook output."}}'
        fi
    fi
fi

exit 0
