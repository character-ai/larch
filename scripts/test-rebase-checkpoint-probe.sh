#!/usr/bin/env bash
# Offline harness: scripts/rebase-checkpoint-probe.sh (see .md sibling).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
unset LARCH_BREADCRUMB_STREAM LARCH_QUIET_ACTIVE LARCH_QUIET_PID \
    LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG LARCH_QUIET_BREADCRUMB_FD \
    LARCH_BREADCRUMBS_SURFACED_FILE 2>/dev/null || true
export LARCH_QUIET_BREADCRUMBS=1

SUT_PROD="$REPO_ROOT/scripts/rebase-checkpoint-probe.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }

[ -x "$SUT_PROD" ] || fail "case 17: production rebase-checkpoint-probe.sh must be executable"

TMPROOT="$(mktemp -d /tmp/larch-test-rebase-probe-XXXXXX)"
trap 'rm -rf "$TMPROOT"' EXIT

stage_with_stubs() {
    local d="$1"
    mkdir -p "$d"
    cp "$REPO_ROOT/scripts/rebase-checkpoint-probe.sh" "$d/"
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$d/"
    cp "$REPO_ROOT/scripts/lib-phantom-probe.sh" "$d/"
    chmod +x "$d/rebase-checkpoint-probe.sh"
}

IMP_BASE="$TMPROOT/imp"
mkdir -p "$IMP_BASE"
touch "$IMP_BASE/untracked-baseline.z"
touch "$IMP_BASE/execution-issues.md"

# --- Case 1: green ---
d="$TMPROOT/c1"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
echo APPENDED=true
exit 0
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" 1.r 'plan materialization' 2>&1) || fail "case1 rc"
echo "$out" | grep -Fq 'REBASE_OUTCOME=ok' || fail "case1 outcome"
echo "$out" | grep -Fq 'PHANTOM_STATUS=clean' || fail "case1 phantom"
echo "$out" | grep -Fq '→ rebase-probe: 1.r plan materialization' || fail "case1 breadcrumb"

# --- Case 2: pushed before fresh precedence ---
d="$TMPROOT/c2"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' 'SKIPPED_ALREADY_FRESH=true' 'SKIPPED_ALREADY_PUSHED=true'
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
echo APPENDED=true
exit 0
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1) || fail "case2 rc"
echo "$out" | grep -Fq 'SKIPPED_ALREADY_PUSHED=true' || fail "case2 pushed"
echo "$out" | grep -Fq 'REBASE_OUTCOME=skipped' || fail "case2 skipped"
if echo "$out" | grep -Fq 'SKIPPED_ALREADY_FRESH=true'; then
    fail "case2 fresh must not emit when pushed wins"
fi

# --- Case 3: fresh only ---
d="$TMPROOT/c3"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
echo SKIPPED_ALREADY_FRESH=true
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1) || fail "case3 rc"
echo "$out" | grep -Fq 'SKIPPED_ALREADY_FRESH=true' || fail "case3 fresh"
echo "$out" | grep -Fq 'REBASE_OUTCOME=skipped' || fail "case3 skipped"

# --- Case 4: conflict + CONFLICT_FILES, no phantom ---
d="$TMPROOT/c4"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
echo CONFLICT_FILES=a.txt,b.txt
exit 1
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo SHOULD_NOT_RUN=1
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
set +e
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "1" ] || fail "case4 rc=$rc"
echo "$out" | grep -Fq 'REBASE_OUTCOME=conflict' || fail "case4 outcome"
echo "$out" | grep -Fq 'CONFLICT_FILES=a.txt,b.txt' || fail "case4 files"
if echo "$out" | grep -Fq 'PHANTOM_STATUS'; then
    fail "case4 phantom must not run"
fi

# --- Case 5: conflict missing CONFLICT_FILES (defensive git diff) ---
d="$TMPROOT/c5"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
set +e
out=$(cd "$REPO_ROOT" && IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "1" ] || fail "case5 rc=$rc"
echo "$out" | grep -Fq 'REBASE_OUTCOME=conflict' || fail "case5 outcome"

# --- Case 6: rc=3 stdout REBASE_ERROR ---
d="$TMPROOT/c6"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
echo REBASE_ERROR=fetch-failed
exit 3
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
set +e
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "3" ] || fail "case6 rc=$rc"
echo "$out" | grep -Fq 'REBASE_ERROR=fetch-failed' || fail "case6 err"

# --- Case 7: rc=3 stderr REBASE_ERROR ---
d="$TMPROOT/c7"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' 'REBASE_ERROR=stderr-err' >&2
exit 3
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
set +e
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "3" ] || fail "case7 rc=$rc"
echo "$out" | grep -Fq 'REBASE_ERROR=stderr-err' || fail "case7 err"

# --- Case 8: unexpected rc ---
d="$TMPROOT/c8"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 7
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
set +e
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1)
rc=$?
set -e
[ "$rc" = "7" ] || fail "case8 rc=$rc"
echo "$out" | grep -Fq 'REBASE_ERROR=unexpected-rc-7' || fail "case8 unexpected"

# --- Case 9 (phantom clean) ---
d="$TMPROOT/c9x"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1) || fail "c9x"
echo "$out" | grep -Fq 'PHANTOM_STATUS=clean' || fail "c9x status"

# --- Case 10 ---
d="$TMPROOT/c10x"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=tracked-only
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1) || fail "c10x"
echo "$out" | grep -Fq 'PHANTOM_STATUS=tracked-only' || fail "c10x"

# --- Case 11 phantom + append ---
d="$TMPROOT/c11x"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=phantom
echo PHANTOM_COUNT=1
echo PHANTOM_PATHS_FILE=/tmp/x.z
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
echo FAILED=true
echo ERROR=cap-test
exit 2
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1) || fail "c11x rc"
echo "$out" | grep -Fq 'PHANTOM_APPEND_WARN_ERROR=cap-test' || fail "c11x append err"

# --- Case 12 unknown append stderr fallback ---
d="$TMPROOT/c12x"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=unknown
echo REASON=probe-ambiguous
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' 'some stderr' >&2
exit 2
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y 2>&1) || fail "c12x rc"
echo "$out" | grep -Fq 'PHANTOM_APPEND_WARN_ERROR=' || fail "c12x append fold"

# --- Case 13: base args pass-through ---
d="$TMPROOT/c13"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" >"$(dirname "$0")/rebase.argv"
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" p s --base-remote upstream --base-ref main >/dev/null 2>&1 || fail "c13 rc"
grep -Fq -- '--base-remote' "$d/rebase.argv" || fail "c13 remote"
grep -Fq -- 'upstream' "$d/rebase.argv" || fail "c13 upstream val"
grep -Fq -- '--base-ref' "$d/rebase.argv" || fail "c13 ref flag"
grep -Fq -- 'main' "$d/rebase.argv" || fail "c13 main val"

# --- Case 14: regex rejection (real rebase-push) ---
gitrepo="$TMPROOT/gitregex"
mkdir -p "$gitrepo"
git -C "$gitrepo" init -q
git -C "$gitrepo" config user.email t@e
git -C "$gitrepo" config user.name T
printf 'x\n' >"$gitrepo/README.md"
git -C "$gitrepo" add README.md
git -C "$gitrepo" commit -q -m init
d="$TMPROOT/c14"
mkdir -p "$d"
cp "$REPO_ROOT/scripts/rebase-checkpoint-probe.sh" "$d/"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$d/"
cp "$REPO_ROOT/scripts/lib-phantom-probe.sh" "$d/"
cp "$REPO_ROOT/scripts/rebase-push.sh" "$d/"
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
chmod +x "$d/rebase-push.sh"
set +e
out=$(cd "$gitrepo" && IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" x y --base-remote 'bad name' 2>&1)
rc=$?
set -e
[ "$rc" = "3" ] || fail "case14 rc=$rc got $out"
echo "$out" | grep -Fq 'REBASE_OUTCOME=failed' || fail "case14 failed"
echo "$out" | grep -Fq 'REBASE_ERROR=' || fail "case14 err"

# --- Case 15: breadcrumb count ---
d="$TMPROOT/c15"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
out=$(IMPLEMENT_TMPDIR="$IMP_BASE" "$d/rebase-checkpoint-probe.sh" a b 2>&1) || fail "c15"
bc=$(printf '%s\n' "$out" | grep -c '→ rebase-probe:' || true)
[ "$bc" = "1" ] || fail "case15 breadcrumb count=$bc"

# --- Case 16: double-source library ---
d="$TMPROOT/c16"
stage_with_stubs "$d"
cat >"$d/rebase-push.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$d/check-phantom-dirty.sh" <<'EOF'
#!/usr/bin/env bash
echo STATUS=clean
exit 0
EOF
cat >"$d/append-execution-issue.sh" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$d"/*.sh
bash -c "set -euo pipefail; source \"$d/lib-phantom-probe.sh\"; source \"$d/lib-phantom-probe.sh\"; IMPLEMENT_TMPDIR=\"$IMP_BASE\" \"$d/rebase-checkpoint-probe.sh\" z z" >/dev/null || fail "c16"

echo "PASS: test-rebase-checkpoint-probe.sh"
exit 0
