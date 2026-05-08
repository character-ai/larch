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
            issue_number=$(awk -F= '$1 == "ISSUE_NUMBER" {print substr($0, index($0, "=") + 1); exit}' "$sentinel_path" 2>/dev/null || true)
            stall_step=$(awk -F= '$1 == "STALL_STEP" {print substr($0, index($0, "=") + 1); exit}' "$sentinel_path" 2>/dev/null || true)
            stash_ref=$(awk -F= '$1 == "STASH_REF" {print substr($0, index($0, "=") + 1); exit}' "$sentinel_path" 2>/dev/null || true)
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

if [[ -n "$MSG" ]]; then
    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        jq -n --arg ctx "$MSG" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}' || true
    else
        if [[ "$GIT_AVAILABLE" == "true" ]]; then
            printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"larch hook preflight: jq not on PATH (install jq for advisory hook output)."}}'
        else
            printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"larch hook preflight: jq not on PATH and git not on PATH; install jq and git for advisory hook output."}}'
        fi
    fi
fi

exit 0
