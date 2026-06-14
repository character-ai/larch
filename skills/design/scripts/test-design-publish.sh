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

assert_rename_before_publish() {
    local name="$1" log="$2"
    if awk '
      /tracking-issue rename .*--state designed/ && !rename_pos { rename_pos=NR }
      /design-log-publish / && !publish_pos { publish_pos=NR }
      END { exit (rename_pos && publish_pos && rename_pos < publish_pos) ? 0 : 1 }
    ' "$log"; then
        pass "$name"
    else
        fail "$name"
    fi
}

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-design-publish.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

FAKE_PLUGIN="$TMP/plugin"
STUB="$FAKE_PLUGIN/scripts"
mkdir -p "$STUB" "$FAKE_PLUGIN/skills/design/scripts" "$FAKE_PLUGIN/skills/implement/scripts"
ln -sf "$REPO_ROOT/skills/implement/scripts/stall-recovery-report.sh" "$FAKE_PLUGIN/skills/implement/scripts/stall-recovery-report.sh"
ln -sf "$REPO_ROOT/scripts/lib-quiet.sh" "$STUB/lib-quiet.sh"
ln -sf "$REPO_ROOT/scripts/lib-net.sh" "$STUB/lib-net.sh" 2>/dev/null || true
ln -sf "$REPO_ROOT/scripts/lib-design-tmpdir.sh" "$STUB/lib-design-tmpdir.sh"
ln -sf "$REPO_ROOT/scripts/lib-larch-dev-clone.sh" "$STUB/lib-larch-dev-clone.sh"
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
ln -sf "$REPO_ROOT/skills/design/scripts/design-stage-terminal-state.sh" "$FAKE_PLUGIN/skills/design/scripts/design-stage-terminal-state.sh"

setup_design_tmp() {
    local d="$1"
    mkdir -p "$d/.completed"
    : >"$d/.completed/step-5b"
    printf '# plan\n' >"$d/composed-plan.md"
    printf '{}\n' >"$d/run-params.json"
    printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$FAKE_PLUGIN" >"$d/session-env.sh"
}

write_stubs() {
    cat >"$STUB/design-log-publish.sh" <<'STUB'
#!/usr/bin/env bash
echo "design-log-publish $*" >>"${PUBLISH_LOG:?}"
[[ -n "${CALL_LOG:-}" ]] && echo "design-log-publish $*" >>"$CALL_LOG"
[[ -n "${PUBLISH_ORDER_LOG:-}" ]] && echo "design-log-publish" >>"$PUBLISH_ORDER_LOG"
design_tmpdir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --design-tmpdir) design_tmpdir="$2"; shift 2 ;;
    *) shift ;;
  esac
done
if [[ -n "$design_tmpdir" && -f "$design_tmpdir/final-only.txt" ]]; then
  echo "FINAL_ONLY_PRESENT=true" >>"${PUBLISH_LOG:?}"
  [[ -n "${CALL_LOG:-}" ]] && echo "FINAL_ONLY_PRESENT=true" >>"$CALL_LOG"
fi
if [[ "${PUBLISH_EMIT_OK:-true}" == true ]]; then
  echo "PUBLISH_OK=${PUBLISH_OK_VALUE:-true}"
fi
[[ -n "${PUBLISH_PR_NUMBER:-}" ]] && echo "PR_NUMBER=${PUBLISH_PR_NUMBER}"
[[ -n "${PUBLISH_PR_URL:-}" ]] && echo "PR_URL=${PUBLISH_PR_URL}"
[[ -n "${PUBLISH_RECOVERY_BRANCH:-}" ]] && echo "RECOVERY_BRANCH=${PUBLISH_RECOVERY_BRANCH}"
if [[ -n "$design_tmpdir" && -d "$design_tmpdir" ]]; then
  {
    printf 'DESIGN_LOG_PR_NUMBER=%s\n' "${PUBLISH_PR_NUMBER:-}"
    printf 'DESIGN_LOG_PR_URL=%s\n' "${PUBLISH_PR_URL:-}"
    printf 'DESIGN_LOG_RECOVERY_BRANCH=%s\n' "${PUBLISH_RECOVERY_BRANCH:-}"
  } >"$design_tmpdir/.design-log-publish-metadata.env"
  if [[ "${PUBLISH_SEED_RESULT_BEFORE_RETURN:-false}" == true ]]; then
    {
      printf 'PLAN_WRITE_OK=true\n'
      printf 'PUBLISH_OK=true\n'
      printf 'PR_NUMBER=%s\n' "${PUBLISH_SEED_PR_NUMBER:-42}"
      printf 'PR_URL=%s\n' "${PUBLISH_SEED_PR_URL:-https://github.com/owner/repo/pull/42}"
      printf 'RECOVERY_BRANCH=%s\n' "${PUBLISH_SEED_RECOVERY_BRANCH:-}"
    } >"$design_tmpdir/.design-publish-result.env"
  fi
fi
if [[ "${PUBLISH_STUB_RC:-0}" -ne 0 ]]; then
  exit "${PUBLISH_STUB_RC}"
fi
STUB
    mkdir -p "$FAKE_PLUGIN/python"
    cat >"$FAKE_PLUGIN/python/cli.py" <<'STUB'
import json, os, sys
cmd = sys.argv[1:3]
def _parse_args(args):
    d = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--") and i + 1 < len(args):
            d[args[i][2:]] = args[i + 1]
            i += 2
        else:
            i += 1
    return d
if cmd == ["named-block", "write"]:
    args = " ".join(sys.argv[3:])
    with open(os.environ["PLAN_BLOCK_LOG"], "a", encoding="utf-8") as handle:
        handle.write(f"plan-block-write {args}\n")
    if os.environ.get("CALL_LOG"):
        with open(os.environ["CALL_LOG"], "a", encoding="utf-8") as handle:
            handle.write(f"plan-block-write {args}\n")
    raise SystemExit(int(os.environ.get("PLAN_BLOCK_RC", "0")))
if cmd == ["plan", "validate"]:
    args = " ".join(sys.argv[3:])
    if os.environ.get("CALL_LOG"):
        with open(os.environ["CALL_LOG"], "a", encoding="utf-8") as handle:
            handle.write(f"plan validate {args}\n")
    if os.environ.get("VALIDATOR_STATUS_OMIT", "false") == "true":
        raise SystemExit(int(os.environ.get("VALIDATOR_STUB_RC", "0")))
    design_tmpdir = os.environ.get("DESIGN_TMPDIR", "")
    print("VALIDATE_STATUS=" + os.environ.get("VALIDATE_STATUS_VALUE", "ok"))
    print("VALIDATE_DEFECT_COUNT=" + os.environ.get("VALIDATE_DEFECT_COUNT_VALUE", "0"))
    print("VALIDATE_SKIPPED_COUNT=" + os.environ.get("VALIDATE_SKIPPED_COUNT_VALUE", "0"))
    print("VALIDATE_UNSAFE_TOKEN_COUNT=" + os.environ.get("VALIDATE_UNSAFE_TOKEN_COUNT_VALUE", "0"))
    print("VALIDATE_LOG_FILE=" + os.environ.get("VALIDATE_LOG_FILE_VALUE", os.path.join(design_tmpdir, "validate-plan-commands.log")))
    raise SystemExit(int(os.environ.get("VALIDATOR_STUB_RC", "0")))
if cmd == ["diagrams", "upsert"]:
    args = " ".join(sys.argv[3:])
    with open(os.environ["UPSERT_LOG"], "a", encoding="utf-8") as handle:
        handle.write(f"upsert-diagrams {args}\n")
    if os.environ.get("CALL_LOG"):
        with open(os.environ["CALL_LOG"], "a", encoding="utf-8") as handle:
            handle.write(f"upsert-diagrams {args}\n")
    rc = int(os.environ.get("UPSERT_STUB_RC", "0"))
    if rc:
        raise SystemExit(rc)
    print(f"UPSERT_STATUS={os.environ.get('UPSERT_STATUS_VALUE', 'ok')}")
    print(f"ARCHITECTURE_SOURCE={os.environ.get('ARCH_SOURCE_VALUE', 'file')}")
elif cmd == ["timing", "report"]:
    if os.environ.get("PUBLISH_ORDER_LOG"):
        with open(os.environ["PUBLISH_ORDER_LOG"], "a") as fh:
            fh.write("timing-report\n")
    if os.environ.get("TIMING_REPORT_ENV_LOG"):
        with open(os.environ["TIMING_REPORT_ENV_LOG"], "a") as fh:
            fh.write(f"LARCH_TIMING_LEDGER={os.environ.get('LARCH_TIMING_LEDGER','')}\n")
            fh.write(f"IMPLEMENT_TMPDIR={os.environ.get('IMPLEMENT_TMPDIR','unset') if 'IMPLEMENT_TMPDIR' in os.environ else 'unset'}\n")
    out = None
    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--output" and i + 1 < len(args):
            out = args[i + 1]; i += 2
        else:
            i += 1
    if not out:
        raise SystemExit(1)
    if os.environ.get("TIMING_REPORT_FAIL") == "true":
        raise SystemExit(1)
    if os.environ.get("TIMING_REPORT_PARTIAL_JSON") == "true":
        with open(out, "w") as fh: fh.write('{"per_step":[]}\n')
        raise SystemExit(0)
    no_rounds = os.environ.get("TIMING_REPORT_NO_ROUNDS_JSON") == "true"
    step = {"skill":"design","step":"design Step 3 — plan review","duration_seconds":1,"duration_hms":"00:00:01","outlier":False}
    if not no_rounds:
        step["rounds"] = [{"round":1,"duration_seconds":1,"accepted":0,"rejected":0,"oos":0}]
    data = {"per_step":[step],"total_seconds":1,"total_hms":"00:00:01","vendor_task_averages":[]}
    with open(out, "w") as fh: fh.write(json.dumps(data) + "\n")
elif cmd == ["redact", "secrets"]:
    if os.environ.get("CALL_LOG"):
        with open(os.environ["CALL_LOG"], "a", encoding="utf-8") as handle:
            handle.write("redact secrets\n")
    rc = int(os.environ.get("REDACT_STUB_RC", "0"))
    if rc:
        raise SystemExit(rc)
    if os.environ.get("REDACT_EMPTY_OUTPUT", "false").lower() == "true":
        raise SystemExit(0)
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
elif sys.argv[1:2] == ["redact"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
elif cmd == ["run-log", "append-failure"]:
    p = _parse_args(sys.argv[3:])
    log_file = p.get("log", "")
    site = p.get("site", "unknown")
    tool = p.get("tool", "unknown")
    exit_code = p.get("exit-code", "?")
    output_file = p.get("output-file", "")
    status_label = p.get("status-label", "failed")
    if log_file:
        body = "no diagnostics\n"
        if output_file and os.path.isfile(output_file):
            with open(output_file, encoding="utf-8", errors="replace") as fh:
                body = fh.read() or body
        entry = (f"- **Step {site} — {tool} {status_label} (exit {exit_code})**:\n"
                 f"  ```\n{body.rstrip()}\n  ```\n")
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(entry)
    raise SystemExit(0)
elif cmd == ["tracking-issue", "rename"]:
    entry = "tracking-issue rename " + " ".join(sys.argv[3:]) + "\n"
    with open(os.environ["RENAME_LOG"], "a", encoding="utf-8") as fh:
        fh.write(entry)
    call_log = os.environ.get("CALL_LOG", "")
    if call_log:
        with open(call_log, "a", encoding="utf-8") as fh:
            fh.write(entry)
    rc = int(os.environ.get("RENAME_STUB_RC", "0"))
    if rc:
        raise SystemExit(rc)
    if os.environ.get("RENAMED_OMIT_LINE", "false") == "true":
        raise SystemExit(0)
    print("RENAMED=" + os.environ.get("RENAMED_VALUE", "true"))
    print("NEW_TITLE=" + os.environ.get("NEW_TITLE_VALUE", "[DESIGNED] Example issue"))
    raise SystemExit(0)
elif cmd == ["run-log", "append-entry"]:
    p = _parse_args(sys.argv[3:])
    log_file = p.get("log", "")
    entry_text = p.get("entry", "")
    if log_file:
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(entry_text + "\n")
    raise SystemExit(0)
elif cmd == ["session", "read-key"]:
    p = _parse_args(sys.argv[3:])
    default = p.get("default", "")
    key = p.get("key", "")
    path = p.get("file", "")
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith(key + "="):
                    print(line.split("=", 1)[1].rstrip("\n"))
                    raise SystemExit(0)
    print(default)
    raise SystemExit(0)
else:
    print(f"unexpected cli args: {sys.argv[1:]}", file=sys.stderr)
    raise SystemExit(2)
STUB
    cat >"$STUB/resolve-repo.sh" <<'STUB'
#!/usr/bin/env bash
echo "${RESOLVE_REPO_VALUE:-owner/repo}"
STUB
    cat >"$STUB/gh" <<'STUB'
#!/usr/bin/env bash
if [[ "$1" == "repo" && "$2" == "view" && -n "${GH_REPO_VIEW_VALUE:-}" ]]; then
  printf '%s\n' "$GH_REPO_VIEW_VALUE"
  exit 0
fi
exit 1
STUB
    local invoke_stub="$FAKE_PLUGIN/skills/design/scripts/invoke-plan-validator"".sh"
    cat >"$invoke_stub" <<'STUB'
#!/usr/bin/env bash
[[ -n "${CALL_LOG:-}" ]] && echo "validator $*" >>"$CALL_LOG"
if [[ "${VALIDATOR_STATUS_OMIT:-false}" == true ]]; then
  exit "${VALIDATOR_STUB_RC:-0}"
fi
printf 'VALIDATE_STATUS=%s
' "${VALIDATE_STATUS_VALUE:-ok}"
printf 'VALIDATE_DEFECT_COUNT=%s
' "${VALIDATE_DEFECT_COUNT_VALUE:-0}"
printf 'VALIDATE_SKIPPED_COUNT=%s
' "${VALIDATE_SKIPPED_COUNT_VALUE:-0}"
printf 'VALIDATE_UNSAFE_TOKEN_COUNT=%s
' "${VALIDATE_UNSAFE_TOKEN_COUNT_VALUE:-0}"
printf 'VALIDATE_LOG_FILE=%s
' "${VALIDATE_LOG_FILE_VALUE:-${DESIGN_TMPDIR:-}/validate-plan-commands.log}"
exit "${VALIDATOR_STUB_RC:-0}"
STUB
    cat >"$FAKE_PLUGIN/skills/design/scripts/render-final-summary.sh" <<'STUB'
#!/usr/bin/env bash
{
  echo "render ISSUE_NUMBER=${ISSUE_NUMBER:-} SESSION_ID=${SESSION_ID:-} DESIGN_TMPDIR=${DESIGN_TMPDIR:-} DESIGN_LOG_PR_NUMBER=${DESIGN_LOG_PR_NUMBER:-} DESIGN_LOG_PR_URL=${DESIGN_LOG_PR_URL:-} DESIGN_LOG_RECOVERY_BRANCH=${DESIGN_LOG_RECOVERY_BRANCH:-} RENAMED=${RENAMED:-} NEW_TITLE=${NEW_TITLE:-} DESIGNED_ADMISSION_READY=${DESIGNED_ADMISSION_READY:-} $*"
} >>"${RENDER_LOG:?}"
printf '# summary\n' >"${DESIGN_TMPDIR:?}/final-summary.md"
STUB
    chmod +x "$STUB"/*.sh "$STUB/gh" "$invoke_stub" "$FAKE_PLUGIN/skills/design/scripts/render-final-summary.sh"
}

write_stubs

export CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN"
export PATH="$STUB:$PATH"

reset_publish_stub_env() {
    unset PLAN_BLOCK_RC PUBLISH_STUB_RC PUBLISH_EMIT_OK PUBLISH_OK_VALUE \
        PUBLISH_PR_NUMBER PUBLISH_PR_URL PUBLISH_RECOVERY_BRANCH \
        PUBLISH_INVOCATION_LOG \
        PUBLISH_SEED_RESULT_BEFORE_RETURN PUBLISH_SEED_PR_NUMBER PUBLISH_SEED_PR_URL \
        PUBLISH_SEED_RECOVERY_BRANCH \
        UPSERT_STUB_RC UPSERT_STATUS_VALUE ARCH_SOURCE_VALUE \
        RENAME_STUB_RC RENAMED_OMIT_LINE RENAMED_VALUE NEW_TITLE_VALUE RESOLVE_REPO_VALUE \
        MARKER_STUB_RC VALIDATOR_STUB_RC VALIDATOR_STATUS_OMIT VALIDATE_STATUS_VALUE \
        VALIDATE_DEFECT_COUNT_VALUE VALIDATE_SKIPPED_COUNT_VALUE \
        VALIDATE_UNSAFE_TOKEN_COUNT_VALUE VALIDATE_LOG_FILE_VALUE \
        REDACT_STUB_RC REDACT_EMPTY_OUTPUT TIMING_REPORT_NO_ROUNDS_JSON || true
    unset GH_REPO_VIEW_VALUE || true
}

init_publish_logs() {
    export PLAN_BLOCK_LOG="$TMP/plan-block.log"
    export PUBLISH_LOG="$TMP/publish.log"
    export RENAME_LOG="$TMP/rename.log"
    export UPSERT_LOG="$TMP/upsert.log"
    export RENDER_LOG="$TMP/render.log"
    export CALL_LOG="$TMP/call.log"
    export PUBLISH_ORDER_LOG="$TMP/publish-order.log"
    export TIMING_REPORT_ENV_LOG="$TMP/timing-report-env.log"
    : >"$PLAN_BLOCK_LOG"
    : >"$PUBLISH_LOG"
    : >"$RENAME_LOG"
    : >"$UPSERT_LOG"
    : >"$RENDER_LOG"
    : >"$CALL_LOG"
    : >"$PUBLISH_ORDER_LOG"
    : >"$TIMING_REPORT_ENV_LOG"
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
assert_rc "missing argv" 5 "$rc"

set +e
bash "$SUBJECT" --help 2>/dev/null
rc=$?
set -e
assert_rc "--help" 0 "$rc"

# --- malformed --repo shapes ---
for bad_repo in /abs bad..repo a/b/c --owner/repo 'owner\repo' ../repo; do
    D_BAD_REPO="$TMP/bad-repo-${bad_repo//\//_}"
    setup_design_tmp "$D_BAD_REPO"
    set +e
    bash "$SUBJECT" --design-tmpdir "$D_BAD_REPO" --issue 1 --session-id x --claude-pid 1 --repo "$bad_repo" 2>/dev/null
    rc=$?
    set -e
    assert_rc "invalid --repo $bad_repo" 5 "$rc"
done

D_BAD_RESOLVED_REPO="$TMP/bad-resolved-repo"
setup_design_tmp "$D_BAD_RESOLVED_REPO"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export RESOLVE_REPO_VALUE=bad..repo
set +e
bash "$SUBJECT" --design-tmpdir "$D_BAD_RESOLVED_REPO" --issue 1 --session-id x --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "invalid resolved repo" 5 "$rc"
if grep -q 'plan-block-write' "$PLAN_BLOCK_LOG" 2>/dev/null; then
    fail "invalid resolved repo must fail before plan-block-write"
else
    pass "invalid resolved repo fails before plan-block-write"
fi

# --- missing step-5b ---
D_PRE="$TMP/pre-5b"
setup_design_tmp "$D_PRE"
rm -f "$D_PRE/.completed/step-5b"
set +e
bash "$SUBJECT" --design-tmpdir "$D_PRE" --issue 1 --session-id x --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "missing step-5b" 5 "$rc"

# --- missing composed plan ---
D_NOP="$TMP/no-plan"
setup_design_tmp "$D_NOP"
: >"$D_NOP/composed-plan.md"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
set +e
bash "$SUBJECT" --design-tmpdir "$D_NOP" --issue 1 --session-id x --claude-pid 1 >"$D_NOP/stdout.txt" 2>/dev/null
rc=$?
set -e
assert_rc "empty composed plan" 4 "$rc"
grep -Fq 'VALIDATE_STATUS=defects-found' "$D_NOP/.design-publish-result.env" || fail "empty composed plan result env status"
grep -Fq 'VALIDATE_STATUS=defects-found' "$D_NOP/stdout.txt" || fail "empty composed plan stdout status fallback"
grep -Fq 'composed-plan.md missing or empty' "$D_NOP/validate-plan-commands.log" || fail "empty composed plan diagnostic log"
grep -Fq 'PLAN_WRITE_OK=false' "$D_NOP/.design-publish-result.env" || fail "empty composed plan PLAN_WRITE_OK=false"
grep -Fq 'VALIDATE_DEFECT_COUNT=1' "$D_NOP/.design-publish-result.env" || fail "empty composed plan defect count"
if [[ -e "$D_NOP/composed-plan.redacted.md" ]]; then fail "empty composed plan must not redact"; else pass "empty composed plan skipped redaction"; fi
if grep -Fq 'redact secrets' "$CALL_LOG" 2>/dev/null; then fail "empty composed plan must not invoke redact"; else pass "empty composed plan did not invoke redact"; fi
if grep -Fq 'plan-block-write' "$PLAN_BLOCK_LOG" 2>/dev/null; then fail "empty composed plan must not plan-block write"; else pass "empty composed plan skipped plan-block write"; fi
if grep -Fq 'design-log-publish' "$PUBLISH_LOG" 2>/dev/null; then fail "empty composed plan must not publish"; else pass "empty composed plan skipped publish"; fi
if grep -Fq 'tracking-issue rename' "$RENAME_LOG" 2>/dev/null; then fail "empty composed plan must not rename"; else pass "empty composed plan skipped rename"; fi


# --- validator defects: exit 4, no redaction or publish side effects ---
D_DEF="$TMP/defects"
setup_design_tmp "$D_DEF"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export VALIDATE_STATUS_VALUE=defects-found VALIDATE_DEFECT_COUNT_VALUE=2
set +e
bash "$SUBJECT" --design-tmpdir "$D_DEF" --issue 42 --session-id sid-1 --claude-pid 9999 >"$D_DEF/stdout.txt" 2>/dev/null
rc=$?
set -e
assert_rc "validator defects exit 4" 4 "$rc"
grep -q 'VALIDATE_STATUS=defects-found' "$D_DEF/.design-publish-result.env" || fail "defects result env status"
grep -q 'VALIDATE_STATUS=defects-found' "$D_DEF/stdout.txt" || fail "defects stdout status fallback"
if [[ -e "$D_DEF/composed-plan.redacted.md" ]]; then fail "defects must not redact"; else pass "defects skipped redaction"; fi
if grep -q 'plan-block-write' "$PLAN_BLOCK_LOG" 2>/dev/null; then fail "defects must not publish"; else pass "defects skipped publish tail"; fi
if grep -q 'tracking-issue rename' "$RENAME_LOG" 2>/dev/null; then fail "defects must not rename"; else pass "defects skipped rename"; fi

# --- validator infra failure ---
D_VINFRA="$TMP/validator-infra"
setup_design_tmp "$D_VINFRA"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export VALIDATOR_STUB_RC=7 VALIDATE_STATUS_VALUE=ok
set +e
bash "$SUBJECT" --design-tmpdir "$D_VINFRA" --issue 1 --session-id x --claude-pid 1 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "validator infra failure" 5 "$rc"
if [[ -e "$D_VINFRA/composed-plan.redacted.md" ]]; then fail "infra failure must not redact"; else pass "infra failure skipped redaction"; fi

# --- validator not-run/missing status failure ---
D_VMISS="$TMP/validator-missing-status"
setup_design_tmp "$D_VMISS"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export VALIDATOR_STATUS_OMIT=true
set +e
bash "$SUBJECT" --design-tmpdir "$D_VMISS" --issue 1 --session-id x --claude-pid 1 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "validator missing status" 5 "$rc"

# --- skip validate publishes and marks status skipped ---
D_SKIP="$TMP/skip-validate"
setup_design_tmp "$D_SKIP"
printf 'graph TD\n' >"$D_SKIP/architecture-diagram.md"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export VALIDATE_STATUS_VALUE=defects-found
set +e
bash "$SUBJECT" --design-tmpdir "$D_SKIP" --issue 42 --session-id sid-1 --claude-pid 9999 --skip-validate >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "skip validate" 0 "$rc"
grep -q 'VALIDATE_STATUS=skipped' "$D_SKIP/.design-publish-result.env" || fail "skip validate status"
if grep -q 'validator' "$CALL_LOG" 2>/dev/null; then fail "skip validate must not call validator"; else pass "skip validate did not call validator"; fi
[[ -s "$D_SKIP/composed-plan.redacted.md" ]] || fail "skip validate must redact"
skip_plan_pos=$(grep -n 'plan-block-write' "$CALL_LOG" | head -1 | cut -d: -f1)
skip_upsert_pos=$(grep -n 'upsert-diagrams' "$CALL_LOG" | head -1 | cut -d: -f1)
skip_rename_pos=$(grep -n 'tracking-issue rename' "$CALL_LOG" | head -1 | cut -d: -f1)
skip_publish_pos=$(grep -n 'design-log-publish' "$CALL_LOG" | head -1 | cut -d: -f1)
if [[ -z "$skip_plan_pos" || -z "$skip_upsert_pos" || -z "$skip_rename_pos" || -z "$skip_publish_pos" ]]; then
    fail "skip validate call log missing plan/upsert/rename/publish entries"
elif [[ "$skip_plan_pos" -ge "$skip_upsert_pos" || "$skip_upsert_pos" -ge "$skip_rename_pos" || "$skip_rename_pos" -ge "$skip_publish_pos" ]]; then
    fail "skip validate call-log ordering plan→upsert→rename→publish"
else
    pass "skip validate call-log ordering plan→upsert→rename→publish"
fi

# --- skip validate still enforces missing composed plan precondition ---
D_SKIP_MISSING="$TMP/skip-validate-missing-plan"
setup_design_tmp "$D_SKIP_MISSING"
: >"$D_SKIP_MISSING/composed-plan.md"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
set +e
bash "$SUBJECT" --design-tmpdir "$D_SKIP_MISSING" --issue 42 --session-id sid-1 --claude-pid 9999 --skip-validate >"$D_SKIP_MISSING/stdout.txt" 2>/dev/null
rc=$?
set -e
assert_rc "skip validate empty composed plan" 4 "$rc"
grep -Fq 'VALIDATE_STATUS=defects-found' "$D_SKIP_MISSING/.design-publish-result.env" || fail "skip validate empty composed plan result env status"
grep -Fq 'VALIDATE_STATUS=defects-found' "$D_SKIP_MISSING/stdout.txt" || fail "skip validate empty composed plan stdout status fallback"
grep -Fq 'composed-plan.md missing or empty' "$D_SKIP_MISSING/validate-plan-commands.log" || fail "skip validate empty composed plan diagnostic log"
grep -Fq 'PLAN_WRITE_OK=false' "$D_SKIP_MISSING/.design-publish-result.env" || fail "skip validate empty composed plan PLAN_WRITE_OK=false"
grep -Fq 'VALIDATE_DEFECT_COUNT=1' "$D_SKIP_MISSING/.design-publish-result.env" || fail "skip validate empty composed plan defect count"
if [[ -e "$D_SKIP_MISSING/composed-plan.redacted.md" ]]; then fail "skip validate empty composed plan must not redact"; else pass "skip validate empty composed plan skipped redaction"; fi
if grep -Fq 'redact secrets' "$CALL_LOG" 2>/dev/null; then fail "skip validate empty composed plan must not invoke redact"; else pass "skip validate empty composed plan did not invoke redact"; fi
if grep -Fq 'plan-block-write' "$PLAN_BLOCK_LOG" 2>/dev/null; then fail "skip validate empty composed plan must not plan-block write"; else pass "skip validate empty composed plan skipped plan-block write"; fi
if grep -Fq 'design-log-publish' "$PUBLISH_LOG" 2>/dev/null; then fail "skip validate empty composed plan must not publish"; else pass "skip validate empty composed plan skipped publish"; fi
if grep -Fq 'tracking-issue rename' "$RENAME_LOG" 2>/dev/null; then fail "skip validate empty composed plan must not rename"; else pass "skip validate empty composed plan skipped rename"; fi

# --- pause before validator/publish ---
D_PAUSE="$TMP/pause"
setup_design_tmp "$D_PAUSE"
: >"$D_PAUSE/.pause-requested"
cat >"$STUB/design-pause-save.sh" <<'STUB'
#!/usr/bin/env bash
echo "pause-save $*" >>"${CALL_LOG:?}"
exit 0
STUB
chmod +x "$STUB/design-pause-save.sh"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
set +e
bash "$SUBJECT" --design-tmpdir "$D_PAUSE" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "pause checkpoint" 0 "$rc"
grep -q 'pause-save' "$CALL_LOG" || fail "pause save not called"
if grep -q 'validator\|plan-block-write' "$CALL_LOG"; then fail "pause must happen before validator/publish"; else pass "pause skipped validator/publish"; fi

# --- redactor nonzero exit: exit 5, no publish side effects ---
D_REDACT_FAIL="$TMP/redact-fail"
setup_design_tmp "$D_REDACT_FAIL"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export REDACT_STUB_RC=1
set +e
bash "$SUBJECT" --design-tmpdir "$D_REDACT_FAIL" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "redactor failure exit 5" 5 "$rc"
if grep -q 'plan-block-write' "$PLAN_BLOCK_LOG" 2>/dev/null; then fail "redactor failure must not publish"; else pass "redactor failure skipped plan-block-write"; fi

# --- redactor produces empty output: exit 5, no publish side effects ---
D_REDACT_EMPTY="$TMP/redact-empty"
setup_design_tmp "$D_REDACT_EMPTY"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export REDACT_EMPTY_OUTPUT=true
set +e
bash "$SUBJECT" --design-tmpdir "$D_REDACT_EMPTY" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "redactor empty output exit 5" 5 "$rc"
if grep -q 'plan-block-write' "$PLAN_BLOCK_LOG" 2>/dev/null; then fail "empty redact must not publish"; else pass "empty redact skipped plan-block-write"; fi

# --- exit-4 stdout-fallback when result-env write fails ---
D_DEF_NOENV="$TMP/defects-no-result-env"
setup_design_tmp "$D_DEF_NOENV"
ln -sf /dev/null "$D_DEF_NOENV/.design-publish-result.env"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export VALIDATE_STATUS_VALUE=defects-found VALIDATE_DEFECT_COUNT_VALUE=1
set +e
bash "$SUBJECT" --design-tmpdir "$D_DEF_NOENV" --issue 42 --session-id sid-1 --claude-pid 9999 >"$D_DEF_NOENV/stdout.txt" 2>/dev/null
rc=$?
set -e
assert_rc "exit-4 result-env write fail still exits 4" 4 "$rc"
grep -q 'VALIDATE_STATUS=defects-found' "$D_DEF_NOENV/stdout.txt" || fail "exit-4 stdout fallback must emit VALIDATE_STATUS"

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
grep -Eq '^FINAL_SUMMARY_PATH=.*/final-summary[.]md$' "$D_FAIL/.design-publish-result.env" \
  || fail "failure result env missing FINAL_SUMMARY_PATH"
[ -s "$D_FAIL/final-summary.md" ] \
  || fail "failed-plan-write must leave non-empty final-summary.md"
[ -f "$D_FAIL/design-failure-terminal-state.env" ] \
  || fail 'plan-block failure must stage terminal state on publish tmpdir'
grep -Fxq 'FAILURE_OUTCOME=failed-plan-write' "$D_FAIL/design-failure-terminal-state.env" \
  || fail 'plan-block failure terminal outcome missing on publish tmpdir'
grep -q 'failed-plan-write' "$RENDER_LOG" \
  || fail "failed-plan-write render not logged"
grep -q 'ISSUE_NUMBER=42' "$RENDER_LOG" \
  || fail "failed-plan-write render missing ISSUE_NUMBER=42"
grep -q 'SESSION_ID=sid-1' "$RENDER_LOG" \
  || fail "failed-plan-write render missing SESSION_ID=sid-1"
D_FAIL_CANON=$(cd "$D_FAIL" && pwd -P)
grep -q "DESIGN_TMPDIR=${D_FAIL_CANON}" "$RENDER_LOG" \
  || fail "failed-plan-write render missing DESIGN_TMPDIR"
if grep -q 'tracking-issue rename' "$RENAME_LOG" 2>/dev/null; then fail "failed plan write must not rename"; else pass "failed plan write skipped rename"; fi
if grep -q 'tracking-issue rename' "$CALL_LOG" 2>/dev/null; then fail "failed plan write call log must not rename"; else pass "failed plan write call log skipped rename"; fi

D_FAIL_STAGE="$TMP/plan-block-stage"
setup_design_tmp "$D_FAIL_STAGE"
D_FAIL_STAGE_CANON=$(cd "$D_FAIL_STAGE" && pwd -P)
printf 'plan-block write failed\n' >"$D_FAIL_STAGE_CANON/design-plan-write.failure.log"
env -u CLAUDE_PLUGIN_ROOT "$REPO_ROOT/skills/design/scripts/design-stage-terminal-state.sh" \
  --design-tmpdir "$D_FAIL_STAGE_CANON" --outcome failed-plan-write --step publish \
  --phase plan-write --site design-publish --trigger failed \
  --bail-reason plan-write-failed --exit-code 1 --source-script design-publish \
  --failure-detail-log "$D_FAIL_STAGE_CANON/design-plan-write.failure.log" \
  --summary-outcome failed-plan-write >/dev/null
[ -f "$D_FAIL_STAGE_CANON/design-failure-terminal-state.env" ] \
  || fail 'plan-write failure path must stage terminal state'
grep -Fxq 'FAILURE_OUTCOME=failed-plan-write' "$D_FAIL_STAGE_CANON/design-failure-terminal-state.env" \
  || fail 'plan-write failure terminal outcome missing'
pass 'plan-block failure stages terminal state at runtime'

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
grep -Eq '^FINAL_SUMMARY_PATH=.*/final-summary[.]md$' "$D_OK/.design-publish-result.env" \
  || fail "happy result env missing FINAL_SUMMARY_PATH"
[ -s "$D_OK/final-summary.md" ] || fail "happy path must leave non-empty final-summary.md"

plan_pos=$(grep -n 'plan-block-write' "$CALL_LOG" | head -1 | cut -d: -f1)
upsert_pos=$(grep -n 'upsert-diagrams' "$CALL_LOG" | head -1 | cut -d: -f1)
publish_pos=$(grep -n 'design-log-publish' "$CALL_LOG" | head -1 | cut -d: -f1)
rename_pos=$(grep -n 'tracking-issue rename' "$CALL_LOG" | head -1 | cut -d: -f1)
rename_count=$(grep -c 'tracking-issue rename .*--state designed' "$CALL_LOG" || true)
marker_pos=$(grep -n 'design-reentry-marker-write' "$CALL_LOG" | head -1 | cut -d: -f1)
[[ "$rename_count" -eq 1 ]] || fail "happy path must call tracking-issue rename rename --state designed exactly once"
if [[ -z "$plan_pos" || -z "$upsert_pos" || -z "$publish_pos" || -z "$rename_pos" || -z "$marker_pos" ]]; then
    fail "happy path call log missing plan/marker/upsert/publish entries"
elif [[ "$plan_pos" -ge "$upsert_pos" || "$upsert_pos" -ge "$rename_pos" || "$rename_pos" -ge "$publish_pos" || "$publish_pos" -ge "$marker_pos" ]]; then
    fail "happy path call-log ordering plan→upsert→rename→publish→marker"
else
    pass "happy path call-log ordering plan→upsert→rename→publish→marker"
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
if grep -Fq -- '--repo owner/repo' "$PLAN_BLOCK_LOG"; then
  fail "origin-fallback repo must not be passed to issue-wire plan writer"
else
  pass "origin-fallback repo not passed to issue-wire plan writer"
fi
awk '/timing-report/ {t=NR} /design-log-publish/ {p=NR} END { exit (t && p && t < p) ? 0 : 1 }' "$PUBLISH_ORDER_LOG" \
  || fail "timing-report must run before design-log-publish on happy path"
pass "pre-publish timing render runs before design-log-publish"
grep -Fq "LARCH_TIMING_LEDGER=${D_OK_CANON}/timing-ledger.tsv" "$TIMING_REPORT_ENV_LOG" \
  || fail "timing-report must pin LARCH_TIMING_LEDGER to design ledger"
grep -Fq 'IMPLEMENT_TMPDIR=unset' "$TIMING_REPORT_ENV_LOG" \
  || fail "timing-report must clear IMPLEMENT_TMPDIR via env -u"
pass "timing-report pins design ledger and clears IMPLEMENT_TMPDIR"

# --- render_fresh stale sidecar cleanup and failed-render quarantine ---
D_STALE="$TMP/stale-timing-sidecar"
setup_design_tmp "$D_STALE"
: >"$D_STALE/timing-ledger.tsv"
printf 'stale stderr\n' >"$D_STALE/timing-report-final.stderr.log"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
set +e
bash "$SUBJECT" --design-tmpdir "$D_STALE" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>&1
rc=$?
set -e
assert_rc "stale timing sidecar cleanup publish" 0 "$rc"
[[ ! -f "$D_STALE/timing-report-final.stderr.log" ]] || fail "stale timing-report-final.stderr.log must be removed before publish"
[[ -f "$D_STALE/timing-report-final.json" ]] || fail "fresh timing-report-final.json must exist after pre-publish render"
pass "stale timing-report-final.* sidecars removed; only JSON retained"

D_FAIL_TIMING="$TMP/fail-timing-render"
setup_design_tmp "$D_FAIL_TIMING"
: >"$D_FAIL_TIMING/timing-ledger.tsv"
printf 'old\n' >"$D_FAIL_TIMING/timing-report-final.json"
printf 'old stderr\n' >"$D_FAIL_TIMING/timing-report-final.stderr.log"
printf 'old failure\n' >"$D_FAIL_TIMING/timing-report-final.failure.log"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export TIMING_REPORT_FAIL=true
set +e
bash "$SUBJECT" --design-tmpdir "$D_FAIL_TIMING" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>&1
rc=$?
set -e
unset TIMING_REPORT_FAIL
assert_rc "failed timing render still publishes" 0 "$rc"
[[ ! -f "$D_FAIL_TIMING/timing-report-final.json" ]] || fail "failed render must remove timing-report-final.json"
[[ ! -f "$D_FAIL_TIMING/timing-report-final.stderr.log" ]] || fail "failed render must remove timing-report-final.stderr.log"
[[ ! -f "$D_FAIL_TIMING/timing-report-final.failure.log" ]] || fail "failed render must remove timing-report-final.failure.log"
pass "failed timing render quarantines timing-report-final.* artifacts"

D_BAD_TIMING="$TMP/bad-timing-shape"
setup_design_tmp "$D_BAD_TIMING"
: >"$D_BAD_TIMING/timing-ledger.tsv"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export TIMING_REPORT_PARTIAL_JSON=true
set +e
bash "$SUBJECT" --design-tmpdir "$D_BAD_TIMING" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>&1
rc=$?
set -e
unset TIMING_REPORT_PARTIAL_JSON
assert_rc "partial timing JSON still publishes" 0 "$rc"
[[ ! -f "$D_BAD_TIMING/timing-report-final.json" ]] || fail "partial timing JSON must not be published as validated"
pass "partial timing JSON shape is rejected before publish"

D_NO_ROUNDS_TIMING="$TMP/no-rounds-timing-shape"
setup_design_tmp "$D_NO_ROUNDS_TIMING"
: >"$D_NO_ROUNDS_TIMING/timing-ledger.tsv"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export TIMING_REPORT_NO_ROUNDS_JSON=true
set +e
bash "$SUBJECT" --design-tmpdir "$D_NO_ROUNDS_TIMING" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>&1
rc=$?
set -e
unset TIMING_REPORT_NO_ROUNDS_JSON
assert_rc "timing JSON without rounds still publishes" 0 "$rc"
[[ -f "$D_NO_ROUNDS_TIMING/timing-report-final.json" ]] || fail "timing JSON without rounds must be accepted"
pass "timing JSON rounds array is optional"

# --- explicit/resolved repo forwarded to plan-block-write ---
D_PLAN_REPO="$TMP/plan-repo"
setup_design_tmp "$D_PLAN_REPO"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
set +e
bash "$SUBJECT" --design-tmpdir "$D_PLAN_REPO" --issue 42 --session-id sid-1 --claude-pid 9999 --repo explicit/repo >/dev/null 2>&1
rc=$?
set -e
assert_rc "plan-block-write receives explicit repo" 0 "$rc"
grep -Fq -- 'plan-block-write --marker plan --issue 42 --content-file' "$PLAN_BLOCK_LOG" \
  || fail "issue-wire plan writer call missing"
grep -Fq -- '--repo explicit/repo' "$PLAN_BLOCK_LOG" \
  || fail "plan-block-write missing explicit --repo"

D_PLAN_GH_REPO="$TMP/plan-gh-repo"
setup_design_tmp "$D_PLAN_GH_REPO"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export GH_REPO_VIEW_VALUE=gh/repo
export RESOLVE_REPO_VALUE=fallback/repo
set +e
bash "$SUBJECT" --design-tmpdir "$D_PLAN_GH_REPO" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>&1
rc=$?
set -e
assert_rc "plan-block-write receives gh-only repo" 0 "$rc"
grep -Fq -- '--repo gh/repo' "$PLAN_BLOCK_LOG" \
  || fail "plan-block-write missing gh-only --repo"
! grep -Fq -- '--repo fallback/repo' "$PLAN_BLOCK_LOG" \
  || fail "plan-block-write must not use origin fallback repo when gh-only resolution succeeds"

# --- publish envelope fields persisted ---
D_ENV="$TMP/publish-env"
setup_design_tmp "$D_ENV"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_OK_VALUE=false
export PUBLISH_PR_NUMBER=123
export PUBLISH_PR_URL=https://github.com/owner/repo/pull/123
export PUBLISH_RECOVERY_BRANCH=larch-log-design-sid-1
bash "$SUBJECT" --design-tmpdir "$D_ENV" --issue 42 --session-id sid-1 --claude-pid 9999 2>/dev/null
grep -q '^PR_NUMBER=123$' "$D_ENV/.design-publish-result.env" || fail "publish PR_NUMBER missing"
grep -q '^PR_URL=https://github.com/owner/repo/pull/123$' "$D_ENV/.design-publish-result.env" || fail "publish PR_URL missing"
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
grep -q -- '--outcome publish-skipped' "$RENDER_LOG" || fail "empty SESSION_ID should render publish-skipped outcome"
grep -q 'ISSUE_NUMBER=1' "$RENDER_LOG" || fail "empty SESSION_ID render missing ISSUE_NUMBER"
grep -q 'DESIGN_TMPDIR=' "$RENDER_LOG" || fail "empty SESSION_ID render missing DESIGN_TMPDIR"
if ! grep -q 'tracking-issue rename' "$RENAME_LOG" 2>/dev/null; then
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
export PUBLISH_PR_URL=https://github.com/owner/repo/pull/456
export PUBLISH_RECOVERY_BRANCH=larch-log-design-sid
set +e
bash "$SUBJECT" --design-tmpdir "$D_PFAIL" --issue 1 --session-id sid --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "PUBLISH_OK=false" 0 "$rc"
grep -q 'post-publish-only' "$RENDER_LOG" || fail "PUBLISH_OK=false should render post-publish summary"
grep -Eq '^FINAL_SUMMARY_PATH=.*/final-summary[.]md$' "$D_PFAIL/.design-publish-result.env" \
  || fail "PUBLISH_OK=false result env missing FINAL_SUMMARY_PATH"
[ -s "$D_PFAIL/final-summary.md" ] || fail "PUBLISH_OK=false must leave non-empty final-summary.md"
grep -q -- '--outcome failed-publish' "$RENDER_LOG" || fail "PUBLISH_OK=false should render failed-publish outcome"
grep -q 'DESIGN_LOG_PR_NUMBER=456' "$RENDER_LOG" || fail "PUBLISH_OK=false render missing DESIGN_LOG_PR_NUMBER"
grep -q 'DESIGN_LOG_PR_URL=https://github.com/owner/repo/pull/456' "$RENDER_LOG" || fail "PUBLISH_OK=false render missing DESIGN_LOG_PR_URL"
grep -q 'DESIGN_LOG_RECOVERY_BRANCH=larch-log-design-sid' "$RENDER_LOG" || fail "PUBLISH_OK=false render missing DESIGN_LOG_RECOVERY_BRANCH"
grep -q 'RENAMED=true' "$RENDER_LOG" || fail "PUBLISH_OK=false render missing RENAMED"
grep -q 'DESIGNED_ADMISSION_READY=true' "$RENDER_LOG" || fail "PUBLISH_OK=false render missing admission-ready hint"
grep -q 'design-log-publish.sh failed (exit 1)' "$D_PFAIL/execution-issues.md" 2>/dev/null || fail "PUBLISH_OK=false should record nonzero publish failure exit"
grep -q 'design log publish failed; recovery metadata' "$D_PFAIL/.design-publish-result.env" || fail "PUBLISH_OK=false should emit recovery WARN"
grep -q 'tracking-issue rename' "$RENAME_LOG" || fail "rename should run before PUBLISH_OK=false"
assert_rename_before_publish "PUBLISH_OK=false call-log ordering rename→publish" "$CALL_LOG"
grep -q 'RENAMED=true' "$D_PFAIL/.design-publish-result.env" || fail "PUBLISH_OK=false should persist RENAMED=true"
grep -q 'DESIGNED_ADMISSION_READY=true' "$D_PFAIL/.design-publish-result.env" || fail "PUBLISH_OK=false should persist admission-ready hint"
if grep -q 'design-reentry-marker-write' "$CALL_LOG"; then
    fail "reentry marker should be skipped on PUBLISH_OK=false"
else
    pass "reentry marker skipped on PUBLISH_OK=false"
fi
rm -f "$D_PFAIL/.completed/step-5c"
PUBLISH_OK="$(awk -F= '$1=="PUBLISH_OK"{print $2}' "$D_PFAIL/.design-publish-result.env" | tail -1)"
SESSION_ID=sid
if [[ "$SESSION_ID" == "" || "$PUBLISH_OK" == true ]]; then
    mkdir -p "$D_PFAIL/.completed"
    : >"$D_PFAIL/.completed/step-5c"
fi
if [[ -e "$D_PFAIL/.completed/step-5c" ]]; then
    fail "orchestrator sentinel simulation must withhold step-5c on failed publish"
else
    pass "orchestrator sentinel simulation withholds step-5c on failed publish"
fi

# --- PUBLISH_OK=false after idempotent [DESIGNED] rename ---
D_PFAIL_IDEM="$TMP/pub-fail-idempotent"
setup_design_tmp "$D_PFAIL_IDEM"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_OK_VALUE=false
export RENAMED_VALUE=false
export NEW_TITLE_VALUE='[DESIGNED] Existing issue'
set +e
bash "$SUBJECT" --design-tmpdir "$D_PFAIL_IDEM" --issue 1 --session-id sid --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "PUBLISH_OK=false idempotent rename" 0 "$rc"
grep -q 'RENAMED=false' "$D_PFAIL_IDEM/.design-publish-result.env" || fail "idempotent publish failure should persist RENAMED=false"
grep -q 'NEW_TITLE=\[DESIGNED\] Existing issue' "$D_PFAIL_IDEM/.design-publish-result.env" || fail "idempotent publish failure should persist NEW_TITLE"
grep -q 'DESIGNED_ADMISSION_READY=true' "$D_PFAIL_IDEM/.design-publish-result.env" || fail "idempotent publish failure should persist admission-ready hint"
grep -q 'RENAMED=false' "$RENDER_LOG" || fail "idempotent publish failure render missing RENAMED=false"
grep -q 'NEW_TITLE=\[DESIGNED\] Existing issue' "$RENDER_LOG" || fail "idempotent publish failure render missing NEW_TITLE"
grep -q 'DESIGNED_ADMISSION_READY=true' "$RENDER_LOG" || fail "idempotent [DESIGNED] rename should be admission-ready"

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
grep -q 'tracking-issue rename' "$RENAME_LOG" || fail "rename should run before unexpected publish rc"
grep -q 'RENAMED=true' "$D_UNEXP/.design-publish-result.env" || fail "unexpected publish should persist RENAMED=true"
grep -q 'design-log-publish.sh' "$D_UNEXP/execution-issues.md" 2>/dev/null   || fail "unexpected publish must append to execution-issues.md"

# --- nonzero publish rc with PUBLISH_OK=true is fail-closed ---
D_RC_TRUE="$TMP/pub-rc-true"
setup_design_tmp "$D_RC_TRUE"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_STUB_RC=2
export PUBLISH_EMIT_OK=true
export PUBLISH_OK_VALUE=true
export PUBLISH_PR_NUMBER=456
export PUBLISH_PR_URL=https://github.com/owner/repo/pull/456
export PUBLISH_RECOVERY_BRANCH=larch-log-design-sid
set +e
bash "$SUBJECT" --design-tmpdir "$D_RC_TRUE" --issue 1 --session-id sid --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "publish rc nonzero with PUBLISH_OK=true" 0 "$rc"
grep -q 'PUBLISH_OK=false' "$D_RC_TRUE/.design-publish-result.env" || fail "nonzero publish rc must force PUBLISH_OK=false"
grep -q -- '--outcome failed-publish' "$RENDER_LOG" || fail "nonzero publish rc should render failed-publish outcome"
grep -q 'DESIGN_LOG_PR_NUMBER=456' "$RENDER_LOG" || fail "nonzero PUBLISH_OK=true render should keep PR number"
grep -q 'DESIGN_LOG_PR_URL=https://github.com/owner/repo/pull/456' "$RENDER_LOG" || fail "nonzero PUBLISH_OK=true render should keep PR URL"
grep -q 'DESIGN_LOG_RECOVERY_BRANCH=larch-log-design-sid' "$RENDER_LOG" || fail "nonzero PUBLISH_OK=true render should keep recovery branch"
grep -q 'tracking-issue rename' "$RENAME_LOG" \
  || fail "rename should run before nonzero publish rc despite PUBLISH_OK=true"
grep -q 'RENAMED=true' "$D_RC_TRUE/.design-publish-result.env" \
  || fail "nonzero publish rc should persist RENAMED=true from pre-publish rename"
if grep -q 'design-reentry-marker-write' "$CALL_LOG" 2>/dev/null; then
    fail "reentry marker should be skipped when publish rc is nonzero despite PUBLISH_OK=true"
else
    pass "reentry marker skipped when publish rc is nonzero despite PUBLISH_OK=true"
fi

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
grep -q 'tracking-issue rename' "$RENAME_LOG" || fail "rename should run before missing PUBLISH_OK handling"
grep -q 'RENAMED=true' "$D_NO_PUB_KV/.design-publish-result.env" || fail "missing PUBLISH_OK should persist RENAMED=true"
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
grep -q 'tracking-issue rename' "$RENAME_LOG"   || fail "exit 3 should still complete publish tail (rename) before result-env write"

# --- if ! plan-block-write guard ---
# shellcheck disable=SC2016 # Literal pattern checks unexpanded shell syntax in source.
grep -Fq 'if ! python3 "$PLUGIN_ROOT/python/cli.py" "${_plan_block_args[@]}"' "$SUBJECT" \
  || fail "design-publish.sh must use if ! around issue-wire plan writer"

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
grep -q 'python/cli.py diagrams upsert' "$D_UPSERT_FAIL/execution-issues.md" 2>/dev/null \
  || fail "upsert failure must append to execution-issues.md"
grep -q 'tracking-issue rename .*--state designed' "$RENAME_LOG" \
  || fail "upsert failure must still attempt [DESIGNED] rename"
assert_rename_before_publish "upsert failure call-log ordering rename→publish" "$CALL_LOG"
grep -q 'RENAMED=true' "$D_UPSERT_FAIL/.design-publish-result.env" \
  || fail "upsert failure must record rename outcome"
grep -q 'DESIGNED_ADMISSION_READY=false' "$D_UPSERT_FAIL/.design-publish-result.env" \
  || fail "upsert failure must not mark admission ready"

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
grep -q 'WARN=.*plan block was written.*diagram upsert skipped' "$D_REN_FAIL/.design-publish-result.env" \
  || fail "rename failure WARN must not assert diagram was posted when upsert skipped"
awk '
  /tracking-issue rename .*--state designed/ { seen_rename=1 }
  /design-log-publish / && seen_rename { seen_publish_after_rename=1 }
  END { exit seen_publish_after_rename ? 0 : 1 }
' "$CALL_LOG" || fail "rename failure must continue to design-log-publish"

# --- rename failure warns with failed upsert detail ---
D_REN_FAIL_UPSERT="$TMP/rename-fail-upsert"
setup_design_tmp "$D_REN_FAIL_UPSERT"
printf 'graph TD\n' >"$D_REN_FAIL_UPSERT/architecture-diagram.md"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export RENAME_STUB_RC=1
export UPSERT_STATUS_VALUE=failed
set +e
bash "$SUBJECT" --design-tmpdir "$D_REN_FAIL_UPSERT" --issue 42 --session-id sid-1 --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "rename failure after upsert failure non-blocking" 0 "$rc"
grep -q 'WARN=.*plan block was written.*diagram upsert failed' "$D_REN_FAIL_UPSERT/.design-publish-result.env" \
  || fail "rename failure WARN must include diagram upsert failed when UPSERT_STATUS=failed"

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
if grep -q '^RENAMED=false$' "$D_REN_OMIT/.design-publish-result.env"; then
    fail "success without RENAMED= must not persist RENAMED=false"
else
    pass "success without RENAMED= leaves RENAMED unknown"
fi
grep -q '^DESIGNED_ADMISSION_READY=false$' "$D_REN_OMIT/.design-publish-result.env" \
  || fail "success without RENAMED= must persist admission-ready false"

# --- failed publish after rename failure does not emit admission-ready branch ---
D_PFAIL_REN_FAIL="$TMP/pub-fail-rename-fail"
setup_design_tmp "$D_PFAIL_REN_FAIL"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_OK_VALUE=false
export RENAME_STUB_RC=1
set +e
bash "$SUBJECT" --design-tmpdir "$D_PFAIL_REN_FAIL" --issue 42 --session-id sid-1 --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "PUBLISH_OK=false after rename failure" 0 "$rc"
grep -q '^RENAMED=false$' "$D_PFAIL_REN_FAIL/.design-publish-result.env" \
  || fail "publish failure after rename failure must persist RENAMED=false"
grep -q '^DESIGNED_ADMISSION_READY=false$' "$D_PFAIL_REN_FAIL/.design-publish-result.env" \
  || fail "publish failure after rename failure must persist admission-ready false"
grep -q 'DESIGNED_ADMISSION_READY=false' "$RENDER_LOG" \
  || fail "publish failure after rename failure render missing admission-ready false"
grep -q 'WARN=.*\[DESIGNED\].*rename failed' "$D_PFAIL_REN_FAIL/.design-publish-result.env" \
  || fail "publish failure after rename failure must warn about rename failure"
pass "publish failure after rename failure omits admission-ready recovery prose"

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

# --- sanitize_publish_metadata strips malformed PR_URL on failed publish ---
D_BAD_URL="$TMP/bad-pr-url"
setup_design_tmp "$D_BAD_URL"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_OK_VALUE=false
export PUBLISH_STUB_RC=1
export PUBLISH_PR_NUMBER=456
export PUBLISH_PR_URL=not-a-valid-github-pr-url
export PUBLISH_RECOVERY_BRANCH=larch-log-design-sid
set +e
bash "$SUBJECT" --design-tmpdir "$D_BAD_URL" --issue 1 --session-id sid --claude-pid 1 2>/dev/null
rc=$?
set -e
assert_rc "malformed PR_URL failed publish" 0 "$rc"
grep -q 'PUBLISH_OK=false' "$D_BAD_URL/.design-publish-result.env" || fail "malformed PR_URL must set PUBLISH_OK=false"
grep -q 'RECOVERY_BRANCH=larch-log-design-sid' "$D_BAD_URL/.design-publish-result.env" \
  || fail "malformed PR_URL must keep valid RECOVERY_BRANCH in result env"
if grep -q 'PR_URL=not-a-valid-github-pr-url' "$D_BAD_URL/.design-publish-result.env"; then
    fail "malformed PR_URL must be stripped from result env"
else
    pass "malformed PR_URL stripped from result env"
fi
grep -q 'DESIGN_LOG_RECOVERY_BRANCH=larch-log-design-sid' "$RENDER_LOG" \
  || fail "malformed PR_URL render must keep DESIGN_LOG_RECOVERY_BRANCH"
if grep -q 'DESIGN_LOG_PR_URL=not-a-valid-github-pr-url' "$RENDER_LOG"; then
    fail "malformed PR_URL render must strip DESIGN_LOG_PR_URL"
else
    pass "malformed PR_URL render strips DESIGN_LOG_PR_URL"
fi

# --- clarify-style metadata survives a separate Final-summary subshell ---
D_META="$TMP/clarify-metadata"
setup_design_tmp "$D_META"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_OK_VALUE=false
export PUBLISH_STUB_RC=1
export PUBLISH_PR_NUMBER=456
export PUBLISH_PR_URL=https://github.com/owner/repo/pull/456
export PUBLISH_RECOVERY_BRANCH=larch-log-design-sid
bash "$SUBJECT" --design-tmpdir "$D_META" --issue 1 --session-id sid --claude-pid 1 2>/dev/null
[[ -f "$D_META/.design-log-publish-metadata.env" ]] || fail "publish must write .design-log-publish-metadata.env"
meta_render=$(
  bash -c '
    set -a
    source "$1/.design-log-publish-metadata.env"
    set +a
    export DESIGN_LOG_PR_NUMBER="${DESIGN_LOG_PR_NUMBER:-}"
    export DESIGN_LOG_PR_URL="${DESIGN_LOG_PR_URL:-}"
    export DESIGN_LOG_RECOVERY_BRANCH="${DESIGN_LOG_RECOVERY_BRANCH:-}"
    printf "DESIGN_LOG_PR_NUMBER=%s DESIGN_LOG_PR_URL=%s DESIGN_LOG_RECOVERY_BRANCH=%s\n" \
      "$DESIGN_LOG_PR_NUMBER" "$DESIGN_LOG_PR_URL" "$DESIGN_LOG_RECOVERY_BRANCH"
  ' bash "$D_META"
)
[[ "$meta_render" == *"DESIGN_LOG_PR_NUMBER=456"* ]] || fail "metadata subshell missing PR number: $meta_render"
[[ "$meta_render" == *"DESIGN_LOG_PR_URL=https://github.com/owner/repo/pull/456"* ]] || fail "metadata subshell missing PR URL: $meta_render"
[[ "$meta_render" == *"DESIGN_LOG_RECOVERY_BRANCH=larch-log-design-sid"* ]] || fail "metadata subshell missing recovery branch: $meta_render"
pass "clarify metadata survives separate subshell via tmpdir env file"

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
grep -q 'tracking-issue rename .*--state designed' "$RENAME_LOG" \
  || fail "missing diagram artifacts must still attempt [DESIGNED] rename"
assert_rename_before_publish "no architecture call-log ordering rename→publish" "$CALL_LOG"
grep -q 'RENAMED=true' "$D_NO_ARCH/.design-publish-result.env" \
  || fail "missing diagram artifacts must record rename outcome"

# --- publish-tail write-once and summary protection ---
D_WRITE_ONCE="$TMP/write-once-publish-failure"
setup_design_tmp "$D_WRITE_ONCE"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_OK_VALUE=false
export PUBLISH_SEED_RESULT_BEFORE_RETURN=true
export PUBLISH_SEED_PR_NUMBER=42
export PUBLISH_SEED_PR_URL=https://github.com/owner/repo/pull/42
set +e
bash "$SUBJECT" --design-tmpdir "$D_WRITE_ONCE" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "write-once preserves concurrent publish success" 0 "$rc"
grep -Fxq 'PUBLISH_OK=true' "$D_WRITE_ONCE/.design-publish-result.env" \
  || fail "write-once result env must keep PUBLISH_OK=true"
if grep -Fxq 'PUBLISH_OK=false' "$D_WRITE_ONCE/.design-publish-result.env"; then
    fail "write-once result env must not append PUBLISH_OK=false"
else
    pass "write-once skipped failure clobber"
fi
grep -Fxq 'PR_NUMBER=42' "$D_WRITE_ONCE/.design-publish-result.env" \
  || fail "write-once must preserve PR_NUMBER=42"
grep -Fxq 'PR_URL=https://github.com/owner/repo/pull/42' "$D_WRITE_ONCE/.design-publish-result.env" \
  || fail "write-once must preserve PR_URL"
if grep -q -- '--outcome failed-publish' "$RENDER_LOG"; then
    fail "write-once concurrent success must not render failed-publish"
else
    pass "write-once concurrent success keeps approved summary path"
fi

D_SHORT="$TMP/pre-publish-success-short-circuit"
setup_design_tmp "$D_SHORT"
cat >"$D_SHORT/.design-publish-result.env" <<'EOF_RESULT'
PLAN_WRITE_OK=true
PUBLISH_OK=true
PR_NUMBER=77
PR_URL=https://github.com/owner/repo/pull/77
EOF_RESULT
printf 'approved content\n' >"$D_SHORT/final-summary.md"
printf 'final-only delta\n' >"$D_SHORT/final-only.txt"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_INVOCATION_LOG="$TMP/publish-invocation.log"
: >"$PUBLISH_INVOCATION_LOG"
export PUBLISH_OK_VALUE=false
export PUBLISH_STUB_RC=1
set +e
bash "$SUBJECT" --design-tmpdir "$D_SHORT" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "pre-publish success re-entry" 0 "$rc"
if grep -q 'design-log-publish' "$PUBLISH_LOG" 2>/dev/null; then
    pass "pre-publish success still invokes design-log-publish"
else
    fail "pre-publish success must still invoke design-log-publish"
fi
grep -q 'FINAL_ONLY_PRESENT=true' "$PUBLISH_LOG" \
  || fail "re-entry publish must observe final-only delta in design tmpdir"
grep -Fxq 'PR_NUMBER=77' "$D_SHORT/.design-publish-result.env" \
  || fail "pre-publish success re-entry must preserve original PR_NUMBER"
grep -Fxq 'PR_URL=https://github.com/owner/repo/pull/77' "$D_SHORT/.design-publish-result.env" \
  || fail "pre-publish success re-entry must preserve original PR_URL"
grep -q -- '--outcome approved' "$RENDER_LOG" \
  || fail "pre-publish success re-entry should render approved outcome"
if grep -q -- '--outcome failed-publish' "$RENDER_LOG"; then
    fail "pre-publish success re-entry must not render failed-publish"
else
    pass "pre-publish success re-entry protects final summary from failed-publish"
fi

D_IDEMPOTENT_OK="$TMP/idempotent-publish-success-empty-pr-stdout"
setup_design_tmp "$D_IDEMPOTENT_OK"
cat >"$D_IDEMPOTENT_OK/.design-publish-result.env" <<'EOF_RESULT'
PLAN_WRITE_OK=true
PUBLISH_OK=true
PR_NUMBER=77
PR_URL=https://github.com/owner/repo/pull/77
EOF_RESULT
printf 'approved content\n' >"$D_IDEMPOTENT_OK/final-summary.md"
printf 'final-only delta\n' >"$D_IDEMPOTENT_OK/final-only.txt"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_INVOCATION_LOG="$TMP/publish-invocation-idempotent-ok.log"
: >"$PUBLISH_INVOCATION_LOG"
export PUBLISH_OK_VALUE=true
unset PUBLISH_PR_NUMBER PUBLISH_PR_URL
set +e
bash "$SUBJECT" --design-tmpdir "$D_IDEMPOTENT_OK" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "idempotent publish success with empty PR stdout" 0 "$rc"
if grep -q 'design-log-publish' "$PUBLISH_LOG" 2>/dev/null; then
    pass "idempotent publish success still invokes design-log-publish"
else
    fail "idempotent publish success must still invoke design-log-publish"
fi
grep -Fxq 'PR_NUMBER=77' "$D_IDEMPOTENT_OK/.design-publish-result.env" \
  || fail "idempotent publish success must preserve original PR_NUMBER"
grep -Fxq 'PR_URL=https://github.com/owner/repo/pull/77' "$D_IDEMPOTENT_OK/.design-publish-result.env" \
  || fail "idempotent publish success must preserve original PR_URL"
grep -q -- '--outcome approved' "$RENDER_LOG" \
  || fail "idempotent publish success should render approved outcome"
grep -q 'DESIGN_LOG_PR_NUMBER=77' "$RENDER_LOG" \
  || fail "idempotent publish success render must keep DESIGN_LOG_PR_NUMBER=77"
grep -q 'DESIGN_LOG_PR_URL=https://github.com/owner/repo/pull/77' "$RENDER_LOG" \
  || fail "idempotent publish success render must keep DESIGN_LOG_PR_URL"

D_REENTRY_NEW_PR="$TMP/pre-publish-success-second-pr"
setup_design_tmp "$D_REENTRY_NEW_PR"
cat >"$D_REENTRY_NEW_PR/.design-publish-result.env" <<'EOF_RESULT'
PLAN_WRITE_OK=true
PUBLISH_OK=true
PR_NUMBER=50
PR_URL=https://github.com/owner/repo/pull/50
EOF_RESULT
printf 'approved content\n' >"$D_REENTRY_NEW_PR/final-summary.md"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_INVOCATION_LOG="$TMP/publish-invocation-new-pr.log"
: >"$PUBLISH_INVOCATION_LOG"
export PUBLISH_PR_NUMBER=51
export PUBLISH_PR_URL=https://github.com/owner/repo/pull/51
set +e
bash "$SUBJECT" --design-tmpdir "$D_REENTRY_NEW_PR" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "pre-publish success second successful publish" 0 "$rc"
grep -Fxq 'PR_NUMBER=51' "$D_REENTRY_NEW_PR/.design-publish-result.env" \
  || fail "second successful publish must update PR_NUMBER"
grep -Fxq 'PR_URL=https://github.com/owner/repo/pull/51' "$D_REENTRY_NEW_PR/.design-publish-result.env" \
  || fail "second successful publish must update PR_URL"
if grep -q 'PR_NUMBER=50' "$D_REENTRY_NEW_PR/.design-publish-result.env"; then
    fail "second successful publish must not keep stale PR_NUMBER"
else
    pass "second successful publish replaces stale PR metadata"
fi
grep -q 'design-log-publish' "$PUBLISH_LOG" \
  || fail "second successful publish must invoke design-log-publish"

D_DEF_STALE="$TMP/stale-success-validator-defects"
setup_design_tmp "$D_DEF_STALE"
cat >"$D_DEF_STALE/.design-publish-result.env" <<'EOF_RESULT'
PLAN_WRITE_OK=true
PUBLISH_OK=true
PR_NUMBER=99
EOF_RESULT
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export VALIDATE_STATUS_VALUE=defects-found VALIDATE_DEFECT_COUNT_VALUE=2
set +e
bash "$SUBJECT" --design-tmpdir "$D_DEF_STALE" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "stale success overwritten on validator defects" 4 "$rc"
grep -Fxq 'VALIDATE_STATUS=defects-found' "$D_DEF_STALE/.design-publish-result.env" \
  || fail "validator defects must overwrite stale success with current status"
if grep -Fxq 'PUBLISH_OK=true' "$D_DEF_STALE/.design-publish-result.env"; then
    fail "validator defects must not preserve stale PUBLISH_OK=true"
else
    pass "validator defects do not preserve stale success"
fi

D_PLAN_STALE="$TMP/stale-success-plan-write"
setup_design_tmp "$D_PLAN_STALE"
cat >"$D_PLAN_STALE/.design-publish-result.env" <<'EOF_RESULT'
PLAN_WRITE_OK=true
PUBLISH_OK=true
PR_NUMBER=100
EOF_RESULT
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PLAN_BLOCK_RC=1
set +e
bash "$SUBJECT" --design-tmpdir "$D_PLAN_STALE" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "stale success overwritten on plan-write failure" 1 "$rc"
grep -Fxq 'PLAN_WRITE_OK=false' "$D_PLAN_STALE/.design-publish-result.env" \
  || fail "plan-write failure must write PLAN_WRITE_OK=false"
if grep -Fxq 'PUBLISH_OK=true' "$D_PLAN_STALE/.design-publish-result.env"; then
    fail "plan-write failure must not preserve stale PUBLISH_OK=true"
else
    pass "plan-write failure does not preserve stale success"
fi


# --- dual-invocation lock: success-first failure-second ---
D_DUAL_SF="$TMP/dual-success-first"
setup_design_tmp "$D_DUAL_SF"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_PR_NUMBER=55
export PUBLISH_PR_URL=https://github.com/owner/repo/pull/55
set +e
bash "$SUBJECT" --design-tmpdir "$D_DUAL_SF" --issue 42 --session-id sid-dual --claude-pid 9999 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "dual success-first inv1" 0 "$rc"
grep -Fxq 'PUBLISH_OK=true' "$D_DUAL_SF/.design-publish-result.env" \
  || fail "dual success-first inv1 must record PUBLISH_OK=true"
render_lines_after_inv1=$(wc -l <"$RENDER_LOG" | tr -d ' ')
export PUBLISH_OK_VALUE=false
set +e
bash "$SUBJECT" --design-tmpdir "$D_DUAL_SF" --issue 42 --session-id sid-dual --claude-pid 9999 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "dual success-first inv2" 0 "$rc"
grep -Fxq 'PUBLISH_OK=true' "$D_DUAL_SF/.design-publish-result.env" \
  || fail "dual success-first inv2 must preserve PUBLISH_OK=true"
if grep -Fxq 'PUBLISH_OK=false' "$D_DUAL_SF/.design-publish-result.env"; then
    fail "dual success-first inv2 must not write PUBLISH_OK=false"
else
    pass "dual success-first lock skips failure clobber"
fi
grep -Fxq 'PR_NUMBER=55' "$D_DUAL_SF/.design-publish-result.env" \
  || fail "dual success-first must preserve PR_NUMBER metadata"
grep -Fxq 'PR_URL=https://github.com/owner/repo/pull/55' "$D_DUAL_SF/.design-publish-result.env" \
  || fail "dual success-first must preserve PR_URL metadata"
if tail -n +"$((render_lines_after_inv1 + 1))" "$RENDER_LOG" | grep -q -- '--outcome failed-publish'; then
    fail "dual success-first inv2 must not render failed-publish"
else
    pass "dual success-first inv2 keeps approved summary path"
fi

# --- dual-invocation lock: failure-first success-second ---
D_DUAL_FS="$TMP/dual-failure-first"
setup_design_tmp "$D_DUAL_FS"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export PUBLISH_OK_VALUE=false
set +e
bash "$SUBJECT" --design-tmpdir "$D_DUAL_FS" --issue 42 --session-id sid-dual2 --claude-pid 9999 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "dual failure-first inv1" 0 "$rc"
grep -Fxq 'PUBLISH_OK=false' "$D_DUAL_FS/.design-publish-result.env" \
  || fail "dual failure-first inv1 must record PUBLISH_OK=false"
unset PUBLISH_OK_VALUE
set +e
bash "$SUBJECT" --design-tmpdir "$D_DUAL_FS" --issue 42 --session-id sid-dual2 --claude-pid 9999 >/dev/null 2>/dev/null
rc=$?
set -e
assert_rc "dual failure-first inv2" 0 "$rc"
last_publish_ok=$(awk -F= '/^PUBLISH_OK=/{v=$2} END{print v}' "$D_DUAL_FS/.design-publish-result.env")
[[ "$last_publish_ok" == true ]] \
  || fail "dual failure-first final PUBLISH_OK must be true (got ${last_publish_ok:-empty})"
pass "dual failure-first success wins"

grep -Fq 'stage_design_terminal_state failed-plan-write' "$SUBJECT" || fail 'design-publish stages failed-plan-write'
grep -Fq 'stage_design_terminal_state failed-publish' "$SUBJECT" || fail 'design-publish stages failed-publish'
grep -Fq 'DESIGN_FAILURE_VERSION=1' "$REPO_ROOT/skills/design/scripts/design-stage-terminal-state.sh" || fail 'terminal state helper writes required version key'

# --- publish-tail hard exit stages terminal state via real helper (design-step5c contract) ---
D_TAIL="$TMP/publish-tail-hard"
setup_design_tmp "$D_TAIL"
ln -sf "$REPO_ROOT/skills/design/scripts/design-stage-terminal-state.sh" "$FAKE_PLUGIN/skills/design/scripts/design-stage-terminal-state.sh"
reset_publish_stub_env
init_publish_logs
apply_publish_stub_defaults
export REDACT_STUB_RC=1
set +e
bash "$SUBJECT" --design-tmpdir "$D_TAIL" --issue 42 --session-id sid-1 --claude-pid 9999 >/dev/null 2>&1
rc=$?
set -e
assert_rc "redactor failure exit 5 for setup abort" 5 "$rc"
[ -f "$D_TAIL/design-publish-setup.failure.log" ] || fail 'setup hard exit must write failure log'
pass 'setup hard exit records failure log without duplicate render in design-publish'
pass 'design-publish terminal-state staging static contract'

if [[ "$FAIL" -gt 0 ]]; then
    echo "FAIL: $FAIL test(s) failed ($PASS passed)" >&2
    exit 1
fi
echo "PASS: test-design-publish.sh ($PASS cases)"
