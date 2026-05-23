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

# --- X1: cross-session cache recovers sentinel + annotates accepted md ---
H1="$TMP/home-x1"
mkdir -p "$H1/.cache/larch/design-oos-filed"
printf 'https://github.com/example/larch/issues/7001\n' >"$H1/.cache/larch/design-oos-filed/501.md"
mkdir -p "$TMP/x1"
: >"$TMP/x1/execution-issues.md"
cat >"$TMP/x1/oos-accepted-design.md" <<'EOF'
### OOS_1: Widget
- **Description**: something wrong
- **Reviewer**: r1
- **Vote tally**: YES=2 NO=0 EXONERATE=0
- **Phase**: design
EOF
set +e
out_x1=$(HOME="$H1" bash "$SUBJECT" prepare --design-tmpdir "$TMP/x1" --issue-number 501 2>/dev/null)
rc=$?
set -e
assert_rc "X1 cross-session cache recovery" 0 "$rc"
grep -q '^FILE_DESIGN_OOS_STATUS=skip-sentinel$' <<<"$out_x1" || fail "X1 not skip-sentinel"
grep -q 'Filed URL.*issues/7001' "$TMP/x1/oos-accepted-design.md" || fail "X1 missing recovered Filed URL"
test -f "$TMP/x1/oos-issues-created.md" || fail "X1 sentinel missing"
grep -q 'issues/7001' "$TMP/x1/oos-issues-created.md" || fail "X1 sentinel url missing"

# --- X2: in-session sentinel wins over cross-session cache ---
H2="$TMP/home-x2"
mkdir -p "$H2/.cache/larch/design-oos-filed"
printf 'https://github.com/example/larch/issues/9999\n' >"$H2/.cache/larch/design-oos-filed/502.md"
mkdir -p "$TMP/x2"
printf 'https://github.com/example/larch/issues/9\n' >"$TMP/x2/oos-issues-created.md"
printf 'unchanged-body\n' >"$TMP/x2/oos-accepted-design.md"
set +e
out_x2=$(HOME="$H2" bash "$SUBJECT" prepare --design-tmpdir "$TMP/x2" --issue-number 502 2>/dev/null)
rc=$?
set -e
assert_rc "X2 in-session sentinel precedence" 0 "$rc"
grep -q '^FILE_DESIGN_OOS_STATUS=skip-sentinel$' <<<"$out_x2" || fail "X2 not skip-sentinel"
grep -q '^unchanged-body$' "$TMP/x2/oos-accepted-design.md" || fail "X2 accepted md should not be rewritten via cache"

# --- X3: --clear-cross-session-cache deletes cache then annotate recreates it ---
H3="$TMP/home-x3"
mkdir -p "$H3/.cache/larch/design-oos-filed"
printf 'https://github.com/example/larch/issues/stale\n' >"$H3/.cache/larch/design-oos-filed/303.md"
mkdir -p "$TMP/x3"
: >"$TMP/x3/execution-issues.md"
cat >"$TMP/x3/oos-accepted-design.md" <<'EOF'
### OOS_1: Widget
- **Description**: something wrong
- **Reviewer**: r1
- **Vote tally**: YES=2 NO=0 EXONERATE=0
- **Phase**: design
EOF
set +e
out_x3a=$(HOME="$H3" bash "$SUBJECT" prepare --design-tmpdir "$TMP/x3" --issue-number 303 --clear-cross-session-cache 2>/dev/null)
rc=$?
set -e
assert_rc "X3 prepare after cache clear" 0 "$rc"
grep -q '^FILE_DESIGN_OOS_STATUS=ready$' <<<"$out_x3a" || fail "X3 not ready after clear"
test ! -f "$H3/.cache/larch/design-oos-filed/303.md" || fail "X3 cache file should be deleted"

cat >"$TMP/x3/issue.stdout" <<'EOF'
ISSUES_CREATED=1
ISSUES_FAILED=0
ISSUES_DEDUPLICATED=0
ISSUE_1_URL=https://github.com/example/larch/issues/30342
EOF
set +e
HOME="$H3" bash "$SUBJECT" annotate --design-tmpdir "$TMP/x3" --issue-stdout-file "$TMP/x3/issue.stdout" --issue-number 303
rc=$?
set -e
assert_rc "X3 annotate after clear" 0 "$rc"
test -f "$H3/.cache/larch/design-oos-filed/303.md" || fail "X3 cache not recreated"
grep -q 'issues/30342' "$H3/.cache/larch/design-oos-filed/303.md" || fail "X3 cache content wrong"

# --- X4: first cross-session write creates cache directory ---
H4="$TMP/home-x4"
mkdir -p "$TMP/x4"
: >"$TMP/x4/execution-issues.md"
cat >"$TMP/x4/oos-accepted-design.md" <<'EOF'
### OOS_1: Widget
- **Description**: something wrong
- **Reviewer**: r1
- **Vote tally**: YES=2 NO=0 EXONERATE=0
- **Phase**: design
EOF
set +e
out_x4=$(HOME="$H4" bash "$SUBJECT" prepare --design-tmpdir "$TMP/x4" --issue-number 404 2>/dev/null)
rc=$?
set -e
assert_rc "X4 prepare" 0 "$rc"
grep -q '^FILE_DESIGN_OOS_STATUS=ready$' <<<"$out_x4" || fail "X4 not ready"
cat >"$TMP/x4/issue.stdout" <<'EOF'
ISSUES_CREATED=1
ISSUES_FAILED=0
ISSUES_DEDUPLICATED=0
ISSUE_1_URL=https://github.com/example/larch/issues/40442
EOF
set +e
HOME="$H4" bash "$SUBJECT" annotate --design-tmpdir "$TMP/x4" --issue-stdout-file "$TMP/x4/issue.stdout" --issue-number 404
rc=$?
set -e
assert_rc "X4 annotate" 0 "$rc"
test -d "$H4/.cache/larch/design-oos-filed" || fail "X4 cache dir missing"
test -f "$H4/.cache/larch/design-oos-filed/404.md" || fail "X4 cache file missing"

# --- X5: unwritable cache directory logs warning; sentinel still written ---
H5="$TMP/home-x5"
mkdir -p "$H5/.cache/larch/design-oos-filed"
chmod a-w "$H5/.cache/larch/design-oos-filed"
mkdir -p "$TMP/x5"
: >"$TMP/x5/execution-issues.md"
cat >"$TMP/x5/oos-accepted-design.md" <<'EOF'
### OOS_1: Widget
- **Description**: something wrong
- **Reviewer**: r1
- **Vote tally**: YES=2 NO=0 EXONERATE=0
- **Phase**: design
EOF
set +e
out_x5=$(HOME="$H5" bash "$SUBJECT" prepare --design-tmpdir "$TMP/x5" --issue-number 505 2>/dev/null)
rc=$?
set -e
assert_rc "X5 prepare" 0 "$rc"
grep -q '^FILE_DESIGN_OOS_STATUS=ready$' <<<"$out_x5" || fail "X5 not ready"
cat >"$TMP/x5/issue.stdout" <<'EOF'
ISSUES_CREATED=1
ISSUES_FAILED=0
ISSUES_DEDUPLICATED=0
ISSUE_1_URL=https://github.com/example/larch/issues/50542
EOF
set +e
HOME="$H5" bash "$SUBJECT" annotate --design-tmpdir "$TMP/x5" --issue-stdout-file "$TMP/x5/issue.stdout" --issue-number 505
rc=$?
set -e
assert_rc "X5 annotate" 0 "$rc"
grep -q 'issues/50542' "$TMP/x5/oos-issues-created.md" || fail "X5 sentinel missing url"
grep -q 'file-design-oos' "$TMP/x5/execution-issues.md" || fail "X5 expected cache warning in execution-issues"
chmod u+w "$H5/.cache/larch/design-oos-filed" 2>/dev/null || true

if [[ "$FAIL" -ne 0 ]]; then
  echo "$FAIL case(s) failed, $PASS passed" >&2
  exit 1
fi
echo "All $PASS cases passed."
