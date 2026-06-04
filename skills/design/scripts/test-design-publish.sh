#!/usr/bin/env bash
# Offline harness for design-publish.sh
set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUBJECT="$SCRIPT_DIR/design-publish.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

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

assert_rc() {
    local name="$1" want="$2" got="$3"
    if [[ "$got" != "$want" ]]; then
        fail "$name — expected exit $want, got $got"
        return 1
    fi
    pass "$name"
}

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-design-publish.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

FAKE_PLUGIN="$TMP/plugin"
STUB="$FAKE_PLUGIN/scripts"
mkdir -p "$STUB" "$FAKE_PLUGIN/skills/design/scripts"
ln -sf "$REPO_ROOT/scripts/lib-quiet.sh" "$STUB/lib-quiet.sh"
ln -sf "$REPO_ROOT/scripts/lib-net.sh" "$STUB/lib-net.sh" 2>/dev/null || true
ln -sf "$REPO_ROOT/scripts/append-tool-failure.sh" "$STUB/append-tool-failure.sh"
ln -sf "$REPO_ROOT/scripts/append-execution-issue.sh" "$STUB/append-execution-issue.sh"
ln -sf "$REPO_ROOT/scripts/redact-secrets.sh" "$STUB/redact-secrets.sh"
write_reentry_guard_wrapper() {
    cat >"$STUB/lib-design-reentry-guard.sh" <<WRAP
# shellcheck shell=bash
# shellcheck source=scripts/lib-design-reentry-guard.sh
source "$REPO_ROOT/scripts/lib-design-reentry-guard.sh"
__larch_orig_design_reentry_marker_write=\$(declare -f design_reentry_marker_write)
eval "\${__larch_orig_design_reentry_marker_write/design_reentry_marker_write/__larch_design_reentry_marker_write}"
design_reentry_marker_write() {
    [[ -n "\${CALL_LOG:-}" ]] && echo "design-reentry-marker-write \$*" >>"\$CALL_LOG"
    if [[ "\${MARKER_STUB_RC:-0}" -ne 0 ]]; then
        return "\${MARKER_STUB_RC}"
    fi
    __larch_design_reentry_marker_write "\$@"
}
WRAP
}
write_reentry_guard_wrapper
ln -sf "$SCRIPT_DIR/lib-phase-driver.sh" "$FAKE_PLUGIN/skills/design/scripts/lib-phase-driver.sh"

setup_design_tmp() {
    local d="$1"
    mkdir -p "$d/.completed"
    : >"$d/.completed/step-5b"
    printf '# plan\n' >"$d/composed-plan.redacted.md"
    printf '{"design_classification":"SIMPLE"}\n' >"$d/run-params.json"
    printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$FAKE_PLUGIN" >"$d/session-env.sh"
}

write_stubs() {
    cat >"$STUB/plan-block-write.sh" <<'STUB'
#!/usr/bin/env bash
echo "plan-block-write $*" >>"${PLAN_BLOCK_LOG:?}"
[[ -n "${CALL_LOG:-}" ]] && echo "plan-block-write $*" >>"$CALL_LOG"
exit "${PLAN_BLOCK_RC:-0}"
STUB
    cat >"$STUB/design-log-publish.sh" <<'STUB'
#!/usr/bin/env bash
echo "design-log-publish $*" >>"${PUBLISH_LOG:?}"
[[ -n "${CALL_LOG:-}" ]] && echo "design-log-publish $*" >>"$CALL_LOG"
if [[ "${PUBLISH_STUB_RC:-0}" -ne 0 ]]; then
  exit "${PUBLISH_STUB_RC}"
fi
if [[ "${PUBLISH_EMIT_OK:-true}" == true ]]; then
  echo "PUBLISH_OK=${PUBLISH_OK_VALUE:-true}"
fi
[[ -n "${PUBLISH_PR_NUMBER:-}" ]] && echo "PR_NUMBER=${PUBLISH_PR_NUMBER}"
[[ -n "${PUBLISH_PR_URL:-}" ]] && echo "PR_URL=${PUBLISH_PR_URL}"
[[ -n "${PUBLISH_RECOVERY_BRANCH:-}" ]] && echo "RECOVERY_BRANCH=${PUBLISH_RECOVERY_BRANCH}"
STUB
    cat >"$STUB/upsert-diagrams-comment.sh" <<'STUB'
#!/usr/bin/env bash
echo "upsert-diagrams $*" >>"${UPSERT_LOG:?}"
[[ -n "${CALL_LOG:-}" ]] && echo "upsert-diagrams $*" >>"$CALL_LOG"
if [[ "${UPSERT_STUB_RC:-0}" -ne 0 ]]; then
  exit "${UPSERT_STUB_RC}"
fi
echo "UPSERT_STATUS=${UPSERT_STATUS_VALUE:-ok}"
echo "ARCHITECTURE_SOURCE=${ARCH_SOURCE_VALUE:-file}"
STUB
    cat >"$STUB/tracking-issue-write.sh" <<'STUB'
#!/usr/bin/env bash
echo "tracking-issue-write $*" >>"${RENAME_LOG:?}"
[[ -n "${CALL_LOG:-}" ]] && echo "tracking-issue-write $*" >>"$CALL_LOG"
if [[ "${RENAME_STUB_RC:-0}" -ne 0 ]]; then
  exit "${RENAME_STUB_RC}"
fi
if [[ "${RENAMED_OMIT_LINE:-false}" == true ]]; then
  exit 0
fi
echo "RENAMED=${RENAMED_VALUE:-true}"
STUB
    cat >"$STUB/resolve-repo.sh" <<'STUB'
#!/usr/bin/env bash
echo "${RESOLVE_REPO_VALUE:-owner/repo}"
STUB
    cat >"$FAKE_PLUGIN/skills/design/scripts/render-final-summary.sh" <<'STUB'
#!/usr/bin/env bash
{
  echo "render ISSUE_NUMBER=${ISSUE_NUMBER:-} SESSION_ID=${SESSION_ID:-} DESIGN_TMPDIR=${DESIGN_TMPDIR:-} DESIGN_LOG_PR_NUMBER=${DESIGN_LOG_PR_NUMBER:-} DESIGN_LOG_PR_URL=${DESIGN_LOG_PR_URL:-} DESIGN_LOG_RECOVERY_BRANCH=${DESIGN_LOG_RECOVERY_BRANCH:-} $*"
} >>"${RENDER_LOG:?}"
printf '# summary\n' >"${DESIGN_TMPDIR:?}/final-summary.md"
STUB
    chmod +x "$STUB"/*.sh "$FAKE_PLUGIN/skills/design/scripts/render-final-summary.sh"
}

write_stubs

export CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN"

reset_publish_stub_env() {
    unset PLAN_BLOCK_RC PUBLISH_STUB_RC PUBLISH_EMIT_OK PUBLISH_OK_VALUE \
        PUBLISH_PR_NUMBER PUBLISH_PR_URL PUBLISH_RECOVERY_BRANCH \
        UPSERT_STUB_RC UPSERT_STATUS_VALUE ARCH_SOURCE_VALUE \
        RENAME_STUB_RC RENAMED_OMIT_LINE RENAMED_VALUE RESOLVE_REPO_VALUE \
        MARKER_STUB_RC || true
}

init_publish_logs() {
    export PLAN_BLOCK_LOG="$TMP/plan-block.log"
    export PUBLISH_LOG="$TMP/publish.log"
    export RENAME_LOG="$TMP/rename.log"
    export UPSERT_LOG="$TMP/upsert.log"
    export RENDER_LOG="$TMP/render.log"
    export CALL_LOG="$TMP/call.log"
    : >"$PLAN_BLOCK_LOG"
    : >"$PUBLISH_LOG"
    : >"$RENAME_LOG"
    : >"$UPSERT_LOG"
    : >"$RENDER_LOG"
    : >"$CALL_LOG"
}

apply_publish_stub_defaults() {
    export PLAN_BLOCK_RC=0
    export PUBLISH_STUB_RC=0
    export PUBLISH_EMIT_OK=true
    export PUBLISH_OK_VALUE=true
    export UPSERT_STUB_RC=0
    export UPSERT_STATUS_VALUE=ok
    export ARCH_SOURCE_VALUE=file
    export RENAMED_VALUE=true
    export RESOLVE_REPO_VALUE=owner/repo
}

run_publish() {
    local d="$1"
    shift
    reset_publish_stub_env
    init_publish_logs
    apply_publish_stub_defaults
    bash "$SUBJECT" --design-tmpdir "$d" --issue 42 --session-id sid-1 --claude-pid 9999 "$@"
}

# --- argv / usage ---
set +e
bash "$SUBJECT" 2>/dev/null
rc=$?
set -e
assert_rc "missing argv" 2 "$rc"

set +e
bash "$SUBJECT" --help 2>/dev/null
rc=$?
set -e
assert_rc "--help" 0 "$rc"

# --- missing step-5b ---
D_PRE="$TMP/pre-5b"
setup_design_tmp "$D_PRE"
rm -f "$D_PRE/.completed/step-5b"
set +e
bash "$SUBJECT" --design-tmpdir "$D_PRE" --issue 1 --session-id x --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "missing step-5b" 2 "$rc"

# --- missing redacted plan ---
D_NOP="$TMP/no-plan"
setup_design_tmp "$D_NOP"
: >"$D_NOP/composed-plan.redacted.md"
set +e
bash "$SUBJECT" --design-tmpdir "$D_NOP" --issue 1 --session-id x --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "empty redacted plan" 2 "$rc"

# --- plan-block-write failure ---
D_FAIL="$TMP/fail-plan"
setup_design_tmp "$D_FAIL"
reset_publish_stub_env
init_publish_logs
export PLAN_BLOCK_RC=1
set +e
bash "$SUBJECT" --design-tmpdir "$D_FAIL" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>&1
rc=$?
set -e
assert_rc "plan-block-write failure" 1 "$rc"
grep -q 'PLAN_WRITE_OK=false' "$D_FAIL/.design-publish-result.env" \
  || fail "failure result env missing PLAN_WRITE_OK=false"
grep -q 'failed-plan-write' "$RENDER_LOG" \
  || fail "failed-plan-write render not logged"
grep -q 'ISSUE_NUMBER=42' "$RENDER_LOG" \
  || fail "failed-plan-write render missing ISSUE_NUMBER=42"
grep -q 'SESSION_ID=sid-1' "$RENDER_LOG" \
  || fail "failed-plan-write render missing SESSION_ID=sid-1"
D_FAIL_CANON=$(cd "$D_FAIL" && pwd -P)
grep -q "DESIGN_TMPDIR=${D_FAIL_CANON}" "$RENDER_LOG" \
  || fail "failed-plan-write render missing DESIGN_TMPDIR"

# --- happy path ---
D_OK="$TMP/happy"
D_OK_HOME="$TMP/happy-home"
setup_design_tmp "$D_OK"
printf 'graph TD\n' >"$D_OK/architecture-diagram.md"
set +e
HOME="$D_OK_HOME" run_publish "$D_OK" >/dev/null 2>&1
rc=$?
set -e
assert_rc "happy path" 0 "$rc"
grep -q 'PLAN_WRITE_OK=true' "$D_OK/.design-publish-result.env" || fail "happy PLAN_WRITE_OK"
grep -q 'PUBLISH_OK=true' "$D_OK/.design-publish-result.env" || fail "happy PUBLISH_OK"
grep -q 'RENAMED=true' "$D_OK/.design-publish-result.env" || fail "happy RENAMED"

plan_pos=$(grep -n 'plan-block-write' "$CALL_LOG" | head -1 | cut -d: -f1)
upsert_pos=$(grep -n 'upsert-diagrams' "$CALL_LOG" | head -1 | cut -d: -f1)
publish_pos=$(grep -n 'design-log-publish' "$CALL_LOG" | head -1 | cut -d: -f1)
rename_pos=$(grep -n 'tracking-issue-write' "$CALL_LOG" | head -1 | cut -d: -f1)
marker_pos=$(grep -n 'design-reentry-marker-write' "$CALL_LOG" | head -1 | cut -d: -f1)
if [[ -z "$plan_pos" || -z "$upsert_pos" || -z "$publish_pos" || -z "$rename_pos" || -z "$marker_pos" ]]; then
    fail "happy path call log missing plan/marker/upsert/publish entries"
elif [[ "$plan_pos" -ge "$upsert_pos" || "$upsert_pos" -ge "$publish_pos" || "$publish_pos" -ge "$rename_pos" || "$rename_pos" -ge "$marker_pos" ]]; then
    fail "happy path call-log ordering plan→upsert→publish→rename→marker"
else
    pass "happy path call-log ordering plan→upsert→publish→rename→marker"
fi
grep -q 'design-log-publish' "$PUBLISH_LOG" || fail "design-log-publish.sh should run on happy path"

marker_file="$D_OK_HOME/.cache/larch/sessions/design-completed-42-9999"
[[ -f "$marker_file" ]] || fail "happy path reentry marker file missing at $marker_file"
! grep -q 'pre-publish-only' "$RENDER_LOG" || fail "happy path must not pre-stage final-summary before publish outcome"
grep -q 'post-publish-only' "$RENDER_LOG" || fail "happy path missing post-publish render"
grep -q 'ISSUE_NUMBER=42' "$RENDER_LOG" || fail "happy render missing ISSUE_NUMBER=42"
grep -q 'SESSION_ID=sid-1' "$RENDER_LOG" || fail "happy render missing SESSION_ID=sid-1"
D_OK_CANON=$(cd "$D_OK" && pwd -P)
grep -q "DESIGN_TMPDIR=${D_OK_CANON}" "$RENDER_LOG" || fail "happy render missing DESIGN_TMPDIR"
grep -q 'upsert-diagrams' "$UPSERT_LOG" || fail "upsert not called on happy path"
test -s "$D_OK/diagrams-architecture-upsert.stdout" || fail "upsert stdout not captured"

# --- publish envelope fields persisted ---
D_ENV="$TMP/publish-env"
setup_design_tmp "$D_ENV"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_OK_VALUE=false
export PUBLISH_PR_NUMBER=123
export PUBLISH_PR_URL=https://github.example/pull/123
export PUBLISH_RECOVERY_BRANCH=larch-log-design-sid-1
bash "$SUBJECT" --design-tmpdir "$D_ENV" --issue 42 --session-id sid-1 --claude-pid 9999 2>/dev/null
grep -q '^PR_NUMBER=123$' "$D_ENV/.design-publish-result.env" || fail "publish PR_NUMBER missing"
grep -q '^PR_URL=https://github.example/pull/123$' "$D_ENV/.design-publish-result.env" || fail "publish PR_URL missing"
grep -q '^RECOVERY_BRANCH=larch-log-design-sid-1$' "$D_ENV/.design-publish-result.env" || fail "publish RECOVERY_BRANCH missing"
grep -q '^LOG_RECOVERY_BRANCH=larch-log-design-sid-1$' "$D_ENV/.design-publish-result.env" || fail "publish LOG_RECOVERY_BRANCH missing"

# --- SESSION_ID empty ---
D_EMPTY="$TMP/empty-sid"
setup_design_tmp "$D_EMPTY"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
set +e
bash "$SUBJECT" --design-tmpdir "$D_EMPTY" --issue 1 --session-id '' --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "empty session id" 0 "$rc"
if ! grep -q 'design-log-publish' "$PUBLISH_LOG" 2>/dev/null; then
    pass "publish skipped when SESSION_ID empty"
else
    fail "publish should be skipped"
fi
grep -q 'SESSION_ID missing' "$D_EMPTY/.design-publish-result.env" || fail "WARN missing for empty SESSION_ID"
render_count=$(grep -c 'render ISSUE_NUMBER=' "$RENDER_LOG" || true)
if [[ "$render_count" -ne 1 ]]; then
    fail "empty SESSION_ID must invoke exactly one render (post-publish-only), got $render_count"
else
    pass "empty SESSION_ID single post-publish render"
fi
grep -q 'post-publish-only' "$RENDER_LOG" || fail "empty SESSION_ID missing post-publish render"
grep -q 'ISSUE_NUMBER=1' "$RENDER_LOG" || fail "empty SESSION_ID render missing ISSUE_NUMBER"
grep -q 'DESIGN_TMPDIR=' "$RENDER_LOG" || fail "empty SESSION_ID render missing DESIGN_TMPDIR"
if ! grep -q 'tracking-issue-write' "$RENAME_LOG" 2>/dev/null; then
    pass "rename skipped when SESSION_ID empty"
else
    fail "rename should be skipped"
fi

# --- PUBLISH_OK=false ---
D_PFAIL="$TMP/pub-fail"
setup_design_tmp "$D_PFAIL"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_OK_VALUE=false
export PUBLISH_PR_NUMBER=456
export PUBLISH_PR_URL=https://github.example/pull/456
export PUBLISH_RECOVERY_BRANCH=larch-log-design-sid
set +e
bash "$SUBJECT" --design-tmpdir "$D_PFAIL" --issue 1 --session-id sid --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "PUBLISH_OK=false" 0 "$rc"
grep -q 'post-publish-only' "$RENDER_LOG" || fail "PUBLISH_OK=false should render post-publish summary"
grep -q -- '--outcome failed-publish' "$RENDER_LOG" || fail "PUBLISH_OK=false should render failed-publish outcome"
grep -q 'DESIGN_LOG_PR_NUMBER=456' "$RENDER_LOG" || fail "PUBLISH_OK=false render missing DESIGN_LOG_PR_NUMBER"
grep -q 'DESIGN_LOG_PR_URL=https://github.example/pull/456' "$RENDER_LOG" || fail "PUBLISH_OK=false render missing DESIGN_LOG_PR_URL"
grep -q 'DESIGN_LOG_RECOVERY_BRANCH=larch-log-design-sid' "$RENDER_LOG" || fail "PUBLISH_OK=false render missing DESIGN_LOG_RECOVERY_BRANCH"
grep -q 'design-log-publish.sh failed (exit 1)' "$D_PFAIL/execution-issues.md" 2>/dev/null || fail "PUBLISH_OK=false should record nonzero publish failure exit"
grep -q 'design log publish failed; recovery metadata' "$D_PFAIL/.design-publish-result.env" || fail "PUBLISH_OK=false should emit recovery WARN"
if ! grep -q 'tracking-issue-write' "$RENAME_LOG"; then
    pass "rename skipped on PUBLISH_OK=false"
else
    fail "rename should be skipped"
fi
if grep -q 'design-reentry-marker-write' "$CALL_LOG"; then
    fail "reentry marker should be skipped on PUBLISH_OK=false"
else
    pass "reentry marker skipped on PUBLISH_OK=false"
fi

# --- unexpected publish (nonzero, no PUBLISH_OK line) ---
D_UNEXP="$TMP/pub-unexp"
setup_design_tmp "$D_UNEXP"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_STUB_RC=2
export PUBLISH_EMIT_OK=false
set +e
bash "$SUBJECT" --design-tmpdir "$D_UNEXP" --issue 1 --session-id sid --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "unexpected publish rc" 0 "$rc"
grep -q 'PUBLISH_OK=false' "$D_UNEXP/.design-publish-result.env" || fail "unexpected publish must set PUBLISH_OK=false"
grep -q 'post-publish-only' "$RENDER_LOG" || fail "unexpected publish should render post-publish summary"
grep -q -- '--outcome failed-publish' "$RENDER_LOG" || fail "unexpected publish rc should render failed-publish outcome"
if grep -q 'tracking-issue-write' "$RENAME_LOG" 2>/dev/null; then
    fail "rename should be skipped after unexpected publish rc"
else
    pass "rename skipped after unexpected publish rc"
fi
grep -q 'design-log-publish.sh' "$D_UNEXP/execution-issues.md" 2>/dev/null   || fail "unexpected publish must append to execution-issues.md"

# --- exit 0 without PUBLISH_OK= line ---
D_NO_PUB_KV="$TMP/no-publish-kv"
setup_design_tmp "$D_NO_PUB_KV"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_STUB_RC=0
export PUBLISH_EMIT_OK=false
set +e
bash "$SUBJECT" --design-tmpdir "$D_NO_PUB_KV" --issue 1 --session-id sid --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "missing PUBLISH_OK on exit 0" 0 "$rc"
grep -q 'PUBLISH_OK=false' "$D_NO_PUB_KV/.design-publish-result.env"   || fail "exit 0 without PUBLISH_OK= must set PUBLISH_OK=false"
grep -q 'post-publish-only' "$RENDER_LOG" || fail "exit 0 without PUBLISH_OK should render post-publish summary"
grep -q -- '--outcome failed-publish' "$RENDER_LOG" || fail "exit 0 without PUBLISH_OK should render failed-publish outcome"
if grep -q 'tracking-issue-write' "$RENAME_LOG" 2>/dev/null; then
    fail "rename should be skipped when PUBLISH_OK is missing"
else
    pass "rename skipped when PUBLISH_OK is missing"
fi
grep -q 'design-log-publish.sh' "$D_NO_PUB_KV/execution-issues.md" 2>/dev/null   || fail "exit 0 without PUBLISH_OK= must append to execution-issues.md"

# --- result-env write failure (exit 3) ---
D_EXIT3="$TMP/exit3-result-env"
setup_design_tmp "$D_EXIT3"
ln -sf /dev/null "$D_EXIT3/.design-publish-result.env"
set +e
run_publish "$D_EXIT3" 2>/dev/null
rc=$?
set -e
assert_rc "result-env symlink refusal" 3 "$rc"
[[ -L "$D_EXIT3/.design-publish-result.env" ]] \
  || fail "exit 3 must not replace symlink result env"
grep -q 'design-log-publish' "$PUBLISH_LOG"   || fail "exit 3 should run design-log-publish before result-env write"
grep -q 'tracking-issue-write' "$RENAME_LOG"   || fail "exit 3 should still complete publish tail (rename) before result-env write"

# --- if ! plan-block-write guard ---
# shellcheck disable=SC2016 # Literal pattern checks unexpanded shell syntax in source.
grep -Fq 'if ! "$PLUGIN_ROOT/scripts/plan-block-write.sh"' "$SUBJECT" \
  || fail "design-publish.sh must use if ! around plan-block-write.sh"

# --- clear-architecture sentinel path ---
D_CLR="$TMP/clear-arch"
setup_design_tmp "$D_CLR"
rm -f "$D_CLR/architecture-diagram.md"
: >"$D_CLR/architecture-diagram.skipped"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
bash "$SUBJECT" --design-tmpdir "$D_CLR" --issue 1 --session-id s --claude-pid 1 2>/dev/null
grep -Fq -- '--clear-architecture' "$UPSERT_LOG" || fail "skipped sentinel must invoke --clear-architecture"

# --- upsert failure non-blocking ---
D_UPSERT_FAIL="$TMP/upsert-fail"
setup_design_tmp "$D_UPSERT_FAIL"
printf 'graph TD\n' >"$D_UPSERT_FAIL/architecture-diagram.md"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export UPSERT_STUB_RC=1
export UPSERT_STATUS_VALUE=failed
set +e
bash "$SUBJECT" --design-tmpdir "$D_UPSERT_FAIL" --issue 42 --session-id sid-1 --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "upsert failure non-blocking" 0 "$rc"
grep -q 'PLAN_WRITE_OK=true' "$D_UPSERT_FAIL/.design-publish-result.env" \
  || fail "upsert failure must still complete publish tail"
grep -q 'upsert-diagrams-comment.sh' "$D_UPSERT_FAIL/execution-issues.md" 2>/dev/null \
  || fail "upsert failure must append to execution-issues.md"

# --- empty architecture-diagram.md (no upsert) ---
D_EMPTY_ARCH="$TMP/empty-arch-file"
setup_design_tmp "$D_EMPTY_ARCH"
: >"$D_EMPTY_ARCH/architecture-diagram.md"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
set +e
bash "$SUBJECT" --design-tmpdir "$D_EMPTY_ARCH" --issue 1 --session-id s --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "empty architecture file" 0 "$rc"
if grep -q 'upsert-diagrams' "$UPSERT_LOG" 2>/dev/null; then
    fail "zero-byte architecture-diagram.md must not invoke upsert"
else
    pass "zero-byte architecture-diagram.md skips upsert"
fi

# --- empty architecture-diagram.md with skipped sentinel (clear) ---
D_EMPTY_ARCH_CLR="$TMP/empty-arch-clear"
setup_design_tmp "$D_EMPTY_ARCH_CLR"
: >"$D_EMPTY_ARCH_CLR/architecture-diagram.md"
: >"$D_EMPTY_ARCH_CLR/architecture-diagram.skipped"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
bash "$SUBJECT" --design-tmpdir "$D_EMPTY_ARCH_CLR" --issue 1 --session-id s --claude-pid 1 2>/dev/null
grep -Fq -- '--clear-architecture' "$UPSERT_LOG" \
  || fail "empty architecture with skipped sentinel must invoke --clear-architecture"

# --- rename failure warns ---
D_REN_FAIL="$TMP/rename-fail"
setup_design_tmp "$D_REN_FAIL"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export RENAME_STUB_RC=1
set +e
bash "$SUBJECT" --design-tmpdir "$D_REN_FAIL" --issue 42 --session-id sid-1 --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "rename failure non-blocking" 0 "$rc"
grep -q 'WARN=.*\[DESIGNED\].*rename failed' "$D_REN_FAIL/.design-publish-result.env" \
  || fail "rename failure must emit [DESIGNED] WARN in result env"

# --- rename success without RENAMED= line ---
D_REN_OMIT="$TMP/rename-omit"
setup_design_tmp "$D_REN_OMIT"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export RENAMED_OMIT_LINE=true
set +e
bash "$SUBJECT" --design-tmpdir "$D_REN_OMIT" --issue 42 --session-id sid-1 --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "rename omit RENAMED line" 0 "$rc"
grep -q 'WARN=.*omitted RENAMED=' "$D_REN_OMIT/.design-publish-result.env" \
  || fail "success without RENAMED= must emit WARN in result env"

# --- marker write failure non-blocking ---
D_MARKER_FAIL="$TMP/marker-fail"
setup_design_tmp "$D_MARKER_FAIL"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export MARKER_STUB_RC=1
set +e
bash "$SUBJECT" --design-tmpdir "$D_MARKER_FAIL" --issue 42 --session-id sid-1 --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "marker failure non-blocking" 0 "$rc"
grep -q 'PLAN_WRITE_OK=true' "$D_MARKER_FAIL/.design-publish-result.env" \
  || fail "marker failure must still complete publish tail"
grep -q 'design Step 5c marker write' "$D_MARKER_FAIL/execution-issues.md" \
  || fail "marker failure must append to execution-issues.md"

# --- no diagram and no skipped sentinel ---
D_NO_ARCH="$TMP/no-arch"
setup_design_tmp "$D_NO_ARCH"
rm -f "$D_NO_ARCH/architecture-diagram.md" "$D_NO_ARCH/architecture-diagram.skipped"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
set +e
bash "$SUBJECT" --design-tmpdir "$D_NO_ARCH" --issue 1 --session-id s --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "no arch file or sentinel" 0 "$rc"
if grep -q 'upsert-diagrams' "$UPSERT_LOG" 2>/dev/null; then
    fail "upsert must be skipped when neither diagram nor sentinel exists"
else
    pass "upsert skipped when neither diagram nor sentinel"
fi

if [[ "$FAIL" -gt 0 ]]; then
    echo "FAIL: $FAIL test(s) failed ($PASS passed)" >&2
    exit 1
fi
echo "PASS: test-design-publish.sh ($PASS cases)"
