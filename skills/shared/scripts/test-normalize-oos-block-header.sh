#!/usr/bin/env bash
# test-normalize-oos-block-header.sh — regression harness for normalize-oos-block-header.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SCRIPT="$SCRIPT_DIR/normalize-oos-block-header.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-normalize-oos-block-header.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

FAIL=0
assert_eq() {
    local name="$1" got="$2" want="$3"
    if [[ "$got" == "$want" ]]; then
        printf '  ok   %s\n' "$name"
    else
        printf '  FAIL %s — got %q want %q\n' "$name" "$got" "$want"
        FAIL=1
    fi
}

echo "# Case: tagged legacy FINDING header → OOS_1, title preserved"
printf '### FINDING_3: [OUT_OF_SCOPE] Timing harness coverage\n- **Description**: body.\n' > "$TMP/a.md"
got=$("$SCRIPT" --seq 1 --block-file "$TMP/a.md" | head -n1)
assert_eq "FINDING_3 [OUT_OF_SCOPE] → OOS_1" "$got" "### OOS_1: [OUT_OF_SCOPE] Timing harness coverage"

echo "# Case: bare scope-drift FINDING header → OOS_2"
printf '### FINDING_2: Drifted finding\n- **Concern**: drift.\n' > "$TMP/b.md"
got=$("$SCRIPT" --seq 2 --block-file "$TMP/b.md" | head -n1)
assert_eq "bare FINDING_2 → OOS_2" "$got" "### OOS_2: Drifted finding"

echo "# Case: existing OOS_9 renumbered → OOS_3"
printf '### OOS_9: Already canonical id\n' > "$TMP/c.md"
got=$("$SCRIPT" --seq 3 --block-file "$TMP/c.md" | head -n1)
assert_eq "OOS_9 → OOS_3 renumber" "$got" "### OOS_3: Already canonical id"

echo "# Case: NR==1 guard — line 2 ### FINDING_2: heading unchanged"
printf '### FINDING_1: [OUT_OF_SCOPE] Outer\n### FINDING_2: cited heading in body\n- tail\n' > "$TMP/d.md"
"$SCRIPT" --seq 4 --block-file "$TMP/d.md" > "$TMP/d.out"
got=$(sed -n '1p' "$TMP/d.out")
assert_eq "line 1 normalized" "$got" "### OOS_4: [OUT_OF_SCOPE] Outer"
got=$(sed -n '2p' "$TMP/d.out")
assert_eq "line 2 cited FINDING heading preserved" "$got" "### FINDING_2: cited heading in body"
got=$(sed -n '3p' "$TMP/d.out")
assert_eq "line 3 tail preserved" "$got" "- tail"

echo "# Case: stdin mode"
got=$(printf '### FINDING_7: [OOS] Stdin block\n' | "$SCRIPT" --seq 5 | head -n1)
assert_eq "stdin block normalized" "$got" "### OOS_5: [OOS] Stdin block"

echo "# Case: line 1 without id token passes through unchanged"
printf 'prose line, not a header\n' > "$TMP/e.md"
got=$("$SCRIPT" --seq 6 --block-file "$TMP/e.md" | head -n1)
assert_eq "non-header line 1 untouched" "$got" "prose line, not a header"

echo "# Case: argument validation exits 2"
set +e
"$SCRIPT" --seq notanumber --block-file "$TMP/a.md" >/dev/null 2>&1
rc=$?
set -e
assert_eq "--seq non-numeric exits 2" "$rc" "2"
set +e
"$SCRIPT" --block-file "$TMP/a.md" >/dev/null 2>&1
rc=$?
set -e
assert_eq "missing --seq exits 2" "$rc" "2"
set +e
"$SCRIPT" --seq 1 --block-file "$TMP/nope.md" >/dev/null 2>&1
rc=$?
set -e
assert_eq "missing block file exits 2" "$rc" "2"

if [[ "$FAIL" -ne 0 ]]; then
    echo "FAILURES detected" >&2
    exit 1
fi
echo "All assertions passed."
