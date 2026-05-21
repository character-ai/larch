#!/usr/bin/env bash
# Regression harness for oos-disposition-gate.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GATE="$SCRIPT_DIR/oos-disposition-gate.sh"

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
  if [ "$got" != "$want" ]; then
    fail "$name — expected exit $want, got $got"
    return 1
  fi
  pass "$name"
}

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-oos-disposition-gate.XXXXXX")
GIT_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-oos-gate-git.XXXXXX")
ORPHAN_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-oos-gate-orphan.XXXXXX")
trap 'rm -rf "$TMP" "$GIT_TMP" "$ORPHAN_TMP"' EXIT

# --- Isolated repo: one commit, no Inline-triage (for fail + controlled ranges) ---
(
  cd "$GIT_TMP"
  git init -q
  git config user.email test@test
  git config user.name test
  echo base >base.txt
  git add base.txt
  git commit -q -m "init only"
  echo feat >feat.txt
  git add feat.txt
  git commit -q -m "$(printf 'second\n\nInline-triage rule 1: a\nInline-triage rule 2: b')"
)

# --- Case: fork-mode skips (no required args needed) ---
set +e
bash "$GATE" --fork-mode >/dev/null 2>&1
rc=$?
set -e
assert_rc "fork-mode skips without full args" 0 "$rc"

# --- Case: repo-unavailable skips ---
set +e
bash "$GATE" --repo-unavailable >/dev/null 2>&1
rc=$?
set -e
assert_rc "repo-unavailable skips" 0 "$rc"

# --- Case: bad args (missing --commit-range) ---
set +e
bash "$GATE" \
  --accepted-files "$TMP/a.md" \
  --filed-urls-file "$TMP/urls.md" >/dev/null 2>&1
rc=$?
set -e
assert_rc "missing --commit-range is exit 2" 2 "$rc"

# --- Case: empty accepted files + empty urls passes ---
: >"$TMP/empty-urls.md"
set +e
(
  cd "$GIT_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/missing1.md,$TMP/missing2.md" \
    --filed-urls-file "$TMP/empty-urls.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "no OOS blocks passes" 0 "$rc"

# --- Case: non-security OOS + filed URL passes ---
cat >"$TMP/acc.md" <<'EOF'
### OOS_1: Widget
- **Description**: bug
- **Phase**: implement
EOF
cat >"$TMP/filed.md" <<'EOF'
Created https://github.com/example/larch/issues/99
EOF
set +e
(
  cd "$GIT_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/acc.md" \
    --filed-urls-file "$TMP/filed.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "non-security OOS with filed URL passes" 0 "$rc"

# --- Case: security-routed block excluded from obligation set ---
cat >"$TMP/sec.md" <<'EOF'
### OOS_1: Secret thing
- **Description**: focus-area = security issue
- **Phase**: implement
EOF
set +e
(
  cd "$GIT_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/sec.md" \
    --filed-urls-file "$TMP/empty-urls.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "security-only accepted block passes without URLs" 0 "$rc"

# --- Case: non-security OOS + no URLs + no inline fails (isolated repo) ---
cat >"$TMP/bad.md" <<'EOF'
### OOS_1: Orphan
- **Description**: no disposition
- **Phase**: implement
EOF
(
  cd "$ORPHAN_TMP"
  git init -q
  git config user.email test@test
  git config user.name test
  echo x >x.txt
  git add x.txt
  git commit -q -m "only commit without inline triage"
)
set +e
(
  cd "$ORPHAN_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/bad.md" \
    --filed-urls-file "$TMP/empty-urls.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "non-security OOS without disposition fails" 1 "$rc"

# --- Case: two OOS blocks + two inline lines on commit range ---
cat >"$TMP/two.md" <<'EOF'
### OOS_1: A
- **Description**: x
### OOS_2: B
- **Description**: y
EOF
set +e
(
  cd "$GIT_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/two.md" \
    --filed-urls-file "$TMP/empty-urls.md" \
    --commit-range "HEAD~1..HEAD" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "two OOS blocks satisfied by two inline-triage lines" 0 "$rc"

# --- Case: combined batch: two OOS one URL ---
cat >"$TMP/comb.md" <<'EOF'
### OOS_1: One
- **Description**: a
### OOS_2: Two
- **Description**: b
EOF
cat >"$TMP/one-url.md" <<'EOF'
https://github.com/example/larch/issues/1
EOF
set +e
(
  cd "$GIT_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/comb.md" \
    --filed-urls-file "$TMP/one-url.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "two OOS entries + single filed URL passes" 0 "$rc"

if [ "$FAIL" -ne 0 ]; then
  echo "$FAIL case(s) failed, $PASS passed" >&2
  exit 1
fi
echo "All $PASS cases passed."
