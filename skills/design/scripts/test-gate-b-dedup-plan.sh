#!/usr/bin/env bash
# Offline harness for gate-b-dedup-plan.sh (issue #3175).

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
SUBJECT="$SCRIPT_DIR/gate-b-dedup-plan.sh"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-gate-b-dedup-test.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

write_plan() {
    local dir="$1"
    mkdir -p "$dir"
    cat >"$dir/plan.txt"
}

# --- snapshot writes keys and values ---
d="$TMPROOT/snapshot"
write_plan "$d" <<'EOF'
body
diff_added: 100
diff_deleted: 50
mechanical_churn: true
diff_lines: 200
EOF
"$SUBJECT" --design-tmpdir "$d" --snapshot-trailers
[[ -f "$d/.gate-b-optional-trailer-keys" ]] || fail "snapshot missing keys file"
grep -qx diff_added "$d/.gate-b-optional-trailer-keys" || fail "snapshot missing diff_added key"
[[ -f "$d/.gate-b-optional-trailer-keys.values" ]] || fail "snapshot missing values file"
grep -q '^diff_added=100$' "$d/.gate-b-optional-trailer-keys.values" || fail "snapshot missing diff_added value"

# --- dedup without prior snapshot fails closed ---
d="$TMPROOT/dedup-no-snapshot"
write_plan "$d" <<'EOF'
body
diff_lines: 1
EOF
set +e
"$SUBJECT" --design-tmpdir "$d" --dedup 2>/dev/null
rc=$?
set -e
[[ "$rc" == 3 ]] || fail "--dedup without snapshot should exit 3, got $rc"

# --- dedup preserves trailers ---
d="$TMPROOT/dedup-preserve"
write_plan "$d" <<'EOF'
body
body
diff_added: 100
diff_deleted: 50
mechanical_churn: true
diff_lines: 200
EOF
"$SUBJECT" --design-tmpdir "$d" --snapshot-trailers
out=$("$SUBJECT" --design-tmpdir "$d" --dedup)
printf '%s\n' "$out" | grep -q 'dedup-sweep: removed 1 duplicate' || fail "dedup should remove one duplicate body line"
grep -q '^diff_added: 100$' "$d/plan.txt" || fail "dedup must preserve diff_added trailer"
grep -q '^mechanical_churn: true$' "$d/plan.txt" || fail "dedup must preserve mechanical_churn trailer"

# --- dedup rejects newly introduced optional trailers when snapshot empty ---
d="$TMPROOT/no-new-trailers"
write_plan "$d" <<'EOF'
line
line
diff_lines: 10
EOF
"$SUBJECT" --design-tmpdir "$d" --snapshot-trailers
printf 'line\nline\nmechanical_churn: true\ndiff_lines: 10\n' >"$d/plan.txt"
set +e
"$SUBJECT" --design-tmpdir "$d" --dedup 2>/dev/null
rc=$?
set -e
[[ "$rc" == 1 ]] || fail "dedup should reject newly introduced optional trailers, got rc=$rc"

# --- dedup rejects trailer value change ---
d="$TMPROOT/value-change"
write_plan "$d" <<'EOF'
body
diff_added: 100
diff_lines: 200
EOF
"$SUBJECT" --design-tmpdir "$d" --snapshot-trailers
printf 'body\ndiff_added: 999\ndiff_lines: 200\n' >"$d/plan.txt"
set +e
"$SUBJECT" --design-tmpdir "$d" --dedup 2>/dev/null
rc=$?
set -e
[[ "$rc" == 1 ]] || fail "dedup should reject trailer value change, got rc=$rc"
grep -q '^diff_added: 999$' "$d/plan.txt" || fail "value-change failure should leave revised plan for operator rework"

echo "PASS: test-gate-b-dedup-plan.sh"
