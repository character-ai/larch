#!/usr/bin/env bash
# test-ship-pr.sh — Offline regression tests for scripts/ship-pr.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1
# Hermetic harness: callers (e.g. Claude Code) may export LARCH_QUIET_BREADCRUMB_FD
# so breadcrumbs route to a non-stdout FD; this test suite greps captured stdout.
unset LARCH_QUIET_BREADCRUMB_FD
unset LARCH_BREADCRUMB_STREAM LARCH_DONE_SENTINEL LARCH_STATUS_FILE LARCH_QUIET_LOG_FILE LARCH_BREADCRUMBS_SURFACED_FILE

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_BASE="$(mktemp -d -t ship-pr-test.XXXXXX)"
PASS_COUNT=0
FAIL_COUNT=0

cleanup() {
    rm -rf "$TMP_BASE"
}
trap cleanup EXIT

ok() { echo "  PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "  FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

write_subject() {
    local root=$1
    mkdir -p "$root/scripts" "$root/.claude/skills/bump-version/scripts" "$root/skills/implement/scripts"
    cp "$REPO_ROOT/scripts/ship-pr.sh" "$root/scripts/ship-pr.sh"
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$root/scripts/lib-quiet.sh"
    cp "$REPO_ROOT/scripts/lib-net.sh" "$root/scripts/lib-net.sh"
    cp "$REPO_ROOT/scripts/lib-finalize-state-keys.sh" "$root/scripts/lib-finalize-state-keys.sh"
    cp "$REPO_ROOT/scripts/lib-changelog.sh" "$root/scripts/lib-changelog.sh"
    cp "$REPO_ROOT/scripts/auto-resolve-changelog.sh" "$root/scripts/auto-resolve-changelog.sh"
    cp "$REPO_ROOT/scripts/oos-disposition-shared.inc.bash" "$root/scripts/oos-disposition-shared.inc.bash"
    cp "$REPO_ROOT/scripts/redact-secrets.sh" "$root/scripts/redact-secrets.sh"
    cp "$REPO_ROOT/scripts/ci-failed-jobs.sh" "$root/scripts/ci-failed-jobs.sh"
    chmod +x "$root/scripts/redact-secrets.sh" "$root/scripts/ci-failed-jobs.sh"
    cp "$REPO_ROOT/skills/implement/scripts/oos-disposition-gate.sh" "$root/skills/implement/scripts/oos-disposition-gate.sh"
    cp "$REPO_ROOT/skills/implement/scripts/oos-non-security-block-count.awk" "$root/skills/implement/scripts/oos-non-security-block-count.awk"
    chmod +x "$root/scripts/ship-pr.sh" "$root/scripts/auto-resolve-changelog.sh" "$root/skills/implement/scripts/oos-disposition-gate.sh"
}

write_stubs() {
    local root=$1
    cat > "$root/scripts/run-relevant-checks-captured.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${STUB_CHECKS_SKIPPED:-false}" == true ]]; then
  echo "RELEVANT_CHECKS_SKIPPED=true SITE=step6"
  exit 0
fi
if [[ "${STUB_CHECKS_OK:-true}" == true ]]; then
  echo "RELEVANT_CHECKS_OK=true SITE=step6 COVERAGE=full"
  exit 0
fi
echo "STATUS=fail FAILURE_REASON=stubbed"
exit 1
SH
    cat > "$root/.claude/skills/bump-version/scripts/classify-bump.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
echo "CURRENT_VERSION=1.0.0"
echo "NEW_VERSION=1.0.1"
echo "BUMP_TYPE=PATCH"
echo "REASONING_FILE=${IMPLEMENT_TMPDIR:-/tmp}/bump-version-reasoning.md"
SH
    cat > "$root/.claude/skills/bump-version/scripts/apply-bump.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${LARCH_LOG_STUB_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$LARCH_LOG_STUB_SENTINEL_DIR"
  printf 'APPLY_BUMP_LARCH_NO_LOGS_COMMIT=%s\n' "${LARCH_NO_LOGS_COMMIT:-unset}" >> "$LARCH_LOG_STUB_SENTINEL_DIR/env-calls.txt"
fi
if [[ "${STUB_APPLY_SAME_VERSION:-false}" == true ]]; then
  echo "APPLIED=false"
  echo "ERROR=origin/main has already bumped to 1.0.1; re-classify needed"
  exit 1
fi
if [[ "${STUB_APPLY_VERSION_REGRESSION:-false}" == true ]]; then
  echo "APPLIED=false"
  echo "ERROR=version regression: 1.0.1 < origin/main 1.0.2; rebase conflict may have been resolved to branch stale version — re-resolve and re-bump"
  exit 1
fi
echo "APPLIED=true"
echo "COMMIT_SHA=abc123"
SH
    cat > "$root/scripts/check-bump-version.sh" <<'SH'
#!/usr/bin/env bash
exit 0
SH
    cat > "$root/scripts/commit-changelog.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
echo "COMMITTED=false"
exit 0
SH
    cat > "$root/scripts/implement-finalize.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  postbump)
    if [[ -n "${STUB_POSTBUMP_COUNT_FILE:-}" ]]; then
      _count=$(cat "$STUB_POSTBUMP_COUNT_FILE" 2>/dev/null || echo 0)
      printf '%s\n' "$((_count + 1))" > "$STUB_POSTBUMP_COUNT_FILE"
    fi
    case "${STUB_POSTBUMP_STATUS:-ok}" in
      conflict)
        echo "RESUME_PHASE=force-push-gate"
        echo "CALLER_KIND=step8b_rebase"
        echo "STATUS=conflict"
        ;;
      rebase-failed)
        echo "STATUS=rebase-failed"
        ;;
      *)
        echo "STATUS=ok"
        ;;
    esac
    ;;
  postmerge)
    echo "LOCAL_CLEANUP_STATUS=skipped-merge-false"
    echo "VERIFY_MAIN_STATUS=skipped"
    ;;
  teardown)
    echo "FINALIZE_SUBCOMMAND=teardown"
    ;;
esac
SH
    cat > "$root/scripts/larch-log.sh" <<'SH'
#!/usr/bin/env bash
sentinel_dir="${LARCH_LOG_STUB_SENTINEL_DIR:-/tmp}"
printf 'LARCH_LOG_ARGS=%s\n' "$*" >> "$sentinel_dir/larch-log-calls.txt"
if [[ -n "${LARCH_LOG_STUB_SENTINEL_DIR:-}" ]]; then
  printf 'larch-log %s\n' "${1:-cmd}" >> "$LARCH_LOG_STUB_SENTINEL_DIR/postmerge-order.log"
  printf 'stub_env LARCH_NO_LOGS_COMMIT=%s\n' "${LARCH_NO_LOGS_COMMIT:-}" >> "$LARCH_LOG_STUB_SENTINEL_DIR/stub-env.log"
fi
if [[ "${1:-}" == manifest && -n "${STUB_LARCH_MANIFEST_FINAL_FAIL:-}" ]]; then
  case "$*" in *status=done*) echo "stub: larch-log manifest final (status=done) failed" >&2; exit 19;; esac
fi
if [[ "${1:-}" == commit ]]; then
  if [[ -n "${IMPLEMENT_TMPDIR:-}" && -e "$IMPLEMENT_TMPDIR/post-merge-sentinel" ]]; then
    echo "stub: larch-log commit refused (post-merge sentinel present)" >&2
    exit 1
  fi
fi
exit 0
SH
    cat > "$root/skills/implement/scripts/write-final-report.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${LARCH_LOG_STUB_SENTINEL_DIR:-}" ]]; then
  printf 'write-final-report\n' >> "$LARCH_LOG_STUB_SENTINEL_DIR/postmerge-order.log"
fi
printf 'STATUS=ok\n'
SH
    cat > "$root/scripts/ci-wait.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
echo "ACTION=${STUB_CI_ACTION:-merge}"
echo "CI_STATUS=pass"
echo "BEHIND_COUNT=0"
echo "FAILED_RUN_ID=${STUB_FAILED_RUN_ID:-}"
echo "BAIL_REASON=${STUB_BAIL_REASON:-}"
echo "ITERATION=1"
echo "ELAPSED=0"
SH
    cat > "$root/scripts/merge-pr.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
echo "MERGE_RESULT=${STUB_MERGE_RESULT:-merged}"
echo "ERROR=${STUB_MERGE_ERROR:-}"
SH
    cat > "$root/scripts/gh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${STUB_GH_PR_VIEW_STATE:-}" != "" && "${1:-}" == pr && "${2:-}" == view ]]; then
  echo "$STUB_GH_PR_VIEW_STATE"
  exit 0
fi
exit "${STUB_GH_EXIT:-1}"
SH
    cat > "$root/scripts/tracking-issue-write.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
echo "RENAMED=true"
SH
    for helper in create-pr.sh gh-pr-body-update.sh rebase-push.sh ci-rerun-failed.sh gh-run-logs.sh launch-cursor-ci.sh launch-codex-ci.sh launch-claude-ci.sh append-token-record.sh git-commit.sh git-push.sh sanitize-mermaid-fragment.sh append-execution-issue.sh append-tool-failure.sh resolve-repo.sh; do
        cat > "$root/scripts/$helper" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
case "$(basename "$0")" in
  create-pr.sh)
    body_file=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --body-file) body_file="$2"; shift 2 ;;
        *) shift ;;
      esac
    done
    if [[ -n "${body_file:-}" && -f "$body_file" && -n "${IMPLEMENT_TMPDIR:-}" ]]; then
      cp "$body_file" "${IMPLEMENT_TMPDIR}/create-pr-body-capture.md"
    fi
    echo "PR_NUMBER=123"; echo "PR_URL=https://example.invalid/pr/123"; echo "PR_TITLE=Title"; echo "PR_STATUS=created" ;;
  sanitize-mermaid-fragment.sh)
    echo "STATUS=ok" ;;
  append-tool-failure.sh)
    redact=false
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --log) log=$2; shift 2 ;;
        --category) category=$2; shift 2 ;;
        --site) site=$2; shift 2 ;;
        --tool) tool=$2; shift 2 ;;
        --exit-code) exit_code=$2; shift 2 ;;
        --output-file) output_file=$2; shift 2 ;;
        --redact) redact=true; shift ;;
        *) shift ;;
      esac
    done
    mkdir -p "$(dirname "${log:-/tmp/execution-issues.md}")"
    {
      printf '### %s\n\n' "${category:-Tool Failures}"
      printf -- '- Step %s — %s failed (exit %s)\n' "${site:-unknown}" "${tool:-unknown}" "${exit_code:-unknown}"
      if [[ "${redact:-false}" == true ]]; then
        sed -E 's/sk-ant-[[:alnum:]]+/[REDACTED]/g' "${output_file:-/dev/null}" 2>/dev/null || true
      else
        cat "${output_file:-/dev/null}" 2>/dev/null || true
      fi
    } >> "${log:-/tmp/execution-issues.md}"
    echo "APPENDED=true"
    echo "LOG=${log:-}"
    ;;
  resolve-repo.sh)
    echo "REPO=owner/repo" ;;
  launch-cursor-ci.sh|launch-codex-ci.sh|launch-claude-ci.sh)
    output=""
    if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
      mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
      printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
    fi
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --output) output="$2"; shift 2 ;;
        *) shift ;;
      esac
    done
    if [[ -n "${output:-}" ]]; then
      printf 'TOKENS=1\n' > "${output}.token-record" 2>/dev/null || true
    fi
    printf 'LAUNCHER_EXIT=0\n'
    ;;
esac
SH
    done
    cat > "$root/scripts/lint-fix-loop.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
site=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --site) site="$2"; shift 2 ;;
    --checks-log) shift 2 ;;
    --tmpdir) shift 2 ;;
    *) shift ;;
  esac
done
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s\n' "${site:-unknown}" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/lint-fix-sites.txt"
fi
echo "LINT_FIX_STATUS=${STUB_LINT_FIX_STATUS:-failed}"
echo "LINT_FIX_SITE=${site:-unknown}"
if [[ -n "${STUB_LINT_FIX_FAILURE_REASON:-}" ]]; then
  echo "FAILURE_REASON=${STUB_LINT_FIX_FAILURE_REASON}"
fi
if [[ -n "${STUB_LINT_FIX_DELTA_PATHS_FILE:-}" ]]; then
  echo "LINT_FIX_DELTA_PATHS_FILE=${STUB_LINT_FIX_DELTA_PATHS_FILE}"
fi
if [[ -n "${STUB_LINT_FIX_COMMIT_SHA:-}" ]]; then
  echo "LINT_FIX_COMMIT_SHA=${STUB_LINT_FIX_COMMIT_SHA}"
fi
if [[ -n "${STUB_LINT_FIX_HEAD_CHANGED:-}" ]]; then
  echo "LINT_FIX_HEAD_CHANGED=${STUB_LINT_FIX_HEAD_CHANGED}"
fi
SH
    cat > "$root/scripts/read-session-env-key.sh" <<'SH'
#!/usr/bin/env bash
while [[ $# -gt 0 ]]; do
    [[ "$1" == --default ]] && { printf '%s\n' "$2"; exit 0; }; shift
done
SH
    cat > "$root/scripts/token-report.sh" <<'SH'
#!/usr/bin/env bash
while [[ $# -gt 0 ]]; do
    [[ "$1" == --output ]] && { touch "$2"; break; }; shift
done
SH
    cat > "$root/scripts/tracking-issue-summary.sh" <<'SH'
#!/usr/bin/env bash
touch "${IMPLEMENT_TMPDIR:-/tmp}/summary-upsert-called"
SH
    # Stub sleep to no-op so ship-pr.sh fix-attempt backoff (2/4/8/16s) does
    # not gate test wall time. ship-pr.sh resolves `sleep` via PATH, so
    # prepending $root/scripts to PATH in run_subject picks this up.
    cat > "$root/scripts/sleep" <<'SH'
#!/usr/bin/env bash
exit 0
SH
    chmod +x "$root"/scripts/*.sh "$root"/scripts/gh "$root"/scripts/sleep "$root"/.claude/skills/bump-version/scripts/*.sh "$root"/skills/implement/scripts/*.sh
}

make_repo() {
    local name=$1 root
    root="$TMP_BASE/$name"
    mkdir -p "$root"
    write_subject "$root"
    write_stubs "$root"
    git -C "$root" init -q
    git -C "$root" config user.email test@example.invalid
    git -C "$root" config user.name Test
    touch "$root/README.md"
    git -C "$root" add README.md
    git -C "$root" commit -q -m initial
    git -C "$root" checkout -q -b feature/test-issue-7
    printf '%s\n' "$root"
}

make_tmpdir() {
    mktemp -d /tmp/claude-implement-ship-pr.XXXXXX
}

write_state() {
    local file=$1 phase=$2
    local state_tmpdir
    state_tmpdir=$(dirname "$file")
    cat > "$file" <<EOF
PHASE=$phase
BRANCH_NAME=feature/test-issue-7
ISSUE_NUMBER=7
RUN_ID=test-run
REPO=owner/repo
REPO_UNAVAILABLE=false
FORKED_TARGET=false
HAS_BUMP=true
BUMP_TYPE=NONE
NEW_VERSION=
MERGE=true
DRAFT=false
DEFERRED=false
PR_CLOSED=false
DONE_RENAME_APPLIED=false
STALL_TRACKING=false
STALL_STEP=
BAIL_NEEDS_USER_INPUT=false
BAIL_REASON=
BAIL_FAILURE_DETAIL_LOG=
CI_PASSED=false
OOS_PENDING=false
PR_NUMBER=123
PR_URL=https://example.invalid/pr/123
PR_TITLE=Title
RESUME_PHASE=
CALLER_KIND=
REBASE_COUNT=0
FIX_ATTEMPTS=0
ITERATION=0
TRANSIENT_RETRIES=0
FAILED_RUN_ID=
MANIFEST_PATH=
TOOL_LABEL=claude
DESIGN_ONLY_DONE=false
NO_LOGS_COMMIT=false
IMPLEMENT_TMPDIR=$state_tmpdir
EXPECTED_SESSION_ID=
EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-test-
EOF
}

run_subject() {
    local root=$1 tmpdir=$2 rc_file=$3
    set +e
    # PATH prepend ensures stub `sleep` (no-op) and other $root/scripts/* stubs
    # are picked up by ship-pr.sh and any helpers it spawns. Without it,
    # ship-pr.sh's fix-attempt backoff (sleeps of 2/4/8/16s) makes scenarios
    # like ci_fix_exhausted take 30s+ each.
    (cd "$root" && PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" IMPLEMENT_TMPDIR="$tmpdir" "$root/scripts/ship-pr.sh" --state-file "$tmpdir/ship-pr-state.sh" --implement-tmpdir "$tmpdir" --merge true --draft false --forked false --repo owner/repo "${@:4}" > "$tmpdir/stdout" 2> "$tmpdir/stderr")
    local rc=$?
    set -e
    printf '%s' "$rc" > "$rc_file"
}

assert_state_line() {
    local file=$1 line=$2 label=$3
    if grep -qxF "$line" "$file"; then
        ok "$label"
    else
        fail "$label"
        sed 's/^/    state: /' "$file"
    fi
}

assert_rc() {
    local file=$1 expected=$2 label=$3 actual
    actual=$(cat "$file")
    if [[ "$actual" == "$expected" ]]; then
        ok "$label"
    else
        fail "$label (expected $expected, got $actual)"
    fi
}

assert_stdout_max_bytes() {
    local file=$1 max_bytes=$2 label=$3 actual
    actual=$(wc -c < "$file" | tr -d ' ')
    if [ "$actual" -le "$max_bytes" ]; then
        ok "$label"
    else
        fail "$label (expected <= $max_bytes bytes, got $actual)"
        sed 's/^/    stdout: /' "$file"
    fi
}

assert_file_absent_or_empty() {
    local file=$1 label=$2
    if [ ! -e "$file" ] || [ ! -s "$file" ]; then
        ok "$label"
    else
        fail "$label"
        sed 's/^/    file: /' "$file"
    fi
}

seed_stale_stall_state() {
    local file=$1
    awk '
      /^BAIL_REASON=/ { print "BAIL_REASON=local HEAD does not match PR head OID"; next }
      /^STALL_TRACKING=/ { print "STALL_TRACKING=true"; next }
      /^STALL_STEP=/ { print "STALL_STEP=12d"; next }
      { print }
    ' "$file" > "$file.new" \
        && mv "$file.new" "$file"
}

clear_pr_state() {
    local file=$1
    awk '
      /^PR_NUMBER=/ { print "PR_NUMBER="; next }
      /^PR_URL=/ { print "PR_URL="; next }
      /^PR_TITLE=/ { print "PR_TITLE="; next }
      { print }
    ' "$file" > "$file.new" \
        && mv "$file.new" "$file"
}

# ──────────────────────────────────────────────────────────────────────────────
# Section dispatch (closes #2349 by reducing the test-ship-pr ceiling)
#
# Scenarios are partitioned into functional sections. Each section becomes a
# separate Makefile target (test-ship-pr-state, -postmerge, -fix-loop,
# -transient, -phase14) so the CI matrix can pack them as independent harness rows.
# Running the script without --section is equivalent to running all listed
# sections sequentially (state, postmerge, fix-loop, transient, phase14;
# backward-compat for local dev).
# ──────────────────────────────────────────────────────────────────────────────
SECTION=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --section) SECTION="$2"; shift 2 ;;
        *) shift ;;
    esac
done
section_runs() {
    [[ -z "$SECTION" || "$SECTION" == "$1" ]]
}

# Helpers used by both the fix-loop and transient sections; defined at top
# scope so a single-section invocation (e.g. --section transient) still sees
# them after the fix-loop section is skipped.
_install_rebump_dep_stubs() {
    local root=$1
    for extra in drop-bump-commit.sh git-sync-local-main.sh git-force-push.sh refresh-run-logs.sh; do
        printf '#!/usr/bin/env bash\nexit 0\n' > "$root/scripts/$extra"
    done
    cat > "$root/scripts/commit-changelog.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [ -f CHANGELOG.md ]; then
  echo "COMMITTED=true"
  echo "COMMIT_SHA=stub-changelog"
else
  echo "COMMITTED=false"
fi
exit 0
STUB
    chmod +x \
        "$root/scripts/drop-bump-commit.sh" \
        "$root/scripts/git-sync-local-main.sh" \
        "$root/scripts/git-force-push.sh" \
        "$root/scripts/refresh-run-logs.sh" \
        "$root/scripts/commit-changelog.sh"
}

# Real git + real rebase-push.sh for CHANGELOG auto-resolve coverage in run_rebase_rebump.
make_repo_rebase_autoresolve_prep() {
    local name=$1 root
    root="$TMP_BASE/$name"
    mkdir -p "$root"
    write_subject "$root"
    write_stubs "$root"
    cp "$REPO_ROOT/scripts/rebase-push.sh" "$root/scripts/rebase-push.sh"
    chmod +x "$root/scripts/rebase-push.sh"
    printf '%s\n' '#!/usr/bin/env bash' 'exit 99' > "$root/scripts/cursor"
    chmod +x "$root/scripts/cursor"
    git -C "$root" init -q
    git -C "$root" config user.email test@example.invalid
    git -C "$root" config user.name Test
    mkdir -p "$root/origin.git"
    git init --bare "$root/origin.git" -q
    git -C "$root" remote add origin "$root/origin.git"
    git -C "$root" checkout -B main -q
    touch "$root/README.md"
    cat > "$root/CHANGELOG.md" <<'EOF'
# Changelog

## Unreleased

### Changed

- Base bullet

## [1.0.0]

### Fixed

- Old
EOF
    git -C "$root" add README.md CHANGELOG.md
    git -C "$root" commit -q -m base
    git -C "$root" push -q -u origin main
    git -C "$root" checkout -b feature -q
    cat > "$root/CHANGELOG.md" <<'EOF'
# Changelog

## Unreleased

### Changed

- Base bullet
- Branch bullet

## [1.0.0]

### Fixed

- Old
EOF
    git -C "$root" add CHANGELOG.md
    git -C "$root" commit -q -m feature
    git -C "$root" checkout main -q
    cat > "$root/CHANGELOG.md" <<'EOF'
# Changelog

## Unreleased

### Changed

- Base bullet
- Mainline bullet

## [1.0.0]

### Fixed

- Old
EOF
    git -C "$root" add CHANGELOG.md
    git -C "$root" commit -q -m advance-main
    git -C "$root" push -q origin main
    git -C "$root" checkout feature -q
    printf '%s\n' "$root"
}

# Same as make_repo_rebase_autoresolve_prep but CHANGELOG.rst (RST section titles + underlines).
make_repo_rebase_autoresolve_rst_prep() {
    local name=$1 root
    root="$TMP_BASE/$name"
    mkdir -p "$root"
    write_subject "$root"
    write_stubs "$root"
    cp "$REPO_ROOT/scripts/rebase-push.sh" "$root/scripts/rebase-push.sh"
    chmod +x "$root/scripts/rebase-push.sh"
    printf '%s\n' '#!/usr/bin/env bash' 'exit 99' > "$root/scripts/cursor"
    chmod +x "$root/scripts/cursor"
    git -C "$root" init -q
    git -C "$root" config user.email test@example.invalid
    git -C "$root" config user.name Test
    mkdir -p "$root/origin.git"
    git init --bare "$root/origin.git" -q
    git -C "$root" remote add origin "$root/origin.git"
    git -C "$root" checkout -B main -q
    touch "$root/README.md"
    cat > "$root/CHANGELOG.rst" <<'EOF'
Changelog
=========

Unreleased
----------

* Base bullet

1.0.0
-----

* Old
EOF
    git -C "$root" add README.md CHANGELOG.rst
    git -C "$root" commit -q -m base
    git -C "$root" push -q -u origin main
    git -C "$root" checkout -b feature -q
    cat > "$root/CHANGELOG.rst" <<'EOF'
Changelog
=========

Unreleased
----------

* Base bullet
* Branch bullet

1.0.0
-----

* Old
EOF
    git -C "$root" add CHANGELOG.rst
    git -C "$root" commit -q -m feature
    git -C "$root" checkout main -q
    cat > "$root/CHANGELOG.rst" <<'EOF'
Changelog
=========

Unreleased
----------

* Base bullet
* Mainline bullet

1.0.0
-----

* Old
EOF
    git -C "$root" add CHANGELOG.rst
    git -C "$root" commit -q -m advance-main
    git -C "$root" push -q origin main
    git -C "$root" checkout feature -q
    printf '%s\n' "$root"
}

# Bare ``CHANGELOG`` (no extension), RST-shaped bodies — exercises basename detection + rst merge.
make_repo_rebase_autoresolve_bare_changelog_prep() {
    local name=$1 root
    root="$TMP_BASE/$name"
    mkdir -p "$root"
    write_subject "$root"
    write_stubs "$root"
    cp "$REPO_ROOT/scripts/rebase-push.sh" "$root/scripts/rebase-push.sh"
    chmod +x "$root/scripts/rebase-push.sh"
    printf '%s\n' '#!/usr/bin/env bash' 'exit 99' > "$root/scripts/cursor"
    chmod +x "$root/scripts/cursor"
    git -C "$root" init -q
    git -C "$root" config user.email test@example.invalid
    git -C "$root" config user.name Test
    mkdir -p "$root/origin.git"
    git init --bare "$root/origin.git" -q
    git -C "$root" remote add origin "$root/origin.git"
    git -C "$root" checkout -B main -q
    touch "$root/README.md"
    cat > "$root/CHANGELOG" <<'EOF'
Changelog
=========

Unreleased
----------

* Base bullet

1.0.0
-----

* Old
EOF
    git -C "$root" add README.md CHANGELOG
    git -C "$root" commit -q -m base
    git -C "$root" push -q -u origin main
    git -C "$root" checkout -b feature -q
    cat > "$root/CHANGELOG" <<'EOF'
Changelog
=========

Unreleased
----------

* Base bullet
* Branch bullet

1.0.0
-----

* Old
EOF
    git -C "$root" add CHANGELOG
    git -C "$root" commit -q -m feature
    git -C "$root" checkout main -q
    cat > "$root/CHANGELOG" <<'EOF'
Changelog
=========

Unreleased
----------

* Base bullet
* Mainline bullet

1.0.0
-----

* Old
EOF
    git -C "$root" add CHANGELOG
    git -C "$root" commit -q -m advance-main
    git -C "$root" push -q origin main
    git -C "$root" checkout feature -q
    printf '%s\n' "$root"
}

# Real git + real rebase-push.sh: only ``.claude-plugin/plugin.json`` conflicts (root-relative path).
make_repo_rebase_plugin_json_prep() {
    local name=$1 root
    root="$TMP_BASE/$name"
    mkdir -p "$root"
    write_subject "$root"
    write_stubs "$root"
    cp "$REPO_ROOT/scripts/rebase-push.sh" "$root/scripts/rebase-push.sh"
    chmod +x "$root/scripts/rebase-push.sh"
    printf '%s\n' '#!/usr/bin/env bash' 'exit 99' > "$root/scripts/cursor"
    chmod +x "$root/scripts/cursor"
    git -C "$root" init -q
    git -C "$root" config user.email test@example.invalid
    git -C "$root" config user.name Test
    mkdir -p "$root/origin.git"
    git init --bare "$root/origin.git" -q
    git -C "$root" remote add origin "$root/origin.git"
    git -C "$root" checkout -B main -q
    touch "$root/README.md"
    mkdir -p "$root/.claude-plugin"
    cat > "$root/.claude-plugin/plugin.json" <<'EOF'
{"name":"ship-pr-test","version":"1.0.0"}
EOF
    git -C "$root" add README.md .claude-plugin/plugin.json
    git -C "$root" commit -q -m base
    git -C "$root" push -q -u origin main
    git -C "$root" checkout -b feature -q
    cat > "$root/.claude-plugin/plugin.json" <<'EOF'
{"name":"ship-pr-test","version":"1.0.0","side":"branch"}
EOF
    git -C "$root" add .claude-plugin/plugin.json
    git -C "$root" commit -q -m feature
    git -C "$root" checkout main -q
    cat > "$root/.claude-plugin/plugin.json" <<'EOF'
{"name":"ship-pr-test","version":"1.0.0","side":"main"}
EOF
    git -C "$root" add .claude-plugin/plugin.json
    git -C "$root" commit -q -m advance-main
    git -C "$root" push -q origin main
    git -C "$root" checkout feature -q
    printf '%s\n' "$root"
}

# CHANGELOG + second file both conflict; auto-merge leaves the second path for the vendor.
make_repo_rebase_dual_conflict_prep() {
    local name=$1 root
    root="$TMP_BASE/$name"
    mkdir -p "$root"
    write_subject "$root"
    write_stubs "$root"
    cp "$REPO_ROOT/scripts/rebase-push.sh" "$root/scripts/rebase-push.sh"
    chmod +x "$root/scripts/rebase-push.sh"
    printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$root/scripts/cursor"
    chmod +x "$root/scripts/cursor"
    git -C "$root" init -q
    git -C "$root" config user.email test@example.invalid
    git -C "$root" config user.name Test
    mkdir -p "$root/origin.git"
    git init --bare "$root/origin.git" -q
    git -C "$root" remote add origin "$root/origin.git"
    git -C "$root" checkout -B main -q
    printf 'm0\n' > "$root/other.txt"
    touch "$root/README.md"
    cat > "$root/CHANGELOG.md" <<'EOF'
# Changelog

## Unreleased

### Changed

- Base bullet

## [1.0.0]

### Fixed

- Old
EOF
    git -C "$root" add README.md CHANGELOG.md other.txt
    git -C "$root" commit -q -m base
    git -C "$root" push -q -u origin main
    git -C "$root" checkout -b feature -q
    printf 'feat-side\n' > "$root/other.txt"
    cat > "$root/CHANGELOG.md" <<'EOF'
# Changelog

## Unreleased

### Changed

- Base bullet
- Branch bullet

## [1.0.0]

### Fixed

- Old
EOF
    git -C "$root" add CHANGELOG.md other.txt
    git -C "$root" commit -q -m feature
    git -C "$root" checkout main -q
    printf 'main-side\n' > "$root/other.txt"
    cat > "$root/CHANGELOG.md" <<'EOF'
# Changelog

## Unreleased

### Changed

- Base bullet
- Mainline bullet

## [1.0.0]

### Fixed

- Old
EOF
    git -C "$root" add CHANGELOG.md other.txt
    git -C "$root" commit -q -m advance-main
    git -C "$root" push -q origin main
    git -C "$root" checkout feature -q
    printf '%s\n' "$root"
}

_make_rebase_stubs() {
    local root=$1 count_dir=$2
    _install_rebump_dep_stubs "$root"
    cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$count_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=rebase\nCI_STATUS=fail\nBEHIND_COUNT=1\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
    chmod +x "$root/scripts/ci-wait.sh"
}

if section_runs state; then
tmp_src_guard=$(make_tmpdir)
set +e
(
  cd "$REPO_ROOT" || exit 1
  # shellcheck disable=SC2030,SC2031
  export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
  bash -c 'set -euo pipefail; __ship_pr_source_witness=42; source "scripts/ship-pr.sh"; printf "WITNESS=%s\n" "${__ship_pr_source_witness:-missing}"'
) >"$tmp_src_guard/out" 2>"$tmp_src_guard/err"
src_guard_rc=$?
set -e
if [[ "$src_guard_rc" -eq 0 ]] && grep -qxF 'WITNESS=42' "$tmp_src_guard/out"; then
    ok "ship-pr.sh sources without executing main (witness preserved)"
else
    fail "ship-pr.sh must be source-safe (no main side effects on import)"
    sed 's/^/    err: /' "$tmp_src_guard/err" | head -n 20 || true
fi
rm -rf "$tmp_src_guard"

root=$(make_repo checks_fail)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
STUB_CHECKS_OK=false run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "checks failure exits 4"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=true" "checks failure marks stall"

root=$(make_repo checks_skip)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
STUB_CHECKS_SKIPPED=true run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "checks skipped stub completes ship-pr"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "checks skip does not stall"

root=$(make_repo checks_verbose_failure)
tmp=$(make_tmpdir)
cat > "$root/scripts/run-relevant-checks-captured.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "STATUS=fail FAILURE_REASON=stubbed"
i=0
while [ "$i" -lt 200 ]; do
    printf 'VERBOSE_LEAK_MARKER_%03d=%080d\n' "$i" "$i"
    i=$((i + 1))
done
exit 1
STUB
chmod +x "$root/scripts/run-relevant-checks-captured.sh"
write_state "$tmp/ship-pr-state.sh" checks
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "verbose checks failure exits 4"
assert_stdout_max_bytes "$tmp/stdout" 2048 "verbose checks failure keeps stdout under 2048 bytes"
if grep -q '^FAILURE_DETAIL_LOG=' "$tmp/stdout"; then
    ok "verbose checks failure emits diagnostic log envelope"
else
    fail "verbose checks failure emits diagnostic log envelope"
    sed 's/^/    stdout: /' "$tmp/stdout"
fi
if grep -q 'VERBOSE_LEAK_MARKER' "$tmp/stdout"; then
    fail "verbose checks failure does not replay helper output to stdout"
    sed 's/^/    stdout: /' "$tmp/stdout"
else
    ok "verbose checks failure does not replay helper output to stdout"
fi

root=$(make_repo postbump_conflict)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" bump
postbump_count_file="$tmp/postbump-count"
: > "$postbump_count_file"
STUB_POSTBUMP_STATUS=conflict STUB_POSTBUMP_COUNT_FILE="$postbump_count_file" \
    run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 5 "postbump conflict exits 5 for Rebase + Re-bump Sub-procedure handoff (#2707)"
assert_state_line "$tmp/ship-pr-state.sh" "CALLER_KIND=step8b_rebase" "postbump conflict preserves caller kind"
assert_state_line "$tmp/ship-pr-state.sh" "RESUME_PHASE=force-push-gate" "postbump conflict records resume phase for orchestrator Exit 5 handler"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "postbump conflict exit 5 does not mark stall (#2707)"
postbump_count=$(cat "$postbump_count_file" 2>/dev/null || echo 0)
if [ "$postbump_count" = "1" ]; then
    ok "postbump conflict invokes implement-finalize.sh postbump exactly once before exit 5 (#2707)"
else
    fail "postbump conflict should invoke postbump exactly once before exit 5 (got $postbump_count invocations)"
fi
if grep -qxF "PR_TITLE=Title" "$tmp/postbump-state.sh"; then
    ok "postbump conflict writes PR_TITLE into postbump state"
else
    fail "postbump conflict should write PR_TITLE into postbump state"
    sed 's/^/    state: /' "$tmp/postbump-state.sh" 2>/dev/null || true
fi

root=$(make_repo same_version)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" bump
STUB_APPLY_SAME_VERSION=true run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "same-version bump stalls after mechanical retry exhausts (exit_stall 8)"
assert_state_line "$tmp/ship-pr-state.sh" "CALLER_KIND=step8_apply_bump_same_version" "same-version writes caller kind"

root=$(make_repo version_regression)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" bump
STUB_APPLY_VERSION_REGRESSION=true run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "version-regression bump stalls after mechanical retry exhausts (exit_stall 8)"
assert_state_line "$tmp/ship-pr-state.sh" "CALLER_KIND=step8_apply_bump_same_version" "version-regression writes caller kind"

root=$(make_repo bump_branch_guard_main)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" bump
sed -i.bak 's/^BRANCH_NAME=.*/BRANCH_NAME=main/' "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "bump branch guard exits 4 when BRANCH_NAME is main"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=bump-branch-guard" "bump branch guard records STALL_STEP for main BRANCH_NAME"

root=$(make_repo bump_branch_guard_mismatch)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" bump
sed -i.bak 's/^BRANCH_NAME=.*/BRANCH_NAME=feature\/wrong-branch/' "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "bump branch guard exits 4 when current branch mismatches BRANCH_NAME"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=bump-branch-guard" "bump branch guard records STALL_STEP for branch mismatch"

root=$(make_repo bump_branch_guard_master)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" bump
sed -i.bak 's/^BRANCH_NAME=.*/BRANCH_NAME=master/' "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "bump branch guard exits 4 when BRANCH_NAME is master"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=bump-branch-guard" "bump branch guard records STALL_STEP for master BRANCH_NAME"

root=$(make_repo bump_branch_guard_aligned_nonfork)
tmp=$(make_tmpdir)
if git -C "$root" show-ref -q --verify refs/heads/main; then
    git -C "$root" checkout -q main
    _align_default=main
elif git -C "$root" show-ref -q --verify refs/heads/master; then
    git -C "$root" checkout -q master
    _align_default=master
else
    printf 'bump_branch_guard_aligned_nonfork: expected main or master ref\n' >&2
    exit 1
fi
write_state "$tmp/ship-pr-state.sh" bump
awk -v br="$_align_default" '
    /^BRANCH_NAME=/ { print "BRANCH_NAME=" br; next }
    /^FORKED_TARGET=/ { print "FORKED_TARGET=false"; next }
    { print }
' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "bump branch guard exits 4 when checkout matches main/master and FORKED_TARGET=false"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=bump-branch-guard" "aligned default-branch bump uses protected-name bump-branch-guard path"

root=$(make_repo bump_branch_guard_empty_branch)
tmp=$(make_tmpdir)
git -C "$root" checkout -q --detach
write_state "$tmp/ship-pr-state.sh" bump
sed -i.bak 's/^BRANCH_NAME=.*/BRANCH_NAME=/' "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "bump branch guard exits 4 when BRANCH_NAME empty on detached HEAD"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=bump-branch-guard" "bump branch guard records STALL_STEP for empty BRANCH_NAME"

root=$(make_repo bump_forked_main_ok)
tmp=$(make_tmpdir)
if git -C "$root" show-ref -q --verify refs/heads/main; then
    git -C "$root" checkout -q main
    _guard_default_branch=main
elif git -C "$root" show-ref -q --verify refs/heads/master; then
    git -C "$root" checkout -q master
    _guard_default_branch=master
else
    printf 'bump_forked_main_ok: expected main or master ref\n' >&2
    exit 1
fi
write_state "$tmp/ship-pr-state.sh" bump
awk -v br="$_guard_default_branch" '
    /^BRANCH_NAME=/ { print "BRANCH_NAME=" br; next }
    /^FORKED_TARGET=/ { print "FORKED_TARGET=true"; next }
    { print }
' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "forked bump allows protected default branch name when checkout matches"

root=$(make_repo bump_resume_phase_branch_guard)
tmp=$(make_tmpdir)
cat > "$root/.claude/skills/bump-version/scripts/classify-bump.sh" <<'STUB'
#!/usr/bin/env bash
printf 'classify-bump invoked before bump-branch-guard\n' >&2
exit 99
STUB
chmod +x "$root/.claude/skills/bump-version/scripts/classify-bump.sh"
if git -C "$root" show-ref -q --verify refs/heads/main; then
    git -C "$root" checkout -q main
    _resume_bump_branch=main
elif git -C "$root" show-ref -q --verify refs/heads/master; then
    git -C "$root" checkout -q master
    _resume_bump_branch=master
else
    printf 'bump_resume_phase_branch_guard: expected main or master ref\n' >&2
    exit 1
fi
write_state "$tmp/ship-pr-state.sh" bump
awk -v br="$_resume_bump_branch" '
    /^BRANCH_NAME=/ { print "BRANCH_NAME=" br; next }
    { print }
' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc" --resume-phase bump
assert_rc "$tmp/rc" 4 "--resume-phase bump re-entry runs bump-branch-guard before classify bump"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=bump-branch-guard" "resume bump records bump-branch-guard on protected default branch"

root=$(make_repo ci_initial)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-initial
STUB_CI_ACTION=merge run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "ci-initial merge path exits 0 after same-invocation continuation"
assert_state_line "$tmp/ship-pr-state.sh" "CI_PASSED=true" "ci-initial merge sets CI_PASSED"
assert_state_line "$tmp/ship-pr-state.sh" "PHASE=done" "ci-initial merge continues through ci-merge to PHASE=done"
if [ -f "$tmp/post-merge-sentinel" ]; then
    ok "ci-initial merge writes post-merge-sentinel during same-invocation continuation"
else
    fail "ci-initial merge should write post-merge-sentinel during same-invocation continuation"
fi

root=$(make_repo ci_bail)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-merge
STUB_CI_ACTION=bail STUB_BAIL_REASON=fix-attempts-exhausted run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 3 "user-input bail exits 3"
assert_state_line "$tmp/ship-pr-state.sh" "BAIL_NEEDS_USER_INPUT=true" "user-input bail marks state"

# Breadcrumb pin: phase-entry breadcrumbs appear in stdout when LARCH_QUIET_BREADCRUMBS=1.
root=$(make_repo breadcrumb_phase_entry)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
LARCH_QUIET_BREADCRUMBS=1 STUB_CI_ACTION=merge run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "breadcrumb phase-entry scenario exits 0"
for crumb in '→ ship-pr: checks' '→ ship-pr: version bump' '→ ship-pr: PR prep' '→ ship-pr: opening PR'; do
    if grep -qF "$crumb" "$tmp/stdout"; then
        ok "breadcrumb phase-entry: stdout contains '$crumb'"
    else
        fail "breadcrumb phase-entry: stdout missing '$crumb'"
        sed 's/^/    stdout: /' "$tmp/stdout"
    fi
done

# Breadcrumb pin: stall breadcrumb appears when LARCH_QUIET_BREADCRUMBS=1 and bump fails.
root=$(make_repo breadcrumb_stall)
tmp=$(make_tmpdir)
cat > "$root/.claude/skills/bump-version/scripts/classify-bump.sh" <<'STUB'
#!/usr/bin/env bash
exit 1
STUB
chmod +x "$root/.claude/skills/bump-version/scripts/classify-bump.sh"
write_state "$tmp/ship-pr-state.sh" bump
LARCH_QUIET_BREADCRUMBS=1 run_subject "$root" "$tmp" "$tmp/rc"
if grep -qF '⛔ ship-pr: stalled at step 8' "$tmp/stdout"; then
    ok "breadcrumb stall: stdout contains stall-at-step-8 breadcrumb"
else
    fail "breadcrumb stall: stdout missing '⛔ ship-pr: stalled at step 8'"
    sed 's/^/    stdout: /' "$tmp/stdout"
fi

# Breadcrumb pin: transient breadcrumb appears when LARCH_QUIET_BREADCRUMBS=1.
root=$(make_repo breadcrumb_transient)
tmp=$(make_tmpdir)
cat > "$root/scripts/create-pr.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf "fatal: unable to access 'https://github.com/owner/repo/': Connection timed out\n" >&2
printf "fatal: unable to access 'https://github.com/owner/repo/': Connection timed out\n"
exit 1
STUB
chmod +x "$root/scripts/create-pr.sh"
write_state "$tmp/ship-pr-state.sh" pr-create
LARCH_QUIET_BREADCRUMBS=1 run_subject "$root" "$tmp" "$tmp/rc"
if grep -qF '⚠ ship-pr: transient network failure' "$tmp/stdout"; then
    ok "breadcrumb transient: stdout contains transient-network breadcrumb"
else
    fail "breadcrumb transient: stdout missing '⚠ ship-pr: transient network failure'"
    sed 's/^/    stdout: /' "$tmp/stdout"
fi

# AC#12: recovery_waterfall_paths_delta_revert uses quoted paths (spaces / glob chars).
root=$(mktemp -d "$TMP_BASE/wf-rollback-sp-XXXXXX")
impl=$(mktemp -d "$TMP_BASE/wf-rollback-sp-impl-XXXXXX")
write_subject "$root"
git -C "$root" init -q
git -C "$root" config user.email test@example.invalid
git -C "$root" config user.name Test
printf 'orig\n' >"$root/my file.txt"
printf 'g\n' >"$root/x*y.txt"
git -C "$root" add "my file.txt" "x*y.txt"
git -C "$root" commit -q -m base
btr=$(mktemp "$impl/baseline-tr.XXXXXX")
bun=$(mktemp "$impl/baseline-un.XXXXXX")
: >"$btr"
: >"$bun"
printf 'dirty\n' >"$root/my file.txt"
printf 'dirty2\n' >"$root/x*y.txt"
wf_log="$impl/wf.log"
(
    cd "$root" || exit 1
    # shellcheck disable=SC2030,SC2031
    export CLAUDE_PLUGIN_ROOT="$root"
    # shellcheck disable=SC1091
    source "$root/scripts/ship-pr.sh"
    # shellcheck disable=SC2030,SC2031
    export IMPLEMENT_TMPDIR="$impl"
    recovery_waterfall_paths_delta_revert "$btr" "$bun" "$wf_log"
)
# shellcheck disable=SC2031
if grep -qxF 'orig' "$root/my file.txt" && grep -qxF 'g' "$root/x*y.txt"; then
    ok "recovery_waterfall_rollback_handles_paths_with_spaces_and_globs"
else
    fail "recovery_waterfall_rollback_handles_paths_with_spaces_and_globs"
fi

# AC#12: staged-index rollback ordering (git restore --staged before checkout).
root=$(mktemp -d "$TMP_BASE/wf-rollback-st-XXXXXX")
impl=$(mktemp -d "$TMP_BASE/wf-rollback-st-impl-XXXXXX")
write_subject "$root"
git -C "$root" init -q
git -C "$root" config user.email test@example.invalid
git -C "$root" config user.name Test
printf 'A\n' >"$root/staged.txt"
git -C "$root" add staged.txt
git -C "$root" commit -q -m base
btr=$(mktemp "$impl/b2-tr.XXXXXX")
bun=$(mktemp "$impl/b2-un.XXXXXX")
: >"$btr"
: >"$bun"
printf 'B\n' >"$root/staged.txt"
git -C "$root" add staged.txt
wf_log="$impl/wf2.log"
(
    cd "$root" || exit 1
    # shellcheck disable=SC2030,SC2031
    export CLAUDE_PLUGIN_ROOT="$root"
    # shellcheck disable=SC1091
    source "$root/scripts/ship-pr.sh"
    # shellcheck disable=SC2030,SC2031
    export IMPLEMENT_TMPDIR="$impl"
    recovery_waterfall_paths_delta_revert "$btr" "$bun" "$wf_log"
)
# shellcheck disable=SC2031
if grep -qxF 'A' "$root/staged.txt"; then
    ok "recovery_waterfall_rollback_restores_staged_changes_via_git_restore_staged"
else
    fail "recovery_waterfall_rollback_restores_staged_changes_via_git_restore_staged"
fi

# Issue #2742: argv-init cold start (no pre-existing state file).
root=$(make_repo argv_init_fresh)
tmp=$(make_tmpdir)
printf 'expected-sid\n' > "$tmp/session-id"
printf '{}\n' > "$tmp/argv-manifest.json"
run_subject "$root" "$tmp" "$tmp/rc" \
  --branch-name 'feature/test-issue-7' \
  --expected-session-id 'expected-sid' \
  --expected-tmpdir-basename-prefix 'argv-prefix-' \
  --force-init-state false \
  --issue-number 'has=equal-sign' \
  --manifest-path "$tmp/argv-manifest.json" \
  --run-id 'argv-run-xyz' \
  --tool-label 'codex' \
  --no-logs-commit true
assert_rc "$tmp/rc" 0 "argv-init fresh cold start completes happy path"
_br=$(grep '^BRANCH_NAME=' "$tmp/ship-pr-state.sh" | cut -d= -f2-)
if [ "$_br" = 'feature/test-issue-7' ]; then
    ok "argv-init fresh BRANCH_NAME"
else
    fail "argv-init fresh BRANCH_NAME (got ${_br})"
fi
_in=$(grep '^ISSUE_NUMBER=' "$tmp/ship-pr-state.sh" | cut -d= -f2-)
if [ "$_in" = 'has=equal-sign' ]; then ok "argv-init fresh ISSUE_NUMBER"; else fail "argv-init fresh ISSUE_NUMBER (got ${_in})"; fi
_rid=$(grep '^RUN_ID=' "$tmp/ship-pr-state.sh" | cut -d= -f2-)
if [ "$_rid" = 'argv-run-xyz' ]; then ok "argv-init fresh RUN_ID"; else fail "argv-init fresh RUN_ID (got ${_rid})"; fi
_mp=$(grep '^MANIFEST_PATH=' "$tmp/ship-pr-state.sh" | cut -d= -f2-)
if [ "$_mp" = "$tmp/argv-manifest.json" ]; then ok "argv-init fresh MANIFEST_PATH"; else fail "argv-init fresh MANIFEST_PATH"; fi
_tl=$(grep '^TOOL_LABEL=' "$tmp/ship-pr-state.sh" | cut -d= -f2-)
if [ "$_tl" = 'codex' ]; then ok "argv-init fresh TOOL_LABEL"; else fail "argv-init fresh TOOL_LABEL (got ${_tl})"; fi
_es=$(grep '^EXPECTED_SESSION_ID=' "$tmp/ship-pr-state.sh" | cut -d= -f2-)
if [ "$_es" = 'expected-sid' ]; then ok "argv-init fresh EXPECTED_SESSION_ID"; else fail "argv-init fresh EXPECTED_SESSION_ID (got ${_es})"; fi
_et=$(grep '^EXPECTED_TMPDIR_BASENAME_PREFIX=' "$tmp/ship-pr-state.sh" | cut -d= -f2-)
if [ "$_et" = 'argv-prefix-' ]; then ok "argv-init fresh EXPECTED_TMPDIR_BASENAME_PREFIX"; else fail "argv-init fresh EXPECTED_TMPDIR_BASENAME_PREFIX (got ${_et})"; fi
if grep -qxF 'BAIL_FAILURE_DETAIL_LOG=' "$tmp/ship-pr-state.sh"; then ok "argv-init fresh BAIL_FAILURE_DETAIL_LOG empty"; else fail "argv-init fresh BAIL_FAILURE_DETAIL_LOG missing"; fi
_nlc=$(grep '^NO_LOGS_COMMIT=' "$tmp/ship-pr-state.sh" | cut -d= -f2-)
if [ "$_nlc" = 'true' ]; then ok "argv-init fresh NO_LOGS_COMMIT"; else fail "argv-init fresh NO_LOGS_COMMIT (got ${_nlc})"; fi
_itd=$(grep '^IMPLEMENT_TMPDIR=' "$tmp/ship-pr-state.sh" | cut -d= -f2-)
if [ "$_itd" = "$tmp" ]; then ok "argv-init fresh IMPLEMENT_TMPDIR"; else fail "argv-init fresh IMPLEMENT_TMPDIR (got ${_itd})"; fi

# Issue #2742: resume ignores argv per-key flags when state already exists.
root=$(make_repo argv_init_resume_precedence)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
sed -i.bak 's/^RUN_ID=.*/RUN_ID=preserved-on-disk-run-id/' "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc" --run-id 'conflicting-argv-run-id'
assert_rc "$tmp/rc" 0 "argv-init resume precedence completes"
_rid2=$(grep '^RUN_ID=' "$tmp/ship-pr-state.sh" | cut -d= -f2-)
if [ "$_rid2" = 'preserved-on-disk-run-id' ]; then ok "argv-init resume ignores --run-id"; else fail "argv-init resume RUN_ID (got ${_rid2})"; fi

# Issue #2742: --force-init-state true rewrites state from argv.
root=$(make_repo argv_init_force_rewrite)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
sed -i.bak 's/^RUN_ID=.*/RUN_ID=preserved-on-disk-run-id/' "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc" --run-id 'overridden-by-force-run-id' --force-init-state true
assert_rc "$tmp/rc" 0 "argv-init force-init completes"
_rid3=$(grep '^RUN_ID=' "$tmp/ship-pr-state.sh" | cut -d= -f2-)
if [ "$_rid3" = 'overridden-by-force-run-id' ]; then ok "argv-init force-init rewrites RUN_ID"; else fail "argv-init force-init RUN_ID (got ${_rid3})"; fi

# Issue #2742: CR/LF rejected for each argv-init per-key flag.
root=$(make_repo argv_init_crlf)
for _flag in branch-name expected-session-id expected-tmpdir-basename-prefix issue-number manifest-path run-id tool-label; do
    tmp=$(make_tmpdir)
    _bad=$(printf 'x\ry')
    run_subject "$root" "$tmp" "$tmp/rc" --"${_flag}" "$_bad"
    assert_rc "$tmp/rc" 2 "argv-init CR/LF rejects --${_flag}"
    if grep -Fq -e "--${_flag} must not contain CR or LF" "$tmp/stderr"; then
        ok "argv-init stderr names --${_flag} for CR/LF rejection"
    else
        fail "argv-init stderr missing --${_flag} CR/LF message"
        sed 's/^/    err: /' "$tmp/stderr" | head -n 5 || true
    fi
done

fi  # end section: state

if section_runs postmerge; then
root=$(make_repo ci_watch_skip_breadcrumb)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-merge
awk '
  /^MERGE=/ { print "MERGE=false"; next }
  { print }
' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
LARCH_QUIET_BREADCRUMBS=1 run_subject "$root" "$tmp" "$tmp/rc" --resume-phase ci-merge
assert_rc "$tmp/rc" 0 "ci-watch skip path exits 0"
if grep -qF '→ ship-pr: CI watch (ci-merge)' "$tmp/stdout"; then
    fail "ci-watch skip path should not emit CI watch breadcrumb"
    sed 's/^/    stdout: /' "$tmp/stdout"
else
    ok "ci-watch skip path omits CI watch breadcrumb"
fi

root=$(make_repo version_published_pr_merged)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-merge
PATH="$root/scripts:$PATH" LARCH_QUIET_BREADCRUMBS=1 STUB_MERGE_RESULT=version_already_published STUB_GH_PR_VIEW_STATE=MERGED run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "version_already_published + merged PR exits 0"
assert_state_line "$tmp/ship-pr-state.sh" "MERGE_RESULT=already_merged" "version_already_published + merged PR records already_merged"
assert_state_line "$tmp/ship-pr-state.sh" "PHASE=done" "version_already_published + merged PR completes postmerge"
if [ -f "$tmp/post-merge-sentinel" ]; then
    ok "version_already_published + merged PR writes post-merge-sentinel"
else
    fail "version_already_published + merged PR should write post-merge-sentinel"
fi
if grep -qF '→ ship-pr: merged' "$tmp/stdout"; then
    ok "version_already_published + merged PR emits merged breadcrumb"
else
    fail "version_already_published + merged PR should emit merged breadcrumb"
    sed 's/^/    stdout: /' "$tmp/stdout"
fi

root=$(make_repo version_published_pr_open)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-version-published-open.XXXXXX)
write_state "$tmp/ship-pr-state.sh" ci-merge
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$sentinel_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
else
    printf 'ACTION=already_merged\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=2\nELAPSED=1\n'
fi
STUB
for extra in drop-bump-commit.sh git-sync-local-main.sh git-force-push.sh; do
    printf '#!/usr/bin/env bash\nexit 0\n' > "$root/scripts/$extra"
done
chmod +x "$root/scripts/ci-wait.sh" \
         "$root/scripts/drop-bump-commit.sh" \
         "$root/scripts/git-sync-local-main.sh" \
         "$root/scripts/git-force-push.sh"
PATH="$root/scripts:$PATH" LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" STUB_MERGE_RESULT=version_already_published STUB_GH_PR_VIEW_STATE=OPEN run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "version_already_published + open PR exits 0 after re-bump"
if [ "$(cat "$sentinel_dir/ci-wait-count" 2>/dev/null || echo 0)" -ge 2 ]; then
    ok "version_already_published + open PR falls through to run_rebase_rebump"
else
    fail "version_already_published + open PR should fall through to run_rebase_rebump"
fi
rm -rf "$sentinel_dir"

# Regression: stale BAIL_REASON and STALL_TRACKING from a prior stall are cleared
# when the ci-merge resume succeeds. Without the fix, write_finalize_state() would
# copy the stale BAIL_REASON into final-bail-reason.txt, causing
# implement-finalize.sh postmerge to skip local branch cleanup.
root=$(make_repo stale_stall_state_cleared_on_merge)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-merge
seed_stale_stall_state "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc" --resume-phase ci-merge
assert_rc "$tmp/rc" 0 "stale stall state: resume exits 0 after successful merge"
assert_state_line "$tmp/ship-pr-state.sh" "PHASE=done" "stale stall state: PHASE=done after resume"
assert_state_line "$tmp/ship-pr-state.sh" "BAIL_REASON=" "stale stall state: BAIL_REASON cleared on merge success"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "stale stall state: STALL_TRACKING cleared on merge success"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=" "stale stall state: STALL_STEP cleared on merge success"
assert_file_absent_or_empty "$tmp/final-bail-reason.txt" "stale stall state: final-bail-reason.txt empty after merge success"

root=$(make_repo stale_stall_state_cleared_on_version_published_merged)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-merge
seed_stale_stall_state "$tmp/ship-pr-state.sh"
PATH="$root/scripts:$PATH" STUB_MERGE_RESULT=version_already_published STUB_GH_PR_VIEW_STATE=MERGED \
    run_subject "$root" "$tmp" "$tmp/rc" --resume-phase ci-merge
assert_rc "$tmp/rc" 0 "stale stall state: version_already_published + merged PR exits 0"
assert_state_line "$tmp/ship-pr-state.sh" "MERGE_RESULT=already_merged" "stale stall state: version_already_published + merged PR records already_merged"
assert_state_line "$tmp/ship-pr-state.sh" "PHASE=done" "stale stall state: version_already_published + merged PR completes postmerge"
assert_state_line "$tmp/ship-pr-state.sh" "BAIL_REASON=" "stale stall state: version_already_published + merged PR clears BAIL_REASON"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "stale stall state: version_already_published + merged PR clears STALL_TRACKING"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=" "stale stall state: version_already_published + merged PR clears STALL_STEP"
assert_file_absent_or_empty "$tmp/final-bail-reason.txt" "stale stall state: version_already_published + merged PR leaves final-bail-reason.txt empty"

root=$(make_repo stale_stall_state_cleared_on_already_merged)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-merge
seed_stale_stall_state "$tmp/ship-pr-state.sh"
LARCH_QUIET_BREADCRUMBS=1 STUB_CI_ACTION=already_merged run_subject "$root" "$tmp" "$tmp/rc" --resume-phase ci-merge
assert_rc "$tmp/rc" 0 "stale stall state: ci-wait already_merged exits 0"
assert_state_line "$tmp/ship-pr-state.sh" "MERGE_RESULT=already_merged" "stale stall state: ci-wait already_merged records already_merged"
assert_state_line "$tmp/ship-pr-state.sh" "PHASE=done" "stale stall state: ci-wait already_merged completes postmerge"
assert_state_line "$tmp/ship-pr-state.sh" "BAIL_REASON=" "stale stall state: ci-wait already_merged clears BAIL_REASON"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "stale stall state: ci-wait already_merged clears STALL_TRACKING"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=" "stale stall state: ci-wait already_merged clears STALL_STEP"
assert_file_absent_or_empty "$tmp/final-bail-reason.txt" "stale stall state: ci-wait already_merged leaves final-bail-reason.txt empty"
if grep -qF '→ ship-pr: merged' "$tmp/stdout"; then
    ok "already_merged path emits merged breadcrumb"
else
    fail "already_merged path should emit merged breadcrumb"
    sed 's/^/    stdout: /' "$tmp/stdout"
fi

root=$(make_repo malformed)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
printf 'lowercase_bad=true\n' >> "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 2 "malformed lowercase state exits 2"

root=$(make_repo postmerge)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" postmerge
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "postmerge phase exits 0"
assert_state_line "$tmp/ship-pr-state.sh" "PHASE=done" "postmerge writes PHASE=done before teardown"
if [ -f "$tmp/summary-upsert-called" ]; then
    fail "postmerge should not call tracking-issue-summary.sh (owned by prompt-side Step 18)"
else
    ok "postmerge does not call tracking-issue-summary.sh (Step 18 owns it)"
fi

root=$(make_repo pr_create_final_summary)
tmp=$(make_tmpdir)
mkdir -p "$root/skills/implement/scripts"
cat > "$root/skills/implement/scripts/write-final-report.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
tmpdir=""
comment_only=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --implement-tmpdir) tmpdir=$2; shift 2 ;;
    --comment-only) comment_only=true; shift ;;
    *) shift ;;
  esac
done
call_count=$(grep -c '^CALL=' "$tmpdir/final-summary-write.log" 2>/dev/null || true)
printf 'CALL=%s\n' "$((call_count + 1))" >> "$tmpdir/final-summary-write.log"
awk -F= '$1=="PR_URL"{print "PR_URL_AT_WRITE=" substr($0, index($0, "=") + 1)}' "$tmpdir/ship-pr-state.sh" \
  >> "$tmpdir/final-summary-write.log"
printf 'COMMENT_ONLY=%s\n' "$comment_only" >> "$tmpdir/final-summary-write.log"
printf 'STATUS=ok\n'
STUB
chmod +x "$root/skills/implement/scripts/write-final-report.sh"
cat > "$root/scripts/git-push.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'git-push-called\n' >> "${IMPLEMENT_TMPDIR:?}/git-push-calls.log"
printf 'BRANCH=feature/test\n'
STUB
chmod +x "$root/scripts/git-push.sh"
write_state "$tmp/ship-pr-state.sh" pr-create
clear_pr_state "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "pr-create final summary refresh exits 0"
if grep -Fqx 'CALL=1' "$tmp/final-summary-write.log" && \
   grep -Fqx 'PR_URL_AT_WRITE=' "$tmp/final-summary-write.log" && \
   grep -Fqx 'COMMENT_ONLY=false' "$tmp/final-summary-write.log"; then
    ok "pr-create final summary first pass runs before PR_URL exists"
else
    fail "pr-create final summary first pass runs before PR_URL exists"
    sed 's/^/    write: /' "$tmp/final-summary-write.log" 2>/dev/null || true
fi
if grep -Fqx 'CALL=2' "$tmp/final-summary-write.log" && \
   grep -Fqx 'PR_URL_AT_WRITE=https://example.invalid/pr/123' "$tmp/final-summary-write.log" && \
   grep -Fqx 'COMMENT_ONLY=true' "$tmp/final-summary-write.log"; then
    ok "pr-create second final summary pass refreshes with persisted PR_URL"
else
    fail "pr-create second final summary pass refreshes with persisted PR_URL"
    sed 's/^/    write: /' "$tmp/final-summary-write.log" 2>/dev/null || true
fi
assert_file_absent_or_empty "$tmp/git-push-calls.log" "pr-create skips post-create push"

root=$(make_repo pr_create_precreate_final_summary_failure)
tmp=$(make_tmpdir)
mkdir -p "$root/skills/implement/scripts"
cat > "$root/skills/implement/scripts/write-final-report.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
while [[ $# -gt 0 ]]; do
  case "$1" in
    --comment-only) shift ;;
    *) shift ;;
  esac
done
printf 'write-final-report failed sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD\n' >&2
exit 17
STUB
chmod +x "$root/skills/implement/scripts/write-final-report.sh"
write_state "$tmp/ship-pr-state.sh" pr-create
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "pr-create pre-create final summary failure stalls"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=true" "pr-create pre-create final summary failure marks stall"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=9b" "pr-create pre-create final summary failure records stall step"
if grep -Fq 'write-final-report.sh failed (exit 17)' "$tmp/execution-issues.md"; then
    ok "pr-create pre-create final summary failure records execution issue"
else
    fail "pr-create pre-create final summary failure records execution issue"
    sed 's/^/    issues: /' "$tmp/execution-issues.md" 2>/dev/null || true
fi
if [ ! -f "$tmp/create-pr-calls.log" ]; then
    ok "pr-create pre-create final summary failure skips create-pr helper"
else
    fail "pr-create pre-create final summary failure should skip create-pr helper"
    sed 's/^/    create-pr: /' "$tmp/create-pr-calls.log" 2>/dev/null || true
fi

root=$(make_repo pr_create_postcreate_final_summary_failure)
tmp=$(make_tmpdir)
mkdir -p "$root/skills/implement/scripts"
cat > "$root/skills/implement/scripts/write-final-report.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
while [[ $# -gt 0 ]]; do
  case "$1" in
    --comment-only)
      printf 'write-final-report failed sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD\n' >&2
      exit 17
      ;;
    *) shift ;;
  esac
done
printf 'STATUS=ok\n'
STUB
chmod +x "$root/skills/implement/scripts/write-final-report.sh"
cat > "$root/scripts/git-push.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'git-push-called\n' >> "${IMPLEMENT_TMPDIR:?}/git-push-calls.log"
printf 'BRANCH=feature/test\n'
STUB
chmod +x "$root/scripts/git-push.sh"
write_state "$tmp/ship-pr-state.sh" pr-create
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "pr-create post-create final summary failure continues"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "pr-create post-create final summary failure does not mark stall"
assert_file_absent_or_empty "$tmp/git-push-calls.log" "pr-create final summary failure skips post-log push"
if grep -Fq 'write-final-report.sh post failed (exit 17)' "$tmp/execution-issues.md"; then
    ok "pr-create final summary failure records execution issue"
else
    fail "pr-create final summary failure records execution issue"
    sed 's/^/    issues: /' "$tmp/execution-issues.md" 2>/dev/null || true
fi
if grep -Fq 'sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD' "$tmp/execution-issues.md"; then
    fail "pr-create final summary failure should redact stderr"
    sed 's/^/    issues: /' "$tmp/execution-issues.md" 2>/dev/null || true
else
    ok "pr-create final summary failure redacts stderr"
fi

root=$(make_repo pr_create_log_commit_failure)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-pr-create-log-commit-failure.XXXXXX)
cat > "$root/scripts/larch-log.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
sentinel_dir="${LARCH_LOG_STUB_SENTINEL_DIR:-/tmp}"
printf 'LARCH_LOG_ARGS=%s\n' "$*" >> "$sentinel_dir/larch-log-calls.txt"
if [[ "${1:-}" == commit ]]; then
  printf 'commit failed sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD\n' >&2
  exit 23
fi
STUB
chmod +x "$root/scripts/larch-log.sh"
cat > "$root/scripts/create-pr.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'create-pr-called\n' >> "${IMPLEMENT_TMPDIR:?}/create-pr-calls.log"
echo "PR_NUMBER=123"
echo "PR_URL=https://example.invalid/pr/123"
echo "PR_TITLE=Title"
echo "PR_STATUS=created"
STUB
chmod +x "$root/scripts/create-pr.sh"
write_state "$tmp/ship-pr-state.sh" pr-create
LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "pr-create log commit failure continues"
if grep -qxF 'create-pr-called' "$tmp/create-pr-calls.log"; then
    ok "pr-create log commit failure still invokes create-pr"
else
    fail "pr-create log commit failure should still invoke create-pr"
    sed 's/^/    create-pr: /' "$tmp/create-pr-calls.log" 2>/dev/null || true
fi
if grep -Fq 'larch-log.sh commit (pre-pr-create) failed (exit 23)' "$tmp/execution-issues.md"; then
    ok "pr-create log commit failure records warning"
else
    fail "pr-create log commit failure records warning"
    sed 's/^/    issues: /' "$tmp/execution-issues.md" 2>/dev/null || true
fi
if grep -Fq 'sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD' "$tmp/execution-issues.md"; then
    fail "pr-create log commit failure should redact stderr"
    sed 's/^/    issues: /' "$tmp/execution-issues.md" 2>/dev/null || true
else
    ok "pr-create log commit failure redacts stderr"
fi
rm -rf "$sentinel_dir"

root=$(make_repo pr_create_body_code_flow_only)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" pr-create
# Pre-create pr-body.md as run_pr_prep_phase would have — PHASE=pr-create skips that step
printf '## Summary\n- Implemented changes.\n\n<details><summary>Code Flow Diagram</summary>\n\nCode flow diagram not available.\n\n</details>\n\n<details><summary>Test plan</summary>\n\n- [x] Ran relevant checks.\n\n</details>\n\nCloses #7\n\nGenerated with [Claude Code](https://claude.com/claude-code)\n' > "$tmp/pr-body.md"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "pr-create body code-flow-only exits 0"
if grep -Fq '<summary>Code Flow Diagram</summary>' "$tmp/create-pr-body-capture.md" && grep -Fq 'Code flow diagram not available.' "$tmp/create-pr-body-capture.md"; then
    ok "pr-create body code-flow-only keeps code flow details"
else
    fail "pr-create body code-flow-only keeps code flow details"
    sed 's/^/    pr-body: /' "$tmp/create-pr-body-capture.md" 2>/dev/null || true
fi
if grep -Fq 'Architecture Diagram' "$tmp/create-pr-body-capture.md"; then
    fail "pr-create body code-flow-only omits architecture section"
    sed 's/^/    pr-body: /' "$tmp/create-pr-body-capture.md" 2>/dev/null || true
else
    ok "pr-create body code-flow-only omits architecture section"
fi

# PR title: oldest commit (tail -1) with issue number prefix.
root=$(make_repo pr_title_oldest_with_issue_num)
tmp=$(make_tmpdir)
initial_branch=$(git -C "$root" branch --show-current)
if [ "$initial_branch" = "main" ]; then
    git -C "$root" commit --allow-empty -q -m "base"
    git -C "$root" update-ref refs/remotes/origin/main HEAD
    git -C "$root" checkout -q -b pr-title-branch
else
    # `make_repo` runs `git init` (which creates `main`), then commits, then
    # checks out feature/test-issue-7. On modern git, `main` already exists,
    # so `git checkout -b main` fails — use `checkout main` (existing) or
    # `checkout -b main` (absent) defensively.
    if git -C "$root" rev-parse --verify --quiet main >/dev/null 2>&1; then
        git -C "$root" checkout -q main
    else
        git -C "$root" checkout -q -b main
    fi
    git -C "$root" commit --allow-empty -q -m "base"
    git -C "$root" update-ref refs/remotes/origin/main HEAD
    git -C "$root" checkout -q "$initial_branch"
fi
git -C "$root" commit --allow-empty -q -m "initial"
git -C "$root" commit --allow-empty -q -m "chore(larch-logs): flush test-run"
git -C "$root" commit --allow-empty -q -m "Bump version to 1.0.1"
write_state "$tmp/ship-pr-state.sh" pr-create
clear_pr_state "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "pr-title oldest: exits 0"
assert_state_line "$tmp/ship-pr-state.sh" "PR_TITLE=Fixes #7: initial" "pr-title: oldest commit with issue prefix used as PR title"

root=$(make_repo pr_create_existing_updates_title)
tmp=$(make_tmpdir)
cat > "$root/scripts/create-pr.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "PR_NUMBER=123"
echo "PR_URL=https://example.invalid/pr/123"
echo "PR_TITLE=Title"
echo "PR_STATUS=existing"
STUB
chmod +x "$root/scripts/create-pr.sh"
cat > "$root/scripts/gh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "${IMPLEMENT_TMPDIR:?}/gh-calls.log"
if [[ "${1:-}" == pr && "${2:-}" == edit ]]; then
  exit 0
fi
exit 1
STUB
chmod +x "$root/scripts/gh"
initial_branch=$(git -C "$root" branch --show-current)
if [ "$initial_branch" = "main" ]; then
    git -C "$root" commit --allow-empty -q -m "base"
    git -C "$root" update-ref refs/remotes/origin/main HEAD
    git -C "$root" checkout -q -b existing-pr-branch
else
    if git -C "$root" rev-parse --verify --quiet main >/dev/null 2>&1; then
        git -C "$root" checkout -q main
    else
        git -C "$root" checkout -q -b main
    fi
    git -C "$root" commit --allow-empty -q -m "base"
    git -C "$root" update-ref refs/remotes/origin/main HEAD
    git -C "$root" checkout -q "$initial_branch"
fi
git -C "$root" commit --allow-empty -q -m "initial"
git -C "$root" commit --allow-empty -q -m "Bump version to 1.0.1"
write_state "$tmp/ship-pr-state.sh" pr-create
clear_pr_state "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "existing pr title refresh: exits 0"
if grep -Fxq 'pr edit 123 --repo owner/repo --title Fixes #7: initial' "$tmp/gh-calls.log"; then
    ok "existing pr title refresh: updates existing PR title"
else
    fail "existing pr title refresh: should update existing PR title"
    sed 's/^/    gh: /' "$tmp/gh-calls.log" 2>/dev/null || true
fi

# Postmerge manifest finalization: with PR_CLOSED=true, larch-log manifest runs.
root=$(make_repo postmerge_flush)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-postmerge-flush.XXXXXX)
mkdir -p "$tmp/larch-logs/implement/test-run"
printf '{"status":"in-progress"}\n' > "$tmp/larch-logs/implement/test-run/manifest.json"
touch "$tmp/post-merge-sentinel"
write_state "$tmp/ship-pr-state.sh" postmerge
awk -F= '{if ($1=="PR_CLOSED") print "PR_CLOSED=true"; else print}' \
    "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-flush" 2>&1)
set -e
if [ -f "$sentinel_dir/larch-log-calls.txt" ]; then
    if grep -q "manifest" "$sentinel_dir/larch-log-calls.txt" && \
       grep -q "status=done" "$sentinel_dir/larch-log-calls.txt" && \
       ! grep -q "^LARCH_LOG_ARGS=commit" "$sentinel_dir/larch-log-calls.txt"; then
        exp=$(printf '%s\n' 'larch-log manifest' 'write-final-report')
        if [[ "$(cat "$sentinel_dir/postmerge-order.log")" == "$exp" ]]; then
            ok "postmerge manifest finalization calls larch-log manifest with status=done but no post-merge commit when PR_CLOSED=true"
        else
            fail "postmerge ordering: expected manifest then write-final-report (no commit); got: $(cat "$sentinel_dir/postmerge-order.log")"
        fi
    else
        fail "postmerge manifest finalization: expected larch-log manifest with status=done and no commit; got: $(cat "$sentinel_dir/larch-log-calls.txt")"
    fi
else
    fail "postmerge manifest finalization: larch-log.sh stub was not called (PR_CLOSED=true path)"
fi
rm -rf "$sentinel_dir"

# Positive assertion: run_postmerge_phase must not advance HEAD vs origin/main (no orphan beyond upstream tip).
root=$(make_repo postmerge_no_orphan_commit)
git -C "$root" remote add origin .
git -C "$root" fetch -q origin "+HEAD:refs/remotes/origin/main"
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-postmerge-no-orphan.XXXXXX)
mkdir -p "$tmp/larch-logs/implement/test-run"
printf '{"status":"in-progress"}\n' > "$tmp/larch-logs/implement/test-run/manifest.json"
touch "$tmp/post-merge-sentinel"
write_state "$tmp/ship-pr-state.sh" postmerge
awk -F= '{if ($1=="PR_CLOSED") print "PR_CLOSED=true"; else print}' \
    "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-no-orphan" 2>&1)
set -e
head_after=$(git -C "$root" rev-parse HEAD 2>/dev/null || true)
set +e
orphan_count=$(git -C "$root" rev-list --count origin/main..HEAD 2>/dev/null)
orphan_rev_list_rc=$?
set -e
if [[ "$orphan_rev_list_rc" -ne 0 ]]; then
    fail "postmerge phase: git rev-list --count origin/main..HEAD failed (rc=$orphan_rev_list_rc, HEAD=$head_after)"
elif [[ "$orphan_count" == "0" ]]; then
    ok "postmerge phase leaves origin/main..HEAD empty (no commits past upstream tip after run_postmerge_phase)"
else
    fail "postmerge phase left $orphan_count commit(s) in origin/main..HEAD (HEAD=$head_after)"
fi
rm -rf "$sentinel_dir"

# Postmerge: manifest failure skips write-final-report (fail-closed downstream).
root=$(make_repo postmerge_manifest_fail_skips_downstream)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-postmerge-manifest-fail.XXXXXX)
mkdir -p "$tmp/larch-logs/implement/test-run"
printf '{"status":"in-progress"}\n' > "$tmp/larch-logs/implement/test-run/manifest.json"
touch "$tmp/post-merge-sentinel"
write_state "$tmp/ship-pr-state.sh" postmerge
awk -F= '{if ($1=="PR_CLOSED") print "PR_CLOSED=true"; else print}' \
    "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    STUB_LARCH_MANIFEST_FINAL_FAIL=1 \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-manifest-fail" 2>&1)
set -e
if [ -f "$sentinel_dir/larch-log-calls.txt" ] && \
   ! grep -q write-final-report "$sentinel_dir/postmerge-order.log" 2>/dev/null; then
    exp=$(printf '%s\n' 'larch-log manifest')
    if [[ "$(cat "$sentinel_dir/postmerge-order.log")" == "$exp" ]]; then
        ok "postmerge manifest failure skips write-final-report (manifest only)"
    else
        fail "postmerge manifest-fail ordering: expected single manifest line; got: $(cat "$sentinel_dir/postmerge-order.log")"
    fi
else
    fail "postmerge manifest failure: expected no write-final-report trace; calls=$(cat "$sentinel_dir/larch-log-calls.txt" 2>/dev/null) order=$(cat "$sentinel_dir/postmerge-order.log" 2>/dev/null)"
fi
rm -rf "$sentinel_dir"

# Stub matches larch-log.sh: post-merge sentinel unconditionally refuses commit (no env bypass).
root=$(make_repo larch_log_stub_postmerge_commit_guards)
tmp=$(make_tmpdir)
touch "$tmp/post-merge-sentinel"
sentinel_dir=$(mktemp -d /tmp/ship-pr-larch-log-stub-guard.XXXXXX)
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" IMPLEMENT_TMPDIR="$tmp" \
    "$root/scripts/larch-log.sh" commit --log-root "$tmp/larch-logs" --skill implement --run-id z \
    >"$tmp/lc-out" 2>"$tmp/lc-err")
rc_guard=$?
set -e
if [[ "$rc_guard" -eq 1 ]]; then
    ok "larch-log stub refuses commit when post-merge sentinel is present"
else
    fail "larch-log stub sentinel refusal expected exit 1, got $rc_guard stderr=$(cat "$tmp/lc-err")"
fi
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" IMPLEMENT_TMPDIR="$tmp" \
    LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR=1 \
    "$root/scripts/larch-log.sh" commit --log-root "$tmp/larch-logs" --skill implement --run-id z \
    >"$tmp/lc-out2" 2>"$tmp/lc-err2")
rc_bypass=$?
set -e
if [[ "$rc_bypass" -eq 1 ]]; then
    ok "larch-log stub still refuses commit when LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR=1 (legacy env ignored)"
else
    fail "larch-log stub expected exit 1 with legacy post-merge env set; got rc=$rc_bypass"
fi
rm -rf "$sentinel_dir"

# Postmerge with --no-logs-commit true: manifest + write-final-report still run; stub sees LARCH_NO_LOGS_COMMIT=true (postmerge never invokes larch-log commit).
root=$(make_repo postmerge_no_logs_commit)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-postmerge-no-logs-commit.XXXXXX)
mkdir -p "$tmp/larch-logs/implement/test-run"
printf '{"status":"in-progress"}\n' > "$tmp/larch-logs/implement/test-run/manifest.json"
touch "$tmp/post-merge-sentinel"
write_state "$tmp/ship-pr-state.sh" postmerge
awk -F= '{if ($1=="PR_CLOSED") print "PR_CLOSED=true"; else print}' \
    "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo --no-logs-commit true \
    > "$tmp/stdout-postmerge-nolc" 2>&1)
set -e
if [ -f "$sentinel_dir/larch-log-calls.txt" ]; then
    if grep -q "status=done" "$sentinel_dir/larch-log-calls.txt" && \
       grep -qFx "stub_env LARCH_NO_LOGS_COMMIT=true" "$sentinel_dir/stub-env.log" 2>/dev/null && \
       ! grep -q "^LARCH_LOG_ARGS=commit" "$sentinel_dir/larch-log-calls.txt"; then
        exp=$(printf '%s\n' 'larch-log manifest' 'write-final-report')
        if [[ "$(cat "$sentinel_dir/postmerge-order.log")" == "$exp" ]]; then
            ok "postmerge with --no-logs-commit true runs manifest then write-final-report with LARCH_NO_LOGS_COMMIT exported"
        else
            fail "postmerge no-logs-commit ordering: expected manifest then write-final-report; got: $(cat "$sentinel_dir/postmerge-order.log")"
        fi
    else
        fail "postmerge no-logs-commit: expected manifest status=done and stub_env LARCH_NO_LOGS_COMMIT=true; calls=$(cat "$sentinel_dir/larch-log-calls.txt") env=$(cat "$sentinel_dir/stub-env.log" 2>/dev/null)"
    fi
else
    fail "postmerge no-logs-commit: larch-log.sh stub was not called"
fi
rm -rf "$sentinel_dir"

# Postmerge manifest finalization: missing manifest is synthesized before final status.
root=$(make_repo postmerge_missing_manifest)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-postmerge-recovery.XXXXXX)
mkdir -p "$tmp/larch-logs/implement/test-run"
touch "$tmp/post-merge-sentinel"
write_state "$tmp/ship-pr-state.sh" postmerge
awk -F= '{if ($1=="PR_CLOSED") print "PR_CLOSED=true"; else print}' \
    "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-recovery" 2>&1)
set -e
if [ -f "$sentinel_dir/larch-log-calls.txt" ]; then
    if grep -q "^LARCH_LOG_ARGS=init" "$sentinel_dir/larch-log-calls.txt" && \
       grep -q "recovery_reason=manifest_lost_mid_run" "$sentinel_dir/larch-log-calls.txt" && \
       grep -q -- "--issue" "$sentinel_dir/larch-log-calls.txt" && \
       grep -q "status=done" "$sentinel_dir/larch-log-calls.txt" && \
       ! grep -q "^LARCH_LOG_ARGS=commit" "$sentinel_dir/larch-log-calls.txt"; then
        exp=$(printf '%s\n' \
            'larch-log init' \
            'larch-log manifest' \
            'larch-log manifest' \
            'write-final-report')
        if [[ "$(cat "$sentinel_dir/postmerge-order.log")" == "$exp" ]]; then
            ok "postmerge missing-manifest recovery: init + partial tag, then manifest done, write-final-report (no post-merge commit)"
        else
            fail "postmerge missing-manifest ordering: expected init, two manifests, write-final-report (no commit); got: $(cat "$sentinel_dir/postmerge-order.log")"
        fi
    else
        fail "postmerge missing-manifest recovery: expected init + partial + --issue + status=done without commit; got: $(cat "$sentinel_dir/larch-log-calls.txt")"
    fi
else
    fail "postmerge missing-manifest recovery: larch-log.sh stub was not called"
fi
rm -rf "$sentinel_dir"

# Postmerge manifest finalization: with PR_CLOSED=false (draft/no-merge), no manifest update.
root=$(make_repo postmerge_no_flush)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-postmerge-noflush.XXXXXX)
write_state "$tmp/ship-pr-state.sh" postmerge
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-noflush" 2>&1)
set -e
if [ -f "$sentinel_dir/larch-log-calls.txt" ] && \
   grep -q "manifest" "$sentinel_dir/larch-log-calls.txt"; then
    fail "postmerge with PR_CLOSED=false should not call larch-log manifest"
else
    ok "postmerge with PR_CLOSED=false skips larch-log manifest finalization"
fi
rm -rf "$sentinel_dir"

# PR create flush: commit the placeholder final-summary before create-pr.
root=$(make_repo pr_create_flush)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-pr-create-flush.XXXXXX)
write_state "$tmp/ship-pr-state.sh" pr-create
LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "pr-create happy path exits 0 after continuation"
if [ -f "$sentinel_dir/larch-log-calls.txt" ]; then
    if grep -q -- 'commit --log-root .* --run-id test-run' "$sentinel_dir/larch-log-calls.txt" && \
       ! grep -q -- 'manifest --log-root .* --run-id test-run --field pr_number=123' "$sentinel_dir/larch-log-calls.txt"; then
        ok "pr-create flush commits pre-PR logs without manifest pr_number write"
    else
        fail "pr-create flush: expected commit without manifest pr_number write; got: $(cat "$sentinel_dir/larch-log-calls.txt")"
    fi
else
    fail "pr-create flush: larch-log.sh stub was not called"
fi
rm -rf "$sentinel_dir"

root=$(make_repo pr_create_no_logs_commit)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-pr-create-no-logs-commit.XXXXXX)
write_state "$tmp/ship-pr-state.sh" pr-create
clear_pr_state "$tmp/ship-pr-state.sh"
LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" run_subject "$root" "$tmp" "$tmp/rc" --no-logs-commit true
assert_rc "$tmp/rc" 0 "pr-create no-logs-commit exits 0"
if [ -f "$sentinel_dir/larch-log-calls.txt" ] && grep -q -- 'commit --log-root' "$sentinel_dir/larch-log-calls.txt"; then
    fail "pr-create no-logs-commit should skip pre-PR larch-log commit"
    sed 's/^/    larch-log: /' "$sentinel_dir/larch-log-calls.txt" 2>/dev/null || true
else
    ok "pr-create no-logs-commit skips pre-PR larch-log commit"
fi
rm -rf "$sentinel_dir"
fi  # end section: postmerge

if section_runs fix-loop; then
# Regression: CI-fix vendors receive the design plan path from session-env.
root=$(make_repo ci_fix_plan_file)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d /tmp/ship-pr-plan-ci-fix.XXXXXX)
plan_file="$tmp/design-plan.txt"
printf 'preserve this implementation plan\n' > "$plan_file"
printf 'PLAN_FILE=%s\n' "$plan_file" > "$tmp/session-env.sh"
cat > "$root/scripts/cursor" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/cursor" "$root/scripts/ci-wait.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
PATH="$root/scripts:$PATH" SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "CI fix plan-file forwarding exits 0"
if [ -f "$call_dir/launcher-calls.txt" ] && \
   grep -Fq 'launch-cursor-ci.sh' "$call_dir/launcher-calls.txt" && \
   grep -Fq -- '--role fix' "$call_dir/launcher-calls.txt" && \
   grep -Fq -- '--plan-file' "$call_dir/launcher-calls.txt" && \
   grep -Fq "$plan_file" "$call_dir/launcher-calls.txt"; then
    ok "CI fix forwards --plan-file to cursor launcher"
else
    fail "CI fix should forward --plan-file to cursor launcher"
    sed 's/^/    launcher: /' "$call_dir/launcher-calls.txt" 2>/dev/null || true
fi
rm -rf "$call_dir"

# Regression: rebase conflict resolver vendors receive the design plan path.
root=$(make_repo conflict_plan_file)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d /tmp/ship-pr-plan-conflict.XXXXXX)
plan_file="$tmp/design-plan.txt"
printf 'preserve this implementation plan through conflict resolution\n' > "$plan_file"
printf 'PLAN_FILE=%s\n' "$plan_file" > "$tmp/session-env.sh"
cat > "$root/scripts/cursor" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=rebase\nCI_STATUS=fail\nBEHIND_COUNT=1\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
cat > "$root/scripts/rebase-push.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/rebase-push-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    echo "CONFLICT_FILES=CHANGELOG.md"
    exit 1
fi
exit 0
STUB
for extra in drop-bump-commit.sh git-sync-local-main.sh git-force-push.sh; do
    printf '#!/usr/bin/env bash\nexit 0\n' > "$root/scripts/$extra"
done
chmod +x "$root/scripts/cursor" \
         "$root/scripts/ci-wait.sh" \
         "$root/scripts/rebase-push.sh" \
         "$root/scripts/drop-bump-commit.sh" \
         "$root/scripts/git-sync-local-main.sh" \
         "$root/scripts/git-force-push.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
PATH="$root/scripts:$PATH" SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "conflict resolver plan-file forwarding exits 0"
if [ -f "$call_dir/launcher-calls.txt" ] && \
   grep -Fq 'launch-cursor-ci.sh' "$call_dir/launcher-calls.txt" && \
   grep -Fq -- '--role resolve-conflict' "$call_dir/launcher-calls.txt" && \
   grep -Fq -- '--plan-file' "$call_dir/launcher-calls.txt" && \
   grep -Fq "$plan_file" "$call_dir/launcher-calls.txt"; then
    ok "conflict resolver forwards --plan-file to cursor launcher"
else
    fail "conflict resolver should forward --plan-file to cursor launcher"
    sed 's/^/    launcher: /' "$call_dir/launcher-calls.txt" 2>/dev/null || true
fi
if [ -f "$call_dir/launcher-calls.txt" ] && grep -qF -- "--timeout 600" "$call_dir/launcher-calls.txt"; then
    ok "conflict resolver uses 600s vendor timeout"
else
    fail "conflict resolver should pass --timeout 600"
    sed 's/^/    launcher: /' "$call_dir/launcher-calls.txt" 2>/dev/null || true
fi
rm -rf "$call_dir"

# Regression: pure CHANGELOG rebase conflict auto-resolves without vendor launcher.
root=$(make_repo_rebase_autoresolve_prep rebump_changelog_auto)
tmp=$(make_tmpdir)
count_dir=$(mktemp -d /tmp/ship-pr-changelog-auto.XXXXXX)
_make_rebase_stubs "$root" "$count_dir"
write_state "$tmp/ship-pr-state.sh" ci-initial
PATH="$root/scripts:$PATH" SHIP_PR_LAUNCH_SENTINEL_DIR="$count_dir" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "CHANGELOG-only rebase conflict auto-resolve exits 0"
if [ ! -f "$count_dir/launcher-calls.txt" ]; then
    ok "CHANGELOG auto-resolve skips vendor launcher"
else
    fail "CHANGELOG auto-resolve should not invoke launch-cursor/codex"
    sed 's/^/    launcher: /' "$count_dir/launcher-calls.txt" 2>/dev/null || true
fi
rm -rf "$count_dir"

# Regression: CHANGELOG.rst conflict uses RST section merge (no vendor).
root=$(make_repo_rebase_autoresolve_rst_prep rebump_changelog_rst)
tmp=$(make_tmpdir)
count_dir=$(mktemp -d /tmp/ship-pr-changelog-rst.XXXXXX)
_make_rebase_stubs "$root" "$count_dir"
write_state "$tmp/ship-pr-state.sh" ci-initial
PATH="$root/scripts:$PATH" SHIP_PR_LAUNCH_SENTINEL_DIR="$count_dir" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "CHANGELOG.rst-only rebase conflict auto-resolve exits 0"
if [ ! -f "$count_dir/launcher-calls.txt" ]; then
    ok "CHANGELOG.rst auto-resolve skips vendor launcher"
else
    fail "CHANGELOG.rst auto-resolve should not invoke launch-cursor/codex"
    sed 's/^/    launcher: /' "$count_dir/launcher-calls.txt" 2>/dev/null || true
fi
rm -rf "$count_dir"

# Regression: bare CHANGELOG filename (RST-shaped) auto-resolves without vendor.
root=$(make_repo_rebase_autoresolve_bare_changelog_prep rebump_changelog_bare)
tmp=$(make_tmpdir)
count_dir=$(mktemp -d /tmp/ship-pr-changelog-bare.XXXXXX)
_make_rebase_stubs "$root" "$count_dir"
write_state "$tmp/ship-pr-state.sh" ci-initial
PATH="$root/scripts:$PATH" SHIP_PR_LAUNCH_SENTINEL_DIR="$count_dir" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "bare CHANGELOG rebase conflict auto-resolve exits 0"
if [ ! -f "$count_dir/launcher-calls.txt" ]; then
    ok "bare CHANGELOG auto-resolve skips vendor launcher"
else
    fail "bare CHANGELOG auto-resolve should not invoke launch-cursor/codex"
    sed 's/^/    launcher: /' "$count_dir/launcher-calls.txt" 2>/dev/null || true
fi
rm -rf "$count_dir"

# Regression: root-relative ``.claude-plugin/plugin.json`` rebase conflict → checkout --ours (no vendor).
root=$(make_repo_rebase_plugin_json_prep rebump_plugin_json_root)
tmp=$(make_tmpdir)
count_dir=$(mktemp -d /tmp/ship-pr-plugin-json-auto.XXXXXX)
_make_rebase_stubs "$root" "$count_dir"
write_state "$tmp/ship-pr-state.sh" ci-initial
PATH="$root/scripts:$PATH" SHIP_PR_LAUNCH_SENTINEL_DIR="$count_dir" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 ".claude-plugin/plugin.json-only rebase conflict auto-resolve exits 0"
if [ ! -f "$count_dir/launcher-calls.txt" ]; then
    ok "plugin.json manifest auto-resolve skips vendor launcher"
else
    fail "plugin.json manifest auto-resolve should not invoke launch-cursor/codex"
    sed 's/^/    launcher: /' "$count_dir/launcher-calls.txt" 2>/dev/null || true
fi
rm -rf "$count_dir"

# Regression: mixed CHANGELOG + non-trivial conflict → vendor sees remaining path + 600s timeout.
root=$(make_repo_rebase_dual_conflict_prep rebump_changelog_mixed)
tmp=$(make_tmpdir)
count_dir=$(mktemp -d /tmp/ship-pr-changelog-mix.XXXXXX)
cat > "$root/scripts/launch-cursor-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
    mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
    printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
# Stage the resolved conflict but DO NOT run `git rebase --continue` — the
# `rebase-nonbump` verifier inside run_recovery_waterfall continues the rebase
# itself (see scripts/ship-pr.sh case verify_kind=rebase-nonbump). A launcher
# that continues the rebase here would leave the verifier with no in-progress
# rebase, causing `git rebase --continue` to fail and the tier to roll back.
# Use `--theirs` (feature-branch content) so the resolved commit is non-empty
# and `git rebase --continue` proceeds without `--allow-empty` prompts.
if git rev-parse --git-dir >/dev/null 2>&1; then
    if [ -d "$(git rev-parse --git-dir)/rebase-merge" ] || [ -d "$(git rev-parse --git-dir)/rebase-apply" ]; then
        git checkout --theirs -- other.txt
        git add other.txt
    fi
fi
exit 0
STUB
chmod +x "$root/scripts/launch-cursor-ci.sh"
cp "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-claude-ci.sh"
chmod +x "$root/scripts/launch-claude-ci.sh"
_make_rebase_stubs "$root" "$count_dir"
write_state "$tmp/ship-pr-state.sh" ci-initial
PATH="$root/scripts:$PATH" SHIP_PR_LAUNCH_SENTINEL_DIR="$count_dir" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "mixed CHANGELOG conflict auto-resolve + recovery waterfall completes rebase"
# The rc=0 path means run_recovery_waterfall succeeded — Phase 1–4 was NOT invoked
# and the legacy stall path (which writes CALLER_KIND=ship_pr_pre_push and emits
# CONFLICT_FILES via emit_kv) was NOT taken. Those keys are stall-only signals; the
# success path proves itself via rc=0 + launcher dispatch (assertion below). Pin the
# negative invariant so a future regression that mistakenly writes the stall keys on
# the success path is caught (FINDING_23 from issue #2395 review).
if grep -qF 'CALLER_KIND=ship_pr_pre_push' "$tmp/ship-pr-state.sh" 2>/dev/null; then
    fail "mixed conflict success path must NOT write CALLER_KIND=ship_pr_pre_push (stall-only key)"
else
    ok "mixed conflict success path leaves CALLER_KIND clear (waterfall recovered without legacy stall)"
fi
if [ -f "$count_dir/launcher-calls.txt" ] && grep -q -- "--role resolve-conflict" "$count_dir/launcher-calls.txt" 2>/dev/null; then
    ok "mixed conflict invokes recovery waterfall resolve-conflict launcher"
else
    fail "mixed conflict should record resolve-conflict in launcher-calls.txt"
    sed 's/^/    launcher: /' "$count_dir/launcher-calls.txt" 2>/dev/null | head -20 || true
fi
rm -rf "$count_dir"

# Regression: non-changelog-only conflict → vendor with --conflict-files + 600s timeout.
root=$(make_repo vendor_only_paths)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d /tmp/ship-pr-vendor-only.XXXXXX)
cat > "$root/scripts/rebase-push.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/rebase-push-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'CONFLICT_FILES=locked.bin\n'
    exit 1
fi
exit 0
STUB
chmod +x "$root/scripts/rebase-push.sh"
cat > "$root/scripts/cursor" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$root/scripts/cursor"
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count2"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=rebase\nCI_STATUS=fail\nBEHIND_COUNT=1\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/ci-wait.sh"
for extra in drop-bump-commit.sh git-sync-local-main.sh git-force-push.sh; do
    printf '#!/usr/bin/env bash\nexit 0\n' > "$root/scripts/$extra"
done
chmod +x "$root/scripts/drop-bump-commit.sh" "$root/scripts/git-sync-local-main.sh" "$root/scripts/git-force-push.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
PATH="$root/scripts:$PATH" SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "non-changelog-only conflict stalls after recovery waterfall exhausts (exit_stall)"
if grep -qF 'CALLER_KIND=ship_pr_pre_push' "$tmp/ship-pr-state.sh" 2>/dev/null; then
    ok "non-changelog conflict dispatches Phase 1–4 (CALLER_KIND=ship_pr_pre_push)"
else
    fail "non-changelog conflict should set CALLER_KIND=ship_pr_pre_push in state"
fi
if [ -f "$call_dir/launcher-calls.txt" ] && grep -Fq "launch-cursor-ci.sh" "$call_dir/launcher-calls.txt" 2>/dev/null \
    && grep -Fq -- '--role resolve-conflict' "$call_dir/launcher-calls.txt" 2>/dev/null; then
    ok "non-changelog conflict recovery waterfall invokes launch-cursor-ci resolve-conflict"
else
    fail "non-changelog conflict should record cursor resolve-conflict tier attempt"
    sed 's/^/    launcher: /' "$call_dir/launcher-calls.txt" 2>/dev/null | head -20 || true
fi
rm -rf "$call_dir"

root=$(make_repo rebase_second_conflict_breadcrumb)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d /tmp/ship-pr-rebase-second-conflict.XXXXXX)
cat > "$root/scripts/cursor" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf 'ACTION=rebase\nCI_STATUS=fail\nBEHIND_COUNT=1\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
STUB
cat > "$root/scripts/rebase-push.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/rebase-push-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
echo "CONFLICT_FILES=README.md"
exit 1
STUB
for extra in drop-bump-commit.sh git-sync-local-main.sh git-force-push.sh; do
    printf '#!/usr/bin/env bash\nexit 0\n' > "$root/scripts/$extra"
done
chmod +x "$root/scripts/cursor" \
         "$root/scripts/ci-wait.sh" \
         "$root/scripts/rebase-push.sh" \
         "$root/scripts/drop-bump-commit.sh" \
         "$root/scripts/git-sync-local-main.sh" \
         "$root/scripts/git-force-push.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
LARCH_QUIET_BREADCRUMBS=1 PATH="$root/scripts:$PATH" SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "second rebase conflict stalls after recovery waterfall exhausts (exit_stall)"
if grep -qF 'CALLER_KIND=ship_pr_pre_push' "$tmp/ship-pr-state.sh" 2>/dev/null; then
    ok "second rebase conflict sets CALLER_KIND=ship_pr_pre_push"
else
    fail "second rebase conflict should set CALLER_KIND=ship_pr_pre_push in state"
fi
rm -rf "$call_dir"

# Regression: second evaluate_failure (TRANSIENT_RETRIES=1) escalates to fix agent,
# not another rerun. Guards the threshold change in run_evaluate_failure (issue #1987).
root=$(make_repo ci_fix_escalation)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d /tmp/ship-pr-escalation.XXXXXX)

# ci-wait.sh: return evaluate_failure on first call, merge on subsequent calls.
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/ci-wait.sh"

# ci-rerun-failed.sh: write sentinel if called — must NOT be called when TRANSIENT_RETRIES=1.
cat > "$root/scripts/ci-rerun-failed.sh" <<'STUB'
#!/usr/bin/env bash
printf 'RERUN_SUBMITTED=true\nALREADY_RUNNING=false\nERROR=\n'
touch "${RERUN_SENTINEL_FILE:-/tmp/rerun-called}"
STUB
chmod +x "$root/scripts/ci-rerun-failed.sh"

write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"

rerun_sentinel="$call_dir/rerun-called"
RERUN_SENTINEL_FILE="$rerun_sentinel" run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 0 "second evaluate_failure (TRANSIENT_RETRIES=1) exits 0 via fix-agent path"
if [ -f "$rerun_sentinel" ]; then
    fail "second evaluate_failure must NOT submit another rerun when TRANSIENT_RETRIES=1"
else
    ok "second evaluate_failure skips rerun and escalates to fix agent (TRANSIENT_RETRIES=1)"
fi
rm -rf "$call_dir"

# Vendor CI-fix outer loop exhaustion (TRANSIENT_RETRIES>=1): 3× tier failures → exit 4, STALL_STEP=10-max-retries.
root=$(make_repo vendor_loop_ci_fix_exhausted)
tmp=$(make_tmpdir)
cat > "$root/scripts/ci-wait.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
STUB
for launcher in launch-cursor-ci.sh launch-codex-ci.sh launch-claude-ci.sh; do
    cat > "$root/scripts/$launcher" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'LAUNCHER_EXIT=1\n'
exit 0
STUB
    chmod +x "$root/scripts/$launcher"
done
chmod +x "$root/scripts/ci-wait.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     /^FIX_ATTEMPTS=/ {print "FIX_ATTEMPTS=0"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "vendor CI-fix loop exhaustion exits 4 (exit_stall)"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=10-max-retries" "vendor loop exhaustion records STALL_STEP=10-max-retries"

# ──────────────────────────────────────────────────────────────────────────────
# --no-logs-commit: exported to lifecycle helper subprocess tree
# ──────────────────────────────────────────────────────────────────────────────

root=$(make_repo rebump_flush_enabled)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-rebump-enabled.XXXXXX)
# Use ci-initial so run_rebase_rebump fires (on ACTION=rebase) before any
# ci-merge entry; the scenario exits 0 after the second ci-wait
# returns ACTION=merge, advancing to ci-merge without entering postmerge.
write_state "$tmp/ship-pr-state.sh" ci-initial
_make_rebase_stubs "$root" "$sentinel_dir"
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo --no-logs-commit false \
    > "$tmp/stdout-rebump-enabled" 2>&1)
printf '%s' "$?" > "$tmp/rc-rebump-enabled"
set -e
assert_rc "$tmp/rc-rebump-enabled" 0 "run_rebase_rebump (--no-logs-commit false): ship-pr exits 0"
if [ -f "$sentinel_dir/env-calls.txt" ] && \
   grep -q "^APPLY_BUMP_LARCH_NO_LOGS_COMMIT=false$" "$sentinel_dir/env-calls.txt"; then
    ok "run_rebase_rebump: LARCH_NO_LOGS_COMMIT=false exported to apply-bump"
else
    fail "run_rebase_rebump: expected LARCH_NO_LOGS_COMMIT=false in apply-bump env"
fi
rm -rf "$sentinel_dir"

root=$(make_repo rebump_changelog_commit_shape)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-rebump-changelog.XXXXXX)
write_state "$tmp/ship-pr-state.sh" ci-initial
_make_rebase_stubs "$root" "$sentinel_dir"
cp "$REPO_ROOT/scripts/drop-bump-commit.sh" "$root/scripts/drop-bump-commit.sh"
cp "$REPO_ROOT/scripts/commit-changelog.sh" "$root/scripts/commit-changelog.sh"
cp "$REPO_ROOT/scripts/git-commit.sh" "$root/scripts/git-commit.sh"
chmod +x "$root/scripts/drop-bump-commit.sh" "$root/scripts/commit-changelog.sh" "$root/scripts/git-commit.sh"
mkdir -p "$root/.claude-plugin"
cat > "$root/.claude-plugin/plugin.json" <<'JSON'
{"version":"1.2.2"}
JSON
cat > "$root/CHANGELOG.md" <<'CHANGELOG'
# Changelog

## [1.2.2] - 2025-12-31

### Fixed

- Previous release.
CHANGELOG
git -C "$root" add .claude-plugin/plugin.json CHANGELOG.md
git -C "$root" commit -q -m "Prepare version fixtures"
cat > "$root/.claude-plugin/plugin.json" <<'JSON'
{"version":"1.2.3"}
JSON
git -C "$root" add .claude-plugin/plugin.json
git -C "$root" commit -q -m "Bump version to 1.2.3"
cat > "$root/CHANGELOG.md" <<'CHANGELOG'
# Changelog

## [1.2.3] - 2026-01-01

### Fixed

- Preserve the changelog entry body.

## [1.2.2] - 2025-12-31

### Fixed

- Previous release.
CHANGELOG
git -C "$root" add CHANGELOG.md
git -C "$root" commit -q -m "Update CHANGELOG for 1.2.3"
cat > "$root/.claude/skills/bump-version/scripts/classify-bump.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
reasoning_file="${IMPLEMENT_TMPDIR:-/tmp}/bump-version-reasoning.md"
printf '# reasoning\n' > "$reasoning_file"
echo "CURRENT_VERSION=1.2.3"
echo "NEW_VERSION=1.2.4"
echo "BUMP_TYPE=PATCH"
echo "REASONING_FILE=$reasoning_file"
STUB
cat > "$root/.claude/skills/bump-version/scripts/apply-bump.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
new_version=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --new-version) new_version=$2; shift 2 ;;
    *) shift ;;
  esac
done
printf '{"version":"%s"}\n' "$new_version" > .claude-plugin/plugin.json
git add .claude-plugin/plugin.json
git commit -q -m "Bump version to $new_version"
echo "APPLIED=true"
echo "COMMIT_SHA=$(git rev-parse HEAD)"
STUB
chmod +x "$root/.claude/skills/bump-version/scripts/classify-bump.sh" \
         "$root/.claude/skills/bump-version/scripts/apply-bump.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-rebump-changelog" 2>&1)
printf '%s' "$?" > "$tmp/rc-rebump-changelog"
set -e
assert_rc "$tmp/rc-rebump-changelog" 0 "run_rebase_rebump creates separate fresh CHANGELOG commit"
rebump_log_subjects=$(git -C "$root" log --format=%s)
if [[ "$rebump_log_subjects"$'\n' == *$'Bump version to 1.2.4\n'* ]] &&
   [[ "$rebump_log_subjects"$'\n' == *$'Update CHANGELOG for 1.2.4\n'* ]] &&
   ! grep -q '^## \[1.2.3\] - ' "$root/CHANGELOG.md" &&
   grep -q '^## \[1.2.4\] - ' "$root/CHANGELOG.md"; then
    ok "run_rebase_rebump replaces stale CHANGELOG entry with fresh version"
else
    fail "run_rebase_rebump should leave fresh bump plus fresh CHANGELOG entry"
    git -C "$root" log --oneline --max-count=8 | sed 's/^/    log: /' || true
    sed 's/^/    changelog: /' "$root/CHANGELOG.md" || true
fi
rm -rf "$sentinel_dir"

root=$(make_repo rebump_flush_suppressed)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-rebump-suppressed.XXXXXX)
write_state "$tmp/ship-pr-state.sh" ci-initial
_make_rebase_stubs "$root" "$sentinel_dir"
set +e
(cd "$root" && LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo --no-logs-commit true \
    > "$tmp/stdout-rebump-suppressed" 2>&1)
printf '%s' "$?" > "$tmp/rc-rebump-suppressed"
set -e
assert_rc "$tmp/rc-rebump-suppressed" 0 "run_rebase_rebump (--no-logs-commit true): ship-pr exits 0"
if [ -f "$sentinel_dir/env-calls.txt" ] && \
   grep -q "^APPLY_BUMP_LARCH_NO_LOGS_COMMIT=true$" "$sentinel_dir/env-calls.txt"; then
    ok "run_rebase_rebump: LARCH_NO_LOGS_COMMIT=true exported to apply-bump"
else
    fail "run_rebase_rebump: expected LARCH_NO_LOGS_COMMIT=true in apply-bump env"
fi
rm -rf "$sentinel_dir"

root=$(make_repo rebump_reasoning_corrected)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-rebump-reasoning.XXXXXX)
write_state "$tmp/ship-pr-state.sh" ci-initial
_make_rebase_stubs "$root" "$sentinel_dir"
cat > "$root/.claude/skills/bump-version/scripts/classify-bump.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
reasoning_file="${IMPLEMENT_TMPDIR:-/tmp}/bump-version-reasoning.md"
cat > "$reasoning_file" <<'EOF'
# Version Bump Reasoning

## Result: PATCH

- **New version**: `2.1.5`
EOF
echo "CURRENT_VERSION=2.1.4"
echo "NEW_VERSION=2.1.5"
echo "BUMP_TYPE=PATCH"
echo "REASONING_FILE=$reasoning_file"
STUB
chmod +x "$root/.claude/skills/bump-version/scripts/classify-bump.sh"
real_git=$(command -v git)
cat > "$root/scripts/git" <<STUB
#!/usr/bin/env bash
set -euo pipefail
if [[ "\${1:-}" == "show" && "\${2:-}" == "origin/main:.claude-plugin/plugin.json" ]]; then
    printf '%s\n' '{"version":"2.3.0"}'
    exit 0
fi
exec "$real_git" "\$@"
STUB
chmod +x "$root/scripts/git"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-rebump-reasoning" 2>&1)
printf '%s' "$?" > "$tmp/rc-rebump-reasoning"
set -e
assert_rc "$tmp/rc-rebump-reasoning" 0 "run_rebase_rebump rewrites reasoning after version correction"
if grep -qxF -- "- **New version**: \`2.3.1\`" "$tmp/bump-version-reasoning.md" && \
   grep -qxF -- "### Rebase + Re-bump Correction" "$tmp/bump-version-reasoning.md"; then
    ok "run_rebase_rebump updates reasoning markdown to the corrected version"
else
    fail "run_rebase_rebump should update reasoning markdown after version correction"
    sed 's/^/    reasoning: /' "$tmp/bump-version-reasoning.md" 2>/dev/null || true
fi
rm -rf "$sentinel_dir"

root=$(make_repo rebump_invalid_new_version)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-initial
_make_rebase_stubs "$root" "$(mktemp -d /tmp/ship-pr-rebump-invalid.XXXXXX)"
cat > "$root/.claude/skills/bump-version/scripts/classify-bump.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "CURRENT_VERSION=2.1.4"
echo "NEW_VERSION=2.1"
echo "BUMP_TYPE=PATCH"
echo "REASONING_FILE=${IMPLEMENT_TMPDIR:-/tmp}/bump-version-reasoning.md"
STUB
chmod +x "$root/.claude/skills/bump-version/scripts/classify-bump.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-rebump-invalid" 2>&1)
printf '%s' "$?" > "$tmp/rc-rebump-invalid"
set -e
assert_rc "$tmp/rc-rebump-invalid" 4 "run_rebase_rebump rejects invalid classify-bump semver output"

root=$(make_repo rebump_drop_false_stalls)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-initial
_make_rebase_stubs "$root" "$(mktemp -d /tmp/ship-pr-rebump-drop-false.XXXXXX)"
cat > "$root/scripts/drop-bump-commit.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" > "${IMPLEMENT_TMPDIR:-/tmp}/drop-bump-argv.txt"
echo "DROPPED=false"
echo "WARN: found commit at HEAD~0 matches bump pattern but touches unexpected files" >&2
exit 0
STUB
chmod +x "$root/scripts/drop-bump-commit.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-rebump-drop-false" 2>&1)
printf '%s' "$?" > "$tmp/rc-rebump-drop-false"
set -e
assert_rc "$tmp/rc-rebump-drop-false" 4 "run_rebase_rebump stalls when drop-bump returns DROPPED=false"
if grep -qxF -- '--allow-changelog-only --max-depth 20' "$tmp/drop-bump-argv.txt"; then
    ok "run_rebase_rebump passes allow-changelog-only and max-depth 20 to drop-bump"
else
    fail "run_rebase_rebump should pass allow-changelog-only and max-depth 20 to drop-bump"
fi

root=$(make_repo rebump_drop_false_no_bump_continues)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-initial
_make_rebase_stubs "$root" "$(mktemp -d /tmp/ship-pr-rebump-drop-false-nobump.XXXXXX)"
cat > "$root/scripts/drop-bump-commit.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "DROPPED=false"
echo "WARN: no bump commit found within 20 commits of HEAD; not dropping" >&2
exit 0
STUB
chmod +x "$root/scripts/drop-bump-commit.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-rebump-drop-false-nobump" 2>&1)
printf '%s' "$?" > "$tmp/rc-rebump-drop-false-nobump"
set -e
assert_rc "$tmp/rc-rebump-drop-false-nobump" 0 "run_rebase_rebump continues when drop-bump reports no bump found"

root=$(make_repo rebump_commit_changelog_missing_committed_stalls)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-initial
cat > "$root/CHANGELOG.md" <<'CHANGELOG'
# Changelog
## [1.0.0] - 2026-01-01
### Fixed
- Initial release.
CHANGELOG
git -C "$root" add CHANGELOG.md && git -C "$root" commit -q -m "Add CHANGELOG"
_make_rebase_stubs "$root" "$(mktemp -d /tmp/ship-pr-rebump-cm-missing.XXXXXX)"
cat > "$root/scripts/commit-changelog.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
exit 0
STUB
chmod +x "$root/scripts/commit-changelog.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-rebump-cm-missing" 2>&1)
printf '%s' "$?" > "$tmp/rc-rebump-cm-missing"
set -e
assert_rc "$tmp/rc-rebump-cm-missing" 4 "run_rebase_rebump stalls when commit-changelog omits COMMITTED state"

root=$(make_repo rebump_commit_changelog_fail_stalls)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-initial
cat > "$root/CHANGELOG.md" <<'CHANGELOG'
# Changelog
## [1.0.0] - 2026-01-01
### Fixed
- Initial release.
CHANGELOG
git -C "$root" add CHANGELOG.md && git -C "$root" commit -q -m "Add CHANGELOG"
_make_rebase_stubs "$root" "$(mktemp -d /tmp/ship-pr-rebump-cm-fail.XXXXXX)"
cat > "$root/scripts/commit-changelog.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "COMMITTED=false"
exit 1
STUB
chmod +x "$root/scripts/commit-changelog.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-rebump-cm-fail" 2>&1)
printf '%s' "$?" > "$tmp/rc-rebump-cm-fail"
set -e
assert_rc "$tmp/rc-rebump-cm-fail" 4 "run_rebase_rebump stalls when commit-changelog fails after re-bump"

root=$(make_repo rebump_commit_changelog_noop_success)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-initial
_make_rebase_stubs "$root" "$(mktemp -d /tmp/ship-pr-rebump-cm-noop.XXXXXX)"
mkdir -p "$root/.claude-plugin"
cat > "$root/.claude-plugin/plugin.json" <<'JSON'
{"version":"1.2.2"}
JSON
cat > "$root/CHANGELOG.md" <<'CHANGELOG'
# Changelog

## [1.2.4] - 2026-01-02

### Fixed

- Already correct release notes.
CHANGELOG
git -C "$root" add .claude-plugin/plugin.json CHANGELOG.md
git -C "$root" commit -q -m "Prepare version fixtures"
cat > "$root/.claude-plugin/plugin.json" <<'JSON'
{"version":"1.2.3"}
JSON
git -C "$root" add .claude-plugin/plugin.json
git -C "$root" commit -q -m "Bump version to 1.2.3"
cat > "$root/scripts/commit-changelog.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "COMMITTED=false"
exit 0
STUB
chmod +x "$root/scripts/commit-changelog.sh"
cat > "$root/.claude/skills/bump-version/scripts/classify-bump.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
reasoning_file="${IMPLEMENT_TMPDIR:-/tmp}/bump-version-reasoning.md"
printf '# reasoning\n' > "$reasoning_file"
echo "CURRENT_VERSION=1.2.3"
echo "NEW_VERSION=1.2.4"
echo "BUMP_TYPE=PATCH"
echo "REASONING_FILE=$reasoning_file"
STUB
cat > "$root/.claude/skills/bump-version/scripts/apply-bump.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf '{"version":"1.2.4"}\n' > .claude-plugin/plugin.json
git add .claude-plugin/plugin.json
git commit -q -m "Bump version to 1.2.4"
echo "APPLIED=true"
echo "COMMIT_SHA=$(git rev-parse HEAD)"
STUB
chmod +x "$root/.claude/skills/bump-version/scripts/classify-bump.sh" \
         "$root/.claude/skills/bump-version/scripts/apply-bump.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-rebump-cm-noop" 2>&1)
printf '%s' "$?" > "$tmp/rc-rebump-cm-noop"
set -e
assert_rc "$tmp/rc-rebump-cm-noop" 0 "run_rebase_rebump accepts COMMITTED=false when CHANGELOG is already correct"

root=$(make_repo rebump_reasoning_fallback_log)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-rebump-fallback.XXXXXX)
write_state "$tmp/ship-pr-state.sh" ci-initial
_make_rebase_stubs "$root" "$sentinel_dir"
cat > "$root/.claude/skills/bump-version/scripts/classify-bump.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
reasoning_file="${IMPLEMENT_TMPDIR:-/tmp}/bump-version-reasoning.md"
cat > "$reasoning_file" <<'EOF'
# Version Bump Reasoning

## Result: PATCH

No structured new-version bullet here.
EOF
echo "CURRENT_VERSION=2.1.4"
echo "NEW_VERSION=2.1.5"
echo "BUMP_TYPE=PATCH"
echo "REASONING_FILE=$reasoning_file"
STUB
chmod +x "$root/.claude/skills/bump-version/scripts/classify-bump.sh"
real_git=$(command -v git)
cat > "$root/scripts/git" <<STUB
#!/usr/bin/env bash
set -euo pipefail
if [[ "\${1:-}" == "show" && "\${2:-}" == "origin/main:.claude-plugin/plugin.json" ]]; then
    printf '%s\n' '{"version":"2.3.0"}'
    exit 0
fi
exec "$real_git" "\$@"
STUB
chmod +x "$root/scripts/git"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" LARCH_LOG_STUB_SENTINEL_DIR="$sentinel_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo \
    > "$tmp/stdout-rebump-fallback" 2>&1)
printf '%s' "$?" > "$tmp/rc-rebump-fallback"
set -e
assert_rc "$tmp/rc-rebump-fallback" 0 "run_rebase_rebump writes corrected fallback reasoning when rewrite fails"
if grep -Eq -- '--input-file .*/bump-version-reasoning-corrected-[0-9]+\.md' "$sentinel_dir/larch-log-calls.txt" 2>/dev/null; then
    ok "run_rebase_rebump logs corrected fallback reasoning instead of stale classify output"
else
    fail "run_rebase_rebump should point larch-log at corrected fallback reasoning"
    sed 's/^/    larch-log: /' "$sentinel_dir/larch-log-calls.txt" 2>/dev/null || true
fi
rm -rf "$sentinel_dir"

# ──────────────────────────────────────────────────────────────────────────────
# run_evaluate_failure: inner local fix loop
# ──────────────────────────────────────────────────────────────────────────────

# Vendor retry loop: two no-change fix attempts still re-dispatch vendor, third succeeds.
root=$(make_repo ci_fix_vendor_retry)
tmp=$(make_tmpdir)
# call_dir must live under IMPLEMENT_TMPDIR ($tmp) so ship-pr resolve_checks_log_path
# accepts REDACTED_LOG_FILE paths from the checks stub (see #2288).
call_dir=$(mktemp -d "$tmp/ship-pr-vendor-retry.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/ci-wait.sh"
cat > "$root/scripts/run-relevant-checks-captured.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/checks-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -lt 4 ]; then
    log_file="$call_dir/redacted-\$count.log"
    : > "\$log_file"
    echo "STATUS=fail FAILURE_REASON=stubbed"
    echo "REDACTED_LOG_FILE=\$log_file"
    exit 1
fi
echo "RELEVANT_CHECKS_OK=true SITE=step10 COVERAGE=full"
exit 0
STUB
chmod +x "$root/scripts/run-relevant-checks-captured.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" STUB_LINT_FIX_STATUS=no-changes \
    SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo > "$tmp/stdout" 2>&1)
printf '%s' "$?" > "$tmp/rc"
set -e
assert_rc "$tmp/rc" 0 "vendor retry loop: third outer attempt can recover after two no-change passes"
launch_count=$(wc -l < "$call_dir/launcher-calls.txt" 2>/dev/null || echo 0)
if [ "$launch_count" -eq 3 ]; then
    ok "vendor retry loop: dispatched vendor fix agent once per outer attempt (3 outers, Cursor wins each tier-1)"
else
    fail "vendor retry loop: expected 3 vendor dispatches (one successful tier per outer), got $launch_count"
fi
rm -rf "$call_dir"

# Inner loop retries: first 2 local check attempts fail, 3rd succeeds -> exits 0.
root=$(make_repo ci_fix_local_retry)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d "$tmp/ship-pr-local-retry.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/ci-wait.sh"
cat > "$root/scripts/run-relevant-checks-captured.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/checks-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -lt 2 ]; then
    log_file="$call_dir/redacted-\$count.log"
    : > "\$log_file"
    echo "STATUS=fail FAILURE_REASON=stubbed"
    echo "REDACTED_LOG_FILE=\$log_file"
    exit 1
fi
echo "RELEVANT_CHECKS_OK=true SITE=step10 COVERAGE=full"
exit 0
STUB
chmod +x "$root/scripts/run-relevant-checks-captured.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" STUB_LINT_FIX_STATUS=applied \
    SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo > "$tmp/stdout" 2>&1)
printf '%s' "$?" > "$tmp/rc"
set -e
assert_rc "$tmp/rc" 0 "local fix loop: 2 failures then success exits 0"
check_count=$(cat "$call_dir/checks-count" 2>/dev/null || echo 0)
if [ "$check_count" -eq 3 ]; then
    ok "local fix loop: ran 3 local check attempts before succeeding"
else
    fail "local fix loop: expected 3 check attempts, got $check_count"
fi
if grep -qx 'ship-pr-ci-initial' "$call_dir/lint-fix-sites.txt" 2>/dev/null; then
    ok "local fix loop: initial CI failures route through ship-pr-ci-initial lint-fix-loop site"
else
    fail "local fix loop: expected ship-pr-ci-initial lint-fix-loop site"
fi
rm -rf "$call_dir"

# Vendor CI fix: ship-pr stages the full lint-fix delta, including untracked files.
root=$(make_repo ci_fix_vendor_untracked)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d /tmp/ship-pr-vendor-untracked.XXXXXX)
delta_file="$call_dir/delta-paths.txt"
cat > "$delta_file" <<'EOF'
fixture.txt
EOF
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/ci-wait.sh"
cat > "$root/scripts/run-relevant-checks-captured.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/checks-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    log_file="$tmp/redacted-\$count.log"
    : > "\$log_file"
    echo "STATUS=fail FAILURE_REASON=stubbed"
    echo "REDACTED_LOG_FILE=\$log_file"
    exit 1
fi
echo "RELEVANT_CHECKS_OK=true SITE=step10 COVERAGE=full"
exit 0
STUB
chmod +x "$root/scripts/run-relevant-checks-captured.sh"
cat > "$root/scripts/launch-cursor-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) output="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'vendor fix\n' > "${output:-/tmp/ci-fix.out}"
printf 'tracked vendor change\n' > README.md
printf 'untracked vendor fixture\n' > fixture.txt
printf 'TOKENS=1\n' > "${output}.token-record"
STUB
chmod +x "$root/scripts/launch-cursor-ci.sh"
# CI runners often lack a `cursor` binary; ship-pr falls back to launch-codex-ci.sh
# for the vendor fix path — mirror the cursor stub so dirty-tree staging is deterministic.
cp "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-codex-ci.sh"
chmod +x "$root/scripts/launch-codex-ci.sh"
cp "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-claude-ci.sh"
chmod +x "$root/scripts/launch-claude-ci.sh"
cat > "$root/scripts/git-commit.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
git diff --cached --name-only > "$call_dir/staged-before-commit.txt"
git commit -q "\$@"
STUB
chmod +x "$root/scripts/git-commit.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" STUB_LINT_FIX_STATUS=applied \
    STUB_LINT_FIX_DELTA_PATHS_FILE="$delta_file" \
    SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo > "$tmp/stdout" 2>&1)
printf '%s' "$?" > "$tmp/rc"
set -e
assert_rc "$tmp/rc" 0 "vendor CI fix: exits 0 after committing full lint-fix delta"
if grep -Fxq 'README.md' "$call_dir/staged-before-commit.txt" 2>/dev/null; then
    ok "vendor CI fix: follow-up commit preserves tracked vendor change outside lint-fix delta"
else
    fail "vendor CI fix: expected staged follow-up commit to include README.md vendor change"
fi
if grep -Fxq 'fixture.txt' "$call_dir/staged-before-commit.txt" 2>/dev/null; then
    ok "vendor CI fix: follow-up commit includes untracked fixture from lint-fix delta"
else
    fail "vendor CI fix: expected staged follow-up commit to include fixture.txt from lint-fix delta"
fi
rm -rf "$call_dir"

# Inner loop exhausted: all 5 vendor attempts fail -> stall (exits 4).
root=$(make_repo ci_fix_exhausted)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d "$tmp/ship-pr-exhausted.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<'STUB'
#!/usr/bin/env bash
printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
STUB
chmod +x "$root/scripts/ci-wait.sh"
cat > "$root/scripts/run-relevant-checks-captured.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/checks-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
log_file="$call_dir/redacted-\$count.log"
: > "\$log_file"
echo "STATUS=fail FAILURE_REASON=stubbed"
echo "REDACTED_LOG_FILE=\$log_file"
exit 1
STUB
chmod +x "$root/scripts/run-relevant-checks-captured.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" STUB_LINT_FIX_STATUS=applied \
    SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo > "$tmp/stdout" 2>&1)
printf '%s' "$?" > "$tmp/rc"
set -e
assert_rc "$tmp/rc" 4 "local fix loop: all 3 outer attempts (3 tiers each) exhausted stalls (exits 4)"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=true" "local fix loop exhausted marks stall"
check_count=$(cat "$call_dir/checks-count" 2>/dev/null || echo 0)
if [ "$check_count" -eq 12 ]; then
    ok "local fix loop exhausted: repeated the 4-check inner loop across 3 outer attempts"
else
    fail "local fix loop exhausted: expected 12 check attempts across 3 outer attempts, got $check_count"
fi
rm -rf "$call_dir"

# ── #2632: run_ci_fix_vendor 3-tier waterfall + gh-run-logs threading ───────

# Per-job argv dispatch stays aligned with ci-failed-jobs job classes.
root=$(make_repo ci_per_job_argv_table)
tmp=$(make_tmpdir)
cat > "$tmp/per-job-argv-check.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
source "$1/scripts/ship-pr.sh"
check_case() {
  local job=$1 shard=${2:-} expected=$3 actual
  _per_job_argv "$job" "$shard"
  actual="${_PJA_ARGV[*]}"
  if [[ "$actual" != "$expected" ]]; then
    printf 'argv mismatch for %s[%s]: expected <%s> got <%s>\n' "$job" "$shard" "$expected" "$actual" >&2
    exit 1
  fi
}
check_case lint "" "env SKIP=agnix,lint-mermaid-fences,shellcheck make lint-only"
check_case lint-mermaid "" "make lint-mermaid"
check_case shellcheck "" "make shellcheck"
check_case test-harnesses 7 "make test-harnesses-7"
check_case test-harnesses shard "make test-harnesses"
check_case agent-lint "" "make agent-lint"
check_case agnix "" "make agnix"
check_case smoke-dialectic "" "make smoke-dialectic"
check_case agent-sync "" "make agent-sync"
STUB
chmod +x "$tmp/per-job-argv-check.sh"
set +e
(cd "$root" && CLAUDE_PLUGIN_ROOT="$root" bash "$tmp/per-job-argv-check.sh" "$root") >"$tmp/argv.out" 2>"$tmp/argv.err"
printf '%s' "$?" >"$tmp/rc"
set -e
assert_rc "$tmp/rc" 0 "per-job argv dispatch table stays aligned with workflow jobs"

# Per-job local CI recovery: failed jobs replay locally and push without the broad vendor waterfall.
root=$(make_repo ci_per_job_happy)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d "$tmp/per-job-happy.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
  printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
  printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
cat > "$root/scripts/gh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == run && "${2:-}" == view ]]; then
  printf '%s\n' 'lint' 'test-harnesses (3)'
  exit 0
fi
exit 1
STUB
cat > "$root/scripts/run-relevant-checks-captured.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "\$*" >> "$call_dir/relevant-checks-calls.txt"
echo "RELEVANT_CHECKS_OK=true SITE=step10 COVERAGE=full"
exit 0
STUB
cat > "$root/scripts/make" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "make \$*" >> "$call_dir/make-calls.txt"
exit 0
STUB
cat > "$root/scripts/env" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "env \$*" >> "$call_dir/make-calls.txt"
shift
exec "\$@"
STUB
cat > "$root/scripts/git-push.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf 'push\n' >> "$call_dir/push-calls.txt"
STUB
for launcher in launch-cursor-ci.sh launch-codex-ci.sh launch-claude-ci.sh; do
  cat > "$root/scripts/$launcher" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$launcher" >> "$call_dir/launcher-calls.txt"
printf 'LAUNCHER_EXIT=0\n'
STUB
  chmod +x "$root/scripts/$launcher"
done
chmod +x "$root/scripts/ci-wait.sh" "$root/scripts/gh" "$root/scripts/make" "$root/scripts/env" "$root/scripts/git-push.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" CLAUDE_PLUGIN_ROOT="$root" \
  "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
  --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
printf '%s' "$?" >"$tmp/rc"
set -e
assert_rc "$tmp/rc" 0 "per-job local CI happy path exits 0"
if grep -Fq 'env SKIP=agnix,lint-mermaid-fences,shellcheck make lint-only' "$call_dir/make-calls.txt" \
    && grep -Fq 'make test-harnesses-3' "$call_dir/make-calls.txt"; then
    ok "per-job local CI happy path runs lint and test-harnesses shard locally"
else
    fail "per-job local CI happy path should run mapped local commands"
    sed 's/^/    make: /' "$call_dir/make-calls.txt" 2>/dev/null || true
fi
if [ -f "$call_dir/push-calls.txt" ] && [ ! -f "$call_dir/launcher-calls.txt" ]; then
    ok "per-job local CI happy path pushes without broad vendor launcher"
else
    fail "per-job local CI happy path should push and skip broad vendor launcher"
    sed 's/^/    launcher: /' "$call_dir/launcher-calls.txt" 2>/dev/null || true
fi
lint_runs=$(grep -c '^env SKIP=agnix,lint-mermaid-fences,shellcheck make lint-only$' "$call_dir/make-calls.txt" 2>/dev/null || echo 0)
shard_runs=$(grep -c '^make test-harnesses-3$' "$call_dir/make-calls.txt" 2>/dev/null || echo 0)
if [ "$lint_runs" = "2" ] && [ "$shard_runs" = "2" ]; then
    ok "per-job local CI happy path reruns successful jobs in Phase B verification"
else
    fail "per-job local CI happy path should rerun successful jobs in Phase B verification"
    sed 's/^/    make: /' "$call_dir/make-calls.txt" 2>/dev/null || true
fi
if grep -Fq -- '--site step10 --tmpdir' "$call_dir/relevant-checks-calls.txt"; then
    ok "per-job local CI happy path reruns relevant-checks gate before push"
else
    fail "per-job local CI happy path should rerun relevant-checks gate before push"
    sed 's/^/    checks: /' "$call_dir/relevant-checks-calls.txt" 2>/dev/null || true
fi
rm -rf "$call_dir"

# Per-job unfixable jobs bail with sanitized ci-local-unfixable reason.
root=$(make_repo ci_per_job_unfixable)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d "$tmp/per-job-unfixable.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<'STUB'
#!/usr/bin/env bash
printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
STUB
cat > "$root/scripts/gh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == run && "${2:-}" == view ]]; then
  printf '%s\n' 'gitleaks' 'lint'
  exit 0
fi
exit 1
STUB
cat > "$root/scripts/make" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "make \$*" >> "$call_dir/make-calls.txt"
exit 0
STUB
cat > "$root/scripts/env" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "env \$*" >> "$call_dir/make-calls.txt"
shift
exec "\$@"
STUB
chmod +x "$root/scripts/ci-wait.sh" "$root/scripts/gh" "$root/scripts/make" "$root/scripts/env"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" CLAUDE_PLUGIN_ROOT="$root" \
  "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
  --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
printf '%s' "$?" >"$tmp/rc"
set -e
assert_rc "$tmp/rc" 3 "per-job unfixable exits 3"
assert_state_line "$tmp/ship-pr-state.sh" "BAIL_REASON=ci-local-unfixable:gitleaks" "per-job unfixable records sanitized bail reason"
rm -rf "$call_dir"

# Per-job local fixer escalation falls back to the broad vendor waterfall instead of bailing ci-local-unfixable.
root=$(make_repo ci_per_job_main_agent_required)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d "$tmp/per-job-main-agent.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
  printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
  printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
cat > "$root/scripts/gh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == run && "${2:-}" == view ]]; then
  printf '%s\n' 'lint'
  exit 0
fi
exit 1
STUB
cat > "$root/scripts/env" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "env \$*" >> "$call_dir/make-calls.txt"
exit 1
STUB
cat > "$root/scripts/launch-cursor-ci.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' cursor >> "$call_dir/launcher-calls.txt"
printf 'LAUNCHER_EXIT=0\n'
STUB
chmod +x "$root/scripts/ci-wait.sh" "$root/scripts/gh" "$root/scripts/env" "$root/scripts/launch-cursor-ci.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" CLAUDE_PLUGIN_ROOT="$root" \
  STUB_LINT_FIX_STATUS=main-agent-required \
  "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
  --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
printf '%s' "$?" >"$tmp/rc"
set -e
assert_rc "$tmp/rc" 0 "per-job main-agent-required falls back to broad vendor recovery"
if grep -qxF 'BAIL_REASON=' "$tmp/ship-pr-state.sh"; then
    ok "per-job main-agent-required avoids ci-local-unfixable bail reason"
else
    fail "per-job main-agent-required should avoid ci-local-unfixable bail reason"
    sed 's/^/    state: /' "$tmp/ship-pr-state.sh"
fi
if grep -Fxq 'cursor' "$call_dir/launcher-calls.txt" 2>/dev/null; then
    ok "per-job main-agent-required triggers broad vendor launcher"
else
    fail "per-job main-agent-required should trigger broad vendor launcher"
    sed 's/^/    launcher: /' "$call_dir/launcher-calls.txt" 2>/dev/null || true
fi
rm -rf "$call_dir"

# Per-job local coder commit is treated as applied, pushed, and re-enters CI.
root=$(make_repo ci_per_job_head_changed)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d "$tmp/per-job-head-changed.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
  printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
  printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
cat > "$root/scripts/gh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == run && "${2:-}" == view ]]; then
  printf '%s\n' 'lint'
  exit 0
fi
exit 1
STUB
cat > "$root/scripts/env" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "env \$*" >> "$call_dir/make-calls.txt"
count_file="$call_dir/env-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
  printf 'mock lint failure\n'
  exit 1
fi
shift
exec "\$@"
STUB
cat > "$root/scripts/make" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "make \$*" >> "$call_dir/make-calls.txt"
exit 0
STUB
cat > "$root/scripts/git-push.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf 'push\n' >> "$call_dir/push-calls.txt"
STUB
chmod +x "$root/scripts/ci-wait.sh" "$root/scripts/gh" "$root/scripts/env" "$root/scripts/make" "$root/scripts/git-push.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     /^MERGE=/ {print "MERGE=false"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" CLAUDE_PLUGIN_ROOT="$root" \
  SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" \
  STUB_LINT_FIX_STATUS=applied STUB_LINT_FIX_COMMIT_SHA=abc123 STUB_LINT_FIX_HEAD_CHANGED=true \
  "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
  --merge false --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
printf '%s' "$?" >"$tmp/rc"
set -e
assert_rc "$tmp/rc" 0 "per-job coder-committed fix exits 0"
if [ -s "$call_dir/push-calls.txt" ]; then
    ok "per-job coder-committed fix pushes before CI replay"
else
    fail "per-job coder-committed fix should push before CI replay"
fi
if grep -qxF 'STALL_TRACKING=true' "$tmp/ship-pr-state.sh"; then
    fail "per-job coder-committed fix should not mark stall"
else
    ok "per-job coder-committed fix avoids stall tracking"
fi
ci_wait_calls=$(cat "$call_dir/ci-wait-count" 2>/dev/null || echo 0)
if [ "$ci_wait_calls" = "2" ]; then
    ok "per-job coder-committed fix re-enters CI monitoring"
else
    fail "per-job coder-committed fix expected two ci-wait calls, got $ci_wait_calls"
fi
if grep -Fxq 'ship-pr-ci-per-job' "$call_dir/lint-fix-sites.txt" 2>/dev/null; then
    ok "per-job coder-committed fix uses ship-pr-ci-per-job lint-fix site"
else
    fail "per-job coder-committed fix should use ship-pr-ci-per-job lint-fix site"
    sed 's/^/    site: /' "$call_dir/lint-fix-sites.txt" 2>/dev/null || true
fi
rm -rf "$call_dir"

# Per-job local head-changed failure stalls immediately with the head-changed marker.
root=$(make_repo ci_per_job_head_changed_failure)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d "$tmp/per-job-head-changed-failure.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
STUB
cat > "$root/scripts/gh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == run && "${2:-}" == view ]]; then
  printf '%s\n' 'lint'
  exit 0
fi
exit 1
STUB
cat > "$root/scripts/env" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "env \$*" >> "$call_dir/make-calls.txt"
printf 'mock lint failure\n'
exit 1
STUB
chmod +x "$root/scripts/ci-wait.sh" "$root/scripts/gh" "$root/scripts/env"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     /^MERGE=/ {print "MERGE=false"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" CLAUDE_PLUGIN_ROOT="$root" \
  SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" \
  STUB_LINT_FIX_STATUS=failed STUB_LINT_FIX_FAILURE_REASON=head-changed-after-dispatch \
  "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
  --merge false --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
printf '%s' "$?" >"$tmp/rc"
set -e
assert_rc "$tmp/rc" 4 "per-job head-changed failure stalls with rc 4"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=true" "per-job head-changed failure marks stall"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=10-head-changed" "per-job head-changed failure records 10-head-changed"
rm -rf "$call_dir"

# Verification regressions after a local replay consume the outer retry budget without dropping into vendor recovery.
root=$(make_repo ci_per_job_verify_regression)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d "$tmp/per-job-verify-regression.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
  printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
  printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
cat > "$root/scripts/gh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == run && "${2:-}" == view ]]; then
  printf '%s\n' 'lint'
  exit 0
fi
exit 1
STUB
cat > "$root/scripts/env" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/lint-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
printf '%s\n' "env \$*" >> "$call_dir/make-calls.txt"
# Alternate per outer attempt: Phase A iter 1 fails (triggers lint-fix dispatch),
# Phase A iter 2 succeeds (the "fix" applied), Phase B fails (verification regression).
if [ "\$((count % 3))" -eq 1 ]; then
  exit 0
fi
printf 'mock lint failure\n'
exit 1
STUB
cat > "$root/scripts/launch-cursor-ci.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' cursor >> "$call_dir/launcher-calls.txt"
printf 'LAUNCHER_EXIT=0\n'
STUB
chmod +x "$root/scripts/ci-wait.sh" "$root/scripts/gh" "$root/scripts/env" "$root/scripts/launch-cursor-ci.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" CLAUDE_PLUGIN_ROOT="$root" \
  SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" \
  STUB_LINT_FIX_STATUS=applied \
  "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
  --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
printf '%s' "$?" >"$tmp/rc"
set -e
assert_rc "$tmp/rc" 4 "per-job verification regression exhausts the outer retry budget"
lint_fix_calls=$(grep -c '^ship-pr-ci-per-job$' "$call_dir/lint-fix-sites.txt" 2>/dev/null || echo 0)
if [ "$lint_fix_calls" = "3" ]; then
    ok "per-job verification regression retries exactly once per outer attempt"
else
    fail "per-job verification regression should consume exactly 3 outer attempts"
    sed 's/^/    lint-fix: /' "$call_dir/lint-fix-sites.txt" 2>/dev/null || true
fi
if [ ! -f "$call_dir/launcher-calls.txt" ]; then
    ok "per-job verification regression skips vendor fallback"
else
    fail "per-job verification regression should skip vendor fallback"
    sed 's/^/    launcher: /' "$call_dir/launcher-calls.txt" 2>/dev/null || true
fi
rm -rf "$call_dir"

# Per-job push failures retry the outer attempt without falling through to a same-attempt vendor launcher.
root=$(make_repo ci_per_job_push_failure)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d "$tmp/per-job-push-failure.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=%s\nELAPSED=1\n' "\$count"
STUB
cat > "$root/scripts/gh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == run && "${2:-}" == view ]]; then
  printf '%s\n' 'lint'
  exit 0
fi
exit 1
STUB
cat > "$root/scripts/env" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "env \$*" >> "$call_dir/make-calls.txt"
exit 0
STUB
cat > "$root/scripts/git-push.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf 'push\n' >> "$call_dir/push-calls.txt"
exit 1
STUB
cat > "$root/scripts/launch-cursor-ci.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' cursor >> "$call_dir/launcher-calls.txt"
printf 'LAUNCHER_EXIT=0\n'
STUB
chmod +x "$root/scripts/ci-wait.sh" "$root/scripts/gh" "$root/scripts/env" "$root/scripts/git-push.sh" "$root/scripts/launch-cursor-ci.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" CLAUDE_PLUGIN_ROOT="$root" \
  "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
  --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
printf '%s' "$?" >"$tmp/rc"
set -e
assert_rc "$tmp/rc" 4 "per-job push failure exhausts outer retries without same-attempt vendor fallback"
if [ -f "$call_dir/launcher-calls.txt" ]; then
    launch_count=$(wc -l < "$call_dir/launcher-calls.txt" | tr -d ' ')
else
    launch_count=0
fi
if [ "${launch_count:-0}" = "0" ]; then
    ok "per-job push failure skips same-attempt vendor launcher"
else
    fail "per-job push failure should skip same-attempt vendor launcher"
    sed 's/^/    launcher: /' "$call_dir/launcher-calls.txt" 2>/dev/null || true
fi
rm -rf "$call_dir"

# 1) Cursor wins on first tier — Codex/Claude not invoked.
root=$(make_repo ci_fix_vendor_tier_order_cursor_first)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d "$tmp/call.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
  printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
  printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/ci-wait.sh"
cat > "$root/scripts/run-relevant-checks-captured.sh" <<'STUB'
#!/usr/bin/env bash
echo "RELEVANT_CHECKS_OK=true SITE=step10 COVERAGE=full"
exit 0
STUB
chmod +x "$root/scripts/run-relevant-checks-captured.sh"
cat > "$root/scripts/launch-cursor-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=cursor\nTOTAL=1\nRAW=c\nINPUT=0\nOUTPUT=0\nCACHE_READ=0\nCACHE_CREATE=0\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=0\n'
STUB
chmod +x "$root/scripts/launch-cursor-ci.sh"
cat > "$root/scripts/launch-codex-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=codex\nTOTAL=1\nRAW=x\nINPUT=0\nOUTPUT=0\nCACHE_READ=0\nCACHE_CREATE=0\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=0\n'
STUB
cat > "$root/scripts/launch-claude-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=cursor\nTOTAL=1\nRAW=x\nINPUT=0\nOUTPUT=0\nCACHE_READ=0\nCACHE_CREATE=0\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=0\n'
STUB
chmod +x "$root/scripts/launch-codex-ci.sh" "$root/scripts/launch-claude-ci.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
printf '%s' "$?" >"$tmp/rc"
set -e
assert_rc "$tmp/rc" 0 "ci_fix_vendor_tier_order_cursor_first: ship-pr exits 0"
lc=$(wc -l <"$call_dir/launcher-calls.txt" 2>/dev/null || echo 0)
if [[ "$lc" -eq 1 ]] && grep -q 'launch-cursor-ci.sh' "$call_dir/launcher-calls.txt" && ! grep -q 'launch-codex-ci.sh' "$call_dir/launcher-calls.txt" && ! grep -q 'launch-claude-ci.sh' "$call_dir/launcher-calls.txt"; then
  ok "ci_fix_vendor_tier_order_cursor_first: only Cursor tier invoked"
else
  fail "ci_fix_vendor_tier_order_cursor_first: expected single Cursor launch, got: $(cat "$call_dir/launcher-calls.txt" 2>/dev/null || true)"
fi
rm -rf "$call_dir"

# 2) Cursor LAUNCHER_EXIT=1 → Codex succeeds; Claude not invoked.
root=$(make_repo ci_fix_vendor_tier_order_falls_through_to_codex)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d "$tmp/call.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
  printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
  printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/ci-wait.sh"
cat > "$root/scripts/run-relevant-checks-captured.sh" <<'STUB'
#!/usr/bin/env bash
echo "RELEVANT_CHECKS_OK=true SITE=step10 COVERAGE=full"
exit 0
STUB
chmod +x "$root/scripts/run-relevant-checks-captured.sh"
cat > "$root/scripts/launch-cursor-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=cursor\nTOTAL=1\nRAW=c\nINPUT=0\nOUTPUT=0\nCACHE_READ=0\nCACHE_CREATE=0\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=1\n'
STUB
cat > "$root/scripts/launch-codex-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=codex\nTOTAL=1\nRAW=c\nINPUT=0\nOUTPUT=0\nCACHE_READ=0\nCACHE_CREATE=0\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=0\n'
STUB
cat > "$root/scripts/launch-claude-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'LAUNCHER_EXIT=0\n'
STUB
chmod +x "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-codex-ci.sh" "$root/scripts/launch-claude-ci.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
printf '%s' "$?" >"$tmp/rc"
set -e
assert_rc "$tmp/rc" 0 "ci_fix_vendor_tier_order_falls_through_to_codex"
if grep -q 'launch-cursor-ci.sh' "$call_dir/launcher-calls.txt" && grep -q 'launch-codex-ci.sh' "$call_dir/launcher-calls.txt" && ! grep -q 'launch-claude-ci.sh' "$call_dir/launcher-calls.txt"; then
  ok "ci_fix_vendor_tier_order_falls_through_to_codex: Cursor then Codex only"
else
  fail "ci_fix_vendor_tier_order_falls_through_to_codex: unexpected launcher order: $(cat "$call_dir/launcher-calls.txt" 2>/dev/null || true)"
fi
rm -rf "$call_dir"

# 3) Cursor and Codex LAUNCHER_EXIT=1 → Claude succeeds.
root=$(make_repo ci_fix_vendor_tier_order_falls_through_to_claude)
tmp=$(make_tmpdir)
call_dir=$(mktemp -d "$tmp/call.XXXXXX")
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$call_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
  printf 'ACTION=evaluate_failure\nCI_STATUS=fail\nBEHIND_COUNT=0\nFAILED_RUN_ID=run123\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
  printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/ci-wait.sh"
cat > "$root/scripts/run-relevant-checks-captured.sh" <<'STUB'
#!/usr/bin/env bash
echo "RELEVANT_CHECKS_OK=true SITE=step10 COVERAGE=full"
exit 0
STUB
chmod +x "$root/scripts/run-relevant-checks-captured.sh"
cat > "$root/scripts/launch-cursor-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=cursor\nTOTAL=1\nRAW=c\nINPUT=0\nOUTPUT=0\nCACHE_READ=0\nCACHE_CREATE=0\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=1\n'
STUB
cat > "$root/scripts/launch-codex-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=codex\nTOTAL=1\nRAW=c\nINPUT=0\nOUTPUT=0\nCACHE_READ=0\nCACHE_CREATE=0\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=1\n'
STUB
cat > "$root/scripts/launch-claude-ci.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output=""
if [[ -n "${SHIP_PR_LAUNCH_SENTINEL_DIR:-}" ]]; then
  mkdir -p "$SHIP_PR_LAUNCH_SENTINEL_DIR"
  printf '%s %s\n' "$(basename "$0")" "$*" >> "$SHIP_PR_LAUNCH_SENTINEL_DIR/launcher-calls.txt"
fi
while [[ $# -gt 0 ]]; do case "$1" in --output) output="$2"; shift 2 ;; *) shift ;; esac; done
printf 'TOOL=cursor\nTOTAL=1\nRAW=c\nINPUT=0\nOUTPUT=0\nCACHE_READ=0\nCACHE_CREATE=0\n' > "${output}.token-record"
printf 'LAUNCHER_EXIT=0\n'
STUB
chmod +x "$root/scripts/launch-cursor-ci.sh" "$root/scripts/launch-codex-ci.sh" "$root/scripts/launch-claude-ci.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
awk '/^TRANSIENT_RETRIES=/ {print "TRANSIENT_RETRIES=1"; next}
     /^FAILED_RUN_ID=/ {print "FAILED_RUN_ID=run123"; next}
     {print}' "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" IMPLEMENT_TMPDIR="$tmp" SHIP_PR_LAUNCH_SENTINEL_DIR="$call_dir" CLAUDE_PLUGIN_ROOT="$root" \
    "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" \
    --merge true --draft false --forked false --repo owner/repo >"$tmp/out" 2>&1)
printf '%s' "$?" >"$tmp/rc"
set -e
assert_rc "$tmp/rc" 0 "ci_fix_vendor_tier_order_falls_through_to_claude"
if grep -q 'launch-cursor-ci.sh' "$call_dir/launcher-calls.txt" && grep -q 'launch-codex-ci.sh' "$call_dir/launcher-calls.txt" && grep -q 'launch-claude-ci.sh' "$call_dir/launcher-calls.txt"; then
  ok "ci_fix_vendor_tier_order_falls_through_to_claude: all three tiers invoked in order"
else
  fail "ci_fix_vendor_tier_order_falls_through_to_claude: expected three launchers: $(cat "$call_dir/launcher-calls.txt" 2>/dev/null || true)"
fi
rm -rf "$call_dir"

# shellcheck source=scripts/test-ship-pr-fix-loop-2632.inc.sh
source "$REPO_ROOT/scripts/test-ship-pr-fix-loop-2632.inc.sh" || fail "2632 harness missing"

fi  # end section: fix-loop

if section_runs transient; then
# --- Transient-net exit-6 tests (Part C) ---

# Positive case 1: create-pr transient — stub emits a network error signature, expect exit 6.
root=$(make_repo transient_create_pr)
tmp=$(make_tmpdir)
cat > "$root/scripts/create-pr.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "ERROR: Failed to push branch: fatal: unable to access 'https://github.com/owner/repo/'" >&2
echo "ERROR: Failed to push branch: fatal: unable to access 'https://github.com/owner/repo/'"
exit 1
STUB
chmod +x "$root/scripts/create-pr.sh"
write_state "$tmp/ship-pr-state.sh" pr-create
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 6 "transient create-pr: exits 6 on network signature"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "transient create-pr: STALL_TRACKING=false"

# Positive case 1b: pre-create write-final-report transient — expect exit 6 before create-pr.
root=$(make_repo transient_precreate_final_summary)
tmp=$(make_tmpdir)
mkdir -p "$root/skills/implement/scripts"
cat > "$root/skills/implement/scripts/write-final-report.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "fatal: Could not resolve host: github.com" >&2
exit 17
STUB
chmod +x "$root/skills/implement/scripts/write-final-report.sh"
write_state "$tmp/ship-pr-state.sh" pr-create
clear_pr_state "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 6 "transient pre-create final summary: exits 6 on network signature"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "transient pre-create final summary: STALL_TRACKING=false"
if [ ! -f "$tmp/create-pr-calls.log" ]; then
    ok "transient pre-create final summary skips create-pr helper"
else
    fail "transient pre-create final summary should skip create-pr helper"
    sed 's/^/    create-pr: /' "$tmp/create-pr-calls.log" 2>/dev/null || true
fi

# Positive case 2: merge-pr transient — stub emits MERGE_RESULT=error with network signature.
root=$(make_repo transient_merge_pr)
tmp=$(make_tmpdir)
cat > "$root/scripts/merge-pr.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "MERGE_RESULT=error"
echo "ERROR=git fetch origin main failed (network/auth issue)"
STUB
chmod +x "$root/scripts/merge-pr.sh"
write_state "$tmp/ship-pr-state.sh" ci-merge
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 6 "transient merge-pr: exits 6 on network/auth signature"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "transient merge-pr: STALL_TRACKING=false"

# Positive case 2b: merge-pr transient admin_failed envelope — stub emits MERGE_RESULT=admin_failed
# with network signature. Pins the envelope-aware retry path for admin_failed alongside the
# existing MERGE_RESULT=error case so a future regression in the predicate's case statement is
# caught immediately (FINDING_12 from issue #2395 review).
root=$(make_repo transient_merge_pr_admin_failed)
tmp=$(make_tmpdir)
cat > "$root/scripts/merge-pr.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "MERGE_RESULT=admin_failed"
echo "ERROR=remote rejected admin merge: connection reset by peer"
STUB
chmod +x "$root/scripts/merge-pr.sh"
write_state "$tmp/ship-pr-state.sh" ci-merge
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 6 "transient merge-pr admin_failed: exits 6 on network/auth signature"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "transient merge-pr admin_failed: STALL_TRACKING=false"

# Positive case 3: ci-wait bail with transient network signature — expect exit 6.
root=$(make_repo transient_ci_wait_bail)
tmp=$(make_tmpdir)
cat > "$root/scripts/ci-wait.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "ACTION=bail"
echo "BAIL_REASON=ci-status.sh returned no valid output 3 times consecutively"
echo "CI_STATUS=pending"
echo "BEHIND_COUNT=0"
echo "FAILED_RUN_ID="
echo "ITERATION=0"
echo "ELAPSED=30"
STUB
chmod +x "$root/scripts/ci-wait.sh"
write_state "$tmp/ship-pr-state.sh" ci-merge
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 6 "transient ci-wait bail: exits 6 on no-valid-output-3-times signature"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "transient ci-wait bail: STALL_TRACKING=false"

# Verify poll-budget exhaustion does NOT trigger exit 6 — it's not network-transient.
root=$(make_repo non_transient_ci_timeout)
tmp=$(make_tmpdir)
cat > "$root/scripts/ci-wait.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "ACTION=bail"
echo "BAIL_REASON=Poll budget (180 polls / 1800s) exhausted"
echo "CI_STATUS=pending"
echo "BEHIND_COUNT=0"
echo "FAILED_RUN_ID="
echo "ITERATION=0"
echo "ELAPSED=1800"
STUB
chmod +x "$root/scripts/ci-wait.sh"
write_state "$tmp/ship-pr-state.sh" ci-merge
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "non-transient ci-wait timeout: exits 4 (poll budget exhaustion is not network-transient)"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=true" "non-transient ci-wait timeout: STALL_TRACKING=true"

# Positive case 4: rebase-push transient — stub emits network error, expect exit 6.
root=$(make_repo transient_rebase_push)
tmp=$(make_tmpdir)
cat > "$root/scripts/rebase-push.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "REBASE_ERROR=git fetch origin main failed (network/auth issue)" >&2
echo "REBASE_ERROR=git fetch origin main failed (network/auth issue)"
exit 3
STUB
chmod +x "$root/scripts/rebase-push.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
# Set up so ci-wait returns rebase action
cat > "$root/scripts/ci-wait.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "ACTION=rebase"
echo "CI_STATUS=pending"
echo "BEHIND_COUNT=1"
echo "FAILED_RUN_ID="
echo "BAIL_REASON="
echo "ITERATION=0"
echo "ELAPSED=0"
STUB
chmod +x "$root/scripts/ci-wait.sh"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 6 "transient rebase-push: exits 6 on network/auth signature"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "transient rebase-push: STALL_TRACKING=false"

# Negative case 1: merge-pr non-transient error — should exit 4.
root=$(make_repo non_transient_merge_pr)
tmp=$(make_tmpdir)
cat > "$root/scripts/merge-pr.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "MERGE_RESULT=error"
echo "ERROR=could not parse origin/main published version (got: corrupt)"
STUB
chmod +x "$root/scripts/merge-pr.sh"
write_state "$tmp/ship-pr-state.sh" ci-merge
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "non-transient merge-pr: exits 4 (not 6)"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=true" "non-transient merge-pr: STALL_TRACKING=true"

# Positive case: OID-mismatch merge-pr error routes to run_rebase_rebump, exits 0.
root=$(make_repo oid_mismatch_recoverable)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-oid-mismatch.XXXXXX)
write_state "$tmp/ship-pr-state.sh" ci-merge

# merge-pr.sh: first call returns OID mismatch, second call returns merged
cat > "$root/scripts/merge-pr.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$sentinel_dir/merge-pr-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    echo "MERGE_RESULT=error"
    echo "ERROR=local HEAD (abc123) does not match PR head OID (def456); refusing to evaluate same-version gate"
else
    echo "MERGE_RESULT=merged"
    echo "ERROR="
fi
STUB
chmod +x "$root/scripts/merge-pr.sh"

# ci-wait.sh: always ACTION=merge (first: merge + OID mismatch → rebump; second: merge + merged).
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$sentinel_dir/ci-wait-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
echo "ACTION=merge"
echo "CI_STATUS=pass"
echo "BEHIND_COUNT=0"
echo "FAILED_RUN_ID="
echo "BAIL_REASON="
echo "ITERATION=1"
echo "ELAPSED=0"
STUB
chmod +x "$root/scripts/ci-wait.sh"

_install_rebump_dep_stubs "$root"
real_git=$(command -v git)
cat > "$root/scripts/git" <<STUB
#!/usr/bin/env bash
set -euo pipefail
if [[ "\${1:-}" == "rev-parse" && "\${2:-}" == "HEAD" ]]; then
    printf '%s\n' 'abc123'
    exit 0
fi
if [[ "\${1:-}" == "merge-base" && "\${2:-}" == "--is-ancestor" && "\${3:-}" == "def456" && "\${4:-}" == "abc123" ]]; then
    exit 0
fi
exec "$real_git" "\$@"
STUB
chmod +x "$root/scripts/git"

set +e
(cd "$root" && PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" IMPLEMENT_TMPDIR="$tmp" "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" --merge true --draft false --forked false --repo owner/repo > "$tmp/stdout" 2> "$tmp/stderr")
printf '%s' "$?" > "$tmp/rc"
set -e
assert_rc "$tmp/rc" 0 "oid-mismatch merge-pr error: exits 0 via run_rebase_rebump"
assert_state_line "$tmp/ship-pr-state.sh" "PHASE=done" "oid-mismatch merge-pr error: PHASE=done after recovery"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "oid-mismatch merge-pr error: STALL_TRACKING=false (no 12d stall)"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=" "oid-mismatch merge-pr error: STALL_STEP cleared"
if [ "$(cat "$sentinel_dir/ci-wait-count" 2>/dev/null || echo 0)" -ge 2 ]; then
    ok "oid-mismatch merge-pr error: ci-wait.sh called at least twice"
else
    fail "oid-mismatch merge-pr error: ci-wait.sh should be called at least twice"
    cat "$sentinel_dir/ci-wait-count" 2>/dev/null || true
fi
if [ "$(cat "$sentinel_dir/merge-pr-count" 2>/dev/null || echo 0)" -ge 2 ]; then
    ok "oid-mismatch merge-pr error: merge-pr.sh called at least twice (rebase then retry)"
else
    fail "oid-mismatch merge-pr error: merge-pr.sh should be called at least twice"
    cat "$sentinel_dir/merge-pr-count" 2>/dev/null || true
fi
if [ ! -e "$tmp/execution-issues.md" ] || ! grep -Fq "merge-pr.sh envelope" "$tmp/execution-issues.md"; then
    ok "oid-mismatch recoverable error: skips merge-pr envelope failure log"
else
    fail "oid-mismatch recoverable error: should not log merge-pr envelope failure"
    sed 's/^/    execution-issues: /' "$tmp/execution-issues.md" 2>/dev/null || true
fi
rm -rf "$sentinel_dir"

# Negative case 1b: OID-mismatch where local HEAD is not ahead of the PR head
# should stall instead of rebasing/retrying.
root=$(make_repo oid_mismatch_non_ancestor)
tmp=$(make_tmpdir)
sentinel_dir=$(mktemp -d /tmp/ship-pr-oid-non-ancestor.XXXXXX)
write_state "$tmp/ship-pr-state.sh" ci-merge
cat > "$root/scripts/merge-pr.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$sentinel_dir/merge-pr-count"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
echo "MERGE_RESULT=error"
echo "ERROR=local HEAD (abc123) does not match PR head OID (def456); refusing to evaluate same-version gate"
STUB
chmod +x "$root/scripts/merge-pr.sh"
real_git=$(command -v git)
cat > "$root/scripts/git" <<STUB
#!/usr/bin/env bash
set -euo pipefail
if [[ "\${1:-}" == "rev-parse" && "\${2:-}" == "HEAD" ]]; then
    printf '%s\n' 'abc123'
    exit 0
fi
if [[ "\${1:-}" == "merge-base" && "\${2:-}" == "--is-ancestor" && "\${3:-}" == "def456" && "\${4:-}" == "abc123" ]]; then
    exit 1
fi
exec "$real_git" "\$@"
STUB
chmod +x "$root/scripts/git"
set +e
(cd "$root" && PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" IMPLEMENT_TMPDIR="$tmp" "$root/scripts/ship-pr.sh" --state-file "$tmp/ship-pr-state.sh" --implement-tmpdir "$tmp" --merge true --draft false --forked false --repo owner/repo > "$tmp/stdout" 2> "$tmp/stderr")
printf '%s' "$?" > "$tmp/rc"
set -e
assert_rc "$tmp/rc" 4 "oid-mismatch non-ancestor error: exits 4"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=true" "oid-mismatch non-ancestor error: STALL_TRACKING=true"
if [ "$(cat "$sentinel_dir/merge-pr-count" 2>/dev/null || echo 0)" = "1" ]; then
    ok "oid-mismatch non-ancestor error: does not retry merge-pr"
else
    fail "oid-mismatch non-ancestor error: should not retry merge-pr"
    cat "$sentinel_dir/merge-pr-count" 2>/dev/null || true
fi
rm -rf "$sentinel_dir"

# Negative case 2: create-pr non-transient error — should exit 4.
root=$(make_repo non_transient_create_pr)
tmp=$(make_tmpdir)
cat > "$root/scripts/create-pr.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "ERROR: Body file not found: /tmp/pr-body.md"
exit 1
STUB
chmod +x "$root/scripts/create-pr.sh"
write_state "$tmp/ship-pr-state.sh" pr-create
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "non-transient create-pr: exits 4 (not 6)"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=true" "non-transient create-pr: STALL_TRACKING=true"
assert_state_line "$tmp/execution-issues.md" "### Tool Failures" "non-transient create-pr: execution issue category logged"
if grep -Fq "Body file not found: /tmp/pr-body.md" "$tmp/execution-issues.md"; then
    ok "non-transient create-pr: captured stderr logged verbatim"
else
    fail "non-transient create-pr: captured stderr logged verbatim"
    sed 's/^/    /' "$tmp/execution-issues.md" 2>/dev/null || true
fi

# Issue #2233: MANIFEST_PATH entry validation contract tests.
# Confirms ship-pr.sh fails fast when MANIFEST_PATH points at a non-JSON file
# (e.g. the /design Step 5 manifest.env shell KV file mistakenly routed here),
# and accepts a valid JSON manifest.
root=$(make_repo manifest_path_non_json)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
# Simulate the failure mode: a shell KEY=VALUE file (design-side manifest.env)
# written into MANIFEST_PATH instead of the implement-side JSON manifest.
cat > "$tmp/fake-design-manifest.env" <<'KV'
PLAN_FILE=/tmp/x
TIMESTAMP=2026-05-17
SESSION_ID=abc
KV
sed -i.bak "s|^MANIFEST_PATH=.*|MANIFEST_PATH=$tmp/fake-design-manifest.env|" "$tmp/ship-pr-state.sh"
rm -f "$tmp/ship-pr-state.sh.bak"
run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 2 "non-JSON MANIFEST_PATH: ship-pr.sh exits 2 (die_usage) at entry"
if grep -q "MANIFEST_PATH must be empty or a readable JSON file" "$tmp/stderr"; then
    ok "non-JSON MANIFEST_PATH: diagnostic names the offending key"
else
    fail "non-JSON MANIFEST_PATH: diagnostic names the offending key"
    sed 's/^/    stderr: /' "$tmp/stderr"
fi

root=$(make_repo manifest_path_valid_json)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
printf '{"summary_bullets":["x"],"files_modified":[]}\n' > "$tmp/fake-implement-manifest.json"
sed -i.bak "s|^MANIFEST_PATH=.*|MANIFEST_PATH=$tmp/fake-implement-manifest.json|" "$tmp/ship-pr-state.sh"
rm -f "$tmp/ship-pr-state.sh.bak"
run_subject "$root" "$tmp" "$tmp/rc"
if grep -q "MANIFEST_PATH must be empty or a readable JSON file" "$tmp/stderr"; then
    fail "valid JSON MANIFEST_PATH: entry validation must not fire"
    sed 's/^/    stderr: /' "$tmp/stderr"
else
    ok "valid JSON MANIFEST_PATH: entry validation does not fire"
fi

root=$(make_repo manifest_path_empty)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" checks
# write_state already sets MANIFEST_PATH= empty; just confirm the empty path passes.
run_subject "$root" "$tmp" "$tmp/rc"
if grep -q "MANIFEST_PATH must be empty or a readable JSON file" "$tmp/stderr"; then
    fail "empty MANIFEST_PATH: entry validation must not fire"
    sed 's/^/    stderr: /' "$tmp/stderr"
else
    ok "empty MANIFEST_PATH: entry validation does not fire"
fi

# Regression: REPO_UNAVAILABLE skip-path clears stale stall keys before advancing to postmerge.
# Prior to the fix, clear_stall_keys_for_postmerge() was missing, so stale BAIL_REASON/
# STALL_TRACKING/STALL_STEP from an earlier ci-merge stall propagated into finalize-state.sh
# and caused implement-finalize.sh postmerge to skip local branch cleanup.
root=$(make_repo stale_stall_cleared_on_repo_unavailable_skip)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-merge
seed_stale_stall_state "$tmp/ship-pr-state.sh"
awk -F= '{if ($1=="REPO_UNAVAILABLE") print "REPO_UNAVAILABLE=true"; else print}' \
    "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc" --resume-phase ci-merge
assert_rc "$tmp/rc" 0 "stale stall state: REPO_UNAVAILABLE skip-path exits 0"
assert_state_line "$tmp/ship-pr-state.sh" "PHASE=done" "stale stall state: REPO_UNAVAILABLE skip-path reaches PHASE=done"
assert_state_line "$tmp/ship-pr-state.sh" "BAIL_REASON=" "stale stall state: REPO_UNAVAILABLE skip-path clears BAIL_REASON"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "stale stall state: REPO_UNAVAILABLE skip-path clears STALL_TRACKING"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=" "stale stall state: REPO_UNAVAILABLE skip-path clears STALL_STEP"
assert_file_absent_or_empty "$tmp/final-bail-reason.txt" "stale stall state: REPO_UNAVAILABLE skip-path leaves final-bail-reason.txt empty"

# Regression: skip-merge guard clears stale stall keys before advancing to postmerge.
root=$(make_repo stale_stall_cleared_on_skip_merge_guard)
tmp=$(make_tmpdir)
write_state "$tmp/ship-pr-state.sh" ci-merge
seed_stale_stall_state "$tmp/ship-pr-state.sh"
awk -F= '{if ($1=="MERGE") print "MERGE=false"; else print}' \
    "$tmp/ship-pr-state.sh" > "$tmp/ship-pr-state.sh.new" \
    && mv "$tmp/ship-pr-state.sh.new" "$tmp/ship-pr-state.sh"
run_subject "$root" "$tmp" "$tmp/rc" --resume-phase ci-merge
assert_rc "$tmp/rc" 0 "stale stall state: skip-merge guard exits 0"
assert_state_line "$tmp/ship-pr-state.sh" "PHASE=done" "stale stall state: skip-merge guard reaches PHASE=done"
assert_state_line "$tmp/ship-pr-state.sh" "BAIL_REASON=" "stale stall state: skip-merge guard clears BAIL_REASON"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_TRACKING=false" "stale stall state: skip-merge guard clears STALL_TRACKING"
assert_state_line "$tmp/ship-pr-state.sh" "STALL_STEP=" "stale stall state: skip-merge guard clears STALL_STEP"
assert_file_absent_or_empty "$tmp/final-bail-reason.txt" "stale stall state: skip-merge guard leaves final-bail-reason.txt empty"
fi  # end section: transient

if section_runs phase14; then
# run_rebase_rebump: non-bump-only conflict → exit_stall (rc 4) after recovery waterfall exhausts.
root=$(make_repo ship_pr_phase14_dispatch)
tmp=$(make_tmpdir)
cat > "$root/scripts/rebase-push.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
    *--keep-on-conflict*)
        printf 'CONFLICT_FILES=Makefile\n'
        exit 1
        ;;
    *)
        exit 0
        ;;
esac
STUB
chmod +x "$root/scripts/rebase-push.sh"
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf 'ACTION=rebase\nCI_STATUS=fail\nBEHIND_COUNT=1\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
STUB
chmod +x "$root/scripts/ci-wait.sh"
_install_rebump_dep_stubs "$root"
write_state "$tmp/ship-pr-state.sh" ci-initial
: >"$tmp/execution-issues.md"
PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" IMPLEMENT_TMPDIR="$tmp" \
    run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "Makefile-only rebase conflict: ship-pr stalls after waterfall (exit_stall, rc 4)"
if grep -qFx 'CONFLICT_FILES=Makefile' "$tmp/stdout"; then
    ok "phase14 dispatch stall stream includes CONFLICT_FILES=Makefile"
else
    fail "phase14 dispatch stall stream missing CONFLICT_FILES=Makefile"
    sed 's/^/    stdout: /' "$tmp/stdout" | head -n 40
fi
if [[ -f "$tmp/ship-pr-rrr-after-phase14.flag" ]]; then
    ok "phase14 dispatch creates resume flag under IMPLEMENT_TMPDIR"
else
    fail "expected ship-pr-rrr-after-phase14.flag after stall (rc 4)"
fi
assert_state_line "$tmp/ship-pr-state.sh" "RESUME_PHASE=ship-pr-rrr-phase14" "phase14 dispatch persists RESUME_PHASE"
assert_state_line "$tmp/ship-pr-state.sh" "CALLER_KIND=ship_pr_pre_push" "phase14 dispatch persists CALLER_KIND"
if grep -qF 'aggregator-dispatch=conflict-resolution.md' "$tmp/stdout"; then
    ok "phase14 dispatch breadcrumb mentions aggregator-dispatch/conflict-resolution"
else
    fail "stdout missing phase14 aggregator-dispatch breadcrumb"
    sed 's/^/    stdout: /' "$tmp/stdout" | head -n 20
fi
if grep -qF 'rebase-push.sh --keep-on-conflict' "$tmp/execution-issues.md" 2>/dev/null; then
    fail "phase14 handoff must not record keep-on-conflict rebase failure before resolution"
else
    ok "phase14 handoff skips premature keep-on-conflict execution-issues line"
fi

# Deep non-bump CONFLICT_FILES CSV (nested path) still reaches exit_stall with the same state keys.
root=$(make_repo ship_pr_phase14_dispatch_deep_csv)
tmp=$(make_tmpdir)
cat > "$root/scripts/rebase-push.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
    *--keep-on-conflict*)
        printf 'CONFLICT_FILES=.claude/skills/audit-runs/scripts/test-audit-runs.md,docs/README.md\n'
        exit 1
        ;;
    *)
        exit 0
        ;;
esac
STUB
chmod +x "$root/scripts/rebase-push.sh"
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf 'ACTION=rebase\nCI_STATUS=fail\nBEHIND_COUNT=1\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
STUB
chmod +x "$root/scripts/ci-wait.sh"
_install_rebump_dep_stubs "$root"
write_state "$tmp/ship-pr-state.sh" ci-initial
: >"$tmp/execution-issues.md"
PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" IMPLEMENT_TMPDIR="$tmp" \
    run_subject "$root" "$tmp" "$tmp/rc"
assert_rc "$tmp/rc" 4 "phase14 deep CSV: ship-pr stalls after waterfall (rc 4)"
if grep -qFx 'CONFLICT_FILES=.claude/skills/audit-runs/scripts/test-audit-runs.md,docs/README.md' "$tmp/stdout"; then
    ok "phase14 deep CSV exit-5 stream includes post–pre-pass CONFLICT_FILES CSV"
else
    fail "phase14 deep CSV exit-5 stream missing expected CONFLICT_FILES= line"
    sed 's/^/    stdout: /' "$tmp/stdout" | head -n 40
fi
if [[ -f "$tmp/ship-pr-rrr-after-phase14.flag" ]]; then
    ok "phase14 deep CSV creates resume flag under IMPLEMENT_TMPDIR"
else
    fail "expected ship-pr-rrr-after-phase14.flag after stall (deep CSV)"
fi
assert_state_line "$tmp/ship-pr-state.sh" "RESUME_PHASE=ship-pr-rrr-phase14" "phase14 deep CSV persists RESUME_PHASE"
assert_state_line "$tmp/ship-pr-state.sh" "CALLER_KIND=ship_pr_pre_push" "phase14 deep CSV persists CALLER_KIND"
if grep -qF 'aggregator-dispatch=conflict-resolution.md' "$tmp/stdout"; then
    ok "phase14 deep CSV stdout mentions aggregator-dispatch/conflict-resolution"
else
    fail "phase14 deep CSV stdout missing aggregator-dispatch breadcrumb"
    sed 's/^/    stdout: /' "$tmp/stdout" | head -n 20
fi
if grep -qF 'rebase-push.sh --keep-on-conflict' "$tmp/execution-issues.md" 2>/dev/null; then
    fail "phase14 deep CSV must not record keep-on-conflict execution-issues line before resolution"
else
    ok "phase14 deep CSV skips premature keep-on-conflict execution-issues line"
fi

# Punctuation-heavy CSV remainder survives into exit_stall CONFLICT_FILES contract line.
root=$(make_repo ship_pr_phase14_dispatch_edge_csv)
tmp=$(make_tmpdir)
cat > "$root/scripts/rebase-push.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
    *--keep-on-conflict*)
        printf 'CONFLICT_FILES=Makefile,  README.md\n'
        exit 1
        ;;
    *)
        exit 0
        ;;
esac
STUB
chmod +x "$root/scripts/rebase-push.sh"
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf 'ACTION=rebase\nCI_STATUS=fail\nBEHIND_COUNT=1\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
STUB
chmod +x "$root/scripts/ci-wait.sh"
_install_rebump_dep_stubs "$root"
write_state "$tmp/ship-pr-state.sh" ci-initial
: >"$tmp/execution-issues.md"
PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" IMPLEMENT_TMPDIR="$tmp" \
    run_subject "$root" "$tmp" "$tmp/rc-edge"
assert_rc "$tmp/rc-edge" 4 "phase14 edge CSV: ship-pr stalls after waterfall (rc 4)"
if grep -qFx 'CONFLICT_FILES=Makefile,  README.md' "$tmp/stdout"; then
    ok "phase14 edge CSV stall stream preserves comma-spacing in CONFLICT_FILES"
else
    fail "phase14 edge CSV stall stream missing expected CONFLICT_FILES= line"
    sed 's/^/    stdout: /' "$tmp/stdout" | head -n 40
fi

# LARCH_BUMP_FILES membership: bump-tagged path must not take the Phase14 exit_stall gate.
root=$(make_repo ship_pr_phase14_larch_bump_files_gate)
tmp=$(make_tmpdir)
mkdir -p "$root/vendor"
printf 'b\n' >"$root/vendor/bump-owned.md"
git -C "$root" add vendor/bump-owned.md
git -C "$root" commit -q -m vendor-bump-owned
cat > "$root/scripts/rebase-push.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
    *--keep-on-conflict*)
        printf 'CONFLICT_FILES=vendor/bump-owned.md\n'
        exit 1
        ;;
    *)
        exit 0
        ;;
esac
STUB
chmod +x "$root/scripts/rebase-push.sh"
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
printf 'ACTION=rebase\nCI_STATUS=fail\nBEHIND_COUNT=1\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
STUB
chmod +x "$root/scripts/ci-wait.sh"
_install_rebump_dep_stubs "$root"
write_state "$tmp/ship-pr-state.sh" ci-initial
: >"$tmp/execution-issues.md"
PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" IMPLEMENT_TMPDIR="$tmp" \
    LARCH_BUMP_FILES=vendor/bump-owned.md \
    run_subject "$root" "$tmp" "$tmp/rc-bumpgate"
actual_bumpgate=$(cat "$tmp/rc-bumpgate")
if [[ "$actual_bumpgate" != 5 ]]; then
    ok "LARCH_BUMP_FILES gate: ship-pr does not use legacy exit 5 when bump-owned path remains (rc=$actual_bumpgate)"
else
    fail "LARCH_BUMP_FILES gate: expected non-5 rc when LARCH_BUMP_FILES marks the conflict path"
fi
if [[ ! -f "$tmp/ship-pr-rrr-after-phase14.flag" ]]; then
    ok "LARCH_BUMP_FILES gate: no ship-pr-rrr-after-phase14.flag"
else
    fail "LARCH_BUMP_FILES gate: unexpected Phase14 resume flag"
fi

# ci-merge + ship-pr-rrr-phase14 resume (PHASE=ci-merge at handoff).
root=$(make_repo ship_pr_phase14_resume_ci_merge)
tmp=$(make_tmpdir)
cat > "$root/scripts/rebase-push.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
    *--keep-on-conflict*)
        printf 'CONFLICT_FILES=Makefile\n'
        exit 1
        ;;
    *)
        exit 0
        ;;
esac
STUB
chmod +x "$root/scripts/rebase-push.sh"
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$tmp/ci-wait-phase14-ci-merge.seq"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=rebase\nCI_STATUS=fail\nBEHIND_COUNT=1\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/ci-wait.sh"
_install_rebump_dep_stubs "$root"
write_state "$tmp/ship-pr-state.sh" ci-merge
: >"$tmp/execution-issues.md"
rm -f "$tmp/ci-wait-phase14-ci-merge.seq"
PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" IMPLEMENT_TMPDIR="$tmp" \
    run_subject "$root" "$tmp" "$tmp/rc-cm-first"
assert_rc "$tmp/rc-cm-first" 4 "phase14 ci-merge first leg stalls after waterfall (rc 4)"
if grep -qFx 'CONFLICT_FILES=Makefile' "$tmp/stdout"; then
    ok "phase14 ci-merge handoff emits CONFLICT_FILES contract line"
else
    fail "phase14 ci-merge handoff missing CONFLICT_FILES=Makefile on stdout"
    sed 's/^/    stdout: /' "$tmp/stdout" | head -n 40
fi
PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" IMPLEMENT_TMPDIR="$tmp" \
    run_subject "$root" "$tmp" "$tmp/rc-cm-second" --resume-phase ship-pr-rrr-phase14
assert_rc "$tmp/rc-cm-second" 0 "phase14 ci-merge resume completes after run_rebase_rebump tail"

# Resume path: run_rebase_rebump continues after orchestrator-simulated Phase 4 success.
root=$(make_repo ship_pr_phase14_resume)
tmp=$(make_tmpdir)
cat > "$root/scripts/rebase-push.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
    *--keep-on-conflict*)
        printf 'CONFLICT_FILES=Makefile\n'
        exit 1
        ;;
    *)
        exit 0
        ;;
esac
STUB
chmod +x "$root/scripts/rebase-push.sh"
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$tmp/ci-wait-phase14.seq"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=rebase\nCI_STATUS=fail\nBEHIND_COUNT=1\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/ci-wait.sh"
_install_rebump_dep_stubs "$root"
write_state "$tmp/ship-pr-state.sh" ci-initial
rm -f "$tmp/ci-wait-phase14.seq"
PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" IMPLEMENT_TMPDIR="$tmp" \
    run_subject "$root" "$tmp" "$tmp/rc-first"
assert_rc "$tmp/rc-first" 4 "phase14 resume prep: first ship-pr stalls after waterfall (rc 4)"
if grep -qFx 'CONFLICT_FILES=Makefile' "$tmp/stdout"; then
    ok "phase14 resume first leg emits CONFLICT_FILES contract line"
else
    fail "phase14 resume first leg missing CONFLICT_FILES=Makefile on stdout"
    sed 's/^/    stdout: /' "$tmp/stdout" | head -n 40
fi
PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" IMPLEMENT_TMPDIR="$tmp" \
    run_subject "$root" "$tmp" "$tmp/rc-second" --resume-phase ship-pr-rrr-phase14
assert_rc "$tmp/rc-second" 0 "phase14 resume: second ship-pr completes after run_rebase_rebump tail"
if [[ ! -f "$tmp/ship-pr-rrr-after-phase14.flag" ]]; then
    ok "phase14 resume consumes the flag file"
else
    fail "resume flag should be removed after successful run_rebase_rebump"
fi

# phase14 resume with real commit-changelog.sh: verifies separate bump+CHANGELOG commit shape
# after resume (acceptance criterion #5 for issue #2852).
root=$(make_repo ship_pr_phase14_changelog_shape)
tmp=$(make_tmpdir)
# Seed bump+CHANGELOG history on the feature branch.
mkdir -p "$root/.claude-plugin"
cat > "$root/.claude-plugin/plugin.json" <<'JSON'
{"version":"1.2.2"}
JSON
cat > "$root/CHANGELOG.md" <<'CHANGELOG'
# Changelog

## [1.2.2] - 2025-12-31

### Fixed

- Previous release.
CHANGELOG
git -C "$root" add .claude-plugin/plugin.json CHANGELOG.md
git -C "$root" commit -q -m "Prepare version fixtures"
cat > "$root/.claude-plugin/plugin.json" <<'JSON'
{"version":"1.2.3"}
JSON
git -C "$root" add .claude-plugin/plugin.json
git -C "$root" commit -q -m "Bump version to 1.2.3"
cat > "$root/CHANGELOG.md" <<'CHANGELOG'
# Changelog

## [1.2.3] - 2026-01-01

### Fixed

- Feature change.

## [1.2.2] - 2025-12-31

### Fixed

- Previous release.
CHANGELOG
git -C "$root" add CHANGELOG.md
git -C "$root" commit -q -m "Update CHANGELOG for 1.2.3"
# Install real helpers for the bump commit shape path.
_install_rebump_dep_stubs "$root"
cp "$REPO_ROOT/scripts/drop-bump-commit.sh" "$root/scripts/drop-bump-commit.sh"
cp "$REPO_ROOT/scripts/commit-changelog.sh" "$root/scripts/commit-changelog.sh"
cp "$REPO_ROOT/scripts/git-commit.sh" "$root/scripts/git-commit.sh"
chmod +x "$root/scripts/drop-bump-commit.sh" "$root/scripts/commit-changelog.sh" "$root/scripts/git-commit.sh"
# Stub classify-bump and apply-bump to produce deterministic fresh commits.
mkdir -p "$root/.claude/skills/bump-version/scripts"
cat > "$root/.claude/skills/bump-version/scripts/classify-bump.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
reasoning_file="${IMPLEMENT_TMPDIR:-/tmp}/bump-version-reasoning.md"
printf '# reasoning\n' > "$reasoning_file"
echo "CURRENT_VERSION=1.2.3"
echo "NEW_VERSION=1.2.4"
echo "BUMP_TYPE=PATCH"
echo "REASONING_FILE=$reasoning_file"
STUB
cat > "$root/.claude/skills/bump-version/scripts/apply-bump.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
new_version=""
while [ "$#" -gt 0 ]; do
  case "$1" in --new-version) new_version=$2; shift 2 ;; *) shift ;; esac
done
printf '{"version":"%s"}\n' "$new_version" > .claude-plugin/plugin.json
git add .claude-plugin/plugin.json
git commit -q -m "Bump version to $new_version"
echo "APPLIED=true"
echo "COMMIT_SHA=$(git rev-parse HEAD)"
STUB
chmod +x "$root/.claude/skills/bump-version/scripts/classify-bump.sh" \
         "$root/.claude/skills/bump-version/scripts/apply-bump.sh"
# Stubs for rebase and CI sequencing.
cat > "$root/scripts/rebase-push.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in *--keep-on-conflict*) printf 'CONFLICT_FILES=Makefile\n'; exit 1 ;; *) exit 0 ;; esac
STUB
chmod +x "$root/scripts/rebase-push.sh"
cat > "$root/scripts/git-sync-local-main.sh" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$root/scripts/git-sync-local-main.sh"
cat > "$root/scripts/refresh-run-logs.sh" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$root/scripts/refresh-run-logs.sh"
cat > "$root/scripts/ci-wait.sh" <<STUB
#!/usr/bin/env bash
set -euo pipefail
count_file="$tmp/ci-wait-phase14-changelog-shape.seq"
count=\$(cat "\$count_file" 2>/dev/null || echo 0)
printf '%s\n' "\$((count + 1))" > "\$count_file"
if [ "\$count" -eq 0 ]; then
    printf 'ACTION=rebase\nCI_STATUS=fail\nBEHIND_COUNT=1\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=0\nELAPSED=1\n'
else
    printf 'ACTION=merge\nCI_STATUS=pass\nBEHIND_COUNT=0\nFAILED_RUN_ID=\nBAIL_REASON=\nITERATION=1\nELAPSED=1\n'
fi
STUB
chmod +x "$root/scripts/ci-wait.sh"
write_state "$tmp/ship-pr-state.sh" ci-initial
: >"$tmp/execution-issues.md"
rm -f "$tmp/ci-wait-phase14-changelog-shape.seq"
PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" IMPLEMENT_TMPDIR="$tmp" \
    run_subject "$root" "$tmp" "$tmp/rc-cls-first"
assert_rc "$tmp/rc-cls-first" 4 "phase14 changelog-shape: first leg stalls (rc 4)"
PATH="$root/scripts:$PATH" CLAUDE_PLUGIN_ROOT="$root" IMPLEMENT_TMPDIR="$tmp" \
    run_subject "$root" "$tmp" "$tmp/rc-cls-second" --resume-phase ship-pr-rrr-phase14
assert_rc "$tmp/rc-cls-second" 0 "phase14 changelog-shape: resume leg exits 0"
cls_subjects=$(git -C "$root" log --format=%s)
if [[ "$cls_subjects"$'\n' == *$'Bump version to 1.2.4\n'* ]] &&
   [[ "$cls_subjects"$'\n' == *$'Update CHANGELOG for 1.2.4\n'* ]] &&
   ! grep -q '^## \[1.2.3\] - ' "$root/CHANGELOG.md" &&
   grep -q '^## \[1.2.4\] - ' "$root/CHANGELOG.md"; then
    ok "phase14 changelog-shape: fresh bump+CHANGELOG commits after resume, stale entry removed"
else
    fail "phase14 changelog-shape: missing fresh bump or CHANGELOG entry after resume"
    git -C "$root" log --oneline --max-count=8 | sed 's/^/    log: /' || true
    sed 's/^/    changelog: /' "$root/CHANGELOG.md" | head -n 20 || true
fi

fi  # end section: phase14

if [[ "$FAIL_COUNT" -ne 0 ]]; then
    echo "test-ship-pr: $FAIL_COUNT failure(s), $PASS_COUNT pass(es)" >&2
    exit 1
fi
echo "test-ship-pr: $PASS_COUNT pass(es)"
