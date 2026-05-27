#!/usr/bin/env bash

set -euo pipefail

# Coverage includes active-session pins plus mtime-based prune ordering:
# deterministic touch -t seeding, lexicographic equal-mtime tiebreaks, and
# STAT_FAIL_VERSION forcing both stat probes to fail for one cache directory.

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

assert_occurrences() {
    local haystack="$1" needle="$2" expected="$3" label="$4"
    local actual
    actual=$(grep -Foc "$needle" <<< "$haystack")
    [[ "$actual" -eq "$expected" ]] || fail "$label: expected $expected occurrences of [$needle], found $actual"
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

write_stub_rm() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

target="${*: -1}"
if [[ -n "${RM_FAIL_VERSION:-}" && "$target" == */"$RM_FAIL_VERSION" ]]; then
    exit 1
fi

/bin/rm "$@"
EOF
    chmod +x "$path"
}

write_stub_stat() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

target="${*: -1}"
if [[ -n "${STAT_FAIL_VERSION:-}" && "$target" == */"$STAT_FAIL_VERSION" ]]; then
    for arg in "$@"; do
        case "$arg" in
            -c|-f) exit 1 ;;
        esac
    done
fi

if [[ -n "${STAT_GNU_F_GARBAGE_VERSION:-}" && "$target" == */"$STAT_GNU_F_GARBAGE_VERSION" ]]; then
    for arg in "$@"; do
        case "$arg" in
            -c) exit 1 ;;
            -f)
                printf 'garbage filesystem info\n'
                exit 0
                ;;
        esac
    done
fi

/usr/bin/stat "$@"
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
    local fallback_session_roots
    local plugin_root session_idx tmp_session_name
    local _seed_idx _ts _override _override_version _override_ts
    local output rc

    mkdir -p "$home/.claude/plugins" "$bin" "$cache_root" "$sessions_root" "$xdg_cache_home"
    fallback_session_roots="${FALLBACK_SESSION_ROOTS:-$work/fallback-sessions}"
    mkdir -p "$work/fallback-sessions"
    plugin_root=$(make_plugin_root "$cache_root" "${PLUGIN_ROOT_VERSION:-29.1.20}")
    write_stub_claude "$bin/claude"
    write_stub_gh "$bin/gh"
    write_stub_rm "$bin/rm"
    write_stub_stat "$bin/stat"
    cat > "$state_file" <<STATE
INSTALLED_VERSION="${INITIAL_INSTALLED_VERSION:-}"
STATE
    for version in ${CACHED_VERSIONS:-}; do
        mkdir -p "$cache_root/$version"
    done
    _seed_idx=0
    for version in ${CACHED_VERSIONS:-}; do
        _seed_idx=$((_seed_idx + 1))
        printf -v _ts '20%02d01010001' "$((10 + _seed_idx))"
        touch -t "$_ts" -- "$cache_root/$version"
    done
    for _override in ${CACHE_MTIME_OVERRIDES:-}; do
        _override_version="${_override%%:*}"
        _override_ts="${_override#*:}"
        [[ -n "$_override_version" && -n "$_override_ts" ]] || continue
        [[ -d "$cache_root/$_override_version" ]] || continue
        touch -t "$_override_ts" -- "$cache_root/$_override_version"
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
            RM_FAIL_VERSION="${RM_FAIL_VERSION:-}" \
            STAT_FAIL_VERSION="${STAT_FAIL_VERSION:-}" \
            STAT_GNU_F_GARBAGE_VERSION="${STAT_GNU_F_GARBAGE_VERSION:-}" \
            LARCH_UPGRADE_FALLBACK_SESSION_ROOTS="$fallback_session_roots" \
            LARCH_BREADCRUMB_STREAM='' \
            LARCH_QUIET_BREADCRUMBS='' \
            LARCH_QUIET_DISABLE=1 \
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
            RM_FAIL_VERSION="${RM_FAIL_VERSION:-}" \
            STAT_FAIL_VERSION="${STAT_FAIL_VERSION:-}" \
            STAT_GNU_F_GARBAGE_VERSION="${STAT_GNU_F_GARBAGE_VERSION:-}" \
            LARCH_UPGRADE_FALLBACK_SESSION_ROOTS="$fallback_session_roots" \
            LARCH_BREADCRUMB_STREAM='' \
            LARCH_QUIET_BREADCRUMBS='' \
            LARCH_QUIET_DISABLE=1 \
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

GH_OUTPUT=$'29.1.30\n29.1.29\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.21"
INSTALL_RESULT_VERSION="29.1.30"
CACHED_VERSIONS="29.1.20 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28"
SESSION_PINNED_VERSIONS="29.1.21"
SET_LARCH_SESSIONS_DIR=1
unset FALLBACK_SESSION_ROOTS
unset SESSION_PINNED_ROOT
export CACHE_MTIME_OVERRIDES="29.1.20:209901010001 29.1.22:200001010001"
run_case active-session-keeps-version
[[ "$CASE_RC" -eq 0 ]] || fail "active-session-keeps-version exit $CASE_RC"
[[ -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "active-session-keeps-version should keep newest-touched unpinned version"
[[ ! -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "active-session-keeps-version should prune next oldest unpinned version"
[[ ! -d "$CASE_CACHE_ROOT/29.1.23" ]] || fail "active-session-keeps-version should prune oldest-by-mtime version"
for version in 29.1.20 29.1.21 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28 29.1.30; do
    [[ -d "$CASE_CACHE_ROOT/$version" ]] || fail "active-session-keeps-version should keep $version"
done
assert_contains "$CASE_OUTPUT" "Warning: preserving cached larch version '29.1.21' because an active session, stale session metadata, or the executing cached plugin root still references it." "active-session-keeps-version warning"
unset CACHE_MTIME_OVERRIDES

GH_OUTPUT=$'29.1.22\n29.1.21\n'
INITIAL_INSTALLED_VERSION="29.1.20"
PLUGIN_ROOT_VERSION="29.1.20"
INSTALL_RESULT_VERSION="29.1.22"
CACHED_VERSIONS="29.1.19 29.1.20 29.1.21 29.1.22"
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT XDG_SESSION_PINNED_VERSIONS TMP_SESSION_PINNED_VERSIONS
SET_LARCH_SESSIONS_DIR=1
unset FALLBACK_SESSION_ROOTS
run_case no-sessions-keeps-under-cap
[[ "$CASE_RC" -eq 0 ]] || fail "no-sessions-keeps-under-cap exit $CASE_RC"
for version in 29.1.19 29.1.20 29.1.21 29.1.22; do
    [[ -d "$CASE_CACHE_ROOT/$version" ]] || fail "no-sessions-keeps-under-cap should keep $version"
done

GH_OUTPUT=$'29.1.22\n29.1.21\n'
INITIAL_INSTALLED_VERSION="29.1.20"
PLUGIN_ROOT_VERSION="29.1.20"
INSTALL_RESULT_VERSION="29.1.22"
CACHED_VERSIONS="29.1.19 29.1.20 29.1.21 29.1.22"
SET_LARCH_SESSIONS_DIR=1
unset SESSION_PINNED_VERSIONS XDG_SESSION_PINNED_VERSIONS TMP_SESSION_PINNED_VERSIONS
SESSION_PINNED_ROOT="/cache/not-a-version"
unset FALLBACK_SESSION_ROOTS
run_case unparseable-session-keeps-under-cap
[[ "$CASE_RC" -eq 0 ]] || fail "unparseable-session-keeps-under-cap exit $CASE_RC"
for version in 29.1.19 29.1.20 29.1.21 29.1.22; do
    [[ -d "$CASE_CACHE_ROOT/$version" ]] || fail "unparseable-session-keeps-under-cap should keep $version"
done

GH_OUTPUT=$'29.1.30\n29.1.29\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.21"
INSTALL_RESULT_VERSION="29.1.30"
CACHED_VERSIONS="29.1.20 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28"
SET_LARCH_SESSIONS_DIR=1
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT XDG_SESSION_PINNED_VERSIONS TMP_SESSION_PINNED_VERSIONS
SESSION_PINNED_ROOT_LITERAL=$'LARCH_CLAUDE_PLUGIN_ROOT=/ignored/prefix/29.1.21\r   '
unset FALLBACK_SESSION_ROOTS
run_case crlf-session-root-keeps-version
[[ "$CASE_RC" -eq 0 ]] || fail "crlf-session-root-keeps-version exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "crlf-session-root-keeps-version should prune oldest unpinned version"
[[ ! -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "crlf-session-root-keeps-version should prune next oldest unpinned version"
for version in 29.1.21 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28 29.1.30; do
    [[ -d "$CASE_CACHE_ROOT/$version" ]] || fail "crlf-session-root-keeps-version should keep $version"
done
assert_contains "$CASE_OUTPUT" "Warning: preserving cached larch version '29.1.21' because an active session, stale session metadata, or the executing cached plugin root still references it." "crlf-session-root-keeps-version warning"

GH_OUTPUT=$'29.1.22\n29.1.21\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.21"
INSTALL_RESULT_VERSION="29.1.22"
CACHED_VERSIONS="29.1.19 29.1.20 29.1.21 29.1.22"
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT SESSION_PINNED_ROOT_LITERAL TMP_SESSION_PINNED_VERSIONS
XDG_SESSION_PINNED_VERSIONS="29.1.20"
unset SET_LARCH_SESSIONS_DIR
unset FALLBACK_SESSION_ROOTS
run_case xdg-default-sessions-root-keeps-version
[[ "$CASE_RC" -eq 0 ]] || fail "xdg-default-sessions-root-keeps-version exit $CASE_RC"
[[ -d "$CASE_CACHE_ROOT/29.1.19" ]] || fail "xdg-default-sessions-root-keeps-version should keep old version under cap"
[[ -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "xdg-default-sessions-root-keeps-version should keep XDG-pinned version"
[[ -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "xdg-default-sessions-root-keeps-version should keep predecessor"
[[ -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "xdg-default-sessions-root-keeps-version should keep latest"
assert_contains "$CASE_OUTPUT" "Warning: preserving cached larch version '29.1.20' because an active session, stale session metadata, or the executing cached plugin root still references it." "xdg-default-sessions-root-keeps-version warning"

GH_OUTPUT=$'29.1.22\n29.1.21\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.21"
INSTALL_RESULT_VERSION="29.1.22"
CACHED_VERSIONS="29.1.19 29.1.20 29.1.21 29.1.22"
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT XDG_SESSION_PINNED_VERSIONS SET_LARCH_SESSIONS_DIR
TMP_SESSION_PINNED_VERSIONS="29.1.20"
FALLBACK_SESSION_ROOTS="/tmp"
run_case tmp-fallback-sessions-root-keeps-version
[[ "$CASE_RC" -eq 0 ]] || fail "tmp-fallback-sessions-root-keeps-version exit $CASE_RC"
[[ -d "$CASE_CACHE_ROOT/29.1.19" ]] || fail "tmp-fallback-sessions-root-keeps-version should keep old version under cap"
[[ -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "tmp-fallback-sessions-root-keeps-version should keep /tmp-pinned version"
[[ -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "tmp-fallback-sessions-root-keeps-version should keep predecessor"
[[ -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "tmp-fallback-sessions-root-keeps-version should keep latest"
assert_contains "$CASE_OUTPUT" "Warning: preserving cached larch version '29.1.20' because an active session, stale session metadata, or the executing cached plugin root still references it." "tmp-fallback-sessions-root-keeps-version warning"

GH_OUTPUT=$'29.1.30\n29.1.29\n'
INITIAL_INSTALLED_VERSION="29.1.29"
PLUGIN_ROOT_VERSION="29.1.29"
INSTALL_RESULT_VERSION="29.1.30"
CACHED_VERSIONS="29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28 29.1.29"
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT SESSION_PINNED_ROOT_LITERAL XDG_SESSION_PINNED_VERSIONS TMP_SESSION_PINNED_VERSIONS
SET_LARCH_SESSIONS_DIR=1
unset FALLBACK_SESSION_ROOTS
export CACHE_MTIME_OVERRIDES="29.1.21:209901010001 29.1.28:200001010001"
run_case cap-prune-trims-to-eight
[[ "$CASE_RC" -eq 0 ]] || fail "cap-prune-trims-to-eight exit $CASE_RC"
for version in 29.1.22 29.1.28; do
    [[ ! -d "$CASE_CACHE_ROOT/$version" ]] || fail "cap-prune-trims-to-eight should prune $version"
done
for version in 29.1.21 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.29 29.1.30; do
    [[ -d "$CASE_CACHE_ROOT/$version" ]] || fail "cap-prune-trims-to-eight should keep $version"
done
unset CACHE_MTIME_OVERRIDES

GH_OUTPUT=$'29.1.30\n29.1.29\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.21"
INSTALL_RESULT_VERSION="29.1.30"
CACHED_VERSIONS="29.1.20 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28"
SESSION_PINNED_VERSIONS="29.1.20 29.1.21"
SET_LARCH_SESSIONS_DIR=1
unset FALLBACK_SESSION_ROOTS
unset SESSION_PINNED_ROOT SESSION_PINNED_ROOT_LITERAL XDG_SESSION_PINNED_VERSIONS TMP_SESSION_PINNED_VERSIONS
export CACHE_MTIME_OVERRIDES="29.1.28:200001010001 29.1.22:209901010001"
run_case multi-pinned-oldest-still-trims-to-eight
[[ "$CASE_RC" -eq 0 ]] || fail "multi-pinned-oldest-still-trims-to-eight exit $CASE_RC"
for version in 29.1.23 29.1.28; do
    [[ ! -d "$CASE_CACHE_ROOT/$version" ]] || fail "multi-pinned-oldest-still-trims-to-eight should prune $version"
done
for version in 29.1.20 29.1.21 29.1.22 29.1.24 29.1.25 29.1.26 29.1.27 29.1.30; do
    [[ -d "$CASE_CACHE_ROOT/$version" ]] || fail "multi-pinned-oldest-still-trims-to-eight should keep $version"
done
assert_contains "$CASE_OUTPUT" "Warning: preserving cached larch version '29.1.20' because an active session, stale session metadata, or the executing cached plugin root still references it." "multi-pinned-oldest-still-trims-to-eight warning 29.1.20"
assert_contains "$CASE_OUTPUT" "Warning: preserving cached larch version '29.1.21' because an active session, stale session metadata, or the executing cached plugin root still references it." "multi-pinned-oldest-still-trims-to-eight warning 29.1.21"
assert_occurrences "$CASE_OUTPUT" "Warning: preserving cached larch version '29.1.20' because an active session, stale session metadata, or the executing cached plugin root still references it." 1 "multi-pinned-oldest-still-trims-to-eight dedupe 29.1.20"
assert_occurrences "$CASE_OUTPUT" "Warning: preserving cached larch version '29.1.21' because an active session, stale session metadata, or the executing cached plugin root still references it." 1 "multi-pinned-oldest-still-trims-to-eight dedupe 29.1.21"
unset CACHE_MTIME_OVERRIDES

GH_OUTPUT=$'29.1.30\n29.1.29\n'
INITIAL_INSTALLED_VERSION="29.1.29"
PLUGIN_ROOT_VERSION="29.1.29"
INSTALL_RESULT_VERSION="29.1.30"
CACHED_VERSIONS="29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28 29.1.29"
RM_FAIL_VERSION="29.1.21"
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT SESSION_PINNED_ROOT_LITERAL XDG_SESSION_PINNED_VERSIONS TMP_SESSION_PINNED_VERSIONS
SET_LARCH_SESSIONS_DIR=1
unset FALLBACK_SESSION_ROOTS
run_case cap-prune-rm-failure-skips-retry
[[ "$CASE_RC" -eq 0 ]] || fail "cap-prune-rm-failure-skips-retry exit $CASE_RC"
[[ -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "cap-prune-rm-failure-skips-retry should retain failed version"
[[ ! -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "cap-prune-rm-failure-skips-retry should prune next oldest version"
[[ ! -d "$CASE_CACHE_ROOT/29.1.23" ]] || fail "cap-prune-rm-failure-skips-retry should prune the second-oldest remaining version"
for version in 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28 29.1.29 29.1.30; do
    [[ -d "$CASE_CACHE_ROOT/$version" ]] || fail "cap-prune-rm-failure-skips-retry should keep $version"
done
assert_contains "$CASE_OUTPUT" "Warning: failed to prune cached larch version '29.1.21'." "cap-prune-rm-failure-skips-retry warning"
assert_occurrences "$CASE_OUTPUT" "Warning: failed to prune cached larch version '29.1.21'." 1 "cap-prune-rm-failure-skips-retry warning count"
unset RM_FAIL_VERSION

GH_OUTPUT=$'42.0.10\n'
INITIAL_INSTALLED_VERSION="42.0.5"
PLUGIN_ROOT_VERSION="42.0.5"
INSTALL_RESULT_VERSION="42.0.10"
CACHED_VERSIONS="42.0.1 42.0.2 42.0.3 42.0.4 42.0.5 42.0.6 42.0.7 42.0.8 42.0.9"
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT SESSION_PINNED_ROOT_LITERAL XDG_SESSION_PINNED_VERSIONS TMP_SESSION_PINNED_VERSIONS
SET_LARCH_SESSIONS_DIR=1
unset FALLBACK_SESSION_ROOTS RM_FAIL_VERSION STAT_FAIL_VERSION
export CACHE_MTIME_OVERRIDES="42.0.9:200001010001 42.0.1:209901010001"
run_case mtime-asc-evicts-oldest-touched
[[ "$CASE_RC" -eq 0 ]] || fail "mtime-asc-evicts-oldest-touched exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/42.0.9" ]] || fail "mtime-asc-evicts-oldest-touched should prune newest semver with oldest mtime"
[[ -d "$CASE_CACHE_ROOT/42.0.1" ]] || fail "mtime-asc-evicts-oldest-touched should keep oldest semver with newest mtime"
[[ -d "$CASE_CACHE_ROOT/42.0.10" ]] || fail "mtime-asc-evicts-oldest-touched should keep latest"
unset CACHE_MTIME_OVERRIDES

GH_OUTPUT=$'9.0.0\n'
INITIAL_INSTALLED_VERSION="1.0.2"
PLUGIN_ROOT_VERSION="1.0.2"
INSTALL_RESULT_VERSION="9.0.0"
CACHED_VERSIONS="1.0.1 1.0.2 1.0.3 1.0.4 5.0.1 5.0.2 5.0.3 5.0.4 5.0.5"
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT SESSION_PINNED_ROOT_LITERAL XDG_SESSION_PINNED_VERSIONS TMP_SESSION_PINNED_VERSIONS
SET_LARCH_SESSIONS_DIR=1
unset FALLBACK_SESSION_ROOTS RM_FAIL_VERSION STAT_FAIL_VERSION
export CACHE_MTIME_OVERRIDES="1.0.1:209901010001 1.0.2:209901010002 5.0.4:200001010001 5.0.5:200001010002"
run_case sparse-used-versions-survive-large-semver-jump
[[ "$CASE_RC" -eq 0 ]] || fail "sparse-used-versions-survive-large-semver-jump exit $CASE_RC"
[[ -d "$CASE_CACHE_ROOT/1.0.1" ]] || fail "sparse-used-versions-survive-large-semver-jump should keep touched 1.0.1"
[[ -d "$CASE_CACHE_ROOT/1.0.2" ]] || fail "sparse-used-versions-survive-large-semver-jump should keep touched 1.0.2"
[[ ! -d "$CASE_CACHE_ROOT/5.0.4" ]] || fail "sparse-used-versions-survive-large-semver-jump should prune stale higher-semver 5.0.4"
[[ ! -d "$CASE_CACHE_ROOT/5.0.5" ]] || fail "sparse-used-versions-survive-large-semver-jump should prune stale higher-semver 5.0.5"
[[ -d "$CASE_CACHE_ROOT/9.0.0" ]] || fail "sparse-used-versions-survive-large-semver-jump should keep latest"
unset CACHE_MTIME_OVERRIDES

GH_OUTPUT=$'42.1.0\n'
INITIAL_INSTALLED_VERSION="42.0.5"
PLUGIN_ROOT_VERSION="42.0.5"
INSTALL_RESULT_VERSION="42.1.0"
CACHED_VERSIONS="42.0.1 42.0.2 42.0.3 42.0.4 42.0.5 42.0.7 42.0.8 42.0.9"
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT SESSION_PINNED_ROOT_LITERAL XDG_SESSION_PINNED_VERSIONS TMP_SESSION_PINNED_VERSIONS
SET_LARCH_SESSIONS_DIR=1
unset FALLBACK_SESSION_ROOTS RM_FAIL_VERSION STAT_FAIL_VERSION
export CACHE_MTIME_OVERRIDES="42.0.1:209901010001 42.0.2:209901010001 42.0.3:209901010001 42.0.4:209901010001 42.0.5:209901010001 42.0.7:200001010001 42.0.8:200001010001 42.0.9:200001010001"
run_case mtime-tiebreaker-lexicographic-basename
[[ "$CASE_RC" -eq 0 ]] || fail "mtime-tiebreaker-lexicographic-basename exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/42.0.7" ]] || fail "mtime-tiebreaker-lexicographic-basename should prune lexicographically earliest equal-mtime version"
[[ -d "$CASE_CACHE_ROOT/42.0.8" ]] || fail "mtime-tiebreaker-lexicographic-basename should keep 42.0.8"
[[ -d "$CASE_CACHE_ROOT/42.0.9" ]] || fail "mtime-tiebreaker-lexicographic-basename should keep 42.0.9"
unset CACHE_MTIME_OVERRIDES

GH_OUTPUT=$'42.0.10\n'
INITIAL_INSTALLED_VERSION="42.0.9"
PLUGIN_ROOT_VERSION="42.0.9"
INSTALL_RESULT_VERSION="42.0.10"
CACHED_VERSIONS="42.0.1 42.0.2 42.0.3 42.0.4 42.0.5 42.0.6 42.0.7 42.0.8 42.0.9"
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT SESSION_PINNED_ROOT_LITERAL XDG_SESSION_PINNED_VERSIONS TMP_SESSION_PINNED_VERSIONS
SET_LARCH_SESSIONS_DIR=1
STAT_FAIL_VERSION="42.0.5"
unset FALLBACK_SESSION_ROOTS RM_FAIL_VERSION
run_case stat-fallback-mtime-zero
[[ "$CASE_RC" -eq 0 ]] || fail "stat-fallback-mtime-zero exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/42.0.5" ]] || fail "stat-fallback-mtime-zero should prune stat-failed version first"
[[ -d "$CASE_CACHE_ROOT/42.0.10" ]] || fail "stat-fallback-mtime-zero should keep latest"
unset STAT_FAIL_VERSION

GH_OUTPUT=$'42.0.10\n'
INITIAL_INSTALLED_VERSION="42.0.9"
PLUGIN_ROOT_VERSION="42.0.9"
INSTALL_RESULT_VERSION="42.0.10"
CACHED_VERSIONS="42.0.1 42.0.2 42.0.3 42.0.4 42.0.5 42.0.6 42.0.7 42.0.8 42.0.9"
unset SESSION_PINNED_VERSIONS SESSION_PINNED_ROOT SESSION_PINNED_ROOT_LITERAL XDG_SESSION_PINNED_VERSIONS TMP_SESSION_PINNED_VERSIONS
SET_LARCH_SESSIONS_DIR=1
STAT_GNU_F_GARBAGE_VERSION="42.0.6"
unset FALLBACK_SESSION_ROOTS RM_FAIL_VERSION STAT_FAIL_VERSION
run_case stat-garbage-fallback-mtime-zero
[[ "$CASE_RC" -eq 0 ]] || fail "stat-garbage-fallback-mtime-zero exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/42.0.6" ]] || fail "stat-garbage-fallback-mtime-zero should prune non-numeric stat-fallback version first"
[[ -d "$CASE_CACHE_ROOT/42.0.10" ]] || fail "stat-garbage-fallback-mtime-zero should keep latest"
unset STAT_GNU_F_GARBAGE_VERSION

printf 'PASS: test-upgrade-larch-prune.sh\n'
