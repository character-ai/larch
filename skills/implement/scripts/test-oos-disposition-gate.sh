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
    local expected_bin got_bin line idx
    set +e
    CLAUDE_PLUGIN_ROOT="$plugin_root" OOS_CAPTURE="$capture" "$helper" "$@" >"$out" 2>"$err"
    rc=$?
    set -e
    [ "$rc" -eq 23 ] || { echo "FAIL: $label exit (want 23 got $rc)" >&2; exit 1; }
    [ "$(cat "$out")" = 'wrapper stdout' ] || { echo "FAIL: $label stdout" >&2; exit 1; }
    [ "$(cat "$err")" = 'wrapper stderr' ] || { echo "FAIL: $label stderr" >&2; exit 1; }
    expected_bin="$(cd "$root/scripts" && pwd -P)/larch.sh"
    got_bin="$(cd "$(dirname "$(sed -n '1p' "$capture")")" && pwd -P)/$(basename "$(sed -n '1p' "$capture")")"
    [ "$got_bin" = "$expected_bin" ] || {
        printf 'FAIL: %s unexpected entrypoint: %s\n' "$label" "$(sed -n '1p' "$capture")" >&2
        exit 1
    }
    [ "$(sed -n '2p' "$capture")" = "oos" ] || {
        printf 'FAIL: %s unexpected domain\n' "$label" >&2
        exit 1
    }
    [ "$(sed -n '3p' "$capture")" = "$verb" ] || {
        printf 'FAIL: %s unexpected verb\n' "$label" >&2
        exit 1
    }
    idx=3
    for line in "$@"; do
        idx=$((idx + 1))
        [ "$(sed -n "${idx}p" "$capture")" = "$line" ] || {
            printf 'FAIL: %s unexpected arg at line %s\n' "$label" "$idx" >&2
            exit 1
        }
    done
    [ "$(wc -l < "$capture" | tr -d ' ')" = "$idx" ] || {
        printf 'FAIL: %s unexpected arity\n' "$label" >&2
        exit 1
    }
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
