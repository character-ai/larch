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
    local implement_tmpdir="${5:-}"
    local home_dir="${6:-}"
    local repo="$TMP/$label-repo"
    local log_root="$TMP/$label-staging/larch-logs"
    local issues="$TMP/$label-execution-issues.md"
    local env_args=("PATH=${PATH:-}" "IMPLEMENT_TMPDIR=" "HOME=$TMP/default-home")

    if [ -n "$implement_tmpdir" ]; then
        env_args+=("IMPLEMENT_TMPDIR=$implement_tmpdir")
    fi
    if [ -n "$home_dir" ]; then
        env_args+=("HOME=$home_dir")
    fi

    mkdir -p "$repo"
    git -C "$repo" init >/dev/null 2>&1
    git -C "$repo" config user.email "ci@test"
    git -C "$repo" config user.name "Test CI"
    touch "$repo/.gitkeep"
    git -C "$repo" add .
    git -C "$repo" commit -q -m "init"

    out="$(cd "$repo" && env "${env_args[@]}" "$CAPTURE" \
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

# Returns the Claude project dir path for a given repo dir and home dir,
# mirroring token-claude-source.sh encoding (repo-root → sed 's#/#-#g').
project_dir_for_repo() {
    local repo_dir="$1"
    local home_dir="$2"
    local real
    real=$(cd "$repo_dir" && pwd -P)
    local encoded
    encoded=$(printf '%s' "$real" | sed 's#/#-#g')
    printf '%s/.claude/projects/%s' "$home_dir" "$encoded"
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

# Fallback discovery tests — the script narrows search to the encoded project dir
# for the current git repo, using IMPLEMENT_TMPDIR/session-id as stable time reference.

# Pre-create the repo dir so we can compute the canonical encoded path before run_capture.
fallback_label="fallback-discovery"
fallback_repo="$TMP/$fallback_label-repo"
fallback_impl="$TMP/${fallback_label}-impl"
fallback_home="$TMP/${fallback_label}-home"
mkdir -p "$fallback_repo" "$fallback_impl"
fallback_project=$(project_dir_for_repo "$fallback_repo" "$fallback_home")
mkdir -p "$fallback_project"
# Stable session-id reference: set mtime to the past so transcripts created after are "newer".
printf 'test-session\n' > "$fallback_impl/session-id"
touch -t 200001010000 "$fallback_impl/session-id"
fallback_transcript="$fallback_project/fallback-session.jsonl"
printf '{"type":"message","text":"fallback"}\n' > "$fallback_transcript"
run_capture "$fallback_label" "captured" "" "false" "$fallback_impl" "$fallback_home"
assert_contains \
    "$fallback_label recovery warning" \
    "$(cat "$TMP/$fallback_label-execution-issues.md")" \
    "source-file-recovered-via-discovery"

fallback_recovered_label="fallback-discovery-recovered-status"
fallback_recovered_repo="$TMP/$fallback_recovered_label-repo"
fallback_recovered_impl="$TMP/${fallback_recovered_label}-impl"
fallback_recovered_home="$TMP/${fallback_recovered_label}-home"
mkdir -p "$fallback_recovered_repo" "$fallback_recovered_impl"
fallback_recovered_project=$(project_dir_for_repo "$fallback_recovered_repo" "$fallback_recovered_home")
mkdir -p "$fallback_recovered_project"
printf 'test-session\n' > "$fallback_recovered_impl/session-id"
touch -t 200001010000 "$fallback_recovered_impl/session-id"
fallback_recovered_transcript="$fallback_recovered_project/fallback-recovered-session.jsonl"
printf '{"type":"message","text":"fallback recovered"}\n' > "$fallback_recovered_transcript"
run_capture "$fallback_recovered_label" "captured" "" "false" "$fallback_recovered_impl" "$fallback_recovered_home"
assert_contains \
    "$fallback_recovered_label recovery warning" \
    "$(cat "$TMP/$fallback_recovered_label-execution-issues.md")" \
    "source-file-recovered-via-discovery"

# No matching transcript: project dir exists but no *.jsonl files.
fallback_no_match_label="fallback-no-match"
fallback_no_match_repo="$TMP/$fallback_no_match_label-repo"
fallback_no_match_impl="$TMP/${fallback_no_match_label}-impl"
fallback_no_match_home="$TMP/${fallback_no_match_label}-home"
mkdir -p "$fallback_no_match_repo" "$fallback_no_match_impl"
fallback_no_match_project=$(project_dir_for_repo "$fallback_no_match_repo" "$fallback_no_match_home")
mkdir -p "$fallback_no_match_project"
printf 'test-session\n' > "$fallback_no_match_impl/session-id"
touch -t 200001010000 "$fallback_no_match_impl/session-id"
run_capture "$fallback_no_match_label" "source-file-missing" "" "false" "$fallback_no_match_impl" "$fallback_no_match_home"

# Stale transcript: *.jsonl exists but is older than the session-id reference — not selected.
fallback_stale_label="fallback-stale-jsonl"
fallback_stale_repo="$TMP/$fallback_stale_label-repo"
fallback_stale_impl="$TMP/${fallback_stale_label}-impl"
fallback_stale_home="$TMP/${fallback_stale_label}-home"
mkdir -p "$fallback_stale_repo" "$fallback_stale_impl"
fallback_stale_project=$(project_dir_for_repo "$fallback_stale_repo" "$fallback_stale_home")
mkdir -p "$fallback_stale_project"
fallback_stale_transcript="$fallback_stale_project/stale-session.jsonl"
printf '{"type":"message","text":"stale"}\n' > "$fallback_stale_transcript"
# session-id is newer than the transcript — transcript should NOT be selected.
touch -t 200001010000 "$fallback_stale_transcript"
printf 'test-session\n' > "$fallback_stale_impl/session-id"
run_capture "$fallback_stale_label" "source-file-missing" "" "false" "$fallback_stale_impl" "$fallback_stale_home"

echo
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
echo "All assertions passed."
