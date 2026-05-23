#!/usr/bin/env bash
# Offline harness for file-design-oos.sh
set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUBJECT="$SCRIPT_DIR/file-design-oos.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CAP_SH="$REPO_ROOT/skills/implement/scripts/oos-issue-cap.sh"

PASS=0
FAIL=0

fail() {
  FAIL=$((FAIL + 1))
  echo "  FAIL: $*" >&2
}

pass() {
  PASS=$((PASS + 1))
  echo "  PASS: $*"
}

assert_rc() {
  local name="$1" want="$2" got="$3"
  if [[ "$got" != "$want" ]]; then
    fail "$name — expected exit $want, got $got"
    return 1
  fi
  pass "$name"
}

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-file-design-oos.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

# --- 1: empty accepted -> skip-no-items ---
mkdir -p "$TMP/c1"
: >"$TMP/c1/oos-accepted-design.md"
set +e
out=$(bash "$SUBJECT" prepare --design-tmpdir "$TMP/c1" 2>/dev/null)
rc=$?
set -e
assert_rc "empty accepted" 0 "$rc"
grep -q '^FILE_DESIGN_OOS_STATUS=skip-no-items$' <<<"$out" || fail "case1 missing skip-no-items"

# --- 2: one non-security block -> ready + annotate ---
mkdir -p "$TMP/c2"
cat >"$TMP/c2/oos-accepted-design.md" <<'EOF'
### OOS_1: Widget
- **Description**: something wrong
- **Reviewer**: r1
- **Vote tally**: YES=2 NO=0 EXONERATE=0
- **Phase**: design
EOF
set +e
out2=$(bash "$SUBJECT" prepare --design-tmpdir "$TMP/c2" 2>/dev/null)
rc=$?
set -e
assert_rc "one block prepare" 0 "$rc"
grep -q '^FILE_DESIGN_OOS_STATUS=ready$' <<<"$out2" || fail "case2 not ready"
grep -q '^FILE_DESIGN_OOS_COMBINED=' <<<"$out2" || fail "case2 missing combined path"
test -f "$TMP/c2/oos-combined.md" || fail "case2 combined missing"
grep -q '^### OOS_1:' "$TMP/c2/oos-combined.md" || fail "case2 combined content"

cat >"$TMP/c2/issue.stdout" <<'EOF'
ISSUES_CREATED=1
ISSUES_FAILED=0
ISSUES_DEDUPLICATED=0
ISSUE_1_URL=https://github.com/example/larch/issues/42
EOF
set +e
bash "$SUBJECT" annotate --design-tmpdir "$TMP/c2" --issue-stdout-file "$TMP/c2/issue.stdout"
rc=$?
set -e
assert_rc "annotate success" 0 "$rc"
grep -q 'Filed URL.*issues/42' "$TMP/c2/oos-accepted-design.md" || fail "case2 missing Filed URL in accepted"
grep -q 'issues/42' "$TMP/c2/oos-issues-created.md" || fail "case2 sentinel missing url"

# --- 3: all security -> skip-all-security ---
mkdir -p "$TMP/c3"
cat >"$TMP/c3/oos-accepted-design.md" <<'EOF'
### OOS_1: Secret
- **focus-area**: security
- **Phase**: design
EOF
set +e
out3=$(bash "$SUBJECT" prepare --design-tmpdir "$TMP/c3" 2>/dev/null)
rc=$?
set -e
assert_rc "all security" 0 "$rc"
grep -q '^FILE_DESIGN_OOS_STATUS=skip-all-security$' <<<"$out3" || fail "case3 not skip-all-security"

# --- 4: oos-issue-cap rejects non-OOS-shaped batch (sanity for prepare dependency) ---
mkdir -p "$TMP/c4"
cat >"$TMP/c4/bad-combined.md" <<'EOF'
### Hello: not oos
body
EOF
set +e
bash "$CAP_SH" --input-file "$TMP/c4/bad-combined.md" --output "$TMP/c4/out.md" >/dev/null 2>&1
rc=$?
set -e
assert_rc "oos-issue-cap rejects generic heading" 1 "$rc"

# --- 5: deps graceful-degrade (empty TSV path) still yields ready ---
mkdir -p "$TMP/c5"
cat >"$TMP/c5/oos-accepted-design.md" <<'EOF'
### OOS_1: A
- **Description**: plain text only
- **Phase**: design
EOF
set +e
out5=$(bash "$SUBJECT" prepare --design-tmpdir "$TMP/c5" 2>/dev/null)
rc=$?
set -e
assert_rc "deps degrade still ready" 0 "$rc"
grep -q '^FILE_DESIGN_OOS_STATUS=ready$' <<<"$out5" || fail "case5 not ready"
grep -q '^FILE_DESIGN_OOS_DEPS_AVAILABLE=false$' <<<"$out5" || fail "case5 expected deps degrade false"

# --- 6: sentinel idempotency ---
mkdir -p "$TMP/c6"
printf 'https://github.com/example/larch/issues/9\n' >"$TMP/c6/oos-issues-created.md"
printf 'x' >"$TMP/c6/oos-accepted-design.md"
set +e
out6=$(bash "$SUBJECT" prepare --design-tmpdir "$TMP/c6" 2>/dev/null)
rc=$?
set -e
assert_rc "sentinel skip" 0 "$rc"
grep -q '^FILE_DESIGN_OOS_STATUS=skip-sentinel$' <<<"$out6" || fail "case6 not skip-sentinel"

# --- 7: partial /issue failure ---
mkdir -p "$TMP/c7"
cat >"$TMP/c7/oos-accepted-design.md" <<'EOF'
### OOS_1: A
- **Description**: a
- **Phase**: design
EOF
# Rebuild combined manually for annotate-only check
grep '^###' "$TMP/c7/oos-accepted-design.md" >/dev/null
cp "$TMP/c7/oos-accepted-design.md" "$TMP/c7/oos-combined.md"
printf '1\n' >"$TMP/c7/oos-design-filing-order.txt"
cat >"$TMP/c7/issue.stdout" <<'EOF'
ISSUES_CREATED=0
ISSUES_FAILED=1
ISSUES_DEDUPLICATED=0
ISSUE_1_FAILED=true
EOF
set +e
bash "$SUBJECT" annotate --design-tmpdir "$TMP/c7" --issue-stdout-file "$TMP/c7/issue.stdout"
rc=$?
set -e
assert_rc "annotate partial failure" 1 "$rc"

if [[ "$FAIL" -ne 0 ]]; then
  echo "$FAIL case(s) failed, $PASS passed" >&2
  exit 1
fi
echo "All $PASS cases passed."
