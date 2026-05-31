#!/usr/bin/env bash

set -euo pipefail

# Offline regression harness for skills/cleanup/scripts/cleanup.sh age-based
# session pruning, retention parsing, and dangling design-env symlink reaping.

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/cleanup/scripts/cleanup.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-cleanup.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

STALE_TS='200001010000'
FRESH_TS='209901010000'

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

assert_eq() {
    local actual="$1" expected="$2" label="$3"
    [[ "$actual" == "$expected" ]] || fail "$label: expected [$expected], got [$actual]"
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    grep -Fq "$needle" <<< "$haystack" || fail "$label: missing [$needle]"
}

kv_get() {
    local key="$1" haystack="$2"
    local line
    line=$(grep "^${key}=" <<< "$haystack" | tail -1 || true)
    [[ -n "$line" ]] || fail "kv_get: missing key [$key]"
    printf '%s\n' "${line#*=}"
}

write_stub_find_failure() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Fail only should_remove_by_age nested scan (-maxdepth 5 adjacent pair).
prev=""
for arg in "$@"; do
    if [[ "$prev" == "-maxdepth" && "$arg" == "5" ]]; then
        exit 2
    fi
    prev="$arg"
done

exec /usr/bin/find "$@"
EOF
    chmod +x "$path"
}

write_stub_pgrep() {
    local path="$1" count="$2"
    cat > "$path" <<EOF
#!/usr/bin/env bash
set -euo pipefail

if [[ "\${1:-}" == "-x" && "\${2:-}" == "claude" ]]; then
    i=0
    while [ "\$i" -lt "$count" ]; do
        printf '%s\n' \$((10000 + i))
        i=\$((i + 1))
    done
    exit 0
fi
exec /usr/bin/pgrep "\$@"
EOF
    chmod +x "$path"
}

run_cleanup() {
    local work="$1"
    local home="$work/home"
    local bin="$work/bin"
    local xdg="$work/xdg-cache"
    local tmp_root="$work/tmp-root"
    local path_prefix="${PATH_PREFIX:-$bin:}"
    local retention="${LARCH_CLEANUP_RETENTION_DAYS:-}"

    mkdir -p "$home" "$bin" "$xdg/larch/sessions" "$tmp_root"

    set +e
    if [[ -n "$retention" ]]; then
        CASE_OUTPUT=$(
            HOME="$home" \
            PATH="${path_prefix}${PATH}" \
            XDG_CACHE_HOME="$xdg" \
            LARCH_TEST_TMP_ROOT="$tmp_root" \
            CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
            LARCH_QUIET_DISABLE=1 \
            LARCH_CLEANUP_RETENTION_DAYS="$retention" \
            "$SCRIPT" 2>&1
        )
    else
        CASE_OUTPUT=$(
            HOME="$home" \
            PATH="${path_prefix}${PATH}" \
            XDG_CACHE_HOME="$xdg" \
            LARCH_TEST_TMP_ROOT="$tmp_root" \
            CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
            LARCH_QUIET_DISABLE=1 \
            "$SCRIPT" 2>&1
        )
    fi
    CASE_RC=$?
    set -e

    CASE_SESSIONS="$xdg/larch/sessions"
}

# --- multiple-claude-no-abort -------------------------------------------------
work="$TMP/multiple-claude-no-abort"
mkdir -p "$work/bin"
write_stub_pgrep "$work/bin/pgrep" 3
PATH_PREFIX="$work/bin:"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "multiple-claude-no-abort exit $CASE_RC"
assert_eq "$(kv_get SESSION_COUNT "$CASE_OUTPUT")" "3" "multiple-claude-no-abort SESSION_COUNT"
unset PATH_PREFIX

# --- stale-dir-removed --------------------------------------------------------
work="$TMP/stale-dir-removed"
mkdir -p "$work/xdg-cache/larch/sessions/stale-session"
touch -t "$STALE_TS" -- "$work/xdg-cache/larch/sessions/stale-session"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "stale-dir-removed exit $CASE_RC"
[[ ! -d "$CASE_SESSIONS/stale-session" ]] || fail "stale-dir-removed should delete stale session dir"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "1" "stale-dir-removed CACHE_REMOVED"

# --- fresh-dir-kept -----------------------------------------------------------
work="$TMP/fresh-dir-kept"
mkdir -p "$work/xdg-cache/larch/sessions/fresh-session"
touch -t "$FRESH_TS" -- "$work/xdg-cache/larch/sessions/fresh-session"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "fresh-dir-kept exit $CASE_RC"
[[ -d "$CASE_SESSIONS/fresh-session" ]] || fail "fresh-dir-kept should keep recent session dir"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "0" "fresh-dir-kept CACHE_REMOVED"

# --- stale-dir-with-keepalive-removed -----------------------------------------
work="$TMP/stale-dir-with-keepalive-removed"
mkdir -p "$work/xdg-cache/larch/sessions/stale-session"
printf '# larch session identity (hook routing)\nCLONE_PATH=%s\nSESSION_ID=%s\n' \
    "/tmp/repo" "stale-session" > "$work/xdg-cache/larch/sessions/stale-session/.larch-keepalive"
touch -t "$STALE_TS" -- "$work/xdg-cache/larch/sessions/stale-session" \
    "$work/xdg-cache/larch/sessions/stale-session/.larch-keepalive"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "stale-dir-with-keepalive-removed exit $CASE_RC"
[[ ! -d "$CASE_SESSIONS/stale-session" ]] || fail "stale-dir-with-keepalive-removed should delete stale keepalive dir by age"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "1" "stale-dir-with-keepalive-removed CACHE_REMOVED"

# --- symlinked-session-dir-skipped --------------------------------------------
work="$TMP/symlinked-session-dir-skipped"
mkdir -p "$work/xdg-cache/larch/sessions" "$work/victim"
touch -t "$STALE_TS" -- "$work/victim"
ln -s "$work/victim" "$work/xdg-cache/larch/sessions/claude-implement-evil"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "symlinked-session-dir-skipped exit $CASE_RC"
[[ -d "$work/victim" ]] || fail "symlinked-session-dir-skipped must not rm -rf through session symlink"
[[ -L "$CASE_SESSIONS/claude-implement-evil" ]] || fail "symlinked-session-dir-skipped should leave symlink entry"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "0" "symlinked-session-dir-skipped CACHE_REMOVED"

# --- stale-toplevel-with-fresh-deep-child-kept --------------------------------
work="$TMP/stale-toplevel-with-fresh-deep-child-kept"
mkdir -p "$work/xdg-cache/larch/sessions/stale-parent"
printf 'fresh\n' > "$work/xdg-cache/larch/sessions/stale-parent/child.txt"
touch -t "$FRESH_TS" -- "$work/xdg-cache/larch/sessions/stale-parent/child.txt"
touch -t "$STALE_TS" -- "$work/xdg-cache/larch/sessions/stale-parent"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "stale-toplevel-with-fresh-deep-child-kept exit $CASE_RC"
[[ -d "$CASE_SESSIONS/stale-parent" ]] || fail "stale-toplevel-with-fresh-deep-child-kept must retain dir when a descendant is fresh"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "0" "stale-toplevel-with-fresh-deep-child-kept CACHE_REMOVED"

# --- find-failure-skips-deletion ----------------------------------------------
# Tied to should_remove_by_age maxdepth 5 bound (see cleanup.md Edit-in-sync).
work="$TMP/find-failure-skips-deletion"
mkdir -p "$work/xdg-cache/larch/sessions/stale-scan-fail"
touch -t "$STALE_TS" -- "$work/xdg-cache/larch/sessions/stale-scan-fail"
mkdir -p "$work/bin"
write_stub_find_failure "$work/bin/find"
PATH_PREFIX="$work/bin:"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "find-failure-skips-deletion exit $CASE_RC"
assert_contains "$CASE_OUTPUT" "failed to scan session activity" "find-failure-skips-deletion warning"
[[ -d "$CASE_SESSIONS/stale-scan-fail" ]] || fail "find-failure-skips-deletion should keep dir when nested scan find fails"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "0" "find-failure-skips-deletion CACHE_REMOVED"
unset PATH_PREFIX

# --- invalid-retention-fallback -----------------------------------------------
work="$TMP/invalid-retention-fallback"
mkdir -p "$work/xdg-cache/larch/sessions/old-session"
touch -t "$STALE_TS" -- "$work/xdg-cache/larch/sessions/old-session"
LARCH_CLEANUP_RETENTION_DAYS='abc'
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "invalid-retention-fallback exit $CASE_RC"
assert_contains "$CASE_OUTPUT" "Warning: invalid LARCH_CLEANUP_RETENTION_DAYS='abc'; using 7." "invalid-retention-fallback warning"
[[ ! -d "$CASE_SESSIONS/old-session" ]] || fail "invalid-retention-fallback should remove stale dir under 7-day fallback"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "1" "invalid-retention-fallback CACHE_REMOVED"
unset LARCH_CLEANUP_RETENTION_DAYS

# --- custom-retention-one-day -------------------------------------------------
work="$TMP/custom-retention-one-day"
mkdir -p "$work/xdg-cache/larch/sessions/stale-session" "$work/xdg-cache/larch/sessions/fresh-session"
touch -t "$STALE_TS" -- "$work/xdg-cache/larch/sessions/stale-session"
touch -t "$FRESH_TS" -- "$work/xdg-cache/larch/sessions/fresh-session"
LARCH_CLEANUP_RETENTION_DAYS='1'
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "custom-retention-one-day exit $CASE_RC"
[[ ! -d "$CASE_SESSIONS/stale-session" ]] || fail "custom-retention-one-day should remove stale session dir"
[[ -d "$CASE_SESSIONS/fresh-session" ]] || fail "custom-retention-one-day should keep fresh session dir"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "1" "custom-retention-one-day CACHE_REMOVED"
unset LARCH_CLEANUP_RETENTION_DAYS

# --- dangling-symlink-reaped --------------------------------------------------
work="$TMP/dangling-symlink-reaped"
mkdir -p "$work/xdg-cache/larch/sessions"
ln -s "$work/missing-target.sh" "$work/xdg-cache/larch/sessions/current-design-env-test.sh"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "dangling-symlink-reaped exit $CASE_RC"
[[ ! -L "$CASE_SESSIONS/current-design-env-test.sh" ]] || fail "dangling-symlink-reaped should remove dangling symlink"
assert_eq "$(kv_get SYMLINKS_REMOVED "$CASE_OUTPUT")" "1" "dangling-symlink-reaped SYMLINKS_REMOVED"

# --- live-symlink-kept --------------------------------------------------------
work="$TMP/live-symlink-kept"
mkdir -p "$work/xdg-cache/larch/sessions"
printf 'export FOO=1\n' > "$work/live-target.sh"
ln -s "$work/live-target.sh" "$work/xdg-cache/larch/sessions/current-design-env-live.sh"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "live-symlink-kept exit $CASE_RC"
[[ -L "$CASE_SESSIONS/current-design-env-live.sh" ]] || fail "live-symlink-kept should keep live symlink"
assert_eq "$(kv_get SYMLINKS_REMOVED "$CASE_OUTPUT")" "0" "live-symlink-kept SYMLINKS_REMOVED"

# --- stale-tmp-dir-removed ----------------------------------------------------
work="$TMP/stale-tmp-dir-removed"
mkdir -p "$work/tmp-root/claude-implement-fixture"
touch -t "$STALE_TS" -- "$work/tmp-root/claude-implement-fixture"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "stale-tmp-dir-removed exit $CASE_RC"
[[ ! -d "$work/tmp-root/claude-implement-fixture" ]] || fail "stale-tmp-dir-removed should delete stale /tmp fixture"
assert_eq "$(kv_get TMP_REMOVED "$CASE_OUTPUT")" "1" "stale-tmp-dir-removed TMP_REMOVED"

# --- stale-tmp-toplevel-with-fresh-deep-child-kept ----------------------------
work="$TMP/stale-tmp-toplevel-with-fresh-deep-child-kept"
mkdir -p "$work/tmp-root/claude-implement-stale-parent"
printf 'fresh\n' > "$work/tmp-root/claude-implement-stale-parent/child.txt"
touch -t "$FRESH_TS" -- "$work/tmp-root/claude-implement-stale-parent/child.txt"
touch -t "$STALE_TS" -- "$work/tmp-root/claude-implement-stale-parent"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "stale-tmp-toplevel-with-fresh-deep-child-kept exit $CASE_RC"
[[ -d "$work/tmp-root/claude-implement-stale-parent" ]] || fail "stale-tmp-toplevel-with-fresh-deep-child-kept must retain dir when a descendant is fresh"
assert_eq "$(kv_get TMP_REMOVED "$CASE_OUTPUT")" "0" "stale-tmp-toplevel-with-fresh-deep-child-kept TMP_REMOVED"

# --- stale-tmp-file-removed ---------------------------------------------------
work="$TMP/stale-tmp-file-removed"
mkdir -p "$work/tmp-root"
printf 'stale\n' > "$work/tmp-root/larch4-review.diff"
touch -t "$STALE_TS" -- "$work/tmp-root/larch4-review.diff"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "stale-tmp-file-removed exit $CASE_RC"
[[ ! -f "$work/tmp-root/larch4-review.diff" ]] || fail "stale-tmp-file-removed should delete stale /tmp fixture file"
assert_eq "$(kv_get TMP_REMOVED "$CASE_OUTPUT")" "1" "stale-tmp-file-removed TMP_REMOVED"

# --- nonlarch-tmp-untouched ---------------------------------------------------
work="$TMP/nonlarch-tmp-untouched"
mkdir -p "$work/tmp-root/unrelated-junk"
touch -t "$STALE_TS" -- "$work/tmp-root/unrelated-junk"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "nonlarch-tmp-untouched exit $CASE_RC"
[[ -d "$work/tmp-root/unrelated-junk" ]] || fail "nonlarch-tmp-untouched should keep non-larch entry"
assert_eq "$(kv_get TMP_REMOVED "$CASE_OUTPUT")" "0" "nonlarch-tmp-untouched TMP_REMOVED"

# --- deep-session-freshness-probe-bounded -------------------------------------
work="$TMP/deep-session-freshness-probe-bounded"
mkdir -p "$work/xdg-cache/larch/sessions/stale-beyond-probe/a/b/c/d/e/f" \
    "$work/xdg-cache/larch/sessions/stale-within-probe/a/b/c"
printf 'fresh\n' > "$work/xdg-cache/larch/sessions/stale-beyond-probe/a/b/c/d/e/f/deep.txt"
touch -t "$FRESH_TS" -- "$work/xdg-cache/larch/sessions/stale-beyond-probe/a/b/c/d/e/f/deep.txt"
find "$work/xdg-cache/larch/sessions/stale-beyond-probe" -mindepth 0 -maxdepth 5 ! -path "$work/xdg-cache/larch/sessions/stale-beyond-probe/a/b/c/d/e/f/deep.txt" \
    -exec touch -t "$STALE_TS" -- {} +
touch -t "$STALE_TS" -- "$work/xdg-cache/larch/sessions/stale-beyond-probe"
printf 'fresh\n' > "$work/xdg-cache/larch/sessions/stale-within-probe/a/b/c/shallow.txt"
touch -t "$FRESH_TS" -- "$work/xdg-cache/larch/sessions/stale-within-probe/a/b/c/shallow.txt"
touch -t "$STALE_TS" -- "$work/xdg-cache/larch/sessions/stale-within-probe"
SECONDS=0
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
elapsed=$SECONDS
[[ "$CASE_RC" -eq 0 ]] || fail "deep-session-freshness-probe-bounded exit $CASE_RC"
[[ ! -d "$CASE_SESSIONS/stale-beyond-probe" ]] || fail "deep-session-freshness-probe-bounded should remove stale dir when fresh activity is beyond maxdepth"
[[ -d "$CASE_SESSIONS/stale-within-probe" ]] || fail "deep-session-freshness-probe-bounded should retain dir when fresh activity is within maxdepth"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "1" "deep-session-freshness-probe-bounded CACHE_REMOVED"
[ "$elapsed" -lt 10 ] || fail "deep-session-freshness-probe-bounded took ${elapsed}s (expected < 10)"

# --- large-tmp-scales ---------------------------------------------------------
work="$TMP/large-tmp-scales"
mkdir -p "$work/tmp-root"
i=0
while [ "$i" -lt 2000 ]; do
    mkdir -p "$work/tmp-root/noise-$i"
    touch -t "$STALE_TS" -- "$work/tmp-root/noise-$i"
    i=$((i + 1))
done
mkdir -p "$work/tmp-root/claude-implement-scale-target"
touch -t "$STALE_TS" -- "$work/tmp-root/claude-implement-scale-target"
SECONDS=0
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
elapsed=$SECONDS
[[ "$CASE_RC" -eq 0 ]] || fail "large-tmp-scales exit $CASE_RC"
[[ ! -d "$work/tmp-root/claude-implement-scale-target" ]] || fail "large-tmp-scales should delete stale matching dir"
[[ -d "$work/tmp-root/noise-0" ]] || fail "large-tmp-scales should keep non-matching entries"
assert_eq "$(kv_get TMP_REMOVED "$CASE_OUTPUT")" "1" "large-tmp-scales TMP_REMOVED"
[ "$elapsed" -lt 60 ] || fail "large-tmp-scales took ${elapsed}s (expected < 60)"

printf 'PASS: test-cleanup.sh\n'
