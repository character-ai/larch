#!/usr/bin/env bash
# Hermetic harness for upgrade-larch.sh cache retention + sparse-cone reconciliation.
# Cases that touch the marketplace clone or source upgrade-larch.sh isolate HOME
# before sourcing. Re-sourcing reruns PLUGIN_ROOT/LARCH_CACHE_DIR assignment, so
# each case resets LARCH_CACHE_DIR after source.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
UPGRADE_SCRIPT="$SCRIPT_DIR/upgrade-larch.sh"
EXPECTED_SPARSE_DIRS=".claude .claude-plugin .gemini .github agents docs hooks python scripts skills tests"

PASS=0
FAIL=0

fail() {
    FAIL=$((FAIL + 1))
    echo "  FAIL: $*" >&2
}

pass() {
    PASS=$((PASS + 1))
    echo "  PASS: $*"
}

assert_success() {
    local label="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        pass "$label"
    else
        fail "$label"
    fi
}

assert_failure() {
    local label="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        fail "$label"
    else
        pass "$label"
    fi
}

assert_eq() {
    local got="$1" expected="$2" label="$3"
    if [[ "$got" == "$expected" ]]; then
        pass "$label"
    else
        fail "$label (got '$got', expected '$expected')"
    fi
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$label"
    else
        fail "$label (missing '$needle')"
    fi
}

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-upgrade-larch-retention.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

source_upgrade_for_case() {
    local case_name="$1" plugin_root="${2:-}"

    export HOME="$TMP/home-$case_name"
    mkdir -p "$HOME"
    if [[ -n "$plugin_root" ]]; then
        export CLAUDE_PLUGIN_ROOT="$plugin_root"
    else
        unset CLAUDE_PLUGIN_ROOT || true
    fi
    # shellcheck source=skills/upgrade-larch/scripts/upgrade-larch.sh
    source "$UPGRADE_SCRIPT"
    LARCH_CACHE_DIR="$TMP/cache-$case_name"
    mkdir -p "$LARCH_CACHE_DIR"
}

make_sparse_marketplace() {
    local case_name="$1"
    shift
    local clone="$TMP/home-$case_name/.claude/plugins/marketplaces/larch-local"

    mkdir -p "$clone"
    git init "$clone" >/dev/null 2>&1
    git -C "$clone" sparse-checkout init --cone >/dev/null 2>&1
    git -C "$clone" sparse-checkout set "$@" >/dev/null 2>&1
    printf '%s\n' "$clone"
}

write_stamp() {
    local ver="$1" ts="$2"
    mkdir -p "$LARCH_CACHE_DIR/$ver"
    printf '%s\n' "$ts" >"$LARCH_CACHE_DIR/$ver/.larch-installed-at"
}

count_version_dirs() {
    find "$LARCH_CACHE_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' '
}

is_cache_shaped_root_for_test() {
    local root="$1" version
    case "$root" in
        "$HOME/.claude/plugins/cache/larch-local/larch/"*) ;;
        *) return 1 ;;
    esac
    [ -d "$root" ] || return 1
    version=$(basename "$root")
    is_safe_version "$version"
}

single_cache_version_dir_for_test() {
    local cache_parent="$HOME/.claude/plugins/cache/larch-local/larch" dir found="" count=0 version
    shopt -s nullglob
    for dir in "$cache_parent"/*; do
        [ -d "$dir" ] || continue
        version=$(basename "$dir")
        is_safe_version "$version" || continue
        found="$dir"
        count=$((count + 1))
    done
    shopt -u nullglob
    [ "$count" -eq 1 ] || return 1
    printf '%s\n' "$found"
}

resolve_release_step7_root_for_test() {
    local current_version="$1" installed_version="$2"
    local bin_dir="$TMP/bin-root-resolve"
    local old_path="$PATH"

    mkdir -p "$bin_dir"
    cat > "$bin_dir/claude" <<CLAUDE
#!/usr/bin/env bash
case "\$*" in
    "plugin list")
        if [ -n "$installed_version" ]; then
            printf 'larch@larch-local\n'
            printf '  Version: %s\n' "$installed_version"
        fi
        ;;
    *)
        exit 1
        ;;
esac
CLAUDE
    chmod +x "$bin_dir/claude"
    PATH="$bin_dir:$PATH" resolve_release_step7_root "$current_version"
    PATH="$old_path"
}

invoke_release_step7_upgrade_for_test() {
    local resolved_root="$1" script_path="$2"
    local upgrade_rc=0 upgrade_out

    upgrade_out=$(CLAUDE_PLUGIN_ROOT="$resolved_root" bash "$script_path" 2>&1) || upgrade_rc=$?
    printf 'RC=%s\n%s\n' "$upgrade_rc" "$upgrade_out"
}

detect_cone_reconcile_for_test() {
    local upgrade_out="$1"
    if [[ "$upgrade_out" == *"LARCH_CONE_RECONCILED=true"* ]]; then
        return 0
    fi
    return 1
}

detect_new_version_installed_for_test() {
    local upgrade_out="$1"
    [[ "$upgrade_out" == *"LARCH_NEW_VERSION_INSTALLED=true"* ]]
}

parse_release_step7_flags_for_test() {
    local upgrade_rc="$1" upgrade_out="$2"
    local cone_reconciled=false new_version_installed=false restart_required=false

    if [ "$upgrade_rc" -eq 0 ]; then
        if [[ "$upgrade_out" == *"LARCH_CONE_RECONCILED=true"* ]]; then
            cone_reconciled=true
        fi
        if [[ "$upgrade_out" == *"LARCH_NEW_VERSION_INSTALLED=true"* ]]; then
            new_version_installed=true
        fi
        if [[ "$upgrade_out" == *"LARCH_RESTART_REQUIRED=true"* ]]; then
            restart_required=true
        fi
    fi
    printf 'CONE_RECONCILED=%s\nNEW_VERSION_INSTALLED=%s\nRESTART_REQUIRED=%s\n' "$cone_reconciled" "$new_version_installed" "$restart_required"
}

# --- sourced allowlist dual-update regression ---
source_upgrade_for_case literal
assert_eq "$LARCH_SPARSE_DIRS" "$EXPECTED_SPARSE_DIRS" "sparse dir literal matches intentional duplicate guard"
if trap -p ERR | grep -q 'recover'; then
    fail "sourcing upgrade-larch.sh must not leave production ERR trap installed"
else
    pass "sourcing upgrade-larch.sh leaves ERR trap unchanged"
fi

# --- marketplace_sparse_cone_matches cases ---
source_upgrade_for_case cone-match
# shellcheck disable=SC2086 # intentional fixture splitting
make_sparse_marketplace cone-match $EXPECTED_SPARSE_DIRS >/dev/null
assert_success "marketplace_sparse_cone_matches accepts matching sparse cone" marketplace_sparse_cone_matches

source_upgrade_for_case cone-missing
assert_failure "marketplace_sparse_cone_matches rejects missing marketplace clone" marketplace_sparse_cone_matches

source_upgrade_for_case cone-logs
# shellcheck disable=SC2086 # intentional fixture splitting
clone=$(make_sparse_marketplace cone-logs $EXPECTED_SPARSE_DIRS)
mkdir -p "$clone/larch-logs"
assert_failure "marketplace_sparse_cone_matches rejects legacy full clone with larch-logs" marketplace_sparse_cone_matches

source_upgrade_for_case cone-not-git
mkdir -p "$HOME/.claude/plugins/marketplaces/larch-local"
assert_failure "marketplace_sparse_cone_matches rejects non-git marketplace dir" marketplace_sparse_cone_matches

source_upgrade_for_case cone-empty
clone=$(make_sparse_marketplace cone-empty .claude)
git -C "$clone" sparse-checkout set --no-cone >/dev/null 2>&1
printf '\n' > "$clone/.git/info/sparse-checkout"
assert_failure "marketplace_sparse_cone_matches rejects empty configured sparse list" marketplace_sparse_cone_matches

# --- already_latest_and_cone_ok cases ---
source_upgrade_for_case latest-match
# shellcheck disable=SC2086 # intentional fixture splitting
make_sparse_marketplace latest-match $EXPECTED_SPARSE_DIRS >/dev/null
LATEST_STABLE="9.0.0"
CURRENT_INSTALLED_VERSION="9.0.0"
assert_success "already_latest_and_cone_ok accepts same version plus matching cone" already_latest_and_cone_ok

source_upgrade_for_case latest-drift
make_sparse_marketplace latest-drift .claude scripts skills >/dev/null
LATEST_STABLE="9.0.0"
CURRENT_INSTALLED_VERSION="9.0.0"
assert_failure "already_latest_and_cone_ok rejects same version plus drifted cone" already_latest_and_cone_ok

source_upgrade_for_case latest-different-version
# shellcheck disable=SC2086 # intentional fixture splitting
make_sparse_marketplace latest-different-version $EXPECTED_SPARSE_DIRS >/dev/null
LATEST_STABLE="9.0.0"
CURRENT_INSTALLED_VERSION="8.0.0"
assert_failure "already_latest_and_cone_ok rejects version mismatch" already_latest_and_cone_ok

# --- RC1 guard: allowlist comes from SCRIPT_ROOT, not stale CLAUDE_PLUGIN_ROOT ---
fake_old_root="$TMP/old-cache/larch-local/larch/8.0.0"
mkdir -p "$fake_old_root/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$fake_old_root/scripts/lib-quiet.sh"
source_upgrade_for_case script-root-split "$fake_old_root"
assert_eq "$LARCH_SPARSE_DIRS" "$EXPECTED_SPARSE_DIRS" "working-tree script sources sparse dirs from SCRIPT_ROOT despite older plugin root"
if [[ ! -e "$fake_old_root/scripts/lib-sparse-dirs.sh" ]]; then
    pass "older fake plugin root lacks lib-sparse-dirs fixture"
else
    fail "older fake plugin root should not contain lib-sparse-dirs fixture"
fi

# --- root-resolution acceptance for release Step 7 prompt contract ---
source_upgrade_for_case root-active
active_root="$HOME/.claude/plugins/cache/larch-local/larch/1.0.0"
metadata_root="$HOME/.claude/plugins/cache/larch-local/larch/2.0.0"
mkdir -p "$active_root" "$metadata_root"
export CLAUDE_PLUGIN_ROOT="$active_root"
resolved=$(resolve_release_step7_root_for_test 1.0.0 2.0.0 || true)
assert_eq "$resolved" "$active_root" "active cache-shaped CLAUDE_PLUGIN_ROOT wins over newer metadata root"

source_upgrade_for_case root-metadata
unset CLAUDE_PLUGIN_ROOT || true
metadata_root="$HOME/.claude/plugins/cache/larch-local/larch/2.0.0"
mkdir -p "$metadata_root"
resolved=$(resolve_release_step7_root_for_test 1.0.0 2.0.0 || true)
assert_eq "$resolved" "$metadata_root" "parsed installed metadata maps to existing cache dir"

source_upgrade_for_case root-current-matches-metadata
unset CLAUDE_PLUGIN_ROOT || true
current_root="$HOME/.claude/plugins/cache/larch-local/larch/3.0.0"
mkdir -p "$current_root"
resolved=$(resolve_release_step7_root_for_test 3.0.0 3.0.0 || true)
assert_eq "$resolved" "$current_root" "CURRENT_VERSION accepted when it matches installed metadata"

source_upgrade_for_case root-current-sole
unset CLAUDE_PLUGIN_ROOT || true
current_root="$HOME/.claude/plugins/cache/larch-local/larch/4.0.0"
mkdir -p "$current_root"
resolved=$(resolve_release_step7_root_for_test 4.0.0 "" || true)
assert_eq "$resolved" "$current_root" "CURRENT_VERSION accepted as sole defensible fallback when metadata unavailable"

source_upgrade_for_case root-zero
unset CLAUDE_PLUGIN_ROOT || true
resolved=$(resolve_release_step7_root_for_test 5.0.0 "" || true)
assert_eq "$resolved" "" "zero cache dirs yields no arbitrary resolved root"

source_upgrade_for_case root-ambiguous
unset CLAUDE_PLUGIN_ROOT || true
mkdir -p "$HOME/.claude/plugins/cache/larch-local/larch/6.0.0" "$HOME/.claude/plugins/cache/larch-local/larch/6.0.1"
resolved=$(resolve_release_step7_root_for_test 6.0.2 "" || true)
assert_eq "$resolved" "" "two cache dirs yields no arbitrary resolved root"

# --- captured working-tree invocation + reconcile detection ---
source_upgrade_for_case invoke-capture
resolved_root="$HOME/.claude/plugins/cache/larch-local/larch/7.0.0"
mkdir -p "$resolved_root"
stub="$TMP/upgrade-stub.sh"
cat > "$stub" <<'STUB'
#!/usr/bin/env bash
printf 'root=%s\n' "$CLAUDE_PLUGIN_ROOT"
printf 'LARCH_CONE_RECONCILED=true\n' >&2
exit 0
STUB
chmod +x "$stub"
out=$(invoke_release_step7_upgrade_for_test "$resolved_root" "$stub")
assert_contains "$out" "root=$resolved_root" "release Step 7 invocation passes explicit CLAUDE_PLUGIN_ROOT"
assert_contains "$out" "LARCH_CONE_RECONCILED=true" "release Step 7 invocation captures stderr with stdout"
assert_success "reconcile detector accepts machine-readable line" detect_cone_reconcile_for_test "$out"
fragment="Already at latest stable larch release (9.0.0), but the sparse checkout is out of date (allowlist changed). Reconciling the marketplace cone and reinstalling..."
assert_failure "reconcile detector rejects pre-install prose fragment" detect_cone_reconcile_for_test "$fragment"
new_version_line="LARCH_NEW_VERSION_INSTALLED=true"
assert_success "new-version detector accepts machine-readable line" detect_new_version_installed_for_test "$new_version_line"
banner="Upgrading larch from 8.0.0 to 9.0.0..."
assert_failure "new-version detector rejects pre-success upgrade banner" detect_new_version_installed_for_test "$banner"
failed_flags=$(parse_release_step7_flags_for_test 1 $'LARCH_CONE_RECONCILED=true\nLARCH_NEW_VERSION_INSTALLED=true')
assert_contains "$failed_flags" "CONE_RECONCILED=false" "release Step 7 ignores reconcile flag from failed upgrade"
assert_contains "$failed_flags" "NEW_VERSION_INSTALLED=false" "release Step 7 ignores new-version flag from failed upgrade"
restart_flags=$(parse_release_step7_flags_for_test 0 "LARCH_RESTART_REQUIRED=true")
assert_contains "$restart_flags" "RESTART_REQUIRED=true" "release Step 7 records restart-required flag from successful upgrade"

# --- production upgrade-larch.sh reconciles a real drifted marketplace clone ---
source_upgrade_for_case production-drift
bin_dir="$TMP/bin-production-drift"
mkdir -p "$bin_dir"
old_path="$PATH"
export PATH="$bin_dir:$PATH"
export CLAUDE_PLUGIN_ROOT="$HOME/.claude/plugins/cache/larch-local/larch/9.0.0"
mkdir -p "$CLAUDE_PLUGIN_ROOT/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$CLAUDE_PLUGIN_ROOT/scripts/lib-quiet.sh"
export LARCH_TEST_VERSION_FILE="$TMP/production-drift-installed-version"
printf '9.0.0\n' > "$LARCH_TEST_VERSION_FILE"
make_sparse_marketplace production-drift .claude scripts skills >/dev/null
cat > "$bin_dir/gh" <<'GH'
#!/usr/bin/env bash
printf 'v9.0.0\n'
GH
chmod +x "$bin_dir/gh"
cat > "$bin_dir/claude" <<'CLAUDE'
#!/usr/bin/env bash
set -euo pipefail
clone="$HOME/.claude/plugins/marketplaces/larch-local"
case "$*" in
    "plugin list")
        printf 'larch@larch-local\n'
        printf '  Version: %s\n' "$(cat "$LARCH_TEST_VERSION_FILE")"
        ;;
    "plugin uninstall larch@larch-local")
        ;;
    "plugin install larch@larch-local")
        printf '9.0.0\n' > "$LARCH_TEST_VERSION_FILE"
        ;;
    "plugin marketplace remove larch-local")
        rm -rf -- "$clone"
        ;;
    plugin\ marketplace\ add\ character-ai/larch\ --sparse*)
        mkdir -p "$clone"
        git init "$clone" >/dev/null 2>&1
        git -C "$clone" sparse-checkout init --cone >/dev/null 2>&1
        shift 5
        git -C "$clone" sparse-checkout set "$@" >/dev/null 2>&1
        ;;
    *)
        printf 'unexpected claude args: %s\n' "$*" >&2
        exit 1
        ;;
esac
CLAUDE
chmod +x "$bin_dir/claude"
prod_out=$(bash "$UPGRADE_SCRIPT" 2>&1)
assert_contains "$prod_out" "LARCH_CONE_RECONCILED=true" "production upgrade emits reconcile signal after drifted marketplace repair"
assert_success "production upgrade leaves marketplace cone matching allowlist" marketplace_sparse_cone_matches
PATH="$old_path"
unset LARCH_TEST_VERSION_FILE

# --- production upgrade-larch.sh signals restart when stable resolution is unavailable ---
source_upgrade_for_case production-unverified-reinstall
bin_dir="$TMP/bin-production-unverified-reinstall"
mkdir -p "$bin_dir"
old_path="$PATH"
export PATH="$bin_dir:$PATH"
export CLAUDE_PLUGIN_ROOT="$HOME/.claude/plugins/cache/larch-local/larch/8.0.0"
mkdir -p "$CLAUDE_PLUGIN_ROOT/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$CLAUDE_PLUGIN_ROOT/scripts/lib-quiet.sh"
export LARCH_TEST_VERSION_FILE="$TMP/production-unverified-installed-version"
printf '8.0.0\n' > "$LARCH_TEST_VERSION_FILE"
# shellcheck disable=SC2086 # intentional fixture splitting
make_sparse_marketplace production-unverified-reinstall $EXPECTED_SPARSE_DIRS >/dev/null
cat > "$bin_dir/gh" <<'GH'
#!/usr/bin/env bash
exit 1
GH
chmod +x "$bin_dir/gh"
cat > "$bin_dir/claude" <<'CLAUDE'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
    "plugin list")
        if [ "${LARCH_TEST_LIST_FAIL:-}" != true ]; then
            printf 'larch@larch-local\n'
            printf '  Version: %s\n' "$(cat "$LARCH_TEST_VERSION_FILE")"
        fi
        ;;
    "plugin uninstall larch@larch-local")
        ;;
    "plugin install larch@larch-local")
        printf '8.0.0\n' > "$LARCH_TEST_VERSION_FILE"
        export LARCH_TEST_LIST_FAIL=true
        ;;
    "plugin marketplace update larch-local")
        ;;
    *)
        printf 'unexpected claude args: %s\n' "$*" >&2
        exit 1
        ;;
esac
CLAUDE
chmod +x "$bin_dir/claude"
unverified_out=$(LARCH_TEST_LIST_FAIL=true bash "$UPGRADE_SCRIPT" 2>&1)
assert_failure "production unverified reinstall emits no verified-new-version signal" detect_new_version_installed_for_test "$unverified_out"
assert_contains "$unverified_out" "LARCH_RESTART_REQUIRED=true" "production upgrade emits restart signal after unverified reinstall"
PATH="$old_path"
unset LARCH_TEST_VERSION_FILE LARCH_TEST_LIST_FAIL

# --- production upgrade-larch.sh early-exits when already latest and cone matches ---
source_upgrade_for_case production-already-latest
bin_dir="$TMP/bin-production-already-latest"
mkdir -p "$bin_dir"
old_path="$PATH"
export PATH="$bin_dir:$PATH"
export CLAUDE_PLUGIN_ROOT="$HOME/.claude/plugins/cache/larch-local/larch/9.0.0"
mkdir -p "$CLAUDE_PLUGIN_ROOT/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$CLAUDE_PLUGIN_ROOT/scripts/lib-quiet.sh"
# shellcheck disable=SC2086 # intentional fixture splitting
make_sparse_marketplace production-already-latest $EXPECTED_SPARSE_DIRS >/dev/null
cat > "$bin_dir/gh" <<'GH'
#!/usr/bin/env bash
printf 'v9.0.0\n'
GH
chmod +x "$bin_dir/gh"
cat > "$bin_dir/claude" <<'CLAUDE'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
    "plugin list")
        printf 'larch@larch-local\n'
        printf '  Version: 9.0.0\n'
        ;;
    "plugin uninstall larch@larch-local"|"plugin install larch@larch-local")
        printf 'unexpected reinstall on already-latest path: %s\n' "$*" >&2
        exit 1
        ;;
    *)
        printf 'unexpected claude args: %s\n' "$*" >&2
        exit 1
        ;;
esac
CLAUDE
chmod +x "$bin_dir/claude"
already_latest_out=$(bash "$UPGRADE_SCRIPT" 2>&1)
assert_contains "$already_latest_out" "No upgrade needed." "production already-latest matching-cone path exits without reinstall"
assert_failure "production already-latest path emits no new-version signal" detect_new_version_installed_for_test "$already_latest_out"
if [[ -f "$CLAUDE_PLUGIN_ROOT/.larch-installed-at" ]]; then
    pass "production already-latest path refreshes install stamp"
else
    fail "production already-latest path should refresh install stamp"
fi
PATH="$old_path"

# --- running dir protected; oldest stamped evicted; eight retained ---
source_upgrade_for_case prune-protected
INSTALLED_VERSION="1.0.0"
mkdir -p "$LARCH_CACHE_DIR/$INSTALLED_VERSION"
for i in $(seq 1 9); do
    write_stamp "1.0.$i" $((1000 + i))
done
prune_cached_versions "2.0.0"
[[ -d "$LARCH_CACHE_DIR/$INSTALLED_VERSION" ]] \
    || fail "running version dir must survive prune"
[[ ! -d "$LARCH_CACHE_DIR/1.0.1" ]] \
    || fail "oldest stamped version should be pruned"
retained=$(count_version_dirs)
if [[ "$retained" -eq 8 ]]; then
    pass "prune retains eight version dirs including protected running tree"
else
    fail "expected 8 retained dirs, got $retained"
fi

# --- backfill stamps previously unstamped survivors ---
source_upgrade_for_case backfill
INSTALLED_VERSION="3.0.0"
mkdir -p "$LARCH_CACHE_DIR/$INSTALLED_VERSION"
for i in $(seq 1 9); do
    mkdir -p "$LARCH_CACHE_DIR/3.0.$i"
    sleep 0.01
done
prune_cached_versions "4.0.0"
if [[ -f "$LARCH_CACHE_DIR/3.0.1/.larch-installed-at" ]]; then
    pass "backfill wrote stamp to previously unstamped dir"
else
    fail "backfill must stamp unstamped survivors"
fi

# --- unverified install must not receive post-install stamp ---
source_upgrade_for_case unverified
ACTUAL_VERSION="9.9.9"
INSTALLED_VERSION="1.0.0"
VERIFIED_TARGET=false
mkdir -p "$LARCH_CACHE_DIR/$ACTUAL_VERSION"
if [[ "$VERIFIED_TARGET" == true ]] && is_safe_version "$ACTUAL_VERSION"; then
    write_install_stamp "$ACTUAL_VERSION"
fi
if [[ ! -f "$LARCH_CACHE_DIR/$ACTUAL_VERSION/.larch-installed-at" ]]; then
    pass "unverified install does not receive post-install stamp"
else
    fail "unverified install must not receive fresh date stamp"
fi

if [[ "$FAIL" -gt 0 ]]; then
    echo "FAIL: $FAIL test(s) failed ($PASS passed)" >&2
    exit 1
fi
echo "PASS: test-upgrade-larch-retention.sh ($PASS cases)"
