#!/usr/bin/env bash
# test-design-step1d5.sh — offline harness for design-step1d5.sh collect mode.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/design-step1d5.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }
contains() { grep -Fq -- "$2" "$1" || fail "$3"; }
not_contains() { ! grep -Fq -- "$2" "$1" || fail "$3"; }
count_lines() { grep -Fc -- "$2" "$1"; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-design-step1d5.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

STUB_DIR="$TMP/bin"
mkdir -p "$STUB_DIR"
cat >"$STUB_DIR/python3" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
_cli=${1:-}
shift || true
cmd1=${1:-}
cmd2=${2:-}
if [ "$cmd1 $cmd2" = "agent collect-results" ]; then
  shift 2
  if [ "${1:-}" = "--timeout" ]; then shift 2; fi
  if [ "$#" -eq 0 ]; then
    printf 'collect-results: expected paths\n' >&2
    exit 2
  fi
  if [ -n "${EXPECTED_PATHS_FILE:-}" ] && [ -f "$EXPECTED_PATHS_FILE" ]; then
    actual="$TMPDIR_STUB/actual-paths.txt"
    printf '%s\n' "$@" >"$actual"
    diff -u "$EXPECTED_PATHS_FILE" "$actual" >/dev/null || { printf 'unexpected collect argv\n' >&2; exit 7; }
  fi
  for path in "$@"; do
    printf 'COLLECTED:%s:%s\n' "$(basename "$path")" "$(cat "$path" 2>/dev/null || true)"
  done
  exit 0
fi
if [ "$cmd1 $cmd2" = "run-log append-failure" ]; then
  shift 2
  log=""; site=""; tool=""; exit_code=""; category=""; output_file=""
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --log) log="$2"; shift 2 ;;
      --site) site="$2"; shift 2 ;;
      --tool) tool="$2"; shift 2 ;;
      --exit-code) exit_code="$2"; shift 2 ;;
      --category) category="$2"; shift 2 ;;
      --output-file) output_file="$2"; shift 2 ;;
      --redact) shift ;;
      *) printf 'unexpected append-failure arg: %s\n' "$1" >&2; exit 8 ;;
    esac
  done
  mkdir -p "$(dirname "$log")"
  {
    printf '### %s\n' "$category"
    printf -- '- **%s**: %s exited %s\n' "$site" "$tool" "$exit_code"
    printf 'OUTPUT_FILE=%s\n' "$output_file"
  } >>"$log"
  exit 0
fi
if [ "$cmd1 $cmd2" = "dirty-tree checkpoint" ]; then
  printf 'STATUS=%s\n' "${LARCH_TEST_DIRTY_STATUS:-clean}"
  exit 0
fi
if [ "$cmd1 $cmd2" = "design pause-save" ]; then
  exit 0
fi
printf 'unexpected python3 call: %s %s %s\n' "$_cli" "$cmd1" "$cmd2" >&2
exit 9
STUB
chmod +x "$STUB_DIR/python3"

run_collect() {
  local design_tmpdir=$1
  shift
  DESIGN_TMPDIR="$design_tmpdir" CLAUDE_PLUGIN_ROOT="$ROOT" ISSUE_NUMBER=123 PATH="$STUB_DIR:$PATH" TMPDIR_STUB="$TMP" "$SUBJECT" --mode collect -- "$@"
}

D0="$TMP/arg-validate"
mkdir -p "$D0"
set +e
DESIGN_TMPDIR="$D0" CLAUDE_PLUGIN_ROOT="$ROOT" ISSUE_NUMBER=123 PATH="$STUB_DIR:$PATH" "$SUBJECT" --mode collect -- >"$D0/out" 2>"$D0/err"
rc=$?
set -e
[ "$rc" -eq 2 ] || fail "collect with no paths must exit 2, got $rc"
contains "$D0/err" 'requires at least one output path' 'collect no-path diagnostic missing'
pass 'collect rejects missing output paths'

D1="$TMP/per-slot"
mkdir -p "$D1"
framing="$D1/cursor-brainstorm-output.txt"
scope="$D1/codex-brainstorm-output.txt"
printf 'framing text' >"$framing"
printf 'scope text' >"$scope"
printf '%s\n%s\n' "$framing" "$scope" >"$D1/expected-paths.txt"
EXPECTED_PATHS_FILE="$D1/expected-paths.txt" LARCH_TEST_DIRTY_STATUS=clean run_collect "$D1" "$framing" "$scope" >"$D1/out"
contains "$D1/out" 'COLLECTED:cursor-brainstorm-output.txt:framing text' 'framing slot output missing'
contains "$D1/out" 'COLLECTED:codex-brainstorm-output.txt:scope text' 'scope slot output missing'
pass 'collect relays per-slot collector output and argv'

D2="$TMP/launch-failures"
mkdir -p "$D2"
framing2="$D2/cursor-brainstorm-output.txt"
scope2="$D2/codex-brainstorm-output.txt"
: >"$framing2"
: >"$scope2"
printf 'STDERR_SINK=%s\n' "$D2/cursor-brainstorm-launch.failure.log" >"$framing2.meta"
printf 'STDERR_SINK=%s\n' "$D2/codex-brainstorm-launch.failure.log" >"$scope2.meta"
printf 'LAUNCHER_EXIT=13\ncursor failed\n' >"$D2/cursor-brainstorm-launch.failure.log"
printf 'LAUNCHER_EXIT=14\ncodex failed\n' >"$D2/codex-brainstorm-launch.failure.log"
printf '%s\n%s\n' "$framing2" "$scope2" >"$D2/expected-paths.txt"
EXPECTED_PATHS_FILE="$D2/expected-paths.txt" LARCH_TEST_DIRTY_STATUS=clean run_collect "$D2" "$framing2" "$scope2" >"$D2/out1"
EXPECTED_PATHS_FILE="$D2/expected-paths.txt" LARCH_TEST_DIRTY_STATUS=clean run_collect "$D2" "$framing2" "$scope2" >"$D2/out2"
contains "$D2/execution-issues.md" 'cursor-brainstorm-launch' 'cursor launch failure row missing'
contains "$D2/execution-issues.md" 'codex-brainstorm-launch' 'codex launch failure row missing'
[ "$(count_lines "$D2/execution-issues.md" '### External Reviewer Issues')" -eq 2 ] || fail 'launch failure rows must be idempotent across reruns'
pass 'collect records launch failures once per sink'

D3="$TMP/dirty"
mkdir -p "$D3"
dirty_a="$D3/cursor-brainstorm-output.txt"
dirty_b="$D3/codex-brainstorm-output.txt"
: >"$dirty_a"
: >"$dirty_b"
printf 'STATUS=clean\n' >"$dirty_a.dirty-tree"
printf 'STATUS=dirty\n' >"$dirty_b.dirty-tree"
printf '%s\n%s\n' "$dirty_a" "$dirty_b" >"$D3/expected-paths.txt"
EXPECTED_PATHS_FILE="$D3/expected-paths.txt" LARCH_TEST_DIRTY_STATUS=clean run_collect "$D3" "$dirty_a" "$dirty_b" >"$D3/out"
contains "$D3/dirty-tree-detected.env" 'STAGE=brainstorm-collection' 'dirty stage missing'
contains "$D3/dirty-tree-detected.env" 'RECOVERY_REQUIRED=true' 'dirty recovery flag missing'
contains "$D3/dirty-tree-detected.env" 'DIRTY_TREE_STATUS=dirty' 'dirty status missing'
pass 'collect merges dirty-tree sidecars'

D4="$TMP/clean"
mkdir -p "$D4"
clean_a="$D4/cursor-brainstorm-output.txt"
: >"$clean_a"
printf '%s\n' "$clean_a" >"$D4/expected-paths.txt"
EXPECTED_PATHS_FILE="$D4/expected-paths.txt" LARCH_TEST_DIRTY_STATUS=clean run_collect "$D4" "$clean_a" >"$D4/out"
contains "$D4/dirty-tree-detected.env" 'RECOVERY_REQUIRED=false' 'clean recovery flag missing'
not_contains "$D4/dirty-tree-detected.env" 'DIRTY_TREE_STATUS=' 'clean case should not write dirty status'
pass 'collect records clean dirty-tree checkpoint'

bash -n "$SUBJECT" || fail 'bash -n design-step1d5.sh failed'
printf 'PASS: test-design-step1d5.sh\n'
