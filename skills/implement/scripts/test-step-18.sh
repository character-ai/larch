#!/usr/bin/env bash
# Offline regression harness for step-18.sh.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
HELPER="$SCRIPT_DIR/step-18.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-step18-test.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
assert_contains() { case "$2" in *"$1"*) : ;; *) fail "$3 missing $1" ;; esac; }
assert_not_contains() { case "$2" in *"$1"*) fail "$3 unexpectedly contained $1" ;; *) : ;; esac; }
assert_eq() { [ "$1" = "$2" ] || fail "$3 expected <$1> got <$2>"; }
kv() { awk -v k="$1" 'BEGIN{p=k"="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$2"; }
count_literal() { awk -v s="$1" 'index($0,s){n++} END{print n+0}' "$2"; }
line_no() { awk -v s="$1" 'index($0,s){print NR; exit}' "$2"; }

PLUGIN="$TMP_ROOT/plugin"
mkdir -p "$PLUGIN/python"
cat >"$PLUGIN/python/cli.py" <<'PY'
#!/usr/bin/env python3
import os
import sys
from pathlib import Path


def log(message: str) -> None:
    path = os.environ.get("STEP18_STUB_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(message + "\n")


def read_key(args: list[str]) -> int:
    file_path = Path(args[args.index("--file") + 1])
    key = args[args.index("--key") + 1]
    default = args[args.index("--default") + 1] if "--default" in args else ""
    fail_key = os.environ.get("STEP18_STUB_READ_KEY_FAIL_KEY") or ""
    if fail_key and key == fail_key:
        return 6
    try:
        for line in file_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                print(line.split("=", 1)[1])
                return 0
    except OSError:
        pass
    print(default)
    return 0


def step18b(args: list[str]) -> int:
    tmp = Path(args[args.index("--implement-tmpdir") + 1])
    sentinel = "true" if (tmp / ".step17-emitted").exists() else "false"
    log(f"step18b sentinel={sentinel} argv={' '.join(sys.argv[1:])}")
    if (os.environ.get("STEP18_STUB_WRITE_SUMMARY") or "true") == "true":
        (tmp / "summary-final.md").write_text((os.environ.get("STEP18_STUB_BODY") or "# Final body\n"), encoding="utf-8")
    if (os.environ.get("STEP18_STUB_REMOVE_SUMMARY") or "false") == "true":
        with open(tmp / "summary-final.md", "w", encoding="utf-8") as handle:
            handle.write((os.environ.get("STEP18_STUB_BODY") or "# Final body\n"))
        os.unlink(tmp / "summary-final.md")
    emit = (os.environ.get("STEP18_STUB_EMIT_BODY") or "true")
    rc = int((os.environ.get("STEP18_STUB_WFR_RC") or "0"))
    print(f"EMIT_BODY={emit}")
    print(f"WFR_RC={rc}")
    print(f"STEP17_EMITTED_PRESENT={sentinel}")
    print("SNAPSHOT_OK=true")
    return rc


def teardown(args: list[str]) -> int:
    tmp = Path(args[args.index("--implement-tmpdir") + 1])
    state = args[args.index("--state-file") + 1]
    expected = str(tmp / "finalize-state.sh")
    if Path(state) != (tmp / "finalize-state.sh"):
        print(f"bad state file {state} expected {expected}", file=sys.stderr)
        return 9
    marker = "before" if (tmp / ".step17-emitted").exists() else "missing"
    log(f"teardown sentinel={marker} argv={' '.join(sys.argv[1:])}")
    print("ISSUE_URL=https://example.test/issues/1")
    print("RENAME_BRANCH=skipped")
    print("RENAME_STATUS=ok")
    print("STASH_REF=refs/stash/test")
    print("SENTINEL_WRITTEN=true")
    print("FINALIZE_SUBCOMMAND=teardown")
    print("FINALIZE_WARNINGS=none")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if args[:2] == ["session", "read-key"]:
        return read_key(args[2:])
    if args[:2] == ["final-report", "step18b"]:
        return step18b(args[2:])
    if args[:2] == ["run-log", "append-failure"]:
        log("append-failure " + " ".join(args[2:]))
        return 0
    if args[:2] == ["token", "report"]:
        log("token report")
        return 0
    if args[:2] == ["timing", "report"]:
        log("timing report")
        return 0
    if args[:2] == ["token", "mark"]:
        log("token mark " + " ".join(args[2:]))
        return 0
    if args[:2] == ["timing", "mark"]:
        log("timing mark " + " ".join(args[2:]))
        return 0
    if args[:2] == ["execution-issues", "flush-safety-net"]:
        log("flush-safety-net " + " ".join(args[2:]))
        return 0
    if args[:2] == ["run-log", "capture-transcript"]:
        log("capture-transcript " + " ".join(args[2:]))
        print("SESSION_TRANSCRIPT_STATUS=captured")
        return 0
    if args[:2] == ["session", "restore-finalize-state"]:
        log("restore-finalize-state " + " ".join(args[2:]))
        return 0
    if args[:2] == ["session", "clear-implement-pointer"]:
        log("clear-implement-pointer " + " ".join(args[2:]))
        return 0
    if args[:2] == ["implement-finalize", "teardown"]:
        return teardown(args[2:])
    print("unexpected argv: " + " ".join(args), file=sys.stderr)
    return 8


if __name__ == "__main__":
    raise SystemExit(main())
PY
chmod +x "$PLUGIN/python/cli.py"
FAKEBIN="$TMP_ROOT/fakebin"
mkdir -p "$FAKEBIN"
cat >"$FAKEBIN/cat" <<'STUB'
#!/usr/bin/env bash
if [ "${STEP18_STUB_CAT_FAIL:-false}" = true ]; then
  case "${1:-}" in
    *summary-final.md) exit 1 ;;
  esac
fi
exec /bin/cat "$@"
STUB
chmod +x "$FAKEBIN/cat"

make_impl() {
    local name=$1
    local dir="$TMP_ROOT/$name"
    mkdir -p "$dir"
    printf 'LARCH_RUN_ID=RUN1\nLARCH_TOKEN_SESSION_ID=tok\nLARCH_CLAUDE_SOURCE_FILE=source.jsonl\nLARCH_TIMING_LEDGER=%s/timing-ledger.tsv\nSTALL_TRACKING=false\n' "$dir" >"$dir/session-env.sh"
    printf 'STALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=\n' >"$dir/ship-pr-state.sh"
    printf 'STALL_TRACKING=false\nSTALL_STEP=\n' >"$dir/finalize-state.sh"
    printf '%s\n' "$dir"
}

run_step18() {
    local impl=$1 out=$2 log=$3
    shift 3
    set +e
    IMPLEMENT_TMPDIR="$impl"       CLAUDE_PLUGIN_ROOT="$PLUGIN"       STEP18_STUB_LOG="$log"       STEP18_STUB_BODY="${STEP18_STUB_BODY:-}"       STEP18_STUB_EMIT_BODY="${STEP18_STUB_EMIT_BODY:-}"       STEP18_STUB_WFR_RC="${STEP18_STUB_WFR_RC:-}"       STEP18_STUB_WRITE_SUMMARY="${STEP18_STUB_WRITE_SUMMARY:-}"       STEP18_STUB_REMOVE_SUMMARY="${STEP18_STUB_REMOVE_SUMMARY:-}"       STEP18_STUB_CAT_FAIL="${STEP18_STUB_CAT_FAIL:-}"       STEP18_STUB_READ_KEY_FAIL_KEY="${STEP18_STUB_READ_KEY_FAIL_KEY:-}"       PATH="$FAKEBIN:$PATH"       "$HELPER" "$@" >"$out" 2>"$out.err"
    rc=$?
    set -e
    return "$rc"
}

# Gate / no-stall.
impl=$(make_impl gate-clear)
out="$TMP_ROOT/gate-clear.out"; log="$TMP_ROOT/gate-clear.log"
run_step18 "$impl" "$out" "$log" --phase gate --stall-tracking-memory false || fail 'gate clear exited non-zero'
text=$(cat "$out")
assert_contains 'STALL_TRACKING_MEMORY=false' "$text" 'gate clear memory KV'
assert_contains 'STALL_TRACKING_DISK=false' "$text" 'gate clear disk KV'
assert_contains 'STALL_TRACKING_FINALIZE=false' "$text" 'gate clear finalize KV'
assert_contains 'STALL_TRACKING_SESSION=false' "$text" 'gate clear session KV'
assert_contains 'STALL_RECOVERY_REQUIRED=false' "$text" 'gate clear recovery KV'
assert_contains '⏩ 18a: stall recovery — no stall detected' "$text" 'gate clear breadcrumb'
[ ! -f "$log" ] || fail 'gate clear should not invoke finalize stubs'

# Gate / stall early-exit and non-canonical active values.
impl=$(make_impl gate-stall)
printf 'STALL_TRACKING=maybe\n' >"$impl/ship-pr-state.sh"
out="$TMP_ROOT/gate-stall.out"; log="$TMP_ROOT/gate-stall.log"
run_step18 "$impl" "$out" "$log" --phase gate --stall-tracking-memory false || fail 'gate stall exited non-zero'
text=$(cat "$out")
assert_contains 'STALL_TRACKING_DISK=maybe' "$text" 'gate stall disk KV'
assert_contains 'STALL_RECOVERY_REQUIRED=true' "$text" 'gate stall recovery KV'
[ ! -f "$log" ] || fail 'gate stall should not invoke finalize stubs'

# Gate predicate table.
for value in '' false; do
    impl=$(make_impl "pred-inactive-${value:-empty}")
    out="$TMP_ROOT/pred-inactive-${value:-empty}.out"; log="$TMP_ROOT/pred-inactive-${value:-empty}.log"
    run_step18 "$impl" "$out" "$log" --phase gate --stall-tracking-memory "$value" || fail "predicate inactive $value exited non-zero"
    assert_eq false "$(kv STALL_RECOVERY_REQUIRED "$out")" "predicate inactive $value"
done
for value in true 1 yes arbitrary; do
    impl=$(make_impl "pred-active-$value")
    out="$TMP_ROOT/pred-active-$value.out"; log="$TMP_ROOT/pred-active-$value.log"
    run_step18 "$impl" "$out" "$log" --phase gate --stall-tracking-memory "$value" || fail "predicate active $value exited non-zero"
    assert_eq true "$(kv STALL_RECOVERY_REQUIRED "$out")" "predicate active $value"
done

# Finalize / no-stall path and marker body.
impl=$(make_impl finalize-body)
out="$TMP_ROOT/finalize-body.out"; log="$TMP_ROOT/finalize-body.log"
STEP18_STUB_BODY=$'# Final body\nDetails\n' run_step18 "$impl" "$out" "$log" --phase finalize --step17-emitted false || fail 'finalize body exited non-zero'
text=$(cat "$out")
assert_not_contains 'STALL_RECOVERY_REQUIRED' "$text" 'finalize body stdout'
assert_eq 1 "$(count_literal '---LARCH-SUMMARY-FINAL-BEGIN---' "$out")" 'finalize body begin marker count'
assert_eq 1 "$(count_literal '---LARCH-SUMMARY-FINAL-END---' "$out")" 'finalize body end marker count'
assert_contains '# Final body' "$text" 'finalize body marker content'
assert_eq 1 "$(count_literal '# Final body' "$out")" 'finalize body raw duplicate check'
assert_contains 'ISSUE_URL=https://example.test/issues/1' "$text" 'teardown issue tail relay'
assert_contains 'RENAME_BRANCH=skipped' "$text" 'teardown rename tail relay'
assert_contains 'RENAME_STATUS=ok' "$text" 'teardown rename status relay'
assert_contains 'STASH_REF=refs/stash/test' "$text" 'teardown stash relay'
assert_contains 'SENTINEL_WRITTEN=true' "$text" 'teardown sentinel relay'
assert_contains 'FINALIZE_SUBCOMMAND=teardown' "$text" 'teardown subcommand relay'
assert_contains 'FINALIZE_WARNINGS=none' "$text" 'teardown warnings relay'
log_text=$(cat "$log")
assert_contains 'step18b sentinel=false argv=final-report step18b --implement-tmpdir' "$log_text" 'finalize step18b invocation'
assert_contains 'flush-safety-net --log-root' "$log_text" 'finalize flush safety net'
assert_contains '--run-id RUN1' "$log_text" 'finalize safety net run id'
assert_contains 'capture-transcript --source-file source.jsonl --log-root' "$log_text" 'finalize transcript capture'
assert_contains '--skill implement --run-id RUN1 --defer-commit true' "$log_text" 'finalize transcript capture argv'
assert_contains 'teardown sentinel=before argv=implement-finalize teardown --state-file' "$log_text" 'finalize teardown invocation'
assert_contains 'SESSION_TRANSCRIPT_STATUS=captured' "$text" 'finalize transcript status relay'

# Step 7a completion suppresses Step 18 transcript recapture.
impl=$(make_impl step7a-complete)
mkdir -p "$impl/.completed"
: >"$impl/.completed/step-7a-terminal"
out="$TMP_ROOT/step7a-complete.out"; log="$TMP_ROOT/step7a-complete.log"
STEP18_STUB_EMIT_BODY=false run_step18 "$impl" "$out" "$log" --phase finalize --step17-emitted false || fail 'step7a-complete exited non-zero'
log_text=$(cat "$log")
assert_contains 'flush-safety-net' "$log_text" 'step7a-complete still flushes execution issues'
assert_not_contains 'capture-transcript' "$log_text" 'step7a-complete skips transcript recapture'

# --step17-emitted true creates sentinel before step18b and can suppress body.
impl=$(make_impl step17-present)
out="$TMP_ROOT/step17-present.out"; log="$TMP_ROOT/step17-present.log"
STEP18_STUB_EMIT_BODY=false run_step18 "$impl" "$out" "$log" --phase finalize --step17-emitted true || fail 'step17-present exited non-zero'
assert_eq false "$(kv EMIT_BODY "$out")" 'step17-present EMIT_BODY'
assert_contains 'step18b sentinel=true' "$(cat "$log")" 'step17-present pre-step18b sentinel'
assert_eq 0 "$(count_literal '---LARCH-SUMMARY-FINAL-BEGIN---' "$out")" 'step17-present marker suppressed'

# Step18b failure tolerance.
impl=$(make_impl step18b-failure)
out="$TMP_ROOT/step18b-failure.out"; log="$TMP_ROOT/step18b-failure.log"
STEP18_STUB_WFR_RC=7 STEP18_STUB_EMIT_BODY=true run_step18 "$impl" "$out" "$log" --phase finalize --step17-emitted false || fail 'step18b failure must still exit 0 after teardown'
assert_eq 7 "$(kv WFR_RC "$out")" 'step18b failure WFR_RC relay'
assert_eq 0 "$(count_literal '---LARCH-SUMMARY-FINAL-BEGIN---' "$out")" 'step18b failure markers suppressed'
log_text=$(cat "$log")
assert_contains 'append-failure' "$log_text" 'step18b failure append log'
assert_contains 'token mark Step 18 — done' "$log_text" 'step18b failure closing mark'
assert_contains 'teardown sentinel=' "$log_text" 'step18b failure teardown'

# Marker cat failure tolerance.
impl=$(make_impl marker-failure)
out="$TMP_ROOT/marker-failure.out"; log="$TMP_ROOT/marker-failure.log"
STEP18_STUB_CAT_FAIL=true STEP18_STUB_EMIT_BODY=true run_step18 "$impl" "$out" "$log" --phase finalize --step17-emitted false || fail 'marker failure must still exit 0 after teardown'
assert_eq 1 "$(count_literal '---LARCH-SUMMARY-FINAL-BEGIN---' "$out")" 'marker failure begin marker appears before cat failure'
assert_eq 0 "$(count_literal '---LARCH-SUMMARY-FINAL-END---' "$out")" 'marker failure lacks balanced end marker'
log_text=$(cat "$log")
assert_contains 'token mark Step 18 — done' "$log_text" 'marker failure closing mark'
assert_contains 'teardown sentinel=' "$log_text" 'marker failure teardown'
assert_contains '**⚠ Step 18: EMIT_BODY=true but marker pair missing from finalize stdout.**' "$(cat "$REPO_ROOT/skills/implement/SKILL.md")" 'missing marker warning documented'
# shellcheck disable=SC2016
assert_contains 'Do not Read `summary-final.md` on the Step 18 path because teardown may have removed the tmpdir.' "$(cat "$REPO_ROOT/skills/implement/SKILL.md")" 'no post-teardown Read documented'

# Restore-finalize-state gate cases.
impl=$(make_impl restore-missing)
rm -f "$impl/finalize-state.sh"
out="$TMP_ROOT/restore-missing.out"; log="$TMP_ROOT/restore-missing.log"
STEP18_STUB_EMIT_BODY=false run_step18 "$impl" "$out" "$log" --phase finalize --step17-emitted false || fail 'restore missing exited non-zero'
assert_contains 'restore-finalize-state --implement-tmpdir' "$(cat "$log")" 'restore missing finalize state'

impl=$(make_impl restore-stall)
printf 'STALL_TRACKING=yes\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=\n' >"$impl/ship-pr-state.sh"
out="$TMP_ROOT/restore-stall.out"; log="$TMP_ROOT/restore-stall.log"
STEP18_STUB_EMIT_BODY=false run_step18 "$impl" "$out" "$log" --phase finalize --step17-emitted false || fail 'restore stall exited non-zero'
assert_contains 'restore-finalize-state --implement-tmpdir' "$(cat "$log")" 'restore ship stall truthy'

impl=$(make_impl restore-bail)
printf 'STALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=ON\nSTALL_STEP=\n' >"$impl/ship-pr-state.sh"
out="$TMP_ROOT/restore-bail.out"; log="$TMP_ROOT/restore-bail.log"
STEP18_STUB_EMIT_BODY=false run_step18 "$impl" "$out" "$log" --phase finalize --step17-emitted false || fail 'restore bail exited non-zero'
assert_contains 'restore-finalize-state --implement-tmpdir' "$(cat "$log")" 'restore ship bail truthy'

impl=$(make_impl restore-mismatch)
printf 'STALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=ship\n' >"$impl/ship-pr-state.sh"
printf 'STALL_TRACKING=false\nSTALL_STEP=final\n' >"$impl/finalize-state.sh"
out="$TMP_ROOT/restore-mismatch.out"; log="$TMP_ROOT/restore-mismatch.log"
STEP18_STUB_EMIT_BODY=false run_step18 "$impl" "$out" "$log" --phase finalize --step17-emitted false || fail 'restore mismatch exited non-zero'
assert_contains 'restore-finalize-state --implement-tmpdir' "$(cat "$log")" 'restore stall step mismatch'

impl=$(make_impl restore-aligned)
printf 'STALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=same\n' >"$impl/ship-pr-state.sh"
printf 'STALL_TRACKING=false\nSTALL_STEP=same\n' >"$impl/finalize-state.sh"
out="$TMP_ROOT/restore-aligned.out"; log="$TMP_ROOT/restore-aligned.log"
STEP18_STUB_EMIT_BODY=false run_step18 "$impl" "$out" "$log" --phase finalize --step17-emitted false || fail 'restore aligned exited non-zero'
assert_not_contains 'restore-finalize-state' "$(cat "$log")" 'restore aligned should skip'

impl=$(make_impl restore-read-key-failure)
printf 'STALL_TRACKING=yes\nBAIL_NEEDS_USER_INPUT=true\nSTALL_STEP=ship\n' >"$impl/ship-pr-state.sh"
printf 'STALL_TRACKING=false\nSTALL_STEP=ship\n' >"$impl/finalize-state.sh"
out="$TMP_ROOT/restore-read-key-failure.out"; log="$TMP_ROOT/restore-read-key-failure.log"
STEP18_STUB_EMIT_BODY=false STEP18_STUB_READ_KEY_FAIL_KEY=STALL_TRACKING run_step18 "$impl" "$out" "$log" --phase finalize --step17-emitted false || fail 'restore read-key failure exited non-zero'
assert_contains 'teardown sentinel=' "$(cat "$log")" 'restore read-key failure still tears down'
assert_contains 'restore-finalize-state --implement-tmpdir' "$(cat "$log")" 'restore read-key failure uses default and continues'

# Ordering: closing marks, safety nets, restore, and teardown.
mark_line=$(line_no 'token mark Step 18 — done' "$TMP_ROOT/restore-mismatch.log")
flush_line=$(line_no 'flush-safety-net' "$TMP_ROOT/restore-mismatch.log")
capture_line=$(line_no 'capture-transcript' "$TMP_ROOT/restore-mismatch.log")
restore_line=$(line_no 'restore-finalize-state' "$TMP_ROOT/restore-mismatch.log")
teardown_line=$(line_no 'teardown sentinel=' "$TMP_ROOT/restore-mismatch.log")
[ -n "$mark_line" ] && [ -n "$flush_line" ] && [ -n "$capture_line" ] && [ -n "$restore_line" ] && [ -n "$teardown_line" ] || fail 'ordering log missing expected rows'
[ "$mark_line" -lt "$flush_line" ] || fail 'closing mark must precede execution-issues safety net'
[ "$flush_line" -lt "$capture_line" ] || fail 'execution-issues safety net must precede transcript safety net'
[ "$capture_line" -lt "$restore_line" ] || fail 'transcript safety net must precede restore-finalize-state'
[ "$restore_line" -lt "$teardown_line" ] || fail 'restore-finalize-state must precede teardown'

# Missing run id skips both safety nets and still tears down.
impl=$(make_impl no-run-id)
awk '$0 !~ /^LARCH_RUN_ID=/' "$impl/session-env.sh" >"$impl/session-env.tmp"
mv "$impl/session-env.tmp" "$impl/session-env.sh"
out="$TMP_ROOT/no-run-id.out"; log="$TMP_ROOT/no-run-id.log"
STEP18_STUB_EMIT_BODY=false RUN_ID='' run_step18 "$impl" "$out" "$log" --phase finalize --step17-emitted false || fail 'no run id finalize exited non-zero'
log_text=$(cat "$log")
assert_not_contains 'flush-safety-net' "$log_text" 'no run id flush safety net skip'
assert_not_contains 'capture-transcript' "$log_text" 'no run id transcript safety net skip'
assert_contains 'teardown sentinel=' "$log_text" 'no run id teardown'

# Post-terminal continuation: finalize can run directly with disk STALL_TRACKING=true.
impl=$(make_impl post-terminal)
printf 'STALL_TRACKING=true\nBAIL_NEEDS_USER_INPUT=false\nSTALL_STEP=terminal\n' >"$impl/ship-pr-state.sh"
printf 'terminal report\n' >"$impl/stall-recovery-terminal-report.env"
out="$TMP_ROOT/post-terminal.out"; log="$TMP_ROOT/post-terminal.log"
STEP18_STUB_EMIT_BODY=false run_step18 "$impl" "$out" "$log" --phase finalize --step17-emitted false || fail 'post-terminal finalize exited non-zero'
assert_not_contains 'STALL_RECOVERY_REQUIRED' "$(cat "$out")" 'post-terminal finalize must not re-run gate'
assert_contains 'FINALIZE_SUBCOMMAND=teardown' "$(cat "$out")" 'post-terminal teardown tail relay'

printf 'PASS: test-step-18.sh\n'
