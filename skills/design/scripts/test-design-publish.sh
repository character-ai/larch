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
ln -sf "$REPO_ROOT/scripts/lib-design-reentry-guard.sh" "$STUB/lib-design-reentry-guard.sh"
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
  echo "render ISSUE_NUMBER=${ISSUE_NUMBER:-} SESSION_ID=${SESSION_ID:-} DESIGN_TMPDIR=${DESIGN_TMPDIR:-} $*"
} >>"${RENDER_LOG:?}"
printf '# summary\n' >"${DESIGN_TMPDIR:?}/final-summary.md"
STUB
    chmod +x "$STUB"/*.sh "$FAKE_PLUGIN/skills/design/scripts/render-final-summary.sh"
}

write_stubs

export CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN"

run_publish() {
    local d="$1"
    shift
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
    export PLAN_BLOCK_RC="${PLAN_BLOCK_RC:-0}"
    export PUBLISH_STUB_RC="${PUBLISH_STUB_RC:-0}"
    export PUBLISH_EMIT_OK="${PUBLISH_EMIT_OK:-true}"
    export PUBLISH_OK_VALUE="${PUBLISH_OK_VALUE:-true}"
    export UPSERT_STUB_RC="${UPSERT_STUB_RC:-0}"
    export UPSERT_STATUS_VALUE="${UPSERT_STATUS_VALUE:-ok}"
    export ARCH_SOURCE_VALUE="${ARCH_SOURCE_VALUE:-file}"
    export RENAMED_VALUE="${RENAMED_VALUE:-true}"
    export RESOLVE_REPO_VALUE="${RESOLVE_REPO_VALUE:-owner/repo}"
    bash "$SUBJECT" --design-tmpdir "$d" --issue 42 --session-id sid-1 --claude-pid 9999 "$@"
}

# --- argv / usage ---
set +e
bash "$SUBJECT" 2>/dev/null
rc=$?
set -e
assert_rc "missing argv" 2 "$rc"

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
export PLAN_BLOCK_RC=1
set +e
run_publish "$D_FAIL" >/dev/null 2>&1
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
unset PLAN_BLOCK_RC

# --- happy path ---
D_OK="$TMP/happy"
setup_design_tmp "$D_OK"
printf 'graph TD\n' >"$D_OK/architecture-diagram.md"
export PLAN_BLOCK_RC=0
set +e
run_publish "$D_OK" >/dev/null 2>&1
rc=$?
set -e
assert_rc "happy path" 0 "$rc"
grep -q 'PLAN_WRITE_OK=true' "$D_OK/.design-publish-result.env" || fail "happy PLAN_WRITE_OK"
grep -q 'PUBLISH_OK=true' "$D_OK/.design-publish-result.env" || fail "happy PUBLISH_OK"
grep -q 'RENAMED=true' "$D_OK/.design-publish-result.env" || fail "happy RENAMED"
plan_pos=$(grep -n 'plan-block-write' "$CALL_LOG" | head -1 | cut -d: -f1)
upsert_pos=$(grep -n 'upsert-diagrams' "$CALL_LOG" | head -1 | cut -d: -f1)
publish_pos=$(grep -n 'design-log-publish' "$CALL_LOG" | head -1 | cut -d: -f1)
if [[ -z "$plan_pos" || -z "$upsert_pos" || -z "$publish_pos" ]]; then
    fail "happy path call log missing plan/upsert/publish entries"
elif [[ "$plan_pos" -ge "$upsert_pos" || "$upsert_pos" -ge "$publish_pos" ]]; then
    fail "happy path call-log ordering plan→upsert→publish"
else
    pass "happy path call-log ordering plan→upsert→publish"
fi
grep -q 'pre-publish-only' "$RENDER_LOG" || fail "happy path missing pre-publish render"
grep -q 'post-publish-only' "$RENDER_LOG" || fail "happy path missing post-publish render"
grep -q 'ISSUE_NUMBER=42' "$RENDER_LOG" || fail "happy render missing ISSUE_NUMBER=42"
grep -q 'SESSION_ID=sid-1' "$RENDER_LOG" || fail "happy render missing SESSION_ID=sid-1"
D_OK_CANON=$(cd "$D_OK" && pwd -P)
grep -q "DESIGN_TMPDIR=${D_OK_CANON}" "$RENDER_LOG" || fail "happy render missing DESIGN_TMPDIR"
grep -q 'upsert-diagrams' "$UPSERT_LOG" || fail "upsert not called on happy path"
test -s "$D_OK/diagrams-architecture-upsert.stdout" || fail "upsert stdout not captured"

# --- SESSION_ID empty ---
D_EMPTY="$TMP/empty-sid"
setup_design_tmp "$D_EMPTY"
export PLAN_BLOCK_RC=0
export PLAN_BLOCK_LOG="$TMP/plan-empty.log"
export PUBLISH_LOG="$TMP/pub-empty.log"
export RENAME_LOG="$TMP/ren-empty.log"
export UPSERT_LOG="$TMP/ups-empty.log"
export RENDER_LOG="$TMP/rend-empty.log"
: >"$PLAN_BLOCK_LOG"
: >"$PUBLISH_LOG"
: >"$RENAME_LOG"
: >"$UPSERT_LOG"
: >"$RENDER_LOG"
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
export PLAN_BLOCK_RC=0
export PUBLISH_STUB_RC=0
export PUBLISH_OK_VALUE=false
export PLAN_BLOCK_LOG="$TMP/plan-pf.log"
export PUBLISH_LOG="$TMP/pub-pf.log"
export RENAME_LOG="$TMP/ren-pf.log"
export UPSERT_LOG="$TMP/ups-pf.log"
export RENDER_LOG="$TMP/rend-pf.log"
: >"$PLAN_BLOCK_LOG"
: >"$PUBLISH_LOG"
: >"$RENAME_LOG"
: >"$UPSERT_LOG"
: >"$RENDER_LOG"
set +e
bash "$SUBJECT" --design-tmpdir "$D_PFAIL" --issue 1 --session-id sid --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "PUBLISH_OK=false" 0 "$rc"
if ! grep -q 'tracking-issue-write' "$RENAME_LOG"; then
    pass "rename skipped on PUBLISH_OK=false"
else
    fail "rename should be skipped"
fi

# --- unexpected publish (nonzero, no PUBLISH_OK line) ---
D_UNEXP="$TMP/pub-unexp"
setup_design_tmp "$D_UNEXP"
export PLAN_BLOCK_RC=0
export PUBLISH_STUB_RC=2
export PUBLISH_EMIT_OK=false
export PLAN_BLOCK_LOG="$TMP/plan-ux.log"
export PUBLISH_LOG="$TMP/pub-ux.log"
export RENAME_LOG="$TMP/ren-ux.log"
export UPSERT_LOG="$TMP/ups-ux.log"
export RENDER_LOG="$TMP/rend-ux.log"
: >"$PLAN_BLOCK_LOG"
: >"$PUBLISH_LOG"
: >"$RENAME_LOG"
: >"$UPSERT_LOG"
: >"$RENDER_LOG"
set +e
bash "$SUBJECT" --design-tmpdir "$D_UNEXP" --issue 1 --session-id sid --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "unexpected publish rc" 0 "$rc"
grep -q 'PUBLISH_OK=false' "$D_UNEXP/.design-publish-result.env" || fail "unexpected publish must set PUBLISH_OK=false"

# --- if ! plan-block-write guard ---
# shellcheck disable=SC2016 # Literal pattern checks unexpanded shell syntax in source.
grep -Fq 'if ! "$PLUGIN_ROOT/scripts/plan-block-write.sh"' "$SUBJECT" \
  || fail "design-publish.sh must use if ! around plan-block-write.sh"

# --- clear-architecture sentinel path ---
D_CLR="$TMP/clear-arch"
setup_design_tmp "$D_CLR"
rm -f "$D_CLR/architecture-diagram.md"
: >"$D_CLR/architecture-diagram.skipped"
export PLAN_BLOCK_RC=0
export PLAN_BLOCK_LOG="$TMP/plan-cl.log"
export PUBLISH_LOG="$TMP/pub-cl.log"
export RENAME_LOG="$TMP/ren-cl.log"
export UPSERT_LOG="$TMP/ups-cl.log"
export RENDER_LOG="$TMP/rend-cl.log"
: >"$PLAN_BLOCK_LOG"
: >"$PUBLISH_LOG"
: >"$RENAME_LOG"
: >"$UPSERT_LOG"
: >"$RENDER_LOG"
bash "$SUBJECT" --design-tmpdir "$D_CLR" --issue 1 --session-id s --claude-pid 1 2>/dev/null
grep -Fq -- '--clear-architecture' "$UPSERT_LOG" || fail "skipped sentinel must invoke --clear-architecture"

# --- upsert failure non-blocking ---
D_UPSERT_FAIL="$TMP/upsert-fail"
setup_design_tmp "$D_UPSERT_FAIL"
export PLAN_BLOCK_RC=0
export UPSERT_STUB_RC=1
export UPSERT_STATUS_VALUE=failed
export PLAN_BLOCK_LOG="$TMP/plan-uf.log"
export PUBLISH_LOG="$TMP/pub-uf.log"
export RENAME_LOG="$TMP/ren-uf.log"
export UPSERT_LOG="$TMP/ups-uf.log"
export RENDER_LOG="$TMP/rend-uf.log"
: >"$PLAN_BLOCK_LOG"
: >"$PUBLISH_LOG"
: >"$RENAME_LOG"
: >"$UPSERT_LOG"
: >"$RENDER_LOG"
set +e
bash "$SUBJECT" --design-tmpdir "$D_UPSERT_FAIL" --issue 42 --session-id sid-1 --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "upsert failure non-blocking" 0 "$rc"
grep -q 'PLAN_WRITE_OK=true' "$D_UPSERT_FAIL/.design-publish-result.env" \
  || fail "upsert failure must still complete publish tail"
unset UPSERT_STUB_RC UPSERT_STATUS_VALUE

# --- rename failure warns ---
D_REN_FAIL="$TMP/rename-fail"
setup_design_tmp "$D_REN_FAIL"
export PLAN_BLOCK_RC=0
export PUBLISH_STUB_RC=0
export PUBLISH_EMIT_OK=true
export PUBLISH_OK_VALUE=true
export RENAME_STUB_RC=1
export PLAN_BLOCK_LOG="$TMP/plan-rf.log"
export PUBLISH_LOG="$TMP/pub-rf.log"
export RENAME_LOG="$TMP/ren-rf.log"
export UPSERT_LOG="$TMP/ups-rf.log"
export RENDER_LOG="$TMP/rend-rf.log"
: >"$PLAN_BLOCK_LOG"
: >"$PUBLISH_LOG"
: >"$RENAME_LOG"
: >"$UPSERT_LOG"
: >"$RENDER_LOG"
set +e
bash "$SUBJECT" --design-tmpdir "$D_REN_FAIL" --issue 42 --session-id sid-1 --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "rename failure non-blocking" 0 "$rc"
grep -q 'WARN=.*\[DESIGNED\].*rename failed' "$D_REN_FAIL/.design-publish-result.env" \
  || fail "rename failure must emit [DESIGNED] WARN in result env"
unset RENAME_STUB_RC

if [[ "$FAIL" -gt 0 ]]; then
    echo "FAIL: $FAIL test(s) failed ($PASS passed)" >&2
    exit 1
fi
echo "PASS: test-design-publish.sh ($PASS cases)"
