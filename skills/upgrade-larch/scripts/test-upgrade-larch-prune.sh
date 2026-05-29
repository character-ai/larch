#!/usr/bin/env bash

set -euo pipefail

# Coverage for max-8 install-stamp prune in upgrade-larch.sh:
# .larch-installed-at ordering (stamped before un-stamped, timestamp desc,
# version desc), dir-mtime fallback for un-stamped dirs,
# ACTUAL_VERSION target seeding, and already-latest stamp+prune without reinstall.

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

assert_not_contains() {
    local haystack="$1" needle="$2" label="$3"
    if grep -Fq "$needle" <<< "$haystack"; then
        fail "$label: unexpectedly found [$needle]"
    fi
}

count_cached_versions() {
    local cache_root="$1"
    local count=0
    local dir version
    shopt -s nullglob
    for dir in "$cache_root"/[0-9]*/; do
        [ -d "$dir" ] || continue
        version=$(basename "${dir%/}")
        [[ "$version" =~ ^[0-9]+(\.[0-9]+)*$ ]] || continue
        count=$((count + 1))
    done
    shopt -u nullglob
    printf '%s\n' "$count"
}

make_plugin_root() {
    local base="$1" version="$2"
    local root="$base/$version"
    mkdir -p "$root/scripts"
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$root/scripts/lib-quiet.sh"
    printf '%s\n' "$root"
}

write_install_stamp() {
    local cache_root="$1" version="$2" epoch="$3"
    printf '%s\n' "$epoch" > "$cache_root/$version/.larch-installed-at"
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
        if [[ -n "${INSTALL_CACHE_VERSION:-}" ]]; then
            mkdir -p "$cache_dir/$INSTALL_CACHE_VERSION"
        fi
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
    local plugin_root
    local stamp_pair stamp_version stamp_epoch
    local mtime_override mtime_version mtime_ts
    local output rc

    mkdir -p "$home/.claude/plugins" "$bin" "$cache_root"
    plugin_root=$(make_plugin_root "$cache_root" "${PLUGIN_ROOT_VERSION:-29.1.20}")
    write_stub_claude "$bin/claude"
    write_stub_gh "$bin/gh"
    write_stub_rm "$bin/rm"
    write_stub_stat "$bin/stat"
    cat > "$state_file" <<STATE
INSTALLED_VERSION="${INITIAL_INSTALLED_VERSION:-}"
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
    for stamp_pair in ${INSTALL_STAMPS:-}; do
        stamp_version="${stamp_pair%%:*}"
        stamp_epoch="${stamp_pair#*:}"
        [[ -n "$stamp_version" && -n "$stamp_epoch" ]] || continue
        [[ -d "$cache_root/$stamp_version" ]] || continue
        write_install_stamp "$cache_root" "$stamp_version" "$stamp_epoch"
    done
    for mtime_override in ${CACHE_MTIME_OVERRIDES:-}; do
        mtime_version="${mtime_override%%:*}"
        mtime_ts="${mtime_override#*:}"
        [[ -n "$mtime_version" && -n "$mtime_ts" ]] || continue
        [[ -d "$cache_root/$mtime_version" ]] || continue
        touch -t "$mtime_ts" -- "$cache_root/$mtime_version"
    done
    if [[ -n "${READONLY_STAMP_VERSION:-}" && -d "$cache_root/$READONLY_STAMP_VERSION" ]]; then
        chmod 500 "$cache_root/$READONLY_STAMP_VERSION"
    fi

    set +e
    output=$(
        HOME="$home" \
        PATH="$bin:$PATH" \
        CLAUDE_PLUGIN_ROOT="$plugin_root" \
        TEST_STATE_FILE="$state_file" \
        TEST_CACHE_DIR="$cache_root" \
        GH_OUTPUT="${GH_OUTPUT:-}" \
        INSTALL_RESULT_VERSION="${INSTALL_RESULT_VERSION:-}" \
        INSTALL_CACHE_VERSION="${INSTALL_CACHE_VERSION:-}" \
        RM_FAIL_VERSION="${RM_FAIL_VERSION:-}" \
        STAT_FAIL_VERSION="${STAT_FAIL_VERSION:-}" \
        LARCH_QUIET_DISABLE=1 \
        "$SCRIPT" 2>&1
    )
    rc=$?
    set -e

    if [[ -n "${READONLY_STAMP_VERSION:-}" && -d "$cache_root/$READONLY_STAMP_VERSION" ]]; then
        chmod 700 "$cache_root/$READONLY_STAMP_VERSION"
    fi

    CASE_OUTPUT="$output"
    CASE_RC="$rc"
    CASE_CACHE_ROOT="$cache_root"
}

GH_OUTPUT=$'29.1.30\n29.1.29\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.21"
INSTALL_RESULT_VERSION="29.1.30"
INSTALL_CACHE_VERSION="29.1.30"
CACHED_VERSIONS="29.1.20 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28"
INSTALL_STAMPS="29.1.20:1000000 29.1.21:1000001 29.1.22:1000002 29.1.23:1000003 29.1.24:1000004 29.1.25:1000005 29.1.26:1000006 29.1.27:1000007 29.1.28:1000008"
unset CACHE_MTIME_OVERRIDES
run_case over-eight-stamped-keeps-eight-newest
[[ "$CASE_RC" -eq 0 ]] || fail "over-eight-stamped-keeps-eight-newest exit $CASE_RC"
[[ "$(count_cached_versions "$CASE_CACHE_ROOT")" -eq 8 ]] || fail "over-eight-stamped-keeps-eight-newest should retain exactly 8 dirs"
[[ ! -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "over-eight-stamped-keeps-eight-newest should prune 29.1.20"
[[ ! -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "over-eight-stamped-keeps-eight-newest should prune 29.1.21"
[[ -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "over-eight-stamped-keeps-eight-newest should keep 29.1.22 in newest eight"
for version in 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28 29.1.30; do
    [[ -d "$CASE_CACHE_ROOT/$version" ]] || fail "over-eight-stamped-keeps-eight-newest should keep $version"
done
assert_contains "$CASE_OUTPUT" "Pruning old larch versions" "over-eight-stamped-keeps-eight-newest prune banner"

GH_OUTPUT=$'29.1.22\n29.1.21\n'
INITIAL_INSTALLED_VERSION="29.1.20"
PLUGIN_ROOT_VERSION="29.1.20"
INSTALL_RESULT_VERSION="29.1.22"
INSTALL_CACHE_VERSION="29.1.22"
CACHED_VERSIONS="29.1.19 29.1.20 29.1.21 29.1.22"
INSTALL_STAMPS="29.1.19:100 29.1.20:101 29.1.21:102 29.1.22:103"
unset CACHE_MTIME_OVERRIDES
run_case under-cap-keeps-all
[[ "$CASE_RC" -eq 0 ]] || fail "under-cap-keeps-all exit $CASE_RC"
[[ "$(count_cached_versions "$CASE_CACHE_ROOT")" -eq 4 ]] || fail "under-cap-keeps-all should retain all 4 dirs"
for version in 29.1.19 29.1.20 29.1.21 29.1.22; do
    [[ -d "$CASE_CACHE_ROOT/$version" ]] || fail "under-cap-keeps-all should keep $version"
done
assert_contains "$CASE_OUTPUT" "No old versions to prune." "under-cap-keeps-all no-op prune"

GH_OUTPUT=$'29.1.30\n29.1.29\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.21"
INSTALL_RESULT_VERSION="29.1.30"
INSTALL_CACHE_VERSION="29.1.30"
CACHED_VERSIONS="29.1.20 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28"
INSTALL_STAMPS="29.1.20:9000000000 29.1.21:8000000000 29.1.22:7000000000 29.1.23:6000000000 29.1.24:5000000000 29.1.25:4000000000 29.1.26:3000000000 29.1.27:2000000000 29.1.28:1000000000"
export CACHE_MTIME_OVERRIDES="29.1.20:200001010001 29.1.28:209901010001"
run_case install-stamp-ordering
[[ "$CASE_RC" -eq 0 ]] || fail "install-stamp-ordering exit $CASE_RC"
[[ -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "install-stamp-ordering should keep newest-stamped 29.1.20 despite oldest mtime"
[[ ! -d "$CASE_CACHE_ROOT/29.1.28" ]] || fail "install-stamp-ordering should prune oldest-stamped 29.1.28 despite newest mtime"
[[ ! -d "$CASE_CACHE_ROOT/29.1.27" ]] || fail "install-stamp-ordering should prune 29.1.27"
[[ "$(count_cached_versions "$CASE_CACHE_ROOT")" -eq 8 ]] || fail "install-stamp-ordering should retain exactly 8 dirs"
unset CACHE_MTIME_OVERRIDES

GH_OUTPUT=$'29.1.30\n29.1.29\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.30"
INSTALL_RESULT_VERSION="29.1.30"
INSTALL_CACHE_VERSION="29.1.30"
CACHED_VERSIONS="29.1.20 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28 29.1.29"
INSTALL_STAMPS="29.1.20:9999999999999"
export CACHE_MTIME_OVERRIDES="29.1.21:209901010001 29.1.22:209901010002 29.1.23:209901010003 29.1.24:209901010004 29.1.25:209901010005 29.1.26:209901010006 29.1.27:209901010007 29.1.28:209901010008 29.1.29:209901010009"
run_case stamp-beats-unstamped-mtime
[[ "$CASE_RC" -eq 0 ]] || fail "stamp-beats-unstamped-mtime exit $CASE_RC"
[[ -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "stamp-beats-unstamped-mtime should keep stamped 29.1.20 when its install stamp is newest"
[[ ! -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "stamp-beats-unstamped-mtime should prune oldest un-stamped 29.1.21"
[[ ! -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "stamp-beats-unstamped-mtime should prune 29.1.22"
[[ ! -d "$CASE_CACHE_ROOT/29.1.23" ]] || fail "stamp-beats-unstamped-mtime should prune 29.1.23"
[[ "$(count_cached_versions "$CASE_CACHE_ROOT")" -eq 8 ]] || fail "stamp-beats-unstamped-mtime should retain exactly 8 dirs"
unset CACHE_MTIME_OVERRIDES INSTALL_STAMPS

GH_OUTPUT=$'42.0.10\n'
INITIAL_INSTALLED_VERSION="42.0.5"
PLUGIN_ROOT_VERSION="42.0.5"
INSTALL_RESULT_VERSION="42.0.10"
INSTALL_CACHE_VERSION="42.0.10"
CACHED_VERSIONS="42.0.1 42.0.2 42.0.3 42.0.4 42.0.5 42.0.6 42.0.7 42.0.8 42.0.9"
unset INSTALL_STAMPS
export CACHE_MTIME_OVERRIDES="42.0.9:200001010001 42.0.1:209901010001"
run_case mtime-fallback-unstamped
[[ "$CASE_RC" -eq 0 ]] || fail "mtime-fallback-unstamped exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/42.0.9" ]] || fail "mtime-fallback-unstamped should prune oldest-mtime 42.0.9"
[[ -d "$CASE_CACHE_ROOT/42.0.1" ]] || fail "mtime-fallback-unstamped should keep newest-mtime 42.0.1"
[[ -d "$CASE_CACHE_ROOT/42.0.10" ]] || fail "mtime-fallback-unstamped should keep latest install"
[[ "$(count_cached_versions "$CASE_CACHE_ROOT")" -eq 8 ]] || fail "mtime-fallback-unstamped should retain exactly 8 dirs"
unset CACHE_MTIME_OVERRIDES

GH_OUTPUT=$'29.1.20\n'
INITIAL_INSTALLED_VERSION="29.1.20"
PLUGIN_ROOT_VERSION="29.1.20"
INSTALL_RESULT_VERSION="29.1.20"
unset INSTALL_CACHE_VERSION
CACHED_VERSIONS="29.1.20 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28 29.1.29"
INSTALL_STAMPS="29.1.20:100 29.1.21:9999999991 29.1.22:9999999992 29.1.23:9999999993 29.1.24:9999999994 29.1.25:9999999995 29.1.26:9999999996 29.1.27:9999999997 29.1.28:9999999998 29.1.29:9999999999"
unset CACHE_MTIME_OVERRIDES
run_case just-installed-seeded
[[ "$CASE_RC" -eq 0 ]] || fail "just-installed-seeded exit $CASE_RC"
[[ -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "just-installed-seeded should retain seeded ACTUAL_VERSION 29.1.20"
[[ ! -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "just-installed-seeded should prune 29.1.21"
[[ ! -d "$CASE_CACHE_ROOT/29.1.22" ]] || fail "just-installed-seeded should prune 29.1.22"
[[ "$(count_cached_versions "$CASE_CACHE_ROOT")" -eq 8 ]] || fail "just-installed-seeded should retain exactly 8 dirs"
assert_contains "$CASE_OUTPUT" "Already at latest stable larch release (29.1.20)." "just-installed-seeded already-latest path"

GH_OUTPUT=$'29.1.30\n29.1.29\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.30"
INSTALL_RESULT_VERSION="29.1.30"
INSTALL_CACHE_VERSION="29.1.30"
CACHED_VERSIONS="29.1.20 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28"
INSTALL_STAMPS="29.1.20:1000000 29.1.21:1000001 29.1.22:1000002 29.1.23:1000003 29.1.24:1000004 29.1.25:1000005 29.1.26:1000006 29.1.27:1000007 29.1.28:1000008"
unset CACHE_MTIME_OVERRIDES
unset READONLY_STAMP_VERSION
run_case install-then-prune-fills-eight
[[ "$CASE_RC" -eq 0 ]] || fail "install-then-prune-fills-eight exit $CASE_RC"
[[ -d "$CASE_CACHE_ROOT/29.1.30" ]] || fail "install-then-prune-fills-eight should create installed target dir"
[[ -f "$CASE_CACHE_ROOT/29.1.30/.larch-installed-at" ]] || fail "install-then-prune-fills-eight should write fresh install stamp"
stamp_contents=$(tr -d '\r\n' < "$CASE_CACHE_ROOT/29.1.30/.larch-installed-at")
[[ "$stamp_contents" =~ ^[0-9]+$ ]] || fail "install-then-prune-fills-eight stamp must be numeric epoch"
[[ "$(count_cached_versions "$CASE_CACHE_ROOT")" -eq 8 ]] || fail "install-then-prune-fills-eight should retain exactly 8 dirs"
[[ ! -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "install-then-prune-fills-eight should prune oldest stamped 29.1.20"
[[ ! -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "install-then-prune-fills-eight should prune 29.1.21"

GH_OUTPUT=$'29.1.30\n29.1.29\n'
INITIAL_INSTALLED_VERSION="29.1.21"
PLUGIN_ROOT_VERSION="29.1.21"
INSTALL_RESULT_VERSION="29.1.30"
unset INSTALL_CACHE_VERSION
CACHED_VERSIONS="29.1.20 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28"
INSTALL_STAMPS="29.1.20:1000000 29.1.21:1000001 29.1.22:1000002 29.1.23:1000003 29.1.24:1000004 29.1.25:1000005 29.1.26:1000006 29.1.27:1000007 29.1.28:1000008"
unset CACHE_MTIME_OVERRIDES READONLY_STAMP_VERSION
run_case absent-target-cache-dir-fills-eight
[[ "$CASE_RC" -eq 0 ]] || fail "absent-target-cache-dir-fills-eight exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/29.1.30" ]] || fail "absent-target-cache-dir-fills-eight should leave missing target cache dir absent"
[[ "$(count_cached_versions "$CASE_CACHE_ROOT")" -eq 8 ]] || fail "absent-target-cache-dir-fills-eight should retain exactly 8 real dirs"
[[ ! -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "absent-target-cache-dir-fills-eight should prune oldest stamped 29.1.20"
[[ -d "$CASE_CACHE_ROOT/29.1.21" ]] || fail "absent-target-cache-dir-fills-eight should not count missing target toward the cap"

GH_OUTPUT=$'29.1.28\n'
INITIAL_INSTALLED_VERSION="29.1.28"
PLUGIN_ROOT_VERSION="29.1.28"
INSTALL_RESULT_VERSION="29.1.28"
INSTALL_CACHE_VERSION="29.1.28"
CACHED_VERSIONS="29.1.20 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28"
INSTALL_STAMPS="29.1.20:100 29.1.21:101 29.1.22:102 29.1.23:103 29.1.24:104 29.1.25:105 29.1.26:106 29.1.27:107"
unset CACHE_MTIME_OVERRIDES
READONLY_STAMP_VERSION="29.1.28"
run_case stamp-write-failure-existing-target
[[ "$CASE_RC" -eq 0 ]] || fail "stamp-write-failure-existing-target exit $CASE_RC"
assert_contains "$CASE_OUTPUT" "Warning: failed to write install stamp for cached larch version '29.1.28'." "stamp-write-failure-existing-target warning"
[[ -d "$CASE_CACHE_ROOT/29.1.28" ]] || fail "stamp-write-failure-existing-target should retain seeded target dir"
[[ "$(count_cached_versions "$CASE_CACHE_ROOT")" -eq 8 ]] || fail "stamp-write-failure-existing-target should retain exactly 8 dirs"
[[ ! -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "stamp-write-failure-existing-target should prune only the oldest competitor"

GH_OUTPUT=$'29.1.28\n'
INITIAL_INSTALLED_VERSION="29.1.28"
PLUGIN_ROOT_VERSION="29.1.28"
INSTALL_RESULT_VERSION="29.1.28"
INSTALL_CACHE_VERSION="29.1.28"
CACHED_VERSIONS="29.1.20 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28"
INSTALL_STAMPS="29.1.20:100 29.1.21:101 29.1.22:102 29.1.23:103 29.1.24:104 29.1.25:105 29.1.26:106 29.1.27:107 29.1.28:108"
unset CACHE_MTIME_OVERRIDES READONLY_STAMP_VERSION
run_case target-in-top-eight-exact-count
[[ "$CASE_RC" -eq 0 ]] || fail "target-in-top-eight-exact-count exit $CASE_RC"
[[ "$(count_cached_versions "$CASE_CACHE_ROOT")" -eq 8 ]] || fail "target-in-top-eight-exact-count should retain exactly 8 dirs, not 9"
[[ -d "$CASE_CACHE_ROOT/29.1.28" ]] || fail "target-in-top-eight-exact-count should keep target 29.1.28"
[[ ! -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "target-in-top-eight-exact-count should prune only 29.1.20"
for version in 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27; do
    [[ -d "$CASE_CACHE_ROOT/$version" ]] || fail "target-in-top-eight-exact-count should keep $version"
done

GH_OUTPUT=$'29.1.28\n'
INITIAL_INSTALLED_VERSION="29.1.28"
PLUGIN_ROOT_VERSION="29.1.28"
INSTALL_RESULT_VERSION="29.1.28"
INSTALL_CACHE_VERSION="29.1.28"
CACHED_VERSIONS="29.1.20 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28"
INSTALL_STAMPS="29.1.20:100 29.1.21:101 29.1.22:102 29.1.23:103 29.1.24:104 29.1.25:105 29.1.26:106 29.1.27:107 29.1.28:108"
unset CACHE_MTIME_OVERRIDES READONLY_STAMP_VERSION
run_case already-latest-prunes
[[ "$CASE_RC" -eq 0 ]] || fail "already-latest-prunes exit $CASE_RC"
assert_contains "$CASE_OUTPUT" "Pruning old larch versions" "already-latest-prunes prune banner"
assert_contains "$CASE_OUTPUT" "Already at latest stable larch release (29.1.28)." "already-latest-prunes already-latest message"
assert_not_contains "$CASE_OUTPUT" "Installing larch plugin" "already-latest-prunes skips install"
assert_not_contains "$CASE_OUTPUT" "Uninstalling larch plugin" "already-latest-prunes skips uninstall"
[[ "$(count_cached_versions "$CASE_CACHE_ROOT")" -eq 8 ]] || fail "already-latest-prunes should retain exactly 8 dirs"
[[ ! -d "$CASE_CACHE_ROOT/29.1.20" ]] || fail "already-latest-prunes should prune oldest 29.1.20"
for version in 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28; do
    [[ -d "$CASE_CACHE_ROOT/$version" ]] || fail "already-latest-prunes should keep $version"
done

GH_OUTPUT=$'29.1.28\n'
INITIAL_INSTALLED_VERSION="29.1.28"
PLUGIN_ROOT_VERSION="29.1.28"
INSTALL_RESULT_VERSION="29.1.28"
unset INSTALL_CACHE_VERSION
CACHED_VERSIONS="29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28"
INSTALL_STAMPS="29.1.21:101 29.1.22:102 29.1.23:103 29.1.24:104 29.1.25:105 29.1.26:106 29.1.27:107 29.1.28:108"
unset CACHE_MTIME_OVERRIDES READONLY_STAMP_VERSION
run_case exactly-eight-no-prune
[[ "$CASE_RC" -eq 0 ]] || fail "exactly-eight-no-prune exit $CASE_RC"
[[ "$(count_cached_versions "$CASE_CACHE_ROOT")" -eq 8 ]] || fail "exactly-eight-no-prune should retain all 8 dirs"
assert_contains "$CASE_OUTPUT" "No old versions to prune." "exactly-eight-no-prune no-op prune"
for version in 29.1.21 29.1.22 29.1.23 29.1.24 29.1.25 29.1.26 29.1.27 29.1.28; do
    [[ -d "$CASE_CACHE_ROOT/$version" ]] || fail "exactly-eight-no-prune should keep $version"
done

GH_OUTPUT=$'31.0.0\n30.9.0\n'
INITIAL_INSTALLED_VERSION="30.8.0"
PLUGIN_ROOT_VERSION="30.8.0"
INSTALL_RESULT_VERSION="31.0.0"
INSTALL_CACHE_VERSION="31.0.0"
CACHED_VERSIONS="29.0.0 30.0.0 31.0.0 32.0.0 33.0.0 34.0.0 35.0.0 36.0.0 99.0.0"
INSTALL_STAMPS="29.0.0:100 30.0.0:200 32.0.0:400 33.0.0:500 34.0.0:600 35.0.0:700 36.0.0:800 99.0.0:900"
run_case cap-pressure-newer-than-stable-survives
[[ "$CASE_RC" -eq 0 ]] || fail "cap-pressure-newer-than-stable-survives exit $CASE_RC"
[[ -d "$CASE_CACHE_ROOT/99.0.0" ]] || fail "cap-pressure-newer-than-stable-survives should keep semver-newer-than-stable 99.0.0"
[[ -d "$CASE_CACHE_ROOT/31.0.0" ]] || fail "cap-pressure-newer-than-stable-survives should keep installed 31.0.0"
[[ -d "$CASE_CACHE_ROOT/30.0.0" ]] || fail "cap-pressure-newer-than-stable-survives should keep stamped 30.0.0 in newest eight"
[[ ! -d "$CASE_CACHE_ROOT/29.0.0" ]] || fail "cap-pressure-newer-than-stable-survives should prune 29.0.0"
[[ ! -d "$CASE_CACHE_ROOT/30.8.0" ]] || fail "cap-pressure-newer-than-stable-survives should prune unstamped plugin root outside cap"
[[ "$(count_cached_versions "$CASE_CACHE_ROOT")" -eq 8 ]] || fail "cap-pressure-newer-than-stable-survives should retain exactly 8 dirs"
unset INSTALL_STAMPS

GH_OUTPUT=$'31.0.0\n30.9.0\n'
INITIAL_INSTALLED_VERSION="31.0.0"
INSTALLED_PLUGINS_VERSION="31.0.0"
PLUGIN_ROOT_VERSION="30.9.0"
unset INSTALL_RESULT_VERSION INSTALL_CACHE_VERSION
CACHED_VERSIONS="29.0.0 30.0.0 30.8.0 30.9.0 31.0.0 32.0.0 33.0.0 34.0.0 35.0.0"
INSTALL_STAMPS="29.0.0:100 30.0.0:200 30.8.0:300 32.0.0:500 33.0.0:600 34.0.0:700 35.0.0:800"
export CACHE_MTIME_OVERRIDES="30.9.0:209901010001"
run_case already-latest-prunes-unstamped-plugin-root
[[ "$CASE_RC" -eq 0 ]] || fail "already-latest-prunes-unstamped-plugin-root exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/30.9.0" ]] || fail "already-latest-prunes-unstamped-plugin-root should prune unstamped plugin root outside newest eight"
assert_contains "$CASE_OUTPUT" "Already at latest stable larch release (31.0.0)." "already-latest-prunes-unstamped-plugin-root message"
unset CACHE_MTIME_OVERRIDES INSTALL_STAMPS INSTALLED_PLUGINS_VERSION

GH_OUTPUT=$'42.0.10\n'
INITIAL_INSTALLED_VERSION="42.0.5"
PLUGIN_ROOT_VERSION="42.0.5"
INSTALL_RESULT_VERSION="42.0.10"
INSTALL_CACHE_VERSION="42.0.10"
CACHED_VERSIONS="42.0.1 42.0.2 42.0.3 42.0.4 42.0.5 42.0.6 42.0.7 42.0.8 42.0.9"
unset INSTALL_STAMPS
export CACHE_MTIME_OVERRIDES="42.0.9:200001010001 42.0.1:209901010001 42.0.5:209901010002"
STAT_FAIL_VERSION="42.0.5"
run_case stat-failure-falls-back-to-zero
[[ "$CASE_RC" -eq 0 ]] || fail "stat-failure-falls-back-to-zero exit $CASE_RC"
[[ ! -d "$CASE_CACHE_ROOT/42.0.5" ]] || fail "stat-failure-falls-back-to-zero should prune unstamped dir when stat mtime falls back to 0"
[[ -d "$CASE_CACHE_ROOT/42.0.10" ]] || fail "stat-failure-falls-back-to-zero should keep install target"
[[ "$(count_cached_versions "$CASE_CACHE_ROOT")" -eq 8 ]] || fail "stat-failure-falls-back-to-zero should retain exactly 8 dirs"
unset CACHE_MTIME_OVERRIDES STAT_FAIL_VERSION

printf 'PASS: test-upgrade-larch-prune.sh\n'
