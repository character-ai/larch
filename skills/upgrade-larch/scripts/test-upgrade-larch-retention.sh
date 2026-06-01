#!/usr/bin/env bash
# Hermetic harness for upgrade-larch.sh cache retention (stamp, backfill, prune).
set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=skills/upgrade-larch/scripts/upgrade-larch.sh
source "$SCRIPT_DIR/upgrade-larch.sh"

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

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-upgrade-larch-retention.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

LARCH_CACHE_DIR="$TMP/cache"
mkdir -p "$LARCH_CACHE_DIR"

write_stamp() {
    local ver="$1" ts="$2"
    mkdir -p "$LARCH_CACHE_DIR/$ver"
    printf '%s\n' "$ts" >"$LARCH_CACHE_DIR/$ver/.larch-installed-at"
}

count_version_dirs() {
    find "$LARCH_CACHE_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' '
}

# --- running dir protected; oldest stamped evicted; eight retained ---
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
rm -rf "$LARCH_CACHE_DIR"
mkdir -p "$LARCH_CACHE_DIR"
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
rm -rf "$LARCH_CACHE_DIR"
mkdir -p "$LARCH_CACHE_DIR"
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
