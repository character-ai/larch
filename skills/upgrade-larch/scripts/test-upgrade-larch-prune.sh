#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/upgrade-larch/scripts/upgrade-larch.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-upgrade-larch-prune.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    grep -Fq "$needle" <<< "$haystack" || fail "$label: missing [$needle]"
}

make_plugin_root() {
    local base="$1" version="$2"
    local root="$base/$version"
    mkdir -p "$root/scripts"
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$root/scripts/lib-quiet.sh"
    printf '%s\n' "$root"
}

write_stub_claude() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

cmd="${1:-}"
subcmd="${2:-}"
if [[ "$cmd" != "plugin" ]]; then
    printf 'unexpected claude command: %s %s\n' "$cmd" "$subcmd" >&2
    exit 1
fi
shift 2

state_file="${TEST_STATE_FILE:?}"
cache_dir="${TEST_CACHE_DIR:?}"

read_state() {
    if [[ -f "$state_file" ]]; then
        # shellcheck disable=SC1090
        source "$state_file"
    else
        INSTALLED_VERSION=""
    fi
}

write_state() {
    cat > "$state_file" <<STATE
INSTALLED_VERSION="${INSTALLED_VERSION:-}"
STATE
}

read_state

case "$subcmd" in
    list)
        cat <<LIST
larch@larch-local
  Version: ${INSTALLED_VERSION:-unknown}
LIST
        ;;
    uninstall)
        INSTALLED_VERSION=""
        write_state
        ;;
    install)
        INSTALLED_VERSION="${INSTALL_RESULT_VERSION:?}"
        mkdir -p "$cache_dir/$INSTALL_RESULT_VERSION"
        write_state
        ;;
    marketplace)
        ;;
    *)
        printf 'unexpected plugin subcommand: %s\n' "$subcmd" >&2
        exit 1
        ;;
esac
EOF
    chmod +x "$path"
}

write_stub_gh() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

printf '%s' "${GH_OUTPUT:?}"
EOF
    chmod +x "$path"
}

run_case() {
    local name="$1"
    local work="$TMP/$name"
    local home="$work/home"
    local bin="$work/bin"
    local state_file="$work/state.sh"
    local cache_root="$work/cache"
    local sessions_root="$work/sessions"
    local plugin_root session_idx
    local output rc

    mkdir -p "$home/.claude/plugins" "$bin" "$cache_root" "$sessions_root"
    plugin_root=$(make_plugin_root "$cache_root" "${PLUGIN_ROOT_VERSION:-29.1.20}")
    write_stub_claude "$bin/claude"
    write_stub_gh "$bin/gh"
    cat > "$state_file" <<STATE
INSTALLED_VERSION="${INITIAL_INSTALLED_VERSION:-}"
STATE
    for version in ${CACHED_VERSIONS:-}; do
        mkdir -p "$cache_root/$version"
    done
    session_idx=0
    for version in ${SESSION_PINNED_VERSIONS:-}; do
        session_idx=$((session_idx + 1))
        write_session_env "$sessions_root" "claude-implement-larch-$session_idx" "$cache_root/$version"
    done
    if [[ -n "${SESSION_PINNED_ROOT:-}" ]]; then
        session_idx=$((session_idx + 1))
        write_session_env "$sessions_root" "claude-implement-larch-$session_idx" "$SESSION_PINNED_ROOT"
    fi

    set +e
    output=$(
        HOME="$home" \
        PATH="$bin:$PATH" \
        CLAUDE_PLUGIN_ROOT="$plugin_root" \
        LARCH_SESSIONS_DIR="$sessions_root" \
        TEST_STATE_FILE="$state_file" \
        TEST_CACHE_DIR="$cache_root" \
        GH_OUTPUT="${GH_OUTPUT:-}" \
        INSTALL_RESULT_VERSION="${INSTALL_RESULT_VERSION:-}" \
        LARCH_QUIET_BREADCRUMBS=1 \
        "$SCRIPT" 2>&1
    )
    rc=$?
    set -e

    CASE_OUTPUT="$output"
    CASE_RC="$rc"
    CASE_CACHE_ROOT="$cache_root"
}

write_session_env() {
    local sessions_root="$1" session_name="$2" plugin_root="$3"
    mkdir -p "$sessions_root/$session_name"
    printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$plugin_root" > "$sessions_root/$session_name/session-env.sh"
}

GH_OUTPUT=$'29.1.22\n29.1.21\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.21"
INSTALL_RESULT_VERSION="29.1.22"
CACHED_VERSIONS="29.1.19 29.1.20 29.1.21 29.1.22"
SESSION_PINNED_VERSIONS="29.1.20"
unset SESSION_PINNED_ROOT
run_case active-session-keeps-version
[[ "$CASE_RC" -eq 0 ]] || fail "active-session-keeps-version exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/29.1.19" ]] || fail "active-session-keeps-version should prune unused old version"
[[ -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "active-session-keeps-version should keep active in-use version"
[[ -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "active-session-keeps-version should keep predecessor"
[[ -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "active-session-keeps-version should keep latest"
assert_contains "$CASE_OUTPUT" "Warning: preserving cached larch version '29.1.20' because an active session is using it." "active-session-keeps-version warning"

GH_OUTPUT=$'29.1.22\n29.1.21\n'
INITIAL_INSTALLED_VERSION="29.1.20"
PLUGIN_ROOT_VERSION="29.1.20"
INSTALL_RESULT_VERSION="29.1.22"
CACHED_VERSIONS="29.1.19 29.1.20 29.1.21 29.1.22"
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT
run_case no-sessions-prunes-old
[[ "$CASE_RC" -eq 0 ]] || fail "no-sessions-prunes-old exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/29.1.19" ]] || fail "no-sessions-prunes-old should prune oldest version"
[[ ! -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "no-sessions-prunes-old should prune old current version"
[[ -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "no-sessions-prunes-old should keep predecessor"
[[ -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "no-sessions-prunes-old should keep latest"

GH_OUTPUT=$'29.1.22\n29.1.21\n'
INITIAL_INSTALLED_VERSION="29.1.20"
PLUGIN_ROOT_VERSION="29.1.20"
INSTALL_RESULT_VERSION="29.1.22"
CACHED_VERSIONS="29.1.19 29.1.20 29.1.21 29.1.22"
unset SESSION_PINNED_VERSIONS
SESSION_PINNED_ROOT="/cache/not-a-version"
run_case unparseable-session-prunes-normally
[[ "$CASE_RC" -eq 0 ]] || fail "unparseable-session-prunes-normally exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/29.1.19" ]] || fail "unparseable-session-prunes-normally should prune oldest version"
[[ ! -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "unparseable-session-prunes-normally should prune old current version"
[[ -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "unparseable-session-prunes-normally should keep predecessor"
[[ -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "unparseable-session-prunes-normally should keep latest"

printf 'PASS: test-upgrade-larch-prune.sh\n'
