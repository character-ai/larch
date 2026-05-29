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

write_stub_date_failure() {
    local path="$1"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "+%s" ]]; then
    exit 1
fi
exec /bin/date "$@"
EOF
    chmod +x "$path"
}

write_stub_find_failure() {
    local path="$1"
    local fail_target="$2"
    cat > "$path" <<EOF
#!/usr/bin/env bash
set -euo pipefail

fail_target="${fail_target}"
target=""
for arg in "\$@"; do
    if [[ "\$arg" != -* ]]; then
        target="\$arg"
        break
    fi
done

if [[ "\$target" == "\$fail_target" ]]; then
    exit 1
fi

exec /usr/bin/find "\$@"
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
[[ ! -d "$CASE_SESSIONS/stale-session" ]] || fail "stale-dir-with-keepalive-removed should delete stale keepalive dir"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "1" "stale-dir-with-keepalive-removed CACHE_REMOVED"

# --- stale-with-fresh-depth1-child --------------------------------------------
work="$TMP/stale-with-fresh-depth1-child"
mkdir -p "$work/xdg-cache/larch/sessions/stale-parent"
touch -t "$STALE_TS" -- "$work/xdg-cache/larch/sessions/stale-parent"
printf 'fresh\n' > "$work/xdg-cache/larch/sessions/stale-parent/recent.txt"
touch -t "$FRESH_TS" -- "$work/xdg-cache/larch/sessions/stale-parent/recent.txt"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "stale-with-fresh-depth1-child exit $CASE_RC"
[[ -d "$CASE_SESSIONS/stale-parent" ]] || fail "stale-with-fresh-depth1-child should keep dir with fresh depth-1 child"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "0" "stale-with-fresh-depth1-child CACHE_REMOVED"

# --- stale-with-fresh-depth2-grandchild ---------------------------------------
work="$TMP/stale-with-fresh-depth2-grandchild"
mkdir -p "$work/xdg-cache/larch/sessions/stale-root/sub"
touch -t "$STALE_TS" -- "$work/xdg-cache/larch/sessions/stale-root" \
    "$work/xdg-cache/larch/sessions/stale-root/sub"
printf 'fresh\n' > "$work/xdg-cache/larch/sessions/stale-root/sub/grandchild.txt"
touch -t "$FRESH_TS" -- "$work/xdg-cache/larch/sessions/stale-root/sub/grandchild.txt"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "stale-with-fresh-depth2-grandchild exit $CASE_RC"
[[ -d "$CASE_SESSIONS/stale-root" ]] || fail "stale-with-fresh-depth2-grandchild should keep dir with fresh depth-2 grandchild"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "0" "stale-with-fresh-depth2-grandchild CACHE_REMOVED"

# --- stale-with-fresh-depth4-manifest -----------------------------------------
work="$TMP/stale-with-fresh-depth4-manifest"
run_id='RUN-DEPTH4'
mkdir -p "$work/xdg-cache/larch/sessions/implement-run/larch-logs/implement/$run_id"
touch -t "$STALE_TS" -- "$work/xdg-cache/larch/sessions/implement-run" \
    "$work/xdg-cache/larch/sessions/implement-run/larch-logs" \
    "$work/xdg-cache/larch/sessions/implement-run/larch-logs/implement" \
    "$work/xdg-cache/larch/sessions/implement-run/larch-logs/implement/$run_id"
printf '{}\n' > "$work/xdg-cache/larch/sessions/implement-run/larch-logs/implement/$run_id/manifest.json"
touch -t "$FRESH_TS" -- "$work/xdg-cache/larch/sessions/implement-run/larch-logs/implement/$run_id/manifest.json"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "stale-with-fresh-depth4-manifest exit $CASE_RC"
[[ -d "$CASE_SESSIONS/implement-run" ]] || fail "stale-with-fresh-depth4-manifest should keep dir with fresh depth-4 manifest"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "0" "stale-with-fresh-depth4-manifest CACHE_REMOVED"

# --- stale-with-fresh-depth5-round --------------------------------------------
work="$TMP/stale-with-fresh-depth5-round"
run_id='RUN-DEPTH5'
mkdir -p "$work/xdg-cache/larch/sessions/implement-round/larch-logs/implement/$run_id/round-1"
touch -t "$STALE_TS" -- "$work/xdg-cache/larch/sessions/implement-round" \
    "$work/xdg-cache/larch/sessions/implement-round/larch-logs" \
    "$work/xdg-cache/larch/sessions/implement-round/larch-logs/implement" \
    "$work/xdg-cache/larch/sessions/implement-round/larch-logs/implement/$run_id" \
    "$work/xdg-cache/larch/sessions/implement-round/larch-logs/implement/$run_id/round-1"
printf '# findings\n' > "$work/xdg-cache/larch/sessions/implement-round/larch-logs/implement/$run_id/round-1/findings.md"
touch -t "$FRESH_TS" -- "$work/xdg-cache/larch/sessions/implement-round/larch-logs/implement/$run_id/round-1/findings.md"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "stale-with-fresh-depth5-round exit $CASE_RC"
[[ -d "$CASE_SESSIONS/implement-round" ]] || fail "stale-with-fresh-depth5-round should keep dir with fresh depth-5 round artifact"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "0" "stale-with-fresh-depth5-round CACHE_REMOVED"

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

# --- date-failure-errors ------------------------------------------------------
work="$TMP/date-failure-errors"
mkdir -p "$work/bin"
write_stub_date_failure "$work/bin/date"
PATH_PREFIX="$work/bin:"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -ne 0 ]] || fail "date-failure-errors should exit non-zero"
assert_contains "$CASE_OUTPUT" "Error: failed to determine the current epoch time; refusing cleanup." "date-failure-errors stderr"
unset PATH_PREFIX

# --- find-failure-skips-deletion ----------------------------------------------
work="$TMP/find-failure-skips-deletion"
mkdir -p "$work/xdg-cache/larch/sessions/fail-find"
touch -t "$STALE_TS" -- "$work/xdg-cache/larch/sessions/fail-find"
mkdir -p "$work/bin"
write_stub_find_failure "$work/bin/find" "$work/xdg-cache/larch/sessions/fail-find"
PATH_PREFIX="$work/bin:"
unset LARCH_CLEANUP_RETENTION_DAYS
run_cleanup "$work"
[[ "$CASE_RC" -eq 0 ]] || fail "find-failure-skips-deletion exit $CASE_RC"
[[ -d "$CASE_SESSIONS/fail-find" ]] || fail "find-failure-skips-deletion should keep dir when find fails"
assert_eq "$(kv_get CACHE_REMOVED "$CASE_OUTPUT")" "0" "find-failure-skips-deletion CACHE_REMOVED"
assert_contains "$CASE_OUTPUT" "Warning: failed to scan session activity for '$work/xdg-cache/larch/sessions/fail-find'; skipping deletion." "find-failure-skips-deletion warning"
unset PATH_PREFIX

printf 'PASS: test-cleanup.sh\n'
