#!/usr/bin/env bash
# Regression harness for oos-disposition-gate.sh and oos-disposition-checkpoint.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GATE="$SCRIPT_DIR/oos-disposition-gate.sh"
CHECKPOINT="$SCRIPT_DIR/oos-disposition-checkpoint.sh"

[ -x "$CHECKPOINT" ] || {
  echo "checkpoint not executable: $CHECKPOINT" >&2
  exit 1
}

[ -x "$GATE" ] || {
  echo "gate not executable: $GATE" >&2
  exit 1
}

PASS=0
FAIL=0
TMPDIRS=()

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

mkitmp() {
  local dir
  dir=$(mktemp -d "${TMPDIR:-/tmp}/oos-chk-impl.XXXXXX")
  TMPDIRS+=("$dir")
  : >"$dir/execution-issues.md"
  : >"$dir/oos-accepted-main-agent.md"
  : >"$dir/oos-accepted-review.md"
  : >"$dir/oos-issues-created.md"
  printf '%s\n' 'FORKED_TARGET=false' >"$dir/ship-pr-state.sh"
  printf '%s\n' 'REPO_UNAVAILABLE=false' >>"$dir/ship-pr-state.sh"
  mkdir -p "$dir/larch-logs/implement"
  printf '%s' "$dir"
}

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-oos-disposition-gate.XXXXXX")
GIT_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-oos-gate-git.XXXXXX")
ORPHAN_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-oos-gate-orphan.XXXXXX")
trap 'rm -rf "$TMP" "$GIT_TMP" "$ORPHAN_TMP" ${TMPDIRS[@]+"${TMPDIRS[@]}"}' EXIT

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

# --- Case: unbulleted focus-area field is security-routed (awk/python parity) ---
cat >"$TMP/sec-unbulleted.md" <<'EOF'
### OOS_1: Hardening item
focus-area = security-hardening
- **Phase**: implement
EOF
set +e
(
  cd "$GIT_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/sec-unbulleted.md" \
    --filed-urls-file "$TMP/empty-urls.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "unbulleted security focus-area passes without URLs" 0 "$rc"

py_count=$(
  PYTHONPATH="$SCRIPT_DIR/../../../python" \
    python3 -c 'from larch.issue import file_oos; import sys; print(file_oos.count_non_security((sys.argv[1],)))' \
    "$TMP/sec-unbulleted.md"
)
if [ "$py_count" = "0" ]; then
  pass "python non-security counter excludes unbulleted security focus-area"
else
  fail "python non-security counter expected 0 for unbulleted security focus-area, got $py_count"
fi

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

# --- Case: legacy tagged FINDING header without disposition fails (#3550) ---
cat >"$TMP/legacy.md" <<'EOF'
### FINDING_1: [OUT_OF_SCOPE] Legacy tagged header
- **Description**: no disposition
- **Phase**: implement
EOF
set +e
(
  cd "$ORPHAN_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/legacy.md" \
    --filed-urls-file "$TMP/empty-urls.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "legacy tagged FINDING header without disposition fails" 1 "$rc"

# --- Case: legacy tagged FINDING header with trailing tag also fails ---
cat >"$TMP/legacy-trailing.md" <<'EOF'
### FINDING_1: Legacy tagged header [OUT_OF_SCOPE]
- **Description**: no disposition
- **Phase**: implement
EOF
set +e
(
  cd "$ORPHAN_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/legacy-trailing.md" \
    --filed-urls-file "$TMP/empty-urls.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "legacy trailing-tag FINDING header without disposition fails" 1 "$rc"

# --- Case: legacy tagged FINDING header with filed URL passes (#3550) ---
set +e
(
  cd "$ORPHAN_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/legacy.md" \
    --filed-urls-file "$TMP/filed.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "legacy tagged FINDING header with filed URL passes" 0 "$rc"

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

# --- S1: strict counter ignores incidental GitHub URL in Description; loose still counts it ---
cat >"$TMP/s1-design.md" <<'EOF'
### OOS_1: Ref
- **Description**: see also https://github.com/owner/repo/issues/1234 for context
- **Phase**: implement
EOF
set +e
(
  cd "$ORPHAN_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/s1-design.md" \
    --filed-urls-strict-file "$TMP/s1-design.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "S1 strict-file mode ignores incidental issue URL (disposition gap exit 1)" 1 "$rc"

set +e
(
  cd "$ORPHAN_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/s1-design.md" \
    --filed-urls-file "$TMP/s1-design.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "S1 loose-file mode still counts incidental issue URL (pass)" 0 "$rc"

# --- S2: two dedicated Filed URL field lines counted via --filed-urls-strict-file ---
cat >"$TMP/s2-design.md" <<'EOF'
### OOS_1: A
- **Description**: a
- **Phase**: implement
- **Filed URL**: https://github.com/example/larch/issues/2700

### OOS_2: B
- **Description**: b
- **Phase**: implement
- **Filed URL**: https://github.com/example/larch/issues/2701
EOF
set +e
(
  cd "$ORPHAN_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/s2-design.md" \
    --filed-urls-strict-file "$TMP/s2-design.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "S2 two Filed URL field lines via strict-file pass" 0 "$rc"

# --- S2b: strict Filed URL line with trailing commentary after URL still counts ---
cat >"$TMP/s2b-design.md" <<'EOF'
### OOS_1: A
- **Description**: a
- **Phase**: implement
- **Filed URL**: https://github.com/example/larch/issues/2800 (see tracking issue)
EOF
set +e
(
  cd "$ORPHAN_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/s2b-design.md" \
    --filed-urls-strict-file "$TMP/s2b-design.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "S2b strict Filed URL with trailing note passes" 0 "$rc"

# --- S3: strict + loose union covers two non-security blocks ---
cat >"$TMP/s3-acc.md" <<'EOF'
### OOS_1: A
- **Phase**: implement
### OOS_2: B
- **Phase**: implement
EOF
cat >"$TMP/s3-strict.md" <<'EOF'
### OOS_9: X
- **Filed URL**: https://github.com/example/larch/issues/2702
EOF
cat >"$TMP/s3-loose.md" <<'EOF'
https://github.com/example/larch/issues/2703
EOF
set +e
(
  cd "$ORPHAN_TMP"
  bash "$GATE" \
    --accepted-files "$TMP/s3-acc.md" \
    --filed-urls-strict-file "$TMP/s3-strict.md" \
    --filed-urls-file "$TMP/s3-loose.md" \
    --commit-range HEAD >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "S3 strict plus loose union passes for two OOS blocks" 0 "$rc"

# --- Checkpoint harness (oos-disposition-checkpoint.sh) ---

# --- Case: checkpoint proceed with zero non-security OOS ---
_impl_zero=$(mkitmp)
set +e
(
  cd "$GIT_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_zero" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint proceed with empty accepted OOS" 0 "$rc"

# --- Case: checkpoint proceed with filed URL ---
_impl_filed=$(mkitmp)
cat >"$_impl_filed/oos-accepted-main-agent.md" <<'EOF'
### OOS_1: Widget
- **Description**: bug
- **Phase**: implement
EOF
cat >"$_impl_filed/oos-issues-created.md" <<'EOF'
Created https://github.com/example/larch/issues/99
EOF
printf 'run-filed\n' >"$_impl_filed/session-id"
mkdir -p "$_impl_filed/larch-logs/implement/run-filed"
: >"$_impl_filed/larch-logs/implement/run-filed/oos-issues.ndjson"
set +e
(
  cd "$GIT_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_filed" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint proceed with filed URL" 0 "$rc"

# --- Case: checkpoint disposition gap logs Tool Failures ---
_impl_gap=$(mkitmp)
cat >"$_impl_gap/oos-accepted-main-agent.md" <<'EOF'
### OOS_1: Orphan
- **Description**: no disposition
- **Phase**: implement
EOF
printf 'run-gap\n' >"$_impl_gap/session-id"
mkdir -p "$_impl_gap/larch-logs/implement/run-gap"
: >"$_impl_gap/larch-logs/implement/run-gap/oos-issues.ndjson"
set +e
(
  cd "$ORPHAN_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_gap" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint disposition gap exit 1" 1 "$rc"
if grep -Fq 'step-8-oos-checkpoint' "$_impl_gap/execution-issues.md" \
  && ! grep -Fq 'step-8-oos-checkpoint-validation' "$_impl_gap/execution-issues.md" \
  && grep -Fq 'oos-disposition-gate' "$_impl_gap/execution-issues.md" \
  && grep -Fq 'Tool Failures' "$_impl_gap/execution-issues.md" \
  && [ -s "$_impl_gap/oos-disposition-gate.stderr.log" ]; then
  pass "checkpoint disposition gap logs Tool Failures"
else
  fail "checkpoint disposition gap missing Tool Failures log entry or gate stderr"
fi

# --- Case: checkpoint legacy tagged FINDING disposition gap (#3550) ---
_impl_gap_legacy=$(mkitmp)
cat >"$_impl_gap_legacy/oos-accepted-main-agent.md" <<'EOF'
### FINDING_1: [OUT_OF_SCOPE] Legacy checkpoint orphan
- **Description**: no disposition
- **Phase**: implement
EOF
printf 'run-gap-legacy\n' >"$_impl_gap_legacy/session-id"
mkdir -p "$_impl_gap_legacy/larch-logs/implement/run-gap-legacy"
: >"$_impl_gap_legacy/larch-logs/implement/run-gap-legacy/oos-issues.ndjson"
set +e
(
  cd "$ORPHAN_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_gap_legacy" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint legacy FINDING disposition gap exit 1" 1 "$rc"
if grep -Fq 'step-8-oos-checkpoint' "$_impl_gap_legacy/execution-issues.md" \
  && ! grep -Fq 'step-8-oos-checkpoint-validation' "$_impl_gap_legacy/execution-issues.md" \
  && grep -Fq 'oos-disposition-gate' "$_impl_gap_legacy/execution-issues.md" \
  && grep -Fq 'Tool Failures' "$_impl_gap_legacy/execution-issues.md" \
  && [ -s "$_impl_gap_legacy/oos-disposition-gate.stderr.log" ]; then
  pass "checkpoint legacy FINDING disposition gap logs Tool Failures"
else
  fail "checkpoint legacy FINDING disposition gap missing Tool Failures log entry or gate stderr"
fi

# --- Case: checkpoint fork-mode skip ---
_impl_fork=$(mkitmp)
printf 'FORKED_TARGET=true\n' >"$_impl_fork/ship-pr-state.sh"
printf 'REPO_UNAVAILABLE=false\n' >>"$_impl_fork/ship-pr-state.sh"
cat >"$_impl_fork/oos-accepted-main-agent.md" <<'EOF'
### OOS_1: Orphan
- **Description**: no disposition
- **Phase**: implement
EOF
set +e
(
  cd "$ORPHAN_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_fork" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint fork-mode skip" 0 "$rc"

# --- Case: checkpoint repo-unavailable skip ---
_impl_unavail=$(mkitmp)
printf 'FORKED_TARGET=false\n' >"$_impl_unavail/ship-pr-state.sh"
printf 'REPO_UNAVAILABLE=true\n' >>"$_impl_unavail/ship-pr-state.sh"
cat >"$_impl_unavail/oos-accepted-main-agent.md" <<'EOF'
### OOS_1: Orphan
- **Description**: no disposition
- **Phase**: implement
EOF
set +e
(
  cd "$ORPHAN_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_unavail" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint repo-unavailable skip" 0 "$rc"

# --- Case: checkpoint ndjson RUN_ID-keyed path ---
_impl_runid=$(mkitmp)
printf 'run-keyed\n' >"$_impl_runid/session-id"
mkdir -p "$_impl_runid/larch-logs/implement/run-keyed"
cat >"$_impl_runid/larch-logs/implement/run-keyed/oos-issues.ndjson" <<'EOF'
{"phase":"code-review","step":"9a.1","category":"OOS","body":"## Rejected / Out-of-Scope Observations (not filed)\n\n### OOS_1: Orphan\nRejected.\n"}
EOF
cat >"$_impl_runid/oos-accepted-main-agent.md" <<'EOF'
### OOS_1: Orphan
- **Phase**: implement
EOF
set +e
(
  cd "$ORPHAN_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_runid" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint ndjson RUN_ID-keyed rejection satisfies" 0 "$rc"

# --- Case: checkpoint stale RUN_ID does not bind a sole foreign ndjson ---
_impl_stale=$(mkitmp)
printf 'run-missing\n' >"$_impl_stale/session-id"
mkdir -p "$_impl_stale/larch-logs/implement/foreign-run"
cat >"$_impl_stale/larch-logs/implement/foreign-run/oos-issues.ndjson" <<'EOF'
{"phase":"code-review","step":"9a.1","category":"OOS","body":"## Rejected / Out-of-Scope Observations (not filed)\n\n### OOS_1: Foreign\nRejected.\n"}
EOF
cat >"$_impl_stale/oos-accepted-main-agent.md" <<'EOF'
### OOS_1: Foreign
- **Phase**: implement
EOF
set +e
(
  cd "$ORPHAN_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_stale" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint stale RUN_ID rejects foreign ndjson fallback" 2 "$rc"
if grep -Fq 'step-8-oos-checkpoint-validation' "$_impl_stale/execution-issues.md" \
  && [ -s "$_impl_stale/oos-disposition-checkpoint.stderr.log" ]; then
  pass "checkpoint stale RUN_ID logs validation failure"
else
  fail "checkpoint stale RUN_ID missing validation log or checkpoint stderr"
fi

# --- Case: checkpoint find-fallback when session-id absent ---
_impl_find=$(mkitmp)
mkdir -p "$_impl_find/larch-logs/implement/solo-run"
cat >"$_impl_find/larch-logs/implement/solo-run/oos-issues.ndjson" <<'EOF'
{"phase":"code-review","step":"9a.1","category":"OOS","body":"## Rejected / Out-of-Scope Observations (not filed)\n\n### OOS_1: Solo\nRejected.\n"}
EOF
cat >"$_impl_find/oos-accepted-main-agent.md" <<'EOF'
### OOS_1: Solo
- **Phase**: implement
EOF
set +e
(
  cd "$ORPHAN_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_find" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint single ndjson find-fallback" 0 "$rc"

# --- Case: checkpoint ambiguity exit 2 ---
_impl_amb=$(mkitmp)
mkdir -p "$_impl_amb/larch-logs/implement/run-a" "$_impl_amb/larch-logs/implement/run-b"
: >"$_impl_amb/larch-logs/implement/run-a/oos-issues.ndjson"
: >"$_impl_amb/larch-logs/implement/run-b/oos-issues.ndjson"
set +e
"$CHECKPOINT" --implement-tmpdir "$_impl_amb" >/dev/null 2>&1
rc=$?
set -e
assert_rc "checkpoint ambiguous ndjson exit 2" 2 "$rc"
if grep -Fq 'step-8-oos-checkpoint-validation' "$_impl_amb/execution-issues.md" \
  && grep -Fq 'Tool Failures' "$_impl_amb/execution-issues.md" \
  && grep -Fq 'oos-disposition-checkpoint' "$_impl_amb/execution-issues.md" \
  && [ -s "$_impl_amb/oos-disposition-checkpoint.stderr.log" ]; then
  pass "checkpoint ambiguity logs validation failure"
else
  fail "checkpoint ambiguity missing validation log or checkpoint stderr"
fi

# --- Case: checkpoint precondition exit 2 (non-sec OOS, no ndjson) ---
_impl_pre=$(mkitmp)
cat >"$_impl_pre/oos-accepted-main-agent.md" <<'EOF'
### OOS_1: Needs ndjson
- **Phase**: implement
EOF
set +e
(
  cd "$GIT_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_pre" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint precondition missing ndjson exit 2" 2 "$rc"
if grep -Fq 'step-8-oos-checkpoint-validation' "$_impl_pre/execution-issues.md" \
  && [ -s "$_impl_pre/oos-disposition-checkpoint.stderr.log" ]; then
  pass "checkpoint precondition logs validation failure"
else
  fail "checkpoint precondition missing validation log or checkpoint stderr"
fi

# --- Case: checkpoint gate-exit-2 passthrough (gate validation, not disposition gap) ---
_impl_g2=$(mktemp -d "${TMPDIR:-/tmp}/oos-chk-g2.XXXXXX")
TMPDIRS+=("$_impl_g2")
: >"$_impl_g2/execution-issues.md"
printf '%s\n' 'FORKED_TARGET=false' >"$_impl_g2/ship-pr-state.sh"
printf '%s\n' 'REPO_UNAVAILABLE=false' >>"$_impl_g2/ship-pr-state.sh"
mkdir -p "$_impl_g2/larch-logs/implement/run-g2val"
cat >"$_impl_g2/larch-logs/implement/run-g2val/oos-issues.ndjson" <<'EOF'
{"body":"Created https://github.com/example/larch/issues/404\n"}
EOF
printf 'run-g2val\n' >"$_impl_g2/session-id"
# Accepted CSV paths absent on disk; ndjson lists filed URLs — gate exit 2
set +e
(
  cd "$GIT_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_g2" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint gate validation exit 2" 2 "$rc"
if grep -Fq 'step-8-oos-checkpoint-validation' "$_impl_g2/execution-issues.md" \
  && [ -s "$_impl_g2/oos-disposition-gate.stderr.log" ]; then
  pass "checkpoint gate-exit-2 uses gate stderr log"
else
  fail "checkpoint gate-exit-2 missing validation log or gate stderr"
fi

# --- Case: merge-base absent uses origin/main..HEAD and proceeds ---
MB_TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-oos-gate-mb.XXXXXX")
TMPDIRS+=("$MB_TMP")
_impl_mb=$(mkitmp)
(
  cd "$MB_TMP"
  git init -q
  git config user.email test@test
  git config user.name test
  git commit --allow-empty -q -m "unrelated root for origin/main"
  _origin_main=$(git rev-parse HEAD)
  git checkout --orphan feature -q
  git commit --allow-empty -q -m "feature head without inline triage"
  git update-ref refs/remotes/origin/main "$_origin_main"
)
cat >"$_impl_mb/oos-accepted-main-agent.md" <<'EOF'
### OOS_1: Range proof
- **Phase**: implement
EOF
printf 'run-mb\n' >"$_impl_mb/session-id"
mkdir -p "$_impl_mb/larch-logs/implement/run-mb"
: >"$_impl_mb/larch-logs/implement/run-mb/oos-issues.ndjson"
set +e
(
  cd "$MB_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_mb" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint merge-base absent uses origin/main..HEAD disposition range" 1 "$rc"
if grep -Fq 'commit-range origin/main..HEAD' "$_impl_mb/oos-disposition-gate.stderr.log"; then
  pass "checkpoint merge-base absent logs origin/main..HEAD range"
else
  fail "checkpoint merge-base absent did not exercise origin/main..HEAD range"
fi

# --- Case: origin/main absent uses HEAD range ---
_impl_head=$(mkitmp)
cat >"$_impl_head/oos-accepted-main-agent.md" <<'EOF'
### OOS_1: HEAD range proof
- **Phase**: implement
EOF
printf 'run-head\n' >"$_impl_head/session-id"
mkdir -p "$_impl_head/larch-logs/implement/run-head"
: >"$_impl_head/larch-logs/implement/run-head/oos-issues.ndjson"
set +e
(
  cd "$ORPHAN_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_head" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint origin/main absent uses HEAD disposition range" 1 "$rc"
if grep -Fq 'commit-range HEAD' "$_impl_head/oos-disposition-gate.stderr.log"; then
  pass "checkpoint origin/main absent logs HEAD range"
else
  fail "checkpoint origin/main absent did not exercise HEAD range"
fi

# --- Case: design-path via --design-tmpdir ---
DESIGN_TMP=$(mktemp -d "${TMPDIR:-/tmp}/oos-design-tmp.XXXXXX")
TMPDIRS+=("$DESIGN_TMP")
_impl_des=$(mkitmp)
cat >"$DESIGN_TMP/oos-accepted-design.md" <<'EOF'
### OOS_1: Design strict
- **Phase**: implement
- **Filed URL**: https://github.com/example/larch/issues/3100
EOF
printf 'run-design\n' >"$_impl_des/session-id"
mkdir -p "$_impl_des/larch-logs/implement/run-design"
: >"$_impl_des/larch-logs/implement/run-design/oos-issues.ndjson"
set +e
(
  cd "$ORPHAN_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_des" --design-tmpdir "$DESIGN_TMP" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint design-tmpdir strict URL passes" 0 "$rc"

DESIGN_TMP_FAIL=$(mktemp -d "${TMPDIR:-/tmp}/oos-design-tmp-fail.XXXXXX")
TMPDIRS+=("$DESIGN_TMP_FAIL")
_impl_des_fail=$(mkitmp)
cat >"$DESIGN_TMP_FAIL/oos-accepted-design.md" <<'EOF'
### OOS_1: Design unresolved
- **Phase**: implement
EOF
printf 'run-design-fail\n' >"$_impl_des_fail/session-id"
mkdir -p "$_impl_des_fail/larch-logs/implement/run-design-fail"
: >"$_impl_des_fail/larch-logs/implement/run-design-fail/oos-issues.ndjson"
set +e
(
  cd "$ORPHAN_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_des_fail" --design-tmpdir "$DESIGN_TMP_FAIL" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint design-tmpdir unresolved OOS fails via design path" 1 "$rc"

# --- Case: design-export fallback ---
_impl_export=$(mkitmp)
mkdir -p "$_impl_export/design-export"
cat >"$_impl_export/design-export/oos-accepted-design.md" <<'EOF'
### OOS_1: Export strict
- **Phase**: implement
- **Filed URL**: https://github.com/example/larch/issues/3200
EOF
printf 'run-export\n' >"$_impl_export/session-id"
mkdir -p "$_impl_export/larch-logs/implement/run-export"
: >"$_impl_export/larch-logs/implement/run-export/oos-issues.ndjson"
set +e
(
  cd "$ORPHAN_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_export" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint design-export fallback passes" 0 "$rc"

_impl_export_fail=$(mkitmp)
mkdir -p "$_impl_export_fail/design-export"
cat >"$_impl_export_fail/design-export/oos-accepted-design.md" <<'EOF'
### OOS_1: Export unresolved
- **Phase**: implement
EOF
printf 'run-export-fail\n' >"$_impl_export_fail/session-id"
mkdir -p "$_impl_export_fail/larch-logs/implement/run-export-fail"
: >"$_impl_export_fail/larch-logs/implement/run-export-fail/oos-issues.ndjson"
set +e
(
  cd "$ORPHAN_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_export_fail" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint design-export unresolved OOS fails via export path" 1 "$rc"

# --- Case: missing --design-tmpdir value logs under implement tmpdir even before normal parse reaches it ---
_impl_missing_design=$(mkitmp)
set +e
"$CHECKPOINT" --design-tmpdir --implement-tmpdir "$_impl_missing_design" >/dev/null 2>&1
rc=$?
set -e
assert_rc "checkpoint missing design-tmpdir value exit 2" 2 "$rc"
if grep -Fq 'step-8-oos-checkpoint-validation' "$_impl_missing_design/execution-issues.md" \
  && grep -Fq 'oos-disposition-checkpoint' "$_impl_missing_design/execution-issues.md" \
  && grep -Fq 'Tool Failures' "$_impl_missing_design/execution-issues.md"; then
  pass "checkpoint missing design-tmpdir value logs under implement tmpdir"
else
  fail "checkpoint missing design-tmpdir value did not log under implement tmpdir"
fi

# --- Case: checkpoint security sidecar leaves private-disposition status ---
_impl_sec=$(mkitmp)
printf '### Security OOS: Private audit\n- **focus-area**: security-hardening\n' \
  >"$_impl_sec/security-oos-observations.md"
set +e
(
  cd "$ORPHAN_TMP"
  "$CHECKPOINT" --implement-tmpdir "$_impl_sec" >/dev/null 2>&1
)
rc=$?
set -e
assert_rc "checkpoint security sidecar exit 3" 3 "$rc"
if grep -Fq 'security sidecar present; non-security OOS disposition cleared' \
  "$_impl_sec/oos-disposition-checkpoint.stderr.log" \
  && grep -Fq 'step-8-oos-checkpoint-security-sidecar' "$_impl_sec/execution-issues.md"; then
  pass "checkpoint security sidecar logs private-disposition status"
else
  fail "checkpoint security sidecar missing private-disposition log or checkpoint stderr"
fi

if [ "$FAIL" -ne 0 ]; then
  echo "$FAIL case(s) failed, $PASS passed" >&2
  exit 1
fi
echo "All $PASS cases passed."
