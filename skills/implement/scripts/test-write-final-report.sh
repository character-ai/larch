#!/usr/bin/env bash
# Delegation smoke for write-final-report.sh.
# Behavioral coverage lives in crates/larch-cli/tests/final_report.rs.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/write-final-report.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-write-final-report.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

write_cli() {
    local root=$1
    mkdir -p "$root/scripts"
    cat >"$root/scripts/larch.sh" <<'SH'
#!/usr/bin/env bash
{
  printf '{"program":'
  printf '%s' "$0" | jq -Rs .
  printf ',"argv":['
  first=1
  for arg in "$@"; do
    if [ "$first" -eq 1 ]; then first=0; else printf ','; fi
    printf '%s' "$arg" | jq -Rs .
  done
  printf ']}\n'
} >"$WFR_CAPTURE"
printf 'wrapper stdout\n'
printf 'wrapper stderr\n' >&2
exit 23
SH
    chmod +x "$root/scripts/larch.sh"
}

assert_case() {
    local helper=$1 root=$2 capture=$3 stdout=$4 stderr=$5 plugin_root=$2 rc
    local expected_bin got_prog
    if [ "$helper" = "$fallback/skills/implement/scripts/write-final-report.sh" ]; then plugin_root=""; fi
    set +e
    CLAUDE_PLUGIN_ROOT="$plugin_root" WFR_CAPTURE="$capture" \
        "$helper" --implement-tmpdir "$TMP_ROOT/impl" --comment-only >"$stdout" 2>"$stderr"
    rc=$?
    set -e
    [ "$rc" -eq 23 ] && [ "$(cat "$stdout")" = 'wrapper stdout' ] && [ "$(cat "$stderr")" = 'wrapper stderr' ]
    expected_bin="$(cd "$root/scripts" && pwd -P)/larch.sh"
    got_prog="$(jq -r '.program' "$capture")"
    got_prog="$(cd "$(dirname "$got_prog")" && pwd -P)/$(basename "$got_prog")"
    [ "$got_prog" = "$expected_bin" ] || {
        printf 'unexpected program: %s\n' "$got_prog" >&2
        exit 1
    }
    jq -e --arg impl "$TMP_ROOT/impl" '
      .argv == ["final-report","write","--implement-tmpdir",$impl,"--comment-only"]
    ' "$capture" >/dev/null || {
        printf 'unexpected argv: %s\n' "$(jq -c . "$capture")" >&2
        exit 1
    }
}

fallback="$TMP_ROOT/fallback"; mkdir -p "$fallback/skills/implement/scripts"
cp "$HELPER" "$fallback/skills/implement/scripts/write-final-report.sh"
chmod +x "$fallback/skills/implement/scripts/write-final-report.sh"
write_cli "$fallback"
assert_case "$fallback/skills/implement/scripts/write-final-report.sh" "$fallback" "$TMP_ROOT/fallback.json" "$TMP_ROOT/fallback.out" "$TMP_ROOT/fallback.err"

override="$TMP_ROOT/override"; write_cli "$override"
assert_case "$HELPER" "$override" "$TMP_ROOT/override.json" "$TMP_ROOT/override.out" "$TMP_ROOT/override.err"
printf 'PASS: write-final-report wrapper delegation\n'
