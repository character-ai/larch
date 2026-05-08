# shellcheck shell=bash
# lib-resolve-implement-tmpdir.sh — sourced helper for /implement hook scripts.
#
# set -e omitted: callers are fail-open hooks and own their strictness.
# Intentional per .claude/rules/shell-strict-mode.md.

resolve_implement_tmpdir() {
    local hook_cwd="${1:-}"
    local roots=(
        "${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions"
        "/tmp"
        "/private/tmp"
    )
    local best="" best_mtime=0
    local root dir manifest mtime keepalive cp_match

    for root in "${roots[@]}"; do
        [[ -d "$root" ]] || continue
        for dir in "$root"/claude-implement-*; do
            [[ -d "$dir" ]] || continue
            manifest="$dir/design-export/manifest.env"
            [[ -f "$manifest" ]] || continue

            if [[ -n "$hook_cwd" ]]; then
                keepalive="$dir/.larch-keepalive"
                [[ -f "$keepalive" ]] || continue
                cp_match=$(awk -F= -v cwd="$hook_cwd" '
                    $1=="CLONE_PATH" {
                        v=substr($0, index($0,"=")+1)
                        if (v==cwd) { print "ok"; exit }
                    }' "$keepalive" 2>/dev/null)
                [[ "$cp_match" = "ok" ]] || continue
            fi

            mtime=$(stat -f %m "$manifest" 2>/dev/null \
                || stat -c %Y "$manifest" 2>/dev/null) || continue
            if (( mtime > best_mtime )); then
                best_mtime=$mtime
                best=$dir
            elif (( mtime == best_mtime )) && [[ -n "$best" && "$dir" < "$best" ]]; then
                best=$dir
            elif (( mtime == best_mtime )) && [[ -z "$best" ]]; then
                best=$dir
            fi
        done
    done

    printf '%s' "$best"
}
