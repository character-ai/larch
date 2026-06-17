#!/usr/bin/env bash
# step-2-post-dispatch.sh: /implement Step 2 post-dispatch probe, branch, and SHA.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR

rehydrate_plugin_root() {
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
        # shellcheck source=/dev/null
        . "$IMPLEMENT_TMPDIR/plugin-root.env"
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
        CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
        CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
    fi
    export CLAUDE_PLUGIN_ROOT
}

rehydrate_plugin_root
# shellcheck source=scripts/lib-quiet.sh
. "$CLAUDE_PLUGIN_ROOT/scripts/lib-quiet.sh"
# shellcheck source=scripts/lib-phantom-probe.sh
. "$CLAUDE_PLUGIN_ROOT/scripts/lib-phantom-probe.sh"

phantom_probe_with_warn "2-post-dispatch"


read_kv_file() {
    local file=$1 key=$2 line
    if [ -f "$file" ]; then
        line=$(grep "^${key}=" "$file" 2>/dev/null | head -n 1 || true)
        if [ -n "$line" ]; then
            printf '%s\n' "${line#*=}"
            return 0
        fi
    fi
    printf '\n'
}

persist_ship_seed_context() {
    local seed_file tmp_file manifest_path tool_label coder_value
    seed_file="$IMPLEMENT_TMPDIR/ship-seed-input.env"
    tmp_file="$seed_file.tmp.$$"
    if [ -f "$seed_file" ] && [ ! -L "$seed_file" ]; then
        cp "$seed_file" "$tmp_file"
    else
        : >"$tmp_file"
    fi
    if ! grep -q '^MANIFEST_PATH=' "$tmp_file" 2>/dev/null; then
        manifest_path=""
        if [ -r "$IMPLEMENT_TMPDIR/codex-step2-out/manifest.json" ]; then
            manifest_path="$IMPLEMENT_TMPDIR/codex-step2-out/manifest.json"
        elif [ -r "$IMPLEMENT_TMPDIR/manifest.json" ]; then
            manifest_path="$IMPLEMENT_TMPDIR/manifest.json"
        fi
        printf 'MANIFEST_PATH=%s\n' "$manifest_path" >>"$tmp_file"
    fi
    if ! grep -q '^TOOL_LABEL=' "$tmp_file" 2>/dev/null; then
        coder_value=$(read_kv_file "$IMPLEMENT_TMPDIR/bootstrap-routing.env" coder)
        case "$coder_value" in
            codex) tool_label=Codex ;;
            cursor) tool_label=Cursor ;;
            *) tool_label=claude ;;
        esac
        printf 'TOOL_LABEL=%s\n' "$tool_label" >>"$tmp_file"
    fi
    mv -f "$tmp_file" "$seed_file"
}


if BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null); then
    emit_kv BRANCH "$BRANCH"
else
    larch_err "step-2-post-dispatch.sh: not on a named branch (detached HEAD or not a git repo)"
    exit 1
fi

commit_sha=$(git rev-parse --short HEAD 2>/dev/null || true)
if [ -n "$commit_sha" ]; then
    emit_kv COMMIT_SHA "$commit_sha"
fi

persist_ship_seed_context

exit 0
