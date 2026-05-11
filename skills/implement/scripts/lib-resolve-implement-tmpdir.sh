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
    # Fail-OPEN when caller did not supply a cwd. Without cwd we cannot bind
    # the candidate to the active session via .larch-keepalive — picking the
    # globally-newest manifest would attach hook state to the wrong session
    # under concurrent or stale runs (and bypass the documented binding rule
    # exercised by the test harness). Empty hook_cwd means: no resolution,
    # no breadcrumb injection, no Stop block.
    if [[ -z "$hook_cwd" ]]; then
        return 0
    fi

    local best="" best_mtime=0
    local root dir manifest mtime keepalive cp_match now session_match sid ttl

    now=$(date +%s 2>/dev/null || echo 0)

    for root in "${roots[@]}"; do
        [[ -d "$root" ]] || continue
        for dir in "$root"/claude-implement-*; do
            [[ -d "$dir" ]] || continue
            # Accept design manifest (normal path) or review summary (both-externals-down
            # path that skips /design but still runs /review — issue #1862).
            local manifest=""
            if [[ -f "$dir/design-export/manifest.env" ]]; then
                manifest="$dir/design-export/manifest.env"
            elif [[ -f "$dir/review-round-summary.md" ]]; then
                manifest="$dir/review-round-summary.md"
            fi
            [[ -n "$manifest" ]] || continue

            keepalive="$dir/.larch-keepalive"
            [[ -f "$keepalive" ]] || continue
            cp_match=$(awk -F= -v cwd="$hook_cwd" '
                $1=="CLONE_PATH" {
                    v=substr($0, index($0,"=")+1)
                    if (v==cwd) { print "ok"; exit }
                }' "$keepalive" 2>/dev/null)
            [[ "$cp_match" = "ok" ]] || continue

            # Session-id binding: when /implement Step 0 exported the active
            # session id, require an exact .larch-keepalive match. When the
            # env var is unset, skip this check and rely on the TTL backstop.
            session_match=false
            if [[ -n "${LARCH_TOKEN_SESSION_ID:-}" ]]; then
                sid=$(awk -F= -v want="$LARCH_TOKEN_SESSION_ID" '
                    $1=="SESSION_ID" {
                        v=substr($0, index($0,"=")+1)
                        if (v==want) { print "ok"; exit }
                    }' "$keepalive" 2>/dev/null)
                if [[ "$sid" = "ok" ]]; then
                    session_match=true
                else
                    continue
                fi
            fi

            # Linux GNU stat first (CI lane), then BSD/macOS fallback.
            # Order matters: GNU `stat -f %m` switches to fs-info mode and
            # treats `%m` as a path argument, polluting stdout with
            # "File: ..." text — running the BSD form first on Linux would
            # capture that text into $mtime and break the arithmetic
            # comparison below under callers that set -u (`File: unbound
            # variable`). Numeric guard covers both branches.
            mtime=$(stat -c %Y "$manifest" 2>/dev/null) \
                || mtime=$(stat -f %m "$manifest" 2>/dev/null) \
                || continue
            [[ "$mtime" =~ ^[0-9]+$ ]] || continue
            if ! $session_match; then
                ttl=${LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS:-21600}
                [[ "$ttl" =~ ^[0-9]+$ ]] || ttl=21600
                if (( ttl > 0 )); then
                    if (( now <= 0 )); then
                        continue
                    fi
                    if (( (now - mtime) >= ttl )); then
                        continue
                    fi
                fi
            fi
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
