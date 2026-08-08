#!/usr/bin/env bash
# Delegation smoke for oos-disposition-gate.sh and oos-disposition-checkpoint.sh.
# Behavioral coverage lives in crates/larch-cli/src/oos_commands.rs.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-oos-disposition-gate.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

write_runtime() {
    local root=$1
    mkdir -p "$root/scripts"
    cat >"$root/scripts/larch.sh" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$0" >"$OOS_CAPTURE"
printf '%s\n' "$@" >>"$OOS_CAPTURE"
printf 'wrapper stdout\n'
printf 'wrapper stderr\n' >&2
exit 23
SH
    chmod +x "$root/scripts/larch.sh"
}

assert_case() {
    local label=$1 helper=$2 root=$3 plugin_root=$4 verb=$5
    shift 5
    local capture="$TMP_ROOT/$label.txt" out="$TMP_ROOT/$label.out" err="$TMP_ROOT/$label.err" rc
    set +e
    CLAUDE_PLUGIN_ROOT="$plugin_root" OOS_CAPTURE="$capture" "$helper" "$@" >"$out" 2>"$err"
    rc=$?
    set -e
    [ "$rc" -eq 23 ] || { echo "FAIL: $label exit (want 23 got $rc)" >&2; exit 1; }
    [ "$(cat "$out")" = 'wrapper stdout' ] || { echo "FAIL: $label stdout" >&2; exit 1; }
    [ "$(cat "$err")" = 'wrapper stderr' ] || { echo "FAIL: $label stderr" >&2; exit 1; }
    python3 - "$capture" "$root" "$verb" "$@" <<'PY'
import sys
from pathlib import Path

rows = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
expected = ["oos", sys.argv[3], *sys.argv[4:]]
if Path(rows[0]).resolve() != (Path(sys.argv[2]) / "scripts" / "larch.sh").resolve():
    raise SystemExit(f"unexpected entrypoint: {rows[0]!r}")
if rows[1:] != expected:
    raise SystemExit(f"unexpected delegation: {rows[1:]!r} != {expected!r}")
PY
    printf 'PASS: %s\n' "$label"
}

# Repo-root fallback: the helper resolves the runtime three levels up from its
# own directory, so the copy under a throwaway root must reach that root's
# entrypoint with no CLAUDE_PLUGIN_ROOT set.
fallback="$TMP_ROOT/fallback"
mkdir -p "$fallback/skills/implement/scripts"
for name in oos-disposition-gate oos-disposition-checkpoint; do
    cp "$SCRIPT_DIR/$name.sh" "$fallback/skills/implement/scripts/$name.sh"
    chmod +x "$fallback/skills/implement/scripts/$name.sh"
done
write_runtime "$fallback"
assert_case "gate-fallback" "$fallback/skills/implement/scripts/oos-disposition-gate.sh" \
    "$fallback" "" "disposition-gate" --accepted-files "a.md" --commit-range "HEAD"
assert_case "checkpoint-fallback" "$fallback/skills/implement/scripts/oos-disposition-checkpoint.sh" \
    "$fallback" "" "disposition-checkpoint" --implement-tmpdir "$TMP_ROOT/impl"

override="$TMP_ROOT/override"
write_runtime "$override"
assert_case "gate-override" "$SCRIPT_DIR/oos-disposition-gate.sh" \
    "$override" "$override" "disposition-gate" --fork-mode
assert_case "checkpoint-override" "$SCRIPT_DIR/oos-disposition-checkpoint.sh" \
    "$override" "$override" "disposition-checkpoint" \
    --implement-tmpdir "$TMP_ROOT/impl" --design-tmpdir "$TMP_ROOT/design"

echo "All delegation smoke assertions passed."
