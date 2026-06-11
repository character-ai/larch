#!/usr/bin/env bash
# test-implement-bootstrap.sh — offline harness for scripts/implement-bootstrap.sh

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
REAL_SCRIPT="$REPO_ROOT/scripts/implement-bootstrap.sh"

[ -x "$REAL_SCRIPT" ] || { echo "FAIL: $REAL_SCRIPT not executable"; exit 1; }

PASS=0
FAIL=0

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

assert_occurrences() {
    local needle=$1 haystack=$2 expected=$3 label=$4
    local actual
    actual=$(printf '%s\n' "$haystack" | grep -cF -- "$needle" || true)
    if [ "$actual" -eq "$expected" ]; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (expected $expected got $actual)"
        echo "  counted: $needle"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    fi
}

assert_line() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s\n' "$haystack" | grep -qxF -- "$needle"; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        echo "  expected exact line: $needle"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    fi
}

assert_order() {
    local first=$1 second=$2 haystack=$3 label=$4
    local first_line second_line
    first_line=$(printf '%s\n' "$haystack" | grep -nF -- "$first" | head -n 1 | cut -d: -f1 || true)
    second_line=$(printf '%s\n' "$haystack" | grep -nF -- "$second" | head -n 1 | cut -d: -f1 || true)
    if [ -n "$first_line" ] && [ -n "$second_line" ] && [ "$first_line" -lt "$second_line" ]; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        echo "  expected order: $first before $second"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    fi
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

build_sandbox() {
    SANDBOX=$(mktemp -d /tmp/larch-ib-test.XXXXXX)
    mkdir -p "$SANDBOX/bin" "$SANDBOX/scripts" "$SANDBOX/skills/implement/scripts" "$SANDBOX/python/stubs/session" "$SANDBOX_TMP"
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$SANDBOX/scripts/"
    cp "$REPO_ROOT/scripts/lib-execution-issues.sh" "$SANDBOX/scripts/"
    cp "$REAL_SCRIPT" "$SANDBOX/scripts/implement-bootstrap.sh"
    cp "$REPO_ROOT"/python/*.py "$SANDBOX/python/"
    mv "$SANDBOX/python/cli.py" "$SANDBOX/python/real-cli.py"
    cat >"$SANDBOX/python/cli.py" <<'DISPATCHER'
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def _ledger_stub(root: Path) -> int:
    log = root.parent / "invoke-log.txt"
    if len(sys.argv) >= 2 and sys.argv[1] in {"token", "timing"}:
        prefix = "token-ledger" if sys.argv[1] == "token" else "timing-ledger"
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(f"{prefix} {' '.join(sys.argv[2:])}\n")
        return 0
    if len(sys.argv) >= 3 and sys.argv[1] == "token" and sys.argv[2] == "claude-source":
        return 0
    return 1

def _append_failure_stub() -> int:
    rc = int(os.environ.get("SANDBOX_APPEND_TOOL_FAILURE_EXIT", "0"))
    if rc:
        print("append-tool-failure failure", file=sys.stderr)
        return rc
    log = site = output_file = ""
    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--log" and i + 1 < len(args):
            log = args[i + 1]; i += 2
        elif args[i] == "--site" and i + 1 < len(args):
            site = args[i + 1]; i += 2
        elif args[i] == "--output-file" and i + 1 < len(args):
            output_file = args[i + 1]; i += 2
        else:
            i += 1
    if log:
        path = Path(log)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{site}\n")
            out = Path(output_file) if output_file else None
            if out is not None and out.is_file():
                handle.write(out.read_text(encoding="utf-8"))
    return 0

def _run_log_stub(root: Path) -> int:
    log = root.parent / "invoke-log.txt"
    with log.open("a", encoding="utf-8") as handle:
        handle.write("larch-log " + " ".join(sys.argv[2:]) + "\n")
    if os.environ.get("LARCH_TEST_LARCH_LOG_FAIL", "") == "true":
        print("LOG_WRITTEN=false")
        print("LOG_PATH=")
        print("BYTES=0")
        print("SHA256=")
        print("COMMIT_SHA=")
        print("UNCHANGED=false")
        print("ERROR=init failed")
        return 1
    args = sys.argv[3:]
    vals = {"--log-root": "", "--skill": "", "--run-id": ""}
    i = 0
    while i < len(args):
        if args[i] in vals and i + 1 < len(args):
            vals[args[i]] = args[i + 1]; i += 2
        else:
            i += 1
    path = Path(vals["--log-root"]) / vals["--skill"] / vals["--run-id"] / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n", encoding="utf-8")
    print("LOG_WRITTEN=true")
    print(f"LOG_PATH={path}")
    print("BYTES=3")
    print("SHA256=dummy")
    print("COMMIT_SHA=")
    print("UNCHANGED=false")
    return 0

def _issue_context_stub(root: Path) -> int:
    raw_args = " ".join(sys.argv[3:])
    tmpdir = ""
    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--tmpdir" and i + 1 < len(args):
            tmpdir = args[i + 1]
            i += 2
        elif args[i] in {"--issue", "--repo"}:
            i += 2
        else:
            i += 1
    with (root.parent / "invoke-log.txt").open("a", encoding="utf-8") as handle:
        handle.write(f"cli.py issue context {raw_args}\n")
    rc = int(os.environ.get("GET_ISSUE_CONTEXT_EXIT", "0"))
    if rc:
        print("simulated upstream context failure", file=sys.stderr)
        return rc
    path = Path(tmpdir)
    path.mkdir(parents=True, exist_ok=True)
    title = path / "upstream-issue-title.txt"
    body = path / "upstream-issue-body.txt"
    title.write_text("title\n", encoding="utf-8")
    body.write_text("body\n", encoding="utf-8")
    print(f"TITLE_FILE={title}")
    print(f"BODY_FILE={body}")
    return 0

def _issue_state_stub(root: Path) -> int:
    with (root.parent / "invoke-log.txt").open("a", encoding="utf-8") as handle:
        handle.write("cli.py issue state " + " ".join(sys.argv[3:]) + "\n")
    if os.environ.get("LARCH_TEST_GET_ISSUE_FAILED", "false") == "true":
        print("FAILED=true")
        print("ERROR=failed=value")
        return 1
    print(f"STATE={os.environ.get('LARCH_TEST_ISSUE_STATE', 'OPEN')}")
    print(f"URL=https://example.test/{os.environ.get('LARCH_TEST_URL_KIND', 'issues')}/123")
    print(f"IS_PR={os.environ.get('LARCH_TEST_IS_PR', 'false')}")
    return 0

def main() -> None:
    root = Path(__file__).resolve().parent
    if len(sys.argv) >= 3 and sys.argv[1:3] == ["issue", "context"]:
        raise SystemExit(_issue_context_stub(root))
    if len(sys.argv) >= 3 and sys.argv[1:3] == ["issue", "state"]:
        raise SystemExit(_issue_state_stub(root))
    if len(sys.argv) >= 3:
        stub = root / "stubs" / sys.argv[1] / sys.argv[2]
        if stub.is_file() and os.access(stub, os.X_OK):
            os.execv(str(stub), [str(stub), *sys.argv[3:]])
    if len(sys.argv) >= 2 and sys.argv[1] in {"token", "timing"}:
        raise SystemExit(_ledger_stub(root))
    if len(sys.argv) >= 3 and sys.argv[1] == "run-log":
        if sys.argv[2] == "append-failure":
            raise SystemExit(_append_failure_stub())
        if sys.argv[2] != "append-entry":
            raise SystemExit(_run_log_stub(root))
    if len(sys.argv) >= 3 and sys.argv[1:3] == ["voting", "write-tally"]:
        invoke_log = root.parent / "invoke-log.txt"
        with invoke_log.open("a", encoding="utf-8") as handle:
            handle.write("voting write-tally " + " ".join(sys.argv[3:]) + "\n")
        rc = int(os.environ.get("SANDBOX_WRITE_TALLY_EXIT", "0"))
        if rc:
            print("write tally failure", file=sys.stderr)
            raise SystemExit(rc)
        raise SystemExit(0)
    os.execv(sys.executable, [sys.executable, str(root / "real-cli.py"), *sys.argv[1:]])

if __name__ == "__main__":
    main()
DISPATCHER
    chmod +x "$SANDBOX/python/cli.py" "$SANDBOX/scripts/implement-bootstrap.sh"

    cat >"$SANDBOX/bin/gh" <<'STUB'
#!/usr/bin/env bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf 'gh %s\n' "$*" >>"$script_dir/../invoke-log.txt"
if [ "${SANDBOX_GH_EXIT:-0}" -ne 0 ]; then
  printf 'gh failure\n' >&2
  exit "$SANDBOX_GH_EXIT"
fi
printf '%s\n\n%s\n' "${SANDBOX_GH_TITLE:-Test Feature}" "${SANDBOX_GH_BODY:-Body}"
exit 0
STUB
    chmod +x "$SANDBOX/bin/gh"

    cat >"$SANDBOX/scripts/create-branch.sh" <<'STUB'
#!/usr/bin/env bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in
  --check)
    echo CURRENT_BRANCH=main
    echo IS_MAIN=true
    echo "IS_USER_BRANCH=${SANDBOX_IS_USER_BRANCH:-false}"
    echo USER_PREFIX=testuser
    exit 0
    ;;
  --branch)
    printf 'create-branch --branch %s\n' "$2" >>"$script_dir/../invoke-log.txt"
    if [ "${SANDBOX_CREATE_BRANCH_EXIT:-0}" -ne 0 ]; then
      printf 'create branch failure\n' >&2
      exit "$SANDBOX_CREATE_BRANCH_EXIT"
    fi
    printf '%s\n' "$2" >"$script_dir/../last-created-branch.txt"
    echo "BRANCH_NAME=$2"
    echo ACTION=created
    exit 0
    ;;
esac
exit 2
STUB
    chmod +x "$SANDBOX/scripts/create-branch.sh"

    cat >"$SANDBOX/python/stubs/session/entry-gate" <<'STUB'
#!/usr/bin/env bash
echo ENTRY_GATE=strict
echo SKIP_BRANCH_CHECK=false
exit 0
STUB
    chmod +x "$SANDBOX/python/stubs/session/entry-gate"

    cat >"$SANDBOX/python/stubs/session/write-id" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$@" >>"$SANDBOX/invoke-log.txt"
while [ \$# -gt 0 ]; do
  case "\$1" in
    --output) mkdir -p "\$(dirname "\$2")"; printf 'sessstub\\n' > "\$2"; shift 2 ;;
    *) shift ;;
  esac
done
exit 0
STUB
    chmod +x "$SANDBOX/python/stubs/session/write-id"

    cat >"$SANDBOX/scripts/tracking-issue-read.sh" <<'STUB'
#!/usr/bin/env bash
sentinel=""
while [ $# -gt 0 ]; do
  case "$1" in
    --sentinel) sentinel=$2; shift 2 ;;
    *) shift ;;
  esac
done
if [ -z "$sentinel" ] || [ ! -f "$sentinel" ]; then
  echo FAILED=true
  echo ERROR=sentinel-not-found
  exit 1
fi
issue=$(awk -F= '$1=="ISSUE_NUMBER"{print substr($0,index($0,"=")+1); exit}' "$sentinel")
run_id=$(awk -F= '$1=="RUN_ID"{print substr($0,index($0,"=")+1); exit}' "$sentinel")
adopted=$(awk -F= '$1=="ADOPTED"{print substr($0,index($0,"=")+1); exit}' "$sentinel")
case "$adopted" in
  ""|true|false) ;;
  *) echo FAILED=true; echo "ERROR=invalid ADOPTED value"; exit 1 ;;
esac
echo "ISSUE_NUMBER=$issue"
echo "RUN_ID=$run_id"
echo "ADOPTED=$adopted"
exit 0
STUB
    chmod +x "$SANDBOX/scripts/tracking-issue-read.sh"

    cat >"$SANDBOX/skills/implement/scripts/post-tracking-issue.sh" <<'STUB'
#!/usr/bin/env bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
printf 'post-tracking-issue %s\n' "$*" >>"$script_dir/invoke-log.txt"
tmpdir=""
issue=""
run_id=""
adopted="true"
emergency="false"
while [ $# -gt 0 ]; do
  case "$1" in
    --implement-tmpdir) tmpdir=$2; shift 2 ;;
    --issue-number) issue=$2; shift 2 ;;
    --run-id) run_id=$2; shift 2 ;;
    --adopted) adopted=$2; shift 2 ;;
    --emergency-requested) emergency=$2; shift 2 ;;
    *) shift ;;
  esac
done
printf 'post-tracking-issue --emergency-requested %s\n' "$emergency" >>"$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/invoke-log.txt"
if [ "${LARCH_TEST_POSTED:-true}" != "true" ]; then
  echo POSTED=false
  echo COMMENT_URL=
  echo "ERROR=post failed"
  exit 1
fi
printf 'ISSUE_NUMBER=%s\nRUN_ID=%s\nADOPTED=%s\n' "$issue" "$run_id" "$adopted" > "$tmpdir/parent-issue.md"
echo POSTED=true
echo COMMENT_URL=https://example.test/comment
exit 0
STUB
    chmod +x "$SANDBOX/skills/implement/scripts/post-tracking-issue.sh"

    cat >"$SANDBOX/scripts/tracking-issue-write.sh" <<'STUB'
#!/usr/bin/env bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf 'tracking-issue-write %s\n' "$*" >>"$script_dir/../invoke-log.txt"
if [ "${LARCH_TEST_RENAME_FAILED:-false}" = "true" ]; then
  echo FAILED=true
  echo "ERROR=rename failed"
  exit 1
fi
echo RENAMED=true
echo "NEW_TITLE=[IMPLEMENTING] test"
exit 0
STUB
    chmod +x "$SANDBOX/scripts/tracking-issue-write.sh"

    cat >"$SANDBOX/scripts/snapshot-untracked.sh" <<'STUB'
#!/usr/bin/env bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf 'snapshot-untracked %s\n' "$*" >>"$script_dir/../invoke-log.txt"
output=""
while [ $# -gt 0 ]; do
  case "$1" in
    --output) output=$2; shift 2 ;;
    *) shift ;;
  esac
done
[ -n "$output" ] && : > "$output"
exit 0
STUB
    chmod +x "$SANDBOX/scripts/snapshot-untracked.sh"

    cat >"$SANDBOX/python/stubs/session/persist-run-flags" <<'STUB'
#!/usr/bin/env bash
sandbox_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
printf 'persist-implement-run-flags %s\n' "$*" >>"$sandbox_root/invoke-log.txt"
if [ "${SANDBOX_PERSIST_FLAGS_EXIT:-0}" -ne 0 ]; then
  printf 'persist failure\n' >&2
  exit "$SANDBOX_PERSIST_FLAGS_EXIT"
fi
tmpdir=""
emergency="false"
while [ $# -gt 0 ]; do
  case "$1" in
    --implement-tmpdir) tmpdir=$2; shift 2 ;;
    --emergency-requested) emergency=$2; shift 2 ;;
    *) shift ;;
  esac
done
[ -n "$tmpdir" ] && printf 'NO_ISSUES=false\nEMERGENCY_REQUESTED=%s\n' "$emergency" >"$tmpdir/run-flags.sh"
exit 0
STUB
    chmod +x "$SANDBOX/python/stubs/session/persist-run-flags"

    cat >"$SANDBOX/python/stubs/session/read-key" <<'STUB'
#!/usr/bin/env bash
file=""; key=""; default=""
while [ $# -gt 0 ]; do
  case "$1" in
    --file)    file=$2;    shift 2 ;;
    --key)     key=$2;     shift 2 ;;
    --default) default=$2; shift 2 ;;
    *) shift ;;
  esac
done
if [ -n "$file" ] && [ -f "$file" ] && [ -n "$key" ]; then
  val=$(awk -F= -v k="$key" '$1==k{print substr($0,index($0,"=")+1); exit}' "$file")
  [ -n "$val" ] && printf '%s\n' "$val" && exit 0
fi
printf '%s\n' "$default"
STUB
    chmod +x "$SANDBOX/python/stubs/session/read-key"

    cat >"$SANDBOX/python/stubs/session/write-env" <<'STUB'
#!/usr/bin/env bash
output=""; plugin_root_only=false; plugin_root_value=""
repo=""; repo_unavailable="false"; forked_target="false"
codex_present=""; cursor_present=""; codex_binary_found=""; cursor_binary_found=""
auto_mode=""; timing_ledger=""; token_session_id=""; claude_source_file=""
prev_implement_tmpdir=""; dynamic_archetypes=""; run_id=""
while [ $# -gt 0 ]; do
  case "$1" in
    --output)               output=$2;               shift 2 ;;
    --plugin-root-only)     plugin_root_only=true;   shift ;;
    --value)                plugin_root_value=$2;    shift 2 ;;
    --repo)                 repo=$2;                 shift 2 ;;
    --repo-unavailable)     repo_unavailable=$2;     shift 2 ;;
    --codex-present)        codex_present=$2;        shift 2 ;;
    --cursor-present)       cursor_present=$2;       shift 2 ;;
    --codex-binary-found)   codex_binary_found=$2;   shift 2 ;;
    --cursor-binary-found)  cursor_binary_found=$2;  shift 2 ;;
    --auto-mode)            auto_mode=$2;            shift 2 ;;
    --timing-ledger)        timing_ledger=$2;        shift 2 ;;
    --token-session-id)     token_session_id=$2;     shift 2 ;;
    --claude-source-file)   claude_source_file=$2;   shift 2 ;;
    --prev-implement-tmpdir) prev_implement_tmpdir=$2; shift 2 ;;
    --forked-target)        forked_target=$2;        shift 2 ;;
    --dynamic-archetypes)   dynamic_archetypes=$2;   shift 2 ;;
    --run-id)               run_id=$2;               shift 2 ;;
    *)                      shift ;;
  esac
done
[ -z "$output" ] && exit 0
mkdir -p "$(dirname "$output")"
if [ "$plugin_root_only" = "true" ]; then
  printf 'CLAUDE_PLUGIN_ROOT=%s\n' "$plugin_root_value" >"$output"
  exit 0
fi
printf 'REPO=%s\n'            "$repo"            >"$output"
printf 'REPO_UNAVAILABLE=%s\n' "$repo_unavailable" >>"$output"
printf 'FORKED_TARGET=%s\n'   "$forked_target"   >>"$output"
[ -n "$codex_present" ]      && { printf 'CODEX_PRESENT=%s\n'       "$codex_present"      >>"$output"; printf 'CODEX_AVAILABLE=%s\n'  "$codex_present"  >>"$output"; }
[ -n "$codex_binary_found" ] && printf 'CODEX_BINARY_FOUND=%s\n'    "$codex_binary_found" >>"$output"
[ -n "$cursor_present" ]     && { printf 'CURSOR_PRESENT=%s\n'      "$cursor_present"     >>"$output"; printf 'CURSOR_AVAILABLE=%s\n' "$cursor_present" >>"$output"; }
[ -n "$cursor_binary_found" ] && printf 'CURSOR_BINARY_FOUND=%s\n'  "$cursor_binary_found" >>"$output"
[ -n "$auto_mode" ]          && printf 'LARCH_AUTO_MODE=%s\n'        "$auto_mode"          >>"$output"
[ -n "$timing_ledger" ]      && printf 'LARCH_TIMING_LEDGER=%s\n'    "$timing_ledger"      >>"$output"
[ -n "$token_session_id" ]   && printf 'LARCH_TOKEN_SESSION_ID=%s\n' "$token_session_id"   >>"$output"
[ -n "$claude_source_file" ] && printf 'LARCH_CLAUDE_SOURCE_FILE=%s\n' "$claude_source_file" >>"$output"
[ -n "$prev_implement_tmpdir" ] && printf 'PREV_IMPLEMENT_TMPDIR=%s\n' "$prev_implement_tmpdir" >>"$output"
[ -n "$dynamic_archetypes" ] && printf 'LARCH_DYNAMIC_ARCHETYPES_MAX=%s\n' "$dynamic_archetypes" >>"$output"
[ -n "$run_id" ]             && printf 'LARCH_RUN_ID=%s\n'           "$run_id"             >>"$output"
plugin_root="${CLAUDE_PLUGIN_ROOT:-}"
if [ -n "$plugin_root" ]; then
  printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$plugin_root" >>"$output"
  printf 'CLAUDE_PLUGIN_ROOT=%s\n' "$plugin_root" >"$(dirname "$output")/plugin-root.env"
fi
STUB
    chmod +x "$SANDBOX/python/stubs/session/write-env"

    cat >"$SANDBOX/scripts/check-mid-run-dirty-tree.sh" <<'STUB'
#!/usr/bin/env bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf 'check-mid-run-dirty-tree %s\n' "$*" >>"$script_dir/../invoke-log.txt"
if [ "${SANDBOX_DIRTY_EXIT:-0}" -ne 0 ]; then
  printf 'dirty tree probe failure\n' >&2
  exit "$SANDBOX_DIRTY_EXIT"
fi
echo "STATUS=${SANDBOX_DIRTY_STATUS:-clean}"
exit 0
STUB
    chmod +x "$SANDBOX/scripts/check-mid-run-dirty-tree.sh"

    cat >"$SANDBOX/scripts/git-current-branch.sh" <<'STUB'
#!/usr/bin/env bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf 'git-current-branch\n' >>"$script_dir/../invoke-log.txt"
if [ "${SANDBOX_BRANCH_CAPTURE_EXIT:-0}" -ne 0 ]; then
  printf 'branch capture failure\n' >&2
  exit "$SANDBOX_BRANCH_CAPTURE_EXIT"
fi
if [ -f "$script_dir/../last-created-branch.txt" ]; then
  branch=$(cat "$script_dir/../last-created-branch.txt")
elif [ "${SANDBOX_IS_USER_BRANCH:-false}" = "true" ]; then
  branch=testuser/existing
else
  branch=main
fi
if [ "${SANDBOX_BRANCH_CAPTURE_EMPTY:-false}" = "true" ]; then
  echo "BRANCH="
else
  echo "BRANCH=$branch"
fi
exit 0
STUB
    chmod +x "$SANDBOX/scripts/git-current-branch.sh"

    cat >"$SANDBOX/scripts/run-step1-plan-log.sh" <<'STUB'
#!/usr/bin/env bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf 'run-step1-plan-log %s\n' "$*" >>"$script_dir/../invoke-log.txt"
if [ "${SANDBOX_RUN_PLAN_LOG_EXIT:-0}" -ne 0 ]; then
  printf 'plan log failure\n' >&2
  exit "$SANDBOX_RUN_PLAN_LOG_EXIT"
fi
tmpdir=""
while [ $# -gt 0 ]; do
  case "$1" in
    --implement-tmpdir) tmpdir=$2; shift 2 ;;
    *) shift ;;
  esac
done
[ -n "$tmpdir" ] && printf 'plan log\n' >"$tmpdir/plan-goals-test.md"
exit 0
STUB
    chmod +x "$SANDBOX/scripts/run-step1-plan-log.sh"

    cat >"$SANDBOX/scripts/tracking-issue-summary.sh" <<'STUB'
#!/usr/bin/env bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf 'tracking-issue-summary %s\n' "$*" >>"$script_dir/../invoke-log.txt"
if [ "${SANDBOX_PLAN_SUMMARY_EXIT:-0}" -ne 0 ]; then
  printf 'tracking summary failure\n' >&2
  exit "$SANDBOX_PLAN_SUMMARY_EXIT"
fi
exit 0
STUB
    chmod +x "$SANDBOX/scripts/tracking-issue-summary.sh"

    mkdir -p "$SANDBOX/python/stubs/redact"
    cat >"$SANDBOX/python/stubs/redact/secrets" <<'STUB'
#!/usr/bin/env bash
if [ "${SANDBOX_REDACT_SECRETS_EXIT:-0}" -ne 0 ]; then
  printf 'redact secrets failure\n' >&2
  exit "$SANDBOX_REDACT_SECRETS_EXIT"
fi
cat
exit 0
STUB
    chmod +x "$SANDBOX/python/stubs/redact/secrets"

    cat >"$SANDBOX/python/stubs/redact/tmpdir-paths" <<'STUB'
#!/usr/bin/env bash
input=$(cat)
if [ -n "${SANDBOX_REDACT_TMPDIR_MATCH:-}" ] && printf '%s' "$input" | grep -qF -- "$SANDBOX_REDACT_TMPDIR_MATCH"; then
  printf 'redact tmpdir failure\n' >&2
  exit "${SANDBOX_REDACT_TMPDIR_EXIT:-1}"
fi
if [ "${SANDBOX_REDACT_TMPDIR_EXIT:-0}" -ne 0 ]; then
  printf 'redact tmpdir failure\n' >&2
  exit "$SANDBOX_REDACT_TMPDIR_EXIT"
fi
printf '%s' "$input"
exit 0
STUB
    chmod +x "$SANDBOX/python/stubs/redact/tmpdir-paths"

    : >"$SANDBOX/invoke-log.txt"
}

write_gp1_session_setup() {
    cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
    chmod +x "$SANDBOX/python/stubs/session/setup"
}

run_bootstrap() {
    (
        cd "$SANDBOX" || exit 1
        env \
            CLAUDE_PLUGIN_ROOT="$SANDBOX" \
            PATH="$SANDBOX/bin:$PATH" \
            LARCH_QUIET_BREADCRUMB_FD="${LARCH_QUIET_BREADCRUMB_FD:-}" \
            bash "$SANDBOX/scripts/implement-bootstrap.sh" "$@"
    )
}

write_preflight_plan() {
    mkdir -p "$SANDBOX/preflight"
    printf 'Plan from issue\n' >"$SANDBOX/preflight/plan-from-issue.txt"
}

SANDBOX_TMP=""
SANDBOX=""

# --- GP1-infra ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(run_bootstrap --up-to-phase infra 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP1-infra exit 0"
assert_contains "IMPLEMENT_TMPDIR=$SANDBOX_TMP" "$out" "GP1 IMPLEMENT_TMPDIR"
assert_contains "SESSION_ID=sessstub" "$out" "GP1 SESSION_ID"
assert_contains "codex_available=true" "$out" "GP1 codex_available"
assert_contains "IMPLEMENT_BAIL_REASON=" "$out" "GP1 IMPLEMENT_BAIL_REASON tail present"
assert_not_contains "STEP_FAILED=" "$out" "GP1 no STEP_FAILED"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP-adopt ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runA 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP-adopt exit 0"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "GP-adopt branch"
assert_contains "ISSUE_NUMBER=123" "$out" "GP-adopt issue"
assert_contains "RUN_ID=runA" "$out" "GP-adopt run id"
assert_contains "DEFERRED=false" "$out" "GP-adopt not deferred"
assert_contains "STALL_TRACKING=false" "$out" "GP-adopt no stall"
assert_contains "RUN_ID=runA" "$(cat "$SANDBOX_TMP/parent-issue.md")" "GP-adopt sentinel run id"
assert_contains "FORKED_TARGET=false" "$(cat "$SANDBOX_TMP/session-env.sh")" "GP-adopt session-env fork default"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_occurrences 'token-ledger mark Step 0 — tracking issue' "$invoke" 1 "GP-adopt bootstrap token mark once"
assert_occurrences 'timing-ledger mark Step 0 — tracking issue' "$invoke" 1 "GP-adopt bootstrap timing mark once"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP-adopt-session-id ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP-adopt-session-id exit 0"
assert_contains "RUN_ID=sessstub" "$out" "GP-adopt-session-id run id"
assert_contains "RUN_ID=sessstub" "$(cat "$SANDBOX_TMP/parent-issue.md")" "GP-adopt-session-id sentinel run id"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_occurrences 'token-ledger mark Step 0 — tracking issue' "$invoke" 1 "GP-adopt-session-id bootstrap token mark once"
assert_occurrences 'timing-ledger mark Step 0 — tracking issue' "$invoke" 1 "GP-adopt-session-id bootstrap timing mark once"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP2 sentinel resume ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=resume1\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP2 exit 0"
assert_contains "BRANCH_SELECTED=branch-1-resume" "$out" "GP2 branch"
assert_contains "ISSUE_NUMBER=123" "$out" "GP2 issue"
assert_contains "RUN_ID=resume1" "$out" "GP2 run id"
assert_contains "DEFERRED=false" "$out" "GP2 not deferred"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_occurrences 'token-ledger mark Step 0 — tracking issue' "$invoke" 1 "GP2 bootstrap token mark once"
assert_occurrences 'timing-ledger mark Step 0 — tracking issue' "$invoke" 1 "GP2 bootstrap timing mark once"
assert_contains "post-tracking-issue --emergency-requested false" "$invoke" "GP2 metadata refresh clears emergency"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP2-persisted-emergency sentinel resume keeps emergency metadata ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=resume1\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
printf 'NO_ISSUES=false\nEMERGENCY_REQUESTED=true\n' > "$SANDBOX_TMP/run-flags.sh"
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --emergency-requested false 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP2-persisted-emergency exit 0"
assert_contains "EMERGENCY_REQUESTED=true" "$out" "GP2-persisted-emergency stdout KV"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "post-tracking-issue --emergency-requested true" "$invoke" "GP2-persisted-emergency metadata stays true"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP2-emergency sentinel resume refreshes metadata ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=resume1\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP2-emergency exit 0"
assert_contains "BRANCH_SELECTED=branch-1-resume" "$out" "GP2-emergency branch"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "persist-implement-run-flags --implement-tmpdir $SANDBOX_TMP --no-issues false --emergency-requested true" "$invoke" "GP2-emergency persist arg"
assert_contains "post-tracking-issue --emergency-requested true" "$invoke" "GP2-emergency metadata refresh"
assert_contains "EMERGENCY_REQUESTED=true" "$(cat "$SANDBOX_TMP/run-flags.sh")" "GP2-emergency run flags"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP2-resume metadata post failure is surfaced ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=resume1\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(LARCH_TEST_POSTED=false run_bootstrap --up-to-phase tracking --issue-number 123 --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP2-resume-post-fail exit 0"
assert_contains "DEFERRED=true" "$out" "GP2-resume-post-fail deferred"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_contains "Step 0 tracking adoption — Branch 1 resume metadata post" "$issues" "GP2-resume-post-fail execution issue site"
assert_contains "ERROR=post failed" "$issues" "GP2-resume-post-fail execution issue body"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP3 forked_target ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --forked-target true --upstream-repo upstream/repo 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP3 exit 0"
assert_contains "BRANCH_SELECTED=forked-target-skip" "$out" "GP3 branch"
assert_line "ISSUE_NUMBER=" "$out" "GP3 empty issue"
assert_contains "DEFERRED=true" "$out" "GP3 deferred"
assert_contains "FORKED_TARGET=true" "$(cat "$SANDBOX_TMP/session-env.sh")" "GP3 session-env fork true"
assert_contains "TITLE_FILE=$SANDBOX_TMP/upstream-issue-title.txt" "$(cat "$SANDBOX_TMP/upstream-context.out")" "GP3 upstream title artifact"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains 'cli.py issue context --issue 123 --repo upstream/repo' "$invoke" "GP3 upstream context invoked"
assert_occurrences 'token-ledger mark Step 0 — tracking issue' "$invoke" 1 "GP3 bootstrap token mark once"
assert_occurrences 'timing-ledger mark Step 0 — tracking issue' "$invoke" 1 "GP3 bootstrap timing mark once"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP3-upstream-context-fail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
export GET_ISSUE_CONTEXT_EXIT=7
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --forked-target true --upstream-repo upstream/repo 2>/dev/null) && rc=$? || rc=$?
unset GET_ISSUE_CONTEXT_EXIT
assert_rc "$rc" 0 "GP3-upstream-context-fail exit 0"
assert_contains "BRANCH_SELECTED=forked-target-skip" "$out" "GP3-upstream-context-fail branch"
assert_contains "Step 0 tracking adoption — forked target upstream context" "$(cat "$SANDBOX_TMP/execution-issues.md")" "GP3-upstream-context-fail execution issues"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP-repo-unavail-tracking ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=
echo REPO_UNAVAILABLE=true
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP-repo-unavail-tracking exit 0"
assert_contains "BRANCH_SELECTED=repo-unavailable-skip" "$out" "GP-repo-unavail-tracking branch"
assert_line "ISSUE_NUMBER=" "$out" "GP-repo-unavail-tracking empty issue"
assert_contains "DEFERRED=true" "$out" "GP-repo-unavail-tracking deferred"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_occurrences 'token-ledger mark Step 0 — tracking issue' "$invoke" 1 "GP-repo-unavail-tracking bootstrap token mark once"
assert_occurrences 'timing-ledger mark Step 0 — tracking issue' "$invoke" 1 "GP-repo-unavail-tracking bootstrap timing mark once"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP-repo-unavail-plan ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=
echo REPO_UNAVAILABLE=true
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
out=$(run_bootstrap --up-to-phase plan --issue-number 123 --run-id runRepoSkip --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP-repo-unavail-plan exit 0"
assert_contains "BRANCH_SELECTED=repo-unavailable-skip" "$out" "GP-repo-unavail-plan branch"
assert_contains "DEFERRED=true" "$out" "GP-repo-unavail-plan deferred"
assert_line "PLAN_FILE=" "$out" "GP-repo-unavail-plan empty plan file"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "snapshot-untracked --output $SANDBOX_TMP/untracked-baseline.z --nul" "$invoke" "GP-repo-unavail-plan snapshot"
assert_not_contains "gh issue view" "$invoke" "GP-repo-unavail-plan no gh"
assert_not_contains "persist-implement-run-flags" "$invoke" "GP-repo-unavail-plan no persist"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP4 repo_unavailable ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=
echo REPO_UNAVAILABLE=true
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
stderrf=$(mktemp "${TMPDIR:-/tmp}/larch-ib-gp4.XXXXXX")
out=$(run_bootstrap --up-to-phase infra 2>"$stderrf") && rc=$? || rc=$?
err=$(cat "$stderrf")
rm -f "$stderrf"
assert_rc "$rc" 0 "GP4 exit 0"
assert_contains "REPO_UNAVAILABLE=true" "$out" "GP4 REPO_UNAVAILABLE in stdout"
assert_contains "**⚠ Could not determine repository name." "$err" "GP4 repo warning on stderr"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B1 sentinel mismatch fall-through ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=999\nRUN_ID=oldrun\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runB 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B1 exit 0"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "B1 fall-through branch"
assert_contains "RUN_ID=runB" "$out" "B1 fresh run id"
assert_contains "ISSUE_NUMBER=123" "$(cat "$SANDBOX_TMP/parent-issue.md")" "B1 sentinel replaced"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B2 CLOSED bail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(LARCH_TEST_ISSUE_STATE=CLOSED run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B2 exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=adopted-issue-closed" "$out" "B2 bail reason"
assert_line "BRANCH_SELECTED=" "$out" "B2 no branch"
assert_line "ISSUE_NUMBER=" "$out" "B2 empty issue tail"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B2-plan CLOSED bail guard ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(LARCH_TEST_ISSUE_STATE=CLOSED run_bootstrap --up-to-phase plan --issue-number 123 --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B2-plan exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=adopted-issue-closed" "$out" "B2-plan bail reason"
assert_not_contains "IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-3" "$out" "B2-plan no phase-3 overwrite"
assert_not_contains "IMPLEMENT_BAIL_REASON=run-flags-persist-failed" "$out" "B2-plan no run-flags overwrite"
assert_not_contains "IMPLEMENT_BAIL_REASON=dirty-tree" "$out" "B2-plan no dirty-tree overwrite"
assert_not_contains "IMPLEMENT_BAIL_REASON=branch-create-failed" "$out" "B2-plan no branch-create overwrite"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B3 IS_PR bail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(LARCH_TEST_IS_PR=true run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B3 exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=adopted-issue-is-pr" "$out" "B3 bail reason"
assert_line "BRANCH_SELECTED=" "$out" "B3 no branch"
assert_line "ISSUE_NUMBER=" "$out" "B3 empty issue tail"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B3-plan IS_PR bail guard ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(LARCH_TEST_IS_PR=true run_bootstrap --up-to-phase plan --issue-number 123 --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B3-plan exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=adopted-issue-is-pr" "$out" "B3-plan bail reason"
assert_not_contains "IMPLEMENT_BAIL_REASON=run-flags-persist-failed" "$out" "B3-plan no run-flags overwrite"
assert_not_contains "IMPLEMENT_BAIL_REASON=dirty-tree" "$out" "B3-plan no dirty-tree overwrite"
assert_not_contains "IMPLEMENT_BAIL_REASON=branch-create-failed" "$out" "B3-plan no branch-create overwrite"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B4 POSTED=false deferred ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=999\nRUN_ID=stale\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(LARCH_TEST_POSTED=false run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runD 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B4 exit 0"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "B4 branch"
assert_contains "DEFERRED=true" "$out" "B4 deferred"
assert_not_contains "STALL_TRACKING=true" "$out" "B4 no stall"
assert_not_contains "IMPLEMENT_BAIL_REASON=tracking-init-failed" "$out" "B4 no tracking-init-failed bail"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "tracking-issue-write rename --issue 123 --state implementing" "$invoke" "B4 rename fires before post-tracking-issue"
assert_order "tracking-issue-write rename --issue 123 --state implementing" "post-tracking-issue --implement-tmpdir $SANDBOX_TMP --issue-number 123 --run-id runD --adopted true" "$invoke" "B4 rename before post-tracking-issue"
if [ ! -f "$SANDBOX_TMP/parent-issue.md" ]; then
    PASS=$((PASS + 1))
    echo "PASS: B4 no sentinel"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B4 sentinel should not exist"
fi
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B4-plan POSTED=false deferred guard ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(LARCH_TEST_POSTED=false run_bootstrap --up-to-phase plan --issue-number 123 --run-id runD --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B4-plan exit 0"
assert_contains "DEFERRED=true" "$out" "B4-plan deferred"
assert_not_contains "IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-3" "$out" "B4-plan no phase-3 overwrite"
assert_not_contains "IMPLEMENT_BAIL_REASON=run-flags-persist-failed" "$out" "B4-plan no run-flags bail"
assert_not_contains "IMPLEMENT_BAIL_REASON=dirty-tree" "$out" "B4-plan no dirty-tree bail"
assert_not_contains "IMPLEMENT_BAIL_REASON=branch-create-failed" "$out" "B4-plan no branch-create bail"
if [ -f "$SANDBOX_TMP/plan.txt" ] && grep -qxF "Plan from issue" "$SANDBOX_TMP/plan.txt"; then
    PASS=$((PASS + 1))
    echo "PASS: B4-plan plan.txt materialized"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B4-plan plan.txt materialized"
fi
if [ -f "$SANDBOX_TMP/feature-description.txt" ] && grep -qxF "Test Feature" "$SANDBOX_TMP/feature-description.txt"; then
    PASS=$((PASS + 1))
    echo "PASS: B4-plan feature-description.txt materialized"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B4-plan feature-description.txt materialized"
fi
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "tracking-issue-write rename --issue 123 --state implementing" "$invoke" "B4-plan rename fires before post-tracking-issue"
assert_order "tracking-issue-write rename --issue 123 --state implementing" "post-tracking-issue --implement-tmpdir $SANDBOX_TMP --issue-number 123 --run-id runD --adopted true" "$invoke" "B4-plan rename before post-tracking-issue"
assert_contains "gh issue view 123" "$invoke" "B4-plan gh invoked"
assert_contains "persist-implement-run-flags" "$invoke" "B4-plan persist invoked"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B4-all POSTED=false deferred guard ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
stderrf=$(mktemp "${TMPDIR:-/tmp}/larch-ib-b4-all.XXXXXX")
out=$(LARCH_TEST_POSTED=false run_bootstrap --up-to-phase all --issue-number 123 --run-id runD --preflight-tmpdir "$SANDBOX/preflight" 2>"$stderrf") && rc=$? || rc=$?
err=$(cat "$stderrf")
rm -f "$stderrf"
assert_rc "$rc" 0 "B4-all exit 0"
assert_contains "DEFERRED=true" "$out" "B4-all deferred"
assert_line "coder=codex" "$out" "B4-all coder"
assert_line "coder_fallback=" "$out" "B4-all no fallback"
assert_not_contains "IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-3" "$out" "B4-all no phase-3 overwrite"
assert_not_contains "IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-4" "$out" "B4-all no phase-4 overwrite"
if [ -f "$SANDBOX_TMP/plan.txt" ] && grep -qxF "Plan from issue" "$SANDBOX_TMP/plan.txt"; then
    PASS=$((PASS + 1))
    echo "PASS: B4-all plan.txt materialized"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B4-all plan.txt materialized"
fi
if [ -f "$SANDBOX_TMP/feature-description.txt" ] && grep -qxF "Test Feature" "$SANDBOX_TMP/feature-description.txt"; then
    PASS=$((PASS + 1))
    echo "PASS: B4-all feature-description.txt materialized"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B4-all feature-description.txt materialized"
fi
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "tracking-issue-write rename --issue 123 --state implementing" "$invoke" "B4-all rename fires before post-tracking-issue"
assert_order "tracking-issue-write rename --issue 123 --state implementing" "post-tracking-issue --implement-tmpdir $SANDBOX_TMP --issue-number 123 --run-id runD --adopted true" "$invoke" "B4-all rename before post-tracking-issue"
assert_contains "gh issue view 123" "$invoke" "B4-all gh invoked"
assert_contains "persist-implement-run-flags" "$invoke" "B4-all persist invoked"
assert_not_contains '→ step0: coder=' "$out" "B4-all coder breadcrumb stays off stdout"
assert_contains '→ step0: coder=codex' "$err" "B4-all coder breadcrumb surfaces on stderr"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B4-all-breadcrumb POSTED=false deferred guard ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(LARCH_TEST_POSTED=false run_bootstrap --up-to-phase all --issue-number 123 --run-id runDeferredBreadcrumb --preflight-tmpdir "$SANDBOX/preflight" 2>&1) && rc=$? || rc=$?
assert_rc "$rc" 0 "B4-all-breadcrumb exit 0"
assert_contains "DEFERRED=true" "$out" "B4-all-breadcrumb deferred"
n=$(printf '%s\n' "$out" | grep -cF '→ step0: coder=codex' || true)
if [ "$n" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: B4-all-breadcrumb coder breadcrumb once"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B4-all-breadcrumb coder breadcrumb expected 1 got $n"
fi
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5 larch-log init fail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(LARCH_TEST_LARCH_LOG_FAIL=true run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runE 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5 exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=tracking-init-failed" "$out" "B5 bail reason"
assert_contains "STALL_TRACKING=true" "$out" "B5 stall"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "B5 branch"
assert_contains "ISSUE_NUMBER=123" "$out" "B5 preserves issue"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "tracking-issue-write rename --issue 123 --state implementing" "$invoke" "B5 rename attempted"
assert_order "tracking-issue-write rename --issue 123 --state implementing" "larch-log init --log-root $SANDBOX_TMP/larch-logs --skill implement --run-id runE" "$invoke" "B5 rename before larch-log init"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-all larch-log init fail guard ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(LARCH_TEST_LARCH_LOG_FAIL=true run_bootstrap --up-to-phase all --issue-number 123 --run-id runE --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-all exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=tracking-init-failed" "$out" "B5-all bail reason"
assert_line "coder=" "$out" "B5-all empty coder"
assert_line "coder_fallback=" "$out" "B5-all empty fallback"
assert_not_contains "IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-3" "$out" "B5-all no phase-3 overwrite"
assert_not_contains "IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-4" "$out" "B5-all no phase-4 overwrite"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "gh issue view" "$invoke" "B5-all no gh"
assert_not_contains "persist-implement-run-flags" "$invoke" "B5-all no persist"
assert_not_contains "check-mid-run-dirty-tree" "$invoke" "B5-all no dirty checkpoint"
assert_not_contains '→ step0: coder=' "$out" "B5-all no coder breadcrumb"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-plan larch-log init fail guard ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(LARCH_TEST_LARCH_LOG_FAIL=true run_bootstrap --up-to-phase plan --issue-number 123 --run-id runE --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=tracking-init-failed" "$out" "B5-plan bail reason"
assert_not_contains "IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-3" "$out" "B5-plan no phase-3 overwrite"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-branch1 larch-log init fail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=resume-fail\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(LARCH_TEST_LARCH_LOG_FAIL=true run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-branch1 exit 0"
assert_contains "BRANCH_SELECTED=branch-1-resume" "$out" "B5-branch1 branch"
assert_contains "IMPLEMENT_BAIL_REASON=tracking-init-failed" "$out" "B5-branch1 bail reason"
assert_contains "STALL_TRACKING=true" "$out" "B5-branch1 stall"
assert_contains "RUN_ID=resume-fail" "$out" "B5-branch1 preserves run id"
assert_contains "ISSUE_NUMBER=123" "$out" "B5-branch1 preserves issue"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "tracking-issue-write rename --issue 123 --state implementing" "$invoke" "B5-branch1 rename attempted"
assert_order "tracking-issue-write rename --issue 123 --state implementing" "larch-log init --log-root $SANDBOX_TMP/larch-logs --skill implement --run-id resume-fail" "$invoke" "B5-branch1 rename before larch-log init"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-plan-green ---
for case_data in \
    "UPPER CASE FEATURE|upper-case-feature" \
    "Symbols: Plan + Branch!!|symbols-plan-branch" \
    "!!!|issue" \
    "This title is deliberately longer than forty characters for slug coverage|this-title-is-deliberately-longer-than-f"
do
    SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
    build_sandbox
    write_gp1_session_setup
    write_preflight_plan
    title=${case_data%%|*}
    expected_slug=${case_data#*|}
    out=$(SANDBOX_GH_TITLE="$title" run_bootstrap --up-to-phase plan --issue-number 123 --run-id runPlan --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
    assert_rc "$rc" 0 "B5-plan-green $expected_slug exit 0"
    assert_contains "BRANCH_NAME=testuser/$expected_slug-123" "$out" "B5-plan-green $expected_slug branch"
    assert_contains "BRANCH_ACTION=created" "$out" "B5-plan-green $expected_slug action"
    assert_contains "PLAN_FILE=$SANDBOX_TMP/plan.txt" "$out" "B5-plan-green $expected_slug plan file"
    if [ -f "$SANDBOX_TMP/plan.txt" ] && grep -qxF "Plan from issue" "$SANDBOX_TMP/plan.txt"; then
        PASS=$((PASS + 1))
        echo "PASS: B5-plan-green $expected_slug plan.txt materialized"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: B5-plan-green $expected_slug plan.txt materialized"
    fi
    if [ -f "$SANDBOX_TMP/feature-description.txt" ] && grep -qxF "$title" "$SANDBOX_TMP/feature-description.txt"; then
        PASS=$((PASS + 1))
        echo "PASS: B5-plan-green $expected_slug feature-description.txt materialized"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: B5-plan-green $expected_slug feature-description.txt materialized"
    fi
    invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
    assert_contains "token-ledger mark implement Step 0 — plan materialization" "$invoke" "B5-plan-green $expected_slug token mark"
    assert_contains "timing-ledger mark implement Step 0 — plan materialization" "$invoke" "B5-plan-green $expected_slug timing mark"
        assert_order "snapshot-untracked" "gh issue view 123" "$invoke" "B5-plan-green $expected_slug snapshot before gh"
    assert_order "persist-implement-run-flags" "check-mid-run-dirty-tree" "$invoke" "B5-plan-green $expected_slug persist before dirty"
    assert_order "check-mid-run-dirty-tree" "create-branch --branch testuser/$expected_slug-123" "$invoke" "B5-plan-green $expected_slug dirty before branch"
    assert_order "create-branch --branch testuser/$expected_slug-123" "git-current-branch" "$invoke" "B5-plan-green $expected_slug branch before capture"
    assert_order "git-current-branch" "run-step1-plan-log" "$invoke" "B5-plan-green $expected_slug capture before plan log"
    assert_order "run-step1-plan-log" "voting write-tally" "$invoke" "B5-plan-green $expected_slug plan log before tally"
    assert_order "voting write-tally" "tracking-issue-summary upsert-summary" "$invoke" "B5-plan-green $expected_slug tally before summary"
    rm -rf "$SANDBOX" "$SANDBOX_TMP"
done

# --- B5-plan-emergency ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
printf 'BYPASS kind=missing-plan issue=123\n' >"$SANDBOX/preflight/emergency-bypass.log"
out=$(run_bootstrap --up-to-phase plan --issue-number 123 --run-id runEmergency --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan-emergency exit 0"
assert_contains "EMERGENCY_REQUESTED=true" "$out" "B5-plan-emergency stdout KV"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "persist-implement-run-flags --implement-tmpdir $SANDBOX_TMP --no-issues false --emergency-requested true" "$invoke" "B5-plan-emergency persist arg"
assert_contains "post-tracking-issue --emergency-requested true" "$invoke" "B5-plan-emergency metadata arg"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_contains "implement-bootstrap emergency-bypass-log" "$issues" "B5-plan-emergency warning site"
assert_contains "BYPASS kind=missing-plan issue=123" "$issues" "B5-plan-emergency warning content"
assert_contains "EMERGENCY_REQUESTED=true" "$(cat "$SANDBOX_TMP/run-flags.sh")" "B5-plan-emergency run flags"
assert_contains "Plan from issue" "$(cat "$SANDBOX_TMP/plan.txt")" "B5-plan-emergency plan.txt materialized"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-plan-emergency-malformed-plan ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
printf 'BYPASS kind=malformed-plan issue=123\n' >"$SANDBOX/preflight/emergency-bypass.log"
out=$(run_bootstrap --up-to-phase plan --issue-number 123 --run-id runEmergencyMalformed --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan-emergency-malformed-plan exit 0"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_contains "BYPASS kind=malformed-plan issue=123" "$issues" "B5-plan-emergency-malformed-plan warning content"
assert_contains "Plan from issue" "$(cat "$SANDBOX_TMP/plan.txt")" "B5-plan-emergency-malformed-plan plan.txt materialized"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-plan-emergency-audit-refuse ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
printf 'BYPASS kind=audit-refuse issue=123\n' >"$SANDBOX/preflight/emergency-bypass.log"
out=$(run_bootstrap --up-to-phase plan --issue-number 123 --run-id runEmergencyAuditRefuse --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan-emergency-audit-refuse exit 0"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_contains "BYPASS kind=audit-refuse issue=123" "$issues" "B5-plan-emergency-audit-refuse warning content"
assert_contains "Plan from issue" "$(cat "$SANDBOX_TMP/plan.txt")" "B5-plan-emergency-audit-refuse plan.txt materialized"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-plan-emergency-clean ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(run_bootstrap --up-to-phase plan --issue-number 123 --run-id runEmergencyClean --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan-emergency-clean exit 0"
assert_contains "EMERGENCY_REQUESTED=true" "$out" "B5-plan-emergency-clean stdout KV"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "persist-implement-run-flags --implement-tmpdir $SANDBOX_TMP --no-issues false --emergency-requested true" "$invoke" "B5-plan-emergency-clean persist arg"
assert_contains "post-tracking-issue --emergency-requested true" "$invoke" "B5-plan-emergency-clean metadata arg"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_not_contains "implement-bootstrap emergency-bypass-log" "$issues" "B5-plan-emergency-clean no bypass warning"
assert_contains "Plan from issue" "$(cat "$SANDBOX_TMP/plan.txt")" "B5-plan-emergency-clean plan.txt materialized"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-plan-bypass-log ignored when emergency false ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
printf 'BYPASS kind=missing-plan issue=123\n' >"$SANDBOX/preflight/emergency-bypass.log"
out=$(run_bootstrap --up-to-phase plan --issue-number 123 --run-id runNonEmergencyBypass --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan-bypass-log ignored when emergency false exit 0"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_not_contains "BYPASS kind=missing-plan issue=123" "$issues" "B5-plan-bypass-log ignored when emergency false no warning content"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-coder-implicit-cursor ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(run_bootstrap --up-to-phase coder --issue-number 123 --run-id runCoderCursor --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-coder-implicit-cursor exit 0"
assert_line "coder=codex" "$out" "B5-coder-implicit-cursor coder"
assert_line "coder_fallback=" "$out" "B5-coder-implicit-cursor no fallback"
assert_line "IMPLEMENT_BAIL_REASON=" "$out" "B5-coder-implicit-cursor no bail"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-coder-implicit-codex ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=false
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=false
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
out=$(run_bootstrap --up-to-phase coder --issue-number 123 --run-id runCoderCodex --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-coder-implicit-codex exit 0"
assert_line "coder=codex" "$out" "B5-coder-implicit-codex coder"
assert_line "coder_fallback=" "$out" "B5-coder-implicit-codex no fallback"
assert_line "IMPLEMENT_BAIL_REASON=" "$out" "B5-coder-implicit-codex no bail"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-coder-implicit-claude ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=false
echo CURSOR_PRESENT=false
echo CODEX_BINARY_FOUND=false
echo CURSOR_BINARY_FOUND=false
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
stderrf=$(mktemp "${TMPDIR:-/tmp}/larch-ib-coder-claude.XXXXXX")
out=$(run_bootstrap --up-to-phase coder --issue-number 123 --run-id runCoderClaude --preflight-tmpdir "$SANDBOX/preflight" 2>"$stderrf") && rc=$? || rc=$?
err=$(cat "$stderrf")
rm -f "$stderrf"
assert_rc "$rc" 0 "B5-coder-implicit-claude exit 0"
assert_line "coder=claude" "$out" "B5-coder-implicit-claude coder"
assert_line "coder_fallback=true" "$out" "B5-coder-implicit-claude fallback"
assert_contains "Codex unavailable — falling back to Cursor implementer" "$err" "B5-coder-implicit-claude codex warning"
assert_contains "Cursor unavailable — falling back to Claude implementer" "$err" "B5-coder-implicit-claude cursor warning"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_occurrences "Step 0 (implementer waterfall)" "$issues" 2 "B5-coder-implicit-claude execution issues"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "larch-log manifest --log-root $SANDBOX_TMP/larch-logs --skill implement --run-id runCoderClaude --field coder_fallback=true" "$invoke" "B5-coder-implicit-claude manifest fallback"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-coder-explicit-cursor-happy ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
out=$(run_bootstrap --up-to-phase coder --issue-number 123 --run-id runCoderExplicitCursor --preflight-tmpdir "$SANDBOX/preflight" --coder cursor 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-coder-explicit-cursor-happy exit 0"
assert_line "coder=cursor" "$out" "B5-coder-explicit-cursor-happy coder"
assert_line "coder_fallback=" "$out" "B5-coder-explicit-cursor-happy no fallback"
assert_line "IMPLEMENT_BAIL_REASON=" "$out" "B5-coder-explicit-cursor-happy no bail"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-coder-explicit-codex-happy ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
out=$(run_bootstrap --up-to-phase coder --issue-number 123 --run-id runCoderExplicitCodex --preflight-tmpdir "$SANDBOX/preflight" --coder codex 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-coder-explicit-codex-happy exit 0"
assert_line "coder=codex" "$out" "B5-coder-explicit-codex-happy coder"
assert_line "coder_fallback=" "$out" "B5-coder-explicit-codex-happy no fallback"
assert_line "IMPLEMENT_BAIL_REASON=" "$out" "B5-coder-explicit-codex-happy no bail"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-coder-explicit-claude-happy ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=false
echo CURSOR_PRESENT=false
echo CODEX_BINARY_FOUND=false
echo CURSOR_BINARY_FOUND=false
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
out=$(run_bootstrap --up-to-phase coder --issue-number 123 --run-id runCoderExplicitClaude --preflight-tmpdir "$SANDBOX/preflight" --coder claude 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-coder-explicit-claude-happy exit 0"
assert_line "coder=claude" "$out" "B5-coder-explicit-claude-happy coder"
assert_line "coder_fallback=" "$out" "B5-coder-explicit-claude-happy no fallback"
assert_line "IMPLEMENT_BAIL_REASON=" "$out" "B5-coder-explicit-claude-happy no bail"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-coder-explicit-unavailable-binary-missing ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=false
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=false
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
stderrf=$(mktemp "${TMPDIR:-/tmp}/larch-ib-coder-explicit.XXXXXX")
out=$(run_bootstrap --up-to-phase coder --issue-number 123 --run-id runCoderExplicit --preflight-tmpdir "$SANDBOX/preflight" --coder cursor 2>"$stderrf") && rc=$? || rc=$?
err=$(cat "$stderrf")
rm -f "$stderrf"
assert_rc "$rc" 0 "B5-coder-explicit-unavailable-binary-missing exit 0"
assert_line "coder=codex" "$out" "B5-coder-explicit-unavailable-binary-missing waterfalls cursor->codex (#3207)"
assert_not_contains "IMPLEMENT_BAIL_REASON=coder-unavailable" "$out" "B5-coder-explicit-unavailable-binary-missing no bail (#3207 waterfall)"
assert_line "STALL_TRACKING=false" "$out" "B5-coder-explicit-unavailable-binary-missing no stall (#3207 waterfall)"
assert_contains "--coder=cursor requested but Cursor binary not found" "$err" "B5-coder-explicit-unavailable-binary-missing warning"
assert_contains "Waterfalling to Codex" "$err" "B5-coder-explicit-unavailable-binary-missing waterfall target"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-coder-explicit-unavailable-undeterminable ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=false
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
stderrf=$(mktemp "${TMPDIR:-/tmp}/larch-ib-coder-undetermined.XXXXXX")
out=$(run_bootstrap --up-to-phase coder --issue-number 123 --run-id runCoderUndetermined --preflight-tmpdir "$SANDBOX/preflight" --coder cursor 2>"$stderrf") && rc=$? || rc=$?
err=$(cat "$stderrf")
rm -f "$stderrf"
assert_rc "$rc" 0 "B5-coder-explicit-unavailable-undeterminable exit 0"
assert_line "coder=codex" "$out" "B5-coder-explicit-unavailable-undeterminable waterfalls cursor->codex (#3207)"
assert_not_contains "IMPLEMENT_BAIL_REASON=coder-unavailable" "$out" "B5-coder-explicit-unavailable-undeterminable no bail (#3207 waterfall)"
assert_contains "CURSOR_BINARY_FOUND could not be determined" "$err" "B5-coder-explicit-unavailable-undeterminable warning"
assert_contains "Waterfalling to Codex" "$err" "B5-coder-explicit-unavailable-undeterminable waterfall target"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-coder-explicit-unavailable-runtime-probe-failed ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=false
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
stderrf=$(mktemp "${TMPDIR:-/tmp}/larch-ib-coder-runtime-failed.XXXXXX")
out=$(run_bootstrap --up-to-phase coder --issue-number 123 --run-id runCoderRuntimeFail --preflight-tmpdir "$SANDBOX/preflight" --coder codex 2>"$stderrf") && rc=$? || rc=$?
err=$(cat "$stderrf")
rm -f "$stderrf"
assert_rc "$rc" 0 "B5-coder-explicit-unavailable-runtime-probe-failed exit 0"
assert_line "coder=cursor" "$out" "B5-coder-explicit-unavailable-runtime-probe-failed waterfalls codex->cursor (#3207)"
assert_not_contains "IMPLEMENT_BAIL_REASON=coder-unavailable" "$out" "B5-coder-explicit-unavailable-runtime-probe-failed no bail (#3207 waterfall)"
assert_contains "--coder=codex requested but Codex runtime probe failed / auth error" "$err" "B5-coder-explicit-unavailable-runtime-probe-failed warning"
assert_contains "Waterfalling to Cursor" "$err" "B5-coder-explicit-unavailable-runtime-probe-failed waterfall target"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-coder-explicit-codex-binary-missing ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=false
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=false
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
stderrf=$(mktemp "${TMPDIR:-/tmp}/larch-ib-coder-codex-binary-missing.XXXXXX")
out=$(run_bootstrap --up-to-phase coder --issue-number 123 --run-id runCoderCodexBinaryMissing --preflight-tmpdir "$SANDBOX/preflight" --coder codex 2>"$stderrf") && rc=$? || rc=$?
err=$(cat "$stderrf")
rm -f "$stderrf"
assert_rc "$rc" 0 "B5-coder-explicit-codex-binary-missing exit 0"
assert_line "coder=cursor" "$out" "B5-coder-explicit-codex-binary-missing waterfalls codex->cursor (#3207)"
assert_not_contains "IMPLEMENT_BAIL_REASON=coder-unavailable" "$out" "B5-coder-explicit-codex-binary-missing no bail (#3207 waterfall)"
assert_line "STALL_TRACKING=false" "$out" "B5-coder-explicit-codex-binary-missing no stall (#3207 waterfall)"
assert_contains "--coder=codex requested but Codex binary not found" "$err" "B5-coder-explicit-codex-binary-missing warning"
assert_contains "Waterfalling to Cursor" "$err" "B5-coder-explicit-codex-binary-missing waterfall target"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-coder-explicit-both-external-unavailable (#3207: codex -> cursor -> claude) ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=false
echo CURSOR_PRESENT=false
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
stderrf=$(mktemp "${TMPDIR:-/tmp}/larch-ib-coder-both-unavail.XXXXXX")
out=$(run_bootstrap --up-to-phase coder --issue-number 123 --run-id runCoderBothUnavail --preflight-tmpdir "$SANDBOX/preflight" --coder codex 2>"$stderrf") && rc=$? || rc=$?
err=$(cat "$stderrf")
rm -f "$stderrf"
assert_rc "$rc" 0 "B5-coder-explicit-both-external-unavailable exit 0"
assert_line "coder=claude" "$out" "B5-coder-explicit-both-external-unavailable waterfalls codex->cursor->claude (#3207)"
assert_line "coder_fallback=true" "$out" "B5-coder-explicit-both-external-unavailable coder_fallback set"
assert_not_contains "IMPLEMENT_BAIL_REASON=coder-unavailable" "$out" "B5-coder-explicit-both-external-unavailable no bail (#3207 waterfall)"
assert_contains "Cursor also unavailable" "$err" "B5-coder-explicit-both-external-unavailable claude fallback warning"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-coder-skip-repo-unavailable ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=
echo REPO_UNAVAILABLE=true
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
out=$(run_bootstrap --up-to-phase coder --issue-number 123 --run-id runCoderRepoUnavailable --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-coder-skip-repo-unavailable exit 0"
assert_line "PLAN_FILE=" "$out" "B5-coder-skip-repo-unavailable empty plan"
assert_line "coder=" "$out" "B5-coder-skip-repo-unavailable empty coder"
assert_line "coder_fallback=" "$out" "B5-coder-skip-repo-unavailable empty fallback"
assert_not_contains "IMPLEMENT_BAIL_REASON=coder-unavailable" "$out" "B5-coder-skip-repo-unavailable no coder-unavailable bail"
assert_not_contains '→ step0: coder=' "$out" "B5-coder-skip-repo-unavailable no coder breadcrumb"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-coder-skip-missing-feature-description ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sessA.XXXXXX)
SANDBOX_TMP_RESUME=$(mktemp -d /tmp/larch-ib-sessB.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
count_file="$SANDBOX/session-setup-count.txt"
count=0
if [ -f "\$count_file" ]; then
  count=\$(cat "\$count_file")
fi
count=\$((count + 1))
printf '%s\n' "\$count" >"\$count_file"
if [ "\$count" -eq 1 ]; then
  tmpdir="$SANDBOX_TMP"
else
  tmpdir="$SANDBOX_TMP_RESUME"
fi
echo SESSION_TMPDIR=\$tmpdir
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
out=$(run_bootstrap --up-to-phase plan --issue-number 123 --run-id runCoderMissingFeature --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-coder-skip-missing-feature-description setup plan exit 0"
rm -f "$SANDBOX_TMP/feature-description.txt"
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase coder --issue-number 123 --run-id runCoderMissingFeature --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-coder-skip-missing-feature-description exit 0"
assert_contains "PLAN_FILE=$SANDBOX_TMP/plan.txt" "$out" "B5-coder-skip-missing-feature-description keeps plan file"
assert_line "coder=" "$out" "B5-coder-skip-missing-feature-description empty coder"
assert_line "coder_fallback=" "$out" "B5-coder-skip-missing-feature-description empty fallback"
assert_line "IMPLEMENT_BAIL_REASON=" "$out" "B5-coder-skip-missing-feature-description empty bail"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
if [ "$(printf '%s\n' "$invoke" | grep -cF 'gh issue view 123' || true)" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: B5-coder-skip-missing-feature-description no second gh"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B5-coder-skip-missing-feature-description no second gh"
    printf '%s\n' "$invoke" | sed 's/^/    /'
fi
rm -rf "$SANDBOX" "$SANDBOX_TMP" "$SANDBOX_TMP_RESUME"

# --- B5-coder-skip-missing-plan ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
printf 'unexpected bypass text\n' >"$SANDBOX/preflight/emergency-bypass.log"
out=$(run_bootstrap --up-to-phase plan --issue-number 123 --run-id runEmergencyInvalid --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan-emergency-invalid-format exit 0"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_contains "invalid-format" "$issues" "B5-plan-emergency-invalid-format status"
assert_contains "BYPASS kind=<lowercase-token> issue=<number>" "$issues" "B5-plan-emergency-invalid-format grammar"
assert_contains "unexpected bypass text" "$issues" "B5-plan-emergency-invalid-format captured content"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-plan-emergency-empty-log-invalid-format ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
printf '\n' >"$SANDBOX/preflight/emergency-bypass.log"
out=$(run_bootstrap --up-to-phase plan --issue-number 123 --run-id runEmergencyEmpty --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan-emergency-empty-log-invalid-format exit 0"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_contains "invalid-format" "$issues" "B5-plan-emergency-empty-log-invalid-format status"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-plan-emergency-issue-mismatch-invalid-format ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
printf 'BYPASS kind=missing-plan issue=999\n' >"$SANDBOX/preflight/emergency-bypass.log"
out=$(run_bootstrap --up-to-phase plan --issue-number 123 --run-id runEmergencyIssueMismatch --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan-emergency-issue-mismatch-invalid-format exit 0"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_contains "invalid-format" "$issues" "B5-plan-emergency-issue-mismatch-invalid-format status"
assert_contains "issue=999" "$issues" "B5-plan-emergency-issue-mismatch-invalid-format captured content"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-plan-emergency-invalid-format-redacts-secrets ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
printf 'unexpected bypass text password=secret123\n' >"$SANDBOX/preflight/emergency-bypass.log"
mkdir -p "$SANDBOX/python/stubs/redact"
cat >"$SANDBOX/python/stubs/redact/secrets" <<'STUB'
#!/usr/bin/env bash
sed 's/secret123/<REDACTED>/g'
STUB
chmod +x "$SANDBOX/python/stubs/redact/secrets"
out=$(run_bootstrap --up-to-phase plan --issue-number 123 --run-id runEmergencyInvalidRedact --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan-emergency-invalid-format-redacts-secrets exit 0"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_contains "<REDACTED>" "$issues" "B5-plan-emergency-invalid-format-redacts-secrets redacted content"
assert_not_contains "secret123" "$issues" "B5-plan-emergency-invalid-format-redacts-secrets raw secret omitted"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-plan-emergency-append-fallback ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
printf 'BYPASS kind=missing-plan issue=123\n' >"$SANDBOX/preflight/emergency-bypass.log"
out=$(SANDBOX_APPEND_TOOL_FAILURE_EXIT=17 run_bootstrap --up-to-phase plan --issue-number 123 --run-id runEmergencyFallback --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan-emergency-append-fallback exit 0"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_contains "fallback append; helper failed" "$issues" "B5-plan-emergency-append-fallback fallback marker"
assert_contains "BYPASS kind=missing-plan issue=123" "$issues" "B5-plan-emergency-append-fallback preserved content"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-plan-emergency-append-double-failure ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
printf 'BYPASS kind=missing-plan issue=123\n' >"$SANDBOX/preflight/emergency-bypass.log"
mkdir -p "$SANDBOX/python/stubs/run-log"
cat >"$SANDBOX/python/stubs/run-log/append-entry" <<'STUB'
#!/usr/bin/env bash
exit 19
STUB
chmod +x "$SANDBOX/python/stubs/run-log/append-entry"
out=$(SANDBOX_APPEND_TOOL_FAILURE_EXIT=17 run_bootstrap --up-to-phase plan --issue-number 123 --run-id runEmergencyDoubleFailure --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 2 "B5-plan-emergency-append-double-failure exit 2"
assert_contains "STEP_FAILED=emergency-bypass-log" "$out" "B5-plan-emergency-append-double-failure STEP_FAILED"
if [ ! -e "$SANDBOX_TMP/.emergency-bypass-log-consumed" ]; then
    PASS=$((PASS + 1))
    echo "PASS: B5-plan-emergency-append-double-failure sentinel not consumed"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B5-plan-emergency-append-double-failure sentinel should not be consumed"
fi
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-coder-skip-missing-plan ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(run_bootstrap --up-to-phase plan --issue-number 123 --run-id runCoderMissingPlan --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-coder-skip-missing-plan setup plan exit 0"
rm -f "$SANDBOX_TMP/plan.txt"
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase coder --issue-number 123 --run-id runCoderMissingPlan --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-coder-skip-missing-plan exit 0"
assert_contains "PLAN_FILE=$SANDBOX_TMP/plan.txt" "$out" "B5-coder-skip-missing-plan keeps plan file path"
assert_line "coder=" "$out" "B5-coder-skip-missing-plan empty coder"
assert_line "coder_fallback=" "$out" "B5-coder-skip-missing-plan empty fallback"
assert_line "IMPLEMENT_BAIL_REASON=" "$out" "B5-coder-skip-missing-plan empty bail"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
if [ "$(printf '%s\n' "$invoke" | grep -cF 'gh issue view 123' || true)" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: B5-coder-skip-missing-plan no second gh"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B5-coder-skip-missing-plan no second gh"
    printf '%s\n' "$invoke" | sed 's/^/    /'
fi
rm -rf "$SANDBOX" "$SANDBOX_TMP" "$SANDBOX_TMP_RESUME"

# --- B5-plan-best-effort-failures ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(SANDBOX_RUN_PLAN_LOG_EXIT=7 SANDBOX_WRITE_TALLY_EXIT=8 SANDBOX_PLAN_SUMMARY_EXIT=9 run_bootstrap --up-to-phase plan --issue-number 123 --run-id runBestEffort --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan-best-effort-failures exit 0"
assert_contains "BRANCH_NAME=testuser/test-feature-123" "$out" "B5-plan-best-effort-failures branch"
assert_line "IMPLEMENT_BAIL_REASON=" "$out" "B5-plan-best-effort-failures empty bail"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_contains "Step 0 plan materialization — plan-goals-test" "$issues" "B5-plan-best-effort-failures plan-goals warning"
assert_contains "Step 0 plan materialization — plan-review tally" "$issues" "B5-plan-best-effort-failures tally warning"
assert_contains "Step 0 plan materialization — larch:plan summary" "$issues" "B5-plan-best-effort-failures summary warning"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-plan-goal-redaction-failure ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(SANDBOX_REDACT_SECRETS_EXIT=11 run_bootstrap --up-to-phase plan --issue-number 123 --run-id runGoalRedact --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan-goal-redaction-failure exit 0"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "--goal-text Implement issue #123: <REDACTED-TITLE>." "$invoke" "B5-plan-goal-redaction-failure fail-closed placeholder"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_contains "Step 0 plan materialization — goal text redaction" "$issues" "B5-plan-goal-redaction-failure warning"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-plan-summary-redaction-failure ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(SANDBOX_REDACT_TMPDIR_MATCH='Plan materialized for run' SANDBOX_REDACT_TMPDIR_EXIT=13 run_bootstrap --up-to-phase plan --issue-number 123 --run-id runSummaryRedact --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan-summary-redaction-failure exit 0"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_contains "Step 0 plan materialization — larch:plan summary redaction" "$issues" "B5-plan-summary-redaction-failure warning"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "tracking-issue-summary upsert-summary" "$invoke" "B5-plan-summary-redaction-failure summary invoked"
assert_not_contains '→ step0: larch:plan posted' "$out" "B5-plan-summary-redaction-failure no breadcrumb on stdout"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B6-plan-flags ---
for persist_rc in 2 1; do
    SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
    build_sandbox
    write_gp1_session_setup
    write_preflight_plan
    out=$(SANDBOX_PERSIST_FLAGS_EXIT=$persist_rc run_bootstrap --up-to-phase plan --issue-number 123 --run-id runFlags --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
    assert_rc "$rc" 0 "B6-plan-flags rc=$persist_rc exit 0"
    assert_contains "IMPLEMENT_BAIL_REASON=run-flags-persist-failed" "$out" "B6-plan-flags rc=$persist_rc bail"
    assert_contains "STALL_TRACKING=true" "$out" "B6-plan-flags rc=$persist_rc stall"
    invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
    assert_not_contains "check-mid-run-dirty-tree" "$invoke" "B6-plan-flags rc=$persist_rc no dirty check"
    assert_not_contains "create-branch --branch" "$invoke" "B6-plan-flags rc=$persist_rc no branch"
    assert_not_contains "git-current-branch" "$invoke" "B6-plan-flags rc=$persist_rc no branch capture"
    rm -rf "$SANDBOX" "$SANDBOX_TMP"
done

# --- B7-plan-dirty-tree ---
for dirty_status in dirty unknown; do
    SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
    build_sandbox
    write_gp1_session_setup
    write_preflight_plan
    out=$(SANDBOX_DIRTY_STATUS=$dirty_status run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDirty --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
    assert_rc "$rc" 0 "B7-plan-dirty-tree $dirty_status exit 0"
    assert_contains "IMPLEMENT_BAIL_REASON=dirty-tree" "$out" "B7-plan-dirty-tree $dirty_status bail"
    assert_contains "STALL_TRACKING=false" "$out" "B7-plan-dirty-tree $dirty_status no stall"
    invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
    assert_not_contains "create-branch --branch" "$invoke" "B7-plan-dirty-tree $dirty_status no branch"
    assert_not_contains "git-current-branch" "$invoke" "B7-plan-dirty-tree $dirty_status no branch capture"
    assert_not_contains "run-step1-plan-log" "$invoke" "B7-plan-dirty-tree $dirty_status no plan log"
    rm -rf "$SANDBOX" "$SANDBOX_TMP"
done

# --- B7-plan-dirty-tree probe failure ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(SANDBOX_DIRTY_EXIT=7 run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDirtyProbe --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-plan-dirty-tree probe failure exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=dirty-tree" "$out" "B7-plan-dirty-tree probe failure bail"
assert_contains "STALL_TRACKING=false" "$out" "B7-plan-dirty-tree probe failure no stall"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "create-branch --branch" "$invoke" "B7-plan-dirty-tree probe failure no branch"
assert_not_contains "git-current-branch" "$invoke" "B7-plan-dirty-tree probe failure no branch capture"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B7-plan-dirty-tree resume tail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sessA.XXXXXX)
SANDBOX_TMP_RESUME=$(mktemp -d /tmp/larch-ib-sessB.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
count_file="$SANDBOX/session-setup-count.txt"
count=0
if [ -f "\$count_file" ]; then
  count=\$(cat "\$count_file")
fi
count=\$((count + 1))
printf '%s\n' "\$count" >"\$count_file"
if [ "\$count" -eq 1 ]; then
  tmpdir="$SANDBOX_TMP"
else
  tmpdir="$SANDBOX_TMP_RESUME"
fi
echo SESSION_TMPDIR=\$tmpdir
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
out=$(SANDBOX_DIRTY_STATUS=dirty run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDirtyResume --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-plan-dirty-tree resume first pass exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=dirty-tree" "$out" "B7-plan-dirty-tree resume first pass bail"
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDirtyResume --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-plan-dirty-tree resume tail exit 0"
assert_line "IMPLEMENT_BAIL_REASON=" "$out" "B7-plan-dirty-tree resume tail clears bail"
assert_contains "BRANCH_NAME=testuser/test-feature-123" "$out" "B7-plan-dirty-tree resume tail branch"
assert_contains "PLAN_FILE=$SANDBOX_TMP/plan.txt" "$out" "B7-plan-dirty-tree resume tail keeps original tmpdir"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "post-tracking-issue --emergency-requested false" "$invoke" "B7-plan-dirty-tree resume tail refreshes metadata"
assert_contains "check-mid-run-dirty-tree --mode checkpoint" "$invoke" "B7-plan-dirty-tree resume tail initial dirty check"
if [ "$(printf '%s\n' "$invoke" | grep -cF "snapshot-untracked --output $SANDBOX_TMP/untracked-baseline.z --nul" || true)" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: B7-plan-dirty-tree resume tail no second snapshot"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B7-plan-dirty-tree resume tail no second snapshot"
    printf '%s\n' "$invoke" | sed 's/^/    /'
fi
if [ "$(printf '%s\n' "$invoke" | grep -cF 'gh issue view 123' || true)" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: B7-plan-dirty-tree resume tail no second gh"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B7-plan-dirty-tree resume tail no second gh"
    printf '%s\n' "$invoke" | sed 's/^/    /'
fi
assert_order "check-mid-run-dirty-tree --mode checkpoint" "create-branch --branch testuser/test-feature-123" "$invoke" "B7-plan-dirty-tree resume tail branch after clean checkpoint path"
if [ ! -e "$SANDBOX_TMP_RESUME/plan.txt" ] && [ ! -e "$SANDBOX_TMP_RESUME/feature-description.txt" ]; then
    PASS=$((PASS + 1))
    echo "PASS: B7-plan-dirty-tree resume tail no artifacts written to fresh tmpdir"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B7-plan-dirty-tree resume tail should not write artifacts to fresh tmpdir"
fi
rm -rf "$SANDBOX" "$SANDBOX_TMP" "$SANDBOX_TMP_RESUME"

# --- B7-resume-tail-plugin-root-env ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess-plugin.XXXXXX)
build_sandbox
write_gp1_session_setup
plugin_root_value="$SANDBOX"
mkdir -p "$SANDBOX_TMP"
printf 'sessstub\n' >"$SANDBOX_TMP/session-id"
cat >"$SANDBOX_TMP/session-env.sh" <<EOF
REPO=owner/repo
REPO_UNAVAILABLE=false
FORKED_TARGET=false
LARCH_CLAUDE_PLUGIN_ROOT=$plugin_root_value
EOF
rm -f "$SANDBOX_TMP/plugin-root.env"
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase infra --resume-plan-tail 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-resume-tail-plugin-root-env first pass exit 0"
if [ -f "$SANDBOX_TMP/plugin-root.env" ]; then
    PASS=$((PASS + 1))
    echo "PASS: B7-resume-tail-plugin-root-env creates sibling"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B7-resume-tail-plugin-root-env creates sibling"
fi
if grep -Fxq "CLAUDE_PLUGIN_ROOT=$plugin_root_value" "$SANDBOX_TMP/plugin-root.env" 2>/dev/null; then
    PASS=$((PASS + 1))
    echo "PASS: B7-resume-tail-plugin-root-env correct value"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B7-resume-tail-plugin-root-env correct value"
fi
if ( unset CLAUDE_PLUGIN_ROOT
     # shellcheck disable=SC1090,SC1091
     . "$SANDBOX_TMP/plugin-root.env"
     [ "$CLAUDE_PLUGIN_ROOT" = "$plugin_root_value" ] ); then
    PASS=$((PASS + 1))
    echo "PASS: B7-resume-tail-plugin-root-env sources cleanly"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B7-resume-tail-plugin-root-env sources cleanly"
fi
plugin_root_snapshot=$(cat "$SANDBOX_TMP/plugin-root.env")
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase infra --resume-plan-tail 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-resume-tail-plugin-root-env repeat exit 0"
if [ "$(cat "$SANDBOX_TMP/plugin-root.env")" = "$plugin_root_snapshot" ]; then
    PASS=$((PASS + 1))
    echo "PASS: B7-resume-tail-plugin-root-env idempotent on repeat"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B7-resume-tail-plugin-root-env idempotent on repeat"
fi
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B7-plan-dirty-tree stale emergency log not replayed on non-emergency resume ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sessA.XXXXXX)
SANDBOX_TMP_RESUME=$(mktemp -d /tmp/larch-ib-sessB.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
count_file="$SANDBOX/session-setup-count.txt"
count=0
if [ -f "\$count_file" ]; then
  count=\$(cat "\$count_file")
fi
count=\$((count + 1))
printf '%s\n' "\$count" >"\$count_file"
if [ "\$count" -eq 1 ]; then
  tmpdir="$SANDBOX_TMP"
else
  tmpdir="$SANDBOX_TMP_RESUME"
fi
echo SESSION_TMPDIR=\$tmpdir
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
printf 'BYPASS kind=missing-plan issue=123\n' >"$SANDBOX/preflight/emergency-bypass.log"
out=$(SANDBOX_DIRTY_STATUS=dirty run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDirtyEmergencyFalse --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-plan-dirty-tree stale-emergency first pass exit 0"
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDirtyEmergencyFalse --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-plan-dirty-tree stale-emergency resume exit 0"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
if [ "$(printf '%s\n' "$issues" | grep -cF 'BYPASS kind=missing-plan issue=123' || true)" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: B7-plan-dirty-tree stale-emergency resume does not replay bypass log"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B7-plan-dirty-tree stale-emergency resume does not replay bypass log"
    printf '%s\n' "$issues" | sed 's/^/    /'
fi
rm -rf "$SANDBOX" "$SANDBOX_TMP" "$SANDBOX_TMP_RESUME"

# --- B4-plan-dirty-resume deferred without sentinel ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sessA.XXXXXX)
SANDBOX_TMP_RESUME=$(mktemp -d /tmp/larch-ib-sessB.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
count_file="$SANDBOX/session-setup-count.txt"
count=0
if [ -f "\$count_file" ]; then
  count=\$(cat "\$count_file")
fi
count=\$((count + 1))
printf '%s\n' "\$count" >"\$count_file"
if [ "\$count" -eq 1 ]; then
  tmpdir="$SANDBOX_TMP"
else
  tmpdir="$SANDBOX_TMP_RESUME"
fi
echo SESSION_TMPDIR=\$tmpdir
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
out=$(LARCH_TEST_POSTED=false SANDBOX_DIRTY_STATUS=dirty run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDeferredResume --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B4-plan-dirty-resume first pass exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=dirty-tree" "$out" "B4-plan-dirty-resume first pass bail"
assert_contains "DEFERRED=true" "$out" "B4-plan-dirty-resume first pass deferred"
if [ ! -e "$SANDBOX_TMP/parent-issue.md" ]; then
    PASS=$((PASS + 1))
    echo "PASS: B4-plan-dirty-resume first pass no sentinel"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B4-plan-dirty-resume first pass should not write sentinel"
fi
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDeferredResume --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B4-plan-dirty-resume resume exit 0"
assert_line "IMPLEMENT_BAIL_REASON=" "$out" "B4-plan-dirty-resume resume clears bail"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "B4-plan-dirty-resume resume branch"
assert_contains "PLAN_FILE=$SANDBOX_TMP/plan.txt" "$out" "B4-plan-dirty-resume resume keeps tmpdir"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
if [ "$(printf '%s\n' "$invoke" | grep -cF "snapshot-untracked --output $SANDBOX_TMP/untracked-baseline.z --nul" || true)" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: B4-plan-dirty-resume no second snapshot"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B4-plan-dirty-resume no second snapshot"
    printf '%s\n' "$invoke" | sed 's/^/    /'
fi
if [ "$(printf '%s\n' "$invoke" | grep -cF 'gh issue view 123' || true)" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: B4-plan-dirty-resume no second gh"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B4-plan-dirty-resume no second gh"
    printf '%s\n' "$invoke" | sed 's/^/    /'
fi
if [ "$(printf '%s\n' "$invoke" | grep -cF "persist-implement-run-flags --implement-tmpdir $SANDBOX_TMP --no-issues false --emergency-requested false" || true)" -eq 3 ]; then
    PASS=$((PASS + 1))
    echo "PASS: B4-plan-dirty-resume reruns persist on resume"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B4-plan-dirty-resume reruns persist on resume"
    printf '%s\n' "$invoke" | sed 's/^/    /'
fi
rm -rf "$SANDBOX" "$SANDBOX_TMP" "$SANDBOX_TMP_RESUME"

# --- B7-plan-dirty-tree emergency resume does not replay bypass log ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sessA.XXXXXX)
SANDBOX_TMP_RESUME=$(mktemp -d /tmp/larch-ib-sessB.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
count_file="$SANDBOX/session-setup-count.txt"
count=0
if [ -f "\$count_file" ]; then
  count=\$(cat "\$count_file")
fi
count=\$((count + 1))
printf '%s\n' "\$count" >"\$count_file"
if [ "\$count" -eq 1 ]; then
  tmpdir="$SANDBOX_TMP"
else
  tmpdir="$SANDBOX_TMP_RESUME"
fi
echo SESSION_TMPDIR=\$tmpdir
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
printf 'BYPASS kind=missing-plan issue=123\n' >"$SANDBOX/preflight/emergency-bypass.log"
out=$(SANDBOX_DIRTY_STATUS=dirty run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDirtyEmergency --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-plan-dirty-tree emergency first pass exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=dirty-tree" "$out" "B7-plan-dirty-tree emergency first pass bail"
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDirtyEmergency --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-plan-dirty-tree emergency resume exit 0"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
if [ "$(printf '%s\n' "$issues" | grep -cF 'BYPASS kind=missing-plan issue=123' || true)" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: B7-plan-dirty-tree emergency resume does not replay bypass log"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B7-plan-dirty-tree emergency resume does not replay bypass log"
    printf '%s\n' "$issues" | sed 's/^/    /'
fi
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
if [ "$(printf '%s\n' "$invoke" | grep -cF "persist-implement-run-flags --implement-tmpdir $SANDBOX_TMP --no-issues false --emergency-requested true" || true)" -eq 3 ]; then
    PASS=$((PASS + 1))
    echo "PASS: B7-plan-dirty-tree emergency resume reruns persist"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B7-plan-dirty-tree emergency resume reruns persist"
    printf '%s\n' "$invoke" | sed 's/^/    /'
fi
rm -rf "$SANDBOX" "$SANDBOX_TMP" "$SANDBOX_TMP_RESUME"

# --- B7-plan-dirty-tree resume infers emergency from run-flags ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sessA.XXXXXX)
SANDBOX_TMP_RESUME=$(mktemp -d /tmp/larch-ib-sessB.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
count_file="$SANDBOX/session-setup-count.txt"
count=0
if [ -f "\$count_file" ]; then
  count=\$(cat "\$count_file")
fi
count=\$((count + 1))
printf '%s\n' "\$count" >"\$count_file"
if [ "\$count" -eq 1 ]; then
  tmpdir="$SANDBOX_TMP"
else
  tmpdir="$SANDBOX_TMP_RESUME"
fi
echo SESSION_TMPDIR=\$tmpdir
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
printf 'BYPASS kind=missing-plan issue=123\n' >"$SANDBOX/preflight/emergency-bypass.log"
out=$(SANDBOX_DIRTY_STATUS=dirty run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDirtyEmergencyResume --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-plan-dirty-tree inferred-emergency first pass exit 0"
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDirtyEmergencyResume --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-plan-dirty-tree inferred-emergency resume exit 0"
assert_contains "EMERGENCY_REQUESTED=true" "$out" "B7-plan-dirty-tree inferred-emergency resume stdout KV"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "persist-implement-run-flags --implement-tmpdir $SANDBOX_TMP --no-issues false --emergency-requested true" "$invoke" "B7-plan-dirty-tree inferred-emergency resume persists true"
assert_contains "post-tracking-issue --emergency-requested true" "$invoke" "B7-plan-dirty-tree inferred-emergency resume refreshes metadata"
rm -rf "$SANDBOX" "$SANDBOX_TMP" "$SANDBOX_TMP_RESUME"

# --- B7-plan-resume metadata post failure is surfaced ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(SANDBOX_DIRTY_STATUS=dirty run_bootstrap --up-to-phase plan --issue-number 123 --run-id resume1 --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-plan-resume-post-fail setup exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=dirty-tree" "$out" "B7-plan-resume-post-fail setup bail"
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" LARCH_TEST_POSTED=false run_bootstrap --up-to-phase plan --issue-number 123 --run-id resume1 --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail --emergency-requested true 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-plan-resume-post-fail exit 0"
assert_contains "DEFERRED=true" "$out" "B7-plan-resume-post-fail deferred"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_contains "Step 0 tracking adoption — Branch 1 resume metadata post" "$issues" "B7-plan-resume-post-fail execution issue site"
assert_contains "ERROR=post failed" "$issues" "B7-plan-resume-post-fail execution issue body"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B7-plan-dirty-tree resume tail re-bails when still dirty ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sessA.XXXXXX)
SANDBOX_TMP_RESUME=$(mktemp -d /tmp/larch-ib-sessB.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
count_file="$SANDBOX/session-setup-count.txt"
count=0
if [ -f "\$count_file" ]; then
  count=\$(cat "\$count_file")
fi
count=\$((count + 1))
printf '%s\n' "\$count" >"\$count_file"
if [ "\$count" -eq 1 ]; then
  tmpdir="$SANDBOX_TMP"
else
  tmpdir="$SANDBOX_TMP_RESUME"
fi
echo SESSION_TMPDIR=\$tmpdir
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
out=$(SANDBOX_DIRTY_STATUS=dirty run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDirtyResumeRetry --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-plan-dirty-tree resume re-bail first pass exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=dirty-tree" "$out" "B7-plan-dirty-tree resume re-bail first pass bail"
out=$(SANDBOX_DIRTY_STATUS=unknown IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDirtyResumeRetry --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-plan-dirty-tree resume re-bail exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=dirty-tree" "$out" "B7-plan-dirty-tree resume re-bail keeps bail"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
if [ "$(printf '%s\n' "$invoke" | grep -cF 'check-mid-run-dirty-tree --mode checkpoint' || true)" -eq 2 ]; then
    PASS=$((PASS + 1))
    echo "PASS: B7-plan-dirty-tree resume re-bail reruns dirty checkpoint"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B7-plan-dirty-tree resume re-bail reruns dirty checkpoint"
    printf '%s\n' "$invoke" | sed 's/^/    /'
fi
assert_not_contains "create-branch --branch" "$invoke" "B7-plan-dirty-tree resume re-bail no branch"
assert_not_contains "git-current-branch" "$invoke" "B7-plan-dirty-tree resume re-bail no branch capture"
assert_not_contains "run-step1-plan-log" "$invoke" "B7-plan-dirty-tree resume re-bail no plan log"
rm -rf "$SANDBOX" "$SANDBOX_TMP" "$SANDBOX_TMP_RESUME"

# --- B7-coder-dirty-tree resume tail reaches coder phase ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sessA.XXXXXX)
SANDBOX_TMP_RESUME=$(mktemp -d /tmp/larch-ib-sessB.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<STUB
#!/usr/bin/env bash
count_file="$SANDBOX/session-setup-count.txt"
count=0
if [ -f "\$count_file" ]; then
  count=\$(cat "\$count_file")
fi
count=\$((count + 1))
printf '%s\n' "\$count" >"\$count_file"
if [ "\$count" -eq 1 ]; then
  tmpdir="$SANDBOX_TMP"
else
  tmpdir="$SANDBOX_TMP_RESUME"
fi
echo SESSION_TMPDIR=\$tmpdir
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
write_preflight_plan
out=$(SANDBOX_DIRTY_STATUS=dirty run_bootstrap --up-to-phase coder --issue-number 123 --run-id runDirtyResumeCoder --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-coder-dirty-tree resume first pass exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=dirty-tree" "$out" "B7-coder-dirty-tree resume first pass bail"
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase coder --issue-number 123 --run-id runDirtyResumeCoder --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B7-coder-dirty-tree resume tail exit 0"
assert_line "IMPLEMENT_BAIL_REASON=" "$out" "B7-coder-dirty-tree resume tail clears bail"
assert_line "coder=codex" "$out" "B7-coder-dirty-tree resume tail reaches coder"
assert_contains "PLAN_FILE=$SANDBOX_TMP/plan.txt" "$out" "B7-coder-dirty-tree resume tail keeps original tmpdir"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
if [ "$(printf '%s\n' "$invoke" | grep -cF 'check-mid-run-dirty-tree --mode checkpoint' || true)" -eq 2 ]; then
    PASS=$((PASS + 1))
    echo "PASS: B7-coder-dirty-tree resume tail reruns dirty checkpoint"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B7-coder-dirty-tree resume tail reruns dirty checkpoint"
    printf '%s\n' "$invoke" | sed 's/^/    /'
fi
rm -rf "$SANDBOX" "$SANDBOX_TMP" "$SANDBOX_TMP_RESUME"

# --- B7-plan-dirty-tree resume tail missing tmpdir ---
build_sandbox
write_preflight_plan
out=$( (unset IMPLEMENT_TMPDIR; run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDirtyResume --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail) 2>&1 ) && rc=$? || rc=$?
assert_rc "$rc" 2 "B7-plan-dirty-tree resume tail missing tmpdir exit 2"
assert_contains "--resume-plan-tail requires IMPLEMENT_TMPDIR in the environment" "$out" "B7-plan-dirty-tree resume tail missing tmpdir usage"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "snapshot-untracked" "$invoke" "B7-plan-dirty-tree resume tail missing tmpdir no snapshot"
assert_not_contains "create-branch --branch" "$invoke" "B7-plan-dirty-tree resume tail missing tmpdir no branch"
rm -rf "$SANDBOX"

# --- B7-plan-dirty-tree resume tail missing session-env ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
rm -f "$SANDBOX_TMP/session-env.sh"
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase plan --issue-number 123 --run-id runDirtyResume --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail 2>&1) && rc=$? || rc=$?
assert_rc "$rc" 2 "B7-plan-dirty-tree resume tail missing session-env exit 2"
assert_contains "--resume-plan-tail requires \$IMPLEMENT_TMPDIR/session-env.sh" "$out" "B7-plan-dirty-tree resume tail missing session-env usage"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "create-branch --branch" "$invoke" "B7-plan-dirty-tree resume tail missing session-env no branch"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B8-plan-forked-target ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(run_bootstrap --up-to-phase plan --forked-target true --upstream-repo upstream/repo --issue-number 123 --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B8-plan-forked-target exit 0"
assert_contains "BRANCH_SELECTED=forked-target-skip" "$out" "B8-plan-forked-target branch selected"
assert_contains "DEFERRED=true" "$out" "B8-plan-forked-target deferred"
assert_contains "RUN_ID=sessstub" "$out" "B8-plan-forked-target run id derived"
assert_contains "PLAN_FILE=$SANDBOX_TMP/plan.txt" "$out" "B8-plan-forked-target plan file"
assert_contains "BRANCH_NAME=main" "$out" "B8-plan-forked-target branch name"
assert_line "BRANCH_ACTION=" "$out" "B8-plan-forked-target empty action"
if [ -f "$SANDBOX_TMP/plan.txt" ] && grep -qxF "Plan from issue" "$SANDBOX_TMP/plan.txt"; then
    PASS=$((PASS + 1))
    echo "PASS: B8-plan-forked-target plan.txt materialized"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B8-plan-forked-target plan.txt materialized"
fi
if [ -f "$SANDBOX_TMP/feature-description.txt" ] && grep -qxF "Test Feature" "$SANDBOX_TMP/feature-description.txt"; then
    PASS=$((PASS + 1))
    echo "PASS: B8-plan-forked-target feature-description.txt materialized"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B8-plan-forked-target feature-description.txt materialized"
fi
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains "gh issue view 123 --repo upstream/repo" "$invoke" "B8-plan-forked-target gh upstream"
assert_contains "voting write-tally --log-root $SANDBOX_TMP/larch-logs --skill implement --run-id sessstub" "$invoke" "B8-plan-forked-target tally run id"
assert_not_contains "create-branch --branch" "$invoke" "B8-plan-forked-target no branch create"
assert_not_contains "tracking-issue-summary upsert-summary" "$invoke" "B8-plan-forked-target no plan summary"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B8-plan-forked-missing-upstream ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(run_bootstrap --up-to-phase plan --forked-target true --issue-number 123 --preflight-tmpdir "$SANDBOX/preflight" 2>&1) && rc=$? || rc=$?
assert_rc "$rc" 2 "B8-plan-forked-missing-upstream exit 2"
assert_contains "STEP_FAILED=gh-issue-view" "$out" "B8-plan-forked-missing-upstream step failed"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "persist-implement-run-flags" "$invoke" "B8-plan-forked-missing-upstream no persist"
assert_not_contains "create-branch --branch" "$invoke" "B8-plan-forked-missing-upstream no branch"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B9-plan-user-branch ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(SANDBOX_IS_USER_BRANCH=true run_bootstrap --up-to-phase plan --issue-number 123 --run-id runUser --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B9-plan-user-branch exit 0"
assert_contains "BRANCH_NAME=testuser/existing" "$out" "B9-plan-user-branch branch name"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "create-branch --branch" "$invoke" "B9-plan-user-branch no branch create"
assert_contains "tracking-issue-summary upsert-summary" "$invoke" "B9-plan-user-branch summary invoked"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B10-plan-missing-preflight-tmpdir ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
set +e
out=$(run_bootstrap --up-to-phase plan --issue-number 123 2>&1)
rc=$?
set -e
assert_rc "$rc" 2 "B10-plan-missing-preflight-tmpdir exit 2"
assert_contains "--preflight-tmpdir is required" "$out" "B10-plan-missing-preflight-tmpdir usage"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B11-plan-copy-plan-failure ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
mkdir -p "$SANDBOX/preflight"
printf 'BYPASS kind=missing-plan issue=123\n' >"$SANDBOX/preflight/emergency-bypass.log"
set +e
out=$(run_bootstrap --up-to-phase plan --issue-number 123 --run-id runCopy --preflight-tmpdir "$SANDBOX/preflight" --emergency-requested true 2>/dev/null)
rc=$?
set -e
assert_rc "$rc" 2 "B11-plan-copy-plan-failure exit 2"
assert_contains "STEP_FAILED=copy-plan" "$out" "B11-plan-copy-plan-failure STEP_FAILED"
assert_contains "IMPLEMENT_TMPDIR=$SANDBOX_TMP" "$out" "B11-plan-copy-plan-failure tmpdir emitted"
issues=$(cat "$SANDBOX_TMP/execution-issues.md" 2>/dev/null || true)
assert_contains "BYPASS kind=missing-plan issue=123" "$issues" "B11-plan-copy-plan-failure preserves emergency bypass audit"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B12-plan-gh-issue-view-failure ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
set +e
out=$(SANDBOX_GH_EXIT=1 run_bootstrap --up-to-phase plan --issue-number 123 --run-id runGh --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null)
rc=$?
set -e
assert_rc "$rc" 2 "B12-plan-gh-issue-view-failure exit 2"
assert_contains "STEP_FAILED=gh-issue-view" "$out" "B12-plan-gh-issue-view-failure STEP_FAILED"
assert_contains "IMPLEMENT_TMPDIR=$SANDBOX_TMP" "$out" "B12-plan-gh-issue-view-failure tmpdir emitted"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B13-plan-branch-create ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(SANDBOX_CREATE_BRANCH_EXIT=9 run_bootstrap --up-to-phase plan --issue-number 123 --run-id runBranchFail --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B13-plan-branch-create exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=branch-create-failed" "$out" "B13-plan-branch-create bail"
assert_contains "STALL_TRACKING=true" "$out" "B13-plan-branch-create stall"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "git-current-branch" "$invoke" "B13-plan-branch-create no branch capture"
assert_not_contains "run-step1-plan-log" "$invoke" "B13-plan-branch-create no plan log"
assert_not_contains "voting write-tally" "$invoke" "B13-plan-branch-create no tally"
assert_not_contains "tracking-issue-summary upsert-summary" "$invoke" "B13-plan-branch-create no plan summary"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B14-plan-branch-capture ---
for branch_capture_mode in exit empty; do
    SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
    build_sandbox
    write_gp1_session_setup
    write_preflight_plan
    if [ "$branch_capture_mode" = "exit" ]; then
        out=$(SANDBOX_BRANCH_CAPTURE_EXIT=8 run_bootstrap --up-to-phase plan --issue-number 123 --run-id runBranchCapture --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
    else
        out=$(SANDBOX_BRANCH_CAPTURE_EMPTY=true run_bootstrap --up-to-phase plan --issue-number 123 --run-id runBranchCapture --preflight-tmpdir "$SANDBOX/preflight" 2>/dev/null) && rc=$? || rc=$?
    fi
    assert_rc "$rc" 0 "B14-plan-branch-capture $branch_capture_mode exit 0"
    assert_contains "IMPLEMENT_BAIL_REASON=branch-create-failed" "$out" "B14-plan-branch-capture $branch_capture_mode bail"
    assert_contains "STALL_TRACKING=true" "$out" "B14-plan-branch-capture $branch_capture_mode stall"
    invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
    assert_contains "git-current-branch" "$invoke" "B14-plan-branch-capture $branch_capture_mode branch capture attempted"
    assert_not_contains "run-step1-plan-log" "$invoke" "B14-plan-branch-capture $branch_capture_mode no plan log"
    assert_not_contains "voting write-tally" "$invoke" "B14-plan-branch-capture $branch_capture_mode no tally"
    rm -rf "$SANDBOX" "$SANDBOX_TMP"
done

# --- B15-resume-plan-tail-sentinel-mismatch ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(run_bootstrap --up-to-phase infra 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B15-resume-plan-tail-sentinel-mismatch setup infra exit 0"
printf 'ISSUE_NUMBER=999\nRUN_ID=resume-ok\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase plan --issue-number 123 --run-id runSentinelMismatch --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 2 "B15-resume-plan-tail-sentinel-mismatch exit 2"
assert_contains "STEP_FAILED=resume-plan-tail-sentinel" "$out" "B15-resume-plan-tail-sentinel-mismatch STEP_FAILED"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "check-mid-run-dirty-tree" "$invoke" "B15-resume-plan-tail-sentinel-mismatch no dirty checkpoint"
assert_not_contains "create-branch --branch" "$invoke" "B15-resume-plan-tail-sentinel-mismatch no branch"
assert_not_contains "run-step1-plan-log" "$invoke" "B15-resume-plan-tail-sentinel-mismatch no plan log"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B16-resume-plan-tail-sentinel-malformed ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(run_bootstrap --up-to-phase infra 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B16-resume-plan-tail-sentinel-malformed setup infra exit 0"
printf 'ISSUE_NUMBER=123\nRUN_ID=bad run\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase plan --issue-number 123 --run-id runSentinelMalformed --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 2 "B16-resume-plan-tail-sentinel-malformed exit 2"
assert_contains "STEP_FAILED=resume-plan-tail-sentinel" "$out" "B16-resume-plan-tail-sentinel-malformed STEP_FAILED"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "check-mid-run-dirty-tree" "$invoke" "B16-resume-plan-tail-sentinel-malformed no dirty checkpoint"
assert_not_contains "create-branch --branch" "$invoke" "B16-resume-plan-tail-sentinel-malformed no branch"
assert_not_contains "run-step1-plan-log" "$invoke" "B16-resume-plan-tail-sentinel-malformed no plan log"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B17-resume-plan-tail-sentinel-missing ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(run_bootstrap --up-to-phase infra 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B17-resume-plan-tail-sentinel-missing setup infra exit 0"
rm -f "$SANDBOX_TMP/plan.txt" "$SANDBOX_TMP/feature-description.txt" "$SANDBOX_TMP/parent-issue.md"
out=$(IMPLEMENT_TMPDIR="$SANDBOX_TMP" run_bootstrap --up-to-phase plan --issue-number 123 --run-id runSentinelMissing --preflight-tmpdir "$SANDBOX/preflight" --resume-plan-tail 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 2 "B17-resume-plan-tail-sentinel-missing exit 2"
assert_contains "STEP_FAILED=resume-plan-tail-sentinel" "$out" "B17-resume-plan-tail-sentinel-missing STEP_FAILED"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "check-mid-run-dirty-tree" "$invoke" "B17-resume-plan-tail-sentinel-missing no dirty checkpoint"
assert_not_contains "create-branch --branch" "$invoke" "B17-resume-plan-tail-sentinel-missing no branch"
assert_not_contains "run-step1-plan-log" "$invoke" "B17-resume-plan-tail-sentinel-missing no plan log"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B6 get-issue-state FAILED=true ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
set +e
out=$(LARCH_TEST_GET_ISSUE_FAILED=true run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null)
rc=$?
set -e
assert_rc "$rc" 2 "B6 exit 2"
assert_contains "STEP_FAILED=get-issue-state" "$out" "B6 STEP_FAILED"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B7 unexpected issue state ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
set +e
out=$(LARCH_TEST_ISSUE_STATE=MERGED run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null)
rc=$?
set -e
assert_rc "$rc" 2 "B7-non-open-state exit 2"
assert_contains "STEP_FAILED=get-issue-state" "$out" "B7-non-open-state STEP_FAILED"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B-sentinel-malformed ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=bad1\nADOPTED=yes\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runF 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B-sentinel-malformed exit 0"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "B-sentinel-malformed fall-through branch"
assert_contains "RUN_ID=runF" "$out" "B-sentinel-malformed fresh run id"
assert_contains "RUN_ID=runF" "$(cat "$SANDBOX_TMP/parent-issue.md")" "B-sentinel-malformed sentinel replaced"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B-sentinel-invalid-run-id ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=bad run\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runG 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B-sentinel-invalid-run-id exit 0"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "B-sentinel-invalid-run-id fall-through branch"
assert_contains "RUN_ID=runG" "$out" "B-sentinel-invalid-run-id fresh run id"
assert_contains "RUN_ID=runG" "$(cat "$SANDBOX_TMP/parent-issue.md")" "B-sentinel-invalid-run-id sentinel replaced"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B-empty-run-id-derivation ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
cat >"$SANDBOX/python/stubs/session/write-id" <<'STUB'
#!/usr/bin/env bash
while [ $# -gt 0 ]; do
  case "$1" in
    --output) mkdir -p "$(dirname "$2")"; : > "$2"; shift 2 ;;
    *) shift ;;
  esac
done
exit 0
STUB
chmod +x "$SANDBOX/python/stubs/session/write-id"
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B-empty-run-id-derivation exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=tracking-init-failed" "$out" "B-empty-run-id-derivation bail reason"
assert_contains "STALL_TRACKING=true" "$out" "B-empty-run-id-derivation stall"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP-adopt-rename-fail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(LARCH_TEST_RENAME_FAILED=true run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runRename 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP-adopt-rename-fail exit 0"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "GP-adopt-rename-fail branch"
assert_contains "Step 0 tracking adoption — Branch 2 adopt rename to implementing" "$(cat "$SANDBOX_TMP/execution-issues.md")" "GP-adopt-rename-fail execution issues"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP2-rename-fail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=resume-rename\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(LARCH_TEST_RENAME_FAILED=true run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP2-rename-fail exit 0"
assert_contains "BRANCH_SELECTED=branch-1-resume" "$out" "GP2-rename-fail branch"
assert_contains "Step 0 tracking adoption — Branch 1 resume rename to implementing" "$(cat "$SANDBOX_TMP/execution-issues.md")" "GP2-rename-fail execution issues"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B-preflight ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/python/stubs/session/setup" <<'STUB'
#!/usr/bin/env bash
echo PREFLIGHT_ERROR=Not on main branch
exit 1
STUB
chmod +x "$SANDBOX/python/stubs/session/setup"
set +e
out=$(run_bootstrap --up-to-phase infra 2>/dev/null)
rc=$?
set -e
assert_rc "$rc" 2 "B-preflight exit 2"
assert_contains "PREFLIGHT_ERROR=Not on main branch" "$out" "B-preflight PREFLIGHT_ERROR"
assert_contains "STEP_FAILED=session-setup" "$out" "B-preflight STEP_FAILED"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "write-session-id" "$invoke" "B-preflight no write-session-id"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B-gate ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
cat >"$SANDBOX/python/stubs/session/entry-gate" <<'STUB'
#!/usr/bin/env bash
echo "GATE_ERROR=internal contract violation" >&2
exit 1
STUB
chmod +x "$SANDBOX/python/stubs/session/entry-gate"
set +e
out=$(run_bootstrap --up-to-phase infra 2>/dev/null)
rc=$?
set -e
assert_rc "$rc" 2 "B-gate exit 2"
assert_contains "GATE_ERROR=internal contract violation" "$out" "B-gate GATE_ERROR forwarded"
assert_contains "STEP_FAILED=session-entry-gate" "$out" "B-gate STEP_FAILED"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "write-session-id" "$invoke" "B-gate no write-session-id"
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- B-issue-required-for-resume ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=resume-guard\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
set +e
out=$(run_bootstrap --up-to-phase tracking 2>/dev/null)
rc=$?
set -e
assert_rc "$rc" 2 "B-issue-required-for-resume exit 2"
assert_contains "STEP_FAILED=issue-number-required-for-resume" "$out" "B-issue-required-for-resume STEP_FAILED"
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- B-fork-missing-issue ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
set +e
out=$(run_bootstrap --up-to-phase tracking --forked-target true --upstream-repo upstream/repo 2>&1)
rc=$?
set -e
assert_rc "$rc" 2 "B-fork-missing-issue exit 2"
assert_contains "--issue-number is required with --upstream-repo" "$out" "B-fork-missing-issue usage"
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- B-invalid-run-id-arg ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
set +e
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --run-id 'bad run' 2>&1)
rc=$?
set -e
assert_rc "$rc" 2 "B-invalid-run-id-arg exit 2"
assert_contains "--run-id must match ^[A-Za-z0-9._-]+$" "$out" "B-invalid-run-id-arg usage"
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- B-invalid-emergency-requested-arg ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
set +e
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --emergency-requested maybe 2>&1)
rc=$?
set -e
assert_rc "$rc" 2 "B-invalid-emergency-requested-arg exit 2"
assert_contains "--emergency-requested must be true or false" "$out" "B-invalid-emergency-requested-arg usage"
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- B-invalid-upstream-repo-arg ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
set +e
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --forked-target true --upstream-repo bad/repo/extra 2>&1)
rc=$?
set -e
assert_rc "$rc" 2 "B-invalid-upstream-repo-arg exit 2"
assert_contains "--upstream-repo must be OWNER/REPO" "$out" "B-invalid-upstream-repo-arg usage"
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- Edge-NEVER14 ---
# Patterns are literal (grep -F); $ in the pattern is not shell expansion.
# shellcheck disable=SC2016
if grep -Fq '>> "$IMPLEMENT_TMPDIR/session-env.sh"' "$REAL_SCRIPT"; then
    FAIL=$((FAIL + 1))
    echo "FAIL: Edge-NEVER14 found append redirect to session-env.sh"
else
    pat='cat > "$IMPLEMENT_TMPDIR/session-env.sh" <<'
    if grep -Fq "$pat" "$REAL_SCRIPT"; then
        FAIL=$((FAIL + 1))
        echo "FAIL: Edge-NEVER14 found cat heredoc redirect to session-env.sh"
    else
        PASS=$((PASS + 1))
        echo "PASS: Edge-NEVER14 no forbidden direct session-env write patterns"
    fi
fi

# --- Edge-breadcrumb-count ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
bc=$(mktemp "${TMPDIR:-/tmp}/larch-ib-bc.XXXXXX")
out=$(run_bootstrap --up-to-phase infra 2>&1) && rc=$? || rc=$?
n=$(printf '%s\n' "$out" | grep -cF '→ step0: infra ready' || true)
rm -f "$bc"
assert_rc "$rc" 0 "Edge-breadcrumb-count exit 0"
if [ "$n" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: Edge-breadcrumb-count exactly one breadcrumb"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: Edge-breadcrumb-count expected 1 got $n"
fi
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- Edge-breadcrumb-count-adopt ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runBreadcrumb 2>&1) && rc=$? || rc=$?
n=$(printf '%s\n' "$out" | grep -cF '→ step0: tracking adopted' || true)
assert_rc "$rc" 0 "Edge-breadcrumb-count-adopt exit 0"
if [ "$n" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: Edge-breadcrumb-count-adopt exactly one breadcrumb"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: Edge-breadcrumb-count-adopt expected 1 got $n"
fi
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- Edge-breadcrumb-count-plan-green ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(run_bootstrap --up-to-phase plan --issue-number 123 --run-id runBreadcrumbPlan --preflight-tmpdir "$SANDBOX/preflight" 2>&1) && rc=$? || rc=$?
assert_rc "$rc" 0 "Edge-breadcrumb-count-plan-green exit 0"
n=$(printf '%s\n' "$out" | grep -cF '→ step0: branch ' || true)
if [ "$n" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: Edge-breadcrumb-count-plan-green branch breadcrumb once"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: Edge-breadcrumb-count-plan-green branch breadcrumb expected 1 got $n"
fi
n=$(printf '%s\n' "$out" | grep -cF '→ step0: larch:plan posted' || true)
if [ "$n" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: Edge-breadcrumb-count-plan-green larch plan breadcrumb once"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: Edge-breadcrumb-count-plan-green larch plan breadcrumb expected 1 got $n"
fi
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- Edge-breadcrumb-count-plan-summary-fail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(SANDBOX_PLAN_SUMMARY_EXIT=5 run_bootstrap --up-to-phase plan --issue-number 123 --run-id runBreadcrumbPlanFail --preflight-tmpdir "$SANDBOX/preflight" 2>&1) && rc=$? || rc=$?
assert_rc "$rc" 0 "Edge-breadcrumb-count-plan-summary-fail exit 0"
n=$(printf '%s\n' "$out" | grep -cF '→ step0: branch ' || true)
if [ "$n" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: Edge-breadcrumb-count-plan-summary-fail branch breadcrumb once"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: Edge-breadcrumb-count-plan-summary-fail branch breadcrumb expected 1 got $n"
fi
n=$(printf '%s\n' "$out" | grep -cF '→ step0: larch:plan posted' || true)
if [ "$n" -eq 0 ]; then
    PASS=$((PASS + 1))
    echo "PASS: Edge-breadcrumb-count-plan-summary-fail no larch plan breadcrumb"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: Edge-breadcrumb-count-plan-summary-fail expected 0 larch plan breadcrumbs got $n"
fi
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- Edge-breadcrumb-count-plan-log-fail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(SANDBOX_RUN_PLAN_LOG_EXIT=5 run_bootstrap --up-to-phase plan --issue-number 123 --run-id runBreadcrumbPlanLogFail --preflight-tmpdir "$SANDBOX/preflight" 2>&1) && rc=$? || rc=$?
assert_rc "$rc" 0 "Edge-breadcrumb-count-plan-log-fail exit 0"
n=$(printf '%s\n' "$out" | grep -cF '→ step0: branch testuser/test-feature-123 + plan logged' || true)
if [ "$n" -eq 0 ]; then
    PASS=$((PASS + 1))
    echo "PASS: Edge-breadcrumb-count-plan-log-fail no + plan logged variant"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: Edge-breadcrumb-count-plan-log-fail expected 0 + plan logged variants got $n"
fi
n=$(printf '%s\n' "$out" | grep -cF '→ step0: branch testuser/test-feature-123' || true)
if [ "$n" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: Edge-breadcrumb-count-plan-log-fail plain branch breadcrumb once"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: Edge-breadcrumb-count-plan-log-fail plain branch breadcrumb expected 1 got $n"
fi
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- Edge-breadcrumb-count-coder-green ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
write_preflight_plan
out=$(run_bootstrap --up-to-phase coder --issue-number 123 --run-id runBreadcrumbCoder --preflight-tmpdir "$SANDBOX/preflight" 2>&1) && rc=$? || rc=$?
assert_rc "$rc" 0 "Edge-breadcrumb-count-coder-green exit 0"
n=$(printf '%s\n' "$out" | grep -cF '→ step0:' || true)
if [ "$n" -eq 6 ]; then
    PASS=$((PASS + 1))
    echo "PASS: Edge-breadcrumb-count-coder-green exactly six step0 breadcrumbs"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: Edge-breadcrumb-count-coder-green expected 6 got $n"
    printf '%s\n' "$out" | sed 's/^/    /'
fi
n=$(printf '%s\n' "$out" | grep -cF '→ step0: coder=codex' || true)
if [ "$n" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: Edge-breadcrumb-count-coder-green coder breadcrumb once"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: Edge-breadcrumb-count-coder-green coder breadcrumb expected 1 got $n"
fi
rm -rf "$SANDBOX_TMP" "$SANDBOX"

echo "---"
echo "PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
exit 0
