#!/usr/bin/env bash
# sessionstart-health.sh — SessionStart hook that probes required CLI tools
# and leftover git state at session start, then emits a spec-compliant
# advisory to Claude's session context when anything needs attention.
#
# INVARIANT: all dynamic content MUST be interpolated only via `jq -n --arg`.
# The jq-missing fallback may hand-craft JSON only from fixed ASCII literals.
#
# SessionStart is non-blocking by spec: the script ALWAYS exits 0. A failing
# probe produces advisory JSON on stdout; a healthy environment produces
# nothing. The hook does not read stdin.

set -euo pipefail
LC_ALL=C

MSG=""
JQ_AVAILABLE=true
GIT_AVAILABLE=true

append_msg() {
    if [[ -n "$MSG" ]]; then
        MSG="$MSG "
    fi
    MSG="${MSG}$1"
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
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        if ! status_out=$(git status --porcelain 2>/dev/null); then
            status_out=""
        fi
        if [[ -n "$status_out" ]]; then
            append_msg "larch hook preflight: working tree has uncommitted changes; the next /implement or /fix-issue will fail preflight or inherit them."
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

        if ! unmerged_branches=$(git branch --no-merged main 2>/dev/null | grep -v '^\*'); then
            unmerged_branches=""
        fi
        if [[ -n "$unmerged_branches" ]]; then
            append_msg "larch hook preflight: local feature branch(es) not merged into main; consider deleting or pushing."
        fi

        if ! sentinel_path=$(git rev-parse --git-path larch-stalled-run.txt 2>/dev/null); then
            sentinel_path=""
        fi
        if [[ -n "$sentinel_path" && -f "$sentinel_path" ]]; then
            issue_number=$(awk -F= '$1 == "ISSUE_NUMBER" {print substr($0, index($0, "=") + 1); exit}' "$sentinel_path" 2>/dev/null || true)
            stall_step=$(awk -F= '$1 == "STALL_STEP" {print substr($0, index($0, "=") + 1); exit}' "$sentinel_path" 2>/dev/null || true)
            stash_ref=$(awk -F= '$1 == "STASH_REF" {print substr($0, index($0, "=") + 1); exit}' "$sentinel_path" 2>/dev/null || true)
            issue_number=${issue_number:-unknown}
            stall_step=${stall_step:-unknown}
            stash_ref=${stash_ref:-no stash}
            append_msg "larch hook preflight: a prior /implement run for #${issue_number} stalled at step ${stall_step}. Working-tree edits stashed as ${stash_ref}. Resume via 'git stash apply ${stash_ref}' or drop via 'git stash drop ${stash_ref}'."
        fi
    fi
fi

if [[ -n "$MSG" ]]; then
    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        jq -n --arg ctx "$MSG" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}' || true
    else
        printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$MSG"
    fi
fi

exit 0
