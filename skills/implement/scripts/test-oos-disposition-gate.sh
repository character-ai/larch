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

: >"$TMP/empty-urls.md"

# --- Case: accepted path exists but is not a regular file (exit 2) ---
mkdir -p "$TMP/not-a-regular-acc-path"
set +e
(
  cd "$GIT_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/not-a-regular-acc-path" \
    --filed-urls-file "$TMP/empty-urls.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "accepted path exists but is not a regular file is exit 2" 2 "$rc"

# --- Case: ndjson lists filed URLs but no accepted-files path exists (exit 2) ---
cat >"$TMP/orphan-ndjson-urls.ndjson" <<'EOF'
{"body":"Created https://github.com/example/larch/issues/404\n"}
EOF
set +e
(
  cd "$GIT_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/does-not-exist-acc-a.md,$TMP/does-not-exist-acc-b.md" \
    --filed-urls-file "$TMP/empty-urls.md" \
    --oos-issues-ndjson "$TMP/orphan-ndjson-urls.ndjson" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "filed URLs in oos-issues.ndjson without any accepted file path is exit 2" 2 "$rc"

# --- Case: empty accepted files + empty urls passes ---
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
- **focus-area**: security
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

# --- Case: security-hardening focus-area is security-routed (case / compound token) ---
cat >"$TMP/sec-hard.md" <<'EOF'
### OOS_1: Hardening item
- **focus-area**: Security-Hardening
- **Phase**: implement
EOF
set +e
(
  cd "$GIT_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/sec-hard.md" \
    --filed-urls-file "$TMP/empty-urls.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "security-hardening focus-area passes without URLs" 0 "$rc"

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

# --- Case: invalid commit-range is exit 2 ---
set +e
(
  cd "$ORPHAN_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/bad.md" \
    --filed-urls-file "$TMP/empty-urls.md" \
    --commit-range 'HEAD~99..HEAD' >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "invalid commit-range yields exit 2" 2 "$rc"

# --- Case: prose 'focus-area = security' in Description is NOT security-routed ---
cat >"$TMP/false-sec.md" <<'EOF'
### OOS_1: Doc mention
- **Description**: focus-area = security issue (prose only)
- **Phase**: implement
EOF
set +e
(
  cd "$ORPHAN_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/false-sec.md" \
    --filed-urls-file "$TMP/empty-urls.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "description prose mentioning focus-area=security still requires disposition" 1 "$rc"

# --- Case: explicit rejection markers in oos-issues.ndjson satisfy disposition ---
cat >"$TMP/rej-acc.md" <<'EOF'
### OOS_1: Out of scope item
- **Phase**: implement
EOF
cat >"$TMP/rej.ndjson" <<'EOF'
{"phase":"code-review","step":"9a.1","category":"OOS","body":"## Rejected / Out-of-Scope Observations (not filed)\n\n### OOS_1: Out of scope item\nPanel rejected.\n"}
EOF
set +e
(
  cd "$ORPHAN_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/rej-acc.md" \
    --filed-urls-file "$TMP/empty-urls.md" \
    --oos-issues-ndjson "$TMP/rej.ndjson" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "rejected OOS markers in ndjson satisfy gate without URLs" 0 "$rc"

# --- Case: filed URLs only in NDJSON (union with empty oos-issues-created) ---
cat >"$TMP/ndjson-url-acc.md" <<'EOF'
### OOS_1: Tracked elsewhere
- **Phase**: implement
EOF
cat >"$TMP/ndjson-url-only.ndjson" <<'EOF'
{"phase":"code-review","step":"9a.1","category":"OOS","body":"Filed https://github.com/example/larch/issues/77 from batch.\n"}
EOF
set +e
(
  cd "$ORPHAN_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/ndjson-url-acc.md" \
    --filed-urls-file "$TMP/empty-urls.md" \
    --oos-issues-ndjson "$TMP/ndjson-url-only.ndjson" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "filed issue URL only in oos-issues ndjson passes via union" 0 "$rc"

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

# --- Case: off-host https://…/issues/<n> URL must not satisfy disposition ---
cat >"$TMP/offhost-acc.md" <<'EOF'
### OOS_1: Needs real GitHub filing
- **Phase**: implement
EOF
cat >"$TMP/offhost-url.md" <<'EOF'
Filed https://evil.example.com/org/repo/issues/999 for tracking.
EOF
set +e
(
  cd "$ORPHAN_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/offhost-acc.md" \
    --filed-urls-file "$TMP/offhost-url.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "off-host issues URL is not counted as filed (exit 1 disposition gap)" 1 "$rc"

# --- Case: two --filed-urls-file union satisfies two OOS blocks ---
cat >"$TMP/two-union.md" <<'EOF'
### OOS_1: A
- **Description**: x
- **Phase**: implement
### OOS_2: B
- **Description**: y
- **Phase**: implement
EOF
cat >"$TMP/url-a.md" <<'EOF'
https://github.com/example/larch/issues/1
EOF
cat >"$TMP/url-b.md" <<'EOF'
https://github.com/example/larch/issues/2
EOF
set +e
(
  cd "$GIT_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/two-union.md" \
    --filed-urls-file "$TMP/url-a.md" \
    --filed-urls-file "$TMP/url-b.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "two --filed-urls-file union passes for two OOS blocks" 0 "$rc"

if [ "$FAIL" -ne 0 ]; then
  echo "$FAIL case(s) failed, $PASS passed" >&2
  exit 1
fi
echo "All $PASS cases passed."
