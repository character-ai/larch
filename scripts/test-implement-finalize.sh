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
    sed -E 's/\([0-9]+s\)/(<elapsed>)/g'
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
        printf 'SLACK_ENABLED=%s\n' "$(override_value SLACK_ENABLED true "$@")"
        printf 'SLACK_AVAILABLE=%s\n' "$(override_value SLACK_AVAILABLE true "$@")"
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

build_sandbox() {
    SANDBOX=$(mktemp -d /tmp/larch-finalize-test.XXXXXX)
    mkdir -p "$SANDBOX/scripts" "$SANDBOX/tmp" "$SANDBOX/bin" "$SANDBOX/repo/.git"
    printf 'session-123\n' > "$SANDBOX/tmp/session-id"
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
    cat > "$SANDBOX/scripts/post-issue-slack.sh" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$@" > "$SANDBOX/slack-argv.txt"
echo "SLACK_TS=\${STUB_SLACK_TS:-1700000000.000000}"
exit "\${STUB_SLACK_RC:-0}"
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
    cat > "$SANDBOX/bin/git" <<STUB
#!/usr/bin/env bash
if [ "\${1:-}" = "-C" ]; then
  shift 2
fi
case "\${1:-} \${2:-} \${3:-}" in
  "rev-parse --show-toplevel ")
    echo "\${STUB_REPO_ROOT:-$SANDBOX/repo}"
    ;;
  "rev-parse --git-dir ")
    echo "\${STUB_GIT_DIR:-$SANDBOX/repo/.git}"
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
    chmod +x "$SANDBOX/bin/git" "$SANDBOX/bin/gh"
}

run_subject() {
    PATH="$SANDBOX/bin:$PATH" "$SANDBOX/scripts/implement-finalize.sh" "$@" 2>&1 | normalize_elapsed
}

run_subject_raw_rc() {
    set +e
    OUT=$(PATH="$SANDBOX/bin:$PATH" "$SANDBOX/scripts/implement-finalize.sh" "$@" 2>&1 | normalize_elapsed)
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
assert_contains "⏭️ 14: local cleanup — skipped (--draft set, staying on feature/finalize for further iteration) (<elapsed>)" "$OUT" "postmerge: draft skip breadcrumb"
assert_contains "LOCAL_CLEANUP_STATUS=skipped-draft" "$OUT" "postmerge: draft status"
assert_contains "VERIFY_MAIN_STATUS=skipped" "$OUT" "postmerge: draft skips verify"

write_state "$STATE" MERGE=false
OUT=$(run_subject postmerge --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "⏭️ 14: local cleanup — skipped (--merge not set), still on feature/finalize (<elapsed>)" "$OUT" "postmerge: merge=false skip"
assert_contains "LOCAL_CLEANUP_STATUS=skipped-merge-false" "$OUT" "postmerge: merge=false status"

printf 'merge blocked\n' > "$BAIL"
write_state "$STATE"
OUT=$(run_subject postmerge --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "**⚠ 14: local cleanup — skipped (PR not merged), still on feature/finalize (<elapsed>)**" "$OUT" "postmerge: bail skip warning"
assert_contains "FINALIZE_WARNINGS=1" "$OUT" "postmerge: bail warning counted"
: > "$BAIL"

write_state "$STATE"
OUT=$(run_subject postmerge --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "✅ 14: local cleanup — switched to main, deleted feature/finalize (<elapsed>)" "$OUT" "postmerge: cleanup success"
assert_contains "✅ 15: verify main — at abc1234 \"Implement finalizer (#123)\" (<elapsed>)" "$OUT" "postmerge: verify success"
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

write_state "$STATE" SLACK_ENABLED=false PR_CLOSED=true
OUT=$(run_subject slack --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "⏭️ 16a: slack issue post — skipped (--slack not set) (<elapsed>)" "$OUT" "slack: --slack-not-set skip"
assert_contains "RUN_OUTCOME=closed" "$OUT" "slack: closed outcome emitted on skip"

write_state "$STATE" SLACK_ENABLED=false DESIGN_ONLY_DONE=true
OUT=$(run_subject slack --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "RUN_OUTCOME=design-only" "$OUT" "slack: design-only outcome"

write_state "$STATE" SLACK_ENABLED=false BAIL_NEEDS_USER_INPUT=true
OUT=$(run_subject slack --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "RUN_OUTCOME=user-input" "$OUT" "slack: user-input outcome"

printf 'blocked reason' > "$BAIL"
write_state "$STATE" SLACK_ENABLED=false
OUT=$(run_subject slack --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "RUN_OUTCOME=blocked" "$OUT" "slack: blocked outcome"
: > "$BAIL"

write_state "$STATE" SLACK_ENABLED=false MERGE=false
OUT=$(run_subject slack --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "RUN_OUTCOME=pr-opened" "$OUT" "slack: merge=false maps to pr-opened"

write_state "$STATE" SLACK_ENABLED=false DRAFT=true
OUT=$(run_subject slack --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "RUN_OUTCOME=pr-opened" "$OUT" "slack: draft maps to pr-opened"

write_state "$STATE"
OUT=$(run_subject slack --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "✅ 16a: slack issue post — posted (<elapsed>)" "$OUT" "slack: posts when eligible"
assert_contains "SLACK_TS=1700000000.000000" "$OUT" "slack: timestamp forwarded"

write_state "$STATE" DESIGN_ONLY_DONE=true
OUT=$(run_subject slack --state-file "$STATE" --final-bail-reason-file "$BAIL")
SLACK_ARGV=$(cat "$SANDBOX/slack-argv.txt")
assert_contains "--status" "$SLACK_ARGV" "slack: argv recorded"
assert_not_contains "--pr-url" "$SLACK_ARGV" "slack: design-only omits pr-url"
assert_contains "RUN_OUTCOME=design-only" "$OUT" "slack: design-only post outcome"

printf 'line one\nline two\n' > "$BAIL"
write_state "$STATE"
OUT=$(run_subject slack --state-file "$STATE" --final-bail-reason-file "$BAIL")
SLACK_ARGV=$(cat "$SANDBOX/slack-argv.txt")
assert_contains "--detail" "$SLACK_ARGV" "slack: blocked detail flag"
assert_contains "line one line two " "$SLACK_ARGV" "slack: blocked detail normalized"
assert_contains "RUN_OUTCOME=blocked" "$OUT" "slack: blocked detail outcome"
: > "$BAIL"

write_state "$STATE"
OUT=$(STUB_SLACK_TS='' STUB_SLACK_RC=1 run_subject slack --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "**⚠ 16a: slack issue post — failed. Continuing.**" "$OUT" "slack: failure warning"
assert_contains "FINALIZE_WARNINGS=1" "$OUT" "slack: failure warning counted"

write_state "$STATE" ISSUE_NUMBER=
OUT=$(run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "RENAME_BRANCH=skipped" "$OUT" "teardown: empty issue skips rename"
assert_contains "RENAME_STATUS=skipped" "$OUT" "teardown: empty issue skipped status"

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
assert_contains "✅ 18: cleanup — implement complete! (<elapsed>)" "$OUT" "teardown: final breadcrumb"
assert_contains "ISSUE_URL=https://github.example/owner/repo/issues/456" "$OUT" "teardown: issue URL tail"

write_state "$STATE"
rm -f "$SANDBOX/tmp/.run-cleaned-up"
OUT=$(STUB_REQUIRE_RUN_CLEANED_UP=true run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "✅ 18: cleanup — implement complete! (<elapsed>)" "$OUT" "teardown: run-cleaned-up exists before cleanup-tmpdir"
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
assert_contains "✅ 18: cleanup — implement complete! (<elapsed>)" "$OUT" "teardown: run-cleaned-up touch failure is non-blocking"

write_state "$STATE"
OUT=$(STUB_CLEANUP_TMPDIR_RC=1 run_subject teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/tmp")
assert_contains "**⚠ 18: cleanup-tmpdir failed. Continuing.**" "$OUT" "teardown: cleanup failure warning"
assert_contains "FINALIZE_WARNINGS=1" "$OUT" "teardown: cleanup warning counted"

write_state "$STATE"
run_subject_raw_rc teardown --state-file "$STATE" --implement-tmpdir "$SANDBOX/not-tmp"
assert_rc "$RC" 2 "teardown: state-file outside implement tmpdir exits 2"

run_subject_raw_rc teardown --state-file "$STATE" --implement-tmpdir /var/not-larch-tmp
assert_rc "$RC" 2 "teardown: implement tmpdir outside /tmp exits 2"
assert_contains "--implement-tmpdir must be under /tmp/, /private/tmp/, or the larch cache sessions root" "$OUT" "teardown: implement tmpdir diagnostic"

printf 'BRANCH_NAME: bad\n' > "$STATE"
run_subject_raw_rc slack --state-file "$STATE" --final-bail-reason-file "$BAIL"
assert_rc "$RC" 2 "state parsing: malformed line exits 2"
assert_contains "malformed state-file line 1" "$OUT" "state parsing: malformed line diagnostic"

write_state "$STATE"
grep -v '^MERGE=' "$STATE" > "$STATE.no-merge"
mv "$STATE.no-merge" "$STATE"
run_subject_raw_rc slack --state-file "$STATE" --final-bail-reason-file "$BAIL"
assert_rc "$RC" 2 "state parsing: missing key exits 2"
assert_contains "state-file missing required key: MERGE" "$OUT" "state parsing: missing key diagnostic"

INJECTED="$SANDBOX/injected"
write_state "$STATE" "PR_TITLE=\$(touch $INJECTED)"
OUT=$(run_subject slack --state-file "$STATE" --final-bail-reason-file "$BAIL")
assert_contains "✅ 16a: slack issue post — posted (<elapsed>)" "$OUT" "state parsing: injection-shaped value accepted as data"
if [ ! -e "$INJECTED" ]; then
    PASS=$((PASS + 1))
    echo "PASS: state parsing: injection value was not executed"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: state parsing: injection side effect exists"
fi

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
