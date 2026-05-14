#!/usr/bin/env bash
# test-implement-finalize.sh — offline regression harness for implement-finalize.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_SCRIPT="$SCRIPT_DIR/implement-finalize.sh"

[ -x "$REAL_SCRIPT" ] || { echo "FAIL: $REAL_SCRIPT not executable"; exit 1; }

PASS=0
FAIL=0
SANDBOX=""

assert_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -qF -- "$needle"; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        echo "  expected to contain: $needle"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    fi
}

assert_not_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -qF -- "$needle"; then
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        echo "  did not expect: $needle"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    else
        PASS=$((PASS + 1))
        echo "PASS: $label"
    fi
}

assert_file_contains() {
    local needle=$1 path=$2 label=$3 content
    content=$(cat "$path" 2>/dev/null || true)
    assert_contains "$needle" "$content" "$label"
}

assert_file_not_contains() {
    local needle=$1 path=$2 label=$3 content
    content=$(cat "$path" 2>/dev/null || true)
    assert_not_contains "$needle" "$content" "$label"
}

assert_rc() {
    local actual=$1 expected=$2 label=$3
    if [ "$actual" -eq "$expected" ]; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (expected rc=$expected got rc=$actual)"
    fi
}

normalize_elapsed() {
    sed -E \
        -e 's/\([0-9]+s\)/(<elapsed>)/g' \
        -e 's/elapsed=[0-9]+[0-9hms]*/elapsed=<elapsed>/g'
}

override_value() {
    local key=$1 default=$2 pair
    shift 2
    for pair in "$@"; do
        case "$pair" in
            "$key="*) printf '%s' "${pair#*=}"; return ;;
        esac
    done
    printf '%s' "$default"
}

write_state() {
    local path=$1
    shift
    {
        printf 'BRANCH_NAME=%s\n' "$(override_value BRANCH_NAME feature/finalize "$@")"
        printf 'PR_NUMBER=%s\n' "$(override_value PR_NUMBER 123 "$@")"
        printf 'PR_TITLE=%s\n' "$(override_value PR_TITLE 'Implement finalizer' "$@")"
        printf 'PR_URL=%s\n' "$(override_value PR_URL 'https://github.example/pr/123' "$@")"
        printf 'ISSUE_NUMBER=%s\n' "$(override_value ISSUE_NUMBER 456 "$@")"
        printf 'REPO=%s\n' "$(override_value REPO owner/repo "$@")"
        printf 'DRAFT=%s\n' "$(override_value DRAFT false "$@")"
        printf 'MERGE=%s\n' "$(override_value MERGE true "$@")"
        printf 'DEFERRED=%s\n' "$(override_value DEFERRED false "$@")"
        printf 'REPO_UNAVAILABLE=%s\n' "$(override_value REPO_UNAVAILABLE false "$@")"
        printf 'PR_CLOSED=%s\n' "$(override_value PR_CLOSED false "$@")"
        printf 'DESIGN_ONLY_DONE=%s\n' "$(override_value DESIGN_ONLY_DONE false "$@")"
        printf 'BAIL_NEEDS_USER_INPUT=%s\n' "$(override_value BAIL_NEEDS_USER_INPUT false "$@")"
        printf 'STALL_TRACKING=%s\n' "$(override_value STALL_TRACKING false "$@")"
        printf 'STALL_STEP=%s\n' "$(override_value STALL_STEP 12d "$@")"
        printf 'DONE_RENAME_APPLIED=%s\n' "$(override_value DONE_RENAME_APPLIED false "$@")"
        printf 'EXPECTED_SESSION_ID=%s\n' "$(override_value EXPECTED_SESSION_ID session-123 "$@")"
        printf 'EXPECTED_TMPDIR_BASENAME_PREFIX=%s\n' "$(override_value EXPECTED_TMPDIR_BASENAME_PREFIX tmp "$@")"
    } > "$path"
}

write_postbump_state() {
    local path=$1 reasoning_file manifest_path
    shift
    reasoning_file=$(override_value BUMP_REASONING_FILE "$SANDBOX/tmp/larch-log-batches-input/version-bump-reasoning-sanitized.md" "$@")
    manifest_path=$(override_value MANIFEST_PATH "$SANDBOX/tmp/manifest.json" "$@")
    mkdir -p "$SANDBOX/tmp/larch-log-batches-input"
    [ -e "$reasoning_file" ] || printf 'Bump reasoning\n' > "$reasoning_file"
    if [ -n "$manifest_path" ] && [ ! -e "$manifest_path" ]; then
        printf '{"summary_bullets":["Ship postbump finalization"]}\n' > "$manifest_path"
    fi
    {
        printf 'BRANCH_NAME=%s\n' "$(override_value BRANCH_NAME feature/finalize "$@")"
        printf 'ISSUE_NUMBER=%s\n' "$(override_value ISSUE_NUMBER 456 "$@")"
        printf 'REPO=%s\n' "$(override_value REPO owner/repo "$@")"
        printf 'REPO_UNAVAILABLE=%s\n' "$(override_value REPO_UNAVAILABLE false "$@")"
        printf 'FORKED_TARGET=%s\n' "$(override_value FORKED_TARGET false "$@")"
        printf 'HAS_BUMP=%s\n' "$(override_value HAS_BUMP true "$@")"
        printf 'BUMP_TYPE=%s\n' "$(override_value BUMP_TYPE PATCH "$@")"
        printf 'NEW_VERSION=%s\n' "$(override_value NEW_VERSION 17.0.4 "$@")"
        printf 'BUMP_REASONING_FILE=%s\n' "$reasoning_file"
        printf 'MANIFEST_PATH=%s\n' "$manifest_path"
        printf 'TOOL_LABEL=%s\n' "$(override_value TOOL_LABEL codex "$@")"
        printf 'EXPECTED_SESSION_ID=%s\n' "$(override_value EXPECTED_SESSION_ID session-123 "$@")"
        printf 'EXPECTED_TMPDIR_BASENAME_PREFIX=%s\n' "$(override_value EXPECTED_TMPDIR_BASENAME_PREFIX tmp "$@")"
    } > "$path"
}

build_sandbox() {
    SANDBOX=$(mktemp -d /tmp/larch-finalize-test.XXXXXX)
    mkdir -p "$SANDBOX/scripts" "$SANDBOX/tmp" "$SANDBOX/bin" "$SANDBOX/repo/.git"
    printf 'session-123\n' > "$SANDBOX/tmp/session-id"
    cat > "$SANDBOX/repo/CHANGELOG.md" <<'CHANGELOG'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [17.0.3] - 2026-05-01

### Changed

- Prior change.
CHANGELOG
    cp "$SANDBOX/repo/CHANGELOG.md" "$SANDBOX/original-CHANGELOG.md"
    cp "$REAL_SCRIPT" "$SANDBOX/scripts/implement-finalize.sh"
    chmod +x "$SANDBOX/scripts/implement-finalize.sh"

    cat > "$SANDBOX/scripts/local-cleanup.sh" <<'STUB'
#!/usr/bin/env bash
echo "CLEANUP_SUCCESS=${STUB_CLEANUP_SUCCESS:-true}"
echo "CURRENT_BRANCH=${STUB_CURRENT_BRANCH:-main}"
echo "BRANCH_DELETED=${STUB_BRANCH_DELETED:-true}"
exit "${STUB_LOCAL_RC:-0}"
STUB
    cat > "$SANDBOX/scripts/verify-main.sh" <<'STUB'
#!/usr/bin/env bash
echo "VERIFIED=${STUB_VERIFIED:-true}"
echo "COMMIT_HASH=${STUB_COMMIT_HASH:-abc1234}"
echo "COMMIT_MESSAGE=${STUB_COMMIT_MESSAGE:-Implement finalizer (#123)}"
exit "${STUB_VERIFY_RC:-0}"
STUB
    cat > "$SANDBOX/scripts/get-issue-info.sh" <<'STUB'
#!/usr/bin/env bash
field=""
while [ $# -gt 0 ]; do
  case "$1" in
    --field) field=$2; shift 2 ;;
    *) shift ;;
  esac
done
if [ "$field" = "state" ]; then
  echo "VALUE=${STUB_ISSUE_STATE:-OPEN}"
else
  echo "VALUE=${STUB_ISSUE_URL:-https://github.example/owner/repo/issues/456}"
fi
exit "${STUB_GET_ISSUE_RC:-0}"
STUB
    cat > "$SANDBOX/scripts/tracking-issue-write.sh" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$@" >> "$SANDBOX/rename-argv.txt"
if [ "\${STUB_RENAME_FAILED:-false}" = "true" ]; then
  echo "FAILED=true"
  echo "ERROR=stub failure"
  exit 2
fi
echo "RENAMED=true"
echo "NEW_TITLE=stub"
exit 0
STUB
    cat > "$SANDBOX/scripts/round-trip-detect.sh" <<'STUB'
#!/usr/bin/env bash
if [ "${STUB_ROUND_TRIP_DETECT_FAIL:-false}" = "true" ]; then
  exit 1
fi
echo "ROUND_TRIP=${STUB_ROUND_TRIP:-false}"
exit 0
STUB
    cat > "$SANDBOX/scripts/cleanup-tmpdir.sh" <<STUB
#!/usr/bin/env bash
dir=""
while [ \$# -gt 0 ]; do
  case "\$1" in
    --dir) dir="\${2:-}"; shift 2 ;;
    *) shift ;;
  esac
done
if [ "\${STUB_REQUIRE_RUN_CLEANED_UP:-false}" = "true" ] && [ ! -f "\$dir/.run-cleaned-up" ]; then
  echo "missing .run-cleaned-up before cleanup" >&2
  exit 42
fi
printf '%s\n' "\$@" > "$SANDBOX/cleanup-argv.txt"
exit "\${STUB_CLEANUP_TMPDIR_RC:-0}"
STUB
    cat > "$SANDBOX/scripts/read-session-env-key.sh" <<'STUB'
#!/usr/bin/env bash
default=""
while [ $# -gt 0 ]; do
  case "$1" in
    --default) default=$2; shift 2 ;;
    *) shift ;;
  esac
done
printf '%s\n' "$default"
STUB
    cat > "$SANDBOX/scripts/token-ledger.sh" <<STUB
#!/usr/bin/env bash
echo "token-ledger \$*" >> "$SANDBOX/ledger-calls.txt"
exit 0
STUB
    cat > "$SANDBOX/scripts/timing-ledger.sh" <<STUB
#!/usr/bin/env bash
echo "timing-ledger \$*" >> "$SANDBOX/ledger-calls.txt"
exit 0
STUB
    cat > "$SANDBOX/scripts/token-report.sh" <<'STUB'
#!/usr/bin/env bash
echo "token report"
exit 0
STUB
    cat > "$SANDBOX/scripts/timing-report.sh" <<'STUB'
#!/usr/bin/env bash
echo "timing report"
exit 0
STUB
    cat > "$SANDBOX/scripts/larch-log.sh" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$@" > "$SANDBOX/larch-log-argv.txt"
# Record the inherited IMPLEMENT_TMPDIR for export regression tests.
printf 'IMPLEMENT_TMPDIR=%s\n' "\${IMPLEMENT_TMPDIR:-UNSET}" >> "$SANDBOX/larch-log-env.txt"
if [ "\${STUB_LARCH_LOG_FAIL:-false}" = "true" ]; then
  echo "FAILED=true"
  echo "ERROR=stub larch-log failure"
  exit 2
fi
echo "LOG_WRITTEN=true"
echo "LOG_PATH=$SANDBOX/repo/larch-logs/implement/tmp/version-bump-reasoning.md"
echo "BYTES=15"
echo "SHA256=stub"
echo "COMMIT_SHA="
echo "UNCHANGED=false"
exit 0
STUB
    cat > "$SANDBOX/scripts/check-changelog-present.sh" <<'STUB'
#!/usr/bin/env bash
echo "CHANGELOG_PRESENT=${STUB_CHANGELOG_PRESENT:-true}"
exit 0
STUB
    cat > "$SANDBOX/scripts/git-amend-add.sh" <<'STUB'
#!/usr/bin/env bash
if [ "${STUB_AMEND_FAIL:-false}" = "true" ]; then
  exit 1
fi
exit 0
STUB
    cat > "$SANDBOX/scripts/rebase-push.sh" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$@" > "$SANDBOX/rebase-argv.txt"
case "\${STUB_REBASE_RC:-0}" in
  0)
    if [ "\${STUB_ALREADY_FRESH:-false}" = "true" ]; then
      echo "SKIPPED_ALREADY_FRESH=true"
    fi
    exit 0 ;;
  1)
    echo "CONFLICT_FILES=CHANGELOG.md"
    exit 1 ;;
  3)
    echo "REBASE_ERROR=stub rebase failed"
    exit 3 ;;
  *)
    exit "\${STUB_REBASE_RC:-9}" ;;
esac
STUB
    cat > "$SANDBOX/scripts/check-remote-branch.sh" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$@" > "$SANDBOX/check-remote-argv.txt"
echo "STATE=\${STUB_REMOTE_STATE:-present}"
case "\${STUB_REMOTE_STATE:-present}" in
  present) echo "RC=0" ;;
  absent) echo "RC=2" ;;
  *) echo "RC=128"; echo "ERROR=stub transport" ;;
esac
exit 0
STUB
    cat > "$SANDBOX/scripts/git-force-push.sh" <<'STUB'
#!/usr/bin/env bash
echo "BRANCH=feature/finalize"
echo "STATUS=${STUB_FORCE_PUSH_STATUS:-pushed}"
case "${STUB_FORCE_PUSH_STATUS:-pushed}" in
  pushed|noop_same_ref) echo "PUSHED=true"; exit 0 ;;
  *) echo "PUSHED=false"; exit 1 ;;
esac
STUB
    cat > "$SANDBOX/bin/git" <<STUB
#!/usr/bin/env bash
if [ "\${1:-}" = "-C" ]; then
  shift 2
fi
case "\${1:-} \${2:-} \${3:-}" in
  "rev-parse --show-toplevel ")
    echo "\${STUB_REPO_ROOT:-$SANDBOX/repo}"
    ;;
  "rev-parse --abbrev-ref HEAD")
    echo "\${STUB_CURRENT_BRANCH:-feature/finalize}"
    ;;
  "rev-parse --git-dir ")
    echo "\${STUB_GIT_DIR:-$SANDBOX/repo/.git}"
    ;;
  "status --porcelain CHANGELOG.md")
    if [ "\${STUB_CHANGELOG_DIRTY:-false}" = "true" ]; then
      echo " M CHANGELOG.md"
    fi
    ;;
  "status --porcelain ")
    if [ "\${STUB_STATUS_RC:-0}" -ne 0 ]; then
      echo "\${STUB_STATUS_ERROR:-status failed}" >&2
      exit "\${STUB_STATUS_RC:-1}"
    fi
    if [ "\${STUB_GIT_DIRTY:-false}" = "true" ]; then
      echo " M file.txt"
    fi
    ;;
  "checkout -- CHANGELOG.md")
    cp "$SANDBOX/original-CHANGELOG.md" "$SANDBOX/repo/CHANGELOG.md" 2>/dev/null || true
    ;;
  "stash push -u")
    printf '%s\n' "\$@" > "$SANDBOX/stash-argv.txt"
    if [ "\${STUB_STASH_RC:-0}" -ne 0 ]; then
      echo "\${STUB_STASH_ERROR:-cannot stash}"
      exit "\${STUB_STASH_RC:-1}"
    fi
    ;;
  "stash list -1")
    echo "\${STUB_STASH_REF:-stash@{0}}"
    ;;
  "stash list --format=%gD"|"stash list --format=%gD %gs")
    # Label-matching lookup: on success the stub emits a synthesized line
    # whose ref is STUB_STASH_REF and whose message contains the label that
    # the production code wrote with \`stash push -u -m\`. STUB_STASH_LABEL
    # is set by the test before invocation; if absent, return nothing so
    # the production code falls back to \`stash list -1\`.
    if [ "\${STUB_STASH_LABEL_OUT:-}" = "skip" ]; then
      :
    else
      echo "\${STUB_STASH_REF:-stash@{0}} On stalled-branch: \${STUB_STASH_LABEL:-larch-stalled-456-12d 20260505T000000Z}"
    fi
    ;;
  *)
    echo "unexpected git invocation: \$*" >&2
    exit 99
    ;;
esac
STUB
    cat > "$SANDBOX/bin/ps" <<'STUB'
#!/usr/bin/env bash
if [ "${STUB_PS_MODE:-}" = "background" ]; then
  case "$*" in
    "-o ppid= -p "*)
      echo "${STUB_PS_PPID:-1}"
      exit 0
      ;;
    "-A -o pid= -o args=")
      printf '%s %s\n' "$STUB_PS_BG_PID" "$STUB_PS_BG_ARG"
      exit 0
      ;;
  esac
fi
exec /bin/ps "$@"
STUB
    cat > "$SANDBOX/bin/gh" <<STUB
#!/usr/bin/env bash
if [ "\${1:-}" = "issue" ] && [ "\${2:-}" = "view" ]; then
  if [ "\${STUB_GH_ISSUE_VIEW_FAIL:-false}" = "true" ]; then
    exit 1
  fi
  # Production path passes --repo "\$REPO". Record argv (incl. --repo) for
  # assertions and require it when STUB_GH_REQUIRE_REPO=true (post-review
  # FINDING_F5).
  printf '%s\n' "\$@" > "$SANDBOX/gh-issue-view-argv.txt"
  saw_repo=""
  while [ \$# -gt 0 ]; do
    case "\$1" in
      --repo) saw_repo="\${2:-}"; shift 2 ;;
      *) shift ;;
    esac
  done
  if [ "\${STUB_GH_REQUIRE_REPO:-false}" = "true" ] && [ -z "\$saw_repo" ]; then
    echo "stub: gh issue view missing --repo" >&2
    exit 1
  fi
  # Emit title+body via the same TITLE= line + body shape that the
  # production --jq expression yields (round-trip detection consumes it).
  printf 'TITLE=%s\n%s\n' "\${STUB_ISSUE_TITLE:-}" "\${STUB_ISSUE_BODY:-}"
  exit 0
fi
echo "unexpected gh invocation: \$*" >&2
exit 99
STUB
    chmod +x "$SANDBOX/scripts/"*.sh
    chmod +x "$SANDBOX/bin/git" "$SANDBOX/bin/gh" "$SANDBOX/bin/ps"
}

run_subject() {
    (cd "$SANDBOX/repo" && PATH="$SANDBOX/bin:$PATH" "$SANDBOX/scripts/implement-finalize.sh" "$@") 2>&1 | normalize_elapsed
}

run_subject_raw_rc() {
    set +e
    OUT=$( (cd "$SANDBOX/repo" && PATH="$SANDBOX/bin:$PATH" "$SANDBOX/scripts/implement-finalize.sh" "$@") 2>&1 | normalize_elapsed )
    RC=$?
    set -e
}

build_sandbox
trap 'rm -rf "$SANDBOX"' EXIT

STATE="$SANDBOX/tmp/finalize-state.sh"
BAIL="$SANDBOX/tmp/final-bail-reason.txt"
: > "$BAIL"

write_state "$STATE" DRAFT=true
OUT=$(run_subject postmerge --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "⏭️ 14: local cleanup status=bypass reason=draft-set elapsed=<elapsed>" "$OUT" "postmerge: draft skip breadcrumb"
assert_contains "LOCAL_CLEANUP_STATUS=skipped-draft" "$OUT" "postmerge: draft status"
assert_contains "VERIFY_MAIN_STATUS=skipped" "$OUT" "postmerge: draft skips verify"

write_state "$STATE" MERGE=false
OUT=$(run_subject postmerge --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "⏭️ 14: local cleanup status=bypass reason=merge-not-set elapsed=<elapsed>" "$OUT" "postmerge: merge=false skip"
assert_contains "LOCAL_CLEANUP_STATUS=skipped-merge-false" "$OUT" "postmerge: merge=false status"

printf 'merge blocked\n' > "$BAIL"
write_state "$STATE"
OUT=$(run_subject postmerge --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "**⚠ 14: local cleanup — skipped (PR not merged), still on feature/finalize (<elapsed>)**" "$OUT" "postmerge: bail skip warning"
assert_contains "FINALIZE_WARNINGS=1" "$OUT" "postmerge: bail warning counted"
: > "$BAIL"

write_state "$STATE"
OUT=$(run_subject postmerge --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "✅ 14: local cleanup status=complete outcome=branch-deleted elapsed=<elapsed>" "$OUT" "postmerge: cleanup success"
assert_contains "✅ 15: verify main status=complete sha=abc1234 elapsed=<elapsed>" "$OUT" "postmerge: verify success"
assert_contains "LOCAL_CLEANUP_STATUS=success" "$OUT" "postmerge: success status"
assert_contains "VERIFY_MAIN_STATUS=verified" "$OUT" "postmerge: verified status"

write_state "$STATE"
OUT=$(STUB_CLEANUP_SUCCESS=false STUB_CURRENT_BRANCH=feature/finalize STUB_BRANCH_DELETED=false STUB_VERIFIED=false STUB_COMMIT_HASH=def5678 STUB_COMMIT_MESSAGE=other run_subject postmerge --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "**⚠ 14: local cleanup — partially failed, branch: feature/finalize, deleted: false (<elapsed>)**" "$OUT" "postmerge: partial warning"
assert_contains "**⚠ 15: verify main — unexpected HEAD: def5678 \"other\". Expected: \"Implement finalizer (#123)\" (<elapsed>)**" "$OUT" "postmerge: verify warning"
assert_contains "FINALIZE_WARNINGS=2" "$OUT" "postmerge: two warnings counted"

write_state "$STATE" MERGE=yes
run_subject_raw_rc postmerge --state-file "$STATE" --final-bail-reason-file "$BAIL"
assert_rc "$RC" 2 "postmerge: invalid boolean exits 2"
assert_contains "MERGE must be true or false" "$OUT" "postmerge: invalid boolean diagnostic"

write_state "$STATE" ISSUE_NUMBER=
OUT=$(run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "RENAME_BRANCH=skipped" "$OUT" "teardown: empty issue skips rename"
assert_contains "RENAME_STATUS=skipped" "$OUT" "teardown: empty issue skipped status"

# kill_session_background_processes: a process launched with the session tmpdir in its
# argv (argv[0] = $SANDBOX/tmp/bg-session-process.sh) should be killed during teardown.
write_state "$STATE" ISSUE_NUMBER=
BG_SCRIPT="$SANDBOX/tmp/bg-session-process.sh"
printf '#!/usr/bin/env bash\nwhile true; do sleep 1; done\n' > "$BG_SCRIPT"
chmod +x "$BG_SCRIPT"
"$BG_SCRIPT" &
BG_PID=$!
OUT=$(STUB_PS_MODE=background STUB_PS_BG_PID="$BG_PID" STUB_PS_BG_ARG="$BG_SCRIPT" run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
if ! kill -0 "$BG_PID" 2>/dev/null; then
    PASS=$((PASS + 1))
    echo "PASS: teardown: kill_session_background_processes killed stale background process"
else
    kill "$BG_PID" 2>/dev/null || true
    FAIL=$((FAIL + 1))
    echo "FAIL: teardown: stale background process still running after teardown"
fi
assert_contains "**⚠ 18: killed 1 stale background process(es)" "$OUT" "teardown: kill_session_background_processes emits warning"
assert_contains "FINALIZE_WARNINGS=1" "$OUT" "teardown: kill counts as warning"

write_state "$STATE" STALL_TRACKING=true
: > "$SANDBOX/rename-argv.txt"
rm -f "$SANDBOX/gh-issue-view-argv.txt"
# Require --repo on every gh issue view from the round-trip detector path
# so an accidental drop of --repo regresses the assertion (FINDING_F5).
OUT=$(STUB_ROUND_TRIP=true STUB_GH_REQUIRE_REPO=true run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
RENAME_ARGV=$(cat "$SANDBOX/rename-argv.txt")
GH_ARGV=$(cat "$SANDBOX/gh-issue-view-argv.txt" 2>/dev/null || true)
assert_contains "--state" "$RENAME_ARGV" "teardown: branch A rename called"
assert_contains "stalled" "$RENAME_ARGV" "teardown: branch A renames stalled"
assert_contains "--round-trip" "$RENAME_ARGV" "teardown: branch A passes round-trip flag"
assert_contains "true" "$RENAME_ARGV" "teardown: branch A body marker passes round-trip true"
assert_contains "--repo" "$GH_ARGV" "teardown: branch A round-trip detector fetch passes --repo"
assert_contains "owner/repo" "$GH_ARGV" "teardown: branch A round-trip detector fetch scopes to state REPO"
assert_contains "RENAME_BRANCH=A" "$OUT" "teardown: branch A tail"
assert_contains "RENAME_STATUS=ok" "$OUT" "teardown: branch A ok"
assert_contains "STASH_REF=" "$OUT" "teardown: clean stalled run emits empty stash ref"
assert_contains "SENTINEL_WRITTEN=true" "$OUT" "teardown: clean stalled run writes sentinel"
assert_file_contains "STALL_STEP=12d" "$SANDBOX/repo/.git/larch-stalled-run.txt" "teardown: clean sentinel records stall step"
assert_file_contains "STASH_REF=" "$SANDBOX/repo/.git/larch-stalled-run.txt" "teardown: clean sentinel records empty stash"

write_state "$STATE" STALL_TRACKING=true STALL_STEP=8b
rm -f "$SANDBOX/stash-argv.txt" "$SANDBOX/repo/.git/larch-stalled-run.txt"
: > "$SANDBOX/rename-argv.txt"
OUT=$(STUB_GIT_DIRTY=true run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
STASH_ARGV=$(cat "$SANDBOX/stash-argv.txt")
assert_contains "larch-stalled-456-8b" "$STASH_ARGV" "teardown: dirty stalled run stashes with larch label"
assert_contains "STASH_REF=stash@{0}" "$OUT" "teardown: dirty stalled run emits stash ref"
assert_contains "SENTINEL_WRITTEN=true" "$OUT" "teardown: dirty stalled run writes sentinel"
assert_file_contains "ISSUE_NUMBER=456" "$SANDBOX/repo/.git/larch-stalled-run.txt" "teardown: dirty sentinel records issue"
assert_file_contains "ISSUE_URL=https://github.example/owner/repo/issues/456" "$SANDBOX/repo/.git/larch-stalled-run.txt" "teardown: dirty sentinel records URL"
assert_file_contains "STALL_STEP=8b" "$SANDBOX/repo/.git/larch-stalled-run.txt" "teardown: dirty sentinel records stall step"
assert_file_contains "STASH_REF=stash@{0}" "$SANDBOX/repo/.git/larch-stalled-run.txt" "teardown: dirty sentinel records stash ref"

write_state "$STATE" STALL_TRACKING=true STALL_STEP=8b
rm -f "$SANDBOX/stash-argv.txt" "$SANDBOX/repo/.git/larch-stalled-run.txt"
: > "$SANDBOX/rename-argv.txt"
OUT=$(STUB_STATUS_RC=1 run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "git status failed" "$OUT" "teardown: status failure warns and skips stash"
if [ ! -e "$SANDBOX/stash-argv.txt" ]; then
    PASS=$((PASS + 1))
    echo "PASS: teardown: status failure means no stash attempted"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: teardown: status failure should not attempt stash"
fi
# Sentinel is still written (no stash, but we record the stall context).
assert_contains "SENTINEL_WRITTEN=true" "$OUT" "teardown: status failure still writes sentinel"
assert_contains "STASH_REF=" "$OUT" "teardown: status failure emits empty stash ref"

write_state "$STATE" STALL_TRACKING=true
: > "$SANDBOX/rename-argv.txt"
OUT=$(STUB_ISSUE_STATE=CLOSED run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
RENAME_ARGV=$(cat "$SANDBOX/rename-argv.txt")
assert_not_contains "rename" "$RENAME_ARGV" "teardown: closed stalled issue silently skips rename"
assert_contains "RENAME_BRANCH=A" "$OUT" "teardown: closed stalled branch identified"
assert_contains "RENAME_STATUS=skipped" "$OUT" "teardown: closed stalled status skipped"

write_state "$STATE" STALL_TRACKING=false DONE_RENAME_APPLIED=false PR_NUMBER=789
rm -f "$SANDBOX/repo/.git/larch-stalled-run.txt" "$SANDBOX/stash-argv.txt"
: > "$SANDBOX/rename-argv.txt"
OUT=$(STUB_ROUND_TRIP=true run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
RENAME_ARGV=$(cat "$SANDBOX/rename-argv.txt")
assert_contains "done" "$RENAME_ARGV" "teardown: branch B renames done"
assert_contains "--round-trip" "$RENAME_ARGV" "teardown: branch B passes round-trip flag"
assert_contains "true" "$RENAME_ARGV" "teardown: branch B body marker passes round-trip true"
assert_contains "RENAME_BRANCH=B" "$OUT" "teardown: branch B tail"
assert_contains "STASH_REF=" "$OUT" "teardown: success path emits empty stash ref"
assert_contains "SENTINEL_WRITTEN=false" "$OUT" "teardown: success path does not write sentinel"
if [ ! -e "$SANDBOX/repo/.git/larch-stalled-run.txt" ] && [ ! -e "$SANDBOX/stash-argv.txt" ]; then
    PASS=$((PASS + 1))
    echo "PASS: teardown: success path leaves no sentinel or stash"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: teardown: success path left sentinel or stash"
fi

write_state "$STATE" STALL_TRACKING=false DONE_RENAME_APPLIED=false PR_NUMBER= DESIGN_ONLY_DONE=true
: > "$SANDBOX/rename-argv.txt"
OUT=$(run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
RENAME_ARGV=$(cat "$SANDBOX/rename-argv.txt")
assert_contains "done" "$RENAME_ARGV" "teardown: branch B design-only renames done"
assert_contains "false" "$RENAME_ARGV" "teardown: no body marker passes round-trip false"
assert_contains "RENAME_BRANCH=B" "$OUT" "teardown: branch B design-only tail"

write_state "$STATE" STALL_TRACKING=false DONE_RENAME_APPLIED=false PR_NUMBER=789
: > "$SANDBOX/rename-argv.txt"
OUT=$(STUB_GH_ISSUE_VIEW_FAIL=true run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
RENAME_ARGV=$(cat "$SANDBOX/rename-argv.txt")
assert_contains "round-trip detection skipped: gh issue title/body fetch failed" "$OUT" "teardown: gh issue view failure warns"
assert_contains "--round-trip" "$RENAME_ARGV" "teardown: detection failure still renames"
assert_contains "false" "$RENAME_ARGV" "teardown: detection failure defaults false"
assert_contains "RENAME_STATUS=ok" "$OUT" "teardown: detection failure does not fail rename"

write_state "$STATE" DONE_RENAME_APPLIED=true
OUT=$(run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "RENAME_BRANCH=C" "$OUT" "teardown: branch C selected"
assert_contains "RENAME_STATUS=skipped" "$OUT" "teardown: branch C skipped"

write_state "$STATE" STALL_TRACKING=true
OUT=$(STUB_RENAME_FAILED=true run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "**⚠ 18: tracking-issue rename to STALLED failed. Continuing.**" "$OUT" "teardown: rename failure warning"
assert_contains "RENAME_STATUS=failed" "$OUT" "teardown: rename failure status"
assert_contains "FINALIZE_WARNINGS=1" "$OUT" "teardown: rename warning counted"

write_state "$STATE"
OUT=$(run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "📎 Tracking issue: https://github.example/owner/repo/issues/456" "$OUT" "teardown: tracking URL printed"
assert_contains "✅ 18: cleanup status=complete elapsed=<elapsed>" "$OUT" "teardown: final breadcrumb"
assert_contains "ISSUE_URL=https://github.example/owner/repo/issues/456" "$OUT" "teardown: issue URL tail"

# Teardown MUST NOT emit the Step 18 — done closing mark. The cap is
# emitted exclusively by the orchestrator-side terminal Bash block in
# skills/implement/SKILL.md Step 18 AFTER --since-last-mark --terse runs,
# so a teardown-side duplicate would race ahead of those terse reports
# and silently make them slice an empty window. Pin the negative
# assertion so a future re-add regresses CI.
write_state "$STATE"
: > "$SANDBOX/ledger-calls.txt"
OUT=$(run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
LEDGER_CALLS=$(cat "$SANDBOX/ledger-calls.txt" 2>/dev/null || true)
assert_not_contains 'Step 18 — done' "$LEDGER_CALLS" "teardown: does NOT emit Step 18 — done (orchestrator owns the cap)"

write_state "$STATE"
rm -f "$SANDBOX/tmp/.run-cleaned-up"
OUT=$(STUB_REQUIRE_RUN_CLEANED_UP=true run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "✅ 18: cleanup status=complete elapsed=<elapsed>" "$OUT" "teardown: run-cleaned-up exists before cleanup-tmpdir"
if [ -f "$SANDBOX/tmp/.run-cleaned-up" ]; then
    PASS=$((PASS + 1))
    echo "PASS: teardown: run-cleaned-up sentinel written"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: teardown: run-cleaned-up sentinel missing"
fi

write_state "$STATE" EXPECTED_SESSION_ID=wrong-session
rm -f "$SANDBOX/tmp/.run-cleaned-up"
OUT=$(run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "refusing to rm-rf" "$OUT" "teardown: sanity-check refusal path reached"
if [ -f "$SANDBOX/tmp/.run-cleaned-up" ]; then
    PASS=$((PASS + 1))
    echo "PASS: teardown: run-cleaned-up written before sanity-check refusal"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: teardown: run-cleaned-up missing on sanity-check refusal"
fi

write_state "$STATE" ISSUE_NUMBER=
rm -f "$SANDBOX/tmp/.run-cleaned-up"
chmod 0500 "$SANDBOX/tmp"
OUT=$(run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
chmod 0700 "$SANDBOX/tmp"
assert_contains "✅ 18: cleanup status=complete elapsed=<elapsed>" "$OUT" "teardown: run-cleaned-up touch failure is non-blocking"

write_state "$STATE"
OUT=$(STUB_CLEANUP_TMPDIR_RC=1 run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "**⚠ 18: cleanup-tmpdir failed. Continuing.**" "$OUT" "teardown: cleanup failure warning"
assert_contains "FINALIZE_WARNINGS=1" "$OUT" "teardown: cleanup warning counted"

write_state "$STATE"
run_subject_raw_rc teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/not-tmp"
assert_rc "$RC" 2 "teardown: state-file outside implement tmpdir exits 2"

run_subject_raw_rc teardown --state-file "$STATE" --implement-tmpdir /var/not-larch-tmp
assert_rc "$RC" 2 "teardown: implement tmpdir outside allowed roots exits 2"
assert_contains "--implement-tmpdir must be under /tmp/, /private/tmp/, /var/folders/, or the larch cache sessions root" "$OUT" "teardown: implement tmpdir diagnostic"

# Unit test: is_tmp_path accepts /var/folders/* and /private/var/folders/* patterns
_itp_func=$(sed -n '/^is_tmp_path()/,/^}/p' "$REAL_SCRIPT")
_itp_result=$(eval "$_itp_func"; is_tmp_path "/var/folders/kf/abc123/T/larch-test.tmp" && echo "ok" || echo "fail")
assert_contains "ok" "$_itp_result" "is_tmp_path: /var/folders/* accepted"
_itp_result2=$(eval "$_itp_func"; is_tmp_path "/private/var/folders/kf/abc123/T/larch-test.tmp" && echo "ok" || echo "fail")
assert_contains "ok" "$_itp_result2" "is_tmp_path: /private/var/folders/* accepted"

# Safety-net: per-section record splitting
write_state "$STATE" ISSUE_NUMBER=
printf 'RUN_ID=testrun123\n' >> "$STATE"
cat > "$SANDBOX/tmp/execution-issues.md" << 'EXEC_ISSUES'
### Q/A

- Q: Did you confirm this?
  A: Yes.

### Warnings

- Step 1: something warned
EXEC_ISSUES
rm -f "$SANDBOX/tmp/.execution-issues-flushed.sha"
rm -f "$SANDBOX/tmp/execution-issues-safety-net.ndjson"
mkdir -p "$SANDBOX/tmp/larch-logs/implement/testrun123"
: > "$SANDBOX/larch-log-argv.txt"
OUT=$(run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
RECORD_FILE="$SANDBOX/tmp/execution-issues-safety-net.ndjson"
if [ -f "$RECORD_FILE" ]; then
    RECORD_CONTENT=$(cat "$RECORD_FILE")
    assert_contains '"category":"Q/A"' "$RECORD_CONTENT" "safety-net: Q/A section gets correct category"
    assert_contains '"category":"Warnings"' "$RECORD_CONTENT" "safety-net: Warnings section gets correct category"
    assert_not_contains '"category":"Tool Failures"' "$RECORD_CONTENT" "safety-net: no hardcoded Tool Failures when sections present"
    LINE_COUNT=$(wc -l < "$RECORD_FILE" | tr -d ' ')
    if [ "$LINE_COUNT" -ge 2 ]; then
        PASS=$((PASS + 1))
        echo "PASS: safety-net: multi-section file produces multiple records"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: safety-net: expected multiple records, got $LINE_COUNT lines"
    fi
else
    FAIL=$((FAIL + 1))
    echo "FAIL: safety-net: record file not created for multi-section execution-issues.md"
fi

# Safety-net: no-header file falls back to Tool Failures
write_state "$STATE" ISSUE_NUMBER=
printf 'RUN_ID=testrun123\n' >> "$STATE"
printf '- something went wrong\n' > "$SANDBOX/tmp/execution-issues.md"
rm -f "$SANDBOX/tmp/.execution-issues-flushed.sha"
rm -f "$SANDBOX/tmp/execution-issues-safety-net.ndjson"
OUT=$(run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
RECORD_FILE="$SANDBOX/tmp/execution-issues-safety-net.ndjson"
if [ -f "$RECORD_FILE" ]; then
    RECORD_CONTENT=$(cat "$RECORD_FILE")
    assert_contains '"category":"Tool Failures"' "$RECORD_CONTENT" "safety-net: no-header file uses Tool Failures fallback"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: safety-net: record file not created for no-header execution-issues.md"
fi

# Safety-net dedup: sentinel match -> skip flush
write_state "$STATE" ISSUE_NUMBER=
printf 'RUN_ID=testrun123\n' >> "$STATE"
DEDUP_CONTENT="- sentinel dedup test"
printf '%s\n' "$DEDUP_CONTENT" > "$SANDBOX/tmp/execution-issues.md"
DEDUP_SHA=$(sha256sum "$SANDBOX/tmp/execution-issues.md" 2>/dev/null | awk '{print $1}' || \
            shasum -a 256 "$SANDBOX/tmp/execution-issues.md" 2>/dev/null | awk '{print $1}' || true)
printf '%s\n' "$DEDUP_SHA" > "$SANDBOX/tmp/.execution-issues-flushed.sha"
rm -f "$SANDBOX/tmp/execution-issues-safety-net.ndjson"
: > "$SANDBOX/larch-log-argv.txt"
run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp" > /dev/null
if [ ! -f "$SANDBOX/tmp/execution-issues-safety-net.ndjson" ]; then
    PASS=$((PASS + 1))
    echo "PASS: safety-net dedup: sentinel match skips flush"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: safety-net dedup: sentinel match should have skipped flush"
fi
rm -f "$SANDBOX/tmp/.execution-issues-flushed.sha"

# Safety-net dedup: source_sha256 field in batch -> skip flush
write_state "$STATE" ISSUE_NUMBER=
printf 'RUN_ID=testrun123\n' >> "$STATE"
printf '%s\n' "$DEDUP_CONTENT" > "$SANDBOX/tmp/execution-issues.md"
rm -f "$SANDBOX/tmp/.execution-issues-flushed.sha"
rm -f "$SANDBOX/tmp/execution-issues-safety-net.ndjson"
printf '{"phase":"implement","step":"11","category":"Warnings","source_sha256":"%s","body":"- sentinel dedup test\n"}\n' "$DEDUP_SHA" \
    > "$SANDBOX/tmp/larch-logs/implement/testrun123/execution-issues.ndjson"
: > "$SANDBOX/larch-log-argv.txt"
run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp" > /dev/null
if [ ! -f "$SANDBOX/tmp/execution-issues-safety-net.ndjson" ]; then
    PASS=$((PASS + 1))
    echo "PASS: safety-net dedup: source_sha256 field match skips flush"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: safety-net dedup: source_sha256 field match should have skipped flush"
fi

# Safety-net dedup: bare sha in body (no source_sha256 field) -> does NOT skip flush
write_state "$STATE" ISSUE_NUMBER=
printf 'RUN_ID=testrun123\n' >> "$STATE"
printf '%s\n' "$DEDUP_CONTENT" > "$SANDBOX/tmp/execution-issues.md"
rm -f "$SANDBOX/tmp/.execution-issues-flushed.sha"
rm -f "$SANDBOX/tmp/execution-issues-safety-net.ndjson"
# Record has the sha in the body text but NOT as source_sha256 field (like a Step 2 Q/A record)
printf '{"phase":"implement","step":"2","category":"Q/A","body":"%s"}\n' "$DEDUP_SHA" \
    > "$SANDBOX/tmp/larch-logs/implement/testrun123/execution-issues.ndjson"
: > "$SANDBOX/larch-log-argv.txt"
run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp" > /dev/null
if [ -f "$SANDBOX/tmp/execution-issues-safety-net.ndjson" ]; then
    PASS=$((PASS + 1))
    echo "PASS: safety-net dedup: bare sha in body (no source_sha256) does not skip flush"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: safety-net dedup: bare sha in body should not have skipped flush (old grep was wrong)"
fi
rm -f "$SANDBOX/tmp/larch-logs/implement/testrun123/execution-issues.ndjson"

printf 'BRANCH_NAME: bad\n' > "$STATE"
run_subject_raw_rc postmerge --state-file "$STATE" --final-bail-reason-file "$BAIL"
assert_rc "$RC" 2 "state parsing: malformed line exits 2"
assert_contains "malformed state-file line 1" "$OUT" "state parsing: malformed line diagnostic"

write_state "$STATE"
grep -v '^MERGE=' "$STATE" > "$STATE.no-merge"
mv "$STATE.no-merge" "$STATE"
run_subject_raw_rc postmerge --state-file "$STATE" --final-bail-reason-file "$BAIL"
assert_rc "$RC" 2 "state parsing: missing key exits 2"
assert_contains "state-file missing required key: MERGE" "$OUT" "state parsing: missing key diagnostic"

INJECTED="$SANDBOX/injected"
write_state "$STATE" "PR_TITLE=\$(touch $INJECTED)"
OUT=$(run_subject postmerge --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "LOCAL_CLEANUP_STATUS=success" "$OUT" "state parsing: injection-shaped value accepted as data"
if [ ! -e "$INJECTED" ]; then
    PASS=$((PASS + 1))
    echo "PASS: state parsing: injection value was not executed"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: state parsing: injection side effect exists"
fi

POSTBUMP_STATE="$SANDBOX/tmp/postbump-state.sh"
cp "$SANDBOX/original-CHANGELOG.md" "$SANDBOX/repo/CHANGELOG.md"
: > "$SANDBOX/tmp/execution-issues.md"
rm -f "$SANDBOX/tmp/.postbump-phase" "$SANDBOX/ledger-calls.txt"
write_postbump_state "$POSTBUMP_STATE"
OUT=$(run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "✅ 8: larch-log status=complete elapsed=<elapsed>" "$OUT" "postbump: larch-log compact breadcrumb"
assert_contains "✅ 8a: changelog status=complete to=v17.0.4 elapsed=<elapsed>" "$OUT" "postbump: changelog compact success breadcrumb"
assert_contains "✅ 8b: rebase status=complete outcome=rebased elapsed=<elapsed>" "$OUT" "postbump: rebase compact success breadcrumb"
assert_contains "✅ 8b: rebase status=complete outcome=force-pushed elapsed=<elapsed>" "$OUT" "postbump: force-push compact success breadcrumb"
assert_not_contains " — " "$OUT" "postbump: happy path avoids prose breadcrumb separator"
assert_contains "LOG_WRITE_STATUS=ok" "$OUT" "postbump: happy path writes larch-log batch"
assert_contains "CHANGELOG_STATUS=updated" "$OUT" "postbump: happy path updates changelog"
assert_contains "REBASE_STATUS=rebased" "$OUT" "postbump: happy path rebases"
assert_contains "FORCE_PUSH_STATUS=pushed" "$OUT" "postbump: happy path force-pushes"
assert_contains "STATUS=ok" "$OUT" "postbump: happy path status ok"
assert_file_contains "Step 8a — changelog" "$SANDBOX/ledger-calls.txt" "postbump: emits Step 8a ledger mark"
assert_file_contains "Step 8b — rebase" "$SANDBOX/ledger-calls.txt" "postbump: emits Step 8b ledger mark"
assert_file_contains "write" "$SANDBOX/larch-log-argv.txt" "postbump: larch-log write verb"
assert_file_contains "--skill" "$SANDBOX/larch-log-argv.txt" "postbump: larch-log passes skill"
assert_file_contains "implement" "$SANDBOX/larch-log-argv.txt" "postbump: larch-log skill is implement"
assert_file_contains "--batch" "$SANDBOX/larch-log-argv.txt" "postbump: larch-log passes batch"
assert_file_contains "version-bump-reasoning" "$SANDBOX/larch-log-argv.txt" "postbump: larch-log writes version-bump-reasoning"
assert_file_contains "## [17.0.4] -" "$SANDBOX/repo/CHANGELOG.md" "postbump: changelog contains new version"
assert_file_contains "### Changed" "$SANDBOX/repo/CHANGELOG.md" "postbump: flat bullets default to Changed"
awk 'prev_blank && /^$/ { print "DOUBLE_BLANK"; exit } /^$/ { prev_blank=1; next } { prev_blank=0 }' \
    "$SANDBOX/repo/CHANGELOG.md" > "$SANDBOX/blank-check.txt"
assert_file_not_contains "DOUBLE_BLANK" "$SANDBOX/blank-check.txt" "postbump: changelog has no consecutive blank lines"

# Double-blank-line regression: a reasoning file with consecutive blank lines
# must produce a batch input file with no consecutive blank lines (MD012 guard).
db_reasoning="$SANDBOX/tmp/larch-log-batches-input/bump-version-reasoning-double-blank.md"
printf '# Version Bump Reasoning\n\nPATCH\n\n\nExtra blank above.\n' > "$db_reasoning"
rm -f "$SANDBOX/tmp/larch-log-batches/version-bump-reasoning.md"
cp "$SANDBOX/original-CHANGELOG.md" "$SANDBOX/repo/CHANGELOG.md"
: > "$SANDBOX/tmp/execution-issues.md"
rm -f "$SANDBOX/tmp/.postbump-phase" "$SANDBOX/ledger-calls.txt"
write_postbump_state "$POSTBUMP_STATE" "BUMP_REASONING_FILE=$db_reasoning"
OUT=$(run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "LOG_WRITE_STATUS=ok" "$OUT" "postbump: double-blank reasoning writes larch-log batch"
awk 'prev_blank && /^$/ { print "DOUBLE_BLANK"; exit } /^$/ { prev_blank=1; next } { prev_blank=0 }' \
    "$SANDBOX/tmp/larch-log-batches/version-bump-reasoning.md" > "$SANDBOX/blank-check-reasoning.txt"
assert_file_not_contains "DOUBLE_BLANK" "$SANDBOX/blank-check-reasoning.txt" \
    "postbump: version-bump-reasoning.md batch input has no consecutive blank lines"

# FINDING_1 regression: Unreleased section bullets must be preserved, not consumed.
cat > "$SANDBOX/repo/CHANGELOG.md" <<'CHANGELOG_UNRELEASED'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- pending feature one
- pending feature two

## [17.0.3] - 2026-05-01

### Changed

- Prior change.
CHANGELOG_UNRELEASED
write_postbump_state "$POSTBUMP_STATE"
OUT=$(run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "CHANGELOG_STATUS=updated" "$OUT" "postbump: Unreleased preserved happy path"
assert_file_contains "pending feature one" "$SANDBOX/repo/CHANGELOG.md" "postbump: Unreleased bullets preserved"
assert_file_contains "pending feature two" "$SANDBOX/repo/CHANGELOG.md" "postbump: all Unreleased bullets preserved"
# Ensure the new release entry comes AFTER the Unreleased body, not before.
awk '
    /^## \[Unreleased\]/ { in_unrel=1; next }
    in_unrel && /^## \[17\.0\.4\] -/ { print "ORDER_OK"; exit }
    in_unrel && /^## \[/ && !/^## \[17\.0\.4\] -/ { print "ORDER_BAD"; exit }
' "$SANDBOX/repo/CHANGELOG.md" > "$SANDBOX/order-check.txt"
assert_file_contains "ORDER_OK" "$SANDBOX/order-check.txt" "postbump: new entry inserted after Unreleased section body"

# FINDING_5 regression: duplicate target-version headers must be rejected (fail closed).
cat > "$SANDBOX/repo/CHANGELOG.md" <<'CHANGELOG_DUP'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [17.0.4] - 2026-05-01

### Fixed

- pre-existing duplicate.

## [17.0.4] - 2026-04-30

### Added

- second pre-existing duplicate.

## [17.0.3] - 2026-04-29

### Changed

- Prior change.
CHANGELOG_DUP
write_postbump_state "$POSTBUMP_STATE"
OUT=$(run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "CHANGELOG_STATUS=failed" "$OUT" "postbump: duplicate target headers fail closed"
assert_contains "STATUS=changelog-failed" "$OUT" "postbump: duplicate target headers route to changelog-failed"
assert_file_contains "multiple existing" "$SANDBOX/tmp/execution-issues.md" "postbump: duplicate-header warning logged"

cp "$SANDBOX/original-CHANGELOG.md" "$SANDBOX/repo/CHANGELOG.md"
printf '{"summary_bullets_categorized":{"Added":["new flow"],"Fixed":["resume bug"],"Security":["guard paths"]}}\n' > "$SANDBOX/tmp/manifest.json"
write_postbump_state "$POSTBUMP_STATE"
OUT=$(STUB_REMOTE_STATE=absent run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "FORCE_PUSH_STATUS=absent" "$OUT" "postbump: absent remote skips force-push"
assert_file_contains "### Added" "$SANDBOX/repo/CHANGELOG.md" "postbump: categorized manifest writes Added"
assert_file_contains "### Fixed" "$SANDBOX/repo/CHANGELOG.md" "postbump: categorized manifest writes Fixed"
assert_file_contains "### Security" "$SANDBOX/repo/CHANGELOG.md" "postbump: categorized manifest writes Security"

cp "$SANDBOX/original-CHANGELOG.md" "$SANDBOX/repo/CHANGELOG.md"
printf 'Fixed\tone\nAdded\ttwo\nthree\n' > "$SANDBOX/tmp/changelog-bullets.txt"
write_postbump_state "$POSTBUMP_STATE" MANIFEST_PATH=
OUT=$(run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp" --changelog-bullets-file "$SANDBOX/tmp/changelog-bullets.txt")
assert_contains "CHANGELOG_STATUS=updated" "$OUT" "postbump: Claude fallback bullets update changelog"
assert_file_contains "### Fixed" "$SANDBOX/repo/CHANGELOG.md" "postbump: fallback categorized Fixed"
assert_file_contains "### Added" "$SANDBOX/repo/CHANGELOG.md" "postbump: fallback categorized Added"
assert_file_contains "### Changed" "$SANDBOX/repo/CHANGELOG.md" "postbump: fallback bare bullet defaults Changed"

# Regression: when target version header already exists (replacement path), no double blank before next header.
cat > "$SANDBOX/repo/CHANGELOG.md" <<'CHANGELOG_REPLACE'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [17.0.4] - 2026-05-01

### Fixed

- old content to be replaced.

## [17.0.3] - 2026-04-30

### Changed

- Prior change.
CHANGELOG_REPLACE
write_postbump_state "$POSTBUMP_STATE"
OUT=$(run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "CHANGELOG_STATUS=updated" "$OUT" "postbump: replacement path updates changelog"
awk 'prev_blank && /^$/ { print "DOUBLE_BLANK"; exit } /^$/ { prev_blank=1; next } { prev_blank=0 }' \
    "$SANDBOX/repo/CHANGELOG.md" > "$SANDBOX/blank-check-replace.txt"
assert_file_not_contains "DOUBLE_BLANK" "$SANDBOX/blank-check-replace.txt" "postbump: replacement path has no consecutive blank lines"

cp "$SANDBOX/original-CHANGELOG.md" "$SANDBOX/repo/CHANGELOG.md"
write_postbump_state "$POSTBUMP_STATE"
OUT=$(STUB_CHANGELOG_PRESENT=false run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "⏩ 8a: changelog status=skip reason=changelog-absent elapsed=<elapsed>" "$OUT" "postbump: absent changelog compact skip breadcrumb"
assert_contains "CHANGELOG_STATUS=skipped-absent" "$OUT" "postbump: absent changelog status"

cp "$SANDBOX/original-CHANGELOG.md" "$SANDBOX/repo/CHANGELOG.md"
write_postbump_state "$POSTBUMP_STATE" BUMP_TYPE=NONE
OUT=$(run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "⏩ 8a: changelog status=skip reason=no-bump-commit elapsed=<elapsed>" "$OUT" "postbump: no-bump compact skip breadcrumb"
assert_contains "CHANGELOG_STATUS=skipped-no-bump" "$OUT" "postbump: BUMP_TYPE=NONE skips changelog"
assert_contains "REBASE_STATUS=rebased" "$OUT" "postbump: BUMP_TYPE=NONE still rebases"

write_postbump_state "$POSTBUMP_STATE" FORKED_TARGET=true REPO_UNAVAILABLE=true
OUT=$(run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "⏩ 8a: changelog status=skip reason=forked-dry-run elapsed=<elapsed>" "$OUT" "postbump: forked compact skip breadcrumb"
assert_contains "⏭️ 8b: rebase status=bypass reason=repo-unavailable elapsed=<elapsed>" "$OUT" "postbump: repo-unavailable compact bypass breadcrumb"
assert_contains "CHANGELOG_STATUS=skipped-fork" "$OUT" "postbump: forked target skips changelog"
assert_contains "FORCE_PUSH_STATUS=skipped-repo-unavailable" "$OUT" "postbump: repo-unavailable skips force-push"
assert_file_contains "--base-remote" "$SANDBOX/rebase-argv.txt" "postbump: forked target rebases against upstream"

write_postbump_state "$POSTBUMP_STATE"
rm -f "$SANDBOX/tmp/.postbump-phase"
OUT=$(STUB_REBASE_RC=1 run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "STATUS=conflict" "$OUT" "postbump: rebase conflict emits conflict status"
assert_contains "RESUME_PHASE=force-push-gate" "$OUT" "postbump: conflict emits informational resume phase"
assert_file_contains "force-push-gate" "$SANDBOX/tmp/.postbump-phase" "postbump: conflict writes checkpoint"

write_postbump_state "$POSTBUMP_STATE"
printf 'force-push-gate\n' > "$SANDBOX/tmp/.postbump-phase"
OUT=$(run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "CHANGELOG_STATUS=skipped-resume" "$OUT" "postbump: checkpoint skips changelog"
assert_contains "REBASE_STATUS=skipped-resume" "$OUT" "postbump: checkpoint skips rebase"
assert_contains "FORCE_PUSH_STATUS=pushed" "$OUT" "postbump: checkpoint runs force-push"
if [ ! -e "$SANDBOX/tmp/.postbump-phase" ]; then
    PASS=$((PASS + 1))
    echo "PASS: postbump: successful force-push clears checkpoint"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: postbump: checkpoint should be cleared"
fi

write_postbump_state "$POSTBUMP_STATE"
printf 'bogus-phase\n' > "$SANDBOX/tmp/.postbump-phase"
OUT=$(run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "STATUS=postbump-state-corrupt" "$OUT" "postbump: corrupt checkpoint fails closed"

write_postbump_state "$POSTBUMP_STATE"
rm -f "$SANDBOX/tmp/.postbump-phase"
ln -s /etc/passwd "$SANDBOX/tmp/.postbump-phase"
OUT=$(run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "STATUS=postbump-state-corrupt" "$OUT" "postbump: symlink checkpoint rejected"
rm -f "$SANDBOX/tmp/.postbump-phase"

write_postbump_state "$POSTBUMP_STATE"
OUT=$(STUB_REMOTE_STATE=error run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "STATUS=remote-check-failed" "$OUT" "postbump: remote check error fails closed"

write_postbump_state "$POSTBUMP_STATE"
OUT=$(STUB_FORCE_PUSH_STATUS=diverged_retry_failed run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "STATUS=push-failed" "$OUT" "postbump: force-push lease failure bails"
assert_contains "FORCE_PUSH_STATUS=failed" "$OUT" "postbump: force-push failure status"

cp "$SANDBOX/original-CHANGELOG.md" "$SANDBOX/repo/CHANGELOG.md"
write_postbump_state "$POSTBUMP_STATE"
OUT=$(STUB_AMEND_FAIL=true run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "STATUS=changelog-failed" "$OUT" "postbump: changelog amend failure is fatal"

write_postbump_state "$POSTBUMP_STATE" BRANCH_NAME=main
run_subject_raw_rc postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp"
assert_rc "$RC" 2 "postbump: main branch rejected"

write_postbump_state "$POSTBUMP_STATE" HAS_BUMP=yes
run_subject_raw_rc postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp"
assert_rc "$RC" 2 "postbump: invalid boolean rejected"

write_postbump_state "$POSTBUMP_STATE" BUMP_TYPE=PATCHX
run_subject_raw_rc postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp"
assert_rc "$RC" 2 "postbump: invalid bump type rejected"

write_postbump_state "$POSTBUMP_STATE" NEW_VERSION=17.0
run_subject_raw_rc postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp"
assert_rc "$RC" 2 "postbump: invalid semver rejected"

write_postbump_state "$POSTBUMP_STATE" BRANCH_NAME=feature/other
OUT=$(STUB_CURRENT_BRANCH=feature/finalize run_subject postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "STATUS=branch-mismatch" "$OUT" "postbump: branch mismatch emits branch-mismatch"

write_postbump_state "$POSTBUMP_STATE"
run_subject_raw_rc postbump --state-file "$POSTBUMP_STATE" --implement-tmpdir "$SANDBOX/tmp" --resume-from force-push-gate
assert_rc "$RC" 2 "postbump: --resume-from flag rejected"

run_subject_raw_rc postmerge --state-file "$STATE" --final-bail-reason-file "$BAIL" --resume-from force-push-gate
assert_rc "$RC" 2 "postmerge: postbump flag rejected by common parser"

if grep -qF "skip directly to Step 8b" "$SCRIPT_DIR/../skills/implement/SKILL.md"; then
    FAIL=$((FAIL + 1))
    echo "FAIL: postbump: SKILL.md still contains legacy 'skip directly to Step 8b' phrase"
else
    PASS=$((PASS + 1))
    echo "PASS: postbump: SKILL.md legacy skip phrase absent"
fi

# Regression: teardown passes an explicit larch-log root even when
# implement-finalize.sh is invoked from a fresh shell without IMPLEMENT_TMPDIR.
rm -f "$SANDBOX/larch-log-env.txt"
rm -f "$SANDBOX/larch-log-argv.txt"
write_state "$STATE" PR_NUMBER=99 EXPECTED_SESSION_ID=session-123 EXPECTED_TMPDIR_BASENAME_PREFIX=tmp
printf 'RUN_ID=test-run-export\n' >> "$STATE"
(cd "$SANDBOX/repo" && unset IMPLEMENT_TMPDIR && PATH="$SANDBOX/bin:$PATH" \
    "$SANDBOX/scripts/implement-finalize.sh" teardown \
    --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp" 2>&1) | normalize_elapsed > /dev/null || true
if [ -f "$SANDBOX/larch-log-argv.txt" ]; then
    if grep -qF -- "--log-root" "$SANDBOX/larch-log-argv.txt" && grep -qF "$SANDBOX/tmp/larch-logs" "$SANDBOX/larch-log-argv.txt"; then
        PASS=$((PASS + 1))
        echo "PASS: teardown: explicit --log-root passed to larch-log.sh (fresh shell)"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: teardown: explicit --log-root missing; got: $(cat "$SANDBOX/larch-log-argv.txt")"
    fi
else
    FAIL=$((FAIL + 1))
    echo "FAIL: teardown: larch-log.sh stub not called (no argv record)"
fi

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
