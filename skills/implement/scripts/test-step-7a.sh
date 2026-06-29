#!/usr/bin/env bash
# test-step-7a.sh — offline harness for step-7a.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/step-7a.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"

PASS=0
FAIL=0
TMP_PARENT="${TMPDIR:-/tmp}"
TMP_PARENT="${TMP_PARENT%/}"
TMP_ROOT="$(mktemp -d "$TMP_PARENT/test-step-7a.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

pass() {
    PASS=$((PASS + 1))
    printf 'PASS: %s\n' "$1"
}

fail() {
    FAIL=$((FAIL + 1))
    printf 'FAIL: %s\n' "$1" >&2
}

assert_contains() {
    local needle=$1 haystack=$2 label=$3
    if grep -Fq -- "$needle" <<<"$haystack"; then
        pass "$label"
    else
        fail "$label (missing: $needle)"
    fi
}

assert_not_contains() {
    local needle=$1 haystack=$2 label=$3
    if grep -Fq -- "$needle" <<<"$haystack"; then
        fail "$label (unexpected: $needle)"
    else
        pass "$label"
    fi
}

assert_file_contains() {
    local needle=$1 path=$2 label=$3
    assert_contains "$needle" "$(cat "$path" 2>/dev/null || true)" "$label"
}

assert_file_not_contains() {
    local needle=$1 path=$2 label=$3
    assert_not_contains "$needle" "$(cat "$path" 2>/dev/null || true)" "$label"
}

assert_file_equals() {
    local expected=$1 path=$2 label=$3 actual
    actual=$(cat "$path" 2>/dev/null || true)
    if [ "$expected" = "$actual" ]; then
        pass "$label"
    else
        fail "$label"
    fi
}

assert_equals() {
    local expected=$1 actual=$2 label=$3
    if [ "$expected" = "$actual" ]; then
        pass "$label"
    else
        fail "$label (expected $expected got $actual)"
    fi
}

assert_call_order() {
    local file=$1 first=$2 second=$3 label=$4 first_line second_line
    first_line=$(grep -nF "$first" "$file" 2>/dev/null | head -n 1 | cut -d: -f1 || true)
    second_line=$(grep -nF "$second" "$file" 2>/dev/null | head -n 1 | cut -d: -f1 || true)
    if [ -n "$first_line" ] && [ -n "$second_line" ] && [ "$first_line" -lt "$second_line" ]; then
        pass "$label"
    else
        fail "$label"
    fi
}

green_expected_summary() {
    cat <<'EOF'
## Code Flow Diagram

```mermaid
graph TD
  A --> B
```
EOF
}

finish() {
    printf 'PASS=%s\n' "$PASS"
    printf 'FAIL=%s\n' "$FAIL"
    [ "$FAIL" -eq 0 ]
}

setup_plugin() {
    local root=$1
    mkdir -p "$root/scripts" "$root/skills/implement/scripts" "$root/python/stubs/session"
    cp "$REPO_ROOT"/python/*.py "$root/python/"
    cp -R "$REPO_ROOT/python/larch" "$root/python/"
    mv "$root/python/cli.py" "$root/python/real-cli.py"
    cat > "$root/python/cli.py" <<'DISPATCHER'
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def _diagrams_upsert_stub() -> int:
    code_file = ""
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--repo" and i + 1 < len(sys.argv):
            i += 2
            continue
        if sys.argv[i] == "--code-flow-file" and i + 1 < len(sys.argv):
            code_file = sys.argv[i + 1]
            i += 2
            continue
        i += 1
    calls_log = os.environ.get("STEP7A_CALLS_LOG", "")
    if calls_log:
        with open(calls_log, "a", encoding="utf-8") as handle:
            if code_file and Path(code_file).is_file():
                handle.write(f"upsert-diagrams-content {code_file}\n")
            handle.write(f"python/cli.py {' '.join(sys.argv[1:])}\n")
    if os.environ.get("STEP7A_UPSERT_FAIL", "0") == "1":
        print("upsert failed", file=sys.stderr)
        return 1
    body_capture = os.environ.get("STEP7A_UPSERT_BODY_CAPTURE", "")
    if body_capture:
        capture_path = Path(body_capture)
        capture_path.write_text("", encoding="utf-8")
        existing = os.environ.get("STEP7A_UPSERT_EXISTING_BODY_FILE", "")
        if existing and Path(existing).is_file():
            lines = Path(existing).read_text(encoding="utf-8").splitlines()
            if lines and lines[0] == "<!-- larch:diagrams v1 -->":
                keep = False
                arch_lines: list[str] = []
                for line in lines:
                    if line == "## Code Flow Diagram":
                        keep = False
                    elif line == "## Architecture Diagram":
                        keep = True
                        continue
                    elif keep:
                        arch_lines.append(line)
                if arch_lines:
                    with capture_path.open("a", encoding="utf-8") as handle:
                        for line in arch_lines:
                            handle.write(f"{line}\n")
        if capture_path.stat().st_size > 0 and code_file and Path(code_file).is_file():
            with capture_path.open("a", encoding="utf-8") as handle:
                handle.write("\n\n")
        if code_file and Path(code_file).is_file():
            with capture_path.open("a", encoding="utf-8") as handle:
                handle.write(Path(code_file).read_text(encoding="utf-8"))
    print("UPSERT_STATUS=ok")
    print("COMMENT_URL=https://example.test/comment/1")
    print("UPDATED=true")
    return 0

def _token_timing_stub() -> int:
    calls_log = os.environ.get("STEP7A_CALLS_LOG", "")
    if calls_log:
        with open(calls_log, "a", encoding="utf-8") as handle:
            handle.write(f"python3 python/cli.py {' '.join(sys.argv[1:])}\n")
    if len(sys.argv) >= 4 and sys.argv[2] == "report":
        idx = 3
        while idx < len(sys.argv):
            if sys.argv[idx] == "--output" and idx + 1 < len(sys.argv):
                Path(sys.argv[idx + 1]).write_text("{}\n", encoding="utf-8")
                break
            idx += 1
    return 0

def _runlog_stub() -> int:
    calls_log = os.environ.get("STEP7A_CALLS_LOG", "")
    verb = sys.argv[2] if len(sys.argv) >= 3 else ""
    rest = " ".join(sys.argv[3:])
    if verb == "capture-transcript":
        if calls_log:
            with open(calls_log, "a", encoding="utf-8") as handle:
                handle.write(f"run-log capture-transcript {rest}\n")
        print("SESSION_TRANSCRIPT_STATUS=ok")
        return 0
    if verb == "append-failure":
        args = sys.argv[3:]
        vals = {"--log": "", "--site": "", "--tool": "", "--exit-code": "", "--category": "", "--output-file": ""}
        i = 0
        while i < len(args):
            if args[i] in vals and i + 1 < len(args):
                vals[args[i]] = args[i + 1]; i += 2
            else:
                i += 1
        if vals["--log"]:
            body = ""
            out = Path(vals["--output-file"]) if vals["--output-file"] else None
            if out is not None and out.is_file():
                body = out.read_text(encoding="utf-8", errors="replace")
            with open(vals["--log"], "a", encoding="utf-8") as handle:
                handle.write(f"\n### {vals['--category']}\n\n")
                handle.write(f"- **Step {vals['--site']} — {vals['--tool']} failed (exit {vals['--exit-code']})**:\n")
                handle.write(body)
                handle.write("\n")
        return 0
    if calls_log:
        with open(calls_log, "a", encoding="utf-8") as handle:
            handle.write(f"run-log {verb} {rest}\n")
    print("LOG_STATUS=ok")
    return 0

def main() -> None:
    root = Path(__file__).resolve().parent
    if len(sys.argv) >= 2 and sys.argv[1] in {"token", "timing"}:
        raise SystemExit(_token_timing_stub())
    if len(sys.argv) >= 2 and sys.argv[1] == "run-log":
        raise SystemExit(_runlog_stub())
    if len(sys.argv) >= 3 and sys.argv[1] == "session":
        stub = root / "stubs" / "session" / sys.argv[2]
        if stub.is_file() and os.access(stub, os.X_OK):
            os.execv(str(stub), [str(stub), *sys.argv[3:]])
    if len(sys.argv) >= 3 and sys.argv[1] == "diagrams" and sys.argv[2] == "upsert":
        raise SystemExit(_diagrams_upsert_stub())
    if len(sys.argv) >= 3 and sys.argv[1] == "push" and sys.argv[2] == "checkpoint-probe":
        with open(os.environ["STEP7A_CALLS_LOG"], "a", encoding="utf-8") as handle:
            handle.write("python/cli.py push checkpoint-probe " + " ".join(sys.argv[3:]) + "\n")
        mode = os.environ.get("STEP7A_REBASE_MODE", "ok")
        if mode == "ok":
            print("REBASE_OUTCOME=ok")
            print("ROUTE=continue")
            print("CHECKPOINT_NEXT=continue")
            raise SystemExit(0)
        if mode == "conflict":
            print("REBASE_OUTCOME=conflict")
            print("CONFLICT_FILES=skills/implement/scripts/step-7a.sh")
            print("ROUTE=conflict")
            print("CHECKPOINT_NEXT=load-routing")
            raise SystemExit(1)
        if mode == "failed":
            print("REBASE_OUTCOME=failed")
            print("REBASE_ERROR=rebase-failed")
            print("ROUTE=bail")
            print("CHECKPOINT_NEXT=load-routing")
            raise SystemExit(3)
        if mode == "unexpected":
            print("REBASE_OUTCOME=failed")
            print("REBASE_ERROR=unexpected-rc-5")
            print("ROUTE=bail")
            print("CHECKPOINT_NEXT=load-routing")
            raise SystemExit(5)
    os.execv(sys.executable, [sys.executable, str(root / "real-cli.py"), *sys.argv[1:]])

if __name__ == "__main__":
    main()
DISPATCHER
    chmod +x "$root/python/cli.py"

    cat > "$root/skills/implement/scripts/generate-code-flow-diagram.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'generate-code-flow-diagram.sh %s\n' "$*" >> "$STEP7A_CALLS_LOG"
tmpdir=""
while [ $# -gt 0 ]; do
    case "$1" in
        --implement-tmpdir) tmpdir=$2; shift 2 ;;
        *) shift ;;
    esac
done
case "${STEP7A_GEN_MODE:-ok}" in
    ok)
        printf '## Code Flow Diagram\n\n```mermaid\ngraph TD\n  A --> B\n```\n' > "$tmpdir/code-flow-diagram.md"
        printf 'STATUS=ok\nDIAGRAM_FILE=%s\nSKIP_REASON=\n' "$tmpdir/code-flow-diagram.md"
        ;;
    rejected)
        token=${STEP7A_SANITIZER_TOKEN:-pipe-in-node-label}
        printf 'generator sanitizer rejected\n' >&2
        printf 'STATUS=skipped\nDIAGRAM_FILE=\nSKIP_REASON=%s fence=mermaid line=7\n' "$token"
        ;;
    failed)
        printf 'generator helper failed\n' >&2
        printf 'STATUS=failed\nDIAGRAM_FILE=\nSKIP_REASON=%s\n' "${STEP7A_GEN_FORCE_SKIP_REASON:-helper-error}"
        ;;
    crash)
        printf 'generator crashed\n' >&2
        exit 99
        ;;
esac
STUB

    cat > "$root/skills/implement/scripts/flush-execution-issues.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
count_file="${STEP7A_FLUSH_COUNT_FILE:?}"
count=0
[ -f "$count_file" ] && count=$(cat "$count_file")
count=$((count + 1))
printf '%s\n' "$count" > "$count_file"
printf 'flush-execution-issues.sh %s\n' "$*" >> "$STEP7A_CALLS_LOG"
if [ "${STEP7A_FLUSH_FAIL_FIRST:-0}" = "1" ] && [ "$count" -eq 1 ]; then
    printf 'flush failed\n' >&2
    exit 1
fi
printf 'FLUSH_STATUS=ok\nRECORDS=0\n'
STUB

    cat > "$root/python/stubs/session/read-key" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
file=""; key=""; default=""
while [ $# -gt 0 ]; do
    case "$1" in
        --file) file=$2; shift 2 ;;
        --key) key=$2; shift 2 ;;
        --default) default=$2; shift 2 ;;
        *) shift ;;
    esac
done
awk -F= -v key="$key" -v default="$default" '$1==key{print substr($0, index($0, "=") + 1); found=1; exit} END{if(!found) print default}' "$file" 2>/dev/null
STUB
    chmod +x "$root/python/stubs/session/read-key"

    cat > "$root/python/stubs/launch-claude-subprocess" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
output_file=""
while [ $# -gt 0 ]; do
    case "$1" in
        --output-file) output_file=$2; shift 2 ;;
        *) shift ;;
    esac
done
printf 'python/cli.py agent launch-claude-subprocess --output-file %s\n' "$output_file" >> "$STEP7A_CALLS_LOG"
case "${STEP7A_GEN_MODE:-ok}" in
    ok)
        printf '## Code Flow Diagram\n\n```mermaid\ngraph TD\n  A --> B\n```\n' > "$output_file"
        ;;
    rejected)
        case "${STEP7A_SANITIZER_TOKEN:-pipe-in-node-label}" in
            br-in-participant-alias)
                printf '## Code Flow Diagram\n\n```mermaid\nsequenceDiagram\n  participant A as Bad<br/>Label\n```\n' > "$output_file"
                ;;
            dollar-in-participant-alias)
                printf '## Code Flow Diagram\n\n```mermaid\nsequenceDiagram\n  participant A as Bad$Label\n```\n' > "$output_file"
                ;;
            unclosed-frontmatter)
                printf '## Code Flow Diagram\n\n```mermaid\n---\ntitle: Bad\n```\n' > "$output_file"
                ;;
            *)
                printf '## Code Flow Diagram\n\n```mermaid\ngraph TD\n  A[Bad|Label]\n```\n' > "$output_file"
                ;;
        esac
        ;;
    failed)
        printf '%s\n' "${STEP7A_GEN_FORCE_SKIP_REASON:-generator helper failed}" >&2
        exit 1
        ;;
    crash)
        printf 'generator crashed\n' >&2
        exit 99
        ;;
esac
STUB
    chmod +x "$root/python/stubs/launch-claude-subprocess"

    for _script in "$root/scripts/"*.sh "$root/skills/implement/scripts/"*.sh; do
        [ -e "$_script" ] || continue
        chmod +x "$_script"
    done
}

install_real_diagrams_helper() {
    local root=$1
    cp "$REPO_ROOT/python/cli.py" "$root/python/cli.py"
    : # redact + mermaid sanitize are handled by the copied Python CLI
    chmod +x \
        "$root/python/cli.py" \
        "$root/python/cli.py"
}

install_diagrams_gh_stub() {
    local dir=$1
    mkdir -p "$dir"
    cat > "$dir/gh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'gh %s\n' "$*" >> "$STEP7A_CALLS_LOG"
if [ "$1" = "api" ]; then
    endpoint=$2
    if [[ "$endpoint" == "/repos/owner/repo/issues/42/comments" ]]; then
        printf '[{"id":101,"body":"<!-- larch:diagrams v1 -->\\n"}]\n'
        exit 0
    fi
    if [[ "$endpoint" == "/repos/owner/repo/issues/comments/101" ]]; then
        if printf '%s\n' "$@" | grep -qx -- "PATCH"; then
            for ((i=1; i<=$#; i++)); do
                if [ "${!i}" = "--input" ]; then
                    next=$((i + 1))
                    jq -r '.body' < "${!next}" > "$STEP7A_UPSERT_BODY_CAPTURE"
                fi
            done
            printf 'https://example.test/comment/1\n'
            exit 0
        fi
        cat "$STEP7A_UPSERT_EXISTING_BODY_FILE"
        exit 0
    fi
fi
exit 1
STUB
    chmod +x "$dir/gh"
}

new_case() {
    local name=$1
    CASE_DIR="$TMP_ROOT/$name"
    mkdir -p "$CASE_DIR/tmp"
    : > "$CASE_DIR/calls.log"
    : > "$CASE_DIR/flush-count"
    touch "$CASE_DIR/tmp/execution-issues.md"
    printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s/plugin\nLARCH_TOKEN_SESSION_ID=test-session\nLARCH_CLAUDE_SOURCE_FILE=%s/source.jsonl\nLARCH_TIMING_LEDGER=%s/timing.log\nLARCH_ISSUE_NUMBER=42\nLARCH_RUN_ID=run-001\nLARCH_NO_LOGS_COMMIT=false\nLARCH_FORKED_TARGET=false\nREPO=owner/repo\nUPSTREAM_REPO=upstream/repo\n' \
        "$TMP_ROOT" "$CASE_DIR" "$CASE_DIR" > "$CASE_DIR/tmp/session-env.sh"
}

run_helper() {
    local workdir=$1
    shift
    (
        cd "$workdir"
        CLAUDE_PLUGIN_ROOT="$TMP_ROOT/plugin" \
        LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS="$TMP_ROOT/plugin/python/stubs/launch-claude-subprocess" \
        STEP7A_CALLS_LOG="$CASE_DIR/calls.log" \
        STEP7A_FLUSH_COUNT_FILE="$CASE_DIR/flush-count" \
        "$HELPER" "$@"
    )
}

run_helper_quiet() {
    local workdir=$1
    shift
    (
        cd "$workdir"
        unset LARCH_QUIET_DISABLE
        CLAUDE_PLUGIN_ROOT="$TMP_ROOT/plugin" \
        LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS="$TMP_ROOT/plugin/python/stubs/launch-claude-subprocess" \
        STEP7A_CALLS_LOG="$CASE_DIR/calls.log" \
        STEP7A_FLUSH_COUNT_FILE="$CASE_DIR/flush-count" \
        "$HELPER" "$@"
    )
}

make_skip_repo() {
    local repo=$1
    mkdir -p "$repo"
    git -C "$repo" init -q
    git -C "$repo" config user.email test@example.test
    git -C "$repo" config user.name Test
    mkdir -p "$repo/docs"
    printf 'base\n' > "$repo/docs/X.md"
    git -C "$repo" add docs/X.md
    git -C "$repo" commit -q -m base
    git -C "$repo" branch -M main
    git -C "$repo" clone --bare . "$repo-origin.git" >/dev/null 2>&1
    git -C "$repo" remote add origin "$repo-origin.git"
    git -C "$repo" fetch origin main >/dev/null 2>&1
    git -C "$repo" checkout -b feature >/dev/null 2>&1
    printf 'feature\n' > "$repo/docs/X.md"
    git -C "$repo" add docs/X.md
    git -C "$repo" commit -q -m docs
}

make_forked_skip_repo() {
    local repo=$1
    mkdir -p "$repo"
    git -C "$repo" init -q
    git -C "$repo" config user.email test@example.test
    git -C "$repo" config user.name Test
    mkdir -p "$repo/docs"
    printf 'base\n' > "$repo/docs/X.md"
    git -C "$repo" add docs/X.md
    git -C "$repo" commit -q -m base
    git -C "$repo" branch -M main
    git -C "$repo" clone --bare . "$repo-upstream.git" >/dev/null 2>&1
    git -C "$repo" remote add upstream "$repo-upstream.git"
    git -C "$repo" fetch upstream main >/dev/null 2>&1
    git -C "$repo" checkout -b feature >/dev/null 2>&1
    printf 'feature\n' > "$repo/docs/X.md"
    git -C "$repo" add docs/X.md
    git -C "$repo" commit -q -m docs
}

make_forked_generate_repo() {
    local repo=$1
    mkdir -p "$repo"
    git -C "$repo" init -q
    git -C "$repo" config user.email test@example.test
    git -C "$repo" config user.name Test
    mkdir -p "$repo/docs"
    printf 'base\n' > "$repo/docs/X.md"
    git -C "$repo" add docs/X.md
    git -C "$repo" commit -q -m base
    git -C "$repo" branch -M main
    git -C "$repo" clone --bare . "$repo-upstream.git" >/dev/null 2>&1
    git -C "$repo" remote add upstream "$repo-upstream.git"
    git -C "$repo" fetch upstream main >/dev/null 2>&1
    git -C "$repo" checkout -b feature >/dev/null 2>&1
    printf 'feature\n' > "$repo/docs/X.md"
    printf 'feature\n' > "$repo/docs/Y.md"
    printf 'feature\n' > "$repo/docs/Z.md"
    git -C "$repo" add docs/X.md docs/Y.md docs/Z.md
    git -C "$repo" commit -q -m docs
}

echo "=== test-step-7a ==="

setup_plugin "$TMP_ROOT/plugin"

assert_file_contains "The \`7a.r\` macro skip is \`CHECKPOINT_NEXT\`-only" "$REPO_ROOT/skills/implement/SKILL.md" "SKILL pins Step 7a CHECKPOINT_NEXT-only macro skip"
assert_file_not_contains "preserves the probe exit code for \`7a.r\` macro routing" "$REPO_ROOT/skills/implement/SKILL.md" "SKILL removes Step 7a exit-code macro routing prose"

new_case green
set +e
out=$(run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "green exits 0"
assert_contains "DIAGRAM_STATUS=ok" "$out" "green emits diagram ok"
assert_contains "DIAGRAM_PATH=$CASE_DIR/tmp/code-flow-diagram.md" "$out" "green emits diagram path"
assert_contains "COMMENT_URL=https://example.test/comment/1" "$out" "green emits comment URL"
assert_contains "LOG_FLUSH_STATUS=degraded" "$out" "green emits degraded log flush in offline harness"
assert_contains "SESSION_TRANSCRIPT_STATUS=ok" "$out" "green relays transcript status"
assert_contains "STEP_7A_BAIL_REASON=" "$out" "green emits empty bail reason"
assert_contains "REBASE_OUTCOME=ok" "$out" "green emits rebase outcome"
assert_contains "ROUTE=continue" "$out" "green emits route continue"
assert_contains "CHECKPOINT_NEXT=continue" "$out" "green relays checkpoint continue"
assert_not_contains "## Code Flow Diagram" "$out" "green does not print code flow diagram body"
assert_contains "python/cli.py agent launch-claude-subprocess" "$(cat "$CASE_DIR/calls.log")" "green invokes generator"
assert_contains "--output-file $CASE_DIR/tmp/code-flow-diagram.raw.md" "$(cat "$CASE_DIR/calls.log")" "green passes raw output path to generator"
assert_call_order "$CASE_DIR/calls.log" "python3 python/cli.py token mark Step 7a — pre-ship" "python/cli.py agent launch-claude-subprocess" "green marks token ledger before generator"
assert_call_order "$CASE_DIR/calls.log" "python3 python/cli.py timing mark Step 7a — pre-ship" "python/cli.py agent launch-claude-subprocess" "green marks timing ledger before generator"
assert_call_order "$CASE_DIR/calls.log" "python/cli.py agent launch-claude-subprocess" "upsert-diagrams-content" "green generate before compose"
assert_call_order "$CASE_DIR/calls.log" "upsert-diagrams-content" "python/cli.py diagrams upsert" "green compose before upsert"
assert_call_order "$CASE_DIR/calls.log" "python/cli.py diagrams upsert" "python/cli.py push checkpoint-probe" "green upsert before rebase"
assert_call_order "$CASE_DIR/calls.log" "python/cli.py push checkpoint-probe" "run-log capture-transcript" "green rebase before flush"
assert_file_equals "$(green_expected_summary)" "$CASE_DIR/tmp/code-flow-section.md" "green writes expected code flow section"
assert_contains "python/cli.py diagrams upsert --issue 42 --code-flow-file $CASE_DIR/tmp/code-flow-section.md --repo owner/repo" "$(cat "$CASE_DIR/calls.log")" "green invokes shared stable diagrams helper"
assert_not_contains "tracking-issue upsert-summary" "$(cat "$CASE_DIR/calls.log")" "green does not call tracking summary directly"

new_case architecture-env-ignored
printf '## Architecture Diagram\n\nstale\n' > "$CASE_DIR/architecture.md"
set +e
out=$(ARCHITECTURE_DIAGRAM_FILE="$CASE_DIR/architecture.md" run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "architecture-env-ignored exits 0"
assert_file_equals "$(green_expected_summary)" "$CASE_DIR/tmp/code-flow-section.md" "architecture-env-ignored writes code flow only"
assert_file_not_contains "Architecture Diagram" "$CASE_DIR/tmp/code-flow-section.md" "architecture-env-ignored ignores architecture env"

new_case diagram-skip
make_skip_repo "$CASE_DIR/repo"
set +e
out=$(run_helper "$CASE_DIR/repo" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "diagram-skip exits 0"
assert_contains "DIAGRAM_STATUS=skip" "$out" "diagram-skip emits skip"
assert_contains "pre-ship status=skip reason=small-non-runtime-change" "$out" "diagram-skip prints skip line"
assert_not_contains "python/cli.py agent launch-claude-subprocess" "$(cat "$CASE_DIR/calls.log")" "diagram-skip does not invoke generator"
if [ ! -e "$CASE_DIR/tmp/code-flow-section.md" ]; then pass "diagram-skip omits code flow section"; else fail "diagram-skip omits code flow section"; fi
assert_not_contains "python/cli.py diagrams upsert" "$(cat "$CASE_DIR/calls.log")" "diagram-skip skips diagrams upsert"

new_case diagram-skip-forked
make_forked_skip_repo "$CASE_DIR/repo"
set +e
out=$(run_helper "$CASE_DIR/repo" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target true 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "diagram-skip-forked exits 0"
assert_contains "DIAGRAM_STATUS=skip" "$out" "diagram-skip-forked emits skip"
assert_contains "pre-ship status=skip reason=small-non-runtime-change" "$out" "diagram-skip-forked prints skip line"
assert_not_contains "python/cli.py agent launch-claude-subprocess" "$(cat "$CASE_DIR/calls.log")" "diagram-skip-forked does not invoke generator"
if [ ! -e "$CASE_DIR/tmp/code-flow-section.md" ]; then pass "diagram-skip-forked omits code flow section"; else fail "diagram-skip-forked omits code flow section"; fi
assert_not_contains "python/cli.py diagrams upsert" "$(cat "$CASE_DIR/calls.log")" "diagram-skip-forked skips diagrams upsert"

new_case diagram-generate-forked
make_forked_generate_repo "$CASE_DIR/repo"
set +e
out=$(run_helper "$CASE_DIR/repo" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target true 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "diagram-generate-forked exits 0"
assert_contains "DIAGRAM_STATUS=ok" "$out" "diagram-generate-forked emits diagram ok"
assert_contains "python/cli.py agent launch-claude-subprocess" "$(cat "$CASE_DIR/calls.log")" "diagram-generate-forked invokes generator"
assert_contains "--output-file $CASE_DIR/tmp/code-flow-diagram.raw.md" "$(cat "$CASE_DIR/calls.log")" "diagram-generate-forked passes raw output path to generator"
assert_contains "python/cli.py diagrams upsert --issue 42 --code-flow-file $CASE_DIR/tmp/code-flow-section.md --repo upstream/repo" "$(cat "$CASE_DIR/calls.log")" "diagram-generate-forked threads repo to upsert"

new_case preserve-architecture
cat > "$CASE_DIR/existing-diagrams.md" <<'EOF'
<!-- larch:diagrams v1 -->

## Architecture Diagram

```mermaid
graph TD
  A["Existing architecture"] --> B["Runtime"]
```
EOF
set +e
out=$(STEP7A_UPSERT_EXISTING_BODY_FILE="$CASE_DIR/existing-diagrams.md" STEP7A_UPSERT_BODY_CAPTURE="$CASE_DIR/body.md" run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "preserve-architecture exits 0"
assert_file_contains "Existing architecture" "$CASE_DIR/body.md" "preserve-architecture keeps architecture content"
assert_file_contains "## Code Flow Diagram" "$CASE_DIR/body.md" "preserve-architecture writes code flow content"

new_case preserve-architecture-production-helper
install_real_diagrams_helper "$TMP_ROOT/plugin"
install_diagrams_gh_stub "$CASE_DIR/stub"
cat > "$CASE_DIR/existing-diagrams.md" <<'EOF'
<!-- larch:diagrams v1 -->

## Architecture Diagram

```mermaid
graph TD
  A["Existing architecture"] --> B["Runtime"]
```
EOF
set +e
old_path=$PATH
PATH="$CASE_DIR/stub:$PATH"
out=$(STEP7A_UPSERT_EXISTING_BODY_FILE="$CASE_DIR/existing-diagrams.md" STEP7A_UPSERT_BODY_CAPTURE="$CASE_DIR/body.md" run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
PATH=$old_path
set -e
assert_equals 3 "$rc" "preserve-architecture-production-helper reaches production helper before real rebase fails"
assert_file_contains "Existing architecture" "$CASE_DIR/body.md" "preserve-architecture-production-helper keeps architecture content"
assert_file_contains "## Code Flow Diagram" "$CASE_DIR/body.md" "preserve-architecture-production-helper writes code flow content"
assert_contains "gh api /repos/owner/repo/issues/comments/101 -X PATCH" "$(cat "$CASE_DIR/calls.log")" "preserve-architecture-production-helper patches existing stable comment"
assert_equals 1 "$(grep -Fc '/repos/owner/repo/issues/42/comments' "$CASE_DIR/calls.log" 2>/dev/null || true)" "preserve-architecture-production-helper lists comments once"
setup_plugin "$TMP_ROOT/plugin"

new_case no-prior-diagrams-comment
set +e
out=$(STEP7A_UPSERT_BODY_CAPTURE="$CASE_DIR/body.md" run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "no-prior-diagrams-comment exits 0"
assert_file_contains "## Code Flow Diagram" "$CASE_DIR/body.md" "no-prior-diagrams-comment creates code flow body"
assert_file_not_contains "Architecture Diagram" "$CASE_DIR/body.md" "no-prior-diagrams-comment omits architecture content"

new_case legacy-diagrams-orphan
cat > "$CASE_DIR/existing-diagrams.md" <<'EOF'
<!-- larch:diagrams v1 runid=legacy -->

## Architecture Diagram

```mermaid
graph TD
  A["Legacy architecture"] --> B["Runtime"]
```
EOF
set +e
out=$(STEP7A_UPSERT_EXISTING_BODY_FILE="$CASE_DIR/existing-diagrams.md" STEP7A_UPSERT_BODY_CAPTURE="$CASE_DIR/body.md" run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "legacy-diagrams-orphan exits 0"
assert_file_contains "## Code Flow Diagram" "$CASE_DIR/body.md" "legacy-diagrams-orphan creates stable code flow body"
assert_file_not_contains "Legacy architecture" "$CASE_DIR/body.md" "legacy-diagrams-orphan ignores legacy comment body"

new_case diagram-rejected
printf 'stale\n' > "$CASE_DIR/tmp/code-flow-diagram.md"
cat > "$CASE_DIR/existing-diagrams.md" <<'EOF'
<!-- larch:diagrams v1 -->

## Code Flow Diagram

```mermaid
graph TD
  Existing --> Preserved
```
EOF
cp "$CASE_DIR/existing-diagrams.md" "$CASE_DIR/body.md"
set +e
out=$(STEP7A_GEN_MODE=rejected STEP7A_UPSERT_EXISTING_BODY_FILE="$CASE_DIR/existing-diagrams.md" STEP7A_UPSERT_BODY_CAPTURE="$CASE_DIR/body.md" run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "diagram-rejected exits 0"
assert_contains "DIAGRAM_STATUS=skipped" "$out" "diagram-rejected emits skipped"
assert_not_contains "python/cli.py diagrams upsert" "$(cat "$CASE_DIR/calls.log")" "diagram-rejected skips diagrams upsert"
assert_contains "COMMENT_URL=" "$out" "diagram-rejected emits empty comment URL"
assert_contains "LOG_FLUSH_STATUS=degraded" "$out" "diagram-rejected keeps offline flush degraded"
assert_contains "### Warnings" "$(cat "$CASE_DIR/tmp/execution-issues.md")" "diagram-rejected records offline flush warning"
assert_file_contains "Existing --> Preserved" "$CASE_DIR/body.md" "diagram-rejected leaves prior issue body unchanged"
if [ ! -e "$CASE_DIR/tmp/code-flow-section.md" ]; then pass "diagram-rejected omits code flow section"; else fail "diagram-rejected omits code flow section"; fi
if [ ! -e "$CASE_DIR/tmp/code-flow-diagram.md" ]; then pass "diagram-rejected clears stale code flow diagram"; else fail "diagram-rejected clears stale code flow diagram"; fi

for sanitizer_token in br-in-participant-alias dollar-in-participant-alias unclosed-frontmatter; do
    new_case "diagram-rejected-$sanitizer_token"
    set +e
    out=$(STEP7A_GEN_MODE=rejected STEP7A_SANITIZER_TOKEN="$sanitizer_token" run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
    rc=$?
    set -e
    assert_equals 0 "$rc" "diagram-rejected-$sanitizer_token exits 0"
    assert_contains "DIAGRAM_STATUS=skipped" "$out" "diagram-rejected-$sanitizer_token emits skipped"
    assert_not_contains "python/cli.py diagrams upsert" "$(cat "$CASE_DIR/calls.log")" "diagram-rejected-$sanitizer_token skips diagrams upsert"
    assert_contains "COMMENT_URL=" "$out" "diagram-rejected-$sanitizer_token emits empty comment URL"
    if [ ! -e "$CASE_DIR/tmp/code-flow-section.md" ]; then pass "diagram-rejected-$sanitizer_token omits code flow section"; else fail "diagram-rejected-$sanitizer_token omits code flow section"; fi
done

new_case diagram-failure
printf 'stale\n' > "$CASE_DIR/tmp/code-flow-diagram.md"
cat > "$CASE_DIR/existing-diagrams.md" <<'EOF'
<!-- larch:diagrams v1 -->

## Code Flow Diagram

```mermaid
graph TD
  Existing --> Preserved
```
EOF
cp "$CASE_DIR/existing-diagrams.md" "$CASE_DIR/body.md"
set +e
out=$(STEP7A_GEN_MODE=failed STEP7A_UPSERT_EXISTING_BODY_FILE="$CASE_DIR/existing-diagrams.md" STEP7A_UPSERT_BODY_CAPTURE="$CASE_DIR/body.md" run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "diagram-generation-failure exits 0"
assert_contains "DIAGRAM_STATUS=failed" "$out" "diagram-generation-failure emits failed"
assert_not_contains "python/cli.py diagrams upsert" "$(cat "$CASE_DIR/calls.log")" "diagram-generation-failure skips diagrams upsert"
assert_contains "COMMENT_URL=" "$out" "diagram-generation-failure skips comment"
assert_file_contains "Existing --> Preserved" "$CASE_DIR/body.md" "diagram-generation-failure leaves prior issue body unchanged"
if [ ! -e "$CASE_DIR/tmp/code-flow-section.md" ]; then pass "diagram-generation-failure omits code flow section"; else fail "diagram-generation-failure omits code flow section"; fi
if [ ! -e "$CASE_DIR/tmp/code-flow-diagram.md" ]; then pass "diagram-generation-failure clears stale code flow diagram"; else fail "diagram-generation-failure clears stale code flow diagram"; fi
assert_file_contains "### Warnings" "$CASE_DIR/tmp/execution-issues.md" "diagram-generation-failure appends warning"
if [ ! -e "$CASE_DIR/tmp/larch-logs/implement/run-001/code-flow-diagram.failure.log" ]; then pass "diagram-generation-failure does not copy failure log to committed run logs"; else fail "diagram-generation-failure does not copy failure log to committed run logs"; fi

new_case diagram-failure-sanitizer
set +e
out=$(STEP7A_GEN_MODE=failed STEP7A_SANITIZER_TOKEN=pipe-in-node-label STEP7A_GEN_FORCE_SKIP_REASON='pipe-in-node-label fence=mermaid line=7' run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "diagram-failure-sanitizer exits 0"
assert_contains "DIAGRAM_STATUS=failed" "$out" "diagram-failure-sanitizer emits failed"
assert_not_contains "python/cli.py diagrams upsert" "$(cat "$CASE_DIR/calls.log")" "diagram-failure-sanitizer skips diagrams upsert"
assert_contains "COMMENT_URL=" "$out" "diagram-failure-sanitizer emits empty comment URL"
if [ ! -e "$CASE_DIR/tmp/code-flow-section.md" ]; then pass "diagram-failure-sanitizer omits code flow section"; else fail "diagram-failure-sanitizer omits code flow section"; fi

new_case upsert-failure
set +e
out=$(STEP7A_UPSERT_FAIL=1 run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "summary-upsert-failure exits 0"
assert_contains "COMMENT_URL=" "$out" "summary-upsert-failure emits empty URL"
assert_file_not_contains "### Tool Failures" "$CASE_DIR/tmp/execution-issues.md" "summary-upsert-failure does not append tool failure"
assert_contains "python/cli.py push checkpoint-probe" "$(cat "$CASE_DIR/calls.log")" "summary-upsert-failure still runs rebase"
assert_contains "run-log capture-transcript" "$(cat "$CASE_DIR/calls.log")" "summary-upsert-failure still runs flush"

new_case flush-failure
set +e
out=$(STEP7A_FLUSH_FAIL_FIRST=1 run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "flush-failure exits 0"
assert_contains "LOG_FLUSH_STATUS=degraded" "$out" "flush-failure emits degraded"
assert_file_not_contains "### Tool Failures" "$CASE_DIR/tmp/execution-issues.md" "flush-failure uses Python flush path"
if [ ! -s "$CASE_DIR/flush-count" ]; then pass "flush-failure does not use shell flush stub"; else fail "flush-failure does not use shell flush stub"; fi
assert_contains "run-log commit" "$(cat "$CASE_DIR/calls.log")" "flush-failure still runs commit"

new_case flush-failure-no-logs-commit
set +e
out=$(STEP7A_FLUSH_FAIL_FIRST=1 run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit true --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "flush-failure-no-logs-commit exits 0"
assert_contains "LOG_FLUSH_STATUS=skipped-no-logs-commit" "$out" "flush-failure-no-logs-commit skips commit path"
assert_not_contains "run-log commit" "$(cat "$CASE_DIR/calls.log")" "flush-failure-no-logs-commit skips commit"

new_case no-logs-commit
set +e
out=$(run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit true --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "no-logs-commit exits 0"
assert_not_contains "run-log commit" "$(cat "$CASE_DIR/calls.log")" "no-logs-commit skips commit"
assert_contains "LOG_FLUSH_STATUS=skipped-no-logs-commit" "$out" "no-logs-commit emits skipped"

new_case forked-target
set +e
out=$(run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target true 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "forked-target exits 0"
assert_contains "python/cli.py push checkpoint-probe 7a.r diagrams --base-remote upstream --base-ref main" "$(cat "$CASE_DIR/calls.log")" "forked-target passes upstream argv"

new_case issue-empty
grep -v '^LARCH_ISSUE_NUMBER=' "$CASE_DIR/tmp/session-env.sh" > "$CASE_DIR/tmp/session-env.new"
mv "$CASE_DIR/tmp/session-env.new" "$CASE_DIR/tmp/session-env.sh"
set +e
out=$(run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number "" --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "ISSUE_NUMBER empty exits 0"
assert_not_contains "python/cli.py diagrams upsert" "$(cat "$CASE_DIR/calls.log")" "ISSUE_NUMBER empty skips upsert"
assert_contains "COMMENT_URL=" "$out" "ISSUE_NUMBER empty emits empty URL"
assert_contains "python/cli.py push checkpoint-probe" "$(cat "$CASE_DIR/calls.log")" "ISSUE_NUMBER empty still runs rebase"

new_case generator-crash
set +e
out=$(STEP7A_GEN_MODE=crash run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "generator-crash exits 0"
assert_contains "DIAGRAM_STATUS=failed" "$out" "generator-crash emits failed"
assert_contains "COMMENT_URL=" "$out" "generator-crash skips comment"
assert_file_contains "### Warnings" "$CASE_DIR/tmp/execution-issues.md" "generator-crash appends warning"

new_case rebase-conflict
set +e
out=$(STEP7A_REBASE_MODE=conflict run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 1 "$rc" "rebase-conflict exits 1"
assert_contains "REBASE_OUTCOME=conflict" "$out" "rebase-conflict emits conflict outcome"
assert_contains "ROUTE=conflict" "$out" "rebase-conflict emits route conflict"
assert_contains "CHECKPOINT_NEXT=load-routing" "$out" "rebase-conflict relays checkpoint load-routing"
assert_contains "LOG_FLUSH_STATUS=skipped-no-logs-commit" "$out" "rebase-conflict defers git commit flush"
assert_not_contains "run-log commit" "$(cat "$CASE_DIR/calls.log")" "rebase-conflict defers run-log commit"

new_case rebase-failed
set +e
out=$(STEP7A_REBASE_MODE=failed run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 3 "$rc" "rebase-failed exits 3"
assert_contains "REBASE_OUTCOME=failed" "$out" "rebase-failed emits failed outcome"
assert_contains "ROUTE=bail" "$out" "rebase-failed emits route bail"
assert_contains "CHECKPOINT_NEXT=load-routing" "$out" "rebase-failed relays checkpoint load-routing"
assert_contains "LOG_FLUSH_STATUS=skipped-no-logs-commit" "$out" "rebase-failed defers git commit flush"
assert_not_contains "run-log commit" "$(cat "$CASE_DIR/calls.log")" "rebase-failed defers run-log commit"

new_case rebase-unexpected-rc
set +e
out=$(STEP7A_REBASE_MODE=unexpected run_helper "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 5 "$rc" "rebase-unexpected-rc exits 5"
assert_contains "REBASE_OUTCOME=failed" "$out" "rebase-unexpected-rc emits failed outcome"
assert_contains "REBASE_ERROR=unexpected-rc-5" "$out" "rebase-unexpected-rc emits unexpected rc error"
assert_contains "ROUTE=bail" "$out" "rebase-unexpected-rc emits route bail"
assert_contains "CHECKPOINT_NEXT=load-routing" "$out" "rebase-unexpected-rc relays checkpoint load-routing"
assert_contains "LOG_FLUSH_STATUS=skipped-no-logs-commit" "$out" "rebase-unexpected-rc defers git commit flush"
assert_not_contains "run-log commit" "$(cat "$CASE_DIR/calls.log")" "rebase-unexpected-rc defers run-log commit"

new_case quiet-rebase-contract
set +e
out=$(run_helper_quiet "$CASE_DIR" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "quiet-rebase-contract exits 0"
assert_contains "REBASE_OUTCOME=ok" "$out" "quiet-rebase-contract preserves rebase outcome on contract stream"
assert_contains "CHECKPOINT_NEXT=continue" "$out" "quiet-rebase-contract preserves checkpoint directive"
assert_contains "LOG_FLUSH_STATUS=degraded" "$out" "quiet-rebase-contract emits final tail"

new_case quiet-diagram-skip-contract
make_skip_repo "$CASE_DIR/repo"
set +e
out=$(run_helper_quiet "$CASE_DIR/repo" --implement-tmpdir "$CASE_DIR/tmp" --issue-number 42 --run-id run-001 --no-logs-commit false --forked-target false 2>&1)
rc=$?
set -e
assert_equals 0 "$rc" "quiet-diagram-skip-contract exits 0"
assert_contains "⏩ 7a: pre-ship status=skip reason=small-non-runtime-change elapsed=0s" "$out" "quiet-diagram-skip-contract preserves skip line on contract stream"

new_case argv-error
set +e
out=$(run_helper "$CASE_DIR" --issue-number 42 2>&1)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass "argv error exits nonzero"; else fail "argv error exits nonzero"; fi
pass "argv error handled by CLI"

finish
