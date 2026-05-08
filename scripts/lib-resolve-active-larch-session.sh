#!/usr/bin/env bash
# Resolve an active larch implement/review session from Claude hook stdin.

set -euo pipefail
LC_ALL=C

if ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

INPUT=$(cat) || exit 0
HOOK_CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null) || exit 0
HOOK_SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null) || exit 0

if [[ -z "$HOOK_CWD" || -z "$HOOK_SESSION_ID" ]]; then
    exit 0
fi

SESSIONS_ROOT="${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions"
[[ -d "$SESSIONS_ROOT" ]] || exit 0

now=$(date +%s 2>/dev/null || echo 0)
ttl=${LARCH_ACTIVE_SESSION_TTL_SECONDS:-21600}
[[ "$ttl" =~ ^[0-9]+$ ]] || ttl=21600

best=""
best_mtime=0
best_prefix=""

for dir in "$SESSIONS_ROOT"/claude-implement-* "$SESSIONS_ROOT"/claude-review-*; do
    [[ -d "$dir" ]] || continue
    keepalive="$dir/.larch-keepalive"
    [[ -f "$keepalive" ]] || continue

    match=$(awk -F= -v cwd="$HOOK_CWD" -v sid="$HOOK_SESSION_ID" '
        $1 == "CLONE_PATH" {
            v = substr($0, index($0, "=") + 1)
            if (v == cwd) cwd_ok = 1
        }
        $1 == "SESSION_ID" {
            v = substr($0, index($0, "=") + 1)
            if (v == sid) sid_ok = 1
        }
        END {
            if (cwd_ok && sid_ok) print "ok"
        }
    ' "$keepalive" 2>/dev/null || true)
    [[ "$match" == "ok" ]] || continue

    mtime=$(stat -c %Y "$keepalive" 2>/dev/null) \
        || mtime=$(stat -f %m "$keepalive" 2>/dev/null) \
        || continue
    [[ "$mtime" =~ ^[0-9]+$ ]] || continue
    if (( ttl > 0 )); then
        (( now > 0 )) || continue
        (( (now - mtime) < ttl )) || continue
    fi

    prefix=$(basename "$dir")
    prefix=${prefix%%-*}-${prefix#*-}
    prefix=${prefix%-*}
    case "$(basename "$dir")" in
        claude-implement-*) prefix="claude-implement" ;;
        claude-review-*) prefix="claude-review" ;;
        *) continue ;;
    esac

    if (( mtime > best_mtime )); then
        best_mtime=$mtime
        best=$dir
        best_prefix=$prefix
    elif (( mtime == best_mtime )) && [[ -n "$best" && "$dir" < "$best" ]]; then
        best=$dir
        best_prefix=$prefix
    elif (( mtime == best_mtime )) && [[ -z "$best" ]]; then
        best=$dir
        best_prefix=$prefix
    fi
done

if [[ -n "$best" ]]; then
    printf 'PREFIX=%s TMPDIR=%s\n' "$best_prefix" "$best"
fi
