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
    local xdg_cache_home="$work/xdg-cache"
    local plugin_root session_idx tmp_session_name
    local output rc

    mkdir -p "$home/.claude/plugins" "$bin" "$cache_root" "$sessions_root" "$xdg_cache_home"
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
    if [[ -n "${SESSION_PINNED_ROOT_LITERAL:-}" ]]; then
        session_idx=$((session_idx + 1))
        write_session_env_literal "$sessions_root" "claude-implement-larch-$session_idx" "$SESSION_PINNED_ROOT_LITERAL"
    fi
    if [[ -n "${XDG_SESSION_PINNED_VERSIONS:-}" ]]; then
        session_idx=0
        for version in ${XDG_SESSION_PINNED_VERSIONS:-}; do
            session_idx=$((session_idx + 1))
            write_session_env "$xdg_cache_home/larch/sessions" "claude-implement-larch-xdg-$session_idx" "$cache_root/$version"
        done
    fi
    if [[ -n "${TMP_SESSION_PINNED_VERSIONS:-}" ]]; then
        session_idx=0
        for version in ${TMP_SESSION_PINNED_VERSIONS:-}; do
            session_idx=$((session_idx + 1))
            tmp_session_name="claude-implement-larch-upgrade-prune-$session_idx-$$"
            rm -rf "/tmp/$tmp_session_name"
            write_session_env "/tmp" "$tmp_session_name" "$cache_root/$version"
        done
    fi

    set +e
    if [[ -n "${SET_LARCH_SESSIONS_DIR:-}" ]]; then
        output=$(
            HOME="$home" \
            PATH="$bin:$PATH" \
            CLAUDE_PLUGIN_ROOT="$plugin_root" \
            XDG_CACHE_HOME="$xdg_cache_home" \
            LARCH_SESSIONS_DIR="$sessions_root" \
            TEST_STATE_FILE="$state_file" \
            TEST_CACHE_DIR="$cache_root" \
            GH_OUTPUT="${GH_OUTPUT:-}" \
            INSTALL_RESULT_VERSION="${INSTALL_RESULT_VERSION:-}" \
            LARCH_QUIET_BREADCRUMBS=1 \
            "$SCRIPT" 2>&1
        )
    else
        output=$(
            HOME="$home" \
            PATH="$bin:$PATH" \
            CLAUDE_PLUGIN_ROOT="$plugin_root" \
            XDG_CACHE_HOME="$xdg_cache_home" \
            TEST_STATE_FILE="$state_file" \
            TEST_CACHE_DIR="$cache_root" \
            GH_OUTPUT="${GH_OUTPUT:-}" \
            INSTALL_RESULT_VERSION="${INSTALL_RESULT_VERSION:-}" \
            LARCH_QUIET_BREADCRUMBS=1 \
            "$SCRIPT" 2>&1
        )
    fi
    rc=$?
    set -e

    rm -rf /tmp/claude-implement-larch-upgrade-prune-*-"$$"

    CASE_OUTPUT="$output"
    CASE_RC="$rc"
    CASE_CACHE_ROOT="$cache_root"
}

write_session_env() {
    local sessions_root="$1" session_name="$2" plugin_root="$3"
    mkdir -p "$sessions_root/$session_name"
    printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$plugin_root" > "$sessions_root/$session_name/session-env.sh"
}

write_session_env_literal() {
    local sessions_root="$1" session_name="$2" literal_line="$3"
    mkdir -p "$sessions_root/$session_name"
    printf '%s\n' "$literal_line" > "$sessions_root/$session_name/session-env.sh"
}

GH_OUTPUT=$'29.1.22\n29.1.21\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.21"
INSTALL_RESULT_VERSION="29.1.22"
CACHED_VERSIONS="29.1.19 29.1.20 29.1.21 29.1.22"
SESSION_PINNED_VERSIONS="29.1.20"
SET_LARCH_SESSIONS_DIR=1
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
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT XDG_SESSION_PINNED_VERSIONS TMP_SESSION_PINNED_VERSIONS
SET_LARCH_SESSIONS_DIR=1
run_case no-sessions-prunes-old
[[ "$CASE_RC" -eq 0 ]] || fail "no-sessions-prunes-old exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/29.1.19" ]] || fail "no-sessions-prunes-old should prune oldest version"
[[ -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "no-sessions-prunes-old should keep the executing cached version"
[[ -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "no-sessions-prunes-old should keep predecessor"
[[ -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "no-sessions-prunes-old should keep latest"

GH_OUTPUT=$'29.1.22\n29.1.21\n'
INITIAL_INSTALLED_VERSION="29.1.20"
PLUGIN_ROOT_VERSION="29.1.20"
INSTALL_RESULT_VERSION="29.1.22"
CACHED_VERSIONS="29.1.19 29.1.20 29.1.21 29.1.22"
SET_LARCH_SESSIONS_DIR=1
unset SESSION_PINNED_VERSIONS XDG_SESSION_PINNED_VERSIONS TMP_SESSION_PINNED_VERSIONS
SESSION_PINNED_ROOT="/cache/not-a-version"
run_case unparseable-session-prunes-normally
[[ "$CASE_RC" -eq 0 ]] || fail "unparseable-session-prunes-normally exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/29.1.19" ]] || fail "unparseable-session-prunes-normally should prune oldest version"
[[ -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "unparseable-session-prunes-normally should keep the executing cached version"
[[ -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "unparseable-session-prunes-normally should keep predecessor"
[[ -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "unparseable-session-prunes-normally should keep latest"

GH_OUTPUT=$'29.1.22\n29.1.21\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.21"
INSTALL_RESULT_VERSION="29.1.22"
CACHED_VERSIONS="29.1.19 29.1.20 29.1.21 29.1.22"
SET_LARCH_SESSIONS_DIR=1
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT XDG_SESSION_PINNED_VERSIONS TMP_SESSION_PINNED_VERSIONS
SESSION_PINNED_ROOT_LITERAL=$'LARCH_CLAUDE_PLUGIN_ROOT=/ignored/prefix/29.1.20\r   '
run_case crlf-session-root-keeps-version
[[ "$CASE_RC" -eq 0 ]] || fail "crlf-session-root-keeps-version exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/29.1.19" ]] || fail "crlf-session-root-keeps-version should prune unused old version"
[[ -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "crlf-session-root-keeps-version should keep CRLF-pinned version"
[[ -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "crlf-session-root-keeps-version should keep predecessor"
[[ -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "crlf-session-root-keeps-version should keep latest"
assert_contains "$CASE_OUTPUT" "Warning: preserving cached larch version '29.1.20' because an active session is using it." "crlf-session-root-keeps-version warning"

GH_OUTPUT=$'29.1.22\n29.1.21\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.21"
INSTALL_RESULT_VERSION="29.1.22"
CACHED_VERSIONS="29.1.19 29.1.20 29.1.21 29.1.22"
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT SESSION_PINNED_ROOT_LITERAL TMP_SESSION_PINNED_VERSIONS
XDG_SESSION_PINNED_VERSIONS="29.1.20"
unset SET_LARCH_SESSIONS_DIR
run_case xdg-default-sessions-root-keeps-version
[[ "$CASE_RC" -eq 0 ]] || fail "xdg-default-sessions-root-keeps-version exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/29.1.19" ]] || fail "xdg-default-sessions-root-keeps-version should prune unused old version"
[[ -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "xdg-default-sessions-root-keeps-version should keep XDG-pinned version"
[[ -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "xdg-default-sessions-root-keeps-version should keep predecessor"
[[ -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "xdg-default-sessions-root-keeps-version should keep latest"
assert_contains "$CASE_OUTPUT" "Warning: preserving cached larch version '29.1.20' because an active session is using it." "xdg-default-sessions-root-keeps-version warning"

GH_OUTPUT=$'29.1.22\n29.1.21\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.21"
INSTALL_RESULT_VERSION="29.1.22"
CACHED_VERSIONS="29.1.19 29.1.20 29.1.21 29.1.22"
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT XDG_SESSION_PINNED_VERSIONS SET_LARCH_SESSIONS_DIR
TMP_SESSION_PINNED_VERSIONS="29.1.20"
run_case tmp-fallback-sessions-root-keeps-version
[[ "$CASE_RC" -eq 0 ]] || fail "tmp-fallback-sessions-root-keeps-version exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/29.1.19" ]] || fail "tmp-fallback-sessions-root-keeps-version should prune unused old version"
[[ -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "tmp-fallback-sessions-root-keeps-version should keep /tmp-pinned version"
[[ -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "tmp-fallback-sessions-root-keeps-version should keep predecessor"
[[ -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "tmp-fallback-sessions-root-keeps-version should keep latest"
assert_contains "$CASE_OUTPUT" "Warning: preserving cached larch version '29.1.20' because an active session is using it." "tmp-fallback-sessions-root-keeps-version warning"

printf 'PASS: test-upgrade-larch-prune.sh\n'
