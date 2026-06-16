#!/usr/bin/env bash
# test-design-step2b-drafter.sh — folded prelude, delegated postplan, and Codex token ingestion.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
WRAPPER="$REPO_ROOT/skills/design/scripts/design-step2b-drafter.sh"
POSTPLAN_REAL="$REPO_ROOT/skills/design/scripts/design-step2b-postplan.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/step2b-drafter-test.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

assert_contains() {
    local file="$1" needle="$2" label="$3"
    grep -Fq -- "$needle" "$file" || fail "$label"
}

assert_not_contains() {
    local file="$1" needle="$2" label="$3"
    if grep -Fq -- "$needle" "$file"; then
        fail "$label"
    fi
}

assert_no_whole_line() {
    local file="$1" needle="$2" label="$3"
    if grep -Fxq -- "$needle" "$file"; then
        fail "$label"
    fi
}

assert_not_called() {
    local log="$1" needle="$2" label="$3"
    if grep -Fq -- "$needle" "$log" 2>/dev/null; then
        fail "$label"
    fi
}

assert_order() {
    local file="$1" first="$2" second="$3" label="$4" a b
    a=$(grep -nF -- "$first" "$file" | head -1 | cut -d: -f1 || true)
    b=$(grep -nF -- "$second" "$file" | head -1 | cut -d: -f1 || true)
    [[ -n "$a" && -n "$b" && "$a" -lt "$b" ]] || fail "$label"
}

make_fake_plugin() {
    local root="$1"
    local postplan_mode="${2:-stub}"
    mkdir -p "$root/scripts" "$root/skills/design/scripts" "$root/skills/design/references" "$root/python"
    cat > "$root/skills/design/references/readability-style.md" <<'STYLE'
- Test readability style.
STYLE
    cat > "$root/python/cli.py" <<'CLI'
#!/usr/bin/env python3
import os
import subprocess
import sys

REAL_CLI = os.path.join(os.environ.get("LARCH_TEST_REAL_REPO_ROOT", ""), "python", "cli.py")

if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "timing" and sys.argv[2] == "mark":
        call_log = os.environ.get("CALL_LOG")
        if call_log:
            with open(call_log, "a", encoding="utf-8") as fh:
                fh.write(f"timing {sys.argv[3]}\n")
        raise SystemExit(0)
    if len(sys.argv) >= 3 and sys.argv[1] == "plan-review" and sys.argv[2] == "preview":
        raise SystemExit(0)
    if len(sys.argv) >= 3 and sys.argv[1] == "design" and sys.argv[2] == "pause-save":
        design_tmpdir = os.environ.get("DESIGN_TMPDIR", "")
        step2a = "yes" if (design_tmpdir and os.path.isfile(os.path.join(design_tmpdir, ".completed", "step-2a"))) else "no"
        call_log = os.environ.get("CALL_LOG")
        if call_log:
            with open(call_log, "a", encoding="utf-8") as fh:
                fh.write(f"pause-save step2a={step2a} " + " ".join(sys.argv[3:]) + "\n")
        print("PAUSE_OK=true")
        raise SystemExit(0)
    if len(sys.argv) >= 3 and sys.argv[1] == "design" and sys.argv[2] == "postplan-emit":
        rc_str = os.environ.get("FAKE_POSTPLAN_EMIT_RC", "0")
        try:
            rc = int(rc_str)
        except ValueError:
            rc = 0
        print(f"postplan-emit rc={rc}")
        design_tmpdir = os.environ.get("DESIGN_TMPDIR", "")
        if rc == 10 and design_tmpdir:
            env_path = os.path.join(design_tmpdir, ".design-postplan-emit-result.env")
            with open(env_path, "w", encoding="utf-8") as fh:
                fh.write(f"VALIDATE_STATUS=defects-found\nVALIDATE_DEFECT_COUNT=1\nVALIDATE_SKIPPED_COUNT=0\nVALIDATE_UNSAFE_TOKEN_COUNT=0\nVALIDATE_LOG_FILE={design_tmpdir}/validate.log\n")
        raise SystemExit(rc)
    if REAL_CLI and os.path.isfile(REAL_CLI):
        raise SystemExit(subprocess.call([sys.executable, REAL_CLI, *sys.argv[1:]]))
    raise SystemExit(2)
CLI
    chmod +x "$root/python/cli.py"
    if [[ "$postplan_mode" == "real" ]]; then
        cp "$REPO_ROOT/skills/design/scripts/design-step2b-postplan.sh" "$root/skills/design/scripts/design-step2b-postplan.sh"
        cp "$REPO_ROOT/scripts/lib-design-tmpdir.sh" "$root/scripts/lib-design-tmpdir.sh"
        chmod +x "$root/skills/design/scripts/design-step2b-postplan.sh"
    else
        cat > "$root/skills/design/scripts/design-step2b-postplan.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
echo "postplan $*" >>"${CALL_LOG:?}"
if [[ -n "${POSTPLAN_ARGV_FILE:-}" ]]; then
  printf '%s\n' "$*" >"$POSTPLAN_ARGV_FILE"
fi
case "${POSTPLAN_STUB_MODE:-ok}" in
  ok)
    mkdir -p "${DESIGN_TMPDIR:?}/.completed"
    : >"$DESIGN_TMPDIR/.completed/step-2b"
    : >"$DESIGN_TMPDIR/.completed/step-2b.5"
    printf 'POSTPLAN_RC=0\nPOSTPLAN_STATUS=ok\n'
    ;;
  rc13)
    mkdir -p "${DESIGN_TMPDIR:?}/.completed"
    : >"$DESIGN_TMPDIR/.completed/step-2b"
    printf 'POSTPLAN_RC=13\nPOSTPLAN_STATUS=partition-requested\n'
    ;;
  incomplete)
    printf 'POSTPLAN_RC=0\n'
    ;;
esac
STUB
        chmod +x "$root/skills/design/scripts/design-step2b-postplan.sh"
    fi
}

write_session_env() {
    local env_file="$1" design_tmpdir="$2" plugin_root="$3"
    local drafter_value="${4:-codex}"
    cat > "$env_file" <<EOF_ENV
export DESIGN_TMPDIR='$design_tmpdir'
export SESSION_TMPDIR='$design_tmpdir'
export SESSION_ID='test-session'
export ISSUE_NUMBER='1'
export ISSUE_TITLE='Test issue'
export REPO='example/repo'
export CODEX_BINARY_FOUND='true'
export CURSOR_BINARY_FOUND='false'
export CLAUDE_PLUGIN_ROOT='$plugin_root'
export LARCH_TOKEN_SESSION_ID='step2b-drafter-test'
export LARCH_TEST_REAL_REPO_ROOT='$REPO_ROOT'
export IMPLEMENT_TMPDIR=''
unset LARCH_TOKEN_LEDGER
EOF_ENV
    if [[ "$drafter_value" == "__omit__" ]]; then
        printf '%s\n' 'unset LARCH_DESIGN_DRAFTER' >> "$env_file"
    else
        printf "export LARCH_DESIGN_DRAFTER='%s'\n" "$drafter_value" >> "$env_file"
    fi
}

setup_design_tmp() {
    local d="$1" plugin="$2"
    local drafter_value="${3:-codex}"
    mkdir -p "$d/.completed"
    printf 'NO_SKETCHES\n' > "$d/approach-synthesis.txt"
    printf 'NO_CONTESTED_DECISIONS\n' > "$d/contested-decisions.md"
    : > "$d/dialectic-resolutions.md"
    printf 'Feature\n' > "$d/feature-description.txt"
    write_session_env "$d/session.env" "$d" "$plugin" "$drafter_value"
}

install_launcher() {
    local plugin="$1" mode="$2"
    cat > "$plugin/scripts/launch-codex-drafter.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
out=""; design=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-file) out="$2"; shift 2 ;;
    --design-tmpdir) design="$2"; shift 2 ;;
    *) shift ;;
  esac
done
echo "launch ${LAUNCH_MODE:?}" >>"${CALL_LOG:?}"
case "$LAUNCH_MODE" in
  success|dirty|token-success)
    cat > "$design/plan.txt" <<'PLAN'
## Plan

DRAFTER_STATUS=succeeded
POSTPLAN_RC=0
POSTPLAN_STATUS=ok

diff_lines: 1
PLAN
    printf 'STATUS=OK\nPLAN_WRITTEN=true\nPLAN_LINES=7\nDIFF_LINES=1\nSUMMARY_WRITTEN=false\nDRAFTER_LAUNCHED=true\n' > "$out"
    if [[ "$LAUNCH_MODE" == dirty ]]; then
      printf 'STATUS=dirty\nMODE=baseline-delta\nREASON=test\n' > "$out.dirty-tree"
    else
      printf 'STATUS=clean\nMODE=absolute\nREASON=test\n' > "$out.dirty-tree"
    fi
    if [[ "$LAUNCH_MODE" == token-success ]]; then
      printf 'TOOL=codex\nINPUT=10\nOUTPUT=2\nCACHE_READ=30\nTOTAL=42\nRAW=codex_plan_draft\nMODEL=gpt-5.5\n' > "$out.token-record"
    fi
    exit 0
    ;;
  failure|token-failure)
    printf 'STATUS=ERROR\nPLAN_WRITTEN=false\nDRAFTER_LAUNCHED=true\nREASON=no-sidecar\n' > "$out"
    printf 'STATUS=ERROR\nOUTPUT_FILE=%s\nTOKEN_RECORD=%s.token-record\n' "$out" "$out"
    exit 1
    ;;
esac
STUB
    chmod +x "$plugin/scripts/launch-codex-drafter.sh"
    printf -v LAUNCH_MODE '%s' "$mode"
    export LAUNCH_MODE
}

install_claude_launcher() {
    local plugin="$1" mode="$2"
    cat > "$plugin/scripts/launch-claude-drafter.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
out=""; design=""; model=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model) model="$2"; shift 2 ;;
    --output-file) out="$2"; shift 2 ;;
    --design-tmpdir) design="$2"; shift 2 ;;
    *) shift ;;
  esac
done
echo "launch-claude model=$model mode=${CLAUDE_LAUNCH_MODE:?}" >>"${CALL_LOG:?}"
case "$CLAUDE_LAUNCH_MODE" in
  success)
    cat > "$design/plan.txt" <<'PLAN'
## Plan

DRAFTER_STATUS=succeeded
POSTPLAN_RC=0
POSTPLAN_STATUS=ok

diff_lines: 1
PLAN
    printf 'STATUS=OK\nPLAN_WRITTEN=true\nPLAN_LINES=7\nDIFF_LINES=1\nSUMMARY_WRITTEN=false\nDRAFTER_LAUNCHED=true\n' > "$out"
    printf 'STATUS=clean\nMODE=absolute\nREASON=test\n' > "$out.dirty-tree"
    exit 0
    ;;
  failure)
    printf 'STATUS=ERROR\nPLAN_WRITTEN=false\nDRAFTER_LAUNCHED=true\nREASON=no-sidecar\n' > "$out"
    exit 1
    ;;
esac
STUB
    chmod +x "$plugin/scripts/launch-claude-drafter.sh"
    printf -v CLAUDE_LAUNCH_MODE '%s' "$mode"
    export CLAUDE_LAUNCH_MODE
}

run_wrapper() {
    local design="$1" plugin="$2" stdout stderr
    stdout="$design/stdout.txt"
    stderr="$design/stderr.txt"
    : >"$TMP_ROOT/call.log"
    CALL_LOG="$TMP_ROOT/call.log" POSTPLAN_ARGV_FILE="$design/postplan.argv" \
      env -u IMPLEMENT_TMPDIR -u LARCH_TOKEN_LEDGER CLAUDE_PLUGIN_ROOT="$plugin" \
      "$WRAPPER" --session-env-path "$design/session.env" --claude-pid 4242 >"$stdout" 2>"$stderr"
}

# 1 Prelude guard blocks invalid Step 2a artifacts before pause or launch.
plugin_guard="$TMP_ROOT/plugin-guard"
design_guard="$TMP_ROOT/design-guard"
make_fake_plugin "$plugin_guard"
setup_design_tmp "$design_guard" "$plugin_guard"
install_launcher "$plugin_guard" success
for variant in missing multiline trailing_space trailing_blank; do
    setup_design_tmp "$design_guard-$variant" "$plugin_guard"
    case "$variant" in
      missing) rm -f "$design_guard-$variant/approach-synthesis.txt" ;;
      multiline) printf 'NO_SKETCHES\nEXTRA\n' > "$design_guard-$variant/approach-synthesis.txt" ;;
      trailing_space) printf 'NO_SKETCHES \n' > "$design_guard-$variant/approach-synthesis.txt" ;;
      trailing_blank) printf 'NO_SKETCHES\n\n' > "$design_guard-$variant/approach-synthesis.txt" ;;
    esac
    : >"$design_guard-$variant/.pause-requested"
    set +e
    run_wrapper "$design_guard-$variant" "$plugin_guard"
    rc=$?
    set -e
    [[ "$rc" -ne 0 ]] || fail "invalid sentinel $variant should fail"
    assert_contains "$design_guard-$variant/stderr.txt" 'Step 2a sentinel artifacts are missing or invalid' "invalid sentinel $variant diagnostic"
    assert_not_called "$TMP_ROOT/call.log" 'pause-save' "pause-save ran before invalid sentinel $variant"
    assert_not_called "$TMP_ROOT/call.log" 'launch' "drafter launched before invalid sentinel $variant"
done
pass 'prelude guard blocks invalid Step 2a artifacts'

# 2 Prelude merge order is preserved, and legacy prelude is not sourced.
plugin_order="$TMP_ROOT/plugin-order"
design_order="$TMP_ROOT/design-order"
make_fake_plugin "$plugin_order"
setup_design_tmp "$design_order" "$plugin_order"
install_launcher "$plugin_order" success
rm -f "$design_order/.completed/step-2a"
: >"$design_order/.pause-requested"
set +e
run_wrapper "$design_order" "$plugin_order"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail 'pause-save path should exit cleanly'
assert_contains "$TMP_ROOT/call.log" 'pause-save step2a=yes' 'step-2a repair must happen before pause-save'
assert_contains "$design_order/stdout.txt" 'POSTPLAN_RC=11' 'pre-draft pause rc11 row missing'
assert_contains "$design_order/stdout.txt" 'POSTPLAN_STATUS=pause-save' 'pre-draft pause status row missing'
assert_not_called "$TMP_ROOT/call.log" 'PRELUDE_SOURCED_OR_EXECUTED' 'design-step2b-prelude.sh was sourced'
rm -f "$design_order/.pause-requested"
set +e
run_wrapper "$design_order" "$plugin_order"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail 'success order run should exit cleanly'
assert_order "$TMP_ROOT/call.log" 'timing design Step 2b — plan' 'launch success' 'timing mark must happen before drafter launch'
assert_not_called "$TMP_ROOT/call.log" 'PRELUDE_SOURCED_OR_EXECUTED' 'design-step2b-prelude.sh was sourced on success'
pass 'prelude merge order is preserved'

# 3 Unset drafter defaults to Codex when the binary is present.
plugin_default="$TMP_ROOT/plugin-default"
design_default="$TMP_ROOT/design-default"
make_fake_plugin "$plugin_default"
setup_design_tmp "$design_default" "$plugin_default" "__omit__"
install_launcher "$plugin_default" success
install_claude_launcher "$plugin_default" success
: >"$TMP_ROOT/call.log"
set +e
CALL_LOG="$TMP_ROOT/call.log" POSTPLAN_ARGV_FILE="$design_default/postplan.argv" \
  env -u IMPLEMENT_TMPDIR -u LARCH_TOKEN_LEDGER -u LARCH_DESIGN_DRAFTER CLAUDE_PLUGIN_ROOT="$plugin_default" \
  "$WRAPPER" --session-env-path "$design_default/session.env" --claude-pid 4242 >"$design_default/stdout.txt" 2>"$design_default/stderr.txt"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail 'default Codex route should exit cleanly'
assert_contains "$TMP_ROOT/call.log" 'launch success' 'default route did not launch Codex'
assert_not_called "$TMP_ROOT/call.log" 'launch-claude' 'default route should not launch Claude'
assert_contains "$design_default/stdout.txt" 'DRAFTER_VENDOR=codex' 'default route vendor row missing'
assert_contains "$design_default/stdout.txt" 'POSTPLAN_STATUS=ok' 'default route postplan row missing'
pass 'unset drafter defaults to Codex when binary present'

# 4 Explicit Claude route honors the model override.
plugin_claude="$TMP_ROOT/plugin-claude"
design_claude="$TMP_ROOT/design-claude"
make_fake_plugin "$plugin_claude"
setup_design_tmp "$design_claude" "$plugin_claude" "claude"
printf "export LARCH_DESIGN_PLAN_MODEL='claude-custom-plan'\n" >> "$design_claude/session.env"
install_launcher "$plugin_claude" success
install_claude_launcher "$plugin_claude" success
set +e
run_wrapper "$design_claude" "$plugin_claude"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail 'explicit Claude route should exit cleanly'
assert_contains "$TMP_ROOT/call.log" 'launch-claude model=claude-custom-plan mode=success' 'explicit Claude route did not pass override model'
assert_not_called "$TMP_ROOT/call.log" 'launch success' 'explicit Claude route should not launch Codex'
assert_contains "$design_claude/stdout.txt" 'DRAFTER_VENDOR=claude' 'explicit Claude vendor row missing'
pass 'explicit Claude route honors model override'

# 5 Drafter failure keeps fallback-only behavior.
plugin_fail="$TMP_ROOT/plugin-fail"
design_fail="$TMP_ROOT/design-fail"
make_fake_plugin "$plugin_fail"
setup_design_tmp "$design_fail" "$plugin_fail"
install_launcher "$plugin_fail" failure
printf 'stale summary\n' >"$design_fail/plan-summary.md"
printf 'stale scout\n' >"$design_fail/scout-plan-manifest.json"
set +e
run_wrapper "$design_fail" "$plugin_fail"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail 'fallback path should exit cleanly'
[[ ! -e "$design_fail/plan-summary.md" ]] || fail 'fallback did not remove stale plan-summary.md'
[[ ! -e "$design_fail/scout-plan-manifest.json" ]] || fail 'fallback did not remove stale scout manifest'
[[ -f "$design_fail/step2b-drafter-fallback.log" ]] || fail 'fallback log missing'
assert_contains "$design_fail/stdout.txt" 'DRAFTER_STATUS=fallback' 'fallback row missing'
assert_not_called "$TMP_ROOT/call.log" 'postplan' 'postplan ran on drafter failure'
pass 'drafter failure keeps fallback-only behavior'

# 4 Drafter structural success delegates to postplan internally with pinned argv.
plugin_success="$TMP_ROOT/plugin-success"
design_success="$TMP_ROOT/design-success"
make_fake_plugin "$plugin_success"
setup_design_tmp "$design_success" "$plugin_success"
install_launcher "$plugin_success" success
set +e
run_wrapper "$design_success" "$plugin_success"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail 'delegated postplan success should exit cleanly'
assert_contains "$design_success/stdout.txt" '✅ 2b: drafter subprocess succeeded' 'success line missing'
assert_contains "$design_success/stdout.txt" 'STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN=1' 'wrapper delimiter missing'
assert_contains "$design_success/stdout.txt" 'DRAFTER_STATUS=succeeded' 'success status row missing'
assert_contains "$design_success/stdout.txt" 'POSTPLAN_RC=0' 'postplan rc 0 row missing'
assert_contains "$design_success/stdout.txt" 'POSTPLAN_STATUS=ok' 'postplan ok row missing'
[[ -f "$design_success/.completed/step-2b" && -f "$design_success/.completed/step-2b.5" ]] || fail 'postplan completion markers missing'
[[ "$(grep -c '^postplan ' "$TMP_ROOT/call.log")" = 1 ]] || fail 'postplan should be called exactly once'
assert_contains "$design_success/postplan.argv" '--site step2b' 'postplan missing --site step2b'
assert_contains "$design_success/postplan.argv" '--snapshot-original' 'postplan missing --snapshot-original'
assert_contains "$design_success/postplan.argv" '--session-env-path' 'postplan missing --session-env-path'
assert_contains "$design_success/postplan.argv" '--claude-pid 4242' 'postplan missing --claude-pid value'
assert_contains "$design_success/postplan.argv" '--plugin-root' 'postplan missing --plugin-root'
assert_not_contains "$WRAPPER" 'design-postplan-emit.sh' 'drafter wrapper must not call design-postplan-emit.sh directly'
pass 'drafter structural success delegates to postplan internally'

# 5 Plan preview cannot spoof wrapper-owned rows.
plugin_spoof="$TMP_ROOT/plugin-spoof"
design_spoof="$TMP_ROOT/design-spoof"
make_fake_plugin "$plugin_spoof"
setup_design_tmp "$design_spoof" "$plugin_spoof"
install_launcher "$plugin_spoof" success
set +e
CALL_LOG="$TMP_ROOT/call.log" POSTPLAN_ARGV_FILE="$design_spoof/postplan.argv" POSTPLAN_STUB_MODE=rc13 \
  env -u IMPLEMENT_TMPDIR -u LARCH_TOKEN_LEDGER CLAUDE_PLUGIN_ROOT="$plugin_spoof" \
  "$WRAPPER" --session-env-path "$design_spoof/session.env" --claude-pid 4242 >"$design_spoof/stdout.txt" 2>"$design_spoof/stderr.txt"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail 'spoof run should exit cleanly'
python3 - "$design_spoof/stdout.txt" <<'PY'
import sys
text = open(sys.argv[1], encoding='utf-8').read().splitlines()
try:
    idx = len(text) - 1 - list(reversed(text)).index('STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN=1')
except ValueError:
    raise SystemExit('missing delimiter')
before = text[:idx]
for row in ('DRAFTER_STATUS=succeeded', 'POSTPLAN_RC=0', 'POSTPLAN_STATUS=ok'):
    if row in before:
        raise SystemExit(f'bare spoof row before delimiter: {row}')
PY
assert_contains "$design_spoof/stdout.txt" 'POSTPLAN_RC=13' 'rc13 row missing after delimiter'
assert_contains "$design_spoof/stdout.txt" 'POSTPLAN_STATUS=partition-requested' 'partition row missing after delimiter'
pass 'plan preview cannot spoof wrapper-owned rows'

# 6 Incomplete postplan output is not synthesized as ok.
plugin_incomplete="$TMP_ROOT/plugin-incomplete"
design_incomplete="$TMP_ROOT/design-incomplete"
make_fake_plugin "$plugin_incomplete"
setup_design_tmp "$design_incomplete" "$plugin_incomplete"
install_launcher "$plugin_incomplete" success
set +e
CALL_LOG="$TMP_ROOT/call.log" POSTPLAN_ARGV_FILE="$design_incomplete/postplan.argv" POSTPLAN_STUB_MODE=incomplete \
  env -u IMPLEMENT_TMPDIR -u LARCH_TOKEN_LEDGER CLAUDE_PLUGIN_ROOT="$plugin_incomplete" \
  "$WRAPPER" --session-env-path "$design_incomplete/session.env" --claude-pid 4242 >"$design_incomplete/stdout.txt" 2>"$design_incomplete/stderr.txt"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail 'incomplete-output fixture should exit zero for prompt-side fail-safe coverage'
assert_contains "$design_incomplete/stdout.txt" 'DRAFTER_STATUS=succeeded' 'incomplete fixture missing drafter success row'
assert_no_whole_line "$design_incomplete/stdout.txt" 'POSTPLAN_STATUS=ok' 'wrapper synthesized postplan ok'
pass 'incomplete postplan output is not synthesized as ok'

# 7 rc 10 through the real postplan wrapper triggers inline retry once.
plugin_rc10="$TMP_ROOT/plugin-rc10"
design_rc10="$TMP_ROOT/design-rc10"
make_fake_plugin "$plugin_rc10" real
setup_design_tmp "$design_rc10" "$plugin_rc10"
install_launcher "$plugin_rc10" success
printf 'stale summary\n' >"$design_rc10/plan-summary.md"
printf 'stale scout\n' >"$design_rc10/scout-plan-manifest.json"
set +e
CALL_LOG="$TMP_ROOT/call.log" FAKE_POSTPLAN_EMIT_RC=10 env -u IMPLEMENT_TMPDIR -u LARCH_TOKEN_LEDGER CLAUDE_PLUGIN_ROOT="$plugin_rc10" \
  "$WRAPPER" --session-env-path "$design_rc10/session.env" --claude-pid 4242 >"$design_rc10/stdout.txt" 2>"$design_rc10/stderr.txt"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail 'rc10 wrapper path should exit zero'
[[ -f "$design_rc10/.step2b-postplan-inline-retry-pending" ]] || fail 'inline retry pending sentinel missing'
[[ -f "$design_rc10/.step2b-postplan-inline-retry-done" ]] || fail 'inline retry done sentinel missing'
[[ ! -e "$design_rc10/plan-summary.md" && ! -e "$design_rc10/scout-plan-manifest.json" ]] || fail 'rc10 did not clear stale plan summary/scout'
assert_contains "$design_rc10/stdout.txt" 'SCOUT_STALE_CLEARED=true' 'rc10 stale scout row missing'
assert_contains "$design_rc10/stdout.txt" '**⚠ 2b: drafter plan failed postplan validation — re-entering inline drafting once**' 'rc10 warning changed'
pass 'drafter structural success with postplan rc 10 triggers inline retry once'

# 8 rc 11 rows are emitted by the real postplan wrapper before pause-save.
plugin_rc11="$TMP_ROOT/plugin-rc11"
design_rc11="$TMP_ROOT/design-rc11"
make_fake_plugin "$plugin_rc11" real
setup_design_tmp "$design_rc11" "$plugin_rc11"
install_launcher "$plugin_rc11" success
set +e
CALL_LOG="$TMP_ROOT/call.log" FAKE_POSTPLAN_EMIT_RC=11 env -u IMPLEMENT_TMPDIR -u LARCH_TOKEN_LEDGER CLAUDE_PLUGIN_ROOT="$plugin_rc11" \
  "$WRAPPER" --session-env-path "$design_rc11/session.env" --claude-pid 4242 >"$design_rc11/stdout.txt" 2>"$design_rc11/stderr.txt"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail 'rc11 wrapper path should pause-save cleanly'
assert_contains "$design_rc11/stdout.txt" 'POSTPLAN_RC=11' 'rc11 row missing'
assert_contains "$design_rc11/stdout.txt" 'POSTPLAN_STATUS=pause-save' 'pause-save status row missing'
assert_no_whole_line "$design_rc11/stdout.txt" 'POSTPLAN_STATUS=ok' 'rc11 synthesized ok'
assert_contains "$TMP_ROOT/call.log" 'pause-save step2a=yes --design-tmpdir' 'pause-save not invoked through real postplan wrapper'
assert_contains "$TMP_ROOT/call.log" '--issue 1' 'pause-save issue not preserved'
assert_contains "$TMP_ROOT/call.log" '--repo example/repo' 'pause-save repo not preserved'
# Distinct pre-emit pause branch.
design_pre_pause="$TMP_ROOT/design-pre-pause"
setup_design_tmp "$design_pre_pause" "$plugin_rc11"
: >"$design_pre_pause/.pause-requested"
set +e
CALL_LOG="$TMP_ROOT/call.log" env -u IMPLEMENT_TMPDIR -u LARCH_TOKEN_LEDGER CLAUDE_PLUGIN_ROOT="$plugin_rc11" \
  "$POSTPLAN_REAL" --session-env-path "$design_pre_pause/session.env" --claude-pid 4242 --plugin-root "$plugin_rc11" --site step2b >"$design_pre_pause/stdout.txt" 2>"$design_pre_pause/stderr.txt"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail 'pre-emit pause path should pause-save cleanly'
assert_contains "$design_pre_pause/stdout.txt" 'POSTPLAN_RC=11' 'pre-emit rc11 row missing'
assert_contains "$design_pre_pause/stdout.txt" 'POSTPLAN_STATUS=pause-save' 'pre-emit pause status row missing'
pass 'real postplan rc 11 preserves pause-save rows'

# 9 Fatal postplan arms fail closed.
for fatal_rc in 1 2 7; do
    plugin_fatal="$TMP_ROOT/plugin-fatal-$fatal_rc"
    design_fatal="$TMP_ROOT/design-fatal-$fatal_rc"
    make_fake_plugin "$plugin_fatal" real
    setup_design_tmp "$design_fatal" "$plugin_fatal"
    install_launcher "$plugin_fatal" success
    set +e
    CALL_LOG="$TMP_ROOT/call.log" FAKE_POSTPLAN_EMIT_RC="$fatal_rc" env -u IMPLEMENT_TMPDIR -u LARCH_TOKEN_LEDGER CLAUDE_PLUGIN_ROOT="$plugin_fatal" \
      "$WRAPPER" --session-env-path "$design_fatal/session.env" --claude-pid 4242 >"$design_fatal/stdout.txt" 2>"$design_fatal/stderr.txt"
    rc=$?
    set -e
    [[ "$rc" -ne 0 ]] || fail "fatal rc $fatal_rc should fail closed"
    assert_not_called "$TMP_ROOT/call.log" 'postplan-failsafe' "fatal rc $fatal_rc should not simulate a second postplan"
done
pass 'fatal postplan arms fail closed'

# 10 rc 12 and rc 13 routing rows are preserved.
for route_rc in 12 13; do
    plugin_route="$TMP_ROOT/plugin-route-$route_rc"
    design_route="$TMP_ROOT/design-route-$route_rc"
    make_fake_plugin "$plugin_route" real
    setup_design_tmp "$design_route" "$plugin_route"
    install_launcher "$plugin_route" success
    set +e
    CALL_LOG="$TMP_ROOT/call.log" FAKE_POSTPLAN_EMIT_RC="$route_rc" env -u IMPLEMENT_TMPDIR -u LARCH_TOKEN_LEDGER CLAUDE_PLUGIN_ROOT="$plugin_route" \
      "$WRAPPER" --session-env-path "$design_route/session.env" --claude-pid 4242 >"$design_route/stdout.txt" 2>"$design_route/stderr.txt"
    rc=$?
    set -e
    [[ "$rc" -eq 0 ]] || fail "route rc $route_rc should exit zero through thin wrapper"
    [[ -f "$design_route/.completed/step-2b" ]] || fail "route rc $route_rc missing step-2b completion"
    if [[ "$route_rc" == 12 ]]; then
      assert_contains "$design_route/stdout.txt" 'POSTPLAN_STATUS=plan-size-trigger' 'rc12 status row missing'
    else
      assert_contains "$design_route/stdout.txt" 'POSTPLAN_STATUS=partition-requested' 'rc13 status row missing'
    fi
done
pass 'rc 12 and rc 13 routing rows are preserved'

# 11 Dirty-tree recovery does not run postplan.
plugin_dirty="$TMP_ROOT/plugin-dirty"
design_dirty="$TMP_ROOT/design-dirty"
make_fake_plugin "$plugin_dirty"
setup_design_tmp "$design_dirty" "$plugin_dirty"
install_launcher "$plugin_dirty" dirty
set +e
run_wrapper "$design_dirty" "$plugin_dirty"
rc=$?
set -e
[[ "$rc" -eq 0 ]] || fail 'dirty-tree path should exit cleanly'
assert_contains "$design_dirty/dirty-tree-detected.env" 'STAGE=step-2b-drafter' 'dirty tree stage changed'
assert_contains "$design_dirty/dirty-tree-detected.env" 'RECOVERY_REQUIRED=true' 'dirty tree recovery row missing'
assert_contains "$design_dirty/stdout.txt" 'DRAFTER_STATUS=dirty-tree' 'dirty-tree status row missing'
assert_not_called "$TMP_ROOT/call.log" 'postplan' 'postplan ran on dirty-tree recovery'
pass 'dirty-tree recovery does not run postplan'

# Token sidecar scenarios also satisfy folded-prelude setup and postplan scaffolding.
plugin1="$TMP_ROOT/plugin-token-stale"
design1="$TMP_ROOT/design-token-stale"
mkdir -p "$design1"
make_fake_plugin "$plugin1"
setup_design_tmp "$design1" "$plugin1"
install_launcher "$plugin1" token-failure
printf 'TOOL=codex\nINPUT=1\nOUTPUT=1\nTOTAL=2\nRAW=codex_plan_draft\n' > "$design1/step2b-drafter-status.txt.token-record"
run_wrapper "$design1" "$plugin1" || true
[[ ! -e "$design1/token-report.ndjson" ]] || fail 'stale sidecar was appended to token-report.ndjson'
if compgen -G "$design1/larch-tokens-*.jsonl" >/dev/null; then
    fail 'stale sidecar reached active ledger'
fi
pass 'stale Codex drafter sidecar cleanup'

plugin2="$TMP_ROOT/plugin-token-fresh"
design2="$TMP_ROOT/design-token-fresh"
impl2="$TMP_ROOT/implement2"
stale_ledger2="$TMP_ROOT/stale-ledger2.jsonl"
mkdir -p "$design2" "$impl2"
make_fake_plugin "$plugin2"
setup_design_tmp "$design2" "$plugin2"
install_launcher "$plugin2" token-success
{
    printf "export IMPLEMENT_TMPDIR='%s'\n" "$impl2"
    printf "export LARCH_TOKEN_LEDGER='%s'\n" "$stale_ledger2"
    printf "export LARCH_TOKEN_SESSION_ID='stale-parent-session'\n"
} >> "$design2/session.env"
run_wrapper "$design2" "$plugin2"
[[ -f "$design2/token-report.ndjson" ]] || fail 'missing token-report.ndjson'
[[ "$(grep -c 'codex_plan_draft' "$design2/token-report.ndjson")" = 1 ]] || fail 'expected one codex_plan_draft NDJSON row'
ledger_count=$(grep -h -c 'codex_plan_draft' "$design2"/larch-tokens-*.jsonl 2>/dev/null || true)
[[ "$ledger_count" = 1 ]] || fail 'expected one active ledger codex_plan_draft row'
if compgen -G "$impl2/larch-tokens-*.jsonl" >/dev/null; then
    fail 'design drafter wrote active ledger under IMPLEMENT_TMPDIR'
fi
[[ ! -e "$stale_ledger2" ]] || fail 'design drafter wrote active ledger to stale LARCH_TOKEN_LEDGER'
grep -Fq '"model":"gpt-5.5"' "$design2/token-report.ndjson" || fail 'missing model in NDJSON row'
grep -h -Fq '"model":"gpt-5.5"' "$design2"/larch-tokens-*.jsonl || fail 'missing model in active ledger row'
if grep -h -Fq 'stale-parent-session' "$design2"/larch-tokens-*.jsonl; then
    fail 'design drafter used stale LARCH_TOKEN_SESSION_ID'
fi
pass 'fresh Codex drafter sidecar exactly-once ingestion'

printf 'PASS: test-design-step2b-drafter.sh\n'
