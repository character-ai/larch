#!/usr/bin/env bash
# test-capture-session-transcript.sh — regression harness for transcript capture statuses.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CAPTURE="$SCRIPT_DIR/capture-session-transcript.sh"

[ -x "$CAPTURE" ] || { echo "FAIL: $CAPTURE not executable" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-capture-session-transcript.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

pass() {
    echo "  ok: $1"
    PASS=$((PASS + 1))
}

fail() {
    echo "FAIL: $1" >&2
    FAIL=$((FAIL + 1))
}

assert_contains() {
    local label="$1"
    local haystack="$2"
    local needle="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$label"
    else
        fail "$label (missing $needle; got ${haystack:0:400})"
    fi
}

run_capture() {
    local label="$1"
    local expected="$2"
    local source_file="$3"
    local no_logs_commit="$4"
    local repo="$TMP/$label-repo"
    local log_root="$TMP/$label-staging/larch-logs"
    local issues="$TMP/$label-execution-issues.md"

    mkdir -p "$repo"
    git -C "$repo" init >/dev/null 2>&1
    git -C "$repo" config user.email "ci@test"
    git -C "$repo" config user.name "Test CI"
    touch "$repo/.gitkeep"
    git -C "$repo" add .
    git -C "$repo" commit -q -m "init"

    out="$(cd "$repo" && "$CAPTURE" \
        --source-file "$source_file" \
        --log-root "$log_root" \
        --skill implement \
        --run-id "$label" \
        --no-logs-commit "$no_logs_commit" \
        --execution-issues-log "$issues")"

    assert_contains "$label stdout status" "$out" "SESSION_TRANSCRIPT_STATUS=$expected"
    if [ -f "$issues" ]; then
        assert_contains "$label execution issue status" "$(cat "$issues")" "session-transcript status=$expected"
    else
        fail "$label execution issue log missing"
    fi
}

run_capture "source-empty" "source-file-missing" "" "false"
run_capture "source-missing" "source-file-missing" "$TMP/missing-source.env" "false"

source_no_path="$TMP/source-no-path.env"
printf 'STATUS=ok\n' > "$source_no_path"
run_capture "path-missing" "transcript-path-missing" "$source_no_path" "false"

source_stale="$TMP/source-stale.env"
printf 'TRANSCRIPT_PATH=%s\n' "$TMP/missing-transcript.jsonl" > "$source_stale"
run_capture "file-missing" "transcript-file-missing" "$source_stale" "false"

transcript="$TMP/transcript.jsonl"
printf '{"type":"message","text":"hello"}\n' > "$transcript"
source_ok="$TMP/source-ok.env"
printf 'TRANSCRIPT_PATH=%s\n' "$transcript" > "$source_ok"
run_capture "captured-run" "captured" "$source_ok" "false"

run_capture "suppressed-run" "suppressed-no-logs-commit" "$source_ok" "true"

echo
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
echo "All assertions passed."
