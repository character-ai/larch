#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/upgrade-larch/scripts/upgrade-larch.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-upgrade-larch.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    grep -Fq "$needle" <<< "$haystack" || fail "$label: missing [$needle]"
}

assert_not_contains() {
    local haystack="$1" needle="$2" label="$3"
    if grep -Fq "$needle" <<< "$haystack"; then
        fail "$label: unexpectedly found [$needle]"
    fi
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
        INSTALL_FAIL=0
    fi
}

write_state() {
    cat > "$state_file" <<STATE
INSTALLED_VERSION="${INSTALLED_VERSION:-}"
INSTALL_FAIL="${INSTALL_FAIL:-0}"
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
        printf 'uninstall\n' >> "${TEST_EVENT_LOG:?}"
        INSTALLED_VERSION=""
        write_state
        ;;
    install)
        printf 'install\n' >> "${TEST_EVENT_LOG:?}"
        if [[ "${INSTALL_FAIL:-0}" == "1" ]]; then
            exit 1
        fi
        if [[ -n "${INSTALL_RESULT_VERSION:-}" ]]; then
            INSTALLED_VERSION="$INSTALL_RESULT_VERSION"
        fi
        if [[ -n "${INSTALL_CACHE_VERSION:-}" ]]; then
            mkdir -p "$cache_dir/$INSTALL_CACHE_VERSION"
        fi
        write_state
        ;;
    marketplace)
        printf 'marketplace-%s\n' "$1" >> "${TEST_EVENT_LOG:?}"
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

if [[ "${GH_FAIL:-0}" == "1" ]]; then
    printf '%s\n' "${GH_STDERR_MESSAGE:-token=secret}" >&2
    exit "${GH_FAIL_STATUS:-1}"
fi

printf '%s' "${GH_OUTPUT:-}"
EOF
    chmod +x "$path"
}

run_case() {
    local name="$1"
    local work="$TMP/$name"
    local home="$work/home"
    local bin="$work/bin"
    local state_file="$work/state.sh"
    local event_log="$work/events.log"
    local cache_root="$work/cache"
    local plugin_root
    local output rc

    mkdir -p "$home/.claude/plugins" "$bin" "$cache_root"
    : > "$event_log"
    plugin_root=$(make_plugin_root "$cache_root" "${PLUGIN_ROOT_VERSION:-1.0.0}")
    write_stub_claude "$bin/claude"
    write_stub_gh "$bin/gh"
    cat > "$state_file" <<STATE
INSTALLED_VERSION="${INITIAL_INSTALLED_VERSION:-}"
INSTALL_FAIL="${INSTALL_FAIL:-0}"
STATE
    if [[ -n "${INSTALLED_PLUGINS_VERSION:-}" ]]; then
        cat > "$home/.claude/plugins/installed_plugins.json" <<JSON
{
  "plugins": {
    "larch@larch-local": {
      "version": "${INSTALLED_PLUGINS_VERSION}"
    }
  }
}
JSON
    fi
    for version in ${CACHED_VERSIONS:-}; do
        mkdir -p "$cache_root/$version"
    done

    set +e
    output=$(
        HOME="$home" \
        PATH="$bin:$PATH" \
        CLAUDE_PLUGIN_ROOT="$plugin_root" \
        TEST_STATE_FILE="$state_file" \
        TEST_CACHE_DIR="$cache_root" \
        TEST_EVENT_LOG="$event_log" \
        GH_OUTPUT="${GH_OUTPUT:-}" \
        GH_FAIL="${GH_FAIL:-0}" \
        GH_FAIL_STATUS="${GH_FAIL_STATUS:-1}" \
        GH_STDERR_MESSAGE="${GH_STDERR_MESSAGE:-token=secret}" \
        INSTALL_RESULT_VERSION="${INSTALL_RESULT_VERSION:-}" \
        INSTALL_CACHE_VERSION="${INSTALL_CACHE_VERSION:-}" \
        LARCH_QUIET_BREADCRUMBS=1 \
        "$SCRIPT" 2>&1
    )
    rc=$?
    set -e

    CASE_OUTPUT="$output"
    CASE_RC="$rc"
    CASE_EVENT_LOG="$event_log"
    CASE_CACHE_ROOT="$cache_root"
}

# Latest valid stable can appear after invalid gh/stderr-like lines.
GH_OUTPUT=$'error: noisy line\n31.0.0\npreview\n30.9.0\n'
INITIAL_INSTALLED_VERSION="30.8.0"
PLUGIN_ROOT_VERSION="30.8.0"
INSTALL_RESULT_VERSION="31.0.0"
INSTALL_CACHE_VERSION="31.0.0"
CACHED_VERSIONS="29.0.0 30.8.0 30.9.0 31.0.0"
run_case stable-filter
[[ "$CASE_RC" -eq 0 ]] || fail "stable-filter exit $CASE_RC"
assert_contains "$CASE_OUTPUT" "Upgrading larch from 30.8.0 to 31.0.0..." "stable-filter latest"
assert_contains "$CASE_OUTPUT" "Verified: larch 31.0.0 installed successfully." "stable-filter verify"
assert_not_contains "$CASE_OUTPUT" "Upgrading larch from 30.8.0 to error: noisy line..." "stable-filter ignored invalid first line"
[[ -d "$CASE_CACHE_ROOT/29.0.0" ]] || fail "stable-filter: should keep all versions when within 8-version limit"

# Idempotency should use installed metadata, not the still-running plugin root.
GH_OUTPUT=$'31.0.0\n30.9.0\n'
INITIAL_INSTALLED_VERSION="31.0.0"
INSTALLED_PLUGINS_VERSION="31.0.0"
PLUGIN_ROOT_VERSION="30.9.0"
unset INSTALL_RESULT_VERSION INSTALL_CACHE_VERSION CACHED_VERSIONS
run_case idempotent-installed
[[ "$CASE_RC" -eq 0 ]] || fail "idempotent-installed exit $CASE_RC"
assert_contains "$CASE_OUTPUT" "Already at latest stable larch release (31.0.0)." "idempotent-installed message"
if [[ -s "$CASE_EVENT_LOG" ]]; then
    fail "idempotent-installed should not perform uninstall/install"
fi

# Verification should succeed when the CLI reports the target even if the cache
# directory for that version is not present yet.
GH_OUTPUT=$'31.0.0\n30.9.0\n'
INITIAL_INSTALLED_VERSION="30.9.0"
PLUGIN_ROOT_VERSION="30.9.0"
INSTALL_RESULT_VERSION="31.0.0"
unset INSTALL_CACHE_VERSION
CACHED_VERSIONS="30.9.0"
run_case verify-without-cache-dir
[[ "$CASE_RC" -eq 0 ]] || fail "verify-without-cache-dir exit $CASE_RC"
assert_contains "$CASE_OUTPUT" "Verified: larch 31.0.0 installed successfully." "verify-without-cache-dir verify"
assert_not_contains "$CASE_OUTPUT" "Upgrade incomplete" "verify-without-cache-dir no failure"

# Pruning removes cached versions newer than the verified stable release even
# when the cache is already under the 8-version limit.
GH_OUTPUT=$'31.0.0\n30.9.0\n'
INITIAL_INSTALLED_VERSION="30.8.0"
PLUGIN_ROOT_VERSION="30.8.0"
INSTALL_RESULT_VERSION="31.0.0"
INSTALL_CACHE_VERSION="31.0.0"
CACHED_VERSIONS="29.0.0 30.0.0 31.0.0 99.0.0"
run_case prune-stray-newer-under-cap
[[ "$CASE_RC" -eq 0 ]] || fail "prune-stray-newer-under-cap exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/99.0.0" ]] || fail "prune-stray-newer-under-cap should prune 99.0.0"
for version in 29.0.0 30.0.0 31.0.0; do
    [[ -d "$CASE_CACHE_ROOT/$version" ]] || fail "prune-stray-newer-under-cap should keep $version"
done

# Pruning keeps the verified stable cache dir even when more than 8 cached
# versions are present.
GH_OUTPUT=$'31.0.0\n30.9.0\n'
INITIAL_INSTALLED_VERSION="30.8.0"
PLUGIN_ROOT_VERSION="30.9.0"
INSTALL_RESULT_VERSION="31.0.0"
INSTALL_CACHE_VERSION="31.0.0"
CACHED_VERSIONS="31.0.0 32.0.0 33.0.0 34.0.0 35.0.0 36.0.0 37.0.0 38.0.0 39.0.0"
run_case preserve-verified-stable
[[ "$CASE_RC" -eq 0 ]] || fail "preserve-verified-stable exit $CASE_RC"
[[ -d "$CASE_CACHE_ROOT/31.0.0" ]] || fail "preserve-verified-stable should keep 31.0.0"
for version in 32.0.0 33.0.0 34.0.0 35.0.0 36.0.0 37.0.0 38.0.0 39.0.0; do
    [[ ! -d "$CASE_CACHE_ROOT/$version" ]] || fail "preserve-verified-stable should prune $version"
done

# Pruning removes cached versions newer than the verified stable release before
# enforcing the 8-version retention limit.
GH_OUTPUT=$'31.0.0\n30.9.0\n'
INITIAL_INSTALLED_VERSION="30.8.0"
PLUGIN_ROOT_VERSION="30.9.0"
INSTALL_RESULT_VERSION="31.0.0"
INSTALL_CACHE_VERSION="31.0.0"
CACHED_VERSIONS="20.0.0 21.0.0 22.0.0 23.0.0 24.0.0 25.0.0 26.0.0 27.0.0 28.0.0 29.0.0 30.9.0 31.0.0 99.0.0"
run_case prune-oldest-after-sanitize
[[ "$CASE_RC" -eq 0 ]] || fail "prune-oldest-after-sanitize exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/99.0.0" ]] || fail "prune-oldest-after-sanitize should prune 99.0.0"
for version in 20.0.0 21.0.0 22.0.0 23.0.0; do
    [[ ! -d "$CASE_CACHE_ROOT/$version" ]] || fail "prune-oldest-after-sanitize should prune $version"
done
for version in 24.0.0 25.0.0 26.0.0 27.0.0 28.0.0 29.0.0 30.9.0 31.0.0; do
    [[ -d "$CASE_CACHE_ROOT/$version" ]] || fail "prune-oldest-after-sanitize should keep $version"
done

# gh failure output should not be echoed back verbatim.
GH_FAIL=1
GH_FAIL_STATUS=42
GH_STDERR_MESSAGE='token=secret account=private'
unset GH_OUTPUT
INITIAL_INSTALLED_VERSION="30.8.0"
PLUGIN_ROOT_VERSION="30.8.0"
INSTALL_RESULT_VERSION="30.8.1"
INSTALL_CACHE_VERSION="30.8.1"
unset CACHED_VERSIONS INSTALLED_PLUGINS_VERSION
run_case gh-failure-redaction
[[ "$CASE_RC" -eq 0 ]] || fail "gh-failure-redaction exit $CASE_RC"
assert_contains "$CASE_OUTPUT" "failed to query GitHub stable releases via gh (exit 42)" "gh-failure-redaction warning"
assert_not_contains "$CASE_OUTPUT" "token=secret" "gh-failure-redaction redacted stderr"

printf 'PASS: test-upgrade-larch.sh\n'
