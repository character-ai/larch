#!/usr/bin/env bash
# Delegation smoke for step-7a.sh.
# Behavioral coverage lives in crates/larch-cli/src/implement_review_commands.rs.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/step-7a.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-step-7a.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

write_runtime() {
    local root=$1
    mkdir -p "$root/scripts"
    cat >"$root/scripts/larch.sh" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$0" >"$STEP7A_CAPTURE"
printf '%s\n' "$@" >>"$STEP7A_CAPTURE"
printf 'wrapper stdout\n'
printf 'wrapper stderr\n' >&2
exit 23
SH
    chmod +x "$root/scripts/larch.sh"
}

assert_case() {
    local helper=$1 root=$2 capture=$3 stdout=$4 stderr=$5 plugin_root=$2 rc
    local expected_bin got_bin i expected_line
    if [ "$helper" = "$fallback/skills/implement/scripts/step-7a.sh" ]; then plugin_root=""; fi
    set +e
    CLAUDE_PLUGIN_ROOT="$plugin_root" STEP7A_CAPTURE="$capture" "$helper" --label 'two words' >"$stdout" 2>"$stderr"
    rc=$?
    set -e
    [ "$rc" -eq 23 ] && [ "$(cat "$stdout")" = 'wrapper stdout' ] && [ "$(cat "$stderr")" = 'wrapper stderr' ]
    expected_bin="$(cd "$root/scripts" && pwd -P)/larch.sh"
    got_bin="$(cd "$(dirname "$(sed -n '1p' "$capture")")" && pwd -P)/$(basename "$(sed -n '1p' "$capture")")"
    [ "$got_bin" = "$expected_bin" ] || {
        printf 'unexpected entrypoint: %s\n' "$(sed -n '1p' "$capture")" >&2
        exit 1
    }
    i=0
    for expected_line in implement step-7a --label 'two words'; do
        i=$((i + 1))
        [ "$(sed -n "$((i + 1))p" "$capture")" = "$expected_line" ] || {
            printf 'unexpected delegation line %s: %s\n' "$i" "$(sed -n "$((i + 1))p" "$capture")" >&2
            exit 1
        }
    done
    [ "$(wc -l < "$capture" | tr -d ' ')" = "5" ] || {
        printf 'unexpected delegation arity\n' >&2
        exit 1
    }
}

fallback="$TMP_ROOT/fallback"; mkdir -p "$fallback/skills/implement/scripts"
cp "$HELPER" "$fallback/skills/implement/scripts/step-7a.sh"
chmod +x "$fallback/skills/implement/scripts/step-7a.sh"
write_runtime "$fallback"
assert_case "$fallback/skills/implement/scripts/step-7a.sh" "$fallback" "$TMP_ROOT/fallback.txt" "$TMP_ROOT/fallback.out" "$TMP_ROOT/fallback.err"

override="$TMP_ROOT/override"; write_runtime "$override"
assert_case "$HELPER" "$override" "$TMP_ROOT/override.txt" "$TMP_ROOT/override.out" "$TMP_ROOT/override.err"
printf 'PASS: step-7a wrapper delegation\n'
