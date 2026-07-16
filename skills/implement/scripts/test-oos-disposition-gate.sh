#!/usr/bin/env bash
# Delegation smoke for oos-disposition-gate.sh and oos-disposition-checkpoint.sh.
# Behavioral coverage lives in python/tests/issue/test_file_oos.py (-k disposition_gate).
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
GATE="$SCRIPT_DIR/oos-disposition-gate.sh"
CHECKPOINT="$SCRIPT_DIR/oos-disposition-checkpoint.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-oos-disposition-gate.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

STUB_BIN="$TMP/bin"
FAKE_PLUGIN="$TMP/fake-plugin"
mkdir -p "$STUB_BIN" "$FAKE_PLUGIN/python"
ARGV_LOG="$TMP/argv.log"
: >"$ARGV_LOG"

cat >"$STUB_BIN/python3" <<EOF
#!/usr/bin/env bash
printf '%s\0' "\$@" >"$ARGV_LOG"
printf 'stdout-marker\n'
printf 'stderr-marker\n' >&2
exit 7
EOF
chmod +x "$STUB_BIN/python3"
: >"$FAKE_PLUGIN/python/cli.py"

assert_delegation() {
  local label="$1" wrapper="$2" cli_path="$3" verb="$4" plugin_root="$5"
  shift 5
  local out_file="$TMP/${label// /_}.stdout" err_file="$TMP/${label// /_}.stderr" rc
  set +e
  if [ -n "$plugin_root" ]; then
    PATH="$STUB_BIN:$PATH" CLAUDE_PLUGIN_ROOT="$plugin_root" bash "$wrapper" "$@" >"$out_file" 2>"$err_file"
  else
    env -u CLAUDE_PLUGIN_ROOT PATH="$STUB_BIN:$PATH" bash "$wrapper" "$@" >"$out_file" 2>"$err_file"
  fi
  rc=$?
  set -e
  [ "$rc" -eq 7 ] || { echo "FAIL: $label exit (want 7 got $rc)" >&2; exit 1; }
  printf 'stdout-marker\n' | cmp -s - "$out_file" || { echo "FAIL: $label stdout" >&2; exit 1; }
  printf 'stderr-marker\n' | cmp -s - "$err_file" || { echo "FAIL: $label stderr" >&2; exit 1; }
  python3 - "$ARGV_LOG" "$cli_path" "oos" "$verb" "$@" <<'PY'
import sys
raw = open(sys.argv[1], "rb").read().split(b"\0")
got = [p.decode() for p in raw if p]
want = sys.argv[2:]
if got != want:
    raise SystemExit(f"argv mismatch:\n got={got!r}\nwant={want!r}")
PY
  echo "PASS: $label"
}

assert_delegation "gate CLAUDE_PLUGIN_ROOT override" "$GATE" \
  "$FAKE_PLUGIN/python/cli.py" "disposition-gate" "$FAKE_PLUGIN" --fork-mode
assert_delegation "gate repo-root fallback" "$GATE" \
  "$REPO_ROOT/python/cli.py" "disposition-gate" "" \
  --accepted-files "a.md" --commit-range "HEAD"
assert_delegation "checkpoint CLAUDE_PLUGIN_ROOT override" "$CHECKPOINT" \
  "$FAKE_PLUGIN/python/cli.py" "disposition-checkpoint" "$FAKE_PLUGIN" \
  --implement-tmpdir "$TMP/impl"
assert_delegation "checkpoint repo-root fallback" "$CHECKPOINT" \
  "$REPO_ROOT/python/cli.py" "disposition-checkpoint" "" \
  --implement-tmpdir "$TMP/impl" --design-tmpdir "$TMP/design"

echo "All delegation smoke assertions passed."
